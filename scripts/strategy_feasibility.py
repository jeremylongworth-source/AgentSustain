"""Conditional target scenario screening with sourced delivery constraints."""
import copy
from datetime import date
import json
import re

from .data_tools import convert, number, serialize
from .finance_tools import OPERATIONS as FINANCE_OPERATIONS, run_finance
from .finance_projects import _review
from .inventory_analysis import _retain_checks
from .strategy_tools import FactorRequired, _fit, _quantity, _record, _reproduce, _reviewed, _selected, _text


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Canonical dated delivery and review records required.")
    return date.fromisoformat(value)


def _projection(state, ident, refs, when):
    metric = _selected(state, ident, refs)
    known = {e["id"]: e for e in state["evidence"]}
    if (metric["period"] != when or number(metric["value"]) < 0 or not _text(metric["assumption"])
            or not any(known[e]["source"]["tier"] == 5 for e in metric["evidence_ids"])):
        raise ValueError("Gross commitment-period scenarios require explicit assumptions and tier 5 model evidence; unknown is not zero.")
    return metric


def _scenario_quantity(*args, **kwargs):
    return _quantity(*args, **kwargs, uncertainty_description="Source quality, joint-model assumptions, future service and delivery uncertainty remain unquantified; supplied scenario bounds are not confidence intervals or delivery probabilities.")


