"""Selected water-volume arithmetic with explicit measurement roles and context."""
import copy
from decimal import localcontext
import json

from .contract_validation import validate_state
from .data_tools import baseline, convert, kpi, number, serialize
from .state_proposal import propose


OPERATIONS = {"build-water-baseline": {"quantities", "coverage_review", "result_id"},
              "calculate-water-intensity": {"baseline_result_id", "denominator_id", "denominator_review", "result_id"},
              "identify-water-hotspots": {"baseline_result_id", "result_id"}}
BASES = {"withdrawal", "discharge", "consumption", "internal_reuse", "metered_use"}


def run_water(state, skill, parameters):
    validate_state(state)
    if skill not in OPERATIONS or not isinstance(parameters, dict) or set(parameters) != OPERATIONS[skill]:
        raise ValueError("Supported water operation with exact parameters required.")
    ident = parameters["result_id"]
    if not isinstance(ident, str) or not ident.strip(): raise ValueError("Result ID required.")
    result = {"id": ident, "skill": skill, "contract_version": "0.1.0", "status": "completed", "review_states": ["ANALYTICAL"],
              "review_requirements": copy.deepcopy(state["review_requirements"]), "metrics": [], "evidence_ids": [],
              "assumptions": list(state["assumptions"]), "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}
    known = {e["id"] for e in state["evidence"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    refs = set()

    def review(record, fields):
        evidence = record.get("evidence_ids") if isinstance(record, dict) else None
        if (not isinstance(record, dict) or record.get("confirmed") is not True or not isinstance(evidence, list)
                or not evidence or any(not isinstance(e, str) for e in evidence) or not set(evidence) <= known
                or any(not isinstance(record.get(f), str) or not record[f].strip() for f in fields)):
            raise ValueError("Explicit source-backed water context/coverage review required.")
        refs.update(evidence)

    def resolve(key, volume=True):
        metric = metrics.get(key)
        if (metric is None or metric["value"] is None or number(metric["value"]) < 0
                or metric["period"] != state["reporting_period"] or metric["boundary_id"] != state["organizational_boundary"]["id"]):
            raise ValueError("Compatible nonnegative volume/activity required; unknown is not zero.")
        if volume: convert(metric["value"], metric["unit"], "m3")
        refs.update(metric["evidence_ids"])
        return metric

    def gap(code, reason):
        result["data_gaps"].append({"id": f"{ident}-gap-{len(result['data_gaps'])}", "field": "water_analysis", "reason": reason,
            "impact": "Selected coverage or local interpretation remains incomplete.", "remedy": "Supply compatible water quantities, measurement roles and facility/catchment context."})
        result["diagnostics"].append({"code": code, "message": reason})

    def emit(suffix, name, value, unit, inputs, formula):
        result["metrics"].append({"id": ident+"-"+suffix, "name": name, "value": serialize(value), "unit": unit,
            "period": copy.deepcopy(state["reporting_period"]), "boundary_id": state["organizational_boundary"]["id"], "evidence_ids": sorted(refs),
            "method": {"name": "Explicit selected water-volume arithmetic", "version": "0.1.0", "source": "docs/water-contract.md"}, "assumption": None,
            "uncertainty": {"kind": "unquantified", "description": "Supplied measurement and local-context judgments are not independently verified.", "value": None, "unit": None},
            "calculation": {"formula": formula, "inputs": inputs, "conversions": ["Supported volume units converted to m3; no mass density, consumption or water-stress inference."], "rounding": "34-digit Decimal arithmetic; JSON serialization"}})

    def aggregate(quantities, record):
        review(record, ("basis", "measurement_boundary", "nonoverlap_assessment", "coverage", "rationale"))
        if record["basis"] not in BASES or not isinstance(record.get("coverage_complete"), bool):
            raise ValueError("Explicit measurement basis and boolean coverage completeness required.")
        if not isinstance(quantities, list) or not quantities or any(not isinstance(q, dict) for q in quantities):
            raise ValueError("Nonempty source-context quantity register required.")
        ids = []
        for quantity in quantities:
            if (set(quantity) != {"metric_id", "basis", "facility_id", "source_kind", "catchment", "evidence_ids"}
                    or quantity["basis"] != record["basis"] or quantity["facility_id"] not in state["organizational_boundary"]["facility_ids"]
                    or not isinstance(quantity["source_kind"], str) or not quantity["source_kind"].strip()
                    or quantity["catchment"] is not None and (not isinstance(quantity["catchment"], str) or not quantity["catchment"].strip())):
                raise ValueError("Match basis, facility and source context for every quantity; do not mix withdrawal/discharge/reuse.")
            if quantity["basis"] == "withdrawal" and quantity["source_kind"] == "internal_reuse":
                raise ValueError("Internal reuse is not a new external withdrawal.")
            review(dict(quantity, confirmed=True), ())
            ids.append(quantity["metric_id"])
        if any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Distinct volume quantity IDs required.")
        selected = [resolve(i) for i in ids]
        for key in ids:
            pending, seen = list(metrics[key]["calculation"]["inputs"]), set()
            while pending:
                parent = pending.pop()
                if parent in seen: continue
                seen.add(parent)
                if parent in metrics: pending.extend(metrics[parent]["calculation"]["inputs"])
            if (set(ids)-{key}) & seen: raise ValueError("Water total and its component quantities cannot both enter the baseline.")
        total = baseline(selected, "m3", True, record.get("coverage_details"))["value"]
        if not record["coverage_complete"]: gap("WATER_COVERAGE_REQUIRED", "Selected water baseline is incomplete; total describes supported selected coverage only.")
        if any(q["catchment"] is None for q in quantities): gap("WATER_LOCAL_CONTEXT_REQUIRED", "Catchment context is missing; volume supports arithmetic, not water-stress or impact conclusions.")
        return total, selected

    try:
        if skill == "build-water-baseline":
            total, selected = aggregate(parameters["quantities"], parameters["coverage_review"])
            emit("volume", "Selected water "+parameters["coverage_review"]["basis"]+" baseline", total, "m3", [m["id"] for m in selected], "Sum nonoverlapping quantities of one declared water measurement basis")
            result["diagnostics"].append({"code": "WATER_BASELINE", "message": json.dumps(parameters, sort_keys=True)})
        else:
            prior = next((r for r in state["results"] if r["id"] == parameters["baseline_result_id"]), None)
            if prior is None or prior["skill"] != "build-water-baseline" or prior["status"] not in {"completed", "partial"} or len(prior["metrics"]) != 1:
                raise ValueError("Supported water baseline required.")
            records = [json.loads(d["message"]) for d in prior["diagnostics"] if d["code"] == "WATER_BASELINE"]
            if len(records) != 1: raise ValueError("One reproducible water coverage record required.")
            total, selected = aggregate(records[0]["quantities"], records[0]["coverage_review"])
            numerator = resolve(prior["metrics"][0]["id"])
            if (numerator["unit"] != "m3" or number(numerator["value"]) != total or set(numerator["calculation"]["inputs"]) != {m["id"] for m in selected}):
                raise ValueError("Water baseline fails source/context revalidation.")
            if skill == "calculate-water-intensity":
                denominator = resolve(parameters["denominator_id"], False)
                record = parameters["denominator_review"]; review(record, ("definition", "unit", "rationale"))
                if record.get("metric_id") != denominator["id"] or record["unit"] != denominator["unit"] or denominator["unit"] == "UNKNOWN_UNIT":
                    raise ValueError("Document the exact denominator definition and unit.")
                value = kpi(numerator, denominator, "ratio")
                emit("intensity", "Selected water "+records[0]["coverage_review"]["basis"]+" intensity", value["value"], value["unit"], [numerator["id"], denominator["id"]], "Declared water-basis m3 / positive evidenced activity denominator")
            else:
                ranked = sorted(selected, key=lambda m: (-convert(m["value"], m["unit"], "m3")["value"], m["id"]))
                with localcontext() as context:
                    context.prec = 34
                    for rank, metric in enumerate(ranked, 1):
                        value = convert(metric["value"], metric["unit"], "m3")["value"]
                        emit(f"rank-{rank}", "Selected water contribution: "+metric["id"], value, "m3", [metric["id"]], "Selected nonoverlapping component converted to m3")
                        if total > 0: emit(f"share-{rank}", "Selected water baseline share", value/total*100, "%", [metric["id"], numerator["id"]], "Component / selected baseline * 100")
                if total == 0: gap("PERCENTAGE_DENOMINATOR_REQUIRED", "Zero baseline supports zero volumes, not percentage shares.")
                result["diagnostics"].append({"code": "WATER_HOTSPOT_LIMITS", "message": "Selected volume contributions only; not local stress, quality, impact or efficiency ranking."})
    except (ValueError, KeyError, TypeError) as error:
        result["metrics"] = []; gap("WATER_DATA_REQUIRED", str(error))
    result["evidence_ids"] = sorted(refs)
    result["status"] = "blocked" if not result["metrics"] else ("partial" if result["data_gaps"] else "completed")
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"] == "open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE"); result["next_actions"] = list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    proposal = propose(state, result, "Compute selected water volumes without local-impact inference or approval")
    if result["metrics"]:
        proposal["state"]["water"].append(ident); validate_state(proposal["state"])
    return {"result": result, "proposal": proposal}
