"""Compose bounded domain analyses and propose owned operational candidates."""
import copy
from datetime import date
import json

from .contract_validation import validate_state
from .energy_tools import OPERATIONS as ENERGY, run_energy
from .water_tools import OPERATIONS as WATER, run_water
from .resource_tools import OPERATIONS as RESOURCES, run_resources
from .finance_tools import OPERATIONS as FINANCE, run_finance
from .finance_projects import _basis, _review
from .ghg_foundation import calculate_result
from .scope_accounting import METHODS as SCOPE_METHODS, compose_scope
from .run_scope3 import OPERATIONS as INVENTORY_OPERATIONS
from .state_proposal import propose


CARBON_PARAMETERS = {
    "calculate-co2e":{"activity_id","factor_id","policy","result_id"},
    **{k:{"sources","components","coverage_review","result_id"} for k in SCOPE_METHODS},
    **{k:required for k,(_,required) in INVENTORY_OPERATIONS.items()},
}


def _run_carbon(state, skill, parameters):
    required = CARBON_PARAMETERS[skill]
    if not required <= set(parameters) or set(parameters)-required-{"fixture_mode"}:
        raise ValueError("Exact carbon helper parameters and optional explicit fixture_mode required.")
    if skill == "calculate-co2e": return calculate_result(state,**parameters)
    if skill in SCOPE_METHODS: return compose_scope(state,skill,**parameters)
    return INVENTORY_OPERATIONS[skill][0](state,**parameters)


RUNNERS = {**{k:run_energy for k in ENERGY}, **{k:run_water for k in WATER},
           **{k:run_resources for k in RESOURCES}, **{k:run_finance for k in FINANCE},
           **{k:_run_carbon for k in CARBON_PARAMETERS}}
INTERPRETATIONS = {
    "energy":{"analyze-energy-usage","identify-efficiency-opportunities"},
    "water":{"assess-water-dependency","identify-water-efficiency-opportunities"},
    "waste":{"classify-waste-streams","identify-waste-reduction-opportunities"},
    "materials":{"identify-resource-efficiency-opportunities"},
}


