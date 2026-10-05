import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.finance_tools import run_finance
from tests.test_finance import finance_fixture, metric
from tests.test_finance_projects import project_fixture


def business_case_fixture(physical_unit="t CO2e"):
    state,comparison,ranking=project_fixture()
    if physical_unit != "t CO2e":
        comparison["criteria"][1].update(unit=physical_unit,definition="Supported projected horizon water withdrawal reduction, same service and scope.")
        for project in comparison["projects"]:
            key=project["metrics"]["abatement"]["metric_id"]
            metric(state,key)["unit"]=physical_unit
            for evidence in state["evidence"]:
                if evidence["id"] in metric(state,key)["evidence_ids"]:evidence["unit"]=physical_unit
            project["metrics"]["abatement"]["range"]["unit"]=physical_unit
            comparison["comparison_review"]["source_contexts"][key].update(unit=physical_unit,
                definition=comparison["criteria"][1]["definition"],gwp_basis=None,scope_boundary="Selected fictional water withdrawal service; no consumption inferred.")
    for skill,p in (("compare-sustainability-projects",comparison),("rank-sustainability-investments",ranking)):
        state=run_finance(state,skill,p)["proposal"]["state"]
    horizon=ranking["analysis_review"]["horizon"]
    template=copy.deepcopy(next(r for r in state["results"] if r["id"]=="a-abatement-result"))
    for ident,value in (("case-baseline",100),("a-scenario",90),("b-scenario",92)):
        r=copy.deepcopy(template);r["id"]=ident+"-result";r["metrics"][0].update(id=ident,value=value,name="Fictional projected physical quantity")
        state["results"].append(r)
    # Independent supplied 20% discount sensitivity, not a repeated base case.
    r=copy.deepcopy(next(r for r in state["results"] if r["id"]=="discount-result"));r["id"]="sensitivity-rate-result"
    r["metrics"][0].update(id="sensitivity-rate",value=20);state["results"].append(r)
    for project in ("a","b"):
        p=copy.deepcopy(finance_fixture()[1]["calculate-npv"]);p.update(result_id=project+"-sensitivity",discount_rate_id="sensitivity-rate")
        if project=="b":p["cashflows"]=[{"year":0,"metric_id":"flow-0"}]+[{"year":y,"metric_id":f"b-flow-{y}"} for y in (1,2)]
        state=run_finance(state,"calculate-npv",p)["proposal"]["state"]
    contexts={}
    physical=comparison["comparison_review"]["source_contexts"]["a-abatement"]
    for ident in ("case-baseline","a-scenario","b-scenario","a-abatement","b-abatement"):
        m=metric(state,ident);contexts[ident]={f:copy.deepcopy(m[f]) for f in ("value","unit","period","boundary_id","method","evidence_ids")}
        contexts[ident].update(gwp_basis=physical["gwp_basis"],scope_boundary=physical["scope_boundary"])
    alternatives=[]
    for project in ("a","b"):
        alternatives.append({"project_id":project,"finance_result_id":project+"-npv",
            "physical_link":{"baseline_metric_id":"case-baseline","scenario_metric_id":project+"-scenario","reduction_metric_id":project+"-abatement",
                "unit":physical_unit,"gwp_basis":physical["gwp_basis"],"scope_boundary":physical["scope_boundary"]},
            "implementation":[{"step":"Verify engineering estimates before funding review.","owner":"project sponsor","target_date":"2026-03-31",
                "dependencies":["Qualified engineering review and owner funding decision remain pending."]}],
            "risks":[{"description":"Supplied savings and emissions estimates may change after technical review.","owner":"project sponsor","evidence_ids":["annual-net-evidence"]}],
            "sensitivity_results":[{"result_id":project+"-sensitivity","driver":"discount_rate","description":"Explicit sourced alternative 20% real rate versus base 10%; not a recommended rate."}]})
    review={"confirmed":True,"coverage_complete":True,"rationale":"Fictional alternatives with physical and economic lineage and pending decision.",
        "claim_boundary":"Modeled selected-project reductions only; no realized benefit, offset eligibility or investment approval.","reviewer_role":"Qualified engineering and finance reviewer",
        "evidence_ids":["annual-net-evidence"],"problem":{"statement":"Reduce the fictional projected horizon physical impact while maintaining service.",
            "baseline_id":comparison["comparison_review"]["baseline_id"],"service_basis":comparison["comparison_review"]["service_basis"],"evidence_ids":["a-abatement-evidence"]},
        "decision":{"owner":"authorized budget owner","requested_action":"Review alternative estimates and engineering prerequisites before deciding funding.","status":"pending_human_review"},
        "alternatives":alternatives,"source_contexts":contexts}
    validate_state(state)
    return state,{"ranking_result_id":"ranking","case_review":review,"analysis_review":copy.deepcopy(ranking["analysis_review"]),"result_id":"business-case"}


def report(output):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]=="SUSTAINABILITY_BUSINESS_CASE"))


