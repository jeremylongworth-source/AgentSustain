"""Build an explicitly selected inventory account, preserving partial coverage."""
import copy
from decimal import Decimal, localcontext
import json

from .contract_validation import validate_state
from .data_tools import convert, number, serialize
from .scope_accounting import _evidence, _text
from .scope_accounting import compose_scope
from .scope3_accounting import CATEGORIES, STANDARD, calculate_category, _result, _gap, _finish


def _diagnostic(result, code):
    matches = [item for item in result["diagnostics"] if item["code"] == code]
    if len(matches) != 1:
        raise ValueError("Expected one method record")
    value = json.loads(matches[0]["message"])
    if not isinstance(value, dict):
        raise ValueError("Method record must be an object")
    return value


def build_inventory(state, scope1_result_id, scope2_result_id, scope3_result_ids, category_screening, coverage_review, result_id, fixture_mode=False):
    result = _result(state, "build-ghg-inventory", result_id)
    if not isinstance(scope3_result_ids, list) or len(scope3_result_ids) != len(set(scope3_result_ids)) or not isinstance(category_screening, list) or not isinstance(coverage_review, dict):
        raise ValueError("Explicit inventory selections and category screening required")
    results = {r["id"]: r for r in state["results"]}
    known = {e["id"] for e in state["evidence"]}
    refs, inputs, included, components = set(), [], [], set()
    total = Decimal(0)
    gwp = coverage_review.get("gwp_basis")
    if coverage_review.get("confirmed") is not True or not _text(coverage_review.get("rationale")) or not _evidence(coverage_review, known) or not _text(gwp):
        _gap(result, "INVENTORY_COVERAGE_REQUIRED", "Inventory source nonoverlap, common GWP basis and scope coverage require an evidenced review.")
    else:
        refs.update(coverage_review["evidence_ids"])
    screening = {}
    for item in category_screening:
        if not isinstance(item, dict) or type(item.get("category")) is not int or item["category"] not in CATEGORIES or item["category"] in screening:
            raise ValueError("Screening requires unique category integers 1–15")
        screening[item["category"]] = item
    if set(screening) != set(CATEGORIES):
        _gap(result, "CATEGORY_SCREENING_REQUIRED", "Screen all 15 categories; omitted categories are not zero.")
    for category, item in screening.items():
        if not _evidence(item, known) or not _text(item.get("rationale")) or item.get("status") not in {"applicable", "not_applicable", "excluded", "unknown"}:
            _gap(result, "CATEGORY_SCREENING_REQUIRED", f"Category {category} requires an evidenced screening status and rationale.")
        else:
            refs.update(item["evidence_ids"])
            if item["status"] in {"excluded", "unknown"}:
                _gap(result, "INCOMPLETE_CATEGORY_COVERAGE", f"Category {category} is {item['status']}: {item['rationale']}")
    selected = [("scope_1", scope1_result_id), ("scope_2", scope2_result_id)] + [("scope_3", ident) for ident in scope3_result_ids]
    category_counts, component_counts = {}, {}
    for scope, ident in selected:
        source = results.get(ident)
        if source is None:
            continue
        try:
            record = _diagnostic(source, "SCOPE3_CATEGORY" if scope == "scope_3" else "SCOPE_METHOD")
            if scope == "scope_3":
                cat = record["category"]
                category_counts[cat] = category_counts.get(cat, 0) + 1
            for leaf in {item["metric_id"] for item in record["accepted"]}:
                component_counts[leaf] = component_counts.get(leaf, 0) + 1
        except (ValueError, KeyError, TypeError):
            continue
    seen_categories = set()
    for scope, ident in selected:
        source = results.get(ident)
        if source is None or ident not in state["ghg"][scope]:
            _gap(result, "SCOPE_RESULT_REQUIRED", f"Selected {scope} result is missing or not linked in its domain.")
            continue
        if not fixture_mode and any(d["code"] == "SYNTHETIC_FIXTURE" for d in source["diagnostics"]):
            _gap(result, "SYNTHETIC_INVENTORY_BLOCKED", "Synthetic scope results cannot enter an ordinary inventory.")
            continue
        expected = {"scope_1": {"calculate-scope-1"}, "scope_2": {"calculate-location-based-scope-2", "calculate-market-based-scope-2"}, "scope_3": {"calculate-scope-3-category"}}[scope]
        if source["skill"] not in expected or source["status"] not in {"completed", "partial"} or len(source["metrics"]) != 1:
            _gap(result, "SCOPE_RESULT_REQUIRED", f"Selected {scope} result has unsupported skill, status or metrics.")
            continue
        try:
            record = _diagnostic(source, "SCOPE3_CATEGORY" if scope == "scope_3" else "SCOPE_METHOD")
            if record["coverage_review"]["gwp_basis"] != gwp:
                raise ValueError("Incompatible GWP basis")
            if scope == "scope_3":
                category = record["category"]
                if type(category) is not int or category not in CATEGORIES or category in seen_categories or category_counts.get(category) != 1:
                    raise ValueError("Duplicate or unsupported category")
                seen_categories.add(category)
                if screening.get(category, {}).get("status") != "applicable":
                    raise ValueError("Category conflicts with screening")
            else:
                if record["scope"] != scope or record["method"] != {"calculate-scope-1":"direct", "calculate-location-based-scope-2":"location", "calculate-market-based-scope-2":"market"}[source["skill"]]:
                    raise ValueError("Scope method mismatch")
            leaves = {item["metric_id"] for item in record["accepted"]}
            if not leaves or components & leaves or any(component_counts[leaf] != 1 for leaf in leaves):
                raise ValueError("Shared emissions component across selected accounts")
            metric = source["metrics"][0]
            amount = convert(metric["value"], metric["unit"], "kg CO2e")["value"]
            if amount < 0 or metric["period"] != state["reporting_period"] or metric["boundary_id"] != state["organizational_boundary"]["id"]:
                raise ValueError("Metric context mismatch")
            # Recheck component arithmetic instead of trusting a labeled subtotal.
            verification_id = result_id + "-verify-" + str(len(included))
            while verification_id in results:
                verification_id += "-next"
            if scope == "scope_3":
                checked = calculate_category(state, category, record["sources"], record["components"], record["coverage_review"], verification_id, fixture_mode)
            else:
                checked = compose_scope(state, source["skill"], record["sources"], record["components"], record["coverage_review"], verification_id, fixture_mode)
            # A zero omitted during revalidation can leave the numeric subtotal
            # unchanged. Retain its failures instead of promoting old completeness.
            existing_gaps = {(item["field"], item["reason"], item["impact"], item["remedy"]) for item in result["data_gaps"]}
            for item in checked["result"]["data_gaps"]:
                key = (item["field"], item["reason"], item["impact"], item["remedy"])
                if key not in existing_gaps:
                    result["data_gaps"].append(copy.deepcopy(item))
                    existing_gaps.add(key)
            for diagnostic in checked["result"]["diagnostics"]:
                if diagnostic["code"] not in {"SCOPE_METHOD", "SCOPE3_CATEGORY", "SYNTHETIC_FIXTURE", "MARKET_COVERAGE"}:
                    if diagnostic not in result["diagnostics"]:
                        result["diagnostics"].append(copy.deepcopy(diagnostic))
            checked_metrics = checked["result"]["metrics"]
            if len(checked_metrics) != 1 or serialize(amount) != serialize(number(checked_metrics[0]["value"])):
                raise ValueError("Subtotal does not reproduce from its component records")
        except (ValueError, KeyError, TypeError):
            _gap(result, "INVENTORY_RECONCILIATION_REQUIRED", f"Selected {scope} result has incompatible method, category, GWP, context or overlapping coverage.")
            continue
        with localcontext() as context:
            context.prec = 34
            total += amount
        components.update(leaves)
        refs.update(source["evidence_ids"])
        inputs.append(metric["id"])
        included.append({"scope": scope, "result_id": ident, "metric_id": metric["id"], "value_kg_CO2e": serialize(amount),
                         "category": record["category"] if scope == "scope_3" else None, "scope_2_method": record.get("method") if scope == "scope_2" else None})
        if source["status"] == "partial":
            _gap(result, "PARTIAL_SCOPE_ACCOUNT", f"Selected {scope} result {ident} is partial; retained subtotal does not establish complete inventory coverage.")
    for category, item in screening.items():
        if item.get("status") == "applicable" and not any(entry["category"] == category for entry in included):
            _gap(result, "CATEGORY_RESULT_REQUIRED", f"Applicable category {category} has no supported selected result.")
    if inputs:
        result["metrics"] = [{"id": result_id + "-metric", "name": "Selected GHG inventory emissions subtotal", "value": serialize(total), "unit": "kg CO2e",
            "period": copy.deepcopy(state["reporting_period"]), "boundary_id": state["organizational_boundary"]["id"], "evidence_ids": sorted(refs),
            "method": {"name": "GHG inventory composition with one selected scope 2 method", "version": "2011 with 2013 corrections", "source": STANDARD},
            "assumption": None, "uncertainty": {"kind":"unquantified","description":"Inventory uncertainty remains in selected components; not combined statistically.","value":None,"unit":None},
            "calculation": {"formula":"Scope 1 + one selected scope 2 account + selected distinct scope 3 categories", "inputs":inputs,
                            "conversions":["Selected scope/category quantities converted to kg CO2e"], "rounding":"34-digit Decimal arithmetic; JSON serialization"}}]
    else:
        _gap(result, "SCOPE_RESULT_REQUIRED", "No supported scope account selected; no zero inventory inferred.")
    result["evidence_ids"] = sorted(refs)
    result["diagnostics"].append({"code":"INVENTORY_SELECTION","message":json.dumps({"included":included,"category_screening":category_screening,
        "coverage_review":coverage_review,"gwp_basis":gwp,"limits":"Selection and arithmetic do not authenticate accounts or prove external completeness."},sort_keys=True)})
    return _finish(state,result,bool(inputs),fixture_mode,"Compose inventory with explicit scope and category selections")
