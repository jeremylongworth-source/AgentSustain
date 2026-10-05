"""Scope 3 factual classification and sourced physical-activity category totals."""
import copy
from decimal import Decimal, localcontext
import json

from .contract_validation import validate_state
from .data_tools import convert, number, serialize
from .ghg_foundation import factor_issues
from .scope_accounting import _evidence, _text
from .state_proposal import propose


STANDARD = "https://ghgprotocol.org/sites/default/files/standards/Corporate-Value-Chain-Accounting-Reporing-Standard_041613_2.pdf"
CATEGORIES = {
    1: "Purchased goods and services", 2: "Capital goods", 3: "Fuel- and energy-related activities",
    4: "Upstream transportation and distribution", 5: "Waste generated in operations", 6: "Business travel",
    7: "Employee commuting", 8: "Upstream leased assets", 9: "Downstream transportation and distribution",
    10: "Processing of sold products", 11: "Use of sold products", 12: "End-of-life treatment of sold products",
    13: "Downstream leased assets", 14: "Franchises", 15: "Investments",
}


def _result(state, skill, result_id):
    validate_state(state)
    if not _text(result_id):
        raise ValueError("Result ID required")
    return {"id": result_id, "skill": skill, "contract_version": "0.1.0", "status": "completed",
            "review_states": ["ANALYTICAL"] + [r["state"] for r in state["review_requirements"] if r["status"] == "open"],
            "review_requirements": copy.deepcopy(state["review_requirements"]), "metrics": [], "evidence_ids": [],
            "assumptions": list(state["assumptions"]), "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}


def _gap(result, code, message):
    result["data_gaps"].append({"id": f"{result['id']}-gap-{len(result['data_gaps'])}", "field": "scope_3_coverage",
        "reason": message, "impact": "Classification or inventory coverage is incomplete.",
        "remedy": "Supply compatible category, source, boundary and factor records; reconcile omissions and overlaps."})
    result["diagnostics"].append({"code": code, "message": message})


def _finish(state, result, supported, fixture_mode, reason):
    if not isinstance(fixture_mode, bool):
        raise ValueError("Fixture mode must be boolean")
    if fixture_mode:
        assumption = "Synthetic fixture scope 3/inventory analysis only; not a real inventory."
        result["assumptions"] = list(dict.fromkeys(result["assumptions"] + [assumption]))
        result["diagnostics"].append({"code": "SYNTHETIC_FIXTURE", "message": assumption})
    result["status"] = "blocked" if not supported else ("partial" if result["data_gaps"] else "completed")
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(gap["remedy"] for gap in result["data_gaps"]))
    if not supported and not result["next_actions"]:
        result["next_actions"] = ["Supply supported source records before analysis."]
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    return {"result": result, "proposal": propose(state, result, reason)}


def _category(facts):
    relationship = facts.get("relationship")
    if relationship == "purchase":
        if type(facts.get("capital_good")) is not bool or facts.get("not_other_categories") is not True:
            return None
        return 2 if facts["capital_good"] else 1
    if relationship == "transport":
        if facts.get("transported_product") == "fuel_energy":
            return 3
        if facts.get("transport_stage") == "tier2_to_tier1":
            return 2 if facts.get("capital_good") is True else (1 if facts.get("capital_good") is False else None)
        if facts.get("transport_purchased_by_org") is True or facts.get("transport_stage") == "tier1_to_org":
            return 4
        if facts.get("transport_stage") == "org_to_customer" and facts.get("transport_purchased_by_org") is False:
            return 9
        return None
    if relationship == "lease":
        return {"lessee": 8, "lessor": 13}.get(facts.get("lease_role"))
    return {"energy_lifecycle": 3, "operational_waste": 5, "business_travel": 6, "employee_commuting": 7,
            "processing_sold_products": 10, "use_sold_products": 11, "end_of_life_sold_products": 12,
            "franchise": 14, "investment": 15}.get(relationship)


def _lease_reconciled(state, source):
    """Leases need an explicit prior scope 1/2 exclusion, never an unknown lease."""
    if source.get("relationship") != "lease":
        return True
    prior = next((r for r in state["results"] if r["id"] == source.get("scope12_result_id")), None)
    if prior is None or prior["skill"] not in {"classify-scope-1-emissions", "classify-scope-2-emissions"}:
        return False
    try:
        records = [json.loads(d["message"]) for d in prior["diagnostics"] if d["code"] == "SOURCE_CLASSIFICATION"]
        if len(records) != 1:
            return False
        matches = [s for s in records[0]["sources"] if s["id"] == source["id"]]
        facts = [s for s in records[0]["input_facts"] if s["id"] == source["id"]]
        return (len(matches) == 1 and matches[0]["scope"] == "excluded"
                and matches[0]["boundary_approach"] == state["organizational_boundary"]["approach"]
                and len(facts) == 1 and facts[0]["period"] == state["reporting_period"])
    except (ValueError, KeyError, TypeError):
        return False


