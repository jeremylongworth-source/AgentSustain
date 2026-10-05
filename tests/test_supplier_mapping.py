import copy
import json
import unittest
from scripts.contract_validation import ROOT, validate_state
from scripts.scope3_accounting import calculate_category
from scripts.supplier_tools import run_suppliers
from tests.test_scope3 import category_fixture


def mapping_fixture():
    state,sources,components,coverage=category_fixture()
    evidence=next(e for e in state["evidence"] if e["id"]=="ev-001")
    evidence["source"].update(title="Fictional buyer purchase-line material quantity",locator="fixture:material-purchase-line")
    evidence["method"].update(name="Fictional material purchase-record fixture",source="fixture:material-purchase-line")
    state["suppliers"]=[{"id":"material-supplier","evidence_ids":["ev-001"],"attributes":{"name":"Fictional material supplier"}}]
    state=calculate_category(state,1,sources,components,coverage,"mapped-category",True)["proposal"]["state"]
    policy=components[0]["policy"]
    allocation={"confirmed":True,"evidence_ids":["ev-001"],"supplier_relationship":"Fictional supplier of this buyer purchase line.",
        "product_scope":"Selected fictional material bought for this buyer.","rationale":"Synthetic attributable purchase quantity already contains allocation; no second allocation.",
        "lifecycle_boundary":policy["lifecycle_boundary"],"allocation_basis":policy["allocation_basis"]}
    link={"id":"material-purchase-link","supplier_id":"material-supplier","purchase_reference":"Fictional PO-001 line 1",
        "purchase_metric_id":"metric-001","category_result_id":"mapped-category","source_id":"material","evidence_ids":["ev-001"],"allocation_review":allocation}
    review={"confirmed":True,"evidence_ids":["ev-001"],"reviewer_role":"buyer emissions analyst","rationale":"One fictional purchase line selected; full supplier population not supplied.",
        "scope_boundary":"Selected buyer material purchase, category 1 cradle-to-gate fixture only.","nonoverlap_assessment":"One already-attributable physical quantity and one emissions component.",
        "coverage_complete":False,"period":state["reporting_period"],"boundary_id":state["organizational_boundary"]["id"]}
    return state,{"links":[link],"mapping_review":review,"result_id":"supply-chain-mapping","fixture_mode":True}


def report(output):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]=="SUPPLY_CHAIN_MAPPING"))


class SupplierMappingTests(unittest.TestCase):
    def test_emissions_quantity_cannot_masquerade_as_purchase_activity(self):
        state,params=mapping_fixture()
        method=json.loads(next(d["message"] for r in state["results"] if r["id"]=="mapped-category" for d in r["diagnostics"] if d["code"]=="SCOPE3_CATEGORY"))
        activity=next(m for r in state["results"] for m in r["metrics"] if m["id"]=="metric-001")
        activity["unit"]="kg CO2e"
        state["emission_factors"][0]["unit"]="kg CO2e/kg CO2e"
        method["components"][0]["policy"]["source_review"]["confirmed_unit"]="kg CO2e/kg CO2e"
        checked=calculate_category(state,1,method["sources"],method["components"],method["coverage_review"],"dubious-category",True)
        self.assertTrue(checked["result"]["metrics"])
        state=checked["proposal"]["state"];params["links"][0]["category_result_id"]="dubious-category"
        output=run_suppliers(state,"map-supply-chain-emissions",params)
        self.assertEqual(output["result"]["status"],"blocked")
        self.assertTrue(any("emissions are not purchase activity" in d["message"] for d in output["result"]["diagnostics"]))

    def test_purchase_component_links_preserve_quantities_without_reallocation(self):
        state,params=mapping_fixture();saved=copy.deepcopy(state)
        output=run_suppliers(state,"map-supply-chain-emissions",params);r=report(output);row=r["rows"][0]
        self.assertEqual(row["purchase_activity"]["value"],100);self.assertEqual(row["purchase_activity"]["unit"],"kg")
        self.assertEqual(row["emissions_component"]["value"],200);self.assertEqual(row["category"],1)
        self.assertFalse(row["allocation_reapplied"]);self.assertIsNone(r["portfolio_total"])
        self.assertFalse(r["procurement_authorized"]);self.assertEqual(output["result"]["metrics"],[])
        self.assertEqual(state,saved);self.assertEqual(output["proposal"]["state"]["suppliers"],state["suppliers"])
        self.assertEqual(output["proposal"]["state"]["ghg"],state["ghg"]);validate_state(output["proposal"]["state"])

    def test_missing_factor_and_ordinary_mode_retain_factor_requirement(self):
        for ordinary in (True,False):
            state,params=mapping_fixture()
            if ordinary:params.pop("fixture_mode")
            else:state["emission_factors"]=[]
            output=run_suppliers(state,"map-supply-chain-emissions",params)
            self.assertEqual(output["result"]["status"],"blocked")
            self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})
            self.assertFalse(any(d["code"]=="SUPPLY_CHAIN_MAPPING" for d in output["result"]["diagnostics"]))

    def test_reused_purchases_wrong_activity_scope_and_allocation_are_rejected(self):
        changes=[lambda p:p["links"].append(copy.deepcopy(p["links"][0])),
            lambda p:p["links"][0].update(purchase_metric_id="material-co2e-metric"),
            lambda p:p["links"][0].update(source_id="unknown"),lambda p:p["links"][0].update(supplier_id="unknown"),
            lambda p:p["links"][0]["allocation_review"].update(allocation_basis="Reapply supplier corporate-total share"),
            lambda p:p["mapping_review"].update(boundary_id="other")]
        for change in changes:
            state,params=mapping_fixture();change(params)
            self.assertEqual(run_suppliers(state,"map-supply-chain-emissions",params)["result"]["status"],"blocked")

    def test_changed_component_and_cached_category_do_not_reproduce(self):
        for metric_id in ("material-co2e-metric","mapped-category-metric"):
            state,params=mapping_fixture()
            metric=next(m for r in state["results"] for m in r["metrics"] if m["id"]==metric_id)
            metric["value"]=1
            self.assertEqual(run_suppliers(state,"map-supply-chain-emissions",params)["result"]["status"],"blocked")

    def test_saved_full_mapping_replay(self):
        capture=json.loads((ROOT/"evaluations/sus14-supply-chain-mapping.json").read_text(encoding="utf-8"))
        self.assertEqual(run_suppliers(capture["state"],"map-supply-chain-emissions",capture["parameters"]),capture["output"])
