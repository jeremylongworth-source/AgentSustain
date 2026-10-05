"""Sourced supplier adverse-impact screening; no legal or procurement determination."""
import copy
from datetime import date

from .finance_projects import _review


def _anchors(entries):
    if not isinstance(entries,list) or len(entries)<2:raise ValueError("At least two explicit ordinal anchors required.")
    ranks=set()
    for entry in entries:
        if (not isinstance(entry,dict) or set(entry)!={"rank","label","description"} or type(entry["rank"]) is not int
                or entry["rank"]<1 or entry["rank"] in ranks
                or any(not isinstance(entry[f],str) or not entry[f].strip() for f in ("label","description"))):
            raise ValueError("Distinct positive integer ordinal ranks with labels and descriptions required.")
        ranks.add(entry["rank"])
    return ranks


def screen(state, parameters, refs, result, gap):
    known={e["id"]:e for e in state["evidence"]}
    supplier=next((s for s in state["suppliers"] if s["id"]==parameters["supplier_id"]),None)
    if supplier is None or not supplier["evidence_ids"]:raise ValueError("Sourced registered supplier required.")
    refs.update(supplier["evidence_ids"])
    review=parameters["screening_review"]
    refs.update(_review(review,set(known),("reviewer_role","rationale","scope_boundary","screening_basis","stakeholder_context")))
    if (review.get("period")!=state["reporting_period"] or review.get("boundary_id")!=state["organizational_boundary"]["id"]
            or not isinstance(review.get("coverage_complete"),bool)):
        raise ValueError("Current buyer period/boundary and explicit coverage required.")
    model=parameters["risk_model"]
    if (not isinstance(model,dict) or set(model)!={"id","severity_anchors","likelihood_anchors","priority_rule"}
            or not isinstance(model["id"],str) or not model["id"].strip() or model["priority_rule"]!="severity_groups"):
        raise ValueError("Explicit ordinal risk model with severity_groups priority rule required.")
    severity=_anchors(model["severity_anchors"]);likelihood=_anchors(model["likelihood_anchors"])
    risks=parameters["risks"]
    if not isinstance(risks,list):raise ValueError("Risk register required; empty selected coverage is not proof of no risk.")
    fields={"id","topic","impact_status","adverse_impact","relationship","product","site","geography","observed_date",
        "period","boundary_id","evidence_ids","evidence_fit","severity_rank","likelihood_rank","scale","scope","irremediability",
        "assessment_rationale","source_applicability","follow_up_owner","follow_up_date"}
    ids=set();rows=[]
    for risk in risks:
        strings=("id","adverse_impact","product","site","geography","scale","scope","irremediability",
            "assessment_rationale","source_applicability","follow_up_owner","follow_up_date")
        if (not isinstance(risk,dict) or set(risk)!=fields
                or any(not isinstance(risk[f],str) or not risk[f].strip() for f in strings)
                or risk["id"] in ids or risk["topic"] not in {"environment","human_rights","labour","governance"}
                or risk["impact_status"] not in {"actual","potential","unknown"}
                or risk["relationship"] not in {"caused","contributed","directly_linked","unknown"}
                or risk["evidence_fit"] not in {"reviewed_supporting","unverified","proxy","irrelevant"}):
            raise ValueError("Distinct risk records require exact sourced impact/context, rationale and owned follow-up fields.")
        ids.add(risk["id"])
        for f in ("observed_date","follow_up_date"):
            if f=="observed_date" and risk[f] is None:continue
            if date.fromisoformat(risk[f]).isoformat()!=risk[f]:raise ValueError("Canonical ISO source observation and follow-up dates required.")
        if risk["observed_date"] is not None and risk["follow_up_date"]<risk["observed_date"]:
            raise ValueError("Follow-up date cannot precede the observed source date.")
        if risk["period"]!=state["reporting_period"] or risk["boundary_id"]!=state["organizational_boundary"]["id"]:
            raise ValueError("Risk application period and buyer boundary must match the selected screening.")
        evidence=risk["evidence_ids"]
        if (not isinstance(evidence,list) or any(not isinstance(i,str) for i in evidence) or len(set(evidence))!=len(evidence)
                or not set(evidence)<=set(known)):
            raise ValueError("Distinct known source evidence IDs required.")
        refs.update(evidence)
        for f,anchors in (("severity_rank",severity),("likelihood_rank",likelihood)):
            if risk[f] is not None and (type(risk[f]) is not int or risk[f] not in anchors):
                raise ValueError("Supplied ordinal ratings must match declared anchors or remain null.")
        if risk["impact_status"]=="actual" and risk["likelihood_rank"] is not None:
            raise ValueError("Actual impacts retain severity; occurrence likelihood must be null, not a probability of a past event.")
        supported=risk["evidence_fit"]=="reviewed_supporting" and bool(evidence) and risk["impact_status"]!="unknown"
        unresolved=[]
        if risk["observed_date"] is None:unresolved.append("Observation date is unknown; source access date is not an event date.")
        if not supported:unresolved.append("Supplier-specific adverse-impact evidence remains unverified, missing, irrelevant or proxy-only.")
        if risk["severity_rank"] is None:unresolved.append("Severity assessment is unknown.")
        if risk["impact_status"]=="potential" and risk["likelihood_rank"] is None:unresolved.append("Potential-impact likelihood is unknown.")
        if risk["relationship"]=="unknown":unresolved.append("Buyer relationship to the adverse impact needs review.")
        for message in unresolved:gap(risk["id"]+": "+message)
        rows.append({"risk":copy.deepcopy(risk),"source_records":[{"id":i,"source":copy.deepcopy(known[i]["source"]),
            "period":copy.deepcopy(known[i]["period"]),"geography":known[i]["geography"],"quality":copy.deepcopy(known[i]["quality"]),
            "uncertainty":copy.deepcopy(known[i]["uncertainty"])} for i in evidence],
            "screening_status":"supported_selected_impact" if supported else "investigation_required",
            "supported_severity_rank":risk["severity_rank"] if supported else None,
            "supported_likelihood_rank":risk["likelihood_rank"] if supported and risk["impact_status"]=="potential" else None,
            "severity_priority_group":None,"unresolved_fields":unresolved,"finding_of_misconduct":False})
    ranked=sorted({r["supported_severity_rank"] for r in rows if r["supported_severity_rank"] is not None},reverse=True)
    groups=[]
    for group,rank in enumerate(ranked,1):
        members=sorted(r["risk"]["id"] for r in rows if r["supported_severity_rank"]==rank)
        groups.append({"group":group,"severity_rank":rank,"risk_ids":members})
        for row in rows:
            if row["risk"]["id"] in members:row["severity_priority_group"]=group
    if not risks:gap("No selected adverse-impact records; absence of reports does not establish absence of risk.")
    if not review["coverage_complete"]:gap("Supplier screening coverage is incomplete; unexamined products, sites and topics are not low risk.")
    gate=parameters["result_id"]+"-risk-review"
    while any(r["id"]==gate for r in result["review_requirements"]):gate+="-next"
    result["review_requirements"].append({"id":gate,"state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Selected supplier impact screening, source fitness and response priorities require substantive due-diligence review.",
        "scope":"Supplier "+supplier["id"]+" adverse-impact screening","reviewer_role":"sustainability due-diligence reviewer","status":"open","resolution":None})
    return {"supplier_id":supplier["id"],"screening_review":review,"risk_model":model,"rows":rows,"severity_priority_groups":groups,
        "aggregate_supplier_risk":None,"legal_determination":None,"supplier_approved":False,"procurement_authorized":False,"contact_authorized":False,
        "limits":"Supplied reviewed impact facts and ordinal severity groups only; not independent source authentication or an OECD numeric score. Equal severities remain tied; likelihood is retained separately, not multiplied. Unsupported allegations/proxies remain investigation needs. No misconduct, compliance, disengagement or overall low-risk finding."}
