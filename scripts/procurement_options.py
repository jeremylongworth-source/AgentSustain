"""Conditional equivalent-service procurement comparisons from reproduced mappings."""
import copy
from datetime import date
from decimal import localcontext, Decimal
import re

from .data_tools import UNITS, convert, number, serialize
from .finance_projects import _review
from .inventory_analysis import _retain_checks
from .supplier_comparison import _record


def evaluate(state, parameters, refs, result, gap):
    from .supplier_tools import run_suppliers
    review=parameters["comparison_review"];known={e["id"] for e in state["evidence"]}
    refs.update(_review(review,known,("reviewer_role","rationale","scope_boundary","functional_unit","service_requirements",
        "lifetime_basis","lifecycle_boundary","allocation_basis","gwp_basis","scenario_assumptions","risk_tradeoffs")))
    if (review.get("period")!=state["reporting_period"] or review.get("boundary_id")!=state["organizational_boundary"]["id"]
            or not isinstance(review.get("coverage_complete"),bool)):
        raise ValueError("Current buyer period and boundary required for procurement comparison.")
    fixture=parameters.get("fixture_mode",False)
    if not isinstance(fixture,bool):raise ValueError("Fixture mode must be boolean.")
    sources={r["id"]:r for r in state["results"]};metrics={m["id"]:m for r in state["results"] for m in r["metrics"]}
    owners={m["id"]:r for r in state["results"] for m in r["metrics"]}
    def resolve(key):
        metric=metrics.get(key)
        if metric is None or owners[key]["status"] not in {"completed","partial"} or not metric["evidence_ids"]:
            raise ValueError("Supported sourced metric required.")
        if metric["period"]!=state["reporting_period"] or metric["boundary_id"]!=state["organizational_boundary"]["id"]:
            raise ValueError("Source quantity period and buyer boundary must match comparison.")
        number(metric["value"]);refs.update(metric["evidence_ids"]);return metric
    options=[];checked_maps={};components=set();purchases=set();categories=None
    for label in ("baseline","alternative"):
        option=parameters[label]
        if (not isinstance(option,dict) or set(option)!={"id","supplier_id","mapping_result_id","link_ids","functional_metric_id","cost_metric_id"}
                or any(not isinstance(option[f],str) or not option[f].strip() for f in ("id","supplier_id","mapping_result_id","functional_metric_id"))):
            raise ValueError("Exact identified option with sourced mapping, links, service and optional cost metric required.")
        selected=option["link_ids"]
        if not isinstance(selected,list) or not selected or any(not isinstance(i,str) for i in selected) or len(set(selected))!=len(selected):
            raise ValueError("Distinct selected purchase-link IDs required.")
        key=option["mapping_result_id"];source=sources.get(key)
        if source is None or source["skill"]!="map-supply-chain-emissions" or source["status"] not in {"completed","partial"}:
            raise ValueError("Supported purchase mapping required.")
        if key not in checked_maps:
            inputs=copy.deepcopy(_record(source,"SUPPLIER_INPUTS"));inputs["result_id"]=parameters["result_id"]+"-check-"+key;inputs["fixture_mode"]=fixture
            while inputs["result_id"] in sources:inputs["result_id"]+="-next"
            checked=run_suppliers(state,source["skill"],inputs)["result"]
            retained=dict(checked,diagnostics=[d for d in checked["diagnostics"] if d["code"] not in {"SUPPLIER_INPUTS","SUPPLY_CHAIN_MAPPING"}])
            _retain_checks(result,retained);result["assumptions"]=list(dict.fromkeys(result["assumptions"]+checked["assumptions"]))
            if checked["status"]=="blocked":raise ValueError("Option purchase mapping reproduction blocked.")
            report=_record(checked,"SUPPLY_CHAIN_MAPPING")
            if report!=_record(source,"SUPPLY_CHAIN_MAPPING"):raise ValueError("Option mapping differs from reproduced source report.")
            checked_maps[key]=report;refs.update(source["evidence_ids"]);refs.update(checked["evidence_ids"])
        report=checked_maps[key]
        if report["mapping_review"]["scope_boundary"]!=review["scope_boundary"]:raise ValueError("Option mapping scope must match comparison.")
        rows=[r for r in report["rows"] if r["link"]["id"] in selected]
        if len(rows)!=len(selected):raise ValueError("Every selected link must resolve in its reproduced mapping.")
        selected_categories=set()
        for row in rows:
            link=row["link"];component=row["emissions_component"]
            if link["supplier_id"]!=option["supplier_id"] or component["id"] in components or link["purchase_metric_id"] in purchases:
                raise ValueError("Distinct attributed option components and activities must match the declared supplier.")
            components.add(component["id"]);purchases.add(link["purchase_metric_id"]);selected_categories.add(row["category"])
            if any(link["allocation_review"][f]!=review[f] for f in ("lifecycle_boundary","allocation_basis")):
                raise ValueError("Comparable declared lifecycle and allocation basis required.")
            category=_record(sources[link["category_result_id"]],"SCOPE3_CATEGORY")
            if category["coverage_review"]["gwp_basis"]!=review["gwp_basis"]:raise ValueError("Comparable declared GWP basis required.")
            resolve(component["id"])
            if number(convert(component["value"],component["unit"],"kg CO2e")["value"])<0:
                raise ValueError("Gross option components cannot net credits or removals.")
        if categories is None:categories=selected_categories
        if categories!=selected_categories:raise ValueError("Alternative selected category coverage must match baseline.")
        function=resolve(option["functional_metric_id"])
        if function["unit"] not in UNITS or UNITS[function["unit"]][0]=="co2e" or number(function["value"])<=0:
            raise ValueError("Positive sourced physical service quantity required, not emissions or spend.")
        costs=option["cost_metric_id"]
        if costs is not None and (not isinstance(costs,str) or not costs.strip()):raise ValueError("Optional cost metric must be a known ID or null.")
        cost=None if costs is None else resolve(costs)
        options.append({"option":copy.deepcopy(option),"rows":copy.deepcopy(rows),"functional_quantity":copy.deepcopy(function),
            "cost":copy.deepcopy(cost),"mapping_coverage_complete":report["mapping_review"]["coverage_complete"]})
    if options[0]["option"]["id"]==options[1]["option"]["id"]:raise ValueError("Distinct baseline and alternative IDs required.")
    base,after=options
    if number(convert(after["functional_quantity"]["value"],after["functional_quantity"]["unit"],base["functional_quantity"]["unit"])["value"])!=number(base["functional_quantity"]["value"]):
        raise ValueError("Sourced equivalent service quantities must match; no automatic mass or lifetime scaling.")
    cost_review=parameters["cost_review"];cost_delta=None
    if base["cost"] is None or after["cost"] is None:
        if cost_review is not None:raise ValueError("Missing paired cost quantities require cost_review=null.")
        gap("Comparable paired costs are missing; no cost premium, savings or affordability inferred.")
    else:
        from .finance_tools import OPERATIONS as finance_operations, run_finance
        refs.update(_review(cost_review,known,("reviewer_role","rationale","currency","cost_scope","valuation_date","dollar_basis","tax_basis")))
        if (not re.fullmatch(r"[A-Z]{3}",cost_review["currency"]) or cost_review["dollar_basis"] not in {"real","nominal"}
                or cost_review["tax_basis"] not in {"pre_tax","after_tax"}
                or not date.fromisoformat(state["reporting_period"]["start"])<=date.fromisoformat(cost_review["valuation_date"])<=date.fromisoformat(state["reporting_period"]["end"])):
            raise ValueError("Explicit comparable currency, valuation, dollar and tax basis required.")
        verified_finance=set()
        for cost in (base["cost"],after["cost"]):
            if cost["unit"]!=cost_review["currency"] or number(cost["value"])<0:raise ValueError("Comparable nonnegative gross costs in the declared currency required; no exchange conversion.")
            pending=[cost["id"]];seen=set()
            while pending:
                key=pending.pop()
                if key in seen or key not in metrics:continue
                seen.add(key)
                if any(d["code"]=="NONCASH_SHADOW_PRICE" for d in owners[key]["diagnostics"]):raise ValueError("Shadow-price exposure is not a procurement cash cost.")
                owner=owners[key]
                if owner["skill"] in finance_operations and owner["id"] not in verified_finance:
                    basis=copy.deepcopy(_record(owner,"FINANCIAL_ANALYSIS_BASIS"))
                    if any(basis["analysis_review"].get(f)!=cost_review[f] for f in ("currency","valuation_date","dollar_basis","tax_basis")):
                        raise ValueError("Financial source and selected quote economic basis must match.")
                    basis["result_id"]=parameters["result_id"]+"-finance-check-"+owner["id"]
                    while basis["result_id"] in sources:basis["result_id"]+="-next"
                    checked=run_finance(state,owner["skill"],basis)["result"]
                    _retain_checks(result,dict(checked,diagnostics=[d for d in checked["diagnostics"] if d["code"]!="FINANCIAL_ANALYSIS_BASIS"]));refs.update(checked["evidence_ids"])
                    content=lambda entries:[{k:v for k,v in m.items() if k!="id"} for m in entries]
                    if checked["status"]=="blocked" or not checked["metrics"] or content(checked["metrics"])!=content(owner["metrics"]):
                        raise ValueError("Financial option cost does not reproduce from current source inputs.")
                    verified_finance.add(owner["id"])
                pending.extend(metrics[key]["calculation"]["inputs"] if metrics[key]["calculation"] else [])
        cost_delta=number(after["cost"]["value"])-number(base["cost"]["value"])
    if not review["coverage_complete"] or not all(o["mapping_coverage_complete"] for o in options):
        gap("Selected mapping coverage is incomplete; comparison does not establish whole-product or full lifecycle superiority.")
    assumption="Conditional equivalent-service selected lifecycle comparison; mutually exclusive alternatives are not an additive inventory."
    if assumption not in result["assumptions"]:result["assumptions"].append(assumption)
    def metric(suffix,name,value,unit,inputs,formula):
        item={"id":parameters["result_id"]+"-"+suffix,"name":name,"value":serialize(value),"unit":unit,"period":copy.deepcopy(state["reporting_period"]),
            "boundary_id":state["organizational_boundary"]["id"],"evidence_ids":sorted(refs),"method":{"name":"Selected procurement option comparison","version":"0.1.0","source":"repository:docs/supplier-contract.md"},
            "assumption":assumption,"uncertainty":{"kind":"unquantified","description":"Source factor/activity, service equivalence, lifetime, coverage and cost uncertainty remains unquantified; point differences are conditional.","value":None,"unit":None},
            "calculation":{"formula":formula,"inputs":inputs,"conversions":["Emissions normalized to kg CO2e; equivalent service unit conversion checked; no currency conversion"],"rounding":"34-digit Decimal arithmetic; JSON serialization"}}
        result["metrics"].append(item);return item
    with localcontext() as context:
        context.prec=34;totals=[]
        for label,option in zip(("baseline","alternative"),options):
            value=sum((number(convert(r["emissions_component"]["value"],r["emissions_component"]["unit"],"kg CO2e")["value"]) for r in option["rows"]),Decimal(0))
            if value<0:raise ValueError("Nonnegative gross option emissions required.")
            totals.append(metric(label,label.title()+" selected procurement emissions",value,"kg CO2e",
                [r["emissions_component"]["id"] for r in option["rows"]],"Sum of distinct selected option components"))
        reduction=number(totals[0]["value"])-number(totals[1]["value"])
        delta=metric("reduction","Baseline minus alternative selected emissions",reduction,"kg CO2e",[m["id"] for m in totals],"Baseline - alternative selected emissions")
        percent=None
        if number(totals[0]["value"])>0:percent=metric("reduction-percent","Conditional selected emissions reduction percent",100*reduction/number(totals[0]["value"]),"%",[delta["id"],totals[0]["id"]],"100 * (baseline - alternative) / baseline")
        else:gap("Zero baseline has no defined emissions reduction percentage.")
        premium=None if cost_delta is None else metric("cost-premium","Alternative minus baseline selected cost",cost_delta,cost_review["currency"],
            [base["cost"]["id"],after["cost"]["id"]],"Alternative selected cost - baseline selected cost")
    gate=parameters["result_id"]+"-option-review"
    while any(r["id"]==gate for r in result["review_requirements"]):gate+="-next"
    result["review_requirements"].append({"id":gate,"state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Functional/lifetime/lifecycle equivalence, option uncertainty, tradeoffs and costs require review before claims or procurement decisions.","scope":"Selected procurement options","reviewer_role":"procurement and lifecycle assessment reviewer","status":"open","resolution":None})
    if fixture:result["diagnostics"].append({"code":"SYNTHETIC_FIXTURE","message":"Synthetic procurement comparison only; no real lower-carbon product finding."})
    return {"comparison_review":review,"cost_review":cost_review,"options":options,"baseline_metric_id":totals[0]["id"],"alternative_metric_id":totals[1]["id"],
        "reduction_metric_id":delta["id"],"reduction_percent_metric_id":None if percent is None else percent["id"],"cost_premium_metric_id":None if premium is None else premium["id"],
        "alternative_has_lower_selected_emissions":reduction>0,"selected_supplier_id":None,"procurement_authorized":False,"public_claim_authorized":False,
        "full_lifecycle_superiority_verified":False,"limits":"Selected sourced quantities only; functional equivalence and source fitness are supplied review. No realized saving, environmental superiority, whole-footprint inventory reduction, investment return or supplier selection inferred."}
