"""Reviewed baseline selection, KPI definitions and proposed target endpoints."""
import copy
from datetime import date
from decimal import localcontext
import json

from .contract_validation import validate_state
from .data_tools import UNITS, baseline, kpi, number, period, serialize
from .finance_projects import _review
from .state_proposal import propose


OPERATIONS = {
    "establish-baseline": {"metric_ids", "unit", "baseline_review", "result_id"},
    "define-kpis": {"definitions", "definition_review", "result_id"},
    "develop-target": {"definition_result_id", "kpi_id", "target", "target_review", "result_id"},
    "evaluate-target-feasibility": {"target_result_id", "scenarios", "feasibility_review", "result_id"},
}
CODE = {"establish-baseline": "STRATEGY_BASELINE", "define-kpis": "KPI_DEFINITIONS", "develop-target": "TARGET_PROPOSAL"}
CODE["evaluate-target-feasibility"] = "TARGET_FEASIBILITY"


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _record(result, code):
    records = [json.loads(d["message"]) for d in result["diagnostics"] if d["code"] == code]
    if len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError("One reproducible strategy record required.")
    return records[0]


def _metric(state, ident, refs, visited=None):
    visited = set() if visited is None else visited
    if ident in visited:
        return
    visited.add(ident)
    for evidence in state["evidence"]:
        if evidence["id"] == ident:
            refs.add(ident)
            if evidence["calculation"]:
                for ancestor in evidence["calculation"]["inputs"]:
                    _metric(state, ancestor, refs, visited)
            return evidence
    for owner in state["results"]:
        for metric in owner["metrics"]:
            if metric["id"] == ident:
                if owner["status"] in {"blocked", "invalid_input"}:
                    raise ValueError("Blocked source quantities cannot support a baseline or target.")
                if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in owner["diagnostics"]):
                    raise FactorRequired("Selected quantity ancestry has an unresolved emission factor.")
                if metric["value"] is None or not metric["evidence_ids"]:
                    raise ValueError("Known sourced metric required; unknown is not zero.")
                refs.update(metric["evidence_ids"])
                for ancestor in metric["calculation"]["inputs"]:
                    _metric(state, ancestor, refs, visited)
                return metric
    raise ValueError("Metric must resolve to the current state.")


class FactorRequired(ValueError):
    pass


def _selected(state, ident, refs):
    metric = _metric(state, ident, refs)
    if not isinstance(metric, dict) or "value" not in metric:
        raise ValueError("Select a metric, not a raw evidence record.")
    number(metric["value"])
    return metric


def _reviewed(state, review, refs, fields):
    refs.update(_review(review, {e["id"] for e in state["evidence"]}, ("reviewer_role", "rationale", *fields)))
    if review.get("boundary_id") != state["organizational_boundary"]["id"]:
        raise ValueError("Reviewed boundary must match the supplied organizational boundary.")


def _fit(state, review, metrics, refs):
    contexts = review.get("metric_contexts")
    if not isinstance(contexts, dict) or set(contexts) != {m["id"] for m in metrics}:
        raise ValueError("Explicit source-fit review for each selected metric only required.")
    for metric in metrics:
        record = contexts[metric["id"]]
        refs.update(_review(record, {e["id"] for e in state["evidence"]}, ("rationale", "scope")))
        if record["scope"] != review["scope"] or set(record["evidence_ids"]) != set(metric["evidence_ids"]):
            raise ValueError("Metric source-fit review must reference its actual evidence and selected scope.")
        if "accounting_basis" in review and record.get("accounting_basis") != review["accounting_basis"]:
            raise ValueError("Each baseline quantity requires the same reviewed gross/accounting basis, including applicable GWP and scope choices.")


