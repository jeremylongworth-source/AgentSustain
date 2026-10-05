import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.scope3_accounting import calculate_category
from scripts.supplier_comparison import _record
from scripts.supplier_tools import run_suppliers
from tests.test_supplier_mapping import mapping_fixture


def hotspot_fixture(second_value=50):
    state,params=mapping_fixture()
    evidence=copy.deepcopy(state["evidence"][0]);evidence["id"]="purchase-b-record"
    evidence["source"].update(title="Fictional second material purchase",locator="fixture:purchase-b")
    state["evidence"].append(evidence)
    raw=copy.deepcopy(state["results"][0]);raw["id"]="second-purchase"
    metric=raw["metrics"][0];metric.update(id="purchase-b",value=second_value,evidence_ids=[evidence["id"]])
    if metric["calculation"]:metric["calculation"]["inputs"]=[evidence["id"]]
    raw["evidence_ids"]=[evidence["id"]];state["results"].append(raw)
    state["suppliers"].append({"id":"supplier-b","evidence_ids":[evidence["id"]],"attributes":{"name":"Fictional second material supplier"}})
    category=_record(next(r for r in state["results"] if r["id"]=="mapped-category"),"SCOPE3_CATEGORY")
    policy=copy.deepcopy(category["components"][0]["policy"])
    policy["source_review"]["activity_id"]="purchase-b"
    state=calculate_result(state,"purchase-b",state["emission_factors"][0]["id"],policy,"purchase-b-emissions",True)["proposal"]["state"]
    sources=copy.deepcopy(category["sources"]);sources.append(dict(sources[0],id="material-b",activity_id="purchase-b",evidence_ids=[evidence["id"]]))
    components=copy.deepcopy(category["components"]);components.append(dict(components[0],source_id="material-b",metric_id="purchase-b-emissions-metric",policy=policy))
    state=calculate_category(state,1,sources,components,category["coverage_review"],"two-purchases",True)["proposal"]["state"]
    params["links"][0]["category_result_id"]="two-purchases"
    link=copy.deepcopy(params["links"][0]);link.update(id="purchase-b-link",supplier_id="supplier-b",purchase_metric_id="purchase-b",
        purchase_reference="Fictional PO-002 line 1",source_id="material-b",evidence_ids=[evidence["id"]])
    link["allocation_review"]["evidence_ids"]=[evidence["id"]];params["links"].append(link)
    params["mapping_review"].update(rationale="Two fictional independent purchase lines selected; full supplier population not supplied.",
        nonoverlap_assessment="Two distinct already-attributable purchase lines and their separate emissions components.")
    out=run_suppliers(state,"map-supply-chain-emissions",params)
    assert out["result"]["status"]!="blocked",out["result"]["diagnostics"]
    state=out["proposal"]["state"]
    review=copy.deepcopy(params["mapping_review"])
    return state,{"mapping_result_ids":[params["result_id"]],"hotspot_review":review,"hotspot_threshold_percent":50,
        "result_id":"supplier-hotspots","fixture_mode":True}


def report(output):return _record(output["result"],"SUPPLIER_HOTSPOTS")


