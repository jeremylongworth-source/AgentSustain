"""Sourced initial-investment and comparable projected annual-cost composition."""
from datetime import date

from .data_tools import baseline, number
from .finance_cashflow import cashflow


OPERATIONS = {
    "build-sustainability-business-case": {"lines", "cashflow_review", "analysis_review", "result_id"},
    "calculate-sustainability-project-cost": {"lines", "composition_review", "analysis_review", "result_id"},
    "calculate-operating-savings": {"baseline_lines", "scenario_lines", "comparison_review", "analysis_review", "result_id"},
}


def compose(state, skill, parameters, resolve, refs):
    if skill == "build-sustainability-business-case":
        return cashflow(state, parameters, resolve, refs)
    known = {e["id"]: e for e in state["evidence"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    currency = parameters["analysis_review"]["currency"]

    def review(record, fields):
        evidence = record.get("evidence_ids") if isinstance(record, dict) else None
        if (not isinstance(record, dict) or record.get("confirmed") is not True or not isinstance(evidence, list)
                or not evidence or any(not isinstance(e, str) for e in evidence) or not set(evidence) <= set(known)
                or any(not isinstance(record.get(f), str) or not record[f].strip() for f in fields)
                or not isinstance(record.get("coverage_complete"), bool)):
            raise ValueError("Explicit sourced composition, nonoverlap and coverage review required.")
        refs.update(evidence)

    def lines_total(lines, unit, period, categories, coverage):
        if not isinstance(lines, list) or not lines or any(not isinstance(line, dict) for line in lines):
            raise ValueError("Nonempty monetary-line register required; unknown omitted costs are not zero.")
        ids = [line.get("id") for line in lines]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Unique monetary-line IDs required.")
        selected, total = [], number(0)
        for line in lines:
            if (set(line) != {"id", "metric_id", "kind", "category"} or line["kind"] not in {"cost", "credit"}
                    or line["category"] not in categories):
                raise ValueError("Declare cost/credit sign and applicable monetary-line category.")
            metric = resolve(line["metric_id"], unit)
            if metric["period"] != period or number(metric["value"]) < 0:
                raise ValueError("Each recorded line must be a nonnegative magnitude in the explicit composition period.")
            selected.append(metric)
            total += number(metric["value"]) * (1 if line["kind"] == "cost" else -1)
        keys = [metric["id"] for metric in selected]
        if len(keys) != len(set(keys)): raise ValueError("A monetary quantity cannot fill two selected line roles.")
        for metric in selected:
            pending, seen = list(metric["calculation"]["inputs"]), set()
            while pending:
                key = pending.pop()
                if key in seen: continue
                seen.add(key)
                if key in metrics: pending.extend(metrics[key]["calculation"]["inputs"])
            if (set(keys)-{metric["id"]}) & seen: raise ValueError("Total/component financial lineage overlaps; reconcile before summing.")
        # Reuse the existing source-fragment reconciliation only. These internal
        # zero-mass surrogates are discarded; monetary values are never converted.
        baseline([dict(metric, value=0, unit="kg") for metric in selected], "kg", True, coverage)
        return total, keys

    if skill == "calculate-sustainability-project-cost":
        record = parameters["composition_review"]
        review(record, ("basis", "measurement_boundary", "nonoverlap_assessment", "allocation_basis", "tax_treatment", "rationale"))
        if record["basis"] != "initial_net_investment":
            raise ValueError("Initial net-investment composition cannot mix lifetime or recurring costs.")
        value, inputs = lines_total(parameters["lines"], currency, state["reporting_period"],
            {"capital", "installation", "fees", "initial_tax", "contingency", "capital_incentive"}, record.get("coverage_details"))
        for line in parameters["lines"]:
            if (line["kind"] == "credit") != (line["category"] == "capital_incentive"):
                raise ValueError("Initial credits must be explicitly evidenced capital incentives; do not deduct operating benefits twice.")
        return value, currency, inputs, "Sum selected initial investment costs - selected capital incentive credits", state["reporting_period"], record["coverage_complete"]
    record = parameters["comparison_review"]
    review(record, ("comparison_basis", "baseline_conditions", "scenario_conditions", "adjustment_method", "nonoverlap_assessment", "fixed_cost_treatment", "rationale"))
    if record.get("analysis_type") != "projection" or record["comparison_basis"] not in {"same_service", "adjusted_baseline"}:
        raise ValueError("Declare a supported projected same-service or documented adjusted-baseline operating comparison.")
    period = record.get("annual_period")
    if (not isinstance(period, dict) or set(period) != {"start", "end"}
            or (date.fromisoformat(period["end"])-date.fromisoformat(period["start"])).days not in {364, 365}):
        raise ValueError("Supply an explicit full-year cost reference period; partial costs are not annualized.")
    model = record.get("model_evidence_ids")
    if (not isinstance(model, list) or not model or any(not isinstance(i, str) for i in model)
            or not set(model) <= set(known) or any(known[i]["source"]["tier"] != 5 or not known[i]["assumption"] for i in model)):
        raise ValueError("Projected operating comparison requires identified tier 5 model evidence with assumptions.")
    refs.update(model)
    categories = {"energy", "water", "material", "waste", "maintenance", "labor", "fixed", "other", "rebate"}
    for line in parameters["baseline_lines"] + parameters["scenario_lines"]:
        if not isinstance(line, dict) or (line.get("kind") == "credit") != (line.get("category") == "rebate"):
            raise ValueError("Operating credits must be declared rebates; costs cannot masquerade as savings.")
    before, before_ids = lines_total(parameters["baseline_lines"], currency+"/year", period, categories, record.get("baseline_coverage_details"))
    after, after_ids = lines_total(parameters["scenario_lines"], currency+"/year", period, categories, record.get("scenario_coverage_details"))
    return before-after, currency+"/year", list(dict.fromkeys(before_ids+after_ids)), "Comparable selected baseline annual net cost - selected projected scenario annual net cost", period, record["coverage_complete"]