def classify_scope3(state, sources, result_id, fixture_mode=False):
    result = _result(state, "classify-scope-3-emissions", result_id)
    if not isinstance(sources, list) or not sources:
        raise ValueError("Supply scope 3 source facts")
    known = {e["id"] for e in state["evidence"]}
    decisions, refs, seen = [], set(), set()
    for source in sources:
        if not isinstance(source, dict) or not _text(source.get("id")) or source["id"] in seen:
            raise ValueError("Unique source IDs required")
        seen.add(source["id"])
        decision = copy.deepcopy(source)
        decision["category"] = None
        decisions.append(decision)
        if (not _evidence(source, known) or not _text(source.get("rationale")) or source.get("period") != state["reporting_period"]
                or source.get("boundary_id") != state["organizational_boundary"]["id"]):
            _gap(result, "SOURCE_CONTEXT_REQUIRED", f"{source['id']}: source evidence, period and organizational context are required.")
            continue
        refs.update(source["evidence_ids"])
        if source.get("in_value_chain") is not True or source.get("emissions_in_scope_1_2") is not False:
            _gap(result, "SCOPE_RECONCILIATION_REQUIRED", f"{source['id']}: establish value-chain relationship and distinct emissions coverage outside scope 1/2.")
            continue
        if not _lease_reconciled(state, source):
            _gap(result, "LEASE_BOUNDARY_REQUIRED", f"{source['id']}: lease category requires a referenced scope 1/2 exclusion; unknown control is not exclusion.")
            continue
        category = _category(source)
        if category is None:
            _gap(result, "CATEGORY_FACTS_REQUIRED", f"{source['id']}: category discriminator facts are incomplete or unsupported.")
            continue
        decision["category"] = category
        decision["category_name"] = CATEGORIES[category]
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code": "SCOPE3_CLASSIFICATION", "message": json.dumps({"sources": decisions,
        "method_source": STANDARD, "version": "2011 with 2013 corrections", "limits": "Supplied factual assessment, not source authentication or category boundary completeness."}, sort_keys=True)})
    return _finish(state, result, any(d["category"] is not None for d in decisions), fixture_mode, "Classify scope 3 relationships with explicit discriminator facts")


