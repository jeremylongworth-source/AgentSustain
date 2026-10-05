"""Explicit supplier questionnaires and conditional buyer-rubric assessments."""
import copy
from decimal import Decimal, localcontext
import json

from .contract_validation import validate_state
from .data_tools import number, serialize
from .finance_projects import _review
from .state_proposal import propose


BASE = {"supplier_id","criteria","assessment_review","result_id"}
OPERATIONS = {"build-supplier-questionnaire":BASE}
OPERATIONS.update({s:BASE|{"responses"} for s in (
    "evaluate-supplier-response","score-supplier-sustainability","identify-supplier-data-gaps")})
OPERATIONS["compare-suppliers"]={"assessment_result_ids","comparison_review","result_id"}
OPERATIONS["map-supply-chain-emissions"]={"links","mapping_review","result_id"}


def run_suppliers(state, skill, parameters):
    validate_state(state)
    if skill not in OPERATIONS or not isinstance(parameters,dict) or (set(parameters) != OPERATIONS[skill]
            and not (skill=="map-supply-chain-emissions" and set(parameters)==OPERATIONS[skill]|{"fixture_mode"})):
        raise ValueError("Supported supplier operation with exact parameters required.")
    ident=parameters["result_id"]
    if not isinstance(ident,str) or not ident.strip(): raise ValueError("Fresh result ID required.")
    result={"id":ident,"skill":skill,"contract_version":"0.1.0","status":"completed","review_states":["ANALYTICAL"],
        "review_requirements":copy.deepcopy(state["review_requirements"]),"metrics":[],"evidence_ids":[],
        "assumptions":list(state["assumptions"]),"data_gaps":copy.deepcopy(state["data_gaps"]),"diagnostics":[],"next_actions":[]}
    known={e["id"] for e in state["evidence"]};refs=set()
    def gap(message):
        result["data_gaps"].append({"id":ident+"-gap-"+str(len(result["data_gaps"])),"field":"supplier_evidence",
            "reason":message,"impact":"Supplier performance, comparability and procurement readiness remain conditional.",
            "remedy":"Obtain supplier-specific evidence and a documented buyer assessment; do not substitute zero for unknown."})
        result["diagnostics"].append({"code":"SUPPLIER_DATA_REQUIRED","message":message})
    try:
        if skill=="compare-suppliers":
            from .supplier_comparison import compare
            report=compare(state,parameters,refs)
        elif skill=="map-supply-chain-emissions":
            from .supplier_mapping import map_chain
            report=map_chain(state,parameters,refs,result,gap)
        else:
            supplier=next((s for s in state["suppliers"] if s["id"]==parameters["supplier_id"]),None)
            if supplier is None or not supplier["evidence_ids"]:
                raise ValueError("Supplier must resolve to the existing sourced supplier register.")
            refs.update(supplier["evidence_ids"])
            review=parameters["assessment_review"]
            refs.update(_review(review,known,("reviewer_role","rationale","rubric_id","scope_boundary")))
            if review.get("period") != state["reporting_period"] or review.get("boundary_id") != state["organizational_boundary"]["id"]:
                raise ValueError("Assessment period and buyer boundary must match the supplied state.")
            criteria=parameters["criteria"]
            if not isinstance(criteria,list) or not criteria: raise ValueError("Nonempty explicit buyer criteria required.")
            rubric={}
            for c in criteria:
                if (not isinstance(c,dict) or set(c)!={"id","question","weight","max_score","anchors","required_evidence"}
                        or any(not isinstance(c[f],str) or not c[f].strip() for f in ("id","question"))
                        or c["id"] in rubric or not isinstance(c["required_evidence"],bool)):
                    raise ValueError("Unique criteria with questions, weights, anchors and evidence policy required.")
                weight,maximum=number(c["weight"]),number(c["max_score"])
                if weight<=0 or maximum<=0: raise ValueError("Criterion weights and score maxima must be positive.")
                anchors=c["anchors"]
                if not isinstance(anchors,list) or not anchors: raise ValueError("Explicit scoring anchors required.")
                values=[]
                for anchor in anchors:
                    if (not isinstance(anchor,dict) or set(anchor)!={"score","description"}
                            or not isinstance(anchor["description"],str) or not anchor["description"].strip()):
                        raise ValueError("Each scoring anchor requires a score and meaningful description.")
                    values.append(number(anchor["score"]))
                if len(values)!=len(set(values)) or min(values)!=0 or max(values)!=maximum:
                    raise ValueError("Unique scoring anchors must span zero to the declared maximum.")
                rubric[c["id"]]=(c,weight,maximum,set(values))
            report={"supplier_id":supplier["id"],"assessment_review":review,"criteria":criteria,
                "procurement_authorized":False,"supplier_approved":False,"source_authentication":"Supplied buyer review; field presence is not independent authentication."}
            if skill=="build-supplier-questionnaire":
                report["questions"]=[{"criterion_id":c["id"],"question":c["question"],"required_evidence":c["required_evidence"]} for c in criteria]
                report["delivery_status"]="draft_unsent"
            else:
                responses=parameters["responses"]
                if not isinstance(responses,list): raise ValueError("Response register required; missing answers may be explicitly empty.")
                indexed={}
                for answer in responses:
                    fields={"criterion_id","status","answer","score","evidence_ids","assessment_rationale"}
                    if (not isinstance(answer,dict) or set(answer) not in (fields,fields|{"evidence_fit"})
                            or not isinstance(answer["criterion_id"],str) or answer["criterion_id"] not in rubric or answer["criterion_id"] in indexed
                            or answer["status"] not in {"provided","missing","unverified","not_applicable"}
                            or not isinstance(answer["answer"],str) or not isinstance(answer["assessment_rationale"],str)
                            or not answer["assessment_rationale"].strip()):
                        raise ValueError("Known distinct responses require explicit status and assessment rationale.")
                    evidence=answer["evidence_ids"]
                    if answer.get("evidence_fit","unverified") not in {"reviewed_supporting","unverified","irrelevant","not_required"}:
                        raise ValueError("Evidence fit must be explicitly reviewed, unverified, irrelevant or not required.")
                    if (not isinstance(evidence,list) or any(not isinstance(e,str) for e in evidence)
                            or len(evidence)!=len(set(evidence)) or not set(evidence)<=known):
                        raise ValueError("Response evidence must resolve to known distinct source records.")
                    refs.update(evidence);indexed[answer["criterion_id"]]=answer
                denominator=Decimal(0);supported_weight=Decimal(0);supported_score=Decimal(0);unknown_weight=Decimal(0);assessments=[]
                with localcontext() as context:
                    context.prec=34
                    for key,(c,weight,maximum,anchors) in rubric.items():
                        answer=indexed.get(key)
                        if answer is not None and answer["status"]=="not_applicable":
                            if answer["score"] is not None or not answer["evidence_ids"] or answer.get("evidence_fit")!="reviewed_supporting":
                                raise ValueError("Not-applicable exclusions require reviewed supporting evidence and a null score.")
                            assessments.append(dict(answer,assessment="documented_exclusion"));continue
                        denominator+=weight
                        supported=False
                        if answer is not None and answer["status"]=="provided":
                            if not answer["answer"].strip(): raise ValueError("Provided responses require the actual supplier answer.")
                            if answer["score"] is None: gap("Buyer rating is missing for criterion "+key)
                            else:
                                score=number(answer["score"])
                                if score not in anchors: raise ValueError("Buyer ratings must match a declared scoring anchor.")
                                supported=(answer.get("evidence_fit")=="reviewed_supporting" and bool(answer["evidence_ids"])) or (
                                    not c["required_evidence"] and answer.get("evidence_fit")=="not_required")
                                if supported: supported_weight+=weight;supported_score+=weight*score/maximum
                                else: gap("Supporting evidence fit is unverified, irrelevant or absent for criterion "+key)
                        else:
                            if answer is not None and answer["score"] is not None:
                                raise ValueError("Missing or unverified responses cannot carry a numerical rating.")
                            gap("Criterion "+key+" is missing or unverified; no score inferred.")
                        if not supported: unknown_weight+=weight
                        assessments.append({"criterion_id":key,"response":answer,"assessment":"buyer_rated" if supported else "unresolved"})
                    report["assessments"]=assessments
                    report["score_basis"]="Weighted supplied anchored ratings divided by applicable criterion weight; not an environmental impact or assurance score."
                    report["score"]=None;report["possible_score_range"]=None;report["weighted_coverage_percent"]=None
                    if denominator>0:
                        low=100*supported_score/denominator;high=100*(supported_score+unknown_weight)/denominator
                        report["possible_score_range"]={"low":serialize(low),"high":serialize(high),"unit":"percent of buyer rubric maximum","basis":"Unknown ratings could occupy any anchor; bounds are not confidence intervals."}
                        report["weighted_coverage_percent"]=serialize(100*supported_weight/denominator)
                        if unknown_weight==0: report["score"]=serialize(low)
                    else: gap("All criteria are excluded; no applicable scoring denominator exists.")
        code={"compare-suppliers":"SUPPLIER_COMPARISON","map-supply-chain-emissions":"SUPPLY_CHAIN_MAPPING"}.get(skill,"SUPPLIER_ASSESSMENT")
        result["diagnostics"].append({"code":code,"message":json.dumps(report,sort_keys=True)})
        result["status"]="partial" if result["data_gaps"] else "completed"
    except (ValueError,TypeError,KeyError) as error:
        gap(str(error));result["status"]="blocked"
    result["evidence_ids"]=sorted(refs)
    result["diagnostics"].append({"code":"SUPPLIER_INPUTS","message":json.dumps(parameters,sort_keys=True)})
    result["review_states"] += [r["state"] for r in result["review_requirements"] if r["status"]=="open"]
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE");result["next_actions"]=list(dict.fromkeys(g["remedy"] for g in result["data_gaps"]))
    result["review_states"]=list(dict.fromkeys(result["review_states"]))
    return {"result":result,"proposal":propose(state,result,"Assess sourced supplier evidence under an explicit buyer rubric without approval or external communication")}