def _quantity(result, suffix, name, value, unit, when, boundary, refs, inputs, formula, assumption, conversions=(), uncertainty_description=None):
    if assumption not in result["assumptions"]:
        result["assumptions"].append(assumption)
    metric = {"id": result["id"] + "-" + suffix, "name": name, "value": serialize(number(value)), "unit": unit,
        "period": copy.deepcopy(when), "boundary_id": boundary, "evidence_ids": sorted(refs),
        "method": {"name": "Reviewed strategy arithmetic", "version": "0.1.0", "source": "repository:docs/strategy-contract.md"},
        "assumption": assumption,
        "uncertainty": {"kind": "unquantified", "description": uncertainty_description or "Source measurement, coverage and future-delivery uncertainty retained; endpoint is a proposed objective, not a forecast or confidence bound.", "value": None, "unit": None},
        "calculation": {"formula": formula, "inputs": list(dict.fromkeys(inputs)), "conversions": list(conversions), "rounding": "Decimal precision 34; no display rounding"}}
    result["metrics"].append(metric)
    return metric


def _reproduce(state, ident, skill, refs):
    owner = next((r for r in state["results"] if r["id"] == ident and r["skill"] == skill), None)
    if owner is None or owner["status"] in {"blocked", "invalid_input"}:
        raise ValueError("Current reproducible strategy dependency required.")
    inputs = _record(owner, "STRATEGY_INPUTS")
    checked, report = _execute(state, skill, inputs)
    if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in checked["diagnostics"]):
        raise FactorRequired("Selected strategy dependency has an unresolved emission factor.")
    if checked["status"] == "blocked" or report != _record(owner, CODE[skill]) or checked["metrics"] != owner["metrics"]:
        raise ValueError("Strategy dependency changed or no longer reproduces against current source state.")
    refs.update(owner["evidence_ids"])
    return owner, report


