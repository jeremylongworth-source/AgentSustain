import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.resource_tools import run_resources
from scripts.state_proposal import propose


class SUS10WorkflowTests(unittest.TestCase):
    def test_opportunity_example_preserves_unknown_treatment_and_unquantified_candidates(self):
        capture=json.loads((ROOT/"evaluations/sus10-opportunity-workflow.json").read_text(encoding="utf-8"))
        state=copy.deepcopy(capture["initial_state"])
        for step in capture["steps"]:
            if step["execution_type"]=="deterministic helper":
                output=run_resources(state,step["skill"],step["parameters"])
                self.assertEqual(output["result"],step["result"]);state=output["proposal"]["state"]
            else:state=propose(state,step["result"],step["proposal_reason"])["state"]
            validate_state(state)
        self.assertEqual(state,capture["final_state"])
        streams=json.loads(capture["steps"][0]["result"]["diagnostics"][0]["message"])["streams"]
        self.assertEqual((streams[2]["hazard"],streams[2]["route"]),("unknown","unknown"))
        self.assertTrue({"residue-treatment-gap","opportunity-quantification-gap"}<={g["id"] for g in state["data_gaps"]})
        self.assertTrue(all(not s["result"]["metrics"] for s in capture["steps"] if s["execution_type"]!="deterministic helper"))

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
