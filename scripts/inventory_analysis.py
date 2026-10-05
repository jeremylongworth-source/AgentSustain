"""Compare selected inventory accounts and rank nonoverlapping contributions."""
import calendar
import copy
from datetime import date
from decimal import Decimal, localcontext
import json

from .data_tools import convert, number, serialize
from .ghg_inventory import build_inventory, _diagnostic
from .scope_accounting import _evidence, _text
from .scope3_accounting import STANDARD, _result, _gap, _finish


def _retain_checks(result, checked):
    keys = {(g["field"], g["reason"], g["impact"], g["remedy"]) for g in result["data_gaps"]}
    for gap in checked["data_gaps"]:
        key = (gap["field"], gap["reason"], gap["impact"], gap["remedy"])
        if key not in keys:
            result["data_gaps"].append(copy.deepcopy(gap))
            keys.add(key)
    for item in checked["diagnostics"]:
        if item["code"] not in {"INVENTORY_SELECTION", "SYNTHETIC_FIXTURE"} and item not in result["diagnostics"]:
            result["diagnostics"].append(copy.deepcopy(item))


def _inventory(state, ident, result, fixture_mode):
    source = next((r for r in state["results"] if r["id"] == ident), None)
    if source is None or source["skill"] != "build-ghg-inventory" or source["status"] not in {"completed", "partial"} or len(source["metrics"]) != 1:
        raise ValueError("Supported inventory result required")
    selection = _diagnostic(source, "INVENTORY_SELECTION")
    included = selection["included"]
    direct = [x["result_id"] for x in included if x["scope"] == "scope_1"]
    energy = [x["result_id"] for x in included if x["scope"] == "scope_2"]
    categories = [x["result_id"] for x in included if x["scope"] == "scope_3"]
    if len(direct) > 1 or len(energy) > 1:
        raise ValueError("Inventory has multiple scope accounts")
    verification_id = result["id"] + "-inventory-check"
    known = {r["id"] for r in state["results"]}
    while verification_id in known:
        verification_id += "-next"
    output = build_inventory(state, direct[0] if direct else None, energy[0] if energy else None, categories,
                             selection["category_screening"], selection["coverage_review"], verification_id, fixture_mode)
    checked = output["result"]
    _retain_checks(result, checked)
    if len(checked["metrics"]) != 1:
        raise ValueError("Inventory could not be revalidated")
    metric = source["metrics"][0]
    observed = convert(metric["value"], metric["unit"], "kg CO2e")["value"]
    if (serialize(observed) != serialize(number(checked["metrics"][0]["value"]))
            or metric["period"] != state["reporting_period"] or metric["boundary_id"] != state["organizational_boundary"]["id"]
            or metric["method"] != checked["metrics"][0]["method"]
            or set(metric["calculation"]["inputs"]) != set(checked["metrics"][0]["calculation"]["inputs"])
            or not set(checked["metrics"][0]["evidence_ids"]) <= set(metric["evidence_ids"])):
        raise ValueError("Inventory quantity/context does not reproduce")
    if source["status"] == "partial" or checked["status"] == "partial":
        _gap(result, "PARTIAL_INVENTORY", f"Inventory {ident} is partial; analysis describes selected supported emissions only.")
    return source, selection, observed


def _metric(result_id, suffix, name, value, unit, state, refs, inputs, formula):
    return {"id":result_id + "-" + suffix,"name":name,"value":serialize(value),"unit":unit,
            "period":copy.deepcopy(state["reporting_period"]),"boundary_id":state["organizational_boundary"]["id"],"evidence_ids":sorted(refs),
            "method":{"name":"Selected GHG inventory analysis","version":"2011 with 2013 corrections","source":STANDARD},"assumption":None,
            "uncertainty":{"kind":"unquantified","description":"Uncertainty from source accounts and comparability/coverage assessment is not quantified.","value":None,"unit":None},
            "calculation":{"formula":formula,"inputs":list(dict.fromkeys(inputs)),"conversions":["Inventory/component values normalized to kg CO2e"],
                           "rounding":"34-digit Decimal arithmetic; JSON serialization"}}


