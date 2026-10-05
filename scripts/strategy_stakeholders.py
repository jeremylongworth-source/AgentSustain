"""Source-attributed stakeholder interests and unsent engagement follow-ups."""
import copy
from datetime import date
import re

from .finance_projects import _review
from .strategy_tools import _reviewed, _text


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Canonical ISO observation and follow-up dates required; unknown observation dates may be null.")
    return date.fromisoformat(value)


def map_stakeholders(state, parameters, refs, result, gap):
    known = {e["id"]: e for e in state["evidence"]}
    review = parameters["mapping_review"]
    _reviewed(state, review, refs, ("scope", "identification_method", "engagement_purpose", "inclusion_basis"))
    if review.get("period") != state["reporting_period"] or not isinstance(review.get("coverage_complete"), bool):
        raise ValueError("Explicit mapping period and selected coverage required.")
    as_of = _date(review.get("as_of_date"))
    if as_of < _date(review["period"]["start"]):
        raise ValueError("Mapping review cannot predate the selected period.")
    exclusions = review.get("exclusions")
    if not isinstance(exclusions, list):
        raise ValueError("Explicit stakeholder exclusions required, including an empty list where none are proposed.")
    for item in exclusions:
        if (not isinstance(item, dict) or set(item) != {"group", "reason", "basis", "evidence_ids"}
                or not _text(item["group"]) or not _text(item["reason"]) or item["basis"] not in {"outside_scope", "unresolved"}):
            raise ValueError("Exclusions require group, reason, outside-scope/unresolved basis and source records.")
        if item["basis"] == "outside_scope":
            refs.update(_review(dict(item, confirmed=True), set(known), ()))
        else:
            evidence(item["evidence_ids"], known, refs)
            gap("Stakeholder exclusion for " + item["group"] + " remains unresolved; absence of influence or participation is not exclusion evidence.")
    groups = parameters["stakeholders"]
    if not isinstance(groups, list) or not groups:
        raise ValueError("Nonempty explicit stakeholder register required.")
    ids = set(); perspective_ids = set(); rows = []; topics = {}; fragments = {}
    for group in groups:
        fields = {"id", "name", "relationship", "affected_status", "impact_description", "relationship_evidence_ids", "evidence_fit", "perspectives", "barriers", "barrier_assessment", "engagement_status", "engagement_evidence_ids", "follow_up"}
        if (not isinstance(group, dict) or set(group) != fields or any(not _text(group[f]) for f in ("id", "name", "relationship", "impact_description", "barrier_assessment"))
                or group["id"] in ids or group["affected_status"] not in {"actual", "potential", "unknown"}
                or group["evidence_fit"] not in {"reviewed_supporting", "proxy", "unverified"}
                or group["engagement_status"] not in {"not_started", "planned", "recorded", "unverified"}):
            raise ValueError("Distinct sourced groups need explicit relationships, affected-interest status, fit and engagement status.")
        ids.add(group["id"])
        evidence(group["relationship_evidence_ids"], known, refs)
        relation_supported = bool(group["relationship_evidence_ids"]) and group["evidence_fit"] == "reviewed_supporting" and group["affected_status"] != "unknown"
        if not relation_supported:
            gap("Affected-interest relationship for " + group["id"] + " is unknown, proxied or unverified; no finding inferred.")
        barriers = group["barriers"]
        if barriers is None:
            gap("Engagement barriers for " + group["id"] + " are unassessed; do not infer there are none.")
        elif not isinstance(barriers, list):
            raise ValueError("Barriers are an explicit reviewed list or null when unknown.")
        else:
            for barrier in barriers:
                if (not isinstance(barrier, dict) or set(barrier) != {"description", "status", "evidence_ids"}
                        or not _text(barrier["description"]) or barrier["status"] not in {"supported", "unverified"}):
                    raise ValueError("Barrier statements require explicit support status and evidence.")
                evidence(barrier["evidence_ids"], known, refs)
                if barrier["status"] == "supported" and not barrier["evidence_ids"]:
                    raise ValueError("Supported barriers require actual source records.")
                if barrier["status"] == "unverified":
                    gap("Barrier for " + group["id"] + " is unverified; preserve it for source review.")
        evidence(group["engagement_evidence_ids"], known, refs)
        if group["engagement_status"] == "recorded" and not group["engagement_evidence_ids"]:
            raise ValueError("Recorded engagement requires an actual engagement source, not a planned follow-up.")
        if group["engagement_status"] != "recorded":
            gap("Engagement with " + group["id"] + " is " + group["engagement_status"] + "; no consultation completed by this workflow.")
        perspectives = group["perspectives"]
        if not isinstance(perspectives, list):
            raise ValueError("Explicit perspective register required; no response can be represented as an empty list.")
        if not perspectives:
            gap("No attributed perspective for " + group["id"] + "; silence is not agreement or absence of impacts.")
        statements = []
        for item in perspectives:
            fields = {"id", "issue", "statement", "origin", "speaker_scope", "representativeness", "observed_date", "evidence_ids", "source_fragment", "evidence_fit", "representation_review"}
            if (not isinstance(item, dict) or set(item) != fields or any(not _text(item[f]) for f in ("id", "issue", "statement", "speaker_scope", "representativeness", "source_fragment"))
                    or item["id"] in perspective_ids or item["origin"] not in {"direct", "representative", "proxy", "unknown"}
                    or item["evidence_fit"] not in {"reviewed_supporting", "unverified", "irrelevant"}):
                raise ValueError("Globally distinct perspectives require source attribution, fit, speaker scope and representativeness limits.")
            perspective_ids.add(item["id"]); evidence(item["evidence_ids"], known, refs)
            period_fit = "within_mapping_period"
            if item["observed_date"] is None:
                period_fit = "unknown"
                gap("Observation date for " + item["id"] + " is unknown; source access date is not a substitute.")
            else:
                observed = _date(item["observed_date"])
                if observed > min(_date(review["period"]["end"]), as_of):
                    raise ValueError("Perspective postdates the mapped reporting period or review as-of date.")
                if observed < _date(review["period"]["start"]):
                    period_fit = "historical"
                    gap("Perspective " + item["id"] + " is historical to this mapping period; current applicability needs review.")
            supporting = bool(item["evidence_ids"]) and item["evidence_fit"] == "reviewed_supporting"
            if item["origin"] == "representative":
                representation = item["representation_review"]
                if representation is not None:
                    refs.update(_review(representation, set(known), ("representation_basis", "represented_scope", "rationale")))
                if representation is None:
                    supporting = False; gap("Representation mandate for " + item["id"] + " is unverified; a job title does not establish it.")
                elif representation["represented_scope"] != item["speaker_scope"]:
                    raise ValueError("Reviewed representation scope must match the attributed speaker scope.")
            elif item["representation_review"] is not None:
                raise ValueError("Only explicitly representative sources carry a representation review.")
            attributable = supporting and relation_supported and item["origin"] in {"direct", "representative"}
            if not attributable:
                gap("Perspective " + item["id"] + " is proxy, unknown, irrelevant or unverified; do not attribute it as the group's expressed position.")
            for ident in item["evidence_ids"]:
                fragments.setdefault((ident, item["source_fragment"]), []).append(item["id"])
            topics.setdefault(item["issue"], []).append({"group_id": group["id"], "perspective_id": item["id"], "origin": item["origin"], "attributed_source_supported": attributable})
            statements.append({"source_record": copy.deepcopy(item), "attributed_source_supported": attributable,
                "period_fit": period_fit, "current_position_verified": False,
                "support_basis": "Supplied source/mandate review; not independently authenticated or group consensus.",
                "source_context": [copy.deepcopy(known[e]) for e in item["evidence_ids"]]})
        follow = group["follow_up"]
        if (not isinstance(follow, dict) or set(follow) != {"owner", "target_date", "purpose"}
                or not _text(follow["owner"]) or not _text(follow["purpose"]) or _date(follow["target_date"]) <= _date(review["period"]["end"])):
            raise ValueError("Named owned follow-up after the mapping period required; no communication is sent.")
        overdue = _date(follow["target_date"]) < as_of
        if overdue:
            gap("Follow-up for " + group["id"] + " predates mapping review; completion is unverified, not inferred.")
        rows.append({"stakeholder": copy.deepcopy(group), "relationship_support": "supplied_review" if relation_supported else "unresolved",
            "perspectives": statements, "group_consensus": None, "engagement_verified": False,
            "follow_up_status": "overdue_unverified" if overdue else "proposed_unsent", "contact_authorized": False})
    shared = [{"evidence_id": key[0], "source_fragment": key[1], "perspective_ids": values} for key, values in fragments.items() if len(values) > 1]
    if shared:
        gap("Shared source fragments occur across perspectives; these are not independent voices or votes.")
    if not review["coverage_complete"]:
        gap("Selected stakeholder coverage is incomplete; absent groups and perspectives need further identification.")
    gate = result["id"] + "-stakeholder-review"
    while any(r["id"] == gate for r in result["review_requirements"]):
        gate += "-next"
    result["review_requirements"].append({"id": gate, "state": "PROFESSIONAL_REVIEW_REQUIRED", "reason": "Review affected-group inclusion, voice/proxy attribution, representation, engagement barriers and coverage before strategy or materiality use.",
        "scope": review["scope"], "reviewer_role": "Accountable stakeholder-engagement and sustainability reviewer", "status": "open", "resolution": None})
    return {"mapping_review": copy.deepcopy(review), "stakeholders": rows, "issue_perspectives": topics, "shared_source_fragments": shared,
        "coverage_verified": False, "stakeholder_importance_ranking": None, "materiality_determination": None,
        "engagement_completed_by_workflow": False, "contact_authorized": False, "public_claim_authorized": False,
        "limits": "Selected sourced register, not proof of consultation, consensus, representative coverage, impact truth, rights/legal status or materiality. Proxy and silence remain separate from expressed affected-group views."}


def evidence(values, known, refs):
    if (not isinstance(values, list) or any(not _text(e) for e in values) or len(values) != len(set(values)) or not set(values) <= set(known)):
        raise ValueError("Distinct known evidence references required; missing evidence may be explicitly empty.")
    refs.update(values)
