"""Rerun the saved composed helper workflow; source facts remain author supplied."""
import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.scope_accounting import compose_scope
from scripts.scope_classification import classify_sources


class SUS07WorkflowTests(unittest.TestCase):
    def test_composed_workflow_reruns_with_exact_state_and_results(self):
        capture = json.loads((ROOT / "evaluations/sus07-composed-workflow.json").read_text(encoding="utf-8"))
        state = copy.deepcopy(capture["initial_state"])
        represented = set()
        totals = {}
        for step in capture["steps"]:
            request = step["request"]
            skill = request["skill"]
            represented.add(skill)
            if skill.startswith("classify-"):
                output = classify_sources(state, skill, **request["parameters"])
            elif skill == "calculate-co2e":
                output = calculate_result(state, **request["parameters"])
            else:
                output = compose_scope(state, skill, **request["parameters"])
                totals[skill] = output["result"]["metrics"][0]["value"]
            self.assertEqual(output["result"], step["result"])
            self.assertEqual(output["proposal"]["reason"], step["proposal_reason"])
            self.assertEqual(output["proposal"]["state"]["ghg"], step["domain_result_ids"])
            self.assertEqual(output["result"]["status"], "partial")
            self.assertIn("PROFESSIONAL_REVIEW_REQUIRED", output["result"]["review_states"])
            self.assertTrue(output["result"]["data_gaps"])
            state = output["proposal"]["state"]
            validate_state(state)
        self.assertTrue({"classify-scope-1-emissions", "classify-scope-2-emissions", "calculate-scope-1",
                         "calculate-location-based-scope-2", "calculate-market-based-scope-2"} <= represented)
        self.assertEqual(totals, {"calculate-scope-1": 25, "calculate-location-based-scope-2": 500, "calculate-market-based-scope-2": 500})
        self.assertEqual(state, capture["final_state"])
        self.assertEqual(state["ghg"]["scope_2"], ["workflow-scope2-location", "workflow-scope2-market"])
        self.assertEqual(len(state["review_requirements"]), 1)
        self.assertEqual(state["review_requirements"][0]["status"], "open")