def _execute(state, skill, parameters):
    result = {"id": parameters["result_id"], "skill": skill, "contract_version": "0.1.0", "status": "completed",
        "review_states": ["ANALYTICAL"], "review_requirements": copy.deepcopy(state["review_requirements"]),
        "metrics": [], "evidence_ids": [], "assumptions": list(state["assumptions"]),
        "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}
    refs = set()
    report = None
    def gap(message, code="STRATEGY_DATA_REQUIRED"):
        result["data_gaps"].append({"id": result["id"] + "-gap-" + str(len(result["data_gaps"])), "field": "strategy_basis",
            "reason": message, "impact": "Baseline, KPI or target remains conditional; no commitment or feasibility established.",
            "remedy": "Obtain scoped source evidence and documented review of the missing strategy basis."})
        result["diagnostics"].append({"code": code, "message": message})
    try:
        with localcontext() as context:
            context.prec = 34
            if skill == "evaluate-target-feasibility":
                from .strategy_feasibility import evaluate
                report = evaluate(state, parameters, refs, result, gap)
            elif skill == "establish-baseline":
                ids = parameters["metric_ids"]
                if not isinstance(ids, list) or not ids or any(not _text(i) for i in ids) or len(ids) != len(set(ids)):
                    raise ValueError("Select distinct metric IDs; overlapping quantities require source reconciliation.")
                metrics = [_selected(state, i, refs) for i in ids]
                review = parameters["baseline_review"]
                _reviewed(state, review, refs, ("scope", "selection_rationale", "recalculation_policy", "accounting_basis"))
                _fit(state, review, metrics, refs)
                if not isinstance(review.get("coverage_complete"), bool) or not isinstance(review.get("exclusions"), list) or any(not _text(x) for x in review["exclusions"]):
                    raise ValueError("Declare selected-scope coverage and explicit exclusions.")
                if review.get("period") != metrics[0]["period"] or any(number(m["value"]) < 0 for m in metrics):
                    raise ValueError("Baseline needs matched reviewed periods and nonnegative gross quantities.")
                # Primitive conversion never chooses scope or determines invoice overlap.
                calculated = baseline(metrics, parameters["unit"], review.get("nonoverlap_confirmed"), review.get("coverage_details"))
                if not review["coverage_complete"]:
                    gap("Selected baseline coverage is incomplete; do not treat its subtotal as the complete organization.")
                assumption = "Selected gross baseline only; source-fit, nonoverlap and accounting basis are supplied substantive review, not source authentication."
                total = _quantity(result, "baseline", "Selected sustainability baseline", calculated["value"], calculated["unit"],
                    metrics[0]["period"], metrics[0]["boundary_id"], refs, ids, calculated["formula"], assumption,
                    [json.dumps(c, default=serialize, sort_keys=True) for c in calculated["conversions"]])
                report = {"baseline_metric_id": total["id"], "source_metrics": metrics, "baseline_review": review,
                    "selected_scope": review["scope"], "coverage_complete": review["coverage_complete"], "organization_coverage_verified": False,
                    "restatement_applied": False, "source_authentication": "Supplied review is not independent authentication."}
            elif skill == "define-kpis":
                review = parameters["definition_review"]
                _reviewed(state, review, refs, ("scope", "monitoring_basis"))
                definitions = parameters["definitions"]
                if not isinstance(definitions, list) or not definitions:
                    raise ValueError("Explicit nonempty KPI definitions required.")
                seen = set(); rows = []
                for item in definitions:
                    fields = {"id", "name", "kind", "baseline_result_id", "denominator_metric_id", "denominator_review", "owner", "frequency", "definition", "desired_direction"}
                    if (not isinstance(item, dict) or set(item) != fields or any(not _text(item[f]) for f in ("id", "name", "owner", "frequency", "definition"))
                            or item["id"] in seen or item["kind"] not in {"absolute", "intensity"} or item["desired_direction"] != "decrease"):
                        raise ValueError("Distinct explicit owned absolute/intensity definitions with decrease direction required.")
                    seen.add(item["id"])
                    owner, base = _reproduce(state, item["baseline_result_id"], "establish-baseline", refs)
                    if base["selected_scope"] != review["scope"]:
                        raise ValueError("Definition scope differs from selected baseline scope.")
                    numerator = _selected(state, base["baseline_metric_id"], refs)
                    denominator = None; unit = numerator["unit"]
                    if item["kind"] == "absolute":
                        if item["denominator_metric_id"] is not None or item["denominator_review"] is not None:
                            raise ValueError("Absolute KPI has no intensity denominator.")
                    else:
                        denominator = _selected(state, item["denominator_metric_id"], refs)
                        fit = item["denominator_review"]
                        _reviewed(state, fit, refs, ("scope", "service_definition", "comparability_policy"))
                        _fit(state, fit, [denominator], refs)
                        if fit["scope"] != review["scope"] or denominator["unit"] not in UNITS or UNITS[denominator["unit"]][0] == "co2e":
                            raise ValueError("Matched physical service denominator required; no currency or emissions denominator inferred.")
                        computed = kpi(numerator, denominator, "ratio")
                        unit = computed["unit"]
                    rows.append({"definition": item, "unit": unit, "baseline_metric": numerator, "denominator_metric": denominator,
                        "baseline_scope_review": base["baseline_review"]})
                    if not base["coverage_complete"]:
                        gap("KPI " + item["id"] + " retains incomplete selected-baseline coverage.")
                report = {"definitions": rows, "definition_review": review, "monitoring_started": False, "performance_verified": False}
            else:
                owner, definitions = _reproduce(state, parameters["definition_result_id"], "define-kpis", refs)
                row = next((r for r in definitions["definitions"] if r["definition"]["id"] == parameters["kpi_id"]), None)
                if row is None:
                    raise ValueError("Target KPI must resolve to the reproduced definition register.")
                review = parameters["target_review"]
                _reviewed(state, review, refs, ("scope", "ambition_basis", "period_comparability", "growth_assumptions", "double_counting_policy", "recalculation_policy"))
                if review["scope"] != row["baseline_scope_review"]["scope"] or review["recalculation_policy"] != row["baseline_scope_review"]["recalculation_policy"]:
                    raise ValueError("Target scope and baseline recalculation policy must match the reviewed baseline.")
                if review.get("offset_policy") != "excluded":
                    raise ValueError("Initial target method uses gross quantities without credits, removals or offsets.")
                target = parameters["target"]
                if (not isinstance(target, dict) or set(target) != {"id", "kind", "level_type", "value", "unit", "period", "owner"}
                        or not _text(target["id"]) or not _text(target["owner"]) or target["kind"] != row["definition"]["kind"]):
                    raise ValueError("Explicit target ID, kind, endpoint period and accountable owner required.")
                when = period(target["period"]); numerator = row["baseline_metric"]; denominator = row["denominator_metric"]
                if when["start"] <= numerator["period"]["end"]:
                    raise ValueError("Target commitment period must follow the baseline; no silent annualization.")
                before = numerator["period"]
                def days(window):
                    return (date.fromisoformat(window["end"]) - date.fromisoformat(window["start"])).days + 1
                calendar_match = (when["start"][5:] == before["start"][5:] and when["end"][5:] == before["end"][5:]
                    and int(when["end"][:4])-int(when["start"][:4]) == int(before["end"][:4])-int(before["start"][:4]))
                if not calendar_match and days(when) != days(before):
                    raise ValueError("Initial endpoint method requires comparable calendar windows or equal duration; multi-year averaging is not inferred.")
                prior = number(numerator["value"])
                inputs = [numerator["id"]]
                if denominator:
                    prior = kpi(numerator, denominator, "ratio")["value"]; inputs.append(denominator["id"])
                value = number(target["value"])
                if target["level_type"] == "reduction_percent":
                    if target["unit"] != "%" or prior <= 0 or not 0 <= value <= 100:
                        raise ValueError("Percentage reduction requires a positive baseline and explicit 0–100 percent.")
                    endpoint = prior * (1 - value / 100); formula = "baseline * (1 - supplied reduction_percent / 100)"
                elif target["level_type"] == "endpoint":
                    if target["unit"] != row["unit"] or not 0 <= value <= prior:
                        raise ValueError("Reduction endpoint requires the exact KPI unit and a nonnegative level no greater than baseline.")
                    endpoint = value; formula = "supplied proposed endpoint; baseline used for reduction comparison"
                else:
                    raise ValueError("Declare endpoint or reduction_percent; no default target level.")
                assumption = "Proposed gross selected-scope objective, not a forecast, approved commitment, feasible delivery or validated science-based target."
                metric = _quantity(result, "target", "Proposed " + row["definition"]["name"] + " endpoint", endpoint, row["unit"], when,
                    numerator["boundary_id"], refs, inputs + review["evidence_ids"], formula, assumption)
                result["review_requirements"].append({"id": result["id"] + "-target-review", "state": "PROFESSIONAL_REVIEW_REQUIRED",
                    "reason": "Review source fitness, target ambition, growth, comparable commitment periods and delivery feasibility before adoption or claims.",
                    "scope": review["scope"], "reviewer_role": "Sustainability strategy reviewer and accountable decision owner", "status": "open", "resolution": None})
                if not row["baseline_scope_review"]["coverage_complete"]:
                    gap("Target retains incomplete selected-baseline coverage; no full-organization reduction claim.")
                report = {"target": target, "target_review": review, "definition": row, "baseline_value": serialize(prior),
                    "baseline_unit": row["unit"], "endpoint_metric_id": metric["id"], "proposed_reduction": serialize(prior-endpoint),
                    "baseline_absolute_quantity": numerator, "absolute_future_quantity": None,
                    "intensity_warning": "Lower intensity can coexist with higher absolute impact; no future activity or absolute outcome inferred." if denominator else None,
                    "trajectory": None, "feasibility": None, "target_adopted": False, "science_based_validated": False,
                    "net_zero_validated": False, "public_claim_authorized": False, "implementation_authorized": False}
            result["diagnostics"].append({"code": CODE[skill], "message": json.dumps(report, sort_keys=True)})
            result["status"] = "partial" if result["data_gaps"] else "completed"
    except (ValueError, TypeError, KeyError) as error:
        result["metrics"] = []
        gap(str(error), "EMISSION_FACTOR_REQUIRED" if isinstance(error, FactorRequired) else "STRATEGY_DATA_REQUIRED")
        result["status"] = "blocked"
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code": "STRATEGY_INPUTS", "message": json.dumps(parameters, sort_keys=True)})
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"] == "open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    return result, report


def run_strategy(state, skill, parameters):
    validate_state(state)
    if skill not in OPERATIONS or not isinstance(parameters, dict) or set(parameters) != OPERATIONS[skill] or not _text(parameters["result_id"]):
        raise ValueError("Supported strategy operation with exact parameters and fresh result ID required.")
    result, _ = _execute(state, skill, parameters)
    return {"result": result, "proposal": propose(state, result, "Propose reviewed baseline, KPI definition or target without adoption or claims")}
