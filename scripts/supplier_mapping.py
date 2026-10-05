"""Link sourced purchase activities to reproduced Scope 3 components."""
import copy

from .finance_projects import _review
from .data_tools import UNITS
from .inventory_analysis import _retain_checks
from .scope3_accounting import calculate_category
from .supplier_comparison import _record


def map_chain(state, parameters, refs, result, gap):
    fixture=parameters.get("fixture_mode",False)
    if not isinstance(fixture,bool): raise ValueError("Fixture mode must be explicitly boolean.")
    known={e["id"] for e in state["evidence"]};sources={r["id"]:r for r in state["results"]}
    metrics={m["id"]:m for r in state["results"] for m in r["metrics"]}
    suppliers={s["id"]:s for s in state["suppliers"]}
    review=parameters["mapping_review"]
    refs.update(_review(review,known,("reviewer_role","rationale","scope_boundary","nonoverlap_assessment")))
    if (review.get("period")!=state["reporting_period"] or review.get("boundary_id")!=state["organizational_boundary"]["id"]
            or not isinstance(review.get("coverage_complete"),bool)):
        raise ValueError("Current buyer period/boundary and explicit selected purchase coverage required.")
    links=parameters["links"]
    if not isinstance(links,list) or not links: raise ValueError("Nonempty sourced purchase-to-supplier links required.")
    ids=set();purchases=set();activities=set();components=set();rows=[];checks={}
    for link in links:
        if (not isinstance(link,dict) or set(link)!={"id","supplier_id","purchase_metric_id","purchase_reference","category_result_id","source_id","evidence_ids","allocation_review"}
                or any(not isinstance(link[f],str) or not link[f].strip() for f in
                    ("id","supplier_id","purchase_metric_id","purchase_reference","category_result_id","source_id"))
                or link["id"] in ids or link["purchase_reference"] in purchases or link["purchase_metric_id"] in activities):
            raise ValueError("Unique link, line-specific purchase reference and physical activity required.")
        ids.add(link["id"]);purchases.add(link["purchase_reference"]);activities.add(link["purchase_metric_id"])
        supplier=suppliers.get(link["supplier_id"])
        if supplier is None or not supplier["evidence_ids"]: raise ValueError("Known sourced supplier required.")
        refs.update(supplier["evidence_ids"]);refs.update(_review(dict(link,confirmed=True),known,()))
        category=sources.get(link["category_result_id"])
        if category is None or category["skill"]!="calculate-scope-3-category" or category["status"] not in {"completed","partial"}:
            raise ValueError("Supported physical-activity category result required, not a corporate total or spend proxy.")
        if category["id"] not in checks:
            method=_record(category,"SCOPE3_CATEGORY")
            check_id=parameters["result_id"]+"-check-"+category["id"]
            while check_id in sources:check_id+="-next"
            checked=calculate_category(state,method["category"],method["sources"],method["components"],method["coverage_review"],check_id,fixture)["result"]
            _retain_checks(result,checked)
            result["assumptions"]=list(dict.fromkeys(result["assumptions"]+checked["assumptions"]))
            refs.update(checked["evidence_ids"])
            content=lambda entries:[{k:v for k,v in m.items() if k!="id"} for m in entries]
            if not checked["metrics"] or content(checked["metrics"])!=content(category["metrics"]):
                raise ValueError("Category quantity and context do not reproduce from current activity/factor inputs.")
            record=_record(checked,"SCOPE3_CATEGORY")
            if record["accepted"]!=method["accepted"]:
                raise ValueError("Accepted category source coverage changed during reproduction.")
            checks[category["id"]]=record
        record=checks[category["id"]]
        accepted=[a for a in record["accepted"] if a["source_id"]==link["source_id"]]
        if len(accepted)!=1 or accepted[0]["activity_id"]!=link["purchase_metric_id"]:
            raise ValueError("Purchase activity must be the accepted category source activity.")
        accepted=accepted[0];metric=metrics.get(accepted["metric_id"]);activity=metrics.get(link["purchase_metric_id"])
        if metric is None or activity is None or metric["id"] in components:
            raise ValueError("Distinct supported emissions component required; do not map a component twice.")
        if activity["unit"] not in UNITS or UNITS[activity["unit"]][0]=="co2e":
            raise ValueError("Purchase activity must have physical mass, volume, energy or count units; emissions are not purchase activity.")
        components.add(metric["id"])
        component=next(c for c in record["components"] if c["source_id"]==link["source_id"])
        allocation=link["allocation_review"]
        refs.update(_review(allocation,known,("supplier_relationship","product_scope","rationale","lifecycle_boundary","allocation_basis")))
        if any(allocation[f]!=component["policy"].get(f) for f in ("lifecycle_boundary","allocation_basis")):
            raise ValueError("Mapping lifecycle and allocation must match the category's supplied physical basis.")
        refs.update(category["evidence_ids"]);refs.update(activity["evidence_ids"]);refs.update(metric["evidence_ids"])
        rows.append({"link":copy.deepcopy(link),"category":record["category"],"category_result_status":category["status"],
            "purchase_activity":copy.deepcopy(activity),"emissions_component":copy.deepcopy(metric),
            "allocation_reapplied":False,"supplier_corporate_emissions_attributed":False})
    if not review["coverage_complete"]:gap("Selected purchase mapping coverage is incomplete; unmapped purchases are not zero emissions.")
    if fixture:
        result["diagnostics"].append({"code":"SYNTHETIC_FIXTURE","message":"Synthetic purchase/category mapping only; not a real supply-chain inventory."})
    return {"mapping_review":review,"rows":rows,"portfolio_total":None,"procurement_authorized":False,
        "limits":"Selected sourced physical activity/component links only. Supplier identity, product scope and allocation judgments are supplied review, not source authentication. No corporate-total allocation or emissions factor derived."}
