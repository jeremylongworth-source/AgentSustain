"""Classify supplied source facts without inferring control from names or leases."""
import copy
import json

from .contract_validation import validate_state
from .data_tools import number, serialize
from .scope_accounting import GASES, _evidence, _text
from .state_proposal import propose


SKILLS = {"classify-scope-1-emissions": "scope_1", "classify-scope-2-emissions": "scope_2"}
APPROACHES = {"operational_control": "operational control", "financial_control": "financial control", "equity_share": "equity share"}


def classify_sources(state, skill, sources, result_id, fixture_mode=False):
    """Emit a common result/proposal; decisions live in SOURCE_CLASSIFICATION.

    Caller-supplied evidence-backed control/relationship assessments are checked,
    not authenticated. No numerical activity, factor, review or boundary is changed.
    """
    validate_state(state)
    if skill not in SKILLS or not _text(result_id) or not isinstance(fixture_mode, bool):
        raise ValueError("Invalid classification request")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Supply source facts")
    ids = [source.get("id") for source in sources if isinstance(source, dict)]
    if len(ids) != len(sources) or any(not _text(ident) for ident in ids) or len(set(ids)) != len(ids):
        raise ValueError("Source IDs must be unique")
    known = {item["id"] for item in state["evidence"]}
    facilities = {item["id"] for item in state["facilities"]}
    metrics = {item["id"]: item for result in state["results"] for item in result["metrics"]}
    result = {"id": result_id, "skill": skill, "contract_version": "0.1.0", "status": "completed", "review_states": ["ANALYTICAL"],
              "review_requirements": copy.deepcopy(state["review_requirements"]), "metrics": [], "evidence_ids": [],
              "assumptions": list(state["assumptions"]), "data_gaps": copy.deepcopy(state["data_gaps"]), "diagnostics": [], "next_actions": []}
    refs, decisions = set(), []

    def gap(source_id, field, reason, review=False):
        description = f"{source_id}: {reason}"
        if not any(item["field"] == field and item["reason"] == description for item in result["data_gaps"]):
            result["data_gaps"].append({"id": f"{result_id}-gap-{len(result['data_gaps'])}", "field": field, "reason": description,
                "impact": "Source classification or downstream calculation is incomplete.", "remedy": "Obtain the missing source facts and evidence; reconcile the inventory boundary before accounting."})
        if review:
            scope = f"inventory boundary for source {source_id}"
            if not any(item["status"] == "open" and item["scope"] == scope for item in result["review_requirements"]):
                result["review_requirements"].append({"id": f"{result_id}-boundary-review-{source_id}", "state": "PROFESSIONAL_REVIEW_REQUIRED",
                    "reason": reason, "scope": scope, "reviewer_role": "GHG inventory boundary specialist", "status": "open", "resolution": None})

    for source in sources:
        ident = source["id"]
        review = source.get("boundary_review", {})
        decision = {key: copy.deepcopy(source[key]) for key in ("id", "kind", "facility_id", "activity_id", "gases", "market") if key in source}
        decision.update(scope="unknown", allocation_fraction=None, allocation_applied=False,
                        boundary_approach=state["organizational_boundary"]["approach"], evidence_ids=[], rationale="Unresolved source facts.")
        decisions.append(decision)
        if not _evidence(source, known) or not _text(source.get("rationale")) or source.get("period") != state["reporting_period"]:
            gap(ident, "source facts", "Source relationship needs evidence, rationale and the reporting period.")
            continue
        refs.update(source["evidence_ids"])
        decision["evidence_ids"] = list(source["evidence_ids"])
        if source.get("facility_id") not in facilities:
            gap(ident, "facility_id", "Facility does not resolve; do not add it implicitly.", True)
            continue
        if not isinstance(review, dict) or not _evidence(review, known) or not _text(review.get("rationale")) or review.get("period") != state["reporting_period"]:
            gap(ident, "boundary_review", "Control/equity assessment requires period-specific evidence and rationale.", True)
            continue
        refs.update(review["evidence_ids"])
        decision["evidence_ids"] = sorted(set(decision["evidence_ids"] + review["evidence_ids"]))
        method = review.get("consolidation_method")
        expected = APPROACHES.get(method)
        approach = state["organizational_boundary"]["approach"].lower()
        supported = expected is not None and (approach == expected or (fixture_mode and approach == expected + " (fixture only)"))
        if review.get("approach") != state["organizational_boundary"]["approach"] or not supported:
            gap(ident, "consolidation_method", "Declared consolidation method differs from the selected boundary or is unsupported.", True)
            continue
        try:
            if method == "equity_share":
                allocation = number(review.get("equity_share"))
                if not 0 <= allocation <= 1:
                    raise ValueError("Equity share outside [0,1]")
            else:
                control = review.get(method)
                if type(control) is not bool:
                    raise ValueError("Control must be determined")
                if method == "financial_control" and review.get("joint_financial_control") is not False:
                    raise ValueError("Joint financial control needs a separately reviewed consolidation treatment")
                allocation = number(1 if control else 0)
        except ValueError:
            gap(ident, "control/equity facts", "Control or equity share is unresolved; ownership or a lease label alone does not determine it.", True)
            continue
        relationship, kind = source.get("relationship"), source.get("kind")
        if relationship not in {"direct", "purchased_consumed", "resold_energy", "upstream_energy"}:
            gap(ident, "source relationship", "Direct emission versus consumed purchased energy is not established.")
            continue
        if (relationship == "direct" and kind != "direct") or (relationship != "direct" and kind not in {"electricity", "steam", "heat", "cooling"}):
            gap(ident, "source kind", "Source kind contradicts the evidenced relationship.")
            continue
        if allocation == 0 or relationship in {"resold_energy", "upstream_energy"}:
            decision.update(scope="excluded", allocation_fraction=serialize(allocation),
                rationale="Outside this scope 1/2 source account; assess scope 3 separately. " + source["rationale"] + " " + review["rationale"])
            continue
        if source["facility_id"] not in state["organizational_boundary"]["facility_ids"]:
            gap(ident, "organizational_boundary", "Positive control/equity facts conflict with the selected facility boundary; reconcile before including.", True)
            continue
        decision.update(scope="scope_1" if relationship == "direct" else "scope_2", allocation_fraction=serialize(allocation),
                        rationale=source["rationale"] + " " + review["rationale"])
        activity = metrics.get(source.get("activity_id"))
        try:
            valid_activity = (activity is not None and activity["period"] == state["reporting_period"]
                              and activity["boundary_id"] == state["organizational_boundary"]["id"] and number(activity["value"]) >= 0)
        except ValueError:
            valid_activity = False
        if not valid_activity:
            gap(ident, "activity_id", "Classification is supported but a compatible activity metric is missing.")
        gases = source.get("gases")
        if not isinstance(gases, list) or not gases or any(not isinstance(gas, str) for gas in gases) or len(set(gases)) != len(gases) or not set(gases) <= GASES:
            gap(ident, "gas coverage", "Classification is supported but gas coverage for emissions accounting is incomplete; biogenic CO2 is separate.")
    if fixture_mode:
        assumption = "Synthetic fixture source classification only; supplied records do not establish real control."
        result["assumptions"] = list(dict.fromkeys(result["assumptions"] + [assumption]))
        result["diagnostics"].append({"code": "SYNTHETIC_FIXTURE", "message": assumption})
    resolved = [decision for decision in decisions if decision["scope"] != "unknown"]
    result["status"] = "blocked" if not resolved else ("partial" if result["data_gaps"] else "completed")
    for review in result["review_requirements"]:
        if review["status"] == "open":
            result["review_states"].append(review["state"])
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(item["remedy"] for item in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code": "SOURCE_CLASSIFICATION", "message": json.dumps({"target_scope": SKILLS[skill], "sources": decisions,
        "input_facts": sources, "limits": "Analytical classification of supplied facts; not authenticated boundary approval or scope 3 category assignment."}, sort_keys=True)})
    proposal = propose(state, result, "Classify supplied source relationships under the selected inventory boundary")
    return {"result": result, "proposal": proposal}
