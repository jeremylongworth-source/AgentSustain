import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.supplier_tools import run_suppliers
from tests.test_supplier_comparison import comparison_fixture


def planning_fixture(left=(1,None),right=(2,2)):
    state,params=comparison_fixture(left,right)
    review=copy.deepcopy(params["comparison_review"])
    review["service_constraints"]="Fictional packaging protection and delivery requirements must be retained."
    engagement={"assessment_result_ids":params["assessment_result_ids"],"engagement_review":review,
        "priority_rule":[{"field":"weighted_coverage_percent","direction":"ascending"}],"result_id":"supplier-engagement"}
    plan={"assessment_result_id":"supplier-a-assessment","plan_review":review,"result_id":"supplier-plan","actions":[
        {"id":"collect-allocation","criterion_id":"allocation","kind":"data_collection","owner":"Fictional buyer analyst",
         "target_date":"2026-11-01","description":"Request source allocation records for the selected packaging purchase.",
         "evidence_target":"Purchase-specific allocation method, lifecycle boundaries and documentation.","target_score":None,"depends_on":[]},
        {"id":"improve-activity","criterion_id":"activity","kind":"improvement","owner":"Fictional procurement lead",
         "target_date":"2026-12-01","description":"Propose fuller activity documentation without changing product protection.",
         "evidence_target":"Complete purchase activity records matching the buyer's declared upper documentation anchor.","target_score":2,"depends_on":["collect-allocation"]}]}
    return state,engagement,plan


def report(output,code):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]==code))


class SupplierPlanningTests(unittest.TestCase):
    def test_partial_evidence_priority_and_supported_supplier_has_no_request(self):
        state,params,_=planning_fixture();saved=copy.deepcopy(state)
        out=run_suppliers(state,"prioritize-supplier-engagement",params);r=report(out,"SUPPLIER_ENGAGEMENT")
        self.assertEqual(r["priority_groups"],[{"group":1,"supplier_ids":["supplier-a"]}])
        self.assertEqual(r["candidates"][0]["questions"][0]["criterion_id"],"allocation")
        self.assertIsNone(r["candidates"][1]["priority_group"]);self.assertIsNone(r["candidates"][0]["source_score"])
        self.assertEqual(r["delivery_status"],"draft_unsent");self.assertFalse(r["procurement_authorized"])
        self.assertEqual(saved,state);self.assertEqual(out["proposal"]["state"]["suppliers"],state["suppliers"])
        self.assertEqual(out["result"]["metrics"],[]);validate_state(out["proposal"]["state"])

    def test_tied_priorities_and_input_reversal_preserve_group(self):
        state,params,_=planning_fixture((1,None),(0,None))
        params["priority_rule"].insert(0,{"field":"unresolved_criterion_count","direction":"descending"})
        expected=[{"group":1,"supplier_ids":["supplier-a","supplier-b"]}]
        for reverse in (False,True):
            if reverse:params["assessment_result_ids"].reverse()
            self.assertEqual(report(run_suppliers(state,"prioritize-supplier-engagement",params),"SUPPLIER_ENGAGEMENT")["priority_groups"],expected)

    def test_changed_source_and_incomparable_basis_reject(self):
        for change in ("report","scope","weight","duplicate","rule"):
            state,params,_=planning_fixture()
            if change=="report":
                source=next(r for r in state["results"] if r["id"]=="supplier-a-assessment")
                d=next(d for d in source["diagnostics"] if d["code"]=="SUPPLIER_ASSESSMENT")
                value=json.loads(d["message"]);value["weighted_coverage_percent"]=0;d["message"]=json.dumps(value)
            elif change=="scope":params["engagement_review"]["scope_boundary"]="other scope"
            elif change=="weight":
                from scripts.supplier_comparison import _record
                source=next(r for r in state["results"] if r["id"]=="supplier-b-assessment")
                inputs=_record(source,"SUPPLIER_INPUTS");inputs["criteria"][0]["weight"]=1;inputs["result_id"]="changed"
                source2=run_suppliers(state,"score-supplier-sustainability",inputs)["result"];source2["id"]=source["id"]
                state["results"][state["results"].index(source)]=source2
            elif change=="duplicate":params["assessment_result_ids"]*=2
            else:params["priority_rule"]=[{"field":"emissions","direction":"descending"}]
            out=run_suppliers(state,"prioritize-supplier-engagement",params)
            self.assertEqual(out["result"]["status"],"blocked");self.assertFalse(any(d["code"]=="SUPPLIER_ENGAGEMENT" for d in out["result"]["diagnostics"]))

    def test_owned_plan_preserves_open_reviews_and_unknowns(self):
        state,_,params=planning_fixture()
        state["review_requirements"]=[{"id":"supplier-review","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Buyer review pending.","scope":"supplier plan","reviewer_role":"buyer analyst","status":"open","resolution":None}]
        saved=copy.deepcopy(state);out=run_suppliers(state,"develop-supplier-improvement-plan",params);r=report(out,"SUPPLIER_IMPROVEMENT_PLAN")
        self.assertEqual(r["proposed_sequence"],["collect-allocation","improve-activity"])
        self.assertTrue(all(not a["supplier_agreed"] and not a["implementation_authorized"] and not a["completion_verified"] for a in r["actions"]))
        self.assertIsNone(r["projected_emissions_reduction"]);self.assertEqual(r["unaddressed_criterion_ids"],[])
        self.assertEqual(out["result"]["review_requirements"],state["review_requirements"])
        self.assertEqual(state,saved);self.assertEqual(out["result"]["metrics"],[])

    def test_invalid_targets_and_dependencies_reject_entire_plan(self):
        changes=[lambda p:p["actions"][0].update(target_score=2),lambda p:p["actions"][1].update(target_score=1),
            lambda p:p["actions"][1].update(target_score=1.5),lambda p:p["actions"][1].update(owner=""),
            lambda p:p["actions"][1].update(target_date="2026-10-01"),lambda p:p["actions"][0].update(depends_on=["improve-activity"],target_date="2026-12-01"),
            lambda p:p["actions"][1].update(depends_on=["unknown"]),lambda p:p["actions"][1].update(criterion_id="allocation"),
            lambda p:p["actions"][1].update(target_date="2026-02-30"),lambda p:p["plan_review"].update(boundary_id="other")]
        for change in changes:
            state,_,params=planning_fixture();change(params);out=run_suppliers(state,"develop-supplier-improvement-plan",params)
            self.assertEqual(out["result"]["status"],"blocked");self.assertFalse(any(d["code"]=="SUPPLIER_IMPROVEMENT_PLAN" for d in out["result"]["diagnostics"]))

    def test_unaddressed_criteria_remain_visible(self):
        state,_,params=planning_fixture();params["actions"]=params["actions"][1:];params["actions"][0]["depends_on"]=[]
        out=run_suppliers(state,"develop-supplier-improvement-plan",params)
        self.assertEqual(report(out,"SUPPLIER_IMPROVEMENT_PLAN")["unaddressed_criterion_ids"],["allocation"])
        self.assertEqual(out["result"]["status"],"partial")

    def test_full_saved_two_step_replay(self):
        capture=json.loads((ROOT/"evaluations/sus14-supplier-planning.json").read_text(encoding="utf-8"))
        state=capture["state"]
        for step in capture["steps"]:
            output=run_suppliers(state,step["skill"],step["parameters"])
            self.assertEqual(output,step["output"]);state=output["proposal"]["state"]