def _periods_comparable(prior, current):
    start, end = date.fromisoformat(prior["start"]), date.fromisoformat(prior["end"])
    after_start, after_end = date.fromisoformat(current["start"]), date.fromisoformat(current["end"])
    if end >= after_start:
        return False
    annual = all(d.month == m and d.day == day for d,m,day in ((start,1,1),(end,12,31),(after_start,1,1),(after_end,12,31))) and start.year == end.year and after_start.year == after_end.year
    monthly = (start.day == after_start.day == 1 and start.year == end.year and start.month == end.month
               and after_start.year == after_end.year and after_start.month == after_end.month
               and end.day == calendar.monthrange(end.year,end.month)[1]
               and after_end.day == calendar.monthrange(after_end.year,after_end.month)[1])
    return annual or monthly or (end - start).days == (after_end - after_start).days


def _history_preserved(prior_state, state, source, selection):
    prior_metrics = {m["id"]:m for r in prior_state["results"] for m in r["metrics"]}
    current_metrics = {m["id"]:m for r in state["results"] for m in r["metrics"]}
    prior_evidence = {e["id"]:e for e in prior_state["evidence"]}
    current_evidence = {e["id"]:e for e in state["evidence"]}
    prior_results = {r["id"]:r for r in prior_state["results"]}
    current_results = {r["id"]:r for r in state["results"]}
    prior_factors = {f["id"]:f for f in prior_state["emission_factors"]}
    current_factors = {f["id"]:f for f in state["emission_factors"]}
    for ident in [source["id"]] + [x["result_id"] for x in selection["included"]]:
        if prior_results.get(ident) != current_results.get(ident):
            return False
    for included in selection["included"]:
        account = prior_results[included["result_id"]]
        record = _diagnostic(account,"SCOPE3_CATEGORY" if included["scope"] == "scope_3" else "SCOPE_METHOD")
        for component in record["components"]:
            if prior_factors.get(component["factor_id"]) != current_factors.get(component["factor_id"]):
                return False
    pending = [source["metrics"][0]["id"]]
    visited = set()
    while pending:
        ident = pending.pop()
        if ident in visited:
            continue
        visited.add(ident)
        if ident in prior_metrics:
            item = prior_metrics[ident]
            if item != current_metrics.get(ident):
                return False
        else:
            item = prior_evidence.get(ident)
            if item is None or item != current_evidence.get(ident):
                return False
        if item["calculation"]:
            pending.extend(item["calculation"]["inputs"])
    return True


def _coverage_signature(state, selection):
    results = {r["id"]:r for r in state["results"]}
    signature = []
    for item in selection["included"]:
        source = results[item["result_id"]]
        record = _diagnostic(source,"SCOPE3_CATEGORY" if item["scope"] == "scope_3" else "SCOPE_METHOD")
        source_coverage = {}
        for accepted in record["accepted"]:
            source_id = accepted["source_id"]
            source = source_coverage.setdefault(source_id,{"gases":{},"allocations":set(),"lifecycle":set()})
            source["allocations"].add(str(number(accepted.get("allocation_fraction",1))))
            for gas in accepted.get("gases",[]):
                source["gases"][gas] = source["gases"].get(gas,Decimal(0)) + number(accepted.get("activity_fraction",1))
            if item["scope"] == "scope_3":
                component = next(c for c in record["components"] if c["metric_id"] == accepted["metric_id"])
                source["lifecycle"].add((component["policy"]["lifecycle_boundary"],component["policy"]["allocation_basis"]))
        signature.append((item["scope"],item["category"],item["scope_2_method"],source_coverage))
    screening = sorted((x["category"],x["status"]) for x in selection["category_screening"])
    return sorted(signature,key=lambda x:(x[0],x[1] or 0)),screening