def _investment(state, investment, projects, parameters, refs, result):
    if investment is None:
        return None
    if not isinstance(investment, dict) or set(investment) != {"cost_metric_id", "budget_metric_id", "review"}:
        raise ValueError("Selected scenario cost, budget and economic source review required.")
    review = investment["review"]
    _reviewed(state, review, refs, ("scope", "currency", "valuation_date", "dollar_basis", "tax_basis", "cost_scope", "funding_basis"))
    if (not re.fullmatch(r"[A-Z]{3}", review["currency"]) or review["dollar_basis"] not in {"real", "nominal"}
            or review["tax_basis"] not in {"pre_tax", "after_tax"} or review.get("project_ids") != sorted(projects)):
        raise ValueError("Exact selected project set and matched currency/dollar/tax basis required; no currency conversion.")
    valuation = _date(review["valuation_date"])
    if not _date(state["reporting_period"]["start"]) <= valuation <= _date(state["reporting_period"]["end"]):
        raise ValueError("Investment valuation must lie within the analysis reporting period.")
    costs = [_selected(state, investment[field], refs) for field in ("cost_metric_id", "budget_metric_id")]
    if costs[0]["id"] == costs[1]["id"]:
        raise ValueError("Selected cost and available budget must be distinct sourced quantities.")
    selected_owners = {m["id"]: r for r in state["results"] for m in r["metrics"]}
    for role, metric in zip(("cost", "budget"), costs, strict=True):
        owner = selected_owners[metric["id"]]
        if owner["skill"] in FINANCE_OPERATIONS and (role == "budget" or owner["skill"] != "calculate-sustainability-project-cost"):
            raise ValueError("Initial investment screening accepts reproduced initial project cost and a sourced budget record, not NPV/returns or a modeled cost as available funding.")
    _fit(state, review, costs, refs)
    if any(m["unit"] != review["currency"] or number(m["value"]) < 0 or m["period"] != state["reporting_period"] for m in costs):
        raise ValueError("Matched nonnegative sourced quote/budget quantities in the analysis period required.")
    owners = {m["id"]: r for r in state["results"] for m in r["metrics"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    evidence = {e["id"]: e for e in state["evidence"]}
    verified = set(); seen = set(); pending = [m["id"] for m in costs]
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        owner = owners.get(key)
        source = metrics.get(key) or evidence.get(key)
        if owner:
            if any(d["code"] == "NONCASH_SHADOW_PRICE" for d in owner["diagnostics"]):
                raise ValueError("Noncash shadow-price ancestry cannot support investment cost or cash budget.")
            if owner["skill"] in FINANCE_OPERATIONS and owner["id"] not in verified:
                basis = copy.deepcopy(_record(owner, "FINANCIAL_ANALYSIS_BASIS"))
                if any(basis["analysis_review"].get(f) != review[f] for f in ("currency", "valuation_date", "dollar_basis", "tax_basis")):
                    raise ValueError("Derived finance cost/budget basis differs from the selected investment review.")
                basis["result_id"] = parameters["result_id"] + "-finance-check-" + owner["id"]
                while any(r["id"] == basis["result_id"] for r in state["results"]):
                    basis["result_id"] += "-next"
                checked = run_finance(state, owner["skill"], basis)["result"]
                _retain_checks(result, dict(checked, diagnostics=[d for d in checked["diagnostics"] if d["code"] != "FINANCIAL_ANALYSIS_BASIS"]))
                refs.update(checked["evidence_ids"])
                if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in checked["diagnostics"]):
                    raise FactorRequired("Investment lineage retains an unresolved emission factor.")
                content = lambda rows: [{k: v for k, v in m.items() if k != "id"} for m in rows]
                if checked["status"] == "blocked" or not checked["metrics"] or content(checked["metrics"]) != content(owner["metrics"]):
                    raise ValueError("Derived investment source does not reproduce against current inputs.")
                verified.add(owner["id"])
        if source and source["calculation"]:
            pending.extend(source["calculation"]["inputs"])
    delta = number(costs[1]["value"]) - number(costs[0]["value"])
    return {"review": review, "cost": costs[0], "budget": costs[1], "budget_minus_cost": serialize(delta),
        "within_supplied_budget": delta >= 0, "funding_authorized": False,
        "limit": "Selected modeled cost versus supplied budget only; no lifecycle-cost, liquidity, financing or investment approval."}


def _delivery(state, scenario, target_period, reviewed_date, refs):
    initiatives = scenario["initiatives"]
    if not isinstance(initiatives, list) or not initiatives:
        raise ValueError("Nonempty owned initiative register required for each modeled scenario.")
    known = {e["id"] for e in state["evidence"]}
    project_register = {p["id"]: p for p in state["projects"]}
    items = {}; projects = set()
    for item in initiatives:
        if (not isinstance(item, dict) or set(item) != {"id", "project_id", "owner", "commission_date", "depends_on", "evidence_ids", "description"}
                or any(not _text(item[f]) for f in ("id", "project_id", "owner", "description")) or item["id"] in items
                or item["project_id"] not in project_register or item["project_id"] in projects):
            raise ValueError("Distinct owned initiatives must resolve to distinct current project records.")
        refs.update(_review(dict(item, confirmed=True), known, ()))
        project = project_register[item["project_id"]]
        if not project["evidence_ids"]:
            raise ValueError("Project-specific source evidence required.")
        refs.update(project["evidence_ids"])
        if not set(project["evidence_ids"]) <= set(item["evidence_ids"]):
            raise ValueError("Initiative must retain its project's actual source evidence.")
        _date(item["commission_date"])
        if (not isinstance(item["depends_on"], list) or any(not _text(i) for i in item["depends_on"])
                or len(item["depends_on"]) != len(set(item["depends_on"]))):
            raise ValueError("Distinct explicit initiative dependency IDs required.")
        items[item["id"]] = item; projects.add(item["project_id"])
    visiting = set(); visited = set()
    def visit(ident):
        if ident in visiting:
            raise ValueError("Initiative dependency cycle prevents a credible delivery sequence.")
        if ident in visited:
            return
        visiting.add(ident)
        for dependency in items[ident]["depends_on"]:
            if dependency not in items or _date(items[dependency]["commission_date"]) > _date(items[ident]["commission_date"]):
                raise ValueError("Known prerequisite initiatives must commission no later than dependent initiatives.")
            visit(dependency)
        visiting.remove(ident); visited.add(ident)
    for ident in items:
        visit(ident)
    timing = scenario["scenario_review"].get("timing_basis")
    if timing not in {"full_period_from_start", "dated_profile_modelled"}:
        raise ValueError("Explicit full-period or dated modeled-profile timing basis required.")
    issues = []; unresolved = []
    for item in initiatives:
        commissioned = _date(item["commission_date"])
        if commissioned < reviewed_date:
            unresolved.append("Proposed commission date for " + item["id"] + " predates review; actual delivery evidence is not verified.")
        if commissioned > _date(target_period["end"]):
            issues.append("Initiative " + item["id"] + " commissions after the commitment period.")
        elif commissioned > _date(target_period["start"]) and timing == "full_period_from_start":
            issues.append("Initiative " + item["id"] + " commissions after the period starts; full-period benefit is unsupported without a dated profile.")
    return list(items.values()), projects, issues, unresolved


def evaluate(state, parameters, refs, result, gap):
    target_owner, target = _reproduce(state, parameters["target_result_id"], "develop-target", refs)
    endpoint = _selected(state, target["endpoint_metric_id"], refs)
    definition = target["definition"]; absolute = definition["baseline_metric"]
    unit = absolute["unit"]; denominator = definition["denominator_metric"]
    review = parameters["feasibility_review"]
    _reviewed(state, review, refs, ("scope", "decision_basis", "uncertainty_basis", "review_date", "accounting_basis"))
    if (review["scope"] != target["target_review"]["scope"] or review["accounting_basis"] != definition["baseline_scope_review"]["accounting_basis"]
            or not isinstance(review.get("coverage_complete"), bool)):
        raise ValueError("Feasibility review must retain the selected target scope/accounting basis and explicit coverage.")
    reviewed_date = _date(review["review_date"])
    if reviewed_date <= _date(absolute["period"]["end"]) or reviewed_date > _date(endpoint["period"]["end"]):
        raise ValueError("Review date must follow the reference period and lie no later than the target commitment end.")
    scenarios = parameters["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Explicit nonempty joint modeled scenarios required; individual savings are not automatically added.")
    rows = []; ids = set()
    for index, scenario in enumerate(scenarios, 1):
        fields = {"id", "outcome_metric_id", "range_metric_ids", "activity_metric_id", "scenario_review", "initiatives", "constraints", "investment"}
        if not isinstance(scenario, dict) or set(scenario) != fields or not _text(scenario["id"]) or scenario["id"] in ids:
            raise ValueError("Distinct complete alternative scenario records required.")
        ids.add(scenario["id"])
        basis = scenario["scenario_review"]
        _reviewed(state, basis, refs, ("scope", "accounting_basis", "model_assumption", "service_definition", "interaction_assessment", "uncertainty_basis"))
        if (basis["scope"] != review["scope"] or basis["accounting_basis"] != review["accounting_basis"]
                or basis.get("aggregation_basis") != "joint_modelled_outcome"):
            raise ValueError("Scenarios must use a reviewed joint outcome, matching scope/accounting and interactions; no sum of isolated measures.")
        if basis["model_assumption"] not in result["assumptions"]:
            result["assumptions"].append(basis["model_assumption"])
        outcome = _projection(state, scenario["outcome_metric_id"], refs, endpoint["period"])
        ranges = scenario["range_metric_ids"]
        if ranges is not None and (not isinstance(ranges, list) or len(ranges) != 2 or any(not _text(i) for i in ranges) or len(set(ranges)) != 2 or outcome["id"] in ranges):
            raise ValueError("Supply distinct lower/upper modeled gross quantities, or explicit null when no range is defensible.")
        limits = [] if ranges is None else [_projection(state, i, refs, endpoint["period"]) for i in ranges]
        selected = [outcome, *limits]; activity = None; activity_conversion = None
        if denominator:
            activity = _projection(state, scenario["activity_metric_id"], refs, endpoint["period"])
            activity_conversion = dict(convert(activity["value"], activity["unit"], denominator["unit"]), metric_id=activity["id"], source_unit=activity["unit"])
            converted_activity = activity_conversion["value"]
            if converted_activity <= 0:
                raise ValueError("Positive comparable modeled future service required for intensity feasibility.")
            selected.append(activity)
        elif scenario["activity_metric_id"] is not None:
            raise ValueError("Absolute target screening does not use an intensity denominator.")
        _fit(state, basis, selected, refs)
        outcome_conversion = dict(convert(outcome["value"], outcome["unit"], unit), metric_id=outcome["id"], source_unit=outcome["unit"])
        gross = outcome_conversion["value"]
        range_conversions = [dict(convert(m["value"], m["unit"], unit), metric_id=m["id"], source_unit=m["unit"]) for m in limits]
        bounds = [c["value"] for c in range_conversions]
        conversions = [json.dumps(c, sort_keys=True, default=serialize) for c in [outcome_conversion, *([activity_conversion] if activity else [])]]
        if bounds and not bounds[0] <= gross <= bounds[1]:
            raise ValueError("Declared lower/point/upper joint outcome order is inconsistent.")
        point = gross / converted_activity if activity else gross
        normalized_bounds = [v / converted_activity if activity else v for v in bounds]
        allowed = number(endpoint["value"]) * converted_activity if activity else number(endpoint["value"])
        initiatives, projects, timing_issues, timing_unknowns = _delivery(state, scenario, endpoint["period"], reviewed_date, refs)
        constraints = scenario["constraints"]; domains = {"technical", "financial", "organizational", "service", "evidence"}
        seen = set(); observed = set(); unresolved = list(timing_unknowns); unmet = list(timing_issues)
        if not isinstance(constraints, list) or not constraints:
            raise ValueError("Explicit owned technical, financial, organizational, service and evidence constraints required.")
        known = {e["id"] for e in state["evidence"]}
        for item in constraints:
            if (not isinstance(item, dict) or set(item) != {"id", "domain", "status", "owner", "description", "evidence_ids"}
                    or any(not _text(item[f]) for f in ("id", "owner", "description")) or item["id"] in seen
                    or item["domain"] not in domains or item["status"] not in {"supported", "unresolved", "not_met"}
                    or not isinstance(item["evidence_ids"], list) or any(not _text(e) for e in item["evidence_ids"])
                    or len(item["evidence_ids"]) != len(set(item["evidence_ids"])) or not set(item["evidence_ids"]) <= known):
                raise ValueError("Distinct explicit constraint statuses, owners, descriptions and known evidence required.")
            seen.add(item["id"]); observed.add(item["domain"]); refs.update(item["evidence_ids"])
            if item["status"] != "unresolved" and not item["evidence_ids"]:
                raise ValueError("Supported or known unmet constraints require source evidence; unknown stays unresolved.")
            if item["status"] == "unresolved":
                unresolved.append(item["description"])
            elif item["status"] == "not_met":
                unmet.append(item["description"])
        if observed != domains:
            raise ValueError("All five delivery constraint domains must be addressed explicitly.")
        investment = _investment(state, scenario["investment"], projects, parameters, refs, result)
        if investment and investment["review"]["scope"] != review["scope"]:
            raise ValueError("Investment scope must match the selected target scenario.")
        if investment is None:
            unresolved.append("Selected scenario investment cost and budget coverage are unknown; no zero cost or affordability inferred.")
        elif not investment["within_supplied_budget"]:
            unmet.append("Selected scenario cost exceeds its supplied comparable budget.")
        if not bounds:
            unresolved.append("No defensible joint scenario range supplied; point arithmetic is not a probability or robust delivery conclusion.")
        if not review["coverage_complete"] or not definition["baseline_scope_review"]["coverage_complete"]:
            unresolved.append("Selected target/scenario coverage is incomplete.")
        for message in (*unmet, *unresolved):
            gap("Scenario " + scenario["id"] + ": " + message)
        meets = point <= number(endpoint["value"])
        range_screen = None if not bounds else ("all_supplied_levels_meet" if normalized_bounds[1] <= number(endpoint["value"])
            else "none_supplied_levels_meet" if normalized_bounds[0] > number(endpoint["value"]) else "range_straddles_objective")
        assumption = "Supplied joint commitment-period model and delivery reviews only; alternatives are not additive, benefits are not realized and feasibility/adoption remain unapproved."
        inputs = [outcome["id"], endpoint["id"]] + ([activity["id"]] if activity else [])
        point_metric = _scenario_quantity(result, f"scenario-{index}-kpi", "Conditional scenario target indicator", point, endpoint["unit"], endpoint["period"],
            endpoint["boundary_id"], refs, inputs, "Converted gross joint scenario quantity / comparable future service for intensity; gross quantity for absolute", assumption, conversions=conversions)
        difference = _scenario_quantity(result, f"scenario-{index}-gap", "Conditional scenario minus target endpoint", point-number(endpoint["value"]), endpoint["unit"], endpoint["period"],
            endpoint["boundary_id"], refs, inputs, "Scenario indicator - proposed endpoint; positive means above reduction objective", assumption, conversions=conversions)
        gross_allowed = _scenario_quantity(result, f"scenario-{index}-gross-limit", "Conditional gross quantity at proposed objective", allowed, unit, endpoint["period"],
            endpoint["boundary_id"], refs, inputs, "Proposed intensity endpoint * modeled future service; absolute endpoint directly", assumption, conversions=conversions)
        change = _scenario_quantity(result, f"scenario-{index}-absolute-change", "Scenario gross difference from reference baseline", gross-number(absolute["value"]), unit, endpoint["period"],
            endpoint["boundary_id"], refs, [outcome["id"], absolute["id"]], "Scenario gross quantity - reference baseline; no causal attribution or realized savings", assumption, conversions=conversions[:1])
        budget_metric = None if investment is None else _scenario_quantity(result, f"scenario-{index}-budget-gap", "Supplied budget minus selected scenario cost", investment["budget_minus_cost"], investment["review"]["currency"], state["reporting_period"],
            endpoint["boundary_id"], refs, [investment["cost"]["id"], investment["budget"]["id"]], "Supplied comparable budget - selected scenario cost; no funding authorization", assumption)
        rows.append({"scenario": scenario, "source_outcome": outcome, "source_range": limits, "future_service": activity,
            "conversions": [json.loads(s) for s in conversions] + json.loads(json.dumps(range_conversions, default=serialize)),
            "point_metric_id": point_metric["id"], "endpoint_gap_metric_id": difference["id"], "allowed_gross_metric_id": gross_allowed["id"],
            "absolute_change_metric_id": change["id"], "budget_gap_metric_id": None if budget_metric is None else budget_metric["id"],
            "point_meets_proposed_objective": meets, "indicator_range": None if not bounds else {"low": serialize(normalized_bounds[0]), "high": serialize(normalized_bounds[1]), "unit": endpoint["unit"], "basis": "Supplied modeled scenario bounds with one declared future service; not confidence intervals or probabilities."},
            "range_screen": range_screen, "initiatives": initiatives, "investment": investment,
            "known_unmet_conditions": unmet, "unresolved_conditions": unresolved,
            "delivery_screen": "known_conditions_not_met" if unmet else "unresolved_conditions" if unresolved else "reviewed_assumptions_only",
            "feasibility": None, "implementation_authorized": False, "funding_authorized": False})
    gate = result["id"] + "-feasibility-review"
    while any(r["id"] == gate for r in result["review_requirements"]):
        gate += "-next"
    result["review_requirements"].append({"id": gate, "state": "PROFESSIONAL_REVIEW_REQUIRED",
        "reason": "Review joint models, service/growth equivalence, uncertainty, delivery/resource dependencies and funding before judging target feasibility or approving actions.",
        "scope": review["scope"], "reviewer_role": "Qualified technical, financial and accountable strategy reviewers", "status": "open", "resolution": None})
    return {"target_result_id": target_owner["id"], "target_snapshot": target, "feasibility_review": review, "scenarios": rows,
        "selected_scenario_id": None, "portfolio_total": None, "feasibility": None, "target_adopted": False,
        "public_claim_authorized": False, "implementation_authorized": False, "funding_authorized": False,
        "limits": "Separate conditional joint scenarios; numerical objective coverage is distinct from delivery feasibility. Source fitness and constraints are supplied review, not authenticated engineering, financial or owner approval."}
