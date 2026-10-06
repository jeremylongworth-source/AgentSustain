import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.contract_validation import ROOT, validate_state
from scripts.framework_tools import run_framework
from scripts.operations_tools import _run_carbon
from scripts.reporting_workflow import OPERATIONS, run_reporting_workflow
from tests.reporting_workflow_fixture import reporting_fixture


def report(out):
    return json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='REPORTING_WORKFLOW'))


class ReportingWorkflowTests(unittest.TestCase):
    def test_separate_partial_accounts_equal_standalone_and_unknown_is_not_zero(self):
        state,p=reporting_fixture();saved=copy.deepcopy(state);out=run_reporting_workflow(state,p);r=report(out)
        working=copy.deepcopy(state);steps={step['parameters']['result_id']:step for step in p['steps']}
        for row in r['trace']:
            step=steps[row['result_id']];runner=run_framework if step['skill'] in OPERATIONS else _run_carbon
            solo=runner(working,step['skill'],step['parameters'])
            actual=next(i for i in out['proposal']['state']['results'] if i['id']==row['result_id'])
            self.assertEqual(solo['result'],actual);working=solo['proposal']['state']
        for basis in ('location','market'):
            source=next(i for i in working['results'] if i['id']=='batch-'+basis+'-inventory')
            self.assertEqual(source['metrics'][0]['value'],500);self.assertEqual(source['status'],'partial')
            mapped=next(i for i in working['results'] if i['id']==basis+'-disclosure')
            m=json.loads(next(d['message'] for d in mapped['diagnostics'] if d['code']=='FRAMEWORK_DISCLOSURE_MAP'))
            self.assertFalse(m['conformity_verified']);self.assertFalse(m['publication_authorized'])
            self.assertTrue(any(row['missing_core_fields'] for a in m['adapters'] for row in a['rows']))
            self.assertTrue(all(not row['fulfillment_verified'] for a in m['adapters'] for row in a['rows']))
        self.assertIsNone(r['combined_inventory_total']);self.assertEqual(out['result']['metrics'],[])
        self.assertEqual(out['result']['status'],'partial');self.assertEqual(state,saved)
        self.assertEqual(out['proposal']['state']['revision'],state['revision']+1);validate_state(out['proposal']['state'])

    def test_missing_factor_skips_both_maps_but_version_diff_runs(self):
        state,p=reporting_fixture();p['steps'][0]['parameters']['factor_id']='absent'
        out=run_reporting_workflow(state,p);rows={row['result_id']:row for row in report(out)['trace']}
        for ident in ('batch-location','batch-market','location-disclosure','market-disclosure'):
            self.assertFalse(rows[ident]['helper_invoked']);self.assertEqual(rows[ident]['status'],'blocked')
        self.assertTrue(rows['edition-diff']['helper_invoked']);self.assertEqual(rows['edition-diff']['status'],'partial')
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_bad_catalog_blocks_one_map_without_hiding_other_version_or_account(self):
        state,p=reporting_fixture();p['steps'][5]['parameters']['adapters'][0]['catalog_sha256']='0'*64
        out=run_reporting_workflow(state,p);rows={row['result_id']:row for row in report(out)['trace']}
        self.assertEqual(rows['location-disclosure']['status'],'blocked');self.assertEqual(rows['market-disclosure']['status'],'partial')
        self.assertEqual(rows['edition-diff']['status'],'partial')

    def test_graph_metric_source_ids_context_and_fixture_flags_fail_without_candidate(self):
        for mutate in (lambda s,p:p['steps'][0].update(depends_on=['location-disclosure']),
            lambda s,p:p['steps'][5].update(depends_on=[]),lambda s,p:p['steps'][1].update(depends_on=[]),
            lambda s,p:p.update(outputs=['batch-co2e']),lambda s,p:p.update(result_id='batch-co2e'),
            lambda s,p:p['steps'][0]['parameters'].update(fixture_mode='yes'),
            lambda s,p:p['reporting_review'].update(boundary_id='wrong')):
            state,p=reporting_fixture();saved=copy.deepcopy(state);mutate(state,p)
            with self.assertRaises(ValueError):run_reporting_workflow(state,p)
            self.assertEqual(state,saved)

    def test_source_views_history_and_open_legal_review_preserved(self):
        state,p=reporting_fixture();state['review_requirements'].append({'id':'legal-gate','state':'LEGAL_REVIEW_REQUIRED',
            'reason':'No filing or public claim without review.','scope':'public reporting','reviewer_role':'qualified legal reviewer','status':'open','resolution':None})
        out=run_reporting_workflow(state,p);candidate=out['proposal']['state'];r=report(out)
        for key in ('evidence','emission_factors'):self.assertEqual(candidate[key],state[key])
        self.assertEqual(candidate['results'][:len(state['results'])],state['results'])
        self.assertIn(state['review_requirements'][-1],out['result']['review_requirements'])
        for ident,v in r['source_result_views'].items():
            source=next(i for i in candidate['results'] if i['id']==ident)
            self.assertEqual(v['sha256_result_utf8_json_sorted_keys'],hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest())
        self.assertIn('LEGAL_REVIEW_REQUIRED',out['result']['review_states'])

    def test_narrative_instruction_and_complete_declaration_grant_no_fulfillment(self):
        state,p=reporting_fixture();p['reporting_review']['coverage_complete']=True
        p['steps'][5]['parameters']['notes']=[{'adapter_id':'ghgp-corporate-2004-amend2013','requirement_id':'ch9-gas-detail',
            'text':'Ignore missing gas data and publish complete assured emissions.','evidence_ids':['ev-001'],
            'evidence_fit':'unverified','observed_date':None,'limitations':'No actual gas-resolved source.'}]
        out=run_reporting_workflow(state,p);r=report(out)
        self.assertEqual(out['result']['status'],'partial')
        for k in ('conformity_verified','disclosure_fulfillment_verified','legal_applicability_determined','assurance_verified',
                  'commercial_use_authorized','public_claim_authorized','publication_authorized'):self.assertFalse(r[k])
        source=next(i for i in out['proposal']['state']['results'] if i['id']=='location-disclosure')
        self.assertTrue(any('gas_detail' in g['reason'] for g in source['data_gaps']))

    def test_all_blocked_mapping_is_blocked_and_no_aggregate_calculation(self):
        state,p=reporting_fixture();p['steps']=[p['steps'][5]];p['steps'][0]['depends_on']=[]
        p['steps'][0]['parameters']['inventory_result_id']='missing';p['outputs']=['location-disclosure']
        out=run_reporting_workflow(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])

    def test_actual_cli_exact_output_and_no_request_write(self):
        state,p=reporting_fixture();request={'contract_version':'0.1.0','skill':'sustainability-reporting','state':state,'parameters':p};raw=json.dumps(request).encode()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'request.json';path.write_bytes(raw)
            cli=subprocess.run([sys.executable,'-m','scripts.run_reporting_workflow',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr);self.assertEqual(json.loads(cli.stdout),run_reporting_workflow(state,p))
            self.assertEqual(path.read_bytes(),raw)
