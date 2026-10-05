"""Rerun energy helpers; replay explicitly author-led reasoning proposals."""
import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.energy_tools import run_energy
from scripts.state_proposal import propose


class SUS09WorkflowTests(unittest.TestCase):
    def test_energy_workflow_preserves_conditional_projection_and_unresolved_context(self):
        capture = json.loads((ROOT / "evaluations/sus09-energy-workflow.json").read_text(encoding="utf-8"))
        state = copy.deepcopy(capture["initial_state"])
        expected_skills = {path.parent.name for path in (ROOT / "skills/energy").glob("*/SKILL.md")}
        self.assertEqual({step["skill"] for step in capture["steps"]},expected_skills)
        for step in capture["steps"]:
            if step["execution_type"]=="deterministic helper":
                output = run_energy(state,step["skill"],step["parameters"])
                self.assertEqual(output["result"],step["result"])
                self.assertEqual(output["proposal"]["reason"],step["proposal_reason"])
                state = output["proposal"]["state"]
            else:
                state = propose(state,step["result"],step["proposal_reason"])["state"]
            validate_state(state)
        self.assertEqual(state,capture["final_state"])
        results = {step["skill"]:step["result"] for step in capture["steps"]}
        self.assertEqual(results["build-energy-baseline"]["metrics"][0]["value"],1500)
        self.assertEqual(results["calculate-energy-intensity"]["metrics"][0]["value"],5)
        self.assertEqual([m["value"] for m in results["estimate-energy-savings"]["metrics"]],[300,20])
        self.assertTrue(results["estimate-energy-savings"]["metrics"][0]["assumption"])
        for skill in ("identify-efficiency-opportunities","prioritize-energy-projects"):
            self.assertEqual(results[skill]["status"],"blocked")
            self.assertEqual(results[skill]["metrics"],[])
        self.assertTrue({"energy-driver-gap","energy-mechanism-gap","energy-project-gap"} <= {g["id"] for g in state["data_gaps"]})