def _action_sequence(actions):
    """Validate proposed precedence without treating scheduled work as completed."""
    identified = [a for a in actions if "id" in a]
    if not identified: return None
    if len(identified) != len(actions):
        raise ValueError("Dependency planning requires IDs and depends_on for every selected action.")
    ids = [a["id"] for a in actions]
    if any(not isinstance(i,str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("Action IDs must be nonempty and unique across the selected plan.")
    records = {a["id"]:a for a in actions}
    for action in actions:
        dependencies = action["depends_on"]
        if (not isinstance(dependencies,list) or any(not isinstance(i,str) for i in dependencies)
                or len(dependencies) != len(set(dependencies))
                or not set(dependencies) <= set(ids)-{action["id"]}):
            raise ValueError("Action dependencies must identify other selected actions once.")
        for dependency in dependencies:
            source = records[dependency]
            if date.fromisoformat(source["target_date"]) > date.fromisoformat(action["target_date"]):
                raise ValueError("A prerequisite target date cannot follow its dependent action.")
    pending = set(ids); ordered = []
    while pending:
        ready = sorted((i for i in pending if not set(records[i]["depends_on"]) & pending),
                       key=lambda i:(records[i]["target_date"],i))
        if not ready: raise ValueError("Proposed action dependencies contain a cycle.")
        ordered.extend(ready);pending.difference_update(ready)
    return {"action_ids":ordered,"basis":"Declared prerequisite graph; dates break ties only, not investment priority.",
            "completion_verified":False,"implementation_authorized":False}


def run_operations(state, parameters):
    validate_state(state)
    if not isinstance(parameters,dict) or set(parameters) != {"steps","opportunities","planning_review","result_id"}:
        raise ValueError("Exact operations composition parameters required.")
    ident = parameters["result_id"]
    if not isinstance(ident,str) or not ident.strip(): raise ValueError("Result ID required.")
    steps = parameters["steps"]
    if not isinstance(steps,list) or not steps or any(not isinstance(s,dict) or set(s) != {"skill","parameters"}
            or not isinstance(s["skill"],str) or s["skill"] not in RUNNERS or not isinstance(s["parameters"],dict) for s in steps):
        raise ValueError("Nonempty ordered allowlisted analytical steps required; arbitrary code and recursive composition are unsupported.")
    ids = [s["parameters"].get("result_id") for s in steps]+[ident]
    if (any(not isinstance(i,str) or not i.strip() for i in ids) or len(ids) != len(set(ids))
            or set(ids) & {r["id"] for r in state["results"]}):
        raise ValueError("Fresh distinct result IDs required for every step and composition.")
    working = copy.deepcopy(state); trace = []
    for step in steps:
        output = RUNNERS[step["skill"]](working,step["skill"],step["parameters"])
        working = output["proposal"]["state"]
        trace.append({"skill":step["skill"],"parameters":copy.deepcopy(step["parameters"]),
            "result_id":output["result"]["id"],"status":output["result"]["status"],"diagnostics":output["result"]["diagnostics"]})
    result = {"id":ident,"skill":"sustainable-operations","contract_version":"0.1.0","status":"completed","review_states":["ANALYTICAL"],
        "review_requirements":copy.deepcopy(working["review_requirements"]),"metrics":[],"evidence_ids":[],
        "assumptions":list(working["assumptions"]),"data_gaps":copy.deepcopy(working["data_gaps"]),"diagnostics":[],"next_actions":[]}
    for stage in trace:
        result["diagnostics"].extend(copy.deepcopy(d) for d in stage["diagnostics"] if d["code"] == "EMISSION_FACTOR_REQUIRED")
    refs, entities, reviews, actions = set(), [], [], []

    def gap(reason,field="operations_planning"):
        result["data_gaps"].append({"id":ident+"-gap-"+str(len(result["data_gaps"])),"field":field,"reason":reason,
            "impact":"Operational candidate/action readiness is not established.","remedy":"Supply sourced assessments, ownership, proposed dates and required review decisions."})
        result["diagnostics"].append({"code":"OPERATIONS_DATA_REQUIRED","message":reason})

    try:
        review = parameters["planning_review"]
        refs.update(_review(review,{e["id"] for e in working["evidence"]},("objective","scope_boundary","rationale")))
        if not isinstance(review.get("coverage_complete"),bool): raise ValueError("Explicit operational coverage assessment required.")
        planning = review.get("planning_period")
        if (not isinstance(planning,dict) or set(planning) != {"start","end"}
                or date.fromisoformat(planning["start"]) > date.fromisoformat(planning["end"])):
            raise ValueError("Explicit ordered planning dates required; do not relabel reporting periods.")
        candidates = parameters["opportunities"]
        if not isinstance(candidates,list) or not candidates or any(not isinstance(o,dict) for o in candidates):
            raise ValueError("Nonempty sourced opportunity register required.")
        opportunity_ids = [o.get("id") for o in candidates]
        if (any(not isinstance(i,str) or not i.strip() for i in opportunity_ids) or len(opportunity_ids) != len(set(opportunity_ids))
                or set(opportunity_ids) & {o["id"] for o in working["opportunities"]}):
            raise ValueError("New unique opportunity IDs required; prior opportunity history cannot be replaced.")
        sources = {r["id"]:r for r in working["results"]}
        known = {e["id"] for e in working["evidence"]}
        known_reviews = {r["id"] for r in result["review_requirements"]}
        for opportunity in candidates:
            fields = {"id","domain","description","owner","evidence_ids","assessment_result_ids","business_case_result_id","business_case_applicability","actions","interacts_with"}
            if (set(opportunity) not in (fields,fields|{"interpretation_result_ids"})
                    or opportunity["domain"] not in {"energy","water","waste","materials"}
                    or not isinstance(opportunity["description"],str) or not opportunity["description"].strip()
                    or (opportunity["owner"] is not None and (not isinstance(opportunity["owner"],str) or not opportunity["owner"].strip()))):
                raise ValueError("Complete operational domain, description and assigned/unassigned owner record required.")
            evidence = _review(dict(opportunity,confirmed=True),known,())
            refs.update(evidence)
            assessment_ids = opportunity["assessment_result_ids"]
            if (not isinstance(assessment_ids,list) or not assessment_ids or any(not isinstance(i,str) or i not in sources for i in assessment_ids)
                    or len(assessment_ids) != len(set(assessment_ids))):
                raise ValueError("Known distinct operational assessment results required.")
            if not set(assessment_ids) <= set(ids[:-1]):
                raise ValueError("Operational assessment links must be freshly executed in this composition; repeat source analysis before registering candidates.")
            waste_skills = {"build-waste-baseline","calculate-diversion-rate","identify-waste-hotspots","analyze-waste-cost"}
            domain_skills = {"energy":set(ENERGY),"water":set(WATER),"waste":waste_skills,"materials":set(RESOURCES)-waste_skills}
            if not any(i in working[opportunity["domain"]] or sources[i]["skill"] in domain_skills[opportunity["domain"]] for i in assessment_ids):
                raise ValueError("Candidate must link at least one assessment in its declared physical domain.")
            for key in assessment_ids: evidence.update(sources[key]["evidence_ids"])
            interpretation_ids = opportunity.get("interpretation_result_ids",[])
            if (not isinstance(interpretation_ids,list) or any(not isinstance(i,str) or i not in sources for i in interpretation_ids)
                    or len(interpretation_ids) != len(set(interpretation_ids))):
                raise ValueError("Interpretation links must identify known distinct common results.")
            for key in interpretation_ids:
                source = sources[key]
                if source["skill"] not in INTERPRETATIONS[opportunity["domain"]] or not source["evidence_ids"]:
                    raise ValueError("Interpretation links require sourced results from the candidate's physical domain interpretation skills.")
                evidence.update(source["evidence_ids"])
            interactions = opportunity["interacts_with"]
            if (not isinstance(interactions,list) or any(not isinstance(i,str) for i in interactions)
                    or len(interactions) != len(set(interactions)) or not set(interactions) <= set(opportunity_ids)-{opportunity["id"]}):
                raise ValueError("Interactions must identify other selected opportunities once.")
            case_id = opportunity["business_case_result_id"]
            if case_id is not None:
                case = sources.get(case_id)
                if case is None or case["skill"] != "build-sustainability-business-case": raise ValueError("Linked business-case result required.")
                basis = _basis(case)
                if "case_review" not in basis: raise ValueError("Annual cash-flow output alone is not a composed business case.")
                basis["result_id"] = ident+"-case-check-"+opportunity["id"]
                while basis["result_id"] in sources: basis["result_id"] += "-next"
                checked = run_finance(working,case["skill"],basis)["result"]
                content = lambda items: [{k:v for k,v in m.items() if k != "id"} for m in items]
                if not checked["metrics"] or content(checked["metrics"]) != content(case["metrics"]):
                    raise ValueError("Linked business case does not reproduce from current source inputs.")
                applicability = opportunity["business_case_applicability"]
                evidence.update(_review(applicability,known,("rationale","scope_boundary")))
                reports = [d for d in checked["diagnostics"] if d["code"] == "SUSTAINABILITY_BUSINESS_CASE"]
                if len(reports) != 1: raise ValueError("Reproduced composed business-case report required.")
                projects = {a["project_id"] for a in json.loads(reports[0]["message"])["alternatives"]}
                selected = applicability.get("project_ids")
                if (not isinstance(selected,list) or not selected or any(not isinstance(i,str) for i in selected)
                        or len(selected) != len(set(selected)) or not set(selected) <= projects):
                    raise ValueError("Applicability must identify actual case alternatives; no unrelated financial benefit inferred.")
                evidence.update(case["evidence_ids"])
            elif opportunity["business_case_applicability"] is not None:
                raise ValueError("Business-case applicability requires a linked composed case.")
            refs.update(evidence)
            gate = ident+"-review-"+opportunity["id"]
            proposed = opportunity["actions"]
            if not isinstance(proposed,list) or not proposed: raise ValueError("At least one proposed owned action required per opportunity.")
            planned = []
            for action in proposed:
                if (not isinstance(action,dict) or set(action) not in (
                        {"description","owner","kind","target_date","prerequisite_review_ids"},
                        {"id","depends_on","description","owner","kind","target_date","prerequisite_review_ids"})
                        or action["kind"] not in {"data_collection","implementation"}
                        or any(not isinstance(action[f],str) or not action[f].strip() for f in ("description","owner","target_date"))
                        or not date.fromisoformat(planning["start"]) <= date.fromisoformat(action["target_date"]) <= date.fromisoformat(planning["end"])):
                    raise ValueError("Explicit proposed action type, owner and in-plan target date required.")
                prerequisites = action["prerequisite_review_ids"]
                if (not isinstance(prerequisites,list) or any(not isinstance(i,str) for i in prerequisites)
                        or len(prerequisites) != len(set(prerequisites)) or not set(prerequisites) <= known_reviews):
                    raise ValueError("Action prerequisite reviews must resolve to the retained review ledger.")
                planned.append(dict(action,status="proposed",implementation_authorized=False,
                    prerequisite_review_ids=prerequisites+([gate] if action["kind"] == "implementation" else [])))
            if any(a["kind"] == "implementation" for a in planned):
                if gate in known_reviews: raise ValueError("Generated operational review ID conflicts with existing review history.")
                reviews.append({"id":gate,"state":"ENGINEERING_REVIEW_REQUIRED","reason":"Validate operational applicability, service/quality, interactions and implementation design before implementation.",
                    "scope":opportunity["description"],"reviewer_role":"qualified operational reviewer","status":"open","resolution":None})
            blocked = any(sources[i]["status"] in {"blocked","partial","invalid_input"} for i in assessment_ids+interpretation_ids)
            if opportunity["owner"] is None: gap("Opportunity owner is unassigned: "+opportunity["id"],"ownership")
            if case_id is None: gap("Economic benefit has no linked composed business case: "+opportunity["id"],"economic_assessment")
            if blocked: gap("Linked assessment coverage is incomplete: "+opportunity["id"],"assessment_coverage")
            entities.append({"id":opportunity["id"],"evidence_ids":sorted(evidence),"attributes":dict(opportunity,
                actions=planned,status="candidate",assessment_coverage="incomplete" if blocked else "selected_supported",
                quantification="Refer to linked source measures; registration establishes no additional saving or portfolio benefit.",implementation_authorized=False)})
            actions.extend(dict(a,opportunity_id=opportunity["id"]) for a in planned)
        for entity in entities:
            for other in entity["attributes"]["interacts_with"]:
                peer = next(e for e in entities if e["id"] == other)
                if entity["id"] not in peer["attributes"]["interacts_with"]: raise ValueError("Declare opportunity interactions symmetrically.")
        sequence = _action_sequence(actions)
        if not review["coverage_complete"]: gap("Selected operational coverage is incomplete.","operations_coverage")
        result["review_requirements"].extend(reviews)
        working["opportunities"].extend(entities)
        result["diagnostics"].append({"code":"OPERATIONS_PLAN","message":json.dumps({"planning_review":review,"opportunities":entities,"actions":actions,
            "steps":trace,"portfolio_total":None,"implementation_authorized":False,"limits":"Candidate registration and proposed actions only. Source assessments, economic applicability and implementation design require review."},sort_keys=True)})
        if sequence is not None:
            result["diagnostics"].append({"code":"OPERATIONS_ACTION_SEQUENCE","message":json.dumps(sequence,sort_keys=True)})
        result["status"] = "partial" if result["data_gaps"] else "completed"
    except (ValueError,KeyError,TypeError) as error:
        gap(str(error));result["status"]="blocked"
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code":"OPERATIONS_INPUTS","message":json.dumps(parameters,sort_keys=True)})
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"] == "open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE");result["next_actions"] = list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    proposal = propose(working,result,"Compose source analyses, candidate opportunities and proposed owned actions without implementation approval")
    proposal["base_revision"] = state["revision"]
    proposal["state"]["revision"] = state["revision"]+1
    validate_state(proposal["state"])
    return {"result":result,"proposal":proposal}
