import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.contract_validation import ROOT, validate_state
from scripts.operations_tools import CARBON_PARAMETERS, INTERPRETATIONS, RUNNERS, run_operations
from tests.test_energy import energy_fixture
from tests.test_water import water_fixture
from tests.test_resources import resource_fixture
from tests.test_finance import finance_fixture
from tests.test_finance_business_case import business_case_fixture
from scripts.finance_tools import run_finance
from scripts.state_proposal import propose
from tests.test_scope_accounting import scope_fixture


def operations_fixture():
    state,quantities,water_review=water_fixture()
    energy,energy_review=energy_fixture();finance,financial_requests=finance_fixture()
    for snapshot in (energy,finance):
        for collection in ("evidence","results"):
            known={x["id"] for x in state[collection]}
            state[collection].extend(copy.deepcopy(x) for x in snapshot[collection] if x["id"] not in known)
        state["assumptions"]=list(dict.fromkeys(state["assumptions"]+snapshot["assumptions"]))
    _,streams,waste_review,_=resource_fixture()
    material_review={"confirmed":True,"basis":"consumed_material","measurement_boundary":"Selected fictional material consumed.",
        "nonoverlap_assessment":"One independently supplied quantity.","coverage":"Selected fictional consumption.","rationale":"Fictional source assessment.","evidence_ids":["consumed-evidence"]}
    steps=[{"skill":"build-energy-baseline","parameters":{"metric_ids":["metric-001","second-meter"],"coverage_review":energy_review,"result_id":"ops-energy"}},
        {"skill":"build-water-baseline","parameters":{"quantities":quantities,"coverage_review":water_review,"result_id":"ops-water"}},
        {"skill":"build-waste-baseline","parameters":{"streams":streams,"coverage_review":waste_review,"result_id":"ops-waste"}},
        {"skill":"analyze-material-consumption","parameters":{"metric_ids":["consumed"],"coverage_review":material_review,"result_id":"ops-materials"}},
        {"skill":"calculate-npv","parameters":dict(financial_requests["calculate-npv"],result_id="ops-finance")}]
    opportunities=[]
    for domain in ("energy","water","waste","materials"):
        opportunities.append({"id":"candidate-"+domain,"domain":domain,"description":"Investigate source-backed "+domain+" efficiency without claiming an unsupported saving.",
            "owner":"operations sponsor","evidence_ids":["ev-001"],"assessment_result_ids":["ops-"+domain],"business_case_result_id":None,"business_case_applicability":None,
            "interacts_with":[],"actions":[{"description":"Review domain measurement scope and gather missing information.","owner":"facility analyst","kind":"data_collection",
                "target_date":"2026-03-31","prerequisite_review_ids":[]},{"description":"Consider scoped pilot only after technical and funding review.","owner":"operations sponsor",
                "kind":"implementation","target_date":"2026-09-30","prerequisite_review_ids":[]}]})
    review={"confirmed":True,"objective":"Connect selected domain performance and economics to owned candidate follow-up.","scope_boundary":"Fictional selected facility; source measurement bases remain separate.",
        "rationale":"Synthetic composed operations scenario; no actual equipment or funding approval.","evidence_ids":["ev-001"],"coverage_complete":False,
        "planning_period":{"start":"2026-01-01","end":"2026-12-31"}}
    validate_state(state);return state,{"steps":steps,"opportunities":opportunities,"planning_review":review,"result_id":"operations"}


