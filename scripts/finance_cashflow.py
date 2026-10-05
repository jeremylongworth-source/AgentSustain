"""Compose one explicitly timed annual net flow from sourced amounts."""
from datetime import date

from .data_tools import baseline, number


def cashflow(state, parameters, resolve, refs):
    review = parameters["cashflow_review"]
    analysis = parameters["analysis_review"]
    known = {e["id"]: e for e in state["evidence"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    fields = ("timing_basis", "nonoverlap_assessment", "constant_annual_assumption", "rationale")
    if (not isinstance(review, dict) or review.get("confirmed") is not True
            or any(not isinstance(review.get(f), str) or not review[f].strip() for f in fields)
            or not isinstance(review.get("coverage_complete"), bool)):
        raise ValueError("Explicit timing, coverage and sourced cash-flow composition review required.")
    evidence = review.get("evidence_ids")
    if (not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) for e in evidence)
            or not set(evidence) <= set(known)):
        raise ValueError("Known cash-flow review evidence required.")
    refs.update(evidence)
    year = review.get("year")
    valuation = date.fromisoformat(analysis["valuation_date"])
    if (isinstance(year, bool) or not isinstance(year, int) or not 0 <= year <= 60
            or analysis.get("timing") != "calendar_year_end" or (valuation.month, valuation.day) != (12, 31)
            or analysis["horizon"]["end"][-6:] != "-12-31"
            or valuation.year+year > date.fromisoformat(analysis["horizon"]["end"]).year):
        raise ValueError("Declare year 0..60 within a December 31 calendar-year-end horizon.")
    period = state["reporting_period"] if year == 0 else {
        "start": f"{valuation.year+year}-01-01", "end": f"{valuation.year+year}-12-31"}
    if year > 0:
        model = review.get("model_evidence_ids")
        if (not isinstance(model, list) or not model or any(not isinstance(e, str) for e in model)
                or not set(model) <= set(known)
                or any(known[e]["source"]["tier"] != 5 or not known[e]["assumption"] for e in model)):
            raise ValueError("Future cash-flow scheduling requires tier 5 model evidence and assumptions.")
        refs.update(model)
    lines = parameters["lines"]
    if not isinstance(lines, list) or not lines or any(not isinstance(line, dict) for line in lines):
        raise ValueError("Nonempty explicit line register required; absent annual amounts are not zero.")
    selected, line_ids, value = [], [], number(0)
    for line in lines:
        if (set(line) != {"id", "metric_id", "kind", "basis"}
                or not isinstance(line["id"], str) or not line["id"].strip()
                or line["kind"] not in {"inflow", "outflow", "signed"}
                or line["basis"] not in {"dated_amount", "constant_annual"}):
            raise ValueError("Declare unique line IDs, inflow/outflow/signed kind and supported amount basis.")
        annual = line["basis"] == "constant_annual"
        if annual and year == 0:
            raise ValueError("Annual operating amounts cannot be initial valuation cash flows.")
        metric = resolve(line["metric_id"], analysis["currency"]+("/year" if annual else ""), year > 0)
        if annual:
            if (review.get("annual_reference_period") != metric["period"]
                    or (date.fromisoformat(metric["period"]["end"])-date.fromisoformat(metric["period"]["start"])).days not in {364, 365}):
                raise ValueError("Constant annual scheduling requires the exact sourced full-year reference period.")
        elif metric["period"] != period:
            raise ValueError("Dated monetary amounts must match their selected cash-flow year.")
        amount = number(metric["value"])
        if line["kind"] != "signed" and amount < 0:
            raise ValueError("Inflow/outflow lines are nonnegative magnitudes; signed net amounts keep their sign.")
        value += amount * (-1 if line["kind"] == "outflow" else 1)
        selected.append(metric); line_ids.append(line["id"])
    keys = [m["id"] for m in selected]
    if len(keys) != len(set(keys)) or len(line_ids) != len(set(line_ids)):
        raise ValueError("Duplicate cash-flow quantities or line IDs must be reconciled.")
    for metric in selected:
        pending, seen = list(metric["calculation"]["inputs"]), set()
        while pending:
            key = pending.pop()
            if key in seen: continue
            seen.add(key)
            if key in metrics: pending.extend(metrics[key]["calculation"]["inputs"])
        if (set(keys)-{metric["id"]}) & seen:
            raise ValueError("Selected cash-flow aggregate/component lineage overlaps.")
    # Reconcile source fragments in a common internal context only; the source
    # periods above are checked before explicit model scheduling takes place.
    baseline([dict(m, value=0, unit="kg", period=period) for m in selected], "kg", True, review.get("coverage_details"))
    return value, analysis["currency"], keys, "Sum signed selected amounts at explicit calendar-year-end; constant annual model scheduled once in selected year", period, review["coverage_complete"]