def compare_inventories(state, prior_state, prior_inventory_id, current_inventory_id, comparability_review, result_id, fixture_mode=False):
    result = _result(state,"compare-ghg-inventories",result_id)
    # _result performs full prior snapshot validation as well.
    _result(prior_state,"compare-ghg-inventories",result_id)
    known = {e["id"] for e in state["evidence"]}
    if not isinstance(comparability_review,dict):
        raise ValueError("Comparability review required")
    current_reviews = {r["id"]:r for r in result["review_requirements"]}
    for prior_review in prior_state["review_requirements"]:
        if prior_review["status"] == "open" and prior_review["id"] not in current_reviews:
            result["review_requirements"].append(copy.deepcopy(prior_review))
            result["review_states"].append(prior_review["state"])
    try:
        prior, before_record, before = _inventory(prior_state,prior_inventory_id,result,fixture_mode)
        current, after_record, after = _inventory(state,current_inventory_id,result,fixture_mode)
        if not _history_preserved(prior_state,state,prior,before_record):
            raise ValueError("Prior inventory/component lineage must be retained unchanged in current state")
        for key in ("id","approach","facility_ids","exclusions"):
            if state["organizational_boundary"][key] != prior_state["organizational_boundary"][key]:
                raise ValueError("Boundary differs; supply a documented restated prior inventory")
        if state["organization"]["id"] != prior_state["organization"]["id"] or before_record["gwp_basis"] != after_record["gwp_basis"]:
            raise ValueError("Organization or GWP basis differs")
        if _coverage_signature(prior_state,before_record) != _coverage_signature(state,after_record):
            raise ValueError("Selected scopes, scope 2 method, category/source coverage or screening differs")
        if not _periods_comparable(prior["metrics"][0]["period"],current["metrics"][0]["period"]):
            raise ValueError("Periods overlap or have incompatible cadence/duration")
        review = comparability_review
        if (review.get("confirmed") is not True or review.get("prior_inventory_id") != prior_inventory_id or review.get("current_inventory_id") != current_inventory_id
                or not _evidence(review,known) or any(not _text(review.get(k)) for k in ("reviewer","rationale","boundary_changes_assessment","coverage_changes_assessment","factor_changes_assessment","restatement_assessment"))):
            raise ValueError("Explicit evidence-backed comparability and change assessment required")
        refs = set(prior["evidence_ids"] + current["evidence_ids"] + review["evidence_ids"])
        inputs = [prior["metrics"][0]["id"],current["metrics"][0]["id"]]
        with localcontext() as context:
            context.prec = 34
            delta = after - before
            result["metrics"].append(_metric(result_id,"absolute-change","Selected inventory absolute change",delta,"kg CO2e",state,refs,inputs,"Current selected inventory kg CO2e - prior selected inventory kg CO2e"))
            if before > 0:
                result["metrics"].append(_metric(result_id,"percentage-change","Selected inventory percentage change",delta / before * 100,"%",state,refs,inputs,"(current - prior) / prior * 100"))
            else:
                _gap(result,"PERCENTAGE_DENOMINATOR_REQUIRED","Prior selected inventory is zero; absolute change is available but percentage change is undefined.")
        result["evidence_ids"] = sorted(refs)
        result["diagnostics"].append({"code":"INVENTORY_COMPARISON","message":json.dumps({"prior_inventory_id":prior_inventory_id,"current_inventory_id":current_inventory_id,
            "prior_period":prior["metrics"][0]["period"],"current_period":current["metrics"][0]["period"],"comparability_review":review,
            "limits":"Arithmetic change in selected supported emissions; not an attributable or verified reduction. Calendar-period lengths may differ; no annualization performed."},sort_keys=True)})
    except (ValueError,KeyError,TypeError) as error:
        _gap(result,"INVENTORY_COMPARABILITY_REQUIRED",str(error))
        result["metrics"] = []
    return _finish(state,result,bool(result["metrics"]),fixture_mode,"Compare explicitly reconciled inventory accounts without rewriting history")


