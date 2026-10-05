"""Evidence-linked alternative business cases with pending human decision gates."""
import copy
from datetime import date
import json

from .data_tools import number, UNITS
from .finance_projects import _basis, _review
from .finance_abatement import AbatementFactorRequired


PARAMETERS = {"ranking_result_id", "case_review", "analysis_review", "result_id"}


def business_case(state, parameters, resolve, refs, rerun):
    analysis, review = parameters["analysis_review"], parameters["case_review"]
    known = {e["id"] for e in state["evidence"]}
    refs.update(_review(review, known, ("rationale", "claim_boundary", "reviewer_role")))
    if not isinstance(review.get("coverage_complete"), bool): raise ValueError("Explicit business-case coverage required.")
    results = {r["id"]: r for r in state["results"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    owners = {m["id"]: r for r in state["results"] for m in r["metrics"]}
    economic_fields = ("currency", "valuation_date", "horizon", "dollar_basis", "tax_basis")

    def reproduce(ident, skill):
        source = results.get(ident)
        if source is None or source["skill"] != skill: raise ValueError("Supported linked analytical result required.")
        basis = _basis(source)
        if any(basis["analysis_review"].get(f) != analysis[f] for f in economic_fields):
            raise ValueError("Business-case source economic basis must match the declared study.")
        original_basis = copy.deepcopy(basis)
        basis["result_id"] = parameters["result_id"]+"-check-"+ident
        while basis["result_id"] in results: basis["result_id"] += "-next"
        checked = rerun(state,skill,basis)["result"]
        content = lambda items: [{k:v for k,v in m.items() if k != "id"} for m in items]
        if not checked["metrics"] or content(checked["metrics"]) != content(source["metrics"]):
            raise ValueError("Business-case analytical source does not reproduce from current inputs.")
        refs.update(source["evidence_ids"])
        return source, original_basis, checked

    ranking, _, checked = reproduce(parameters["ranking_result_id"], "rank-sustainability-investments")
    reports = [d for d in checked["diagnostics"] if d["code"] == "INVESTMENT_RANKING"]
    if len(reports) != 1: raise ValueError("Reproduced ranking report required.")
    ranked = json.loads(reports[0]["message"])
    problem = review.get("problem")
    refs.update(_review(dict(problem, confirmed=True) if isinstance(problem,dict) else problem, known,
        ("statement", "baseline_id", "service_basis")))
    if (problem["baseline_id"] != ranked["comparison_review"]["baseline_id"]
            or problem["service_basis"] != ranked["comparison_review"]["service_basis"]):
        raise ValueError("Business problem baseline/service must match compared alternatives.")
    decision = review.get("decision")
    if (not isinstance(decision,dict) or set(decision) != {"owner", "requested_action", "status"}
            or decision["status"] != "pending_human_review"
            or any(not isinstance(decision[f],str) or not decision[f].strip() for f in ("owner","requested_action"))):
        raise ValueError("Named decision owner and pending human-review decision required; analytical composition cannot approve funding.")
    alternatives = review.get("alternatives")
    rows = {r["id"]: r for r in ranked["projects"]}
    if (not isinstance(alternatives,list) or any(not isinstance(a,dict) for a in alternatives)
            or any(not isinstance(a.get("project_id"),str) for a in alternatives)
            or len(alternatives) != len(rows) or {a["project_id"] for a in alternatives} != set(rows)):
        raise ValueError("Business-case register must retain every compared alternative exactly once, including deferrals.")
    contexts = review.get("source_contexts")
    if not isinstance(contexts,dict): raise ValueError("Physical source confirmations required.")
    selected, entries, detailed = set(), [], []

    def physical(ident, unit):
        metric = resolve(ident,unit,True); selected.add(ident)
        source = contexts.get(ident)
        if (metric["period"] != analysis["horizon"] or not isinstance(source,dict)
                or any(source.get(f) != metric[f] for f in ("value","unit","period","boundary_id","method","evidence_ids"))
                or not metric["evidence_ids"] or number(metric["value"]) < 0):
            raise ValueError("Nonnegative supported physical horizon quantities and current source confirmations required.")
        pending, seen = [ident], set()
        while pending:
            key = pending.pop()
            if key in seen or key not in metrics: continue
            seen.add(key)
            if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in owners[key]["diagnostics"]):
                raise AbatementFactorRequired("Business-case physical lineage retains an emission-factor requirement.")
            pending.extend(metrics[key]["calculation"]["inputs"])
        return metric

    for index, alternative in enumerate(alternatives,1):
        if set(alternative) != {"project_id","finance_result_id","physical_link","implementation","risks","sensitivity_results"}:
            raise ValueError("Complete physical/financial/sensitivity/implementation alternative record required.")
        row = rows[alternative["project_id"]]
        finance, finance_basis, _ = reproduce(alternative["finance_result_id"], "calculate-npv")
        if finance["metrics"][0]["id"] not in {m["metric_id"] for m in row["metrics"].values()}:
            raise ValueError("Alternative NPV must be a measure in that project's verified comparison.")
        link = alternative["physical_link"]
        if (not isinstance(link,dict) or set(link) != {"baseline_metric_id","scenario_metric_id","reduction_metric_id","unit","gwp_basis","scope_boundary"}
                or link["unit"] not in UNITS
                or not isinstance(link["scope_boundary"],str) or not link["scope_boundary"].strip()
                or ("CO2e" in link["unit"] and (not isinstance(link["gwp_basis"],str) or not link["gwp_basis"].strip()))
                or ("CO2e" not in link["unit"] and link["gwp_basis"] is not None)):
            raise ValueError("Explicit matched physical baseline/scenario/reduction link required; CO2e needs GWP basis and other quantities use null GWP.")
        before, after, reduction = [physical(link[f],link["unit"]) for f in ("baseline_metric_id","scenario_metric_id","reduction_metric_id")]
        if len({m["id"] for m in (before,after,reduction)}) != 3:
            raise ValueError("Physical baseline, scenario and reduction must be distinct quantities.")
        if number(before["value"])-number(after["value"]) != number(reduction["value"]):
            raise ValueError("Physical baseline minus scenario does not reproduce the compared reduction.")
        if reduction["id"] not in {m["metric_id"] for m in row["metrics"].values()}:
            raise ValueError("Physical reduction must link that alternative's compared outcome.")
        for m in (before,after,reduction):
            if any(contexts[m["id"]].get(f) != link[f] for f in ("gwp_basis","scope_boundary")):
                raise ValueError("Physical link source GWP/scope contexts differ.")
        compared = ranked["comparison_review"]["source_contexts"][reduction["id"]]
        compared_fields = ("gwp_basis","scope_boundary") if "CO2e" in link["unit"] else ("scope_boundary",)
        if any(compared.get(f) != link[f] for f in compared_fields):
            raise ValueError("Business-case physical basis differs from comparison.")
        phases, risks = alternative["implementation"], alternative["risks"]
        if not isinstance(phases,list) or not phases or not isinstance(risks,list) or not risks:
            raise ValueError("Nonempty implementation and risk registers with owners required.")
        for phase in phases:
            if (not isinstance(phase,dict) or set(phase) != {"step","owner","target_date","dependencies"}
                    or any(not isinstance(phase[f],str) or not phase[f].strip() for f in ("step","owner","target_date"))
                    or not isinstance(phase["dependencies"],list) or any(not isinstance(d,str) or not d.strip() for d in phase["dependencies"])
                    or not date.fromisoformat(analysis["horizon"]["start"]) <= date.fromisoformat(phase["target_date"]) <= date.fromisoformat(analysis["horizon"]["end"])):
                raise ValueError("Owned implementation steps, explicit dependencies and in-horizon proposed dates required.")
        for risk in risks:
            refs.update(_review(dict(risk,confirmed=True) if isinstance(risk,dict) else risk,known,("description","owner")))
        sensitivity = alternative["sensitivity_results"]
        if not isinstance(sensitivity,list) or not sensitivity or any(not isinstance(s,dict) for s in sensitivity):
            raise ValueError("At least one explicitly varied sourced financial scenario per alternative required.")
        summaries = []
        for scenario in sensitivity:
            if set(scenario) != {"result_id","driver","description"} or any(not isinstance(scenario[f],str) or not scenario[f].strip() for f in scenario):
                raise ValueError("Named sensitivity driver, description and analytical result required.")
            result, basis, _ = reproduce(scenario["result_id"], "calculate-npv")
            changed = [field for field in ("cashflows","discount_rate_id") if basis[field] != finance_basis[field]]
            if not changed: raise ValueError("Sensitivity must change explicit cash-flow or discount-rate inputs; duplicate base scenarios are not sensitivity evidence.")
            bounds = next(item["range"] for item in row["metrics"].values() if item["metric_id"] == finance["metrics"][0]["id"])
            outside = not number(bounds["low"]) <= number(result["metrics"][0]["value"]) <= number(bounds["high"])
            summaries.append(dict(scenario,changed_inputs=changed,metrics=copy.deepcopy(result["metrics"]),assumptions=result["assumptions"],
                outside_comparison_range=outside))
        for role, m in (("npv",finance["metrics"][0]),("physical-reduction",reduction)):
            entries.append((parameters["result_id"]+f"-alternative-{index}-{role}",number(m["value"]),m["unit"],[m["id"]],
                "Verified alternative measure retained separately in evidence-linked business case; no portfolio total",m["period"]))
        detailed.append(dict(alternative,screening=copy.deepcopy(row),finance=copy.deepcopy(finance),finance_inputs=finance_basis,
            physical_sources=copy.deepcopy([before,after,reduction]),sensitivity=summaries))
    if set(contexts) != selected: raise ValueError("Physical confirmations must cover selected business-case metrics only.")
    report = {"problem":problem,"alternatives":detailed,"decision":decision,"claim_boundary":review["claim_boundary"],
        "ranking":ranked,"screening_leaders":[r["id"] for r in ranked["projects"] if r["rank"] == 1],
        "review_requirements":copy.deepcopy(state["review_requirements"]),"data_gaps":copy.deepcopy(state["data_gaps"]),
        "portfolio_total":None,"implementation_authorized":False,
        "limits":"Conditional modeled business case; supplied applicability, feasibility, risk and sensitivity coverage are not authenticated. Human funding, engineering and claims review remain pending."}
    return entries, report, review["coverage_complete"] and ranked["comparison_review"]["coverage_complete"]
