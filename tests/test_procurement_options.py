import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.supplier_comparison import _record
from scripts.supplier_tools import run_suppliers
from tests.test_supplier_hotspots import hotspot_fixture


def option_fixture(alternative_value=50):
    state,_=hotspot_fixture(alternative_value)
    raw=state["results"][0]
    for name,value,unit in (("base-service",100,"count"),("alt-service",100,"count"),("base-cost",120,"CAD"),("alt-cost",140,"CAD")):
        evidence=copy.deepcopy(state["evidence"][0]);evidence.update(id=name+"-record",unit=unit)
        evidence["source"].update(title="Fictional "+name+" purchase specification or quote",locator="fixture:"+name)
        evidence["method"].update(name="Fictional service specification or price quote",source="fixture:"+name)
        evidence["quality"]["fitness_notes"]="Fictional selected-option equivalent service or quote only."
        state["evidence"].append(evidence)
        source=copy.deepcopy(raw);source["id"]=name+"-source";source["evidence_ids"]=[evidence["id"]]
        metric=source["metrics"][0];metric.update(id=name,name="Fictional "+name,value=value,unit=unit,evidence_ids=[evidence["id"]])
        if metric["calculation"]:metric["calculation"]["inputs"]=[evidence["id"]]
        state["results"].append(source)
    mapping=_record(next(r for r in state["results"] if r["id"]=="supply-chain-mapping"),"SUPPLY_CHAIN_MAPPING")
    allocation=mapping["rows"][0]["link"]["allocation_review"]
    review=copy.deepcopy(mapping["mapping_review"])
    review.update(functional_unit="100 packaging deliveries meeting the fictional protection specification.",service_requirements="Equal documented product protection and delivery service.",
        lifetime_basis="One delivery per packaging unit, same selected service period.",lifecycle_boundary=allocation["lifecycle_boundary"],allocation_basis=allocation["allocation_basis"],
        gwp_basis="Synthetic fixture basis",scenario_assumptions="Fictional mutually exclusive material quantity alternatives for equivalent deliveries, not implemented purchases.",
        risk_tradeoffs="Damage, supply capacity and wider social/ecosystem tradeoffs require substantive review.")
    cost_review={"confirmed":True,"evidence_ids":["base-cost-record","alt-cost-record"],"reviewer_role":"fictional procurement analyst",
        "rationale":"Comparable selected fictional quotes for the same delivery service, not a lifecycle cost or return analysis.","currency":"CAD",
        "cost_scope":"Selected purchase quote only; transport/tax/lifecycle operating costs not established.","valuation_date":"2025-09-01","dollar_basis":"nominal","tax_basis":"pre_tax"}
    base={"id":"base-option","supplier_id":"material-supplier","mapping_result_id":"supply-chain-mapping","link_ids":["material-purchase-link"],"functional_metric_id":"base-service","cost_metric_id":"base-cost"}
    alternate={"id":"alternative-option","supplier_id":"supplier-b","mapping_result_id":"supply-chain-mapping","link_ids":["purchase-b-link"],"functional_metric_id":"alt-service","cost_metric_id":"alt-cost"}
    return state,{"baseline":base,"alternative":alternate,"comparison_review":review,"cost_review":cost_review,"result_id":"procurement-options","fixture_mode":True}


def report(output):return _record(output["result"],"PROCUREMENT_OPTION_COMPARISON")


