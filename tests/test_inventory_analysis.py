import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.ghg_inventory import build_inventory
from scripts.inventory_analysis import compare_inventories, identify_hotspots, _periods_comparable
from scripts.scope_accounting import compose_scope
from scripts.state_proposal import propose
from test_scope_accounting import scope_fixture, market_review


def comparison_fixture(before=1000, after=800, prior_year=2025, current_year=2026):
    state, sources, components, coverage = scope_fixture()
    period = {"start":f"{prior_year}-01-01","end":f"{prior_year}-12-31"}
    state["reporting_period"] = period
    for evidence in state["evidence"]:
        evidence["period"] = copy.deepcopy(period)
    for result in state["results"]:
        for metric in result["metrics"]:
            metric["period"] = copy.deepcopy(period)
    state["results"][0]["metrics"][0]["value"] = before
    state["results"][1]["metrics"][0]["value"] = before * 0.5
    state = compose_scope(state,"calculate-location-based-scope-2",sources,components,coverage,"prior-energy",True)["proposal"]["state"]
    screening = [{"category":i,"status":"not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional screening for this electricity-only example."} for i in range(1,16)]
    review = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional distinct electricity account; direct emissions missing, not zero.","gwp_basis":coverage["gwp_basis"]}
    state = build_inventory(state,None,"prior-energy",[],screening,review,"prior-inventory",True)["proposal"]["state"]
    prior = copy.deepcopy(state)
    state["reporting_period"] = {"start":f"{current_year}-01-01","end":f"{current_year}-12-31"}
    evidence = copy.deepcopy(state["evidence"][0]);evidence.update(id="current-evidence",period=state["reporting_period"])
    raw = copy.deepcopy(state["results"][0]);raw.update(id="current-activity-result",assumptions=state["assumptions"],data_gaps=state["data_gaps"],status="partial",review_states=["ANALYTICAL","EVIDENCE_INCOMPLETE"],evidence_ids=["current-evidence"])
    raw["metrics"][0].update(id="current-activity",value=after,period=state["reporting_period"],evidence_ids=["current-evidence"])
    raw["metrics"][0]["calculation"]["inputs"] = ["current-evidence"]
    state = propose(state,raw,"Add current fictional activity with preserved historical lineage",[evidence])["state"]
    policy = copy.deepcopy(components[0]["policy"]);policy["source_review"]["activity_id"]="current-activity"
    state = calculate_result(state,"current-activity","synthetic-factor",policy,"current-co2e",True)["proposal"]["state"]
    source = copy.deepcopy(sources[0]);source.update(activity_id="current-activity",evidence_ids=["current-evidence"])
    component = copy.deepcopy(components[0]);component.update(metric_id="current-co2e-metric",policy=policy)
    current_coverage = copy.deepcopy(coverage);current_coverage["evidence_ids"]=["current-evidence"]
    state = compose_scope(state,"calculate-location-based-scope-2",[source],[component],current_coverage,"current-energy",True)["proposal"]["state"]
    state = build_inventory(state,None,"current-energy",[],screening,review,"current-inventory",True)["proposal"]["state"]
    comparison = {"confirmed":True,"prior_inventory_id":"prior-inventory","current_inventory_id":"current-inventory",
                  "evidence_ids":["ev-001","current-evidence"],"reviewer":"Fictional reviewer","rationale":"Synthetic comparison of matching selected electricity accounts only.",
                  "boundary_changes_assessment":"No fixture boundary change.","coverage_changes_assessment":"Same single-source coverage; both inventories partial.",
                  "factor_changes_assessment":"Same synthetic intensity; no real factor applicability claimed.","restatement_assessment":"No fixture restatement needed; not a verified reduction claim."}
    return state,prior,comparison


