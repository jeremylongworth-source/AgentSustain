"""Selected waste/material mass arithmetic with explicit scope and route policy."""
import copy
from decimal import localcontext
import json
import re

from .contract_validation import validate_state
from .data_tools import baseline, convert, kpi, number, serialize
from .state_proposal import propose


ROUTES = {"preparing_for_reuse", "recycling", "composting", "other_recovery", "landfill",
          "incineration_energy", "incineration_no_energy", "other_disposal", "unknown"}
OPERATIONS = {
    "build-waste-baseline": {"streams", "coverage_review", "result_id"},
    "calculate-diversion-rate": {"baseline_result_id", "route_policy", "result_id"},
    "identify-waste-hotspots": {"baseline_result_id", "result_id"},
    "analyze-material-consumption": {"metric_ids", "coverage_review", "result_id"},
    "calculate-material-intensity": {"material_result_id", "denominator_id", "denominator_review", "result_id"},
    "identify-material-loss": {"opening_stock_id", "closing_stock_id", "receipt_ids", "product_ids", "loss_ids", "other_output_ids", "balance_review", "result_id"},
    "analyze-waste-cost": {"lines", "accounting_review", "result_id"},
}


def run_resources(state, skill, parameters):
    validate_state(state)
    if skill not in OPERATIONS or not isinstance(parameters, dict) or set(parameters) != OPERATIONS[skill]:
        raise ValueError("Supported resource operation with exact parameters required.")
    ident = parameters["result_id"]
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("Result ID required.")
    result = {"id": ident, "skill": skill, "contract_version": "0.1.0", "status": "completed",
              "review_states": ["ANALYTICAL"], "review_requirements": copy.deepcopy(state["review_requirements"]),
              "metrics": [], "evidence_ids": [], "assumptions": list(state["assumptions"]),
              "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}
    refs = set()
    known = {e["id"] for e in state["evidence"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}

    def review(record, fields):
        evidence = record.get("evidence_ids") if isinstance(record, dict) else None
        if (not isinstance(record, dict) or record.get("confirmed") is not True or not isinstance(evidence, list)
                or not evidence or any(not isinstance(e, str) for e in evidence) or not set(evidence) <= known
                or any(not isinstance(record.get(f), str) or not record[f].strip() for f in fields)):
            raise ValueError("Supply explicit sourced coverage/definition review.")
        refs.update(evidence)

    def resolve(key, mass=True):
        metric = metrics.get(key)
        if (metric is None or metric["value"] is None or number(metric["value"]) < 0
                or metric["period"] != state["reporting_period"]
                or metric["boundary_id"] != state["organizational_boundary"]["id"]):
            raise ValueError("Compatible nonnegative quantity required; unknown is not zero.")
        if mass: convert(metric["value"], metric["unit"], "kg")
        refs.update(metric["evidence_ids"])
        return metric

    def selected_quantities(ids, record, mass=True):
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Unique quantity IDs required.")
        selected = [resolve(i, mass) for i in ids]
        for key in ids:
            pending, seen = list(metrics[key]["calculation"]["inputs"]), set()
            while pending:
                parent = pending.pop()
                if parent in seen: continue
                seen.add(parent)
                if parent in metrics: pending.extend(metrics[parent]["calculation"]["inputs"])
            if (set(ids)-{key}) & seen:
                raise ValueError("Aggregate and component quantities cannot both enter a total.")
        return selected

    def sum_mass(ids, record, basis):
        review(record, ("basis", "measurement_boundary", "nonoverlap_assessment", "coverage", "rationale"))
        if record["basis"] != basis:
            raise ValueError("Declare the actual measurement basis; purchases, shipments and consumption are not interchangeable.")
        selected = selected_quantities(ids, record)
        return baseline(selected, "kg", True, record.get("coverage_details"))["value"]

    def gap(code, reason):
        result["data_gaps"].append({"id": f"{ident}-gap-{len(result['data_gaps'])}", "field": "resource_analysis",
            "reason": reason, "impact": "Selected coverage or interpretation is incomplete.",
            "remedy": "Supply compatible mass records, treatment/definition evidence and coverage review."})
        result["diagnostics"].append({"code": code, "message": reason})

    def emit(suffix, name, value, unit, inputs, formula, monetary=False):
        result["metrics"].append({"id": ident+"-"+suffix, "name": name, "value": serialize(value), "unit": unit,
            "period": copy.deepcopy(state["reporting_period"]), "boundary_id": state["organizational_boundary"]["id"],
            "evidence_ids": sorted(refs), "method": {"name": "Explicit selected invoice arithmetic" if monetary else "Explicit selected mass arithmetic", "version": "0.1.0", "source": "docs/waste-resource-contract.md"},
            "assumption": None, "uncertainty": {"kind": "unquantified", "description": "Supplied invoice quantities and coverage judgments are not independently verified." if monetary else "Supplied mass, coverage and route judgments are not independently verified.", "value": None, "unit": None},
            "calculation": {"formula": formula, "inputs": inputs, "conversions": ["No currency conversion or inferred tax/tariff adjustment." if monetary else "Mass converted to kg using the supported unit registry; no volume density inferred."], "rounding": "34-digit Decimal arithmetic; JSON serialization"}})

    def waste_baseline(streams, record):
        if not isinstance(streams, list) or not streams or any(not isinstance(s, dict) for s in streams):
            raise ValueError("Nonempty waste stream register required.")
        ids = [s.get("id") for s in streams]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("Distinct waste stream IDs required.")
        for stream in streams:
            if (set(stream) != {"id", "metric_id", "material", "hazard", "route", "route_evidence_ids"}
                    or not isinstance(stream["material"], str) or not stream["material"].strip()
                    or stream["hazard"] not in {"hazardous", "nonhazardous", "unknown"}
                    or stream["route"] not in ROUTES):
                raise ValueError("Declare material, assessed hazard, treatment route and its evidence for every stream.")
            if stream["route"] != "unknown":
                review({"confirmed": True, "evidence_ids": stream["route_evidence_ids"]}, ())
            elif stream["route_evidence_ids"]:
                review({"confirmed": True, "evidence_ids": stream["route_evidence_ids"]}, ())
        return sum_mass([s["metric_id"] for s in streams], record, "generated_waste_same_cohort")

    try:
        if skill == "build-waste-baseline":
            total = waste_baseline(parameters["streams"], parameters["coverage_review"])
            emit("mass", "Selected generated waste mass", total, "kg", [s["metric_id"] for s in parameters["streams"]], "Sum of nonoverlapping selected generated waste masses")
            for stream in parameters["streams"]:
                if stream["route"] == "unknown" or stream["hazard"] == "unknown":
                    gap("WASTE_CLASSIFICATION_REQUIRED", "Unresolved route/hazard for stream "+stream["id"]+"; mass remains in selected total.")
            result["diagnostics"].append({"code": "WASTE_BASELINE", "message": json.dumps(parameters, sort_keys=True)})
        elif skill in {"calculate-diversion-rate", "identify-waste-hotspots"}:
            prior = next((r for r in state["results"] if r["id"] == parameters["baseline_result_id"]), None)
            if prior is None or prior["skill"] != "build-waste-baseline" or prior["status"] not in {"completed", "partial"} or len(prior["metrics"]) != 1:
                raise ValueError("Supported waste baseline required.")
            records = [json.loads(d["message"]) for d in prior["diagnostics"] if d["code"] == "WASTE_BASELINE"]
            if len(records) != 1: raise ValueError("One reproducible stream coverage record required.")
            record = records[0]
            total = waste_baseline(record["streams"], record["coverage_review"])
            previous = prior["metrics"][0]
            if (previous["unit"] != "kg" or number(previous["value"]) != total
                    or set(previous["calculation"]["inputs"]) != {s["metric_id"] for s in record["streams"]}
                    or previous["period"] != state["reporting_period"] or previous["boundary_id"] != state["organizational_boundary"]["id"]):
                raise ValueError("Waste total fails revalidation against its selected sources.")
            if skill == "calculate-diversion-rate":
                policy = parameters["route_policy"]
                review(policy, ("name", "version", "source", "rationale"))
                routes = policy.get("included_routes")
                if (not isinstance(routes, list) or any(not isinstance(r, str) for r in routes)
                        or len(routes) != len(set(routes)) or not set(routes) <= ROUTES-{"unknown", "landfill", "other_disposal", "incineration_no_energy"}):
                    raise ValueError("Explicit supported diversion routes required; unknown/disposal cannot be counted as diverted.")
                with localcontext() as context:
                    context.prec = 34
                    amount = sum((convert(resolve(s["metric_id"])["value"], metrics[s["metric_id"]]["unit"], "kg")["value"]
                                  for s in record["streams"] if s["route"] in routes), number(0))
                    emit("diverted-mass", "Known selected diverted mass under supplied policy", amount, "kg", [s["metric_id"] for s in record["streams"]], "Filter selected generated masses by evidenced eligible treatment routes, then sum")
                    if total > 0:
                        emit("rate", "Known diversion / selected generated mass", amount/total*100, "%", [s["metric_id"] for s in record["streams"]], "Known eligible routed mass / selected generated mass * 100")
                    else: gap("PERCENTAGE_DENOMINATOR_REQUIRED", "Zero generated waste supports mass, not a diversion percentage.")
                if any(s["route"] == "unknown" for s in record["streams"]):
                    gap("WASTE_ROUTE_REQUIRED", "Unknown routes remain in denominator; known diversion is a lower-bound subtotal, not a complete rate.")
                result["diagnostics"].append({"code": "DIVERSION_POLICY", "message": json.dumps(policy, sort_keys=True)})
            else:
                ranked = sorted(record["streams"], key=lambda s: (-convert(metrics[s["metric_id"]]["value"], metrics[s["metric_id"]]["unit"], "kg")["value"], s["id"]))
                for rank, stream in enumerate(ranked, 1):
                    value = convert(metrics[stream["metric_id"]]["value"], metrics[stream["metric_id"]]["unit"], "kg")["value"]
                    emit(f"rank-{rank}", "Selected waste contribution: "+stream["id"], value, "kg", [stream["metric_id"]], "Selected stream mass converted to kg; mass order only")
                result["diagnostics"].append({"code": "WASTE_HOTSPOT_LIMITS", "message": "Mass contribution order, not hazard, cost or impact ranking; selected coverage only."})
            if prior["status"] == "partial": gap("PARTIAL_WASTE_BASELINE", "Selected baseline is partial; preserve coverage/classification limitations.")
        elif skill == "analyze-material-consumption":
            value = sum_mass(parameters["metric_ids"], parameters["coverage_review"], "consumed_material")
            emit("mass", "Selected consumed material mass", value, "kg", parameters["metric_ids"], "Sum of nonoverlapping documented consumed material masses; not purchases")
            result["diagnostics"].append({"code": "MATERIAL_BASELINE", "message": json.dumps(parameters, sort_keys=True)})
        elif skill == "analyze-waste-cost":
            record = parameters["accounting_review"]
            review(record, ("currency", "measurement_boundary", "nonoverlap_assessment", "coverage", "allocation_basis", "rationale"))
            if (not re.fullmatch(r"[A-Z]{3}", record["currency"]) or record.get("basis") != "documented_invoice_lines"
                    or record.get("tax_basis") not in {"included_as_recorded", "excluded_as_recorded"}
                    or not isinstance(record.get("coverage_complete"), bool)):
                raise ValueError("Declare invoice basis, explicit currency code, recorded tax treatment and coverage completeness.")
            lines = parameters["lines"]
            if not isinstance(lines, list) or not lines or any(not isinstance(line, dict) for line in lines):
                raise ValueError("Nonempty invoice-line register required.")
            ids = [line.get("id") for line in lines]
            if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
                raise ValueError("Unique invoice line IDs required.")
            for line in lines:
                if (set(line) != {"id", "metric_id", "kind", "category"}
                        or line["kind"] not in {"charge", "credit"}
                        or line["category"] not in {"haul", "treatment", "rental", "tax", "surcharge", "other", "rebate"}
                        or (line["kind"] == "credit") != (line["category"] == "rebate")):
                    raise ValueError("Declare nonnegative recorded charge/credit quantities with matching cost categories.")
            selected = selected_quantities([line["metric_id"] for line in lines], record, False)
            if any(metric["unit"] != record["currency"] for metric in selected):
                raise ValueError("Each invoice quantity must use the explicit currency; no FX conversion inferred.")
            # Reuse only the coverage reconciliation from the mass primitive; do not
            # treat these surrogate values as currency or emit a converted metric.
            coverage = [dict(metric, value=0, unit="kg") for metric in selected]
            baseline(coverage, "kg", True, record.get("coverage_details"))
            with localcontext() as context:
                context.prec = 34
                charges = sum((number(metrics[line["metric_id"]]["value"]) for line in lines if line["kind"] == "charge"), number(0))
                credits = sum((number(metrics[line["metric_id"]]["value"]) for line in lines if line["kind"] == "credit"), number(0))
                inputs = [line["metric_id"] for line in lines]
                emit("charges", "Selected recorded waste charges", charges, record["currency"], inputs, "Sum selected charge lines as recorded", True)
                emit("credits", "Selected recorded waste credits", credits, record["currency"], inputs, "Sum selected credit lines as recorded", True)
                emit("net-cost", "Selected recorded net waste cost", charges-credits, record["currency"], inputs, "Selected recorded charges - selected recorded credits", True)
            if not record["coverage_complete"]:
                gap("WASTE_COST_COVERAGE_REQUIRED", "Selected invoice coverage is incomplete; net cost is a supported subtotal, not total organization waste cost.")
            result["diagnostics"].append({"code": "WASTE_COST_ACCOUNTING", "message": json.dumps(parameters, sort_keys=True)})
        elif skill == "identify-material-loss":
            record = parameters["balance_review"]
            review(record, ("material", "mass_basis", "measurement_boundary", "stock_timing", "nonoverlap_assessment", "coverage", "rationale"))
            if (record.get("opening_position") != "start_before_flows" or record.get("closing_position") != "end_after_flows"
                    or not isinstance(record.get("all_flows_accounted"), bool)):
                raise ValueError("Document opening/closing stock positions and explicit completeness assessment.")
            groups = {key: parameters[key] for key in ("receipt_ids", "product_ids", "loss_ids", "other_output_ids")}
            if any(not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) for ids in groups.values()):
                raise ValueError("Declare each receipt/output category as a list of mass quantity IDs.")
            empty = record.get("empty_categories_confirmed")
            if (not isinstance(empty, list) or any(not isinstance(k, str) for k in empty)
                    or len(empty) != len(set(empty)) or set(empty) != {k for k, ids in groups.items() if not ids}):
                raise ValueError("Explicitly confirm each empty flow category; omitted/unknown flows are not zero.")
            stocks = [parameters[k] for k in ("opening_stock_id", "closing_stock_id") if parameters[k] is not None]
            if any(not isinstance(key, str) for key in stocks): raise ValueError("Stock quantity ID or null for unavailable required.")
            selected = stocks + [key for ids in groups.values() for key in ids]
            if not selected or len(selected) != len(set(selected)):
                raise ValueError("Distinct stock/flow quantity IDs required; one mass cannot fill multiple balance roles.")
            # Baseline primitive enforces shared-document fragments and aggregate/component exclusions;
            # the summed quantity is discarded because stocks and flows have different roles.
            sum_mass(selected, dict(record, basis="material_balance_roles"), "material_balance_roles")
            with localcontext() as context:
                context.prec = 34
                amounts = {key: convert(resolve(key)["value"], metrics[key]["unit"], "kg")["value"] for key in selected}
                totals = {group: sum((amounts[key] for key in ids), number(0)) for group, ids in groups.items()}
                emit("measured-loss", "Documented selected material loss", totals["loss_ids"], "kg", selected,
                     "Sum of supplied mutually exclusive measured loss masses; empty loss category requires explicit confirmation")
                incomplete = not record["all_flows_accounted"] or len(stocks) != 2
                if incomplete:
                    gap("MATERIAL_BALANCE_DATA_REQUIRED", "Opening/closing stock or flow coverage is incomplete; measured loss subtotal does not establish total loss and residual is withheld.")
                else:
                    available = amounts[parameters["opening_stock_id"]] + totals["receipt_ids"]
                    residual = available - amounts[parameters["closing_stock_id"]] - totals["product_ids"] - totals["loss_ids"] - totals["other_output_ids"]
                    emit("residual", "Unexplained material balance residual", residual, "kg", selected,
                         "Opening stock + receipts - closing stock - products - measured losses - other accounted outputs")
                    if residual != 0:
                        gap("MATERIAL_BALANCE_UNRESOLVED", "Nonzero signed residual needs reconciliation; it is not automatically material loss, waste or zero.")
            result["diagnostics"].append({"code": "MATERIAL_BALANCE", "message": json.dumps(parameters, sort_keys=True)})
        else:
            prior = next((r for r in state["results"] if r["id"] == parameters["material_result_id"]), None)
            if prior is None or prior["skill"] != "analyze-material-consumption" or prior["status"] not in {"completed", "partial"} or len(prior["metrics"]) != 1:
                raise ValueError("Supported documented material consumption result required.")
            records = [json.loads(d["message"]) for d in prior["diagnostics"] if d["code"] == "MATERIAL_BASELINE"]
            if len(records) != 1: raise ValueError("One material consumption coverage record required.")
            record = records[0]
            total = sum_mass(record["metric_ids"], record["coverage_review"], "consumed_material")
            material = resolve(prior["metrics"][0]["id"])
            if (material["unit"] != "kg" or number(material["value"]) != total
                    or set(material["calculation"]["inputs"]) != set(record["metric_ids"])):
                raise ValueError("Material consumption total fails source revalidation.")
            denominator = resolve(parameters["denominator_id"], False)
            record = parameters["denominator_review"]
            review(record, ("definition", "unit", "rationale"))
            if record.get("metric_id") != denominator["id"] or record["unit"] != denominator["unit"] or denominator["unit"] == "UNKNOWN_UNIT":
                raise ValueError("Document the exact activity denominator and supported unit.")
            numerator = copy.deepcopy(material)
            numerator.update(value=convert(material["value"], material["unit"], "kg")["value"], unit="kg")
            value = kpi(numerator, denominator, "ratio")
            emit("intensity", "Selected material intensity", value["value"], value["unit"], [material["id"], denominator["id"]], "Selected consumed material kg / positive evidenced activity denominator")
    except (ValueError, KeyError, TypeError) as error:
        result["metrics"] = []
        gap("RESOURCE_DATA_REQUIRED", str(error))
    result["evidence_ids"] = sorted(refs)
    result["status"] = "blocked" if not result["metrics"] else ("partial" if result["data_gaps"] else "completed")
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"] == "open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    proposal = propose(state, result, "Compute selected mass analysis with explicit definitions and retained review obligations")
    if result["metrics"]:
        proposal["state"]["waste" if "waste" in skill or skill == "calculate-diversion-rate" else "materials"].append(ident)
        validate_state(proposal["state"])
    return {"result": result, "proposal": proposal}