def calculate_category(state, category, sources, components, coverage_review, result_id, fixture_mode=False):
    """Sum verified existing activity-factor CO2e components for one category.

    Allocation must already be reflected in the physical activity quantity. This
    primitive does not derive spend, lifecycle, product-use or financial factors.
    """
    result = _result(state, "calculate-scope-3-category", result_id)
    if type(category) is not int or category not in CATEGORIES or not isinstance(sources, list) or not sources or not isinstance(components, list):
        raise ValueError("Category, classified sources and components required")
    if not isinstance(coverage_review, dict):
        raise ValueError("Coverage review required")
    known = {e["id"] for e in state["evidence"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    factors = {f["id"]: f for f in state["emission_factors"]}
    refs, inputs, accepted, total = set(), [], [], Decimal(0)
    if (type(coverage_review.get("category")) is not int or coverage_review.get("category") != category or coverage_review.get("confirmed") is not True
            or not _evidence(coverage_review, known) or not _text(coverage_review.get("minimum_boundary_assessment"))
            or not _text(coverage_review.get("exclusions_and_optional_coverage"))):
        _gap(result, "CATEGORY_BOUNDARY_REQUIRED", "Review minimum category boundary, exclusions and optional coverage with evidence.")
    else:
        refs.update(coverage_review["evidence_ids"])
    source_map = {}
    for source in sources:
        if not isinstance(source, dict) or not _text(source.get("id")) or source["id"] in source_map:
            raise ValueError("Unique source IDs required")
        source_map[source["id"]] = source
    if any(not isinstance(c, dict) or c.get("source_id") not in source_map for c in components):
        raise ValueError("Component source does not resolve")
    counts = {}
    for source in sources:
        counts[source.get("activity_id")] = counts.get(source.get("activity_id"), 0) + 1
    metric_counts = {}
    for component in components:
        ident = component.get("metric_id")
        metric_counts[ident] = metric_counts.get(ident, 0) + 1
    for ident, source in source_map.items():
        if (type(source.get("category")) is not int or source.get("category") != category or _category(source) != category or not _evidence(source, known)
                or source.get("period") != state["reporting_period"] or source.get("boundary_id") != state["organizational_boundary"]["id"]
                or not _text(source.get("rationale"))
                or not _lease_reconciled(state, source)
                or source.get("in_value_chain") is not True or source.get("emissions_in_scope_1_2") is not False):
            _gap(result, "CATEGORY_CLASSIFICATION_REQUIRED", f"{ident}: supplied category or scope relationship is unsupported.")
            continue
        refs.update(source["evidence_ids"])
        activity = metrics.get(source.get("activity_id"))
        if (activity is None or counts.get(source.get("activity_id")) != 1 or activity["period"] != state["reporting_period"]
                or activity["boundary_id"] != state["organizational_boundary"]["id"] or activity["value"] is None or number(activity["value"]) < 0):
            _gap(result, "ACTIVITY_DATA_REQUIRED", f"{ident}: unique, nonnegative activity and compatible period/boundary required.")
            continue
        candidates = [c for c in components if c["source_id"] == ident]
        # One aggregate intensity per activity avoids lifecycle-total/component overlap.
        if len(candidates) != 1:
            _gap(result, "DUPLICATE_COVERAGE", f"{ident}: supply one aggregate physical-activity factor component; reconcile overlaps separately.")
            continue
        component = candidates[0]
        metric = metrics.get(component.get("metric_id"))
        factor = factors.get(component.get("factor_id"))
        policy = component.get("policy", {})
        issues = factor_issues(factor, activity, policy, fixture_mode) if isinstance(policy, dict) else ["Factor policy required."]
        if issues:
            _gap(result, "EMISSION_FACTOR_REQUIRED", f"{ident}: {' '.join(issues)}")
            continue
        if (type(policy.get("scope3_category")) is not int or policy.get("scope3_category") != category or factor["gwp_basis"] != coverage_review.get("gwp_basis")
                or not _text(policy.get("lifecycle_boundary")) or not _text(policy.get("allocation_basis"))):
            _gap(result, "FACTOR_COVERAGE_REQUIRED", f"{ident}: category, lifecycle coverage, allocation basis and common GWP basis required.")
            continue
        numerator, denominator = [s.strip() for s in factor["unit"].split("/")]
        with localcontext() as context:
            context.prec = 34
            expected = convert(convert(activity["value"], activity["unit"], denominator)["value"] * number(factor["value"]), numerator, "kg CO2e")["value"]
            try:
                observed = convert(metric["value"], metric["unit"], "kg CO2e")["value"] if metric else None
                valid = observed is not None and serialize(observed) == serialize(expected)
            except (ValueError, TypeError):
                valid = False
            needed = set(activity["evidence_ids"] + factor["evidence_ids"])
            if (not valid or metric_counts.get(metric["id"]) != 1 or metric["period"] != activity["period"]
                    or metric["boundary_id"] != activity["boundary_id"] or metric["method"] != factor["method"]
                    or not needed <= set(metric["evidence_ids"])
                    or not {activity["id"], *factor["evidence_ids"]} <= set(metric["calculation"]["inputs"])):
                _gap(result, "COMPONENT_REQUIRED", f"{ident}: component does not match sourced activity-factor arithmetic and lineage.")
                continue
            total += observed
        refs.update(metric["evidence_ids"])
        inputs.append(metric["id"])
        accepted.append({"source_id": ident, "activity_id": activity["id"], "metric_id": metric["id"], "factor_id": factor["id"]})
    if inputs:
        result["metrics"] = [{"id": result_id + "-metric", "name": f"Scope 3 category {category} emissions subtotal", "value": serialize(total), "unit": "kg CO2e",
            "period": copy.deepcopy(state["reporting_period"]), "boundary_id": state["organizational_boundary"]["id"], "evidence_ids": sorted(refs),
            "method": {"name": "GHG Protocol scope 3 physical-activity component composition", "version": "2011 with 2013 corrections", "source": STANDARD},
            "assumption": None, "uncertainty": {"kind": "unquantified", "description": "Combined activity, lifecycle factor and allocation uncertainty is not quantified.", "value": None, "unit": None},
            "calculation": {"formula": "Sum of supported, independently covered physical-activity CO2e components", "inputs": inputs,
                            "conversions": ["Components normalized to kg CO2e; allocation already reflected in activity/factor, not reapplied"],
                            "rounding": "34-digit Decimal arithmetic; JSON serialization"}}]
    else:
        _gap(result, "COMPONENT_REQUIRED", "No supported category component; no zero inferred.")
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code": "SCOPE3_CATEGORY", "message": json.dumps({"category": category, "name": CATEGORIES[category],
        "sources": sources, "components": components, "coverage_review": coverage_review, "accepted": accepted,
        "limits": "Physical-activity composition only; category-specific factor derivation and supplied boundary judgments are not authenticated."}, sort_keys=True)})
    output = _finish(state, result, bool(inputs), fixture_mode, "Compose a sourced physical-activity scope 3 category subtotal")
    if inputs:
        output["proposal"]["state"]["ghg"]["scope_3"].append(result_id)
        validate_state(output["proposal"]["state"])
    return output
