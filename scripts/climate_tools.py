"""Source-attributed physical hazard and geographic exposure screening, not modelling."""
import copy
from datetime import date
import json

from .contract_validation import validate_state
from .data_tools import number, period
from .finance_projects import _review
from .state_proposal import propose


OPERATIONS = {
    "identify-climate-hazards": {"hazards", "hazard_review", "result_id"},
    "map-assets-to-hazards": {"hazard_result_id", "assets", "comparisons", "mapping_review", "result_id"},
    "assess-exposure": {"mapping_result_id", "observations", "exposure_review", "result_id"},
    "assess-vulnerability": {"exposure_result_id", "rubric", "factors", "vulnerability_review", "result_id"},
    "score-physical-risk": {"vulnerability_result_id", "model", "ratings", "risk_review", "result_id"},
    "identify-adaptation-options": {"risk_result_id", "options", "adaptation_review", "result_id"},
}
CODE = {"identify-climate-hazards": "CLIMATE_HAZARDS", "map-assets-to-hazards": "ASSET_HAZARD_MAP"}
CODE.update({"assess-exposure": "CLIMATE_EXPOSURE", "assess-vulnerability": "CLIMATE_VULNERABILITY"})
CODE.update({"score-physical-risk": "PHYSICAL_RISK_SCREEN", "identify-adaptation-options": "ADAPTATION_OPTIONS"})
OPERATIONS['assess-transition-exposure'] = {'driver_results', 'subjects', 'observations', 'exposure_review', 'result_id'}
CODE['assess-transition-exposure'] = 'TRANSITION_EXPOSURE'
OPERATIONS['build-climate-risk-register'] = {'physical_results','transition_results','entries','interactions','register_review','result_id'}
CODE['build-climate-risk-register'] = 'CLIMATE_RISK_REGISTER'
for _skill, _family in [('identify-policy-risk', 'POLICY'), ('identify-market-risk', 'MARKET'),
        ('identify-technology-risk', 'TECHNOLOGY'), ('identify-reputation-risk', 'REPUTATION')]:
    OPERATIONS[_skill] = {'drivers', 'transition_review', 'result_id'}
    CODE[_skill] = 'TRANSITION_' + _family + '_DRIVERS'


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _date(value):
    if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Canonical ISO date required.")
    return date.fromisoformat(value)


def _window(value):
    if not isinstance(value, dict):
        raise ValueError("Explicit dated period required; no inferred horizon.")
    return period(value)


def _fields(row, fields, texts=()):
    if not isinstance(row, dict) or set(row) != set(fields) or any(not _text(row[f]) for f in texts):
        raise ValueError("Exact structured fields and substantive source descriptions required.")


def _sources(state, ids, refs):
    known = {e["id"]: e for e in state["evidence"]}
    if (not isinstance(ids, list) or any(not _text(i) for i in ids)
            or len(ids) != len(set(ids)) or not set(ids) <= set(known)):
        raise ValueError("Distinct current evidence IDs required.")
    refs.update(ids)
    return [copy.deepcopy(known[i]) for i in ids]


def _reviewed(state, review, refs, method):
    refs.update(_review(review, {e["id"] for e in state["evidence"]},
        ("scope", "selection_basis", "limitations", "reviewer_role")))
    if (review.get("boundary_id") != state["organizational_boundary"]["id"]
            or review.get("period") != state["reporting_period"] or review.get("method") != method
            or not isinstance(review.get("coverage_complete"), bool)
            or not isinstance(review.get("exclusions"), list)
            or any(not _text(x) for x in review["exclusions"])):
        raise ValueError("Matched boundary/reporting period, named method and explicit coverage/exclusions required.")
    when = _date(review.get("as_of_date"))
    if when < _date(state["reporting_period"]["start"]):
        raise ValueError("Review cannot predate its reporting period.")
    return when


