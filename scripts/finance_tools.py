"""Conditional payback, horizon ROI and annual end-of-year project NPV."""
import copy
import calendar
from datetime import date
from decimal import localcontext
import json
import re

from .contract_validation import validate_state
from .data_tools import number, serialize
from .state_proposal import propose
from .finance_composition import OPERATIONS as COMPOSITION_OPERATIONS, compose
from .irr_tools import irr_roots
from .finance_prices import OPERATIONS as PRICE_OPERATIONS, price_path
from .finance_abatement import abatement_cost
from .finance_projects import compare_projects, rank_projects
from .finance_business_case import PARAMETERS as CASE_PARAMETERS, business_case


OPERATIONS = {"calculate-simple-payback": {"investment_id", "annual_savings_id", "analysis_review", "result_id"},
              "calculate-roi": {"investment_id", "net_benefit_id", "analysis_review", "result_id"},
              "calculate-npv": {"cashflows", "discount_rate_id", "analysis_review", "result_id"}}
OPERATIONS["calculate-irr"] = {"cashflows", "root_search", "analysis_review", "result_id"}
OPERATIONS.update(COMPOSITION_OPERATIONS)
OPERATIONS.update(PRICE_OPERATIONS)
OPERATIONS["calculate-marginal-abatement-cost"] = {"incremental_cost_id", "baseline_emissions_id", "scenario_emissions_id", "abatement_review", "analysis_review", "result_id"}
OPERATIONS["compare-sustainability-projects"] = {"projects", "criteria", "comparison_review", "analysis_review", "result_id"}
OPERATIONS["rank-sustainability-investments"] = {"comparison_result_id", "decision_review", "analysis_review", "result_id"}


