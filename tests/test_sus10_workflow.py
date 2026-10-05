import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.resource_tools import run_resources


class SUS10WorkflowTests(unittest.TestCase):
    def test_saved_mass_workflow_reproduces_known_answers_and_unknown_route(self):
        capture=json.loads((ROOT/"evaluations/sus10-mass-workflow.json").read_text(encoding="utf-8"))
        state=copy.deepcopy(capture["initial_state"])
        for step in capture["steps"]:
            output=run_resources(state,step["skill"],step["parameters"])
            self.assertEqual(output["result"],step["result"])
            self.assertEqual(output["proposal"]["reason"],step["proposal_reason"])
            state=output["proposal"]["state"];validate_state(state)
        self.assertEqual(state,capture["final_state"])
        results={s["skill"]:s["result"] for s in capture["steps"]}
        self.assertEqual(results["build-waste-baseline"]["metrics"][0]["value"],1000)
        self.assertEqual([m["value"] for m in results["calculate-diversion-rate"]["metrics"]],[600,60])
        self.assertEqual(results["calculate-material-intensity"]["metrics"][0]["value"],20)
        self.assertTrue(state["data_gaps"])
        self.assertEqual(results["calculate-diversion-rate"]["status"],"partial")
