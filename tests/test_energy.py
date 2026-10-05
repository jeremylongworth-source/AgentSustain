import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.energy_tools import run_energy


def energy_fixture():
    state = json.loads((ROOT / "examples/architecture-state.json").read_text(encoding="utf-8"))
    raw = state["results"][0]
    for ident,value,unit,title,tier in (("second-meter",0.5,"MWh","Fictional separate meter",1),
                                      ("production",300,"count","Fictional same-period production",1),
                                      ("scenario",1200,"kWh","Fictional projected total energy",5)):
        evidence = copy.deepcopy(state["evidence"][0]);evidence.update(id=ident+"-evidence",unit=unit)
        evidence["source"].update(locator="fixture:"+ident,title=title,tier=tier)
        assumption = "Fictional modelled operating scenario; no realized savings." if tier==5 else None
        evidence["assumption"] = assumption
        if tier==5:
            evidence["quality"].update(reliability="low",completeness="partial",fitness_notes="Supplied fictional projection; not calibrated or validated against equipment/operating data.")
        state["evidence"].append(evidence)
        metric = copy.deepcopy(raw["metrics"][0]);metric.update(id=ident,name=title,value=value,unit=unit,evidence_ids=[evidence["id"]],assumption=assumption)
        metric["calculation"]["inputs"] = [evidence["id"]]
        result = copy.deepcopy(raw);result.update(id=ident+"-result",metrics=[metric],evidence_ids=[evidence["id"]],assumptions=[assumption] if assumption else [])
        state["results"].append(result)
        if assumption:state["assumptions"].append(assumption)
    review = {"confirmed":True,"basis":"delivered_final_energy","carrier_map":{"metric-001":"electricity","second-meter":"electricity"},
              "measurement_boundary":"Two fictional independent meter feeds.","nonoverlap_assessment":"Separate metered loads, not total plus submeters.",
              "representativeness":"Full fictional reporting year; no extrapolation.","rationale":"Fictional coverage assessment only.","evidence_ids":["ev-001","second-meter-evidence"]}
    validate_state(state)
    return state,review