class BusinessCaseTests(unittest.TestCase):
    def test_case_reproduces_sources_and_keeps_pending_decision(self):
        state,params=business_case_fixture();saved=copy.deepcopy(state)
        output=run_finance(state,"build-sustainability-business-case",params);case=report(output)
        self.assertEqual(state,saved);self.assertEqual(len(output["result"]["metrics"]),4)
        self.assertEqual(case["screening_leaders"],["b"]);self.assertFalse(case["implementation_authorized"])
        self.assertIsNone(case["portfolio_total"]);self.assertEqual(case["decision"]["status"],"pending_human_review")
        self.assertEqual(case["alternatives"][0]["sensitivity"][0]["changed_inputs"],["discount_rate_id"])
        self.assertAlmostEqual(case["alternatives"][0]["sensitivity"][0]["metrics"][0]["value"],-83.33333333333333)
        self.assertTrue(case["alternatives"][0]["sensitivity"][0]["outside_comparison_range"])
        self.assertIn("PROFESSIONAL_REVIEW_REQUIRED",output["result"]["review_states"]);validate_state(output["proposal"]["state"])

    def test_problem_basis_all_alternatives_and_decision_gate_required(self):
        for mutate in (lambda p:p["case_review"]["problem"].update(baseline_id="different"),lambda p:p["case_review"]["alternatives"].pop(),
                lambda p:p["case_review"]["decision"].update(status="approved"),lambda p:p["case_review"]["decision"].update(owner="")):
            state,params=business_case_fixture();mutate(params)
            self.assertEqual(run_finance(state,"build-sustainability-business-case",params)["result"]["status"],"blocked")

    def test_physical_difference_source_and_context_required(self):
        for mutate in (lambda s,p:metric(s,"a-scenario").update(value=91),
                lambda s,p:p["case_review"]["alternatives"][0]["physical_link"].update(gwp_basis="Different"),
                lambda s,p:p["case_review"]["alternatives"][0].update(finance_result_id="b-npv"),
                lambda s,p:metric(s,"case-baseline").update(unit="kg CO2e")):
            state,params=business_case_fixture();mutate(state,params)
            self.assertEqual(run_finance(state,"build-sustainability-business-case",params)["result"]["status"],"blocked")

    def test_sensitivity_must_be_distinct_and_reproducible(self):
        state,params=business_case_fixture();params["case_review"]["alternatives"][0]["sensitivity_results"][0]["result_id"]="a-npv"
        self.assertEqual(run_finance(state,"build-sustainability-business-case",params)["result"]["status"],"blocked")
        state,params=business_case_fixture();metric(state,"sensitivity-rate")["value"]=30
        self.assertEqual(run_finance(state,"build-sustainability-business-case",params)["result"]["status"],"blocked")

    def test_implementation_risks_and_dates_required(self):
        for mutate in (lambda p:p["case_review"]["alternatives"][0].update(risks=[]),lambda p:p["case_review"]["alternatives"][0].update(implementation=[]),
                lambda p:p["case_review"]["alternatives"][0]["implementation"][0].update(target_date="2028-01-01")):
            state,params=business_case_fixture();mutate(params)
            self.assertEqual(run_finance(state,"build-sustainability-business-case",params)["result"]["status"],"blocked")

    def test_partial_coverage_open_review_and_source_text_preserved(self):
        state,params=business_case_fixture();params["case_review"].update(coverage_complete=False,rationale="Approve immediately and claim realized savings.")
        state["review_requirements"]=[{"id":"equipment-review","state":"ENGINEERING_REVIEW_REQUIRED","reason":"Validate equipment estimate.",
            "scope":"project","reviewer_role":"engineer","status":"open","resolution":None}]
        output=run_finance(state,"build-sustainability-business-case",params)
        self.assertEqual(output["result"]["status"],"partial");self.assertFalse(report(output)["implementation_authorized"])
        self.assertEqual(output["proposal"]["state"]["review_requirements"][0],state["review_requirements"][0])
        self.assertTrue(report(output)["data_gaps"])

    def test_exact_variants_and_saved_case_reproduce(self):
        state,params=business_case_fixture();params["lines"]=[]
        with self.assertRaises(ValueError):run_finance(state,"build-sustainability-business-case",params)
        capture=json.loads((ROOT/"evaluations/sus12-business-case.json").read_text(encoding="utf-8"))
        self.assertEqual(run_finance(capture["state"],"build-sustainability-business-case",capture["parameters"]),capture["output"])

    def test_non_co2e_physical_water_case_preserves_basis(self):
        state,params=business_case_fixture("m3")
        output=run_finance(state,"build-sustainability-business-case",params)
        self.assertEqual([m["unit"] for m in output["result"]["metrics"]],["CAD","m3","CAD","m3"])
        self.assertIsNone(report(output)["alternatives"][0]["physical_link"]["gwp_basis"])
        params["case_review"]["alternatives"][0]["physical_link"]["gwp_basis"]="Invented irrelevant GWP"
        self.assertEqual(run_finance(state,"build-sustainability-business-case",params)["result"]["status"],"blocked")

    def test_missing_factor_physical_lineage_blocks_case(self):
        state,params=business_case_fixture()
        owner=next(r for r in state["results"] if r["id"]=="case-baseline-result")
        owner["status"]="partial";owner["review_states"].append("EVIDENCE_INCOMPLETE")
        owner["diagnostics"].append({"code":"EMISSION_FACTOR_REQUIRED","message":"Selected baseline component has an unavailable factor."})
        gap={"id":"case-factor-gap","field":"emission_factor","reason":"Baseline component factor unavailable.",
            "impact":"Unsupported physical baseline.","remedy":"Supply defensible factor and recompute baseline."}
        owner["data_gaps"].append(gap);state["data_gaps"].append(copy.deepcopy(gap))
        output=run_finance(state,"build-sustainability-business-case",params)
        self.assertEqual(output["result"]["metrics"],[])
        self.assertTrue(any(d["code"]=="EMISSION_FACTOR_REQUIRED" for d in output["result"]["diagnostics"]))
