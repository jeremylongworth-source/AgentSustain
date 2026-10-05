"""Selected mapped purchase emissions contributions, with source reproduction."""
import copy
from decimal import Decimal, localcontext

from .data_tools import convert, number, serialize
from .finance_projects import _review
from .inventory_analysis import _retain_checks
from .supplier_comparison import _record


def hotspots(state, parameters, refs, result, gap):
    from .supplier_tools import run_suppliers
    review=parameters["hotspot_review"]
    refs.update(_review(review,{e["id"] for e in state["evidence"]},("reviewer_role","rationale","scope_boundary","nonoverlap_assessment")))
    if (review.get("period")!=state["reporting_period"] or review.get("boundary_id")!=state["organizational_boundary"]["id"]
            or not isinstance(review.get("coverage_complete"),bool)):
        raise ValueError("Current buyer period, boundary and explicit selected coverage required.")
    fixture=parameters.get("fixture_mode",False)
    if not isinstance(fixture,bool):raise ValueError("Fixture mode must be boolean.")
    threshold=number(parameters["hotspot_threshold_percent"])
    if not 0<threshold<=100:raise ValueError("Explicit hotspot threshold must be greater than zero and at most 100 percent.")
    selected=parameters["mapping_result_ids"]
    if (not isinstance(selected,list) or not selected or any(not isinstance(i,str) for i in selected)
            or len(set(selected))!=len(selected)):
        raise ValueError("Distinct mapping result IDs required.")
    sources={r["id"]:r for r in state["results"]};rows=[];seen=[set(),set(),set()];gwp=None
    complete=review["coverage_complete"]
    for key in selected:
        source=sources.get(key)
        if source is None or source["skill"]!="map-supply-chain-emissions" or source["status"] not in {"completed","partial"}:
            raise ValueError("Supported purchase mapping source required.")
        inputs=copy.deepcopy(_record(source,"SUPPLIER_INPUTS"));inputs["fixture_mode"]=fixture
        inputs["result_id"]=parameters["result_id"]+"-check-"+key
        while inputs["result_id"] in sources:inputs["result_id"]+="-next"
        checked=run_suppliers(state,source["skill"],inputs)["result"]
        retained=dict(checked,diagnostics=[d for d in checked["diagnostics"] if d["code"] not in {"SUPPLIER_INPUTS","SUPPLY_CHAIN_MAPPING"}])
        _retain_checks(result,retained);result["assumptions"]=list(dict.fromkeys(result["assumptions"]+checked["assumptions"]))
        if checked["status"]=="blocked":raise ValueError("Purchase mapping reproduction blocked.")
        report=_record(checked,"SUPPLY_CHAIN_MAPPING")
        if report!=_record(source,"SUPPLY_CHAIN_MAPPING"):raise ValueError("Stored purchase mapping differs from reproduced source inputs.")
        if report["mapping_review"]["scope_boundary"]!=review["scope_boundary"]:
            raise ValueError("Mapping and hotspot scope must match.")
        complete=complete and report["mapping_review"]["coverage_complete"]
        refs.update(checked["evidence_ids"]);refs.update(source["evidence_ids"])
        for row in report["rows"]:
            link=row["link"];metric=row["emissions_component"]
            identities=(metric["id"],link["purchase_metric_id"],link["purchase_reference"])
            if any(i in registered for i,registered in zip(identities,seen)):
                raise ValueError("Mapped emissions, purchase activities and line references must not repeat across selected maps.")
            for i,registered in zip(identities,seen):registered.add(i)
            category=_record(sources[link["category_result_id"]],"SCOPE3_CATEGORY")
            basis=category["coverage_review"]["gwp_basis"]
            if gwp is None:gwp=basis
            if basis!=gwp:raise ValueError("Mixed GWP bases cannot form a supplier hotspot denominator.")
            if metric["period"]!=state["reporting_period"] or metric["boundary_id"]!=state["organizational_boundary"]["id"]:
                raise ValueError("Mapped emissions require current buyer period and boundary.")
            value=number(convert(metric["value"],metric["unit"],"kg CO2e")["value"])
            if value<0:raise ValueError("Nonnegative gross mapped contributions required; do not net removals or credits.")
            rows.append({"mapping_result_id":key,"source_row":copy.deepcopy(row),"kg_co2e":value})
    if not complete:gap("Selected mapped purchase coverage is incomplete; shares are not shares of the whole Scope 3 footprint.")
    if fixture:result["diagnostics"].append({"code":"SYNTHETIC_FIXTURE","message":"Synthetic mapped supplier contributions only; not a real inventory or hotspot assessment."})
    def metric(suffix,name,value,unit,inputs,formula):
        assumption="Selected mapped purchase denominator only; supplier and category views overlap and cannot be added."
        if assumption not in result["assumptions"]:result["assumptions"].append(assumption)
        entry={"id":parameters["result_id"]+"-"+suffix,"name":name,"value":serialize(value),"unit":unit,
            "period":copy.deepcopy(state["reporting_period"]),"boundary_id":state["organizational_boundary"]["id"],"evidence_ids":sorted(refs),
            "method":{"name":"Selected mapped supplier emissions contributions","version":"0.1.0","source":"repository:docs/supplier-contract.md"},
            "assumption":assumption,
            "uncertainty":{"kind":"unquantified","description":"Source quantity, factor, allocation and coverage uncertainty is retained; contribution order is conditional on supplied point values.","value":None,"unit":None},
            "calculation":{"formula":formula,"inputs":inputs,"conversions":["Mapped component quantities normalized to kg CO2e"],"rounding":"34-digit Decimal arithmetic; JSON serialization"}}
        result["metrics"].append(entry);return entry
    with localcontext() as context:
        context.prec=34
        total=sum((r["kg_co2e"] for r in rows),Decimal(0))
        if not rows:raise ValueError("Mapped contributions required.")
        denominator=metric("total","Selected mapped purchase emissions subtotal",total,"kg CO2e",
            [r["source_row"]["emissions_component"]["id"] for r in rows],"Sum of distinct mapped emissions components")
        if total==0:gap("Zero mapped subtotal has no defined contribution percentages or emissions hotspots.")
        views={}
        for view in ("supplier","category"):
            groups={}
            for row in rows:
                key=row["source_row"]["link"]["supplier_id"] if view=="supplier" else str(row["source_row"]["category"])
                groups.setdefault(key,[]).append(row)
            contributions=[]
            for index,(key,items) in enumerate(sorted(groups.items()),1):
                amount=sum((r["kg_co2e"] for r in items),Decimal(0))
                component=metric(view+"-"+str(index),"Selected "+view+" contribution: "+key,amount,"kg CO2e",
                    [r["source_row"]["emissions_component"]["id"] for r in items],"Sum of distinct mapped components in this "+view+" group")
                share=None
                if total>0:share=metric(view+"-share-"+str(index),"Selected "+view+" subtotal share: "+key,
                    100*amount/total,"%",[component["id"],denominator["id"]],"100 * group contribution / selected mapped subtotal")
                contributions.append({"id":key,"contribution_metric_id":component["id"],"kg_co2e":serialize(amount),
                    "share_metric_id":None if share is None else share["id"],"percent_of_selected_subtotal":None if share is None else share["value"],
                    "hotspot":total>0 and 100*amount/total>=threshold,"priority_group":None})
            contributions.sort(key=lambda c:(-number(c["kg_co2e"]),c["id"]))
            last=None;rank=0
            for item in contributions:
                if item["kg_co2e"]!=last:rank+=1;last=item["kg_co2e"]
                item["priority_group"]=rank if total>0 else None
            views[view]=contributions
    return {"hotspot_review":review,"mapping_result_ids":selected,"gwp_basis":gwp,"hotspot_threshold_percent":serialize(threshold),
        "denominator_metric_id":denominator["id"],"denominator_scope":"Selected mapped purchases only", "selected_mapping_coverage_complete":complete,
        "full_scope_3_coverage_verified":False,"views":views,"procurement_authorized":False,
        "limits":"Supplier and category views are alternate partitions of one selected subtotal, not additive inventories. Point-contribution order does not quantify uncertainty, supplier risk, reduction feasibility, capacity or whole-footprint materiality."}