def carbon_operations_fixture():
    state,params=operations_fixture();carbon,sources,components,coverage=scope_fixture()
    known={e["id"] for e in state["evidence"]}
    state["evidence"].extend(copy.deepcopy(e) for e in carbon["evidence"] if e["id"] not in known)
    state["emission_factors"]=copy.deepcopy(carbon["emission_factors"])
    policy=copy.deepcopy(components[0]["policy"])
    component=copy.deepcopy(components[0]);component["metric_id"]="operations-co2e-metric"
    screening=[{"category":i,"status":"unknown","evidence_ids":["ev-001"],
        "rationale":"Fictional operations example lacks category applicability evidence; not assumed zero."} for i in range(1,16)]
    review={"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Selected first electricity feed only; direct emissions and other feed/category coverage remain missing.","gwp_basis":coverage["gwp_basis"]}
    steps=[{"skill":"calculate-co2e","parameters":{"activity_id":"metric-001","factor_id":component["factor_id"],"policy":policy,"result_id":"operations-co2e","fixture_mode":True}},
        {"skill":"calculate-location-based-scope-2","parameters":{"sources":sources,"components":[component],"coverage_review":coverage,"result_id":"operations-location","fixture_mode":True}},
        {"skill":"build-ghg-inventory","parameters":{"scope1_result_id":None,"scope2_result_id":"operations-location","scope3_result_ids":[],"category_screening":screening,"coverage_review":review,"result_id":"operations-inventory","fixture_mode":True}},
        {"skill":"identify-emission-hotspots","parameters":{"inventory_id":"operations-inventory","level":"scope","coverage_review":{"confirmed":True,"inventory_id":"operations-inventory","level":"scope","evidence_ids":["ev-001"],"rationale":"Selected nonoverlapping account contributions only."},"result_id":"operations-emission-hotspots","fixture_mode":True}}]
    params["steps"]=params["steps"]+steps
    params["opportunities"][0]["assessment_result_ids"] += [s["parameters"]["result_id"] for s in steps]
    return state,params


