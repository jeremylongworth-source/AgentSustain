"""Compose evidenced, pre-calculated CO2e components into separate scope accounts.

Coverage and quality records are supplied assessments, not authenticated reviews.
"""
import copy
from decimal import Decimal, localcontext
import json

from .contract_validation import validate_state
from .data_tools import convert, number, serialize
from .ghg_foundation import factor_issues
from .state_proposal import propose


METHODS = {
    "calculate-scope-1": ("scope_1", "direct"),
    "calculate-location-based-scope-2": ("scope_2", "location"),
    "calculate-market-based-scope-2": ("scope_2", "market"),
}
GASES = {"CO2", "CH4", "N2O", "HFCs", "PFCs", "SF6", "NF3"}
GUIDANCE = "https://ghgprotocol.org/sites/default/files/2023-03/Scope%202%20Guidance.pdf"
CORPORATE = "https://ghgprotocol.org/sites/default/files/standards/ghg-protocol-revised.pdf"


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _evidence(record, known):
    refs = record.get("evidence_ids")
    return (isinstance(refs, list) and bool(refs) and all(_text(ref) for ref in refs)
            and len(refs) == len(set(refs)) and set(refs) <= known)


def _quality(record, source, fraction, activity, known, claim_ids):
    """Return issues for electricity contracts or explicit hierarchy fallbacks."""
    issues = []
    category = record.get("category")
    if category not in {"certificate", "supplier", "direct_contract", "residual_mix", "grid_fallback"}:
        return ["Supply a recognized market factor category."]
    if not _evidence(record, known) or not _text(record.get("rationale")):
        issues.append("Market coverage requires source evidence and rationale.")
    if record.get("period") != activity["period"] or record.get("market") != source.get("market") or not _text(source.get("market")):
        issues.append("Market and consumption period must match the supplied coverage record.")
    try:
        matched = convert(record.get("matched_quantity"), record.get("unit"), activity["unit"])["value"]
        if matched < 0 or matched != number(activity["value"]) * fraction:
            issues.append("Matched energy does not equal the declared consumption partition.")
    except (ValueError, TypeError):
        issues.append("Matched energy needs compatible, finite quantities and units.")
    if category in {"residual_mix", "grid_fallback"}:
        if record.get("hierarchy_reviewed") is not True or not _text(record.get("higher_priority_unavailable")):
            issues.append("Fallback needs an evidenced hierarchy assessment.")
        if category == "grid_fallback" and (record.get("residual_mix_available") is not False or not _text(record.get("absence_disclosure"))):
            issues.append("Grid fallback needs explicit residual-mix absence and disclosure.")
        if category == "residual_mix" and record.get("residual_mix_available") is not True:
            issues.append("A residual mix must be supplied, not manufactured.")
        return issues
    claim = record.get("claim_id")
    if not _text(claim) or claim in claim_ids:
        issues.append("Contract claim IDs must be unique in this account.")
    else:
        claim_ids.add(claim)
    if record.get("beneficiary") != source.get("organization_id"):
        issues.append("Contract beneficiary must match the reporting organization.")
    criteria = record.get("criteria")
    if (not isinstance(criteria, list) or len(criteria) != 8
            or any(not isinstance(item, dict) or type(item.get("criterion")) is not int for item in criteria)
            or {item["criterion"] for item in criteria} != set(range(1, 9))):
        return issues + ["Supply separate records for all eight quality criteria."]
    for criterion in criteria:
        ident = criterion["criterion"]
        applicable = ident not in (6, 7) or (ident == 6 and category == "supplier") or (ident == 7 and category == "direct_contract")
        expected = "met" if applicable else "not_applicable"
        if criterion.get("status") != expected or not _text(criterion.get("rationale")) or not _evidence(criterion, known):
            issues.append(f"Quality criterion {ident} needs a supported {expected} assessment.")
    return issues


