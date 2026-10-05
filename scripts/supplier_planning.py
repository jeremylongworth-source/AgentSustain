"""Source-reproduced supplier evidence priorities and proposed improvement actions."""
import copy
from datetime import date

from .data_tools import number
from .finance_projects import _review
from .supplier_comparison import _record


def _assessment(state, key, review, ident, refs):
    from .supplier_tools import run_suppliers
    source=next((r for r in state["results"] if r["id"]==key),None)
    if source is None or source["skill"]!="score-supplier-sustainability" or source["status"] not in {"completed","partial"}:
        raise ValueError("Supported supplier scoring source required.")
    inputs=copy.deepcopy(_record(source,"SUPPLIER_INPUTS"));inputs["result_id"]=ident+"-check-"+key
    while any(r["id"]==inputs["result_id"] for r in state["results"]):inputs["result_id"]+="-next"
    checked=run_suppliers(state,source["skill"],inputs)["result"]
    if checked["status"]=="blocked":raise ValueError("Supplier assessment reproduction blocked.")
    report=_record(checked,"SUPPLIER_ASSESSMENT")
    if report!=_record(source,"SUPPLIER_ASSESSMENT"):
        raise ValueError("Supplier assessment differs from reproduced inputs.")
    if any(report["assessment_review"].get(f)!=review.get(f) for f in ("rubric_id","scope_boundary","period","boundary_id")):
        raise ValueError("Supplier assessment and planning review must share scope, rubric, period and buyer boundary.")
    refs.update(source["evidence_ids"]);refs.update(checked["evidence_ids"])
    return report


def _context(state, review, refs):
    refs.update(_review(review,{e["id"] for e in state["evidence"]},("reviewer_role","rationale","rubric_id","scope_boundary","service_constraints")))
    if review.get("period")!=state["reporting_period"] or review.get("boundary_id")!=state["organizational_boundary"]["id"]:
        raise ValueError("Current buyer period and boundary required for supplier planning.")


def engage(state, parameters, refs, gap):
    review=parameters["engagement_review"];_context(state,review,refs)
    selected=parameters["assessment_result_ids"]
    if not isinstance(selected,list) or not selected or any(not isinstance(i,str) for i in selected) or len(set(selected))!=len(selected):
        raise ValueError("Distinct supplier assessment IDs required.")
    rule=parameters["priority_rule"];allowed={"unresolved_criterion_count":"descending","weighted_coverage_percent":"ascending"}
    if (not isinstance(rule,list) or not rule or any(not isinstance(r,dict) or set(r)!={"field","direction"}
            or r.get("field") not in allowed or r.get("direction")!=allowed[r["field"]] for r in rule)
            or len({r["field"] for r in rule})!=len(rule)):
        raise ValueError("Explicit distinct evidence-gap priority fields and directions required.")
    candidates=[];seen=set();basis=None
    for key in selected:
        report=_assessment(state,key,review,parameters["result_id"],refs)
        supplier=report["supplier_id"]
        if supplier in seen:raise ValueError("One assessment per distinct supplier required.")
        seen.add(supplier)
        criteria=sorted(report["criteria"],key=lambda c:c["id"])
        exclusions=sorted(a["criterion_id"] for a in report["assessments"] if a["assessment"]=="documented_exclusion")
        current=(criteria,exclusions)
        if basis is None:basis=current
        if basis!=current:raise ValueError("Evidence priorities require equal rubric criteria, weights, anchors, evidence policies and exclusions.")
        unresolved=[a["criterion_id"] for a in report["assessments"] if a["assessment"]=="unresolved"]
        questions=[{"criterion_id":c["id"],"question":c["question"],"required_evidence":c["required_evidence"]} for c in criteria if c["id"] in unresolved]
        row={"supplier_id":supplier,"assessment_result_id":key,"unresolved_criterion_count":len(unresolved),
            "weighted_coverage_percent":report["weighted_coverage_percent"],"questions":questions,"priority_group":None,
            "source_score":report["score"],"source_score_range":report["possible_score_range"]}
        if unresolved:gap("Supplier "+supplier+" has unresolved criteria; proposed requests do not resolve them.")
        candidates.append(row)
    eligible=[r for r in candidates if r["questions"] and all(r[c["field"]] is not None for c in rule)]
    def order(row):return tuple(-number(row[c["field"]]) if c["direction"]=="descending" else number(row[c["field"]]) for c in rule)
    eligible.sort(key=lambda r:(order(r),r["supplier_id"]))
    last=None;group=0
    for row in eligible:
        value=order(row)
        if value!=last:group+=1;last=value
        row["priority_group"]=group
    return {"engagement_review":review,"priority_rule":rule,"candidates":candidates,
        "priority_groups":[{"group":g,"supplier_ids":sorted(r["supplier_id"] for r in eligible if r["priority_group"]==g)} for g in range(1,group+1)],
        "delivery_status":"draft_unsent","procurement_authorized":False,
        "limits":"Selected evidence-request priorities only; ties share a group. No environmental impact, emissions priority, supplier risk or capacity inferred. Complete/excluded rubrics have no request priority. No default rule or contact authorization."}