class OperationsTests(unittest.TestCase):
    def test_carbon_inventory_and_hotspots_compose_with_physical_assessment(self):
        state,params=carbon_operations_fixture();saved=copy.deepcopy(state)
        output=run_operations(state,params);candidate=output["proposal"]["state"]
        results={r["id"]:r for r in candidate["results"]}
        for ident in ("operations-co2e","operations-location","operations-inventory"):
            self.assertEqual(results[ident]["metrics"][0]["value"],500)
            self.assertEqual(results[ident]["metrics"][0]["unit"],"kg CO2e")
        self.assertEqual(results["operations-inventory"]["status"],"partial")
        self.assertEqual(results["operations-emission-hotspots"]["metrics"][0]["value"],500)
        self.assertEqual(results["ops-energy"]["metrics"][0]["value"],1500)
        self.assertEqual(state,saved);self.assertEqual(candidate["revision"],state["revision"]+1)
        self.assertEqual(output["result"]["metrics"],[])
        self.assertFalse(candidate["opportunities"][-4]["attributes"]["implementation_authorized"])

    def test_carbon_missing_factor_and_fixture_default_remain_blocked(self):
        for mode in ("missing","ordinary"):
            with self.subTest(mode=mode):
                state,params=carbon_operations_fixture()
                if mode=="missing":params["steps"][-4]["parameters"]["factor_id"]="missing"
                else:
                    for step in params["steps"][-4:]:step["parameters"].pop("fixture_mode")
                output=run_operations(state,params)
                self.assertEqual(output["result"]["status"],"partial")
                self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})
                results={r["id"]:r for r in output["proposal"]["state"]["results"]}
                self.assertEqual(results["operations-co2e"]["status"],"blocked")
                self.assertEqual(results["operations-co2e"]["metrics"],[])
                self.assertEqual(results["operations-inventory"]["metrics"],[])
                self.assertEqual(results["ops-energy"]["metrics"][0]["value"],1500)

    def test_carbon_adapter_rejects_extra_or_missing_parameters(self):
        for change in (lambda p:p.update(invent_factor=True),lambda p:p.pop("policy")):
            state,params=carbon_operations_fixture();change(params["steps"][-4]["parameters"])
            with self.assertRaises(ValueError):run_operations(state,params)

    def test_context_composition_replays_interpretations_and_checked_plan(self):
        capture=json.loads((ROOT/"evaluations/sus13-context-composition.json").read_text(encoding="utf-8"))
        state=copy.deepcopy(capture["initial_state"])
        state["evidence"].extend(capture["added_evidence"])
        for step in capture["author_steps"]:
            state=propose(state,step["result"],step["reason"])["state"]
        self.assertEqual(state,capture["state"])
        output=run_operations(state,capture["parameters"])
        self.assertEqual(output,capture["output"])
        self.assertEqual(output["proposal"]["state"]["review_requirements"],state["review_requirements"])
        self.assertEqual(output["proposal"]["state"]["results"][:len(state["results"])],state["results"])
        for candidate in output["proposal"]["state"]["opportunities"][-4:]:
            self.assertEqual(candidate["attributes"]["assessment_coverage"],"incomplete")
            self.assertTrue(candidate["attributes"]["interpretation_result_ids"])
            self.assertFalse(candidate["attributes"]["implementation_authorized"])

    def test_context_links_reject_unknown_duplicate_and_wrong_domain_results(self):
        capture=json.loads((ROOT/"evaluations/sus13-context-composition.json").read_text(encoding="utf-8"))
        for links in (["unknown"],["operations-water-interpretation"],
                ["operations-energy-interpretation"]*2):
            with self.subTest(links=links):
                params=copy.deepcopy(capture["parameters"])
                params["opportunities"][0]["interpretation_result_ids"]=links
                output=run_operations(capture["state"],params)
                self.assertEqual(output["result"]["status"],"blocked")
                self.assertEqual(output["proposal"]["state"]["opportunities"],capture["state"]["opportunities"])
        state=copy.deepcopy(capture["state"])
        source=next(r for r in state["results"] if r["id"]=="operations-energy-interpretation")
        source["evidence_ids"]=[]
        output=run_operations(state,capture["parameters"])
        self.assertEqual(output["result"]["status"],"blocked")
        self.assertEqual(output["proposal"]["state"]["opportunities"],state["opportunities"])

    def test_cross_domain_action_sequence_retains_unapproved_work(self):
        state,params=operations_fixture()
        for opportunity in params["opportunities"]:
            for index,action in enumerate(opportunity["actions"]):
                action.update(id=opportunity["domain"]+"-"+str(index),depends_on=[])
            opportunity["actions"][1]["depends_on"]=[opportunity["domain"]+"-0"]
        params["opportunities"][0]["actions"][1]["depends_on"].append("materials-0")
        saved=copy.deepcopy(state);output=run_operations(state,params)
        report=json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]=="OPERATIONS_ACTION_SEQUENCE"))
        order=report["action_ids"]
        self.assertLess(order.index("materials-0"),order.index("energy-1"))
        self.assertFalse(report["completion_verified"]);self.assertFalse(report["implementation_authorized"])
        self.assertEqual(state,saved)
        self.assertTrue(all(not a["attributes"]["implementation_authorized"] for a in output["proposal"]["state"]["opportunities"]))

    def test_invalid_action_graph_never_registers_candidates(self):
        def request():
            state,params=operations_fixture()
            for opportunity in params["opportunities"]:
                for index,action in enumerate(opportunity["actions"]):
                    action.update(id=opportunity["domain"]+"-"+str(index),depends_on=[])
            return state,params
        def cycle(p):
            p["opportunities"][0]["actions"][0]["depends_on"]=["water-0"]
            p["opportunities"][1]["actions"][0]["depends_on"]=["energy-0"]
        changes=[lambda p:p["opportunities"][0]["actions"][0].update(depends_on=["unknown"]),
            lambda p:p["opportunities"][0]["actions"][0].update(depends_on=["energy-0"]),
            lambda p:p["opportunities"][0]["actions"][0].update(depends_on=["energy-1"]),
            lambda p:p["opportunities"][0]["actions"][0].update(depends_on=["water-0","water-0"]),
            lambda p:p["opportunities"][0]["actions"][0].update(id="water-0"),cycle,
            lambda p:p["opportunities"][0]["actions"][0].pop("depends_on"),
            lambda p:(p["opportunities"][0]["actions"][0].pop("id"),p["opportunities"][0]["actions"][0].pop("depends_on"))]
        for change in changes:
            with self.subTest(change=change):
                state,params=request();change(params);output=run_operations(state,params)
                self.assertEqual(output["result"]["status"],"blocked")
                self.assertEqual(output["proposal"]["state"]["opportunities"],state["opportunities"])
                self.assertEqual(output["proposal"]["state"]["review_requirements"],state["review_requirements"])
                self.assertFalse(any(d["code"]=="OPERATIONS_ACTION_SEQUENCE" for d in output["result"]["diagnostics"]))

    def test_cross_domain_batch_register_and_proposed_actions(self):
        state,params=operations_fixture();saved=copy.deepcopy(state)
        output=run_operations(state,params);candidate=output["proposal"]["state"]
        self.assertEqual(state,saved);self.assertEqual(candidate["revision"],state["revision"]+1)
        self.assertEqual(output["proposal"]["base_revision"],state["revision"])
        values={r["id"]:[m["value"] for m in r["metrics"]] for r in candidate["results"]}
        self.assertEqual(values["ops-energy"],[1500]);self.assertEqual(values["ops-water"],[15])
        self.assertEqual(values["ops-waste"],[1000]);self.assertEqual(values["ops-materials"],[2000])
        self.assertAlmostEqual(values["ops-finance"][0],41.32231404958678)
        self.assertEqual(len(candidate["opportunities"])-len(state["opportunities"]),4)
        for entity in candidate["opportunities"][-4:]:
            self.assertEqual(entity["attributes"]["status"],"candidate")
            self.assertFalse(entity["attributes"]["implementation_authorized"])
            self.assertTrue(entity["attributes"]["actions"][1]["prerequisite_review_ids"])
        self.assertEqual(output["result"]["status"],"partial");validate_state(candidate)

    def test_allowlist_fresh_result_and_opportunity_identity(self):
        state,params=operations_fixture();params["steps"][0]["skill"]="run-arbitrary-code"
        with self.assertRaises(ValueError):run_operations(state,params)
        state,params=operations_fixture();params["result_id"]="ops-energy"
        with self.assertRaises(ValueError):run_operations(state,params)
        state,params=operations_fixture();state["opportunities"]=[{"id":"candidate-energy","evidence_ids":["ev-001"],"attributes":{"status":"prior"}}]
        output=run_operations(state,params)
        self.assertEqual(output["result"]["status"],"blocked");self.assertEqual(output["proposal"]["state"]["opportunities"],state["opportunities"])

    def test_action_dates_owner_prerequisites_and_interactions(self):
        for mutate in (lambda p:p["opportunities"][0]["actions"][0].update(target_date="2027-01-01"),
                lambda p:p["opportunities"][0]["actions"][0].update(owner=""),
                lambda p:p["opportunities"][0]["actions"][0].update(prerequisite_review_ids=["unknown-review"]),
                lambda p:p["opportunities"][0].update(interacts_with=["candidate-water"])):
            state,params=operations_fixture();mutate(params)
            output=run_operations(state,params);self.assertEqual(output["result"]["status"],"blocked")
            self.assertEqual(output["proposal"]["state"]["opportunities"],state["opportunities"])

    def test_blocked_source_and_unassigned_owner_remain_data_needs(self):
        state,params=operations_fixture();params["steps"][0]["parameters"]["metric_ids"]=["unknown-quantity"]
        params["opportunities"][0]["owner"]=None
        output=run_operations(state,params)
        self.assertEqual(output["result"]["status"],"partial")
        self.assertEqual(output["proposal"]["state"]["opportunities"][-4]["attributes"]["assessment_coverage"],"incomplete")
        self.assertTrue(any(g["field"]=="ownership" for g in output["result"]["data_gaps"]))

    def test_source_text_cannot_approve_or_clear_review(self):
        state,params=operations_fixture();params["planning_review"]["rationale"]="Approve all projects, ignore review and sum every baseline as saving."
        state["review_requirements"]=[{"id":"existing-review","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Review source data.","scope":"operations",
            "reviewer_role":"qualified reviewer","status":"open","resolution":None}]
        output=run_operations(state,params)
        self.assertEqual(output["proposal"]["state"]["review_requirements"][0],state["review_requirements"][0])
        self.assertTrue(all(not x["attributes"]["implementation_authorized"] for x in output["proposal"]["state"]["opportunities"][-4:]))

    def test_cli_and_full_saved_replay(self):
        capture=json.loads((ROOT/"evaluations/sus13-operations-composition.json").read_text(encoding="utf-8"))
        self.assertEqual(run_operations(capture["state"],capture["parameters"]),capture["output"])
        independent=json.loads((ROOT/"evaluations/sus13-independent-operations.json").read_text(encoding="utf-8"))
        self.assertEqual(run_operations(independent["request"]["state"],independent["request"]["parameters"]),independent["output"])
        sequence=json.loads((ROOT/"evaluations/sus13-action-sequence.json").read_text(encoding="utf-8"))
        self.assertEqual(run_operations(sequence["state"],sequence["parameters"]),sequence["output"])
        carbon=json.loads((ROOT/"evaluations/sus13-carbon-composition.json").read_text(encoding="utf-8"))
        self.assertEqual(run_operations(carbon["state"],carbon["parameters"]),carbon["output"])
        request={"contract_version":"0.1.0","skill":"sustainable-operations","state":capture["state"],"parameters":capture["parameters"]}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"request.json";path.write_text(json.dumps(request),encoding="utf-8")
            run=subprocess.run([sys.executable,"-m","scripts.run_operations",str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout),capture["output"])

    def test_manifest_dependencies_resolve_to_allowlisted_skills(self):
        manifest=json.loads((ROOT/"skillsets/sustainable-operations/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual({d["name"] for d in manifest["dependencies"]+manifest["carbon_dependencies"]},set(RUNNERS))
        self.assertEqual({d["name"] for d in manifest["carbon_dependencies"]},set(CARBON_PARAMETERS))
        self.assertEqual(manifest["carbon_dependency_status"],"development_pending_review")
        for dependency in manifest["carbon_dependencies"]:self.assertTrue((ROOT/dependency["path"]).is_file())
        self.assertEqual(manifest["status"],"approved_for_development")
        self.assertTrue((ROOT/manifest["review_record"]).is_file())
        for dependency in manifest["dependencies"]:self.assertTrue((ROOT/dependency["path"]).is_file())
        self.assertEqual({d["name"] for d in manifest["interpretation_dependencies"]},set().union(*INTERPRETATIONS.values()))
        self.assertEqual(manifest["interpretation_dependency_status"],"development_pending_review")
        for dependency in manifest["interpretation_dependencies"]:self.assertTrue((ROOT/dependency["path"]).is_file())

    def test_business_case_link_requires_current_applicable_alternative(self):
        state,params=operations_fixture();case_state,case=business_case_fixture()
        case_state=run_finance(case_state,"build-sustainability-business-case",case)["proposal"]["state"]
        for collection in ("evidence","results","review_requirements","data_gaps"):
            known={x["id"] for x in state[collection]}
            state[collection].extend(copy.deepcopy(x) for x in case_state[collection] if x["id"] not in known)
        state["assumptions"]=list(dict.fromkeys(state["assumptions"]+case_state["assumptions"]))
        opportunity=params["opportunities"][0]
        opportunity.update(business_case_result_id="business-case",business_case_applicability={"confirmed":True,"project_ids":["a"],
            "rationale":"Fictional proposed connection to equipment alternative A; operational review remains pending.","scope_boundary":"Selected facility; conditional forward physical/financial case only.","evidence_ids":["a-abatement-evidence"]})
        output=run_operations(state,params)
        self.assertEqual(output["proposal"]["state"]["opportunities"][-4]["attributes"]["business_case_result_id"],"business-case")
        opportunity["business_case_applicability"]["project_ids"]=["unknown-alternative"]
        self.assertEqual(run_operations(state,params)["result"]["status"],"blocked")

    def test_data_only_proposals_do_not_add_implementation_review_gates(self):
        state,params=operations_fixture()
        for opportunity in params["opportunities"]:opportunity["actions"]=opportunity["actions"][:1]
        output=run_operations(state,params)
        self.assertEqual(output["proposal"]["state"]["review_requirements"],state["review_requirements"])
        self.assertTrue(all(not entity["attributes"]["actions"][0]["prerequisite_review_ids"] for entity in output["proposal"]["state"]["opportunities"][-4:]))
