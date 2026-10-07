import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT
from scripts.workflow_example import run_workflow_example


def bundle():
    return json.loads((ROOT/'examples/food-manufacturer-forward-test-input.json').read_text())


class WorkflowExampleTests(unittest.TestCase):
    def test_reconstruction_matches_recorded_manager_and_preserves_inputs(self):
        request=bundle();original=copy.deepcopy(request)
        output=run_workflow_example(request)
        recorded=json.loads((ROOT/'evaluations/sus23-food-manager-preliminary.json').read_text())['output']
        self.assertEqual(output['manager_output'],recorded)
        self.assertEqual(request,original)
        self.assertEqual(len(output['preparation_result_ids']),5)
        self.assertEqual(output['execution_status'],'partial')
        self.assertFalse(output['independent_acceptance'])
        self.assertFalse(output['public_v1_readiness'])

    def test_actual_cli_missing_factor_preserves_physical_and_review_branches(self):
        path=ROOT/'examples/food-manufacturer-forward-test-input.json';before=path.read_bytes()
        process=subprocess.run([sys.executable,'-m','scripts.run_workflow_example',str(path),
                                '--omit-factor','synthetic-factor'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        output=json.loads(process.stdout);manager=output['manager_output']
        results={r['id']:r for r in manager['proposal']['state']['results']}
        self.assertEqual(results['operations-inventory']['status'],'blocked')
        self.assertEqual(results['operations-inventory']['metrics'],[])
        self.assertEqual(results['framework-map']['status'],'blocked')
        self.assertEqual(results['ops-energy']['metrics'][0]['value'],430000)
        self.assertEqual(results['ops-finance']['metrics'][0]['value'],0)
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in manager['result']['diagnostics']))
        self.assertTrue(all(r['state'].endswith('_REQUIRED') and r['resolution'] is None
                            for r in manager['proposal']['state']['review_requirements']))
        self.assertFalse(output['publication_authorized'])
        self.assertEqual(path.read_bytes(),before)

    def test_invalid_profile_or_omission_cannot_claim_execution(self):
        changes=[('version','future'),('external_action_authorized',True),
                 ('sequential_fuel_parameters',[])]
        for key,value in changes:
            request=bundle();request[key]=value
            with self.assertRaises(ValueError):run_workflow_example(request)
        for omitted in [('not-supplied',),('synthetic-factor','synthetic-factor'),(' ',)]:
            with self.assertRaises(ValueError):run_workflow_example(bundle(),omitted)

    def test_cli_oversize_input_is_refused_without_echoing_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'too-large.json'
            path.write_bytes(b'private sentinel'+b' '*1048576)
            process=subprocess.run([sys.executable,'-m','scripts.run_workflow_example',str(path)],
                                    cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(process.returncode,2)
            self.assertEqual(json.loads(process.stdout)['error'],'INVALID_WORKFLOW_EXAMPLE')
            self.assertNotIn('sentinel',process.stdout+process.stderr)
