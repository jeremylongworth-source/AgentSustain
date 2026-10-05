"""Regression checks for saved author-led outputs, not fresh agent inference."""
import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.state_proposal import propose


class SUS06EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.capture = json.loads((ROOT / "evaluations/sus06-author-execution.json").read_text(encoding="utf-8"))

    def test_all_foundation_skills_and_proposals_preserve_review(self):
        state = copy.deepcopy(self.capture["initial_state"])
        expected = {path.parent.name for path in (ROOT / "skills/carbon").glob("*/SKILL.md")
                    if path.parent.name in {
                        "define-ghg-inventory-boundary", "identify-emission-sources", "select-emission-factor",
                        "validate-emission-factor", "calculate-co2e", "identify-ghg-data-gaps",
                        "estimate-missing-activity-data", "assess-ghg-data-quality"}}
        self.assertEqual({step["result"]["skill"] for step in self.capture["steps"]}, expected)
        for step in self.capture["steps"]:
            state = propose(state, step["result"], step["reason"])["state"]
            self.assertEqual(state["review_requirements"], self.capture["initial_state"]["review_requirements"])
        self.assertEqual(state, self.capture["final_state"])
        validate_state(state)

    def test_fixture_does_not_close_missing_records_or_enable_estimate(self):
        results = {step["result"]["skill"]: step["result"] for step in self.capture["steps"]}
        calculation = results["calculate-co2e"]
        self.assertEqual(calculation["status"], "partial")
        self.assertEqual(calculation["metrics"][0]["value"], 500)
        self.assertIn("SYNTHETIC_FIXTURE", {item["code"] for item in calculation["diagnostics"]})
        self.assertTrue({"lease-gap", "gas-gap", "refrigerant-gap", "real-factor-gap"}
                        <= {gap["id"] for gap in self.capture["final_state"]["data_gaps"]})
        for skill in ("select-emission-factor", "validate-emission-factor", "estimate-missing-activity-data"):
            self.assertEqual(results[skill]["status"], "blocked")
            self.assertEqual(results[skill]["metrics"], [])
