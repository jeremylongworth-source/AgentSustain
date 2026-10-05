"""Reviewed project-level incremental cost per positive horizon abatement."""
import json

from .data_tools import number


class AbatementFactorRequired(ValueError):
    diagnostic_code = "EMISSION_FACTOR_REQUIRED"


def abatement_cost(state, parameters, resolve, refs):
    review, analysis = parameters["abatement_review"], parameters["analysis_review"]
    fields = ("scope_boundary", "baseline_conditions", "scenario_conditions", "functional_service",
              "nonoverlap_assessment", "exclusions", "method_comparability", "reviewer_role", "rationale")
    known = {e["id"] for e in state["evidence"]}
    if (not isinstance(review, dict) or review.get("confirmed") is not True
            or not isinstance(review.get("coverage_complete"), bool)
            or any(not isinstance(review.get(f), str) or not review[f].strip() for f in fields)
            or review.get("abatement_type") != "physical_reduction" or review.get("offsets_excluded") is not True
            or review.get("emissions_basis") != "undiscounted_horizon_total"
            or review.get("cost_basis") not in {"undiscounted_horizon_net_cost", "discounted_horizon_net_cost"}
            or review.get("cost_sign_convention") not in {"net_cost", "negative_net_cashflow"}
            or review.get("incremental_cost_definition") != "project_minus_baseline_net_cost"):
        raise ValueError("Reviewed physical-reduction, comparable horizon net-cost and nonoverlap definitions required.")
    evidence = review.get("evidence_ids")
    if (not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) for e in evidence)
            or not set(evidence) <= known):
        raise ValueError("Known abatement/cost source review evidence required.")
    refs.update(evidence)
    unit = review.get("emissions_unit")
    if unit not in {"kg CO2e", "t CO2e"}:
        raise ValueError("Explicit compatible CO2e mass unit required; no GWP or unit conversion inferred.")
    cost = resolve(parameters["incremental_cost_id"], analysis["currency"], True)
    before = resolve(parameters["baseline_emissions_id"], unit, True)
    after = resolve(parameters["scenario_emissions_id"], unit, True)
    if (before["id"] == after["id"] or any(m["period"] != analysis["horizon"] for m in (cost, before, after))
            or any(not m["evidence_ids"] for m in (cost, before, after))):
        raise ValueError("Distinct supported baseline/scenario and cost quantities must cover exactly the same study horizon.")
    owners = {m["id"]: r for r in state["results"] for m in r["metrics"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    contexts = review.get("source_contexts")
    if not isinstance(contexts, dict) or set(contexts) != {cost["id"], before["id"], after["id"]}:
        raise ValueError("Source context confirmation for selected cost and both emissions metrics required.")
    for metric in (cost, before, after):
        source = contexts[metric["id"]]
        if (not isinstance(source, dict) or any(source.get(f) != metric[f] for f in
                ("value", "unit", "period", "boundary_id", "method", "evidence_ids"))):
            raise ValueError("Source review must confirm selected quantities, units, periods, boundaries, methods and evidence.")
    for metric in (before, after):
        source = contexts[metric["id"]]
        if (not isinstance(source.get("gwp_basis"), str) or not source["gwp_basis"].strip()
                or source.get("scope_boundary") != review["scope_boundary"]):
            raise ValueError("Emissions source review requires explicit matching scope and GWP basis.")
        pending, seen = [metric["id"]], set()
        while pending:
            key = pending.pop()
            if key in seen or key not in metrics: continue
            seen.add(key)
            if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in owners[key]["diagnostics"]):
                raise AbatementFactorRequired("Selected emissions lineage retains a missing emission-factor requirement; supply defensible emissions before cost-per-abatement analysis.")
            pending.extend(metrics[key]["calculation"]["inputs"])
    if contexts[before["id"]]["gwp_basis"] != contexts[after["id"]]["gwp_basis"]:
        raise ValueError("Baseline and scenario GWP bases differ; no implicit restatement supported.")
    if number(before["value"]) < 0 or number(after["value"]) < 0:
        raise ValueError("Nonnegative gross physical emissions required; removals and offsets need separate methods.")
    reduction = number(before["value"])-number(after["value"])
    if reduction <= 0:
        raise ValueError("Zero or negative abatement does not support a conventional positive-abatement cost ratio.")
    inputs = [cost["id"], before["id"], after["id"]]
    if review["cost_basis"] == "discounted_horizon_net_cost":
        rate = resolve(review.get("discount_rate_id"), "%")
        if (rate["period"] != state["reporting_period"] or number(rate["value"]) <= -100
                or review.get("discount_basis") != analysis["dollar_basis"]):
            raise ValueError("Explicit compatible sourced rate context required for already-discounted cost.")
        inputs.append(rate["id"])
        # A supplied NPV numerator has an available, machine-checkable basis.
        if owners[cost["id"]]["skill"] == "calculate-npv":
            basis = [d for d in owners[cost["id"]]["diagnostics"] if d["code"] == "FINANCIAL_ANALYSIS_BASIS"]
            if len(basis) != 1: raise ValueError("NPV source economic basis required.")
            supplied = json.loads(basis[0]["message"])
            if not isinstance(supplied, dict) or not isinstance(supplied.get("analysis_review"), dict):
                raise ValueError("Structured NPV source economic basis required.")
            if (supplied.get("discount_rate_id") != rate["id"] or review["cost_sign_convention"] != "negative_net_cashflow"
                    or any(supplied.get("analysis_review", {}).get(f) != analysis[f] for f in
                           ("currency", "valuation_date", "horizon", "dollar_basis", "tax_basis"))):
                raise ValueError("NPV net-cashflow sign, discount rate and economic context must match cost-per-abatement review.")
    elif owners[cost["id"]]["skill"] == "calculate-npv":
        raise ValueError("NPV cannot be relabeled as undiscounted cost.")
    net_cost = number(cost["value"])*(-1 if review["cost_sign_convention"] == "negative_net_cashflow" else 1)
    entries = [(parameters["result_id"]+"-value", net_cost/reduction, analysis["currency"]+"/"+unit, inputs,
        "Reviewed signed project-minus-baseline horizon net cost / (baseline horizon emissions - scenario horizon emissions)", analysis["horizon"]),
        (parameters["result_id"]+"-abatement", reduction, unit, [before["id"], after["id"]],
         "Baseline - scenario; undiscounted physical horizon reduction, excluding offsets", analysis["horizon"])]
    return entries, review["coverage_complete"]