class InventoryAnalysisTests(unittest.TestCase):
    def test_comparison_known_answer_and_prior_lineage_preserved(self):
        state,prior,review = comparison_fixture()
        saved = copy.deepcopy(state)
        output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"comparison",True)
        self.assertEqual([m["value"] for m in output["result"]["metrics"]],[-100,-20])
        self.assertEqual(output["result"]["status"],"partial")
        self.assertEqual(state,saved)
        validate_state(output["proposal"]["state"])
        self.assertEqual(output["result"]["metrics"][0]["calculation"]["inputs"],["prior-inventory-metric","current-inventory-metric"])

    def test_leap_year_monthly_and_unequal_partial_periods(self):
        state,prior,review = comparison_fixture(prior_year=2024,current_year=2025)
        output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"leap",True)
        self.assertEqual([m["value"] for m in output["result"]["metrics"]],[-100,-20])
        self.assertTrue(_periods_comparable({"start":"2025-01-01","end":"2025-01-31"},{"start":"2025-02-01","end":"2025-02-28"}))
        self.assertFalse(_periods_comparable({"start":"2025-01-02","end":"2025-01-31"},{"start":"2025-02-02","end":"2025-02-28"}))

    def test_zero_prior_has_absolute_change_without_percentage(self):
        state,prior,review = comparison_fixture(before=0,after=200)
        output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"zero",True)
        self.assertEqual([m["value"] for m in output["result"]["metrics"]],[100])
        self.assertIn("PERCENTAGE_DENOMINATOR_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})

    def test_missing_review_history_or_changed_boundary_blocks_comparison(self):
        for change in ("review","history","boundary","overlap"):
            state,prior,review = comparison_fixture(current_year=2025 if change=="overlap" else 2026)
            if change=="review": review["factor_changes_assessment"]=""
            if change=="history": next(r for r in state["results"] if r["id"]=="prior-inventory")["metrics"][0]["value"]=1
            if change=="boundary": state["organizational_boundary"]["exclusions"].append("new excluded operation")
            output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"blocked",True)
            self.assertEqual(output["result"]["status"],"blocked")
            self.assertEqual(output["result"]["metrics"],[])

    def test_changed_category_screening_and_source_coverage_blocked(self):
        state,prior,review = comparison_fixture()
        inventory = next(r for r in state["results"] if r["id"]=="current-inventory")
        diag = next(d for d in inventory["diagnostics"] if d["code"]=="INVENTORY_SELECTION")
        data = json.loads(diag["message"]);data["category_screening"][0]["status"]="unknown";diag["message"]=json.dumps(data)
        output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"coverage-change",True)
        self.assertEqual(output["result"]["status"],"blocked")
        state,prior,review = comparison_fixture()
        energy = next(r for r in state["results"] if r["id"]=="current-energy")
        diag = next(d for d in energy["diagnostics"] if d["code"]=="SCOPE_METHOD")
        record = json.loads(diag["message"])
        record["sources"][0]["gases"] = ["CO2"]
        record["components"][0]["gases"] = ["CO2"]
        record["components"][0]["policy"]["gas_coverage"] = ["CO2"]
        record["accepted"][0]["gases"] = ["CO2"]
        diag["message"] = json.dumps(record)
        output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"gas-coverage-change",True)
        self.assertEqual(output["result"]["status"],"blocked")

    def test_scope2_method_change_requires_restated_comparable_account(self):
        state,prior,review = comparison_fixture()
        energy = next(r for r in state["results"] if r["id"]=="current-energy")
        record = json.loads(next(d["message"] for d in energy["diagnostics"] if d["code"]=="SCOPE_METHOD"))
        component = record["components"][0]
        component["policy"]["scope_basis"] = "certificate"
        component["market_review"] = market_review(state)
        component["market_review"]["matched_quantity"] = 800
        state = compose_scope(state,"calculate-market-based-scope-2",record["sources"],[component],record["coverage_review"],"current-market",True)["proposal"]["state"]
        inventory = next(r for r in state["results"] if r["id"]=="current-inventory")
        selection = json.loads(next(d["message"] for d in inventory["diagnostics"] if d["code"]=="INVENTORY_SELECTION"))
        state = build_inventory(state,None,"current-market",[],selection["category_screening"],selection["coverage_review"],"market-inventory",True)["proposal"]["state"]
        review["current_inventory_id"] = "market-inventory"
        output = compare_inventories(state,prior,"prior-inventory","market-inventory",review,"method-change",True)
        self.assertEqual(output["result"]["metrics"],[])

    def test_source_hotspot_allocation_applied_once(self):
        state,sources,components,coverage = scope_fixture()
        state["organizational_boundary"]["approach"] = "equity share (fixture only)"
        sources[0].update(boundary_approach=state["organizational_boundary"]["approach"],allocation_fraction=0.4)
        state = compose_scope(state,"calculate-location-based-scope-2",sources,components,coverage,"allocated-energy",True)["proposal"]["state"]
        screening = [{"category":i,"status":"not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional screening."} for i in range(1,16)]
        review = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional equity allocation.","gwp_basis":coverage["gwp_basis"]}
        state = build_inventory(state,None,"allocated-energy",[],screening,review,"allocated-inventory",True)["proposal"]["state"]
        review.update(inventory_id="allocated-inventory",level="source")
        output = identify_hotspots(state,"allocated-inventory","source",review,"allocated-hotspot",True)
        self.assertEqual([m["value"] for m in output["result"]["metrics"]],[200,100])

    def test_blocked_comparison_retains_prior_open_review(self):
        state,prior,review = comparison_fixture()
        obligation = {"id":"prior-professional-review","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Fictional scoped boundary question.",
                      "scope":"prior inventory boundary","reviewer_role":"inventory specialist","status":"open","resolution":None}
        prior["review_requirements"].append(obligation)
        review["confirmed"] = False
        output = compare_inventories(state,prior,"prior-inventory","current-inventory",review,"blocked-review",True)
        self.assertEqual(output["result"]["status"],"blocked")
        self.assertIn(obligation,output["result"]["review_requirements"])
        self.assertIn("PROFESSIONAL_REVIEW_REQUIRED",output["result"]["review_states"])

    def test_hotspots_all_levels_have_explicit_denominator_and_partial_state(self):
        state = json.loads((ROOT / "evaluations/sus08-composed-workflow.json").read_text())["final_state"]
        for level,expected in (("scope",[500,200,25]),("category",[200]),("source",[500,200,25])):
            review = {"confirmed":True,"inventory_id":"workflow-inventory","level":level,"evidence_ids":["material-evidence"],"rationale":"Fictional distinct contribution coverage at this level."}
            output = identify_hotspots(state,"workflow-inventory",level,review,"hotspots",True)
            self.assertEqual(output["result"]["status"],"partial")
            record = json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"]=="EMISSION_HOTSPOTS"))
            self.assertEqual([entry["value_kg_CO2e"] for entry in record["ranking"]],expected)
            self.assertEqual(record["denominator_kg_CO2e"],725)
            self.assertAlmostEqual(record["ranking"][0]["share_percent"],expected[0]/725*100)
            self.assertEqual(output["result"]["review_requirements"],state["review_requirements"])

    def test_hotspot_zero_denominator_and_tampered_inventory(self):
        state,_,_ = comparison_fixture(before=0,after=0)
        review = {"confirmed":True,"inventory_id":"current-inventory","level":"scope","evidence_ids":["current-evidence"],"rationale":"Fictional zero activity with eligible fixture factor."}
        output = identify_hotspots(state,"current-inventory","scope",review,"zero-hotspots",True)
        self.assertEqual(len(output["result"]["metrics"]),1)
        self.assertEqual(output["result"]["metrics"][0]["value"],0)
        next(r for r in state["results"] if r["id"]=="current-inventory")["metrics"][0]["value"]=10
        self.assertEqual(identify_hotspots(state,"current-inventory","scope",review,"tampered",True)["result"]["metrics"],[])

    def test_fixture_mode_and_level_confirmation_required(self):
        state,prior,review = comparison_fixture()
        self.assertEqual(compare_inventories(state,prior,"prior-inventory","current-inventory",review,"ordinary")["result"]["metrics"],[])
        coverage = {"confirmed":True,"inventory_id":"current-inventory","level":"category","evidence_ids":["current-evidence"],"rationale":"Fictional assessment."}
        self.assertEqual(identify_hotspots(state,"current-inventory","scope",coverage,"wrong-level",True)["result"]["metrics"],[])

    def test_common_cli_comparison_and_hotspots(self):
        state,prior,review = comparison_fixture()
        operations = [("compare-ghg-inventories",{"prior_state":prior,"prior_inventory_id":"prior-inventory","current_inventory_id":"current-inventory","comparability_review":review,"result_id":"cli-compare","fixture_mode":True}),
                      ("identify-emission-hotspots",{"inventory_id":"current-inventory","level":"scope","coverage_review":{"confirmed":True,"inventory_id":"current-inventory","level":"scope","evidence_ids":["current-evidence"],"rationale":"Fictional nonoverlap."},"result_id":"cli-hotspots","fixture_mode":True})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"request.json"
            for skill,params in operations:
                path.write_text(json.dumps({"contract_version":"0.1.0","skill":skill,"state":state,"parameters":params}),encoding="utf-8")
                run = subprocess.run([sys.executable,"-m","scripts.run_scope3",str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertTrue(json.loads(run.stdout)["result"]["metrics"])

    def test_saved_analysis_cases_rerun(self):
        capture = json.loads((ROOT / "evaluations/sus08-analysis-workflow.json").read_text(encoding="utf-8"))
        operations = {"compare-ghg-inventories":compare_inventories,"identify-emission-hotspots":identify_hotspots}
        for case in capture["cases"]:
            request = case["request"]
            output = operations[request["skill"]](request["state"],**request["parameters"])
            self.assertEqual(output["result"],case["result"])
            self.assertEqual(output["proposal"]["reason"],case["proposal_reason"])
            validate_state(output["proposal"]["state"])