def _support(row, sources, as_of, gap, label):
    if row["evidence_fit"] not in {"reviewed_supporting", "unverified", "irrelevant"}:
        raise ValueError("Declare reviewed_supporting, unverified or irrelevant source fitness.")
    when = _date(row["observed_date"]) if row["observed_date"] is not None else None
    if when is not None and when > as_of:
        raise ValueError("Source observation cannot postdate review.")
    supported = bool(sources) and row["evidence_fit"] == "reviewed_supporting" and when is not None
    if when and sources and any(not _date(e["period"]["start"]) <= when <= _date(e["period"]["end"]) for e in sources):
        gap(label + ": source observation does not match every selected evidence period.")
        supported = False
    if sources and any(e["source"]["version"] is None for e in sources):
        gap(label + ": hazard/location source version is unknown.")
        supported = False
    if not supported:
        gap(label + ": source applicability remains unverified; metadata and fitness do not authenticate source truth.")
    return supported


def _bounds(extent):
    if extent is None:
        return None
    _fields(extent, {"crs", "bounds", "representation", "resolution"}, ("resolution",))
    if extent["crs"] != "OGC:CRS84" or extent["representation"] != "bounding_box":
        raise ValueError("Initial screening requires explicit OGC:CRS84 longitude/latitude bounding boxes; no CRS conversion.")
    raw = extent["bounds"]
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError("Supply [west, south, east, north] in decimal degrees.")
    west, south, east, north = [number(x) for x in raw]
    if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise ValueError("Invalid or antimeridian-crossing box; specialist geometry review required.")
    return west, south, east, north


def _intersects(a, b):
    return max(a[0], b[0]) <= min(a[2], b[2]) and max(a[1], b[1]) <= min(a[3], b[3])


def _hazards(state, parameters, refs, result, gap):
    review = parameters["hazard_review"]
    as_of = _reviewed(state, review, refs, "source_hazard_register")
    raw = parameters["hazards"]
    if not isinstance(raw, list):
        raise ValueError("Explicit selected physical hazard list required.")
    rows = []; seen = set()
    for hazard in raw:
        _fields(hazard, {"id", "name", "physical_type", "mechanism", "context", "spatial_extent", "evidence_ids", "evidence_fit", "source_fragment", "observed_date", "limitations"},
            ("id", "name", "mechanism", "source_fragment", "limitations"))
        if hazard["id"] in seen or hazard["physical_type"] not in {"acute", "chronic"}:
            raise ValueError("Distinct physical hazard IDs and acute/chronic classification required; transition risks are separate.")
        seen.add(hazard["id"])
        context = hazard["context"]
        _fields(context, {"kind", "scenario", "model", "baseline_period", "horizon"})
        baseline = _window(context["baseline_period"]); horizon = _window(context["horizon"])
        if context["kind"] == "projected":
            if not _text(context["scenario"]) or not _text(context["model"]) or horizon["start"] <= baseline["end"]:
                raise ValueError("Projection requires named supplied scenario/model and horizon after its baseline; no default future climate.")
        elif context["kind"] == "observed":
            if context["scenario"] is not None or context["model"] is not None or horizon != baseline or _date(horizon["end"]) > as_of:
                raise ValueError("Historical observations cannot imply a future scenario, projection or later observation.")
        else:
            raise ValueError("Declare observed or projected climate context.")
        sources = _sources(state, hazard["evidence_ids"], refs)
        supported = _support(hazard, sources, as_of, gap, hazard["id"])
        extent = _bounds(hazard["spatial_extent"])
        if extent is None:
            gap(hazard["id"] + ": spatial extent is unknown; geography labels cannot locate hazards.")
        rows.append(dict(copy.deepcopy(hazard), sources=sources,
            source_support="reviewed_source_candidate" if supported else "unverified",
            probability=None, asset_damage=None, climate_attribution_verified=False))
    if not raw:
        gap("No hazards selected; empty register does not establish absence of climate hazards.")
    if not review["coverage_complete"] or review["exclusions"]:
        gap("Selected hazard coverage has omissions/exclusions; no complete regional or organization hazard assessment.")
    return {"hazards": rows, "hazard_review": copy.deepcopy(review),
        "review_sources": _sources(state, review["evidence_ids"], refs),
        "risk_score": None, "specialist_model_validated": False, "public_claim_authorized": False}


