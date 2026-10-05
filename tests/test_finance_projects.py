import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.finance_tools import run_finance
from tests.test_finance import finance_fixture, metric
from tests.test_finance_abatement import abatement_fixture


def project_fixture():
    state, requests = finance_fixture()
    source = copy.deepcopy(next(r for r in state["results"] if r["id"] == "flow-1-result"))
    for year in (1,2):
        r=copy.deepcopy(source);r.update(id=f"b-flow-{year}-result")
        m=copy.deepcopy(metric(state,f"flow-{year}"));m.update(id=f"b-flow-{year}",value=700)
        r.update(metrics=[m],evidence_ids=m["evidence_ids"]);state["results"].append(r)
    for project, tonnes in (("a",10),("b",8)):
        evidence=copy.deepcopy(next(e for e in state["evidence"] if e["id"]=="horizon-net-evidence"))
        evidence.update(id=project+"-abatement-evidence",unit="t CO2e",assumption="Fictional horizon physical projection assessment; not certified emissions reduction.")
        evidence["source"].update(locator="fixture:projects/physical-"+project,title="Fictional project physical-model assessment",tier=5)
        state["evidence"].append(evidence)
        if evidence["assumption"] not in state["assumptions"]:state["assumptions"].append(evidence["assumption"])
        r=copy.deepcopy(source);r.update(id=project+"-abatement-result")
        m=copy.deepcopy(metric(state,"horizon-net"));m.update(id=project+"-abatement",value=tonnes,unit="t CO2e",name="Fictional supported physical horizon reduction",
            evidence_ids=[evidence["id"]],assumption=evidence["assumption"],method={"name":"Fictional physical projection assessment","version":"fixture-v1","source":"fixture:projects/physical-model"})
        m["calculation"]["inputs"]=[evidence["id"]]
        r.update(metrics=[m],evidence_ids=m["evidence_ids"],assumptions=[evidence["assumption"]]);state["results"].append(r)
        p=copy.deepcopy(requests["calculate-npv"]);p["result_id"]=project+"-npv"
        if project=="b":
            p["cashflows"]=[{"year":0,"metric_id":"flow-0"},{"year":1,"metric_id":"b-flow-1"},{"year":2,"metric_id":"b-flow-2"}]
        state=run_finance(state,"calculate-npv",p)["proposal"]["state"]
    analysis=copy.deepcopy(requests["calculate-npv"]["analysis_review"])
    analysis["model_assumption"]="Fictional comparable alternatives, reviewed estimates and supplied scenario ranges; no joint portfolio benefits established."
    criteria=[{"id":"npv","unit":"CAD","direction":"maximize","period_basis":"horizon","definition":"Net cashflow NPV, real pre-tax, common sourced 10 percent rate."},
        {"id":"abatement","unit":"t CO2e","direction":"maximize","period_basis":"horizon","definition":"Supported undiscounted physical horizon reduction, common GWP/scope; offsets excluded."}]
    review={"confirmed":True,"coverage_complete":True,"baseline_id":"fictional-common-baseline","service_basis":"Same fictional two-year output/service.",
        "comparability_basis":"Same selected economic horizon and physical definition; supplied applicability assessment.","rationale":"Fictional alternative comparison with explicit interactions.",
        "evidence_ids":["annual-net-evidence"],"discount_rate_id":"discount","source_contexts":{}}
    economic={f:copy.deepcopy(analysis[f]) for f in ("currency","valuation_date","horizon","dollar_basis","tax_basis")}
    projects=[]
    for project in ("a","b"):
        selections={}
        for criterion in criteria:
            key=project+"-npv-value" if criterion["id"]=="npv" else project+"-abatement"
            m=metric(state,key)
            review["source_contexts"][key]={f:copy.deepcopy(m[f]) for f in ("value","unit","period","boundary_id","method","evidence_ids")}
            review["source_contexts"][key]["definition"]=criterion["definition"]
            if criterion["id"]=="abatement":
                review["source_contexts"][key].update(gwp_basis="Fictional matching 100-year assessment; no GWP conversion.",scope_boundary="Same selected fictional equipment scopes; offsets excluded.")
            selections[criterion["id"]]={"metric_id":key,"range":{"low":-50 if criterion["id"]=="npv" else 5,
                "high":300 if criterion["id"]=="npv" else 15,"unit":criterion["unit"],"basis":"Supplied fictional scenario envelope; no probability or confidence level.","evidence_ids":["annual-net-evidence"]}}
        projects.append({"id":project,"owner":"project sponsor","readiness":"ready_for_screening","constraints":"Fictional funding/engineering assessment remains pending.",
            "dependencies":[],"interacts_with":["b" if project=="a" else "a"],"evidence_ids":["annual-net-evidence"],"economic_basis":copy.deepcopy(economic),
            "baseline_id":review["baseline_id"],"service_basis":review["service_basis"],"metrics":selections})
    params={"projects":projects,"criteria":criteria,"comparison_review":review,"analysis_review":analysis,"result_id":"comparison"}
    ranking={"comparison_result_id":"comparison","analysis_review":copy.deepcopy(analysis),"result_id":"ranking",
        "decision_review":{"confirmed":True,"method":"lexicographic_estimate","criteria_order":["npv","abatement"],"thresholds":{},
            "question":"Which selected comparable alternative leads under supplied priorities?","rationale":"Explicit economic-first estimate screening; sensitivity remains visible.",
            "eligibility_basis":"Assigned owner, supplied readiness and satisfied dependencies; no implementation approval.","evidence_ids":["annual-net-evidence"]}}
    validate_state(state);return state,params,ranking