class ProcurementOptionTests(unittest.TestCase):
    def test_equivalent_service_reduction_and_cost_premium_without_approval(self):
        state,params=option_fixture();saved=copy.deepcopy(state);out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params);r=report(out)
        self.assertEqual([m["value"] for m in out["result"]["metrics"]],[200,100,100,50,20])
        self.assertTrue(r["alternative_has_lower_selected_emissions"]);self.assertFalse(r["procurement_authorized"])
        self.assertFalse(r["public_claim_authorized"]);self.assertFalse(r["full_lifecycle_superiority_verified"]);self.assertIsNone(r["selected_supplier_id"])
        self.assertEqual(out["result"]["status"],"partial");self.assertEqual(state,saved)
        self.assertEqual(out["proposal"]["state"]["suppliers"],state["suppliers"]);self.assertEqual(out["proposal"]["state"]["ghg"],state["ghg"])
        self.assertEqual(out["result"]["review_requirements"][-1]["status"],"open");validate_state(out["proposal"]["state"])

    def test_unlike_service_or_source_boundaries_reject(self):
        for change in ("service","unit","lifecycle","gwp","supplier","reused","scope"):
            state,params=option_fixture()
            if change in {"service","unit"}:
                metric=next(m for r in state["results"] for m in r["metrics"] if m["id"]=="alt-service")
                if change=="service":metric["value"]=50
                else:metric["unit"]="kg CO2e"
            elif change=="lifecycle":params["comparison_review"]["lifecycle_boundary"]="Full lifecycle instead of selected material boundary"
            elif change=="gwp":params["comparison_review"]["gwp_basis"]="Other"
            elif change=="supplier":params["alternative"]["supplier_id"]="unknown"
            elif change=="reused":params["alternative"].update(supplier_id="material-supplier",link_ids=["material-purchase-link"])
            else:params["comparison_review"]["boundary_id"]="other"
            out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params)
            self.assertEqual(out["result"]["status"],"blocked");self.assertEqual(out["result"]["metrics"],[])

    def test_missing_factor_or_fixture_permission_retains_native_requirement(self):
        for missing in (True,False):
            state,params=option_fixture()
            if missing:state["emission_factors"]=[]
            else:params.pop("fixture_mode")
            out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params)
            self.assertEqual(out["result"]["status"],"blocked")
            self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in out["result"]["diagnostics"]})

    def test_missing_costs_are_not_zero_or_affordability(self):
        state,params=option_fixture();params["alternative"]["cost_metric_id"]=None;params["cost_review"]=None
        out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params);r=report(out)
        self.assertIsNone(r["cost_premium_metric_id"]);self.assertEqual(len(out["result"]["metrics"]),4)
        self.assertTrue(any("costs are missing" in g["reason"] for g in out["result"]["data_gaps"]))

    def test_currency_and_shadow_cost_ancestry_reject(self):
        for change in ("currency","shadow","ancestor","valuation"):
            state,params=option_fixture();owner=next(r for r in state["results"] if r["id"]=="alt-cost-source")
            if change=="currency":owner["metrics"][0]["unit"]="USD"
            elif change in {"shadow","ancestor"}:
                if change=="ancestor":
                    owner["metrics"][0]["calculation"]={"formula":"Copied shadow exposure","inputs":["base-cost"],"conversions":[],"rounding":"None"}
                    owner=next(r for r in state["results"] if r["id"]=="base-cost-source")
                owner["diagnostics"].append({"code":"NONCASH_SHADOW_PRICE","message":"Internal modeled exposure, not a purchase payment."})
            else:params["cost_review"]["valuation_date"]="2026-01-01"
            self.assertEqual(run_suppliers(state,"evaluate-low-carbon-procurement-option",params)["result"]["status"],"blocked")

    def test_equal_and_worse_alternatives_do_not_become_reductions(self):
        for activity,reduction,percent in ((100,0,0),(150,-100,-50)):
            state,params=option_fixture(activity);out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params)
            self.assertFalse(report(out)["alternative_has_lower_selected_emissions"])
            self.assertEqual(out["result"]["metrics"][2]["value"],reduction);self.assertEqual(out["result"]["metrics"][3]["value"],percent)

    def test_changed_mapping_report_rejects_before_arithmetic(self):
        state,params=option_fixture();source=next(r for r in state["results"] if r["id"]=="supply-chain-mapping")
        d=next(d for d in source["diagnostics"] if d["code"]=="SUPPLY_CHAIN_MAPPING")
        value=json.loads(d["message"]);value["rows"][1]["emissions_component"]["value"]=1;d["message"]=json.dumps(value)
        self.assertEqual(run_suppliers(state,"evaluate-low-carbon-procurement-option",params)["result"]["status"],"blocked")

    def test_financial_cost_reproduction_and_altered_quote_reject(self):
        from scripts.finance_tools import run_finance
        from tests.test_finance_composition import composition_fixture
        state,params=option_fixture();_,requests=composition_fixture();cost=copy.deepcopy(requests["calculate-sustainability-project-cost"])
        cost["lines"]=[{"id":"base-quote","metric_id":"base-cost","kind":"cost","category":"capital"}]
        cost["composition_review"]["evidence_ids"]=["base-cost-record"]
        cost["analysis_review"]["evidence_ids"]=["base-cost-record"]
        cost["analysis_review"].update(valuation_date=params["cost_review"]["valuation_date"],dollar_basis="nominal")
        cost["analysis_review"]["horizon"]["start"]=params["cost_review"]["valuation_date"]
        state=run_finance(state,"calculate-sustainability-project-cost",cost)["proposal"]["state"]
        params["baseline"]["cost_metric_id"]="composed-cost-value"
        out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params)
        self.assertEqual(out["result"]["metrics"][-1]["value"],20)
        source=next(m for r in state["results"] for m in r["metrics"] if m["id"]=="base-cost");source["value"]=90
        self.assertEqual(run_suppliers(state,"evaluate-low-carbon-procurement-option",params)["result"]["status"],"blocked")

    def test_zero_baseline_keeps_signed_difference_without_percentage(self):
        from scripts.ghg_foundation import calculate_result
        from scripts.scope3_accounting import calculate_category
        state,params=option_fixture()
        category=_record(next(r for r in state["results"] if r["id"]=="two-purchases"),"SCOPE3_CATEGORY")
        state["results"][0]["metrics"][0]["value"]=0
        state=calculate_result(state,"metric-001",state["emission_factors"][0]["id"],category["components"][0]["policy"],"zero-base",True)["proposal"]["state"]
        category["components"][0]["metric_id"]="zero-base-metric"
        state=calculate_category(state,1,category["sources"],category["components"],category["coverage_review"],"zero-base-category",True)["proposal"]["state"]
        source=next(r for r in state["results"] if r["id"]=="supply-chain-mapping")
        mapping=_record(source,"SUPPLIER_INPUTS");mapping["result_id"]="zero-base-map"
        for link in mapping["links"]:link["category_result_id"]="zero-base-category"
        state=run_suppliers(state,"map-supply-chain-emissions",mapping)["proposal"]["state"]
        for option in (params["baseline"],params["alternative"]):option["mapping_result_id"]="zero-base-map"
        out=run_suppliers(state,"evaluate-low-carbon-procurement-option",params);r=report(out)
        self.assertEqual(out["result"]["metrics"][2]["value"],-100)
        self.assertIsNone(r["reduction_percent_metric_id"]);self.assertFalse(r["alternative_has_lower_selected_emissions"])

    def test_full_saved_replay(self):
        saved=json.loads((ROOT/"evaluations/sus14-procurement-options.json").read_text(encoding="utf-8"))
        self.assertEqual(run_suppliers(saved["state"],"evaluate-low-carbon-procurement-option",saved["parameters"]),saved["output"])