def identify_hotspots(state, inventory_id, level, coverage_review, result_id, fixture_mode=False):
    result = _result(state,"identify-emission-hotspots",result_id)
    if level not in {"scope","category","source"} or not isinstance(coverage_review,dict):
        raise ValueError("Supported contribution level and review required")
    known = {e["id"] for e in state["evidence"]}
    try:
        source, selection, denominator = _inventory(state,inventory_id,result,fixture_mode)
        if (coverage_review.get("confirmed") is not True or coverage_review.get("inventory_id") != inventory_id or coverage_review.get("level") != level
                or not _evidence(coverage_review,known) or not _text(coverage_review.get("rationale"))):
            raise ValueError("Explicit inventory/level and evidenced nonoverlap assessment required")
        results = {r["id"]:r for r in state["results"]}
        metrics = {m["id"]:m for r in state["results"] for m in r["metrics"]}
        groups = {}
        for item in selection["included"]:
            account = results[item["result_id"]]
            if level == "category" and item["scope"] != "scope_3":
                continue
            if level in {"scope","category"}:
                key = (item["scope"],item["category"] if level == "category" else None,None)
                contributions = [(account["metrics"][0]["id"],Decimal(1))]
            else:
                record = _diagnostic(account,"SCOPE3_CATEGORY" if item["scope"] == "scope_3" else "SCOPE_METHOD")
                contributions = []
                for accepted in record["accepted"]:
                    key = (item["scope"],item["category"],accepted["source_id"])
                    with localcontext() as context:
                        context.prec = 34
                        factor = number(accepted.get("activity_fraction",1)) * number(accepted.get("allocation_fraction",1))
                    contributions.append((key,accepted["metric_id"],factor))
            if level in {"scope","category"}:
                contributions = [(key,ident,fraction) for ident,fraction in contributions]
            for key,ident,fraction in contributions:
                group = groups.setdefault(key,{"value":Decimal(0),"inputs":[],"evidence_ids":set()})
                metric = metrics[ident]
                with localcontext() as context:
                    context.prec = 34
                    group["value"] += convert(metric["value"],metric["unit"],"kg CO2e")["value"] * fraction
                group["inputs"].append(ident)
                group["evidence_ids"].update(metric["evidence_ids"])
        if not groups:
            raise ValueError("No supported contributions at selected level")
        with localcontext() as context:
            context.prec = 34
            represented = sum((g["value"] for g in groups.values()),Decimal(0))
        if represented > denominator or (level != "category" and serialize(represented) != serialize(denominator)):
            raise ValueError("Contribution coverage does not reconcile with inventory denominator")
        ranked = sorted(groups.items(),key=lambda pair:(-pair[1]["value"],str(pair[0])))
        refs = set(source["evidence_ids"] + coverage_review["evidence_ids"])
        ranking = []
        for rank,(key,group) in enumerate(ranked,1):
            scope,category,source_id = key
            label = source_id or (f"category {category}" if category is not None else scope)
            result["metrics"].append(_metric(result_id,f"rank-{rank}-emissions",f"Rank {rank}: {label} emissions",group["value"],"kg CO2e",state,refs,group["inputs"],"Sum of nonoverlapping selected contributions with recorded allocation applied once"))
            share = None
            if denominator > 0:
                with localcontext() as context:
                    context.prec = 34
                    share = group["value"] / denominator * 100
                result["metrics"].append(_metric(result_id,f"rank-{rank}-share",f"Rank {rank}: {label} inventory share",share,"%",state,refs,group["inputs"] + [source["metrics"][0]["id"]],"Contribution / selected inventory denominator * 100"))
            ranking.append({"rank":rank,"scope":scope,"category":category,"source_id":source_id,"value_kg_CO2e":serialize(group["value"]),"share_percent":serialize(share) if share is not None else None})
        if denominator == 0:
            _gap(result,"PERCENTAGE_DENOMINATOR_REQUIRED","Zero inventory supports zero contribution quantities, not percentage shares.")
        result["evidence_ids"] = sorted(refs)
        result["diagnostics"].append({"code":"EMISSION_HOTSPOTS","message":json.dumps({"inventory_id":inventory_id,"level":level,"ranking":ranking,
            "denominator_metric_id":source["metrics"][0]["id"],"denominator_kg_CO2e":serialize(denominator),"coverage_review":coverage_review,
            "limits":"Shares of selected supported inventory emissions, with missing coverage retained; ranking is not feasible or verified reduction potential."},sort_keys=True)})
    except (ValueError,KeyError,TypeError) as error:
        _gap(result,"HOTSPOT_COVERAGE_REQUIRED",str(error))
        result["metrics"] = []
    return _finish(state,result,bool(result["metrics"]),fixture_mode,"Rank one reconciled inventory contribution level with an explicit denominator")
