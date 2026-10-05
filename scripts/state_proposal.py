"""Validate append-only analytical proposals without writing or approving state."""

import copy

from .contract_validation import validate_shape, validate_state


def propose(state, result, reason, evidence=()):
    """Return a candidate revision with preserved evidence, gaps and review ledger."""
    validate_state(state)
    validate_shape("result.schema.json", result)
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("A proposal reason is required")
    candidate = copy.deepcopy(state)
    result = copy.deepcopy(result)
    if result["id"] in {item["id"] for item in state["results"]}:
        raise ValueError("Result ID already exists; preserve history")
    known_evidence = {item["id"] for item in state["evidence"]}
    for item in evidence:
        validate_shape("evidence.schema.json", item)
        if item["id"] in known_evidence:
            raise ValueError("Evidence ID already exists; do not replace records")
        candidate["evidence"].append(copy.deepcopy(item))
        known_evidence.add(item["id"])
    reviews = {item["id"]: item for item in result["review_requirements"]}
    for item in state["review_requirements"]:
        if item["status"] == "open":
            if reviews.get(item["id"]) != item:
                raise ValueError("Outstanding review requirement omitted or changed")
            if item["state"] not in result["review_states"]:
                raise ValueError("Outstanding review state omitted")
    for item in result["review_requirements"]:
        existing = next((old for old in candidate["review_requirements"] if old["id"] == item["id"]), None)
        if existing is not None and existing != item:
            raise ValueError("Analytical proposal cannot alter a review decision")
        if existing is None:
            candidate["review_requirements"].append(copy.deepcopy(item))
    gaps = {item["id"]: item for item in result["data_gaps"]}
    for item in state["data_gaps"]:
        if gaps.get(item["id"]) != item:
            raise ValueError("Existing gap omitted or changed without reconciliation")
    if not set(state["assumptions"]) <= set(result["assumptions"]):
        raise ValueError("Existing assumption omitted")
    for metric in result["metrics"]:
        if metric["assumption"] and metric["assumption"] not in result["assumptions"]:
            raise ValueError("Metric assumption omitted from result")
    candidate["results"].append(result)
    candidate["data_gaps"] = copy.deepcopy(result["data_gaps"])
    candidate["assumptions"] = list(result["assumptions"])
    candidate["revision"] += 1
    validate_state(candidate)
    return {"base_revision": state["revision"], "reason": reason, "state": candidate}