def improve(state, parameters, refs, gap):
    review=parameters["plan_review"];_context(state,review,refs)
    report=_assessment(state,parameters["assessment_result_id"],review,parameters["result_id"],refs)
    actions=parameters["actions"]
    if not isinstance(actions,list) or not actions:raise ValueError("Nonempty proposed action register required.")
    criteria={c["id"]:c for c in report["criteria"]};assessments={a["criterion_id"]:a for a in report["assessments"]}
    fields={"id","criterion_id","kind","owner","target_date","description","evidence_target","target_score","depends_on"}
    ids=set();used=set();rows=[]
    for action in actions:
        if not isinstance(action,dict) or set(action)!=fields or any(not isinstance(action[f],str) or not action[f].strip()
                for f in ("id","criterion_id","owner","target_date","description","evidence_target")):
            raise ValueError("Actions require exact fields, named owners, dates, descriptions and evidence targets.")
        key=action["criterion_id"]
        if action["id"] in ids or key in used or key not in criteria:raise ValueError("Distinct action IDs and known distinct criteria required.")
        ids.add(action["id"]);used.add(key)
        if date.fromisoformat(action["target_date"]).isoformat()!=action["target_date"]:raise ValueError("ISO action date required.")
        deps=action["depends_on"]
        if not isinstance(deps,list) or any(not isinstance(i,str) for i in deps) or len(deps)!=len(set(deps)):
            raise ValueError("Distinct dependency IDs required.")
        assessment=assessments[key];criterion=criteria[key]
        if action["kind"]=="data_collection":
            if assessment["assessment"]!="unresolved" or action["target_score"] is not None:
                raise ValueError("Data collection targets an unresolved criterion and cannot promise a score.")
            gap("Proposed data collection for "+key+" does not resolve missing supplier evidence.")
        elif action["kind"]=="improvement":
            if assessment["assessment"]!="buyer_rated":raise ValueError("Improvement targets require a supported current rating.")
            target=number(action["target_score"])
            if target not in {number(a["score"]) for a in criterion["anchors"]} or target<=number(assessment["response"]["score"]):
                raise ValueError("Improvement target must be a declared anchor above the supported current rating.")
        else:raise ValueError("Action kind must be data_collection or improvement.")
        rows.append(dict(copy.deepcopy(action),source_criterion=copy.deepcopy(criterion),source_assessment=copy.deepcopy(assessment),
            status="proposed",supplier_agreed=False,implementation_authorized=False,completion_verified=False))
    indexed={r["id"]:r for r in rows};remaining=set(ids);sequence=[]
    for row in rows:
        if any(i not in ids or i==row["id"] or indexed[i]["target_date"]>row["target_date"] for i in row["depends_on"]):
            raise ValueError("Known distinct prerequisites must precede their dependent target date.")
    while remaining:
        ready=sorted((i for i in remaining if not set(indexed[i]["depends_on"])&remaining),key=lambda i:(indexed[i]["target_date"],i))
        if not ready:raise ValueError("Supplier action dependency cycle rejected.")
        sequence.extend(ready);remaining.difference_update(ready)
    unaddressed=sorted(k for k,a in assessments.items() if a["assessment"]=="unresolved" and k not in used)
    if unaddressed:gap("Unaddressed supplier evidence criteria: "+", ".join(unaddressed))
    return {"supplier_id":report["supplier_id"],"assessment_result_id":parameters["assessment_result_id"],"plan_review":review,
        "actions":rows,"proposed_sequence":sequence,"unaddressed_criterion_ids":unaddressed,"delivery_status":"draft_unsent",
        "procurement_authorized":False,"projected_emissions_reduction":None,
        "limits":"Targets are buyer rubric goals, not predictions or supplier agreement. Dependency order does not establish resources, critical path or completion. Implementation needs separate supplier, engineering and procurement decisions; existing reviews remain open."}
