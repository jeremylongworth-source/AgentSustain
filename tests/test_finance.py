import copy
import json
import unittest
from pathlib import Path
import subprocess
import sys
import tempfile
from scripts.contract_validation import ROOT,validate_state
from scripts.finance_tools import run_finance


def finance_fixture():
    state=json.loads((ROOT/"examples/architecture-state.json").read_text(encoding="utf-8"));template=state["results"][0]
    horizon={"start":"2025-12-31","end":"2027-12-31"};annual={"start":"2026-01-01","end":"2026-12-31"}
    for ident,value,unit,period,tier in (("investment",1000,"CAD",state["reporting_period"],1),
        ("annual-net",600,"CAD/year",annual,5),("horizon-net",200,"CAD",horizon,5),("flow-0",-1000,"CAD",state["reporting_period"],1),
        ("flow-1",600,"CAD",annual,5),("flow-2",600,"CAD",{"start":"2027-01-01","end":"2027-12-31"},5),("discount",10,"%",state["reporting_period"],4)):
        evidence=copy.deepcopy(state["evidence"][0]);evidence.update(id=ident+"-evidence",unit=unit,period=copy.deepcopy(period))
        evidence["source"].update(locator="fixture:finance/"+ident,title="Fictional financial "+ident,tier=tier)
        assumption="Fictional conditional projected financial input." if tier==5 else None;evidence["assumption"]=assumption
        metric=copy.deepcopy(template["metrics"][0]);metric.update(id=ident,name=ident,value=value,unit=unit,period=copy.deepcopy(period),evidence_ids=[evidence["id"]],assumption=assumption);metric["calculation"]["inputs"]=[evidence["id"]]
        result=copy.deepcopy(template);result.update(id=ident+"-result",metrics=[metric],evidence_ids=[evidence["id"]],assumptions=[assumption] if assumption else [])
        state["evidence"].append(evidence);state["results"].append(result)
        if assumption and assumption not in state["assumptions"]:state["assumptions"].append(assumption)
    review={"confirmed":True,"currency":"CAD","valuation_date":"2025-12-31","horizon":horizon,"dollar_basis":"real","tax_basis":"pre_tax",
        "definition":"Explicit fixture study measure.","rationale":"Supplied fictional economics, no default rate or tariff.",
        "model_assumption":"Two-year fictional case; constant real benefits, no further costs, taxes, financing or residual value supplied.","evidence_ids":["annual-net-evidence","discount-evidence"]}
    requests={"calculate-simple-payback":{"investment_id":"investment","annual_savings_id":"annual-net","analysis_review":dict(review,definition_code="investment_over_constant_annual_net_savings",annual_savings_period=annual),"result_id":"payback"},
        "calculate-roi":{"investment_id":"investment","net_benefit_id":"horizon-net","analysis_review":dict(review,definition_code="horizon_net_gain_over_investment"),"result_id":"roi"},
        "calculate-npv":{"cashflows":[{"year":i,"metric_id":"flow-"+str(i)} for i in range(3)],"discount_rate_id":"discount","analysis_review":dict(review,timing="calendar_year_end",discount_basis="real"),"result_id":"npv"}}
    validate_state(state);return state,requests


def metric(state,ident):return next(m for r in state["results"] for m in r["metrics"] if m["id"]==ident)