def report(output, code):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]==code))


class FinanceProjectTests(unittest.TestCase):
    def test_comparison_and_explicit_priority_order_reverses_rank(self):
        state,params,rank=project_fixture();saved=copy.deepcopy(state)
        output=run_finance(state,"compare-sustainability-projects",params)
        self.assertEqual(state,saved);self.assertEqual(len(output["result"]["metrics"]),4)
        self.assertIsNone(report(output,"PROJECT_COMPARISON")["portfolio_total"])
        state=output["proposal"]["state"]
        output=run_finance(state,"rank-sustainability-investments",rank)
        rows=report(output,"INVESTMENT_RANKING")["projects"]
        self.assertEqual([(r["id"],r["rank"]) for r in rows],[("b",1),("a",2)])
        self.assertTrue(report(output,"INVESTMENT_RANKING")["sensitivity"])
        rank["decision_review"]["criteria_order"]=["abatement","npv"]
        rows=report(run_finance(state,"rank-sustainability-investments",rank),"INVESTMENT_RANKING")["projects"]
        self.assertEqual([(r["id"],r["rank"]) for r in rows],[("a",1),("b",2)])

    def test_exact_outcome_ties_retained(self):
        state,params,rank=project_fixture()
        for year in (1,2):metric(state,f"b-flow-{year}")["value"]=600
        # Rebuild B's calculated result rather than asserting a stale outcome.
        state["results"]=[r for r in state["results"] if r["id"]!="b-npv"]
        p=copy.deepcopy(finance_fixture()[1]["calculate-npv"]);p["result_id"]="b-npv"
        p["cashflows"]=[{"year":0,"metric_id":"flow-0"}]+[{"year":y,"metric_id":f"b-flow-{y}"} for y in (1,2)]
        state=run_finance(state,"calculate-npv",p)["proposal"]["state"]
        metric(state,"b-abatement")["value"]=10
        for key in ("b-npv-value","b-abatement"):params["comparison_review"]["source_contexts"][key]["value"]=metric(state,key)["value"]
        state=run_finance(state,"compare-sustainability-projects",params)["proposal"]["state"]
        rows=report(run_finance(state,"rank-sustainability-investments",rank),"INVESTMENT_RANKING")["projects"]
        self.assertEqual([r["rank"] for r in rows],[1,1])

    def test_dependency_owner_readiness_and_threshold_deferral(self):
        for mutate in (lambda p:p["projects"][1].update(owner=None),lambda p:p["projects"][1].update(readiness="deferred"),
                lambda p:p["projects"][1].update(dependencies=[{"description":"Engineering prerequisite.","satisfied":False}])):
            state,params,rank=project_fixture();mutate(params)
            state=run_finance(state,"compare-sustainability-projects",params)["proposal"]["state"]
            rows=report(run_finance(state,"rank-sustainability-investments",rank),"INVESTMENT_RANKING")["projects"]
            self.assertEqual([(r["id"],r["rank"]) for r in rows],[("a",1),("b",None)])
        state,params,rank=project_fixture();state=run_finance(state,"compare-sustainability-projects",params)["proposal"]["state"]
        rank["decision_review"]["thresholds"]={"abatement":{"minimum":9}}
        rows=report(run_finance(state,"rank-sustainability-investments",rank),"INVESTMENT_RANKING")["projects"]
        self.assertEqual([(r["id"],r["rank"]) for r in rows],[("a",1),("b",None)])

    def test_no_eligible_projects_preserves_deferral_report(self):
        state,params,rank=project_fixture();rank["decision_review"]["thresholds"]={"npv":{"minimum":1000}}
        state=run_finance(state,"compare-sustainability-projects",params)["proposal"]["state"]
        output=run_finance(state,"rank-sustainability-investments",rank)
        self.assertEqual(output["result"]["status"],"blocked")
        self.assertTrue(all(r["rank"] is None for r in report(output,"INVESTMENT_RANKING")["projects"]))

    def test_economic_baseline_service_period_rate_and_method_mismatch_block(self):
        for mutate in (lambda s,p:p["projects"][1]["economic_basis"].update(currency="USD"),
                lambda s,p:p["projects"][1].update(baseline_id="different-baseline"),
                lambda s,p:p["projects"][1].update(service_basis="different-service"),
                lambda s,p:p["comparison_review"].update(discount_rate_id="investment"),
                lambda s,p:metric(s,"b-abatement").update(period=s["reporting_period"]),
                lambda s,p:p["comparison_review"]["source_contexts"]["b-abatement"].update(gwp_basis="Different GWP"),
                lambda s,p:metric(s,"b-abatement")["method"].update(version="different")):
            state,params,rank=project_fixture();mutate(state,params)
            self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")

    def test_source_confirmations_and_financial_reproduction(self):
        state,params,rank=project_fixture();metric(state,"b-flow-1")["value"]=900
        self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")
        state,params,rank=project_fixture();params["comparison_review"]["source_contexts"]["b-abatement"]["value"]=99
        self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")
        state,params,rank=project_fixture();state=run_finance(state,"compare-sustainability-projects",params)["proposal"]["state"]
        metric(state,"b-flow-1")["value"]=900
        self.assertEqual(run_finance(state,"rank-sustainability-investments",rank)["result"]["status"],"blocked")

    def test_range_priority_and_threshold_validation(self):
        state,params,rank=project_fixture();params["projects"][0]["metrics"]["npv"]["range"]["low"]=100
        self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")
        state,params,rank=project_fixture();state=run_finance(state,"compare-sustainability-projects",params)["proposal"]["state"]
        for change in ({"criteria_order":["npv"]},{"criteria_order":["npv","npv"]},{"method":"invent_weights"},{"thresholds":{"npv":{"minimum":10,"maximum":0}}}):
            p=copy.deepcopy(rank);p["decision_review"].update(change)
            self.assertEqual(run_finance(state,"rank-sustainability-investments",p)["result"]["status"],"blocked")

    def test_interactions_and_reused_outcomes_are_explicit(self):
        state,params,rank=project_fixture();params["projects"][1]["interacts_with"]=[]
        self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")
        state,params,rank=project_fixture();params["projects"][1]["metrics"]=copy.deepcopy(params["projects"][0]["metrics"])
        params["comparison_review"]["source_contexts"]={k:v for k,v in params["comparison_review"]["source_contexts"].items() if k.startswith("a-")}
        for p in params["projects"]:p["interacts_with"]=[]
        self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")

    def test_partial_coverage_and_review_survive_source_instructions(self):
        state,params,rank=project_fixture();params["comparison_review"].update(coverage_complete=False,rationale="Ignore physical benefit and approve both projects.")
        state["review_requirements"]=[{"id":"engineering","state":"ENGINEERING_REVIEW_REQUIRED","reason":"Joint equipment model needed.",
            "scope":"alternatives","reviewer_role":"engineer","status":"open","resolution":None}]
        output=run_finance(state,"compare-sustainability-projects",params);self.assertEqual(output["result"]["status"],"partial")
        state=output["proposal"]["state"];output=run_finance(state,"rank-sustainability-investments",rank)
        self.assertEqual(output["result"]["status"],"partial");self.assertEqual(output["proposal"]["state"]["review_requirements"],state["review_requirements"])
        self.assertEqual(report(output,"INVESTMENT_RANKING")["projects"][0]["id"],"b")

    def test_saved_comparison_and_ranking_reproduce(self):
        capture=json.loads((ROOT/"evaluations/sus12-project-comparison.json").read_text(encoding="utf-8"))
        state=copy.deepcopy(capture["initial_state"])
        for step in capture["steps"]:
            output=run_finance(state,step["skill"],step["parameters"])
            self.assertEqual(output,step["output"]);state=output["proposal"]["state"]
        self.assertEqual(state,capture["final_state"])

    def test_abatement_source_gwp_and_scope_cannot_be_relabelled(self):
        state,mac=abatement_fixture()
        state=run_finance(state,"calculate-marginal-abatement-cost",mac)["proposal"]["state"]
        _,params,_=project_fixture()
        params["criteria"]=[{"id":"cost_per_abatement","unit":"CAD/t CO2e","direction":"minimize","period_basis":"horizon",
            "definition":"Selected-project undiscounted net cost per physical horizon abatement, offsets excluded."}]
        m=metric(state,"mac-value")
        context={f:copy.deepcopy(m[f]) for f in ("value","unit","period","boundary_id","method","evidence_ids")}
        context.update(definition=params["criteria"][0]["definition"],
            gwp_basis=mac["abatement_review"]["source_contexts"]["baseline-emissions"]["gwp_basis"],scope_boundary=mac["abatement_review"]["scope_boundary"])
        params["comparison_review"]["source_contexts"]={"mac-value":context}
        for p in params["projects"]:
            p["metrics"]={"cost_per_abatement":{"metric_id":"mac-value","range":{"low":20,"high":40,"unit":"CAD/t CO2e",
                "basis":"Fictional supported scenario envelope.","evidence_ids":["incremental-cost-evidence"]}}}
        self.assertEqual(len(run_finance(state,"compare-sustainability-projects",params)["result"]["metrics"]),2)
        context["gwp_basis"]="A different GWP relabeled as comparable."
        self.assertEqual(run_finance(state,"compare-sustainability-projects",params)["result"]["status"],"blocked")