class SupplierHotspotTests(unittest.TestCase):
    def test_selected_supplier_and_category_partitions_have_known_denominator(self):
        state,params=hotspot_fixture();saved=copy.deepcopy(state)
        out=run_suppliers(state,"identify-scope-3-hotspots",params);r=report(out)
        self.assertEqual(out["result"]["metrics"][0]["value"],300)
        suppliers=r["views"]["supplier"]
        self.assertEqual([s["kg_co2e"] for s in suppliers],[200,100])
        self.assertAlmostEqual(suppliers[0]["percent_of_selected_subtotal"],100*2/3)
        self.assertTrue(suppliers[0]["hotspot"]);self.assertFalse(suppliers[1]["hotspot"])
        self.assertEqual(r["views"]["category"][0]["percent_of_selected_subtotal"],100)
        self.assertFalse(r["selected_mapping_coverage_complete"]);self.assertFalse(r["full_scope_3_coverage_verified"])
        self.assertEqual(out["result"]["status"],"partial");self.assertEqual(state,saved)
        self.assertEqual(len([d for d in out["result"]["diagnostics"] if d["code"]=="SUPPLIER_INPUTS"]),1)
        self.assertIn("SYNTHETIC_FIXTURE",{d["code"] for d in out["result"]["diagnostics"]})
        self.assertEqual(out["proposal"]["state"]["ghg"],state["ghg"]);self.assertEqual(out["proposal"]["state"]["suppliers"],state["suppliers"])
        validate_state(out["proposal"]["state"])

    def test_ties_share_contribution_priority_and_threshold_includes_equality(self):
        state,params=hotspot_fixture(100);r=report(run_suppliers(state,"identify-scope-3-hotspots",params))
        self.assertEqual([s["priority_group"] for s in r["views"]["supplier"]],[1,1])
        self.assertTrue(all(s["hotspot"] and s["percent_of_selected_subtotal"]==50 for s in r["views"]["supplier"]))

    def test_duplicate_mapping_and_cross_mapping_components_reject(self):
        for repeated in (True,False):
            state,params=hotspot_fixture()
            if repeated:params["mapping_result_ids"]*=2
            else:
                source=next(r for r in state["results"] if r["id"]=="supply-chain-mapping")
                inputs=_record(source,"SUPPLIER_INPUTS");inputs["result_id"]="duplicate-map"
                state=run_suppliers(state,"map-supply-chain-emissions",inputs)["proposal"]["state"]
                params["mapping_result_ids"].append("duplicate-map")
            out=run_suppliers(state,"identify-scope-3-hotspots",params)
            self.assertEqual(out["result"]["status"],"blocked");self.assertEqual(out["result"]["metrics"],[])

    def test_missing_factor_fixture_permission_and_changed_source_reject(self):
        for change in ("factor","fixture","report","quantity","scope","threshold"):
            state,params=hotspot_fixture()
            if change=="factor":state["emission_factors"]=[]
            elif change=="fixture":params.pop("fixture_mode")
            elif change=="report":
                source=next(r for r in state["results"] if r["id"]=="supply-chain-mapping")
                d=next(d for d in source["diagnostics"] if d["code"]=="SUPPLY_CHAIN_MAPPING")
                value=json.loads(d["message"]);value["rows"][0]["emissions_component"]["value"]=1;d["message"]=json.dumps(value)
            elif change=="quantity":state["results"][0]["metrics"][0]["value"]=5
            elif change=="scope":params["hotspot_review"]["scope_boundary"]="Other scope"
            else:params["hotspot_threshold_percent"]=0
            out=run_suppliers(state,"identify-scope-3-hotspots",params)
            self.assertEqual(out["result"]["status"],"blocked");self.assertEqual(out["result"]["metrics"],[])
            if change in {"factor","fixture"}:self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in out["result"]["diagnostics"]})

    def test_coverage_confirmation_cannot_upgrade_partial_map(self):
        state,params=hotspot_fixture();params["hotspot_review"]["coverage_complete"]=True
        self.assertFalse(report(run_suppliers(state,"identify-scope-3-hotspots",params))["selected_mapping_coverage_complete"])

    def test_supported_unit_conversion_preserves_denominator(self):
        state,params=hotspot_fixture()
        component=next(m for r in state["results"] for m in r["metrics"] if m["id"]=="material-co2e-metric")
        component.update(value=0.2,unit="t CO2e")
        source=next(r for r in state["results"] if r["id"]=="supply-chain-mapping")
        inputs=_record(source,"SUPPLIER_INPUTS");inputs["result_id"]="tonnes-map"
        state=run_suppliers(state,"map-supply-chain-emissions",inputs)["proposal"]["state"]
        params["mapping_result_ids"]=["tonnes-map"]
        out=run_suppliers(state,"identify-scope-3-hotspots",params)
        self.assertEqual(out["result"]["metrics"][0]["value"],300)
        self.assertEqual(report(out)["views"]["supplier"][0]["kg_co2e"],200)

    def test_distinct_supported_maps_with_mixed_gwp_basis_reject(self):
        state,params=hotspot_fixture()
        original=next(r for r in state["results"] if r["id"]=="supply-chain-mapping")
        inputs=_record(original,"SUPPLIER_INPUTS")
        category=_record(next(r for r in state["results"] if r["id"]=="two-purchases"),"SCOPE3_CATEGORY")
        factor=copy.deepcopy(state["emission_factors"][0]);factor.update(id="other-factor",gwp_basis="Other fictional GWP basis")
        state["emission_factors"].append(factor)
        policy=copy.deepcopy(category["components"][1]["policy"]);policy["gwp_basis"]=factor["gwp_basis"]
        policy["source_review"]["factor_id"]=factor["id"]
        state=calculate_result(state,"purchase-b",factor["id"],policy,"other-emissions",True)["proposal"]["state"]
        review=copy.deepcopy(category["coverage_review"]);review["gwp_basis"]=factor["gwp_basis"]
        component=dict(category["components"][1],metric_id="other-emissions-metric",factor_id=factor["id"],policy=policy)
        state=calculate_category(state,1,[category["sources"][1]],[component],review,"other-category",True)["proposal"]["state"]
        selected=[]
        for index,category_id in enumerate(("mapped-category","other-category")):
            request=copy.deepcopy(inputs);request["links"]=[request["links"][index]]
            request["links"][0]["category_result_id"]=category_id;request["result_id"]="distinct-map-"+str(index)
            output=run_suppliers(state,"map-supply-chain-emissions",request)
            self.assertNotEqual(output["result"]["status"],"blocked")
            state=output["proposal"]["state"];selected.append(request["result_id"])
        params["mapping_result_ids"]=selected;out=run_suppliers(state,"identify-scope-3-hotspots",params)
        self.assertEqual(out["result"]["status"],"blocked");self.assertEqual(out["result"]["metrics"],[])
        self.assertTrue(any("Mixed GWP" in d["message"] for d in out["result"]["diagnostics"]))

    def test_zero_subtotal_has_no_percentage_or_hotspot(self):
        from tests.test_supplier_mapping import mapping_fixture
        state,params=mapping_fixture();state["results"][0]["metrics"][0]["value"]=0
        category=_record(next(r for r in state["results"] if r["id"]=="mapped-category"),"SCOPE3_CATEGORY")
        policy=category["components"][0]["policy"]
        state=calculate_result(state,"metric-001",state["emission_factors"][0]["id"],policy,"zero-component",True)["proposal"]["state"]
        category["components"][0]["metric_id"]="zero-component-metric"
        state=calculate_category(state,1,category["sources"],category["components"],category["coverage_review"],"zero-category",True)["proposal"]["state"]
        params["links"][0]["category_result_id"]="zero-category";params["result_id"]="zero-mapping"
        state=run_suppliers(state,"map-supply-chain-emissions",params)["proposal"]["state"]
        request={"mapping_result_ids":["zero-mapping"],"hotspot_review":params["mapping_review"],"hotspot_threshold_percent":50,"result_id":"zero-hotspots","fixture_mode":True}
        out=run_suppliers(state,"identify-scope-3-hotspots",request);r=report(out)
        self.assertEqual(out["result"]["metrics"][0]["value"],0)
        self.assertTrue(all(s["percent_of_selected_subtotal"] is None and not s["hotspot"] and s["priority_group"] is None for s in r["views"]["supplier"]))

    def test_full_saved_replay(self):
        saved=json.loads((ROOT/"evaluations/sus14-supplier-hotspots.json").read_text(encoding="utf-8"))
        self.assertEqual(run_suppliers(saved["state"],"identify-scope-3-hotspots",saved["parameters"]),saved["output"])