def compose_scope(state, skill, sources, components, coverage_review, result_id, fixture_mode=False):
    """Return one total/subtotal and a proposal; never sum scope 2 alternatives.

    Components reference existing unallocated CO2e metrics. Their arithmetic is
    rechecked against resolved activity and factor; allocation is applied once.
    Unsupported components are omitted with gaps, never counted as zero.
    """
    validate_state(state)
    if skill not in METHODS or not _text(result_id) or not isinstance(fixture_mode, bool):
        raise ValueError("Invalid scope method, result ID or fixture mode")
    if not isinstance(sources, list) or not sources or not isinstance(components, list) or not isinstance(coverage_review, dict):
        raise ValueError("Source register, components and coverage review are required")
    scope, method = METHODS[skill]
    known = {item["id"] for item in state["evidence"]}
    metrics = {item["id"]: item for result in state["results"] for item in result["metrics"]}
    factors = {item["id"]: item for item in state["emission_factors"]}
    result = {"id": result_id, "skill": skill, "contract_version": "0.1.0", "status": "completed",
              "review_states": ["ANALYTICAL"], "review_requirements": copy.deepcopy(state["review_requirements"]),
              "metrics": [], "evidence_ids": [], "assumptions": list(state["assumptions"]),
              "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}
    for review in result["review_requirements"]:
        if review["status"] == "open":
            result["review_states"].append(review["state"])
    refs, inputs, conversions, accepted = set(), [], [], []

    def gap(code, message):
        result["data_gaps"].append({"id": f"{result_id}-gap-{len(result['data_gaps'])}", "field": "scope_coverage",
                                   "reason": message, "impact": "Scope total is incomplete or unavailable.",
                                   "remedy": "Reconcile source coverage, classification, factors and eligibility with supporting records."})
        result["diagnostics"].append({"code": code, "message": message})

    if coverage_review.get("confirmed") is not True or not _text(coverage_review.get("rationale")) or not _evidence(coverage_review, known):
        gap("COVERAGE_REVIEW_REQUIRED", "Source register completeness and nonoverlap require an evidenced assessment.")
    else:
        refs.update(coverage_review["evidence_ids"])
    source_map = {}
    for source in sources:
        if not isinstance(source, dict) or not _text(source.get("id")) or source["id"] in source_map:
            raise ValueError("Source IDs must be unique")
        source_map[source["id"]] = source
    if any(not isinstance(c, dict) or c.get("source_id") not in source_map for c in components):
        raise ValueError("Component source does not resolve")
    activity_owners = {}
    for source in sources:
        if source.get("scope") == scope:
            activity_owners.setdefault(source.get("activity_id"), []).append(source["id"])
    duplicate_sources = {ident for owners in activity_owners.values() if len(owners) > 1 for ident in owners}
    metric_counts, claim_counts = {}, {}
    for component in components:
        ident = component.get("metric_id")
        metric_counts[ident] = metric_counts.get(ident, 0) + 1
        review = component.get("market_review", {})
        if method == "market" and isinstance(review, dict) and review.get("category") in {"certificate", "supplier", "direct_contract"}:
            claim = review.get("claim_id")
            claim_counts[claim] = claim_counts.get(claim, 0) + 1
    seen_metrics, claim_ids = set(), set()
    total = Decimal(0)
    for source_id, source in source_map.items():
        eligible = source.get("scope") == scope
        if source.get("scope") not in {"scope_1", "scope_2", "excluded"}:
            gap("CLASSIFICATION_REQUIRED", f"Source {source_id} has unresolved classification.")
            continue
        if not _evidence(source, known) or not _text(source.get("rationale")):
            gap("CLASSIFICATION_REQUIRED", f"Source {source_id} requires classification evidence and rationale.")
            continue
        refs.update(source["evidence_ids"])
        if not eligible:
            if any(c["source_id"] == source_id for c in components):
                gap("SCOPE_MISMATCH", f"Components for {source_id} do not belong to this scope account.")
            continue
        if source_id in duplicate_sources:
            gap("DUPLICATE_COVERAGE", f"Source {source_id} repeats another source's activity; reconcile register before counting either.")
            continue
        try:
            allocation = number(source.get("allocation_fraction"))
            gases = source.get("gases")
            if not 0 < allocation <= 1 or source.get("allocation_applied") is not False:
                raise ValueError("Allocation must be explicit and not already applied")
            if source.get("boundary_approach") != state["organizational_boundary"]["approach"]:
                raise ValueError("Consolidation approach differs")
            if allocation != 1 and not source["boundary_approach"].lower().startswith("equity share"):
                raise ValueError("Partial consolidation requires an equity-share basis")
            if source.get("facility_id") not in state["organizational_boundary"]["facility_ids"]:
                raise ValueError("Facility is outside selected boundary")
            if source.get("kind") not in ({"direct"} if scope == "scope_1" else {"electricity", "steam", "heat", "cooling"}):
                raise ValueError("Source type differs from scope")
            if not isinstance(gases, list) or not gases or len(gases) != len(set(gases)) or not set(gases) <= GASES:
                raise ValueError("Explicit non-biogenic gas coverage required")
            activity = metrics[source["activity_id"]]
            if activity["period"] != state["reporting_period"] or activity["boundary_id"] != state["organizational_boundary"]["id"] or number(activity["value"]) < 0:
                raise ValueError("Activity context mismatch")
            if scope == "scope_2":
                convert(activity["value"], activity["unit"], "kWh")
        except (ValueError, KeyError, TypeError):
            gap("SOURCE_CONTEXT_REQUIRED", f"Source {source_id} has unsupported boundary, activity, allocation or gas coverage.")
            continue
        coverage = {gas: Decimal(0) for gas in gases}
        source_components = [c for c in components if c["source_id"] == source_id]
        # Preflight coverage before accepting any numeric contribution.
        try:
            for component in source_components:
                fraction = number(component.get("activity_fraction"))
                cgases = component.get("gases")
                if not 0 < fraction <= 1 or not isinstance(cgases, list) or not cgases or len(cgases) != len(set(cgases)) or not set(cgases) <= set(gases):
                    raise ValueError("Invalid component coverage")
                if scope == "scope_1" and fraction != 1:
                    raise ValueError("Direct components require full activity coverage")
                if scope == "scope_2" and set(cgases) != set(gases):
                    raise ValueError("Energy partitions require matching gas coverage")
                for gas in cgases:
                    coverage[gas] += fraction
            if any(value > 1 for value in coverage.values()):
                raise ValueError("Overlapping coverage")
        except (ValueError, TypeError):
            gap("DUPLICATE_COVERAGE", f"Source {source_id} has duplicate or invalid component coverage; no components counted.")
            continue
        successful = {gas: Decimal(0) for gas in gases}
        for component in source_components:
            metric = metrics.get(component.get("metric_id"))
            factor = factors.get(component.get("factor_id"))
            policy = component.get("policy", {})
            issues = factor_issues(factor, activity, policy, fixture_mode) if isinstance(policy, dict) else ["Factor policy is missing."]
            if issues:
                gap("EMISSION_FACTOR_REQUIRED", f"Source {source_id}: {' '.join(issues)}")
                continue
            if factor["gwp_basis"] != coverage_review.get("gwp_basis"):
                gap("GWP_BASIS_MISMATCH", f"Source {source_id} factor differs from the declared account GWP basis.")
                continue
            if (policy.get("activity_kind") != source["kind"] or policy.get("gas_coverage") != component["gases"]
                    or policy.get("scope_basis") != (component.get("market_review", {}).get("category") if method == "market" else method)):
                gap("FACTOR_COVERAGE_REQUIRED", f"Source {source_id} needs an explicit factor coverage record matching energy/source type, gases and method category.")
                continue
            fraction = number(component["activity_fraction"])
            if method == "location" and component.get("basis") != "location":
                gap("METHOD_MISMATCH", f"Source {source_id} requires a geographic location factor basis.")
                continue
            if scope == "scope_2" and source["kind"] != "electricity":
                thermal = component.get("thermal_review", {})
                if (not isinstance(thermal, dict) or not _evidence(thermal, known) or not _text(thermal.get("rationale"))
                        or thermal.get("method") != {"name": "Scope 2 Guidance appendix A", "version": "2015", "source": GUIDANCE}
                        or thermal.get("factor_id") != factor["id"] or thermal.get("energy_type") != source["kind"]
                        or thermal.get("generation_only") is not True or not _text(thermal.get("allocation_and_losses"))):
                    gap("SPECIALIST_METHOD_REQUIRED", f"Source {source_id} requires evidenced appendix A derived-factor allocation and loss treatment.")
                    continue
                refs.update(thermal["evidence_ids"])
            if method == "market":
                record = component.get("market_review", {})
                if source["kind"] != "electricity" and isinstance(record, dict) and record.get("category") not in {"supplier", "direct_contract"}:
                    gap("SPECIALIST_METHOD_REQUIRED", f"Source {source_id} needs a thermal supplier/direct-contract factor, not an electricity certificate or grid fallback.")
                    continue
                if isinstance(record, dict) and claim_counts.get(record.get("claim_id"), 0) > 1:
                    gap("DUPLICATE_CLAIM", f"Source {source_id} repeats a contractual claim; no repeated claim counted.")
                    continue
                source_context = dict(source, organization_id=state["organization"]["id"])
                issues = _quality(record, source_context, fraction, activity, known, claim_ids) if isinstance(record, dict) else ["Missing market review."]
                if issues:
                    gap("CONTRACT_QUALITY_REQUIRED", f"Source {source_id}: {' '.join(issues)}")
                    continue
                refs.update(record["evidence_ids"])
                for criterion in record.get("criteria", []):
                    refs.update(criterion["evidence_ids"])
                result["diagnostics"].append({"code": "MARKET_COVERAGE", "message": json.dumps(record, sort_keys=True)})
            if metric is None or metric["id"] in seen_metrics or metric_counts.get(metric["id"], 0) > 1:
                gap("COMPONENT_REQUIRED", f"Source {source_id} needs a unique resolved CO2e component metric.")
                continue
            numerator, denominator = [part.strip() for part in factor["unit"].split("/")]
            with localcontext() as context:
                context.prec = 34
                expected = convert(convert(activity["value"], activity["unit"], denominator)["value"] * number(factor["value"]), numerator, "kg CO2e")["value"]
                try:
                    observed = convert(metric["value"], metric["unit"], "kg CO2e")["value"]
                    # Compare serialized arithmetic, avoiding Decimal/JSON representation noise.
                    valid = serialize(observed) == serialize(expected)
                except (ValueError, TypeError):
                    valid = False
                needed = set(activity["evidence_ids"] + factor["evidence_ids"])
                if (not valid or metric["period"] != activity["period"] or metric["boundary_id"] != activity["boundary_id"]
                        or not needed <= set(metric["evidence_ids"]) or metric["method"] != factor["method"]
                        or not {activity["id"], *factor["evidence_ids"]} <= set((metric["calculation"] or {}).get("inputs", []))):
                    gap("COMPONENT_REQUIRED", f"Source {source_id} component arithmetic, context or lineage does not match the supplied factor/activity.")
                    continue
                amount = observed * fraction * allocation
                total += amount
            seen_metrics.add(metric["id"])
            refs.update(metric["evidence_ids"])
            inputs.append(metric["id"])
            conversions.append(f"{metric['id']}: {metric['unit']} -> kg CO2e; activity fraction {fraction}; consolidation allocation {allocation}, applied once")
            accepted.append({"source_id": source_id, "metric_id": metric["id"], "activity_fraction": serialize(fraction), "allocation_fraction": serialize(allocation), "gases": component["gases"]})
            for gas in component["gases"]:
                successful[gas] += fraction
        if any(value != 1 for value in successful.values()):
            gap("INCOMPLETE_SCOPE_COVERAGE", f"Source {source_id} has uncovered or unsupported gas/activity portions.")
    if fixture_mode:
        assumption = "Synthetic fixture scope account only; not a real inventory."
        result["assumptions"] = list(dict.fromkeys(result["assumptions"] + [assumption]))
        result["diagnostics"].append({"code": "SYNTHETIC_FIXTURE", "message": assumption})
    if inputs:
        result["metrics"] = [{"id": result_id + "-metric", "name": f"{scope} {method} emissions subtotal", "value": serialize(total), "unit": "kg CO2e",
            "period": copy.deepcopy(state["reporting_period"]), "boundary_id": state["organizational_boundary"]["id"], "evidence_ids": sorted(refs),
            "method": {"name": f"GHG Protocol {scope} {method} composition", "version": "2004" if scope == "scope_1" else "2015",
                       "source": CORPORATE if scope == "scope_1" else GUIDANCE}, "assumption": assumption if fixture_mode else None,
            "uncertainty": {"kind": "unquantified", "description": "Combined component and allocation uncertainty has not been quantified.", "value": None, "unit": None},
            "calculation": {"formula": "Sum of accepted component CO2e * activity fraction * consolidation allocation", "inputs": list(dict.fromkeys(inputs + sorted(refs))),
                            "conversions": conversions, "rounding": "34-digit Decimal component arithmetic; JSON number serialization"}}]
    else:
        gap("COMPONENT_REQUIRED", "No supported emissions components were available; no zero total inferred.")
    result["status"] = "blocked" if not inputs else ("partial" if result["data_gaps"] else "completed")
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(item["remedy"] for item in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code": "SCOPE_METHOD", "message": json.dumps({"scope": scope, "method": method, "accepted": accepted,
        "coverage_review": coverage_review, "sources": sources, "components": components,
        "limitations": "Supplied source and criterion assessments are not authenticated; alternative scope 2 accounts must not be summed."}, sort_keys=True)})
    proposal = propose(state, result, "Compose a separate scope account with retained evidence and review obligations")
    if inputs:
        proposal["state"]["ghg"][scope].append(result_id)
        validate_state(proposal["state"])
    return {"result": result, "proposal": proposal}
