import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result, factor_issues


def ghg_fixture():
    state = json.loads((ROOT / "examples/architecture-state.json").read_text(encoding="utf-8"))
    evidence = copy.deepcopy(state["evidence"][0])
    evidence.update(id="factor-evidence", unit="kg CO2e/kWh")
    evidence["source"].update(locator="fixture:factor", title="Synthetic emission-factor fixture", version="fixture-1")
    state["evidence"].append(evidence)
    factor = {"id": "synthetic-factor", "value": 0.5, "unit": "kg CO2e/kWh",
              "source": {"locator": "fixture:factor", "publisher": "Fictional fixture publisher", "version": "fixture-1", "accessed": "2026-10-04"},
              "geography": "CA-ON", "vintage_year": 2025,
              "method": {"name": "Synthetic CO2e calculation", "version": "fixture-1", "source": "fixture:method"},
              "gwp_basis": "Synthetic fixture basis", "evidence_ids": ["factor-evidence"], "status": "synthetic"}
    state["emission_factors"] = [factor]
    review = {"factor_id": factor["id"], "activity_id": "metric-001", "source_locator": factor["source"]["locator"],
              "source_version": factor["source"]["version"], "confirmed_value": factor["value"], "confirmed_unit": factor["unit"],
              "evidence_ids": factor["evidence_ids"], "reviewer": "Fictional fixture reviewer", "coverage": "Fictional activity only",
              "rationale": "Synthetic factor supplied solely to test arithmetic and provenance, not for real use."}
    policy = {"geography": "CA-ON", "acceptable_vintages": [2025], "method": copy.deepcopy(factor["method"]),
              "gwp_basis": factor["gwp_basis"], "source_review": review}
    return state, policy


