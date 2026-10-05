"""Rerun scope 3 and inventory composition with explicit fictional source facts."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.scope3_accounting import classify_scope3, calculate_category
from scripts.ghg_inventory import build_inventory


class SUS08WorkflowTests(unittest.TestCase):
    def test_helper_and_cli_workflow_reproduce_partial_inventory(self):
        capture = json.loads((ROOT / "evaluations/sus08-composed-workflow.json").read_text(encoding="utf-8"))
        state = copy.deepcopy(capture["initial_state"])
        operations = {"classify-scope-3-emissions":classify_scope3,"calculate-co2e":calculate_result,
                      "calculate-scope-3-category":calculate_category,"build-ghg-inventory":build_inventory}
        for step in capture["steps"]:
            output = operations[step["skill"]](state,**step["parameters"])
            self.assertEqual(output["result"],step["result"])
            self.assertEqual(output["proposal"]["reason"],step["proposal_reason"])
            self.assertEqual(output["result"]["status"],"partial")
            self.assertIn("PROFESSIONAL_REVIEW_REQUIRED",output["result"]["review_states"])
            if step["skill"] in {"calculate-scope-3-category","build-ghg-inventory"}:
                request = {"contract_version":"0.1.0","skill":step["skill"],"state":state,"parameters":step["parameters"]}
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)/"request.json"
                    path.write_text(json.dumps(request),encoding="utf-8")
                    run = subprocess.run([sys.executable,"-m","scripts.run_scope3",str(path)],cwd=ROOT,capture_output=True,text=True)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(json.loads(run.stdout),output)
            state = output["proposal"]["state"]
            validate_state(state)
        self.assertEqual(state,capture["final_state"])
        self.assertEqual(state["results"][-1]["metrics"][0]["value"],725)
        selection = json.loads(next(d["message"] for d in state["results"][-1]["diagnostics"] if d["code"]=="INVENTORY_SELECTION"))
        self.assertEqual([entry["value_kg_CO2e"] for entry in selection["included"]],[25,500,200])
        self.assertTrue(any(d["code"]=="INCOMPLETE_CATEGORY_COVERAGE" for d in state["results"][-1]["diagnostics"]))
        self.assertEqual(state["review_requirements"],capture["initial_state"]["review_requirements"])
