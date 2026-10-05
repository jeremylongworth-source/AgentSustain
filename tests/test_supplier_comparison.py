import copy
import json
import unittest
from scripts.contract_validation import ROOT, validate_state
from scripts.supplier_tools import run_suppliers
from tests.test_suppliers import supplier_fixture


def comparison_fixture(left=(1,None),right=(2,2)):
    state,base=supplier_fixture()
    evidence=copy.deepcopy(state["evidence"][-1]);evidence["id"]="supplier-b-record"
    evidence["source"].update(locator="fixture:supplier-b-packaging-record",publisher="Fictional supplier B")
    evidence["method"]["source"]="fixture:supplier-b-packaging-record"
    state["evidence"].append(evidence)
    state["suppliers"].append({"id":"supplier-b","evidence_ids":[evidence["id"]],"attributes":{"name":"Fictional supplier B"}})
    for ident,values,source in (("supplier-a",left,"supplier-record"),("supplier-b",right,"supplier-b-record")):
        params=copy.deepcopy(base);params.update(supplier_id=ident,result_id=ident+"-assessment",responses=[])
        for c,value in zip(params["criteria"],values):
            if value is not None:
                params["responses"].append({"criterion_id":c["id"],"status":"provided","answer":"Supplied fictional documentation assessment.",
                    "score":value,"evidence_ids":[source],"evidence_fit":"reviewed_supporting","assessment_rationale":"Fictional buyer reviews documentation under this shared anchor; no real assurance."})
        state=run_suppliers(state,"score-supplier-sustainability",params)["proposal"]["state"]
    review=copy.deepcopy(base["assessment_review"])
    review.update(functional_unit="One selected packaging unit meeting the documented purchase specification.",service_requirements="Same buyer product-protection and delivery requirements; supplied fictional comparability review only.")
    return state,{"assessment_result_ids":["supplier-a-assessment","supplier-b-assessment"],"comparison_review":review,"result_id":"supplier-comparison"}


def report(output):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]=="SUPPLIER_COMPARISON"))


class SupplierComparisonTests(unittest.TestCase):
    def test_strict_range_separation_withholds_purchase_selection(self):
        state,params=comparison_fixture();saved=copy.deepcopy(state)
        output=run_suppliers(state,"compare-suppliers",params);r=report(output)
        self.assertEqual(r["pairwise"][0]["relation"],"right_strictly_above")
        self.assertEqual(r["candidates"][0]["possible_score_range"]["high"],62.5)
        self.assertIsNone(r["selected_supplier_id"]);self.assertFalse(r["procurement_authorized"])
        self.assertEqual(state,saved);self.assertEqual(output["proposal"]["state"]["suppliers"],state["suppliers"])
        validate_state(output["proposal"]["state"])

    def test_overlapping_touching_and_complete_tied_scores(self):
        for left,right,relation in (((1,None),(1,1),"overlap_or_touch"),((0,None),(0,2),"overlap_or_touch"),((1,1),(1,1),"equal_complete_scores")):
            state,params=comparison_fixture(left,right)
            self.assertEqual(report(run_suppliers(state,"compare-suppliers",params))["pairwise"][0]["relation"],relation)

    def test_changed_sources_and_incomparable_rubrics_are_blocked(self):
        for change in ("stored_score","weight","rubric","supplier","exclusion"):
            state,params=comparison_fixture()
            source=next(r for r in state["results"] if r["id"]=="supplier-b-assessment")
            method=next(d for d in source["diagnostics"] if d["code"]=="SUPPLIER_INPUTS")
            inputs=json.loads(method["message"])
            if change=="stored_score":
                d=next(d for d in source["diagnostics"] if d["code"]=="SUPPLIER_ASSESSMENT")
                payload=json.loads(d["message"]);payload["score"]=1;d["message"]=json.dumps(payload)
            else:
                if change=="weight":inputs["criteria"][0]["weight"]=1
                if change=="rubric":inputs["assessment_review"]["rubric_id"]="other"
                if change=="supplier":inputs["supplier_id"]="supplier-a"
                if change=="exclusion":inputs["responses"][0].update(status="not_applicable",score=None)
                inputs["result_id"]="altered-source"
                changed=run_suppliers(state,"score-supplier-sustainability",inputs)["result"]
                changed["id"]=source["id"];state["results"][state["results"].index(source)]=changed
            output=run_suppliers(state,"compare-suppliers",params)
            self.assertEqual(output["result"]["status"],"blocked");self.assertEqual(output["result"]["metrics"],[])

    def test_duplicate_missing_and_wrong_scope_assessments_rejected(self):
        for change in (lambda p:p.update(assessment_result_ids=["supplier-a-assessment"]*2),
                lambda p:p.update(assessment_result_ids=["unknown","supplier-b-assessment"]),
                lambda p:p["comparison_review"].update(scope_boundary="Other purchase")):
            state,params=comparison_fixture();change(params)
            self.assertEqual(run_suppliers(state,"compare-suppliers",params)["result"]["status"],"blocked")

    def test_full_saved_comparison_replay(self):
        capture=json.loads((ROOT/"evaluations/sus14-supplier-comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(run_suppliers(capture["state"],"compare-suppliers",capture["parameters"]),capture["output"])