class GHGFoundationTests(unittest.TestCase):
    def test_common_request_cli_and_fixture_default(self):
        state, policy = ghg_fixture()
        request = {"contract_version": "0.1.0", "skill": "calculate-co2e", "state": state,
                   "parameters": {"activity_id": "metric-001", "factor_id": "synthetic-factor", "policy": policy,
                                  "result_id": "cli-result", "fixture_mode": True}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            for enabled in (True, False):
                request["parameters"]["fixture_mode"] = enabled
                path.write_text(json.dumps(request), encoding="utf-8")
                completed = subprocess.run([sys.executable, "-m", "scripts.run_ghg_calculation", str(path)],
                                           cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                output = json.loads(completed.stdout)
                if enabled:
                    self.assertEqual(output["result"]["metrics"][0]["value"], 500)
                else:
                    self.assertEqual(output["result"]["status"], "blocked")
                    self.assertEqual(output["result"]["metrics"], [])
            request["skill"] = "calculate-scope-1"
            path.write_text(json.dumps(request), encoding="utf-8")
            completed = subprocess.run([sys.executable, "-m", "scripts.run_ghg_calculation", str(path)], cwd=ROOT,
                                       capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(completed.stdout)["error"], "INVALID_REQUEST")

    def test_known_answer_synthetic_co2e_with_lineage(self):
        state, policy = ghg_fixture()
        saved = copy.deepcopy(state)
        output = calculate_result(state, "metric-001", "synthetic-factor", policy, "co2e-test", True)
        metric = output["result"]["metrics"][0]
        self.assertEqual((metric["value"], metric["unit"]), (500, "kg CO2e"))
        self.assertEqual(set(metric["evidence_ids"]), {"ev-001", "factor-evidence"})
        self.assertEqual(set(metric["calculation"]["inputs"]), {"metric-001", "factor-evidence"})
        self.assertIn("SYNTHETIC_FIXTURE", {item["code"] for item in output["result"]["diagnostics"]})
        self.assertEqual(state, saved)
        validate_state(output["proposal"]["state"])

    def test_no_factor_returns_required_without_numeric_output(self):
        state, policy = ghg_fixture()
        output = calculate_result(state, "metric-001", "missing-factor", policy, "blocked")
        self.assertEqual(output["result"]["status"], "blocked")
        self.assertEqual(output["result"]["metrics"], [])
        self.assertEqual(output["result"]["diagnostics"][0]["code"], "EMISSION_FACTOR_REQUIRED")
        self.assertIn("EVIDENCE_INCOMPLETE", output["result"]["review_states"])

    def test_synthetic_never_enabled_by_default_or_relabeling(self):
        state, policy = ghg_fixture()
        for status in ("synthetic", "reviewed", "candidate"):
            state["emission_factors"][0]["status"] = status
            output = calculate_result(state, "metric-001", "synthetic-factor", policy, "blocked-" + status)
            self.assertEqual(output["result"]["metrics"], [])
        with self.assertRaises(ValueError):
            calculate_result(state, "metric-001", "synthetic-factor", policy, "blocked", "false")

    def test_factor_metadata_is_required(self):
        state, policy = ghg_fixture()
        activity = state["results"][0]["metrics"][0]
        for field in ("source", "geography", "vintage_year", "unit", "method", "gwp_basis", "evidence_ids"):
            factor = copy.deepcopy(state["emission_factors"][0])
            del factor[field]
            with self.subTest(field=field):
                self.assertTrue(factor_issues(factor, activity, policy, True))

    def test_geography_vintage_method_and_gwp_mismatch(self):
        state, policy = ghg_fixture()
        for change in ({"geography": "US"}, {"acceptable_vintages": [2024]}, {"method": {"name": "other", "version": "1", "source": "fixture:other"}}, {"gwp_basis": "other"}):
            wrong = copy.deepcopy(policy)
            wrong.update(change)
            with self.subTest(change=change):
                result = calculate_result(state, "metric-001", "synthetic-factor", wrong, "blocked", True)["result"]
                self.assertEqual(result["metrics"], [])
                self.assertEqual(result["diagnostics"][0]["code"], "EMISSION_FACTOR_REQUIRED")

    def test_source_review_must_match_factor_and_activity(self):
        state, policy = ghg_fixture()
        for key, value in (("confirmed_value", 0.2), ("confirmed_value", True), ("activity_id", "other"), ("source_version", "old"), ("reviewer", ""), ("coverage", "")):
            wrong = copy.deepcopy(policy)
            wrong["source_review"][key] = value
            with self.subTest(key=key):
                result = calculate_result(state, "metric-001", "synthetic-factor", wrong, "blocked", True)["result"]
                self.assertEqual(result["metrics"], [])

    def test_incompatible_factor_units_and_gas_basis_block(self):
        state, policy = ghg_fixture()
        for unit in ("kg CO2e/L", "kg CH4/kWh", "kg CO2e/UNKNOWN_UNIT", "kg CO2e"):
            modified = copy.deepcopy(state)
            modified["emission_factors"][0]["unit"] = unit
            wrong = copy.deepcopy(policy)
            wrong["source_review"]["confirmed_unit"] = unit
            with self.subTest(unit=unit):
                self.assertEqual(calculate_result(modified, "metric-001", "synthetic-factor", wrong, "blocked", True)["result"]["metrics"], [])

    def test_activity_conversion_and_output_mass_scale(self):
        state, policy = ghg_fixture()
        activity = state["results"][0]["metrics"][0]
        activity.update(value=1, unit="MWh")
        output = calculate_result(state, "metric-001", "synthetic-factor", policy, "converted", True)
        self.assertEqual(output["result"]["metrics"][0]["value"], 500)
        state["emission_factors"][0].update(value=0.0005, unit="t CO2e/kWh")
        policy["source_review"].update(confirmed_value=0.0005, confirmed_unit="t CO2e/kWh")
        self.assertEqual(calculate_result(state, "metric-001", "synthetic-factor", policy, "converted-mass", True)["result"]["metrics"][0]["value"], 500)

    def test_unknown_negative_mixed_period_activity_blocks(self):
        state, policy = ghg_fixture()
        for change in ({"value": None}, {"value": -1}, {"period": {"start": "2024-01-01", "end": "2024-12-31"}}):
            modified = copy.deepcopy(state)
            modified["results"][0]["metrics"][0].update(change)
            with self.subTest(change=change):
                result = calculate_result(modified, "metric-001", "synthetic-factor", policy, "blocked", True)["result"]
                self.assertEqual(result["diagnostics"][0]["code"], "ACTIVITY_DATA_REQUIRED")
                self.assertEqual(result["metrics"], [])

    def test_review_states_and_existing_gaps_survive(self):
        state, policy = ghg_fixture()
        state["review_requirements"] = [{"id": "legal-review", "state": "LEGAL_REVIEW_REQUIRED", "reason": "Outstanding fictional obligation",
                                         "scope": "organization", "reviewer_role": "legal professional", "status": "open", "resolution": None}]
        state["data_gaps"] = [{"id": "coverage-gap", "field": "coverage", "reason": "Other source missing", "impact": "Inventory incomplete", "remedy": "Obtain missing source"}]
        output = calculate_result(state, "metric-001", "synthetic-factor", policy, "partial", True)
        self.assertEqual(output["result"]["status"], "partial")
        self.assertIn("LEGAL_REVIEW_REQUIRED", output["result"]["review_states"])
        self.assertEqual(output["proposal"]["state"]["review_requirements"], state["review_requirements"])
        self.assertEqual(output["result"]["data_gaps"], state["data_gaps"])


if __name__ == "__main__":
    unittest.main()