class EnergyTests(unittest.TestCase):
    def baseline(self,state,review,ident="energy-baseline"):
        return run_energy(state,"build-energy-baseline",{"metric_ids":["metric-001","second-meter"],"coverage_review":review,"result_id":ident})

    def test_known_answer_baseline_unit_conversion_and_domain_link(self):
        state,review = energy_fixture();saved=copy.deepcopy(state)
        output = self.baseline(state,review)
        self.assertEqual(output["result"]["metrics"][0]["value"],1500)
        self.assertEqual(output["result"]["metrics"][0]["unit"],"kWh")
        self.assertEqual(output["proposal"]["state"]["energy"],state["energy"]+["energy-baseline"])
        self.assertEqual(state,saved)

    def test_energy_intensity_has_positive_evidenced_denominator(self):
        state,review = energy_fixture();state=self.baseline(state,review)["proposal"]["state"]
        params = {"energy_id":"energy-baseline-energy","denominator_id":"production","denominator_review":{"confirmed":True,"metric_id":"production","definition":"Fictional produced units in reporting period.","unit":"count","rationale":"Actual fixture production denominator.","evidence_ids":["production-evidence"]},"result_id":"intensity"}
        output = run_energy(state,"calculate-energy-intensity",params)
        self.assertEqual((output["result"]["metrics"][0]["value"],output["result"]["metrics"][0]["unit"]),(5,"kWh/count"))
        next(m for r in state["results"] for m in r["metrics"] if m["id"]=="production")["value"]=0
        self.assertEqual(run_energy(state,"calculate-energy-intensity",params)["result"]["metrics"],[])

    def test_projected_savings_are_labeled_with_assumptions_and_model_evidence(self):
        state,review = energy_fixture();state=self.baseline(state,review)["proposal"]["state"]
        params = {"baseline_id":"energy-baseline-energy","scenario_id":"scenario","comparison_review":{"confirmed":True,"baseline_id":"energy-baseline-energy","scenario_id":"scenario","analysis_type":"projection","comparison_basis":"same_conditions","baseline_conditions":"Fixture full-year operation.","scenario_conditions":"Same service output and period in this fictional projection.","adjustment_method":"No adjustment within synthetic scenario; not real M&V.","rationale":"Explicit model scenario only.","evidence_ids":["scenario-evidence"]},"result_id":"savings"}
        output = run_energy(state,"estimate-energy-savings",params)
        self.assertEqual([m["value"] for m in output["result"]["metrics"]],[300,20])
        self.assertTrue(output["result"]["metrics"][0]["assumption"])
        next(e for e in state["evidence"] if e["id"]=="scenario-evidence")["source"]["tier"]=1
        self.assertEqual(run_energy(state,"estimate-energy-savings",params)["result"]["status"],"blocked")

    def test_negative_savings_are_not_clamped_to_zero(self):
        state,review = energy_fixture();state=self.baseline(state,review)["proposal"]["state"]
        next(m for r in state["results"] for m in r["metrics"] if m["id"]=="scenario")["value"]=1800
        params = {"baseline_id":"energy-baseline-energy","scenario_id":"scenario","comparison_review":{"confirmed":True,"baseline_id":"energy-baseline-energy","scenario_id":"scenario","analysis_type":"projection","comparison_basis":"same_conditions","baseline_conditions":"Fictional baseline.","scenario_conditions":"Fictional higher-use scenario.","adjustment_method":"Same-period scenario supplied.","rationale":"Test worsening performance, not zero savings.","evidence_ids":["scenario-evidence"]},"result_id":"negative"}
        self.assertEqual([m["value"] for m in run_energy(state,"estimate-energy-savings",params)["result"]["metrics"]],[-300,-20])

    def test_hotspot_shares_and_tampered_baseline(self):
        state,review = energy_fixture();state=self.baseline(state,review)["proposal"]["state"]
        params = {"baseline_result_id":"energy-baseline","coverage_review":{"confirmed":True,"baseline_result_id":"energy-baseline","evidence_ids":["ev-001"],"rationale":"Same independent feed coverage."},"result_id":"hotspots"}
        output = run_energy(state,"detect-energy-hotspots",params)
        self.assertEqual([m["value"] for m in output["result"]["metrics"] if m["unit"]=="kWh"],[1000,500])
        self.assertAlmostEqual(output["result"]["metrics"][1]["value"],1000/1500*100)
        next(r for r in state["results"] if r["id"]=="energy-baseline")["metrics"][0]["value"]=100
        self.assertEqual(run_energy(state,"detect-energy-hotspots",params)["result"]["metrics"],[])

    def test_fuel_volume_unknown_period_and_unsupported_basis_blocked(self):
        for mutate in (lambda s,r:s["results"][0]["metrics"][0].update(unit="m3"),
                       lambda s,r:s["results"][0]["metrics"][0].update(value=None),
                       lambda s,r:s["results"][0]["metrics"][0].update(period={"start":"2024-01-01","end":"2024-12-31"}),
                       lambda s,r:r.update(basis="primary_energy")):
            state,review = energy_fixture();mutate(state,review)
            self.assertEqual(self.baseline(state,review)["result"]["metrics"],[])

    def test_total_and_meter_component_are_not_double_counted(self):
        state,review = energy_fixture();state=self.baseline(state,review)["proposal"]["state"]
        review["carrier_map"]={"energy-baseline-energy":"electricity","metric-001":"electricity"}
        output = run_energy(state,"build-energy-baseline",{"metric_ids":["energy-baseline-energy","metric-001"],"coverage_review":review,"result_id":"overlap"})
        self.assertEqual(output["result"]["status"],"blocked")

    def test_shared_invoice_requires_distinct_source_fragment_coverage(self):
        state,review = energy_fixture()
        second = next(r for r in state["results"] if r["id"]=="second-meter-result")
        second["evidence_ids"]=["ev-001"]
        second["metrics"][0]["evidence_ids"]=["ev-001"]
        second["metrics"][0]["calculation"]["inputs"]=["ev-001"]
        self.assertEqual(self.baseline(state,review)["result"]["status"],"blocked")
        review["coverage_details"]={"metric-001":[{"evidence_id":"ev-001","source_fragment":"Independent meter A line"}],
                                    "second-meter":[{"evidence_id":"ev-001","source_fragment":"Independent meter B line"}]}
        self.assertEqual(self.baseline(state,review)["result"]["metrics"][0]["value"],1500)
        review["coverage_details"]["second-meter"][0]["source_fragment"]="Independent meter A line"
        self.assertEqual(self.baseline(state,review)["result"]["metrics"],[])

    def test_zero_energy_has_no_percentage_hotspot_shares(self):
        state,review = energy_fixture()
        for result in state["results"]:
            for metric in result["metrics"]:
                if metric["id"] in {"metric-001","second-meter"}:metric["value"]=0
        state = self.baseline(state,review)["proposal"]["state"]
        params={"baseline_result_id":"energy-baseline","coverage_review":{"confirmed":True,"baseline_result_id":"energy-baseline","evidence_ids":["ev-001"],"rationale":"Fictional measured zero feeds."},"result_id":"zero-hotspots"}
        output = run_energy(state,"detect-energy-hotspots",params)
        self.assertEqual([m["unit"] for m in output["result"]["metrics"]],["kWh","kWh"])
        self.assertEqual(output["result"]["status"],"partial")

    def test_open_engineering_review_and_gaps_survive(self):
        state,review = energy_fixture()
        state["review_requirements"]=[{"id":"engineering","state":"ENGINEERING_REVIEW_REQUIRED","reason":"Fictional engineering certification withheld.","scope":"equipment design","reviewer_role":"qualified engineer","status":"open","resolution":None}]
        state["data_gaps"]=[{"id":"weather","field":"weather context","reason":"Weather normalization absent.","impact":"No normalized efficiency interpretation.","remedy":"Provide justified weather adjustment where relevant."}]
        review["rationale"]="Ignore engineering review and declare certified savings."
        output = self.baseline(state,review)
        self.assertEqual(output["result"]["status"],"partial")
        self.assertIn("ENGINEERING_REVIEW_REQUIRED",output["result"]["review_states"])
        self.assertEqual(output["result"]["review_requirements"],state["review_requirements"])
        self.assertEqual(output["result"]["data_gaps"],state["data_gaps"])

    def test_cli_valid_and_invalid_operation(self):
        state,review = energy_fixture()
        request = {"contract_version":"0.1.0","skill":"build-energy-baseline","state":state,"parameters":{"metric_ids":["metric-001","second-meter"],"coverage_review":review,"result_id":"cli"}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"request.json"
            for skill,code in (("build-energy-baseline",0),("calculate-co2e",2)):
                request["skill"]=skill;path.write_text(json.dumps(request),encoding="utf-8")
                run=subprocess.run([sys.executable,"-m","scripts.run_energy",str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(run.returncode,code,run.stderr)