class ClimateFactorRequired(ValueError):
    pass


def _record(result, code):
    rows = [json.loads(d["message"]) for d in result["diagnostics"] if d["code"] == code]
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("One current reproducible climate record required.")
    return rows[0]


def _reproduce(state, ident, refs, skill="identify-climate-hazards"):
    owner = next((r for r in state["results"] if r["id"] == ident and r["skill"] == skill), None)
    if owner is None:
        raise ValueError("Current " + skill + " result required.")
    if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in owner["diagnostics"]):
        raise ClimateFactorRequired("Selected climate dependency has an unresolved emission factor.")
    if owner["status"] in {"blocked", "invalid_input"}:
        raise ValueError("Blocked climate results cannot support assessment.")
    checked, report = _execute(state, skill, _record(owner, "CLIMATE_INPUTS"))
    if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in checked["diagnostics"]):
        raise ClimateFactorRequired("Selected climate dependency has an unresolved emission factor.")
    if (checked["status"] == "blocked" or report != _record(owner, CODE[skill]) or owner["metrics"] != checked["metrics"]
            or set(owner['evidence_ids']) != set(checked['evidence_ids'])):
        raise ValueError("Climate source metadata/context changed or no longer reproduces against current state.")
    refs.update(owner["evidence_ids"])
    return report


