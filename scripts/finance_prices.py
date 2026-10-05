"""Explicit annual variable-unit price paths; no inferred tariffs or obligations."""
from datetime import date

from .data_tools import number


OPERATIONS = {skill: {"path", "scenario_review", "analysis_review", "result_id"} for skill in (
    "model-energy-price-scenario", "model-resource-cost-scenario", "model-carbon-price-scenario")}


def price_path(state, skill, parameters, resolve, refs):
    record, analysis = parameters["scenario_review"], parameters["analysis_review"]
    known = {e["id"]: e for e in state["evidence"]}
    fields = ("quantity_unit", "quantity_basis", "service_boundary", "nonoverlap_assessment",
              "excluded_charges", "escalation_basis", "rationale")
    if (not isinstance(record, dict) or record.get("confirmed") is not True
            or not isinstance(record.get("coverage_complete"), bool)
            or any(not isinstance(record.get(f), str) or not record[f].strip() for f in fields)):
        raise ValueError("Explicit sourced price-path, physical/service basis and coverage review required.")
    for field in ("evidence_ids", "model_evidence_ids"):
        evidence = record.get(field)
        if (not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) for e in evidence)
                or not set(evidence) <= set(known)):
            raise ValueError("Known scenario and model evidence required.")
        if field == "model_evidence_ids" and any(known[e]["source"]["tier"] != 5 or not known[e]["assumption"] for e in evidence):
            raise ValueError("Price paths require explicit tier 5 model evidence with assumptions.")
        refs.update(evidence)
    allowed = {"model-energy-price-scenario": {"kWh", "MWh", "MJ", "GJ"},
               "model-resource-cost-scenario": {"kg", "t", "L", "m3", "count"},
               "model-carbon-price-scenario": {"kg CO2e", "t CO2e"}}
    unit = record["quantity_unit"]
    if unit not in allowed[skill]:
        raise ValueError("Explicit supported physical quantity/rate denominator required; no conversion inferred.")
    if skill == "model-carbon-price-scenario":
        if (record.get("exposure_basis") not in {"internal_shadow", "regulatory_payment", "contractual_charge"}
                or any(not isinstance(record.get(f), str) or not record[f].strip()
                       for f in ("applicability_basis", "eligible_coverage", "exclusions", "reviewer_role"))):
            raise ValueError("Separate shadow pricing from sourced payment applicability, eligible coverage and exclusions.")
    valuation = date.fromisoformat(analysis["valuation_date"])
    end = date.fromisoformat(analysis["horizon"]["end"])
    years = end.year-valuation.year
    path = parameters["path"]
    if (analysis.get("timing") != "calendar_year_end" or (valuation.month, valuation.day) != (12, 31)
            or (end.month, end.day) != (12, 31) or not 1 <= years <= 60
            or not isinstance(path, list) or len(path) != years
            or any(not isinstance(line, dict) or set(line) != {"year", "quantity_id", "price_id", "price_context"}
                   or isinstance(line["year"], bool) or not isinstance(line["year"], int) for line in path)
            or [line["year"] for line in path] != list(range(1, years+1))):
        raise ValueError("Supply one explicit price/quantity pair for every future calendar year of the 1..60 year horizon.")
    entries, selected = [], []
    for line in path:
        year = line["year"]
        period = {"start": f"{valuation.year+year}-01-01", "end": f"{valuation.year+year}-12-31"}
        context = line["price_context"]
        if (not isinstance(context, dict) or context.get("charge_type") != "variable_unit"
                or context.get("effective_period") != period
                or context.get("dollar_basis") != analysis["dollar_basis"] or context.get("tax_basis") != analysis["tax_basis"]
                or any(not isinstance(context.get(f), str) or not context[f].strip() for f in ("rate_version", "service", "applicability"))):
            raise ValueError("Reviewed dated variable-unit price context must match economic basis; fixed/demand charges need separate models.")
        quantity = resolve(line["quantity_id"], unit, True)
        price = resolve(line["price_id"], analysis["currency"]+"/"+unit)
        if (quantity["period"] != period or price["period"] != period
                or not quantity["evidence_ids"] or not price["evidence_ids"]
                or number(quantity["value"]) < 0 or number(price["value"]) < 0):
            raise ValueError("Nonnegative sourced quantity and unit price must match their explicit annual period.")
        selected.extend((quantity["id"], price["id"]))
        entries.append((parameters["result_id"]+f"-year-{year}", number(quantity["value"])*number(price["value"]),
            analysis["currency"], [quantity["id"], price["id"]],
            "Supplied eligible physical quantity * supplied variable unit price for explicit annual period", period))
    if len(selected) != len(set(selected)):
        raise ValueError("Distinct annual quantity/price metrics required; source paths cannot be silently repeated.")
    return entries, record["coverage_complete"]
