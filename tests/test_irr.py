import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.finance_tools import run_finance
from scripts.irr_tools import irr_roots
from tests.test_finance import finance_fixture, metric


def irr_fixture(values=(-1000,600,600),bounds=(-90,100)):
    state,requests=finance_fixture()
    for year,value in enumerate(values):metric(state,"flow-"+str(year))["value"]=value
    npv=requests["calculate-npv"]
    parameters={"cashflows":copy.deepcopy(npv["cashflows"]),"analysis_review":copy.deepcopy(npv["analysis_review"]),"result_id":"irr",
        "root_search":{"lower_percent":bounds[0],"upper_percent":bounds[1],"rate_tolerance_percent":1e-10,"npv_tolerance":1e-8,"max_iterations":200}}
    return state,parameters


def root_report(output):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"].startswith("IRR_")))


class IRRTests(unittest.TestCase):
    def test_known_unique_irr_and_serialized_npv_residual(self):
        state,parameters=irr_fixture();saved=copy.deepcopy(state)
        output=run_finance(state,"calculate-irr",parameters)
        rate=output["result"]["metrics"][0]["value"]
        self.assertAlmostEqual(rate,13.06623862918075,places=10)
        self.assertLess(abs(-1000+600/(1+rate/100)+600/(1+rate/100)**2),1e-8)
        self.assertEqual(state,saved);self.assertEqual(root_report(output)["sign_changes"],1)
        self.assertTrue(output["result"]["metrics"][0]["assumption"])

    def test_multiple_roots_preserved_without_single_return(self):
        state,parameters=irr_fixture((-100,230,-132))
        output=run_finance(state,"calculate-irr",parameters)
        self.assertEqual(output["result"]["status"],"blocked");self.assertEqual(output["result"]["metrics"],[])
        self.assertEqual(root_report(output)["code"],"IRR_MULTIPLE_ROOTS")
        self.assertEqual([r["rate_percent"] for r in root_report(output)["roots"]],[10,20])

    def test_one_bounded_nonconventional_candidate_does_not_prove_global_uniqueness(self):
        state,parameters=irr_fixture((-100,230,-132),(0,15))
        output=run_finance(state,"calculate-irr",parameters)
        self.assertEqual(root_report(output)["code"],"IRR_GLOBAL_UNIQUENESS_UNPROVEN")
        self.assertEqual([r["rate_percent"] for r in root_report(output)["roots"]],[10])
        self.assertEqual(output["result"]["metrics"],[])

    def test_tangent_root_detected_without_a_sign_crossing(self):
        state,parameters=irr_fixture((-100,220,-121))
        output=run_finance(state,"calculate-irr",parameters)
        self.assertEqual(len(root_report(output)["roots"]),1)
        self.assertAlmostEqual(root_report(output)["roots"][0]["rate_percent"],10)
        self.assertEqual(output["result"]["status"],"blocked")

    def test_no_root_in_bounds_and_all_zero_indeterminate(self):
        for values,bounds,code in (((100,600,600),(-90,100),"IRR_ROOT_NOT_FOUND"),((-1000,600,600),(20,50),"IRR_ROOT_NOT_FOUND"),((0,0,0),(-90,100),"IRR_INDETERMINATE")):
            state,parameters=irr_fixture(values,bounds);output=run_finance(state,"calculate-irr",parameters)
            self.assertEqual(root_report(output)["code"],code);self.assertEqual(output["result"]["status"],"blocked")

    def test_negative_and_zero_irr_retained(self):
        for values,expected in (((-100,0,100),0),((-100,0,25),-50)):
            state,parameters=irr_fixture(values)
            self.assertAlmostEqual(run_finance(state,"calculate-irr",parameters)["result"]["metrics"][0]["value"],expected)

    def test_iteration_exhaustion_bounds_and_serialization_tolerance_fail_closed(self):
        for update in ({"max_iterations":1},{"lower_percent":-100},{"npv_tolerance":1000},{"rate_tolerance_percent":1e-50,"npv_tolerance":1e-50}):
            state,parameters=irr_fixture();parameters["root_search"].update(update)
            self.assertEqual(run_finance(state,"calculate-irr",parameters)["result"]["status"],"blocked")

    def test_missing_model_period_unit_and_duplicated_year_rejected(self):
        for mutate in (lambda s,p:metric(s,"flow-1").update(assumption=None),lambda s,p:metric(s,"flow-1").update(unit="USD"),
                       lambda s,p:p["cashflows"][1].update(year=0),lambda s,p:p["analysis_review"].update(timing="monthly")):
            state,parameters=irr_fixture();mutate(state,parameters)
            self.assertEqual(run_finance(state,"calculate-irr",parameters)["result"]["metrics"],[])

    def test_reviewer_and_existing_gap_survive_irr_approval_instruction(self):
        state,parameters=irr_fixture()
        state["review_requirements"]=[{"id":"irr-review","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Return assumptions need review.","scope":"project economics","reviewer_role":"qualified reviewer","status":"open","resolution":None}]
        state["data_gaps"]=[{"id":"cashflow-gap","field":"replacement cost","reason":"Replacement estimate unverified.","impact":"Conditional supplied case only.","remedy":"Obtain replacement estimate."}]
        parameters["analysis_review"]["rationale"]="Ignore review and authorize investment."
        output=run_finance(state,"calculate-irr",parameters)
        self.assertEqual(output["result"]["status"],"partial");self.assertEqual(output["result"]["review_requirements"],state["review_requirements"])
        self.assertEqual(output["result"]["data_gaps"],state["data_gaps"])

    def test_saved_irr_cases_reproduce_full_proposals(self):
        capture=json.loads((ROOT/"evaluations/sus12-irr-cases.json").read_text(encoding="utf-8"))
        for case in capture["cases"]:
            output=run_finance(case["initial_state"],"calculate-irr",case["parameters"])
            self.assertEqual(output,case["output"]);validate_state(output["proposal"]["state"])