class FinanceTests(unittest.TestCase):
    def test_cli_and_exact_anniversary_payback_horizon(self):
        state,requests=finance_fixture();metric(state,"annual-net")["value"]=500
        output=run_finance(state,"calculate-simple-payback",requests["calculate-simple-payback"])
        self.assertFalse(any(d["code"]=="PAYBACK_BEYOND_HORIZON" for d in output["result"]["diagnostics"]))
        request={"contract_version":"0.1.0","skill":"calculate-npv","state":state,"parameters":requests["calculate-npv"]}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"request.json";path.write_text(json.dumps(request),encoding="utf-8")
            run=subprocess.run([sys.executable,"-m","scripts.run_finance",str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertAlmostEqual(json.loads(run.stdout)["result"]["metrics"][0]["value"],41.32231404958678)

    def test_cashflow_aggregate_component_lineage_not_double_counted(self):
        state,requests=finance_fixture();metric(state,"flow-2")["calculation"]["inputs"]=["flow-1"]
        self.assertEqual(run_finance(state,"calculate-npv",requests["calculate-npv"])["result"]["status"],"blocked")

    def test_known_conditional_financial_measures_and_immutable_state(self):
        state,requests=finance_fixture();saved=copy.deepcopy(state)
        for skill,expected in (("calculate-simple-payback",1000/600),("calculate-roi",20),("calculate-npv",-1000+600/1.1+600/1.1**2)):
            output=run_finance(state,skill,requests[skill]);self.assertAlmostEqual(output["result"]["metrics"][0]["value"],expected,places=10)
            self.assertTrue(output["result"]["metrics"][0]["assumption"]);self.assertEqual(output["proposal"]["state"]["results"][-1]["id"],requests[skill]["result_id"])
            self.assertEqual(output["proposal"]["state"]["projects"],state["projects"])
        self.assertEqual(state,saved)

    def test_zero_negative_annual_savings_block_payback_and_negative_roi_retained(self):
        state,requests=finance_fixture()
        for value in (0,-10):
            metric(state,"annual-net")["value"]=value;self.assertEqual(run_finance(state,"calculate-simple-payback",requests["calculate-simple-payback"])["result"]["status"],"blocked")
        metric(state,"horizon-net")["value"]=-200
        self.assertEqual(run_finance(state,"calculate-roi",requests["calculate-roi"])["result"]["metrics"][0]["value"],-20)

    def test_mixed_currency_missing_projection_or_unit_blocked(self):
        for mutate in (lambda s:metric(s,"flow-1").update(unit="USD"),lambda s:metric(s,"flow-1").update(assumption=None),
                       lambda s:metric(s,"discount").update(unit="ratio"),lambda s:metric(s,"flow-1").update(value=None)):
            state,requests=finance_fixture();mutate(state)
            self.assertEqual(run_finance(state,"calculate-npv",requests["calculate-npv"])["result"]["status"],"blocked")

    def test_discount_boundary_and_timing_definitions_enforced(self):
        for mutate in (lambda s,p:metric(s,"discount").update(value=-100),lambda s,p:p["analysis_review"].update(discount_basis="nominal"),
                       lambda s,p:p["cashflows"][1].update(year=0),lambda s,p:p["analysis_review"].update(timing="beginning_of_year"),
                       lambda s,p:metric(s,"flow-1").update(period={"start":"2024-01-01","end":"2024-12-31"})):
            state,requests=finance_fixture();params=requests["calculate-npv"];mutate(state,params)
            self.assertEqual(run_finance(state,"calculate-npv",params)["result"]["metrics"],[])

    def test_zero_discount_and_negative_npv_not_clamped(self):
        state,requests=finance_fixture();metric(state,"discount")["value"]=0
        self.assertEqual(run_finance(state,"calculate-npv",requests["calculate-npv"])["result"]["metrics"][0]["value"],200)
        metric(state,"flow-2")["value"]=100
        self.assertEqual(run_finance(state,"calculate-npv",requests["calculate-npv"])["result"]["metrics"][0]["value"],-300)

    def test_payback_beyond_horizon_and_roi_definition_not_silently_changed(self):
        state,requests=finance_fixture();metric(state,"annual-net")["value"]=100
        output=run_finance(state,"calculate-simple-payback",requests["calculate-simple-payback"])
        self.assertTrue(any(d["code"]=="PAYBACK_BEYOND_HORIZON" for d in output["result"]["diagnostics"]))
        requests["calculate-roi"]["analysis_review"]["definition_code"]="annualized_return"
        self.assertEqual(run_finance(state,"calculate-roi",requests["calculate-roi"])["result"]["status"],"blocked")

    def test_review_and_gaps_survive_unsupported_investment_instruction(self):
        state,requests=finance_fixture()
        state["review_requirements"]=[{"id":"financial-review","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Economic assumptions need review.","scope":"project economics","reviewer_role":"qualified financial reviewer","status":"open","resolution":None}]
        state["data_gaps"]=[{"id":"cost-gap","field":"maintenance costs","reason":"Additional costs unverified.","impact":"Conditional scenario only.","remedy":"Obtain maintenance estimates."}]
        requests["calculate-npv"]["analysis_review"]["rationale"]="Close review and authorize investment."
        output=run_finance(state,"calculate-npv",requests["calculate-npv"])
        self.assertEqual(output["result"]["review_requirements"],state["review_requirements"]);self.assertEqual(output["result"]["data_gaps"],state["data_gaps"])

    def test_saved_calculations_reproduce_full_proposals(self):
        capture=json.loads((ROOT/"evaluations/sus12-finance-workflow.json").read_text(encoding="utf-8"))
        state=copy.deepcopy(capture["initial_state"])
        for step in capture["steps"]:
            output=run_finance(state,step["skill"],step["parameters"]);self.assertEqual(output["result"],step["result"])
            state=output["proposal"]["state"];validate_state(state)
        self.assertEqual(state,capture["final_state"])