def _mapping(state, parameters, refs, result, gap):
    source = _reproduce(state, parameters["hazard_result_id"], refs)
    review = parameters["mapping_review"]
    as_of = _reviewed(state, review, refs, "bounding_box_screen")
    if review["scope"] != source["hazard_review"]["scope"] or as_of < _date(source["hazard_review"]["as_of_date"]):
        raise ValueError("Mapping requires the same selected hazard scope and a current review date.")
    hazards = {h["id"]: h for h in source["hazards"]}
    raw = parameters["assets"]
    if not isinstance(raw, list):
        raise ValueError("Explicit asset/service/people inventory required.")
    assets = {}; support = {}
    boundary = set(state["organizational_boundary"]["facility_ids"])
    for asset in raw:
        _fields(asset, {"id", "name", "asset_type", "boundary_relation", "facility_id", "function", "owner", "location", "operating_period", "evidence_ids", "evidence_fit", "source_fragment", "observed_date", "limitations"},
            ("id", "name", "function", "owner", "source_fragment", "limitations"))
        if (asset["id"] in assets or asset["asset_type"] not in {"physical_asset", "service_dependency", "people_group", "ecosystem"}
                or asset["boundary_relation"] not in {"direct", "value_chain"}
                or (asset["boundary_relation"] == "direct" and asset["facility_id"] not in boundary)
                or (asset["boundary_relation"] == "value_chain" and asset["facility_id"] is not None)):
            raise ValueError("Distinct assets require explicit direct selected-facility or external value-chain relation; no inferred control.")
        _bounds(asset["location"])
        if asset["operating_period"] is not None:
            _window(asset["operating_period"])
        sources = _sources(state, asset["evidence_ids"], refs)
        support[asset["id"]] = _support(asset, sources, as_of, gap, asset["id"])
        assets[asset["id"]] = dict(copy.deepcopy(asset), sources=sources)
    comparisons = parameters["comparisons"]
    if not isinstance(comparisons, list):
        raise ValueError("Explicit reviewed asset/hazard pairs required; no default spatial or scenario fit.")
    rows = []; seen = set()
    for comparison in comparisons:
        _fields(comparison, {"asset_id", "hazard_id", "evidence_ids", "spatial_fit", "context_fit", "rationale"}, ("asset_id", "hazard_id", "rationale"))
        pair = comparison["asset_id"], comparison["hazard_id"]
        if pair in seen or pair[0] not in assets or pair[1] not in hazards:
            raise ValueError("Distinct known asset/hazard comparisons required.")
        seen.add(pair)
        if any(comparison[f] not in {"reviewed_supporting", "unverified", "irrelevant"} for f in ("spatial_fit", "context_fit")):
            raise ValueError("Declare spatial and climate-context fitness independently.")
        comparison_sources = _sources(state, comparison["evidence_ids"], refs)
        asset = assets[pair[0]]; hazard = hazards[pair[1]]
        if not set(asset["evidence_ids"] + hazard["evidence_ids"]) <= set(comparison["evidence_ids"]):
            raise ValueError("Pair review must reference the actual selected asset and hazard evidence.")
        a = _bounds(asset["location"]); h = _bounds(hazard["spatial_extent"])
        candidate = ("intersects_selected_boxes" if _intersects(a, h) else "outside_selected_box") if a is not None and h is not None else "unknown"
        operating = asset["operating_period"]; horizon = hazard["context"]["horizon"]
        temporal = "unknown" if operating is None else "overlapping" if max(operating["start"], horizon["start"]) <= min(operating["end"], horizon["end"]) else "not_overlapping"
        supported = (support[pair[0]] and hazard["source_support"] == "reviewed_source_candidate"
            and bool(comparison_sources) and comparison["spatial_fit"] == comparison["context_fit"] == "reviewed_supporting"
            and candidate != "unknown" and temporal != "unknown")
        status = "unverified"
        if supported:
            status = "no_documented_temporal_overlap" if temporal == "not_overlapping" else "possible_exposure_candidate" if candidate == "intersects_selected_boxes" else "outside_selected_extent_screen"
        else:
            gap(" / ".join(pair) + ": mapping source, location, scenario/horizon or operating-period fitness remains unverified.")
        if status == "possible_exposure_candidate":
            gap(" / ".join(pair) + ": bounding-box overlap needs site/dependency investigation; vulnerability and damage are unassessed.")
        rows.append(dict(copy.deepcopy(comparison), comparison_sources=comparison_sources, candidate_spatial_relation=candidate,
            temporal_relation=temporal, screening_status=status, exposure_verified=False,
            vulnerability=None, probability=None, damage=None, risk_score=None, asset_safe=False))
    for asset_id in sorted(assets):
        for hazard_id in sorted(hazards):
            if (asset_id, hazard_id) not in seen:
                gap(asset_id + " / " + hazard_id + ": selected pair omitted; exposure unknown, not absent.")
    if not raw or not hazards:
        gap("Empty selected assets or hazards cannot establish organization exposure coverage.")
    if not review["coverage_complete"] or review["exclusions"]:
        gap("Asset/hazard mapping coverage is incomplete or excludes locations/dependencies.")
    return {"hazard_snapshot": source, "assets": list(assets.values()), "comparisons": rows,
        "mapping_review": copy.deepcopy(review), "review_sources": _sources(state, review["evidence_ids"], refs),
        "specialist_model_validated": False, "implementation_authorized": False,
        "public_claim_authorized": False, "organization_safe": False}


