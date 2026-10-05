"""Shared shape and reference validation; domain fitness needs skill checks."""

import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    path.name: json.loads(path.read_text(encoding="utf-8"))
    for path in (ROOT / "schemas").glob("*.schema.json")
}
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS.values()
)


def validate_shape(name, value):
    Draft202012Validator(
        SCHEMAS[name], registry=REGISTRY, format_checker=FormatChecker()
    ).validate(value)


def validate_state(state):
    """Check shape, references, temporal order and review retention."""
    validate_shape("state.schema.json", state)

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def unique(records, label):
        ids = [record["id"] for record in records]
        require(len(ids) == len(set(ids)), f"Duplicate {label} IDs")
        return set(ids)

    def period(value):
        require(value["start"] <= value["end"], "Reversed period")

    evidence_ids = unique(state["evidence"], "evidence")
    result_ids = unique(state["results"], "result")
    facility_ids = unique(state["facilities"], "facility")
    metric_ids = unique(
        [metric for result in state["results"] for metric in result["metrics"]],
        "metric",
    )
    boundary = state["organizational_boundary"]

    def evidence_refs(refs):
        require(set(refs) <= evidence_ids, "Unresolved evidence reference")

    def review_refs(requirements):
        unique(requirements, "review requirement")
        for requirement in requirements:
            if requirement["resolution"] is not None:
                require(requirement["resolution"]["scope"] == requirement["scope"], "Review resolution scope mismatch")
                evidence_refs(requirement["resolution"]["evidence_ids"])

    unique(state["emission_factors"], "emission factor")
    for factor in state["emission_factors"]:
        evidence_refs(factor["evidence_ids"])
        require(math.isfinite(factor["value"]), "Nonfinite emission factor")

    period(state["reporting_period"])
    require(set(boundary["facility_ids"]) <= facility_ids, "Unknown boundary facility")
    evidence_refs(boundary["evidence_ids"])
    for facility in state["facilities"]:
        require(facility["jurisdiction"] in state["jurisdictions"], "Unknown jurisdiction")
    for evidence in state["evidence"]:
        period(evidence["period"])
        require(evidence["boundary_id"] == boundary["id"], "Unknown evidence boundary")
        if evidence["calculation"] is not None:
            require(
                set(evidence["calculation"]["inputs"]) <= evidence_ids | metric_ids,
                "Unresolved calculation input",
            )

    state_reviews = {item["id"]: item for item in state["review_requirements"]}
    review_refs(state["review_requirements"])
    for result in state["results"]:
        evidence_refs(result["evidence_ids"])
        review_refs(result["review_requirements"])
        for requirement in result["review_requirements"]:
            require(requirement["id"] in state_reviews, "Dropped review requirement")
            current = state_reviews[requirement["id"]]
            require(
                all(current[key] == requirement[key] for key in ("state", "scope", "reason", "reviewer_role")),
                "Review identity changed",
            )
            if requirement["status"] == "open":
                require(requirement["state"] in result["review_states"], "Missing review state")
        state_gap_ids = {item["id"] for item in state["data_gaps"]}
        require(
            all(item["id"] in state_gap_ids for item in result["data_gaps"]),
            "Dropped data gap",
        )
        require(set(result["assumptions"]) <= set(state["assumptions"]), "Dropped assumption")
        required_states = {
            item["state"] for item in result["review_requirements"] if item["status"] == "open"
        }
        for review_state in result["review_states"]:
            if review_state.endswith("_REQUIRED"):
                require(review_state in required_states, "Review state has no requirement")
        unique(result["data_gaps"], "result gap")
        for metric in result["metrics"]:
            require(metric["value"] is None or math.isfinite(metric["value"]), "Nonfinite metric")
            period(metric["period"])
            require(metric["boundary_id"] == boundary["id"], "Unknown metric boundary")
            evidence_refs(metric["evidence_ids"])
            require(set(metric["evidence_ids"]) <= set(result["evidence_ids"]), "Metric lineage omitted from result")
            require(
                set(metric["calculation"]["inputs"]) <= evidence_ids | metric_ids,
                "Unresolved calculation input",
            )

    for collection in ("energy", "water", "materials", "waste"):
        require(set(state[collection]) <= result_ids, "Unresolved domain result")
    for refs in state["ghg"].values():
        require(set(refs) <= result_ids, "Unresolved GHG result")
    for collection in ("suppliers", "targets", "risks", "opportunities", "projects"):
        unique(state[collection], collection)
        for entity in state[collection]:
            evidence_refs(entity["evidence_ids"])
    unique(state["data_gaps"], "state gap")
    unique(state["frameworks"], "framework")
    for framework in state["frameworks"]:
        if framework["effective_to"] is not None:
            require(framework["effective_from"] <= framework["effective_to"], "Reversed framework dates")

    # Shape/reference validity alone permits self-reference and indirect cycles.
    graph = {}
    for evidence in state["evidence"]:
        graph[evidence["id"]] = evidence["calculation"]["inputs"] if evidence["calculation"] else []
    for result in state["results"]:
        for metric in result["metrics"]:
            require(metric["id"] not in evidence_ids, "Evidence and metric IDs collide")
            graph[metric["id"]] = metric["calculation"]["inputs"]
    visited, active = set(), set()

    def walk(ident):
        require(ident not in active, "Calculation lineage cycle")
        if ident in visited:
            return
        active.add(ident)
        for parent in graph[ident]:
            walk(parent)
        active.remove(ident)
        visited.add(ident)

    for ident in graph:
        walk(ident)