def run_finance(state, skill, parameters):
    validate_state(state)
    full_case = skill == "build-sustainability-business-case" and isinstance(parameters,dict) and set(parameters) == CASE_PARAMETERS
    if skill not in OPERATIONS or not isinstance(parameters, dict) or (set(parameters) != OPERATIONS[skill] and not full_case):
        raise ValueError("Supported finance operation with exact parameters required.")
    ident = parameters["result_id"]
    if not isinstance(ident, str) or not ident.strip(): raise ValueError("Result ID required.")
    result = {"id": ident, "skill": skill, "contract_version": "0.1.0", "status": "completed", "review_states": ["ANALYTICAL"],
              "review_requirements": copy.deepcopy(state["review_requirements"]), "metrics": [], "evidence_ids": [],
              "assumptions": list(state["assumptions"]), "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}
    known = {e["id"]: e for e in state["evidence"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    metric_results = {m["id"]: r for r in state["results"] for m in r["metrics"]}
    refs = set()

    def resolve(key, unit, projected=False):
        metric = metrics.get(key)
        if (metric is None or metric["value"] is None or metric["unit"] != unit
                or metric["boundary_id"] != state["organizational_boundary"]["id"]):
            raise ValueError("Resolved finite quantity with the declared unit/boundary required; no currency conversion inferred.")
        number(metric["value"]); refs.update(metric["evidence_ids"])
        pending, seen = [key], set()
        while pending:
            source = pending.pop()
            if source in seen or source not in metrics: continue
            seen.add(source)
            if any(d["code"] == "NONCASH_SHADOW_PRICE" for d in metric_results[source]["diagnostics"]):
                raise ValueError("Internal shadow-price exposure cannot be used as a payment, cash flow or investment return.")
            pending.extend(metrics[source]["calculation"]["inputs"])
        if projected and (not metric["assumption"] or not any(known[e]["source"]["tier"] == 5 for e in metric["evidence_ids"])):
            raise ValueError("Future/recurring benefits require explicit model assumptions and tier 5 evidence.")
        return metric

    def gap(code, reason):
        result["data_gaps"].append({"id": ident+"-gap-"+str(len(result["data_gaps"])), "field": "financial_analysis", "reason": reason,
            "impact": "The requested financial measure is unsupported.", "remedy": "Supply sourced monetary quantities, timing, model definitions and economic assumptions."})
        result["diagnostics"].append({"code": code, "message": reason})

    try:
        review = parameters["analysis_review"]
        fields = ("currency", "definition", "rationale", "model_assumption", "valuation_date", "dollar_basis", "tax_basis")
        evidence = review.get("evidence_ids") if isinstance(review, dict) else None
        if (not isinstance(review, dict) or review.get("confirmed") is not True or not isinstance(evidence, list) or not evidence
                or any(not isinstance(e, str) for e in evidence) or not set(evidence) <= set(known)
                or any(not isinstance(review.get(f), str) or not review[f].strip() for f in fields)
                or not re.fullmatch(r"[A-Z]{3}", review["currency"]) or review["dollar_basis"] not in {"real", "nominal"}
                or review["tax_basis"] not in {"pre_tax", "after_tax"}):
            raise ValueError("Explicit sourced financial definition, currency, dollar/tax basis and model review required.")
        refs.update(evidence)
        valuation = date.fromisoformat(review["valuation_date"])
        if not date.fromisoformat(state["reporting_period"]["start"]) <= valuation <= date.fromisoformat(state["reporting_period"]["end"]):
            raise ValueError("Valuation date must lie within the analysis reporting period.")
        horizon = review.get("horizon")
        if not isinstance(horizon, dict) or set(horizon) != {"start", "end"} or horizon["start"] != valuation.isoformat() or date.fromisoformat(horizon["end"]) <= valuation:
            raise ValueError("Explicit future analysis horizon beginning on valuation date required.")
        currency = review["currency"]
        inputs = []
        entries = None
        output_period = horizon
        with localcontext() as context:
            context.prec = 34
            if full_case:
                entries, report, complete = business_case(state,parameters,resolve,refs,run_finance)
                result["review_requirements"].append({"id":ident+"-case-review","state":"PROFESSIONAL_REVIEW_REQUIRED",
                    "reason":"Review business-case financial/physical assumptions, sensitivity, implementation feasibility and decision/claims boundaries.",
                    "scope":"Business-case decision pack","reviewer_role":parameters["case_review"]["reviewer_role"],"status":"open","resolution":None})
                if not complete: gap("FINANCIAL_COVERAGE_REQUIRED","Business-case coverage is incomplete; retained outcomes are conditional alternatives.")
                report["review_requirements"] = copy.deepcopy(result["review_requirements"])
                report["data_gaps"] = copy.deepcopy(result["data_gaps"])
                result["diagnostics"].append({"code":"SUSTAINABILITY_BUSINESS_CASE","message":json.dumps(report,sort_keys=True)})
            elif skill in {"compare-sustainability-projects", "rank-sustainability-investments"}:
                if skill == "compare-sustainability-projects":
                    entries, report, complete = compare_projects(state,parameters,resolve,refs,run_finance,OPERATIONS)
                    code = "PROJECT_COMPARISON"
                else:
                    entries, report, complete = rank_projects(state,parameters,resolve,refs,run_finance)
                    code = "INVESTMENT_RANKING"
                result["diagnostics"].append({"code": code, "message": json.dumps(report, sort_keys=True)})
                if not complete: gap("FINANCIAL_COVERAGE_REQUIRED", "Project comparison coverage is incomplete; outcomes/ranks remain conditional.")
                if not entries: raise ValueError("No eligible alternatives remain under the supplied criteria, ownership, readiness and dependencies.")
            elif skill == "calculate-marginal-abatement-cost":
                entries, complete = abatement_cost(state,parameters,resolve,refs)
                if not complete:
                    gap("FINANCIAL_COVERAGE_REQUIRED", "Cost-per-abatement coverage is incomplete; this is a conditional selected-project ratio.")
                result["review_requirements"].append({"id": ident+"-abatement-review", "state": "PROFESSIONAL_REVIEW_REQUIRED",
                    "reason": "Review incremental cost completeness, baseline/scenario applicability, physical reduction and exclusions.",
                    "scope": "Project cost per abatement", "reviewer_role": parameters["abatement_review"]["reviewer_role"], "status": "open", "resolution": None})
            elif skill in PRICE_OPERATIONS:
                entries, complete = price_path(state,skill,parameters,resolve,refs)
                if not complete:
                    gap("FINANCIAL_COVERAGE_REQUIRED", "Selected variable-unit price coverage is incomplete; results are conditional exposure subtotals.")
                if skill == "model-carbon-price-scenario":
                    record = parameters["scenario_review"]
                    result["review_requirements"].append({"id": ident+"-applicability-review", "state": "PROFESSIONAL_REVIEW_REQUIRED",
                        "reason": "Review carbon-price applicability, eligible coverage, exclusions and shadow/payment interpretation.",
                        "scope": "Carbon-price scenario", "reviewer_role": record["reviewer_role"], "status": "open", "resolution": None})
                    if record["exposure_basis"] == "internal_shadow":
                        result["diagnostics"].append({"code": "NONCASH_SHADOW_PRICE", "message": "Internal shadow-price exposure is a noncash analytical value, not a payment obligation or cash saving."})
            elif skill in COMPOSITION_OPERATIONS:
                value,unit,inputs,formula,output_period,complete = compose(state,skill,parameters,resolve,refs)
                if not complete:
                    gap("FINANCIAL_COVERAGE_REQUIRED", "Selected cost/benefit coverage is incomplete; composition is a supported subtotal, not complete project economics.")
            elif skill in {"calculate-npv", "calculate-irr"}:
                flows = parameters["cashflows"]
                if (not isinstance(flows, list) or len(flows) < 2 or any(not isinstance(f, dict) or set(f) != {"year", "metric_id"}
                        or isinstance(f["year"], bool) or not isinstance(f["year"], int) for f in flows)
                        or [f["year"] for f in flows] != list(range(len(flows))) or review.get("timing") != "calendar_year_end"
                        or (valuation.month, valuation.day) != (12, 31)):
                    raise ValueError("Supply year 0 through N once, with Dec 31 valuation and calendar-year-end cash-flow timing.")
                if horizon["end"] != f"{valuation.year+len(flows)-1}-12-31":
                    raise ValueError("Horizon must match the complete annual cash-flow series.")
                if skill == "calculate-npv":
                    rate = resolve(parameters["discount_rate_id"], "%")
                    if rate["period"] != state["reporting_period"] or review.get("discount_basis") != review["dollar_basis"]:
                        raise ValueError("Discount-rate context and real/nominal basis must match the reviewed cash flows.")
                    discount = number(rate["value"])/100
                    if discount <= -1: raise ValueError("Discount rate must exceed -100 percent.")
                selected, value = [], number(0)
                for flow in flows:
                    metric = resolve(flow["metric_id"], currency, flow["year"] > 0)
                    expected = state["reporting_period"] if flow["year"] == 0 else {"start": f"{valuation.year+flow['year']}-01-01", "end": f"{valuation.year+flow['year']}-12-31"}
                    if metric["period"] != expected: raise ValueError("Cash-flow metric period must match its explicit year.")
                    selected.append(metric); inputs.append(metric["id"])
                    if skill == "calculate-npv": value += number(metric["value"])/(1+discount)**flow["year"]
                if len(inputs) != len(set(inputs)): raise ValueError("Cash-flow quantities cannot be reused across years.")
                # Each year is one already-composed net flow, not invoice lines.
                # Reusing an aggregate and one of its selected components would
                # nevertheless count the same financial amount twice.
                for metric in selected:
                    if not metric["evidence_ids"]: raise ValueError("Cash-flow source evidence required.")
                    pending, seen = list(metric["calculation"]["inputs"]), set()
                    while pending:
                        key = pending.pop()
                        if key in seen: continue
                        seen.add(key)
                        if key in metrics: pending.extend(metrics[key]["calculation"]["inputs"])
                    if (set(inputs)-{metric["id"]}) & seen:
                        raise ValueError("Cash-flow aggregate/component overlap must be reconciled before discounting.")
                if skill == "calculate-irr":
                    report, value = irr_roots([m["value"] for m in selected], parameters["root_search"])
                    result["diagnostics"].append({"code": report["code"], "message": json.dumps(report, sort_keys=True)})
                    if value is None: raise ValueError(report["message"])
                    formula, unit = "Verified rate solving sum(CF_t / (1+r)^t)=0; unique positive-x root for one-sign-change annual flows", "%"
                else:
                    inputs.append(rate["id"])
                    if len(inputs) != len(set(inputs)): raise ValueError("Discount rate cannot also be a cash-flow quantity.")
                    formula, unit = "Sum cashflow(year) / (1 + supplied percent discount rate / 100)^year, including year 0", currency
            else:
                investment = resolve(parameters["investment_id"], currency)
                if investment["period"] != state["reporting_period"] or number(investment["value"]) <= 0:
                    raise ValueError("Positive investment in the analysis context required.")
                if skill == "calculate-simple-payback":
                    benefit = resolve(parameters["annual_savings_id"], currency+"/year", True)
                    if review.get("definition_code") != "investment_over_constant_annual_net_savings":
                        raise ValueError("Declare the constant annual net-savings payback definition.")
                    if number(benefit["value"]) <= 0: raise ValueError("Nonpositive annual net savings gives no finite positive simple payback.")
                    value, unit = number(investment["value"])/number(benefit["value"]), "years"
                    formula = "Positive investment / supplied constant annual net operating savings; undiscounted"
                else:
                    benefit = resolve(parameters["net_benefit_id"], currency, True)
                    if review.get("definition_code") != "horizon_net_gain_over_investment":
                        raise ValueError("Declare net horizon gain AFTER investment / investment; not annual ROI.")
                    if benefit["period"] != horizon: raise ValueError("Net horizon gain must cover the explicitly declared horizon.")
                    value, unit = number(benefit["value"])/number(investment["value"])*100, "%"
                    formula = "Supplied undiscounted horizon net gain AFTER all costs including investment / positive investment * 100"
                inputs = [investment["id"], benefit["id"]]
                if len(set(inputs)) != len(inputs): raise ValueError("Investment and benefit must be distinct quantities.")
                if skill == "calculate-simple-payback":
                    if review.get("annual_savings_period") != benefit["period"]:
                        raise ValueError("Explicit representative annual savings period must match its source metric.")
                    if (date.fromisoformat(benefit["period"]["end"])-date.fromisoformat(benefit["period"]["start"])).days not in {364,365}:
                        raise ValueError("Constant annual savings requires a documented full-year reference, not extrapolated partial data.")
                    end = date.fromisoformat(horizon["end"])
                    whole_years = end.year-valuation.year
                    def anniversary(year):
                        return date(year, valuation.month, min(valuation.day, calendar.monthrange(year, valuation.month)[1]))
                    if end < anniversary(valuation.year+whole_years): whole_years -= 1
                    prior_anniversary = anniversary(valuation.year+whole_years)
                    next_anniversary = anniversary(valuation.year+whole_years+1)
                    horizon_years = number(whole_years) + number((end-prior_anniversary).days)/number((next_anniversary-prior_anniversary).days)
                    if value > horizon_years:
                        result["diagnostics"].append({"code": "PAYBACK_BEYOND_HORIZON", "message": "Arithmetic payback extends beyond supplied study horizon; no recovery within horizon established."})
        assumption = review["model_assumption"]
        if assumption not in result["assumptions"]: result["assumptions"].append(assumption)
        if entries is None:
            entries = [(ident+"-value", value, unit, inputs, formula, output_period)]
        result["metrics"] = [{"id": metric_id, "name": "Conditional "+skill.replace("calculate-", ""), "value": serialize(value), "unit": unit,
            "period": copy.deepcopy(output_period), "boundary_id": state["organizational_boundary"]["id"], "evidence_ids": sorted(refs),
            "method": {"name": "Explicit supplied project-finance arithmetic", "version": "0.1.0", "source": "docs/finance-contract.md"},
            "assumption": assumption, "uncertainty": {"kind": "unquantified", "description": "Model applicability, inputs and sensitivity are not independently verified.", "value": None, "unit": None},
            "calculation": {"formula": formula, "inputs": inputs, "conversions": ["No currency, inflation, tax or tariff conversion inferred."], "rounding": "70-digit Decimal root isolation; verified JSON serialization" if skill == "calculate-irr" else "34-digit Decimal arithmetic; JSON serialization"}}
            for metric_id, value, unit, inputs, formula, output_period in entries]
        result["diagnostics"].append({"code": "FINANCIAL_ANALYSIS_BASIS", "message": json.dumps(parameters, sort_keys=True)})
    except (ValueError, KeyError, TypeError) as error:
        result["metrics"] = []; gap(getattr(error, "diagnostic_code", "FINANCIAL_DATA_REQUIRED"), str(error))
    result["evidence_ids"] = sorted(refs)
    result["status"] = "blocked" if not result["metrics"] else ("partial" if result["data_gaps"] else "completed")
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"] == "open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE"); result["next_actions"] = list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    proposal = propose(state, result, "Compute conditional financial measure without investment advice or approval")
    return {"result": result, "proposal": proposal}
