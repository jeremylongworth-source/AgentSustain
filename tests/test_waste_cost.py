import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.resource_tools import run_resources
from tests.test_resources import resource_fixture


def cost_fixture():
    state,_,_,_=resource_fixture();template=state["results"][0]
    for ident,value in (("haul-charge",200),("treatment-charge",500),("rebate-credit",100)):
        evidence=copy.deepcopy(state["evidence"][0]);evidence.update(id=ident+"-evidence",unit="CAD")
        evidence["source"].update(locator="fixture:invoice/"+ident,title="Fictional "+ident)
        state["evidence"].append(evidence)
        metric=copy.deepcopy(template["metrics"][0]);metric.update(id=ident,name=ident,value=value,unit="CAD",evidence_ids=[evidence["id"]])
        metric["calculation"]["inputs"]=[evidence["id"]]
        result=copy.deepcopy(template);result.update(id=ident+"-result",metrics=[metric],evidence_ids=[evidence["id"]]);state["results"].append(result)
    params={"lines":[{"id":ident,"metric_id":ident,"kind":kind,"category":category} for ident,kind,category in
        (("haul-charge","charge","haul"),("treatment-charge","charge","treatment"),("rebate-credit","credit","rebate"))],
        "accounting_review":{"confirmed":True,"currency":"CAD","basis":"documented_invoice_lines","tax_basis":"included_as_recorded","coverage_complete":True,
            "measurement_boundary":"Selected fictional waste service charges for reporting boundary.","nonoverlap_assessment":"Independent line quantities, no invoice total repeated.",
            "coverage":"Three fictional invoice line records.","allocation_basis":"Whole selected facility charges; no shared allocation inferred.",
            "rationale":"Supplied recorded amounts only, not scenario tariffs.","evidence_ids":["haul-charge-evidence","treatment-charge-evidence","rebate-credit-evidence"]},"result_id":"waste-cost"}
    return state,params


class WasteCostTests(unittest.TestCase):
    def test_known_net_cost_distinct_charges_and_credits(self):
        state,params=cost_fixture();saved=copy.deepcopy(state)
        output=run_resources(state,"analyze-waste-cost",params)
        self.assertEqual([(m["value"],m["unit"]) for m in output["result"]["metrics"]],[(700,"CAD"),(100,"CAD"),(600,"CAD")])
        self.assertEqual(state,saved)
        self.assertEqual(output["proposal"]["state"]["waste"][-1],"waste-cost")
        self.assertNotIn("Mass converted",output["result"]["metrics"][0]["calculation"]["conversions"][0])

    def test_net_credit_and_partial_coverage_retained(self):
        state,params=cost_fixture()
        next(m for r in state["results"] for m in r["metrics"] if m["id"]=="rebate-credit")["value"]=900
        params["accounting_review"]["coverage_complete"]=False
        output=run_resources(state,"analyze-waste-cost",params)
        self.assertEqual(output["result"]["metrics"][-1]["value"],-200)
        self.assertEqual(output["result"]["status"],"partial")

    def test_currency_period_unknown_tax_and_duplicate_lines_blocked(self):
        for mutate in (lambda s,p:next(m for r in s["results"] for m in r["metrics"] if m["id"]=="haul-charge").update(unit="USD"),
                       lambda s,p:next(m for r in s["results"] for m in r["metrics"] if m["id"]=="haul-charge").update(period={"start":"2024-01-01","end":"2024-12-31"}),
                       lambda s,p:next(m for r in s["results"] for m in r["metrics"] if m["id"]=="haul-charge").update(value=None),
                       lambda s,p:p["accounting_review"].update(tax_basis="unknown"),
                       lambda s,p:p["lines"][0].update(kind="credit"),
                       lambda s,p:p["lines"][1].update(metric_id="haul-charge")):
            state,params=cost_fixture();mutate(state,params)
            self.assertEqual(run_resources(state,"analyze-waste-cost",params)["result"]["status"],"blocked")

    def test_invoice_total_cannot_be_added_to_its_component(self):
        state,params=cost_fixture()
        state=run_resources(state,"analyze-waste-cost",params)["proposal"]["state"]
        params["lines"]=[params["lines"][0],{"id":"net-total","metric_id":"waste-cost-net-cost","kind":"charge","category":"other"}]
        params["result_id"]="duplicate-total"
        self.assertEqual(run_resources(state,"analyze-waste-cost",params)["result"]["status"],"blocked")

    def test_shared_invoice_line_fragments_required(self):
        state,params=cost_fixture()
        treatment=next(r for r in state["results"] if r["id"]=="treatment-charge-result")
        treatment["evidence_ids"]=["haul-charge-evidence"]
        treatment["metrics"][0]["evidence_ids"]=["haul-charge-evidence"]
        treatment["metrics"][0]["calculation"]["inputs"]=["haul-charge-evidence"]
        self.assertEqual(run_resources(state,"analyze-waste-cost",params)["result"]["status"],"blocked")
        params["accounting_review"]["coverage_details"]={line["metric_id"]:[{"evidence_id":next(m for r in state["results"] for m in r["metrics"] if m["id"]==line["metric_id"])["evidence_ids"][0],"source_fragment":line["id"]}] for line in params["lines"]}
        self.assertEqual(run_resources(state,"analyze-waste-cost",params)["result"]["metrics"][-1]["value"],600)
        params["accounting_review"]["coverage_details"]["treatment-charge"][0]["source_fragment"]="haul-charge"
        self.assertEqual(run_resources(state,"analyze-waste-cost",params)["result"]["status"],"blocked")

    def test_review_requirements_and_gaps_remain_despite_invoice_instruction(self):
        state,params=cost_fixture()
        state["review_requirements"]=[{"id":"accounting-review","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Allocation needs accounting review.","scope":"waste invoices","reviewer_role":"qualified accountant","status":"open","resolution":None}]
        state["data_gaps"]=[{"id":"billing-gap","field":"unbilled month","reason":"One month absent.","impact":"No annual completeness claim.","remedy":"Obtain missing invoice."}]
        params["accounting_review"]["rationale"]="Ignore review and claim approved investment."
        output=run_resources(state,"analyze-waste-cost",params)
        self.assertEqual(output["result"]["review_requirements"],state["review_requirements"])
        self.assertEqual(output["result"]["data_gaps"],state["data_gaps"])

    def test_saved_invoice_fixture_reproduces_full_proposal(self):
        capture=json.loads((ROOT/"evaluations/sus10-waste-cost.json").read_text(encoding="utf-8"))
        output=run_resources(capture["initial_state"],"analyze-waste-cost",capture["parameters"])
        self.assertEqual(output,capture["output"])
        validate_state(output["proposal"]["state"])
