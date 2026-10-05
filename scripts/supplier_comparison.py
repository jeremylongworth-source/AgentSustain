"""Reproduce supplier rubric assessments before comparing selected bounds."""
import copy
import json

from .finance_projects import _review


def _record(result, code):
    items=[d for d in result["diagnostics"] if d["code"]==code]
    if len(items)!=1: raise ValueError("Exactly one supplier source-method record required.")
    value=json.loads(items[0]["message"])
    if not isinstance(value,dict): raise ValueError("Supplier source-method record must be an object.")
    return value


def compare(state, parameters, refs):
    # Local import keeps the shared dispatcher and source reproduction composable.
    from .supplier_tools import run_suppliers
    review=parameters["comparison_review"];known={e["id"] for e in state["evidence"]}
    refs.update(_review(review,known,("reviewer_role","rationale","rubric_id","scope_boundary","functional_unit","service_requirements")))
    if review.get("period")!=state["reporting_period"] or review.get("boundary_id")!=state["organizational_boundary"]["id"]:
        raise ValueError("Comparison period and buyer boundary must match current state.")
    selected=parameters["assessment_result_ids"]
    if (not isinstance(selected,list) or len(selected)<2 or any(not isinstance(i,str) for i in selected)
            or len(selected)!=len(set(selected))):
        raise ValueError("At least two distinct supplier assessment IDs required.")
    sources={r["id"]:r for r in state["results"]};candidates=[];rubric=None;exclusions=None;supplier_ids=set()
    for key in selected:
        source=sources.get(key)
        if source is None or source["skill"]!="score-supplier-sustainability" or source["status"] not in {"completed","partial"}:
            raise ValueError("Supported supplier-scoring source required.")
        inputs=copy.deepcopy(_record(source,"SUPPLIER_INPUTS"))
        inputs["result_id"]=parameters["result_id"]+"-check-"+key
        while inputs["result_id"] in sources:inputs["result_id"]+="-next"
        checked=run_suppliers(state,source["skill"],inputs)["result"]
        if checked["status"]=="blocked": raise ValueError("Supplier assessment does not reproduce from current source inputs.")
        report=_record(checked,"SUPPLIER_ASSESSMENT")
        if report!=_record(source,"SUPPLIER_ASSESSMENT"):
            raise ValueError("Stored supplier assessment differs from reproduced source assessment.")
        ident=report["supplier_id"]
        if ident in supplier_ids: raise ValueError("Compare distinct suppliers, not multiple ratings of the same supplier.")
        supplier_ids.add(ident)
        assessment=report["assessment_review"]
        if any(assessment.get(f)!=review.get(f) for f in ("rubric_id","scope_boundary","period","boundary_id")):
            raise ValueError("Supplier rubric, scope, period and buyer boundary must share the comparison basis.")
        criteria=sorted(report["criteria"],key=lambda c:c["id"])
        omitted=sorted(a["criterion_id"] for a in report["assessments"] if a["assessment"]=="documented_exclusion")
        if rubric is None:rubric=criteria;exclusions=omitted
        if criteria!=rubric or omitted!=exclusions:
            raise ValueError("Different criteria, weights, anchors, evidence policy or exclusions are not comparable.")
        if report["possible_score_range"] is None:
            raise ValueError("A positive applicable rubric denominator is required for comparison.")
        refs.update(source["evidence_ids"]);refs.update(checked["evidence_ids"])
        candidates.append({"supplier_id":ident,"assessment_result_id":key,"score":report["score"],
            "possible_score_range":report["possible_score_range"],"weighted_coverage_percent":report["weighted_coverage_percent"],
            "source_status":source["status"],"excluded_criterion_ids":omitted})
    pairs=[]
    for index,left in enumerate(candidates):
        for right in candidates[index+1:]:
            a,b=left["possible_score_range"],right["possible_score_range"]
            if a["low"]>b["high"]:relation="left_strictly_above";favored=left["supplier_id"]
            elif b["low"]>a["high"]:relation="right_strictly_above";favored=right["supplier_id"]
            elif a["low"]==a["high"]==b["low"]==b["high"]:relation="equal_complete_scores";favored=None
            else:relation="overlap_or_touch";favored=None
            pairs.append({"left_supplier_id":left["supplier_id"],"right_supplier_id":right["supplier_id"],
                "relation":relation,"higher_rubric_range_supplier_id":favored})
    return {"comparison_review":review,"criteria":rubric,"candidates":candidates,"pairwise":pairs,
        "supplier_approved":False,"procurement_authorized":False,"selected_supplier_id":None,
        "limits":"Conditional buyer rubric bounds only. Functional equivalence is supplied review, not authentication. No price, service risk, emissions, procurement selection or complete supplier performance inferred."}