def _execute(state, skill, parameters):
    result = {"id": parameters["result_id"], "skill": skill, "contract_version": "0.1.0", "status": "partial",
        "review_states": ["ADVISORY"], "review_requirements": copy.deepcopy(state["review_requirements"]), "metrics": [],
        "evidence_ids": [], "assumptions": list(state["assumptions"]), "data_gaps": copy.deepcopy(state["data_gaps"]),
        "diagnostics": [], "next_actions": []}
    refs = set(); report = None
    transition = skill in {'identify-policy-risk', 'identify-market-risk', 'identify-technology-risk', 'identify-reputation-risk', 'assess-transition-exposure', 'build-climate-risk-register'}
    def gap(message, code="CLIMATE_DATA_REQUIRED"):
        result["data_gaps"].append({"id": result["id"] + "-gap-" + str(len(result["data_gaps"])),
            "field": "climate_screening_basis", "reason": message,
            "impact": ("Selected transition driver is source-attributed; organization exposure, obligation and business effects remain unverified." if transition else
                "Selected hazard/exposure screening is conditional; no vulnerability, loss, safety or risk determination."),
            "remedy": ("Inspect actual transition sources and obtain qualified domain/applicability review." if transition else
                "Inspect scoped versioned hazard and asset sources and obtain qualified climate/site review.")})
        result["diagnostics"].append({"code": code, "message": message})
    try:
        if skill == 'build-climate-risk-register':
            from .climate_register import build
            report = build(state, parameters, refs, result, gap)
        elif skill == 'assess-transition-exposure':
            from .climate_transition_exposure import assess
            report = assess(state, parameters, refs, result, gap)
        elif skill in {"identify-policy-risk", "identify-market-risk", "identify-technology-risk", "identify-reputation-risk"}:
            from .climate_transition import identify
            report = identify(state, skill, parameters, refs, result, gap)
        elif skill in {"score-physical-risk", "identify-adaptation-options"}:
            from .climate_risk import score, adaptation
            report = (score if skill == "score-physical-risk" else adaptation)(state, parameters, refs, result, gap)
        elif skill in {"assess-exposure", "assess-vulnerability"}:
            from .climate_assessment import exposure, vulnerability
            report = (exposure if skill == "assess-exposure" else vulnerability)(state, parameters, refs, result, gap)
        else:
            report = (_hazards if skill == "identify-climate-hazards" else _mapping)(state, parameters, refs, result, gap)
        result["review_requirements"].append({"id": result["id"] + "-climate-review", "state": "PROFESSIONAL_REVIEW_REQUIRED",
            "reason": ("Review transition-source status, applicability, segment/service/group coverage, scenario/horizon and organizational pathways; source candidates do not establish obligations, losses or risk acceptance." if transition else
                "Review source applicability, scenario/horizon, spatial resolution and site/dependency conditions; screening does not establish vulnerability, damage or safety."),
            "scope": report[{"identify-climate-hazards": "hazard_review", "map-assets-to-hazards": "mapping_review",
                "assess-exposure": "exposure_review", "assess-vulnerability": "vulnerability_review",
                "score-physical-risk": "risk_review", "identify-adaptation-options": "adaptation_review",
                "assess-transition-exposure": "exposure_review", "build-climate-risk-register": "register_review"}.get(skill, "transition_review")]["scope"],
            "reviewer_role": ("Qualified transition-risk domain specialist and legal/applicability reviewer where relevant, with accountable owner" if transition else
                "Qualified climate-risk and site/dependency specialist with accountable owner"), "status": "open", "resolution": None})
        result["diagnostics"].append({"code": CODE[skill], "message": json.dumps(report, sort_keys=True)})
        result["status"] = "partial" if result["data_gaps"] else "completed"
    except (ValueError, TypeError, KeyError) as error:
        result["metrics"] = []
        gap(str(error), "EMISSION_FACTOR_REQUIRED" if isinstance(error, ClimateFactorRequired) else "CLIMATE_DATA_REQUIRED")
        result["status"] = "blocked"
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code": "CLIMATE_INPUTS", "message": json.dumps(parameters, sort_keys=True)})
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"] == "open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    return result, report


def run_climate(state, skill, parameters):
    validate_state(state)
    if skill not in OPERATIONS or not isinstance(parameters, dict) or set(parameters) != OPERATIONS[skill] or not _text(parameters["result_id"]):
        raise ValueError("Supported climate operation with exact parameters and fresh result ID required.")
    result, _ = _execute(state, skill, parameters)
    return {"result": result, "proposal": propose(state, result, "Record source-attributed climate hazard/exposure candidates without modelling, decisions or claims")}
