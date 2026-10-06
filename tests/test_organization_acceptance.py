import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.business_ingestion import ingest_business_csv
from scripts.contract_validation import ROOT
from scripts.organization_acceptance import evaluate_organization_acceptance


def fixture():
    return (json.loads((ROOT/'examples/organization-acceptance.json').read_text()),
            json.loads((ROOT/'examples/organization-acceptance-oracle.json').read_text()))


class ClassifiedBusinessSourceTests(unittest.TestCase):
    def test_explicit_row_tiers_preserve_document_and_model_classifications(self):
        case,_=fixture();request=case['ingestion_request'];state=copy.deepcopy(request['state'])
        out=ingest_business_csv(state,request['parameters']);self.assertEqual(out['result']['status'],'partial')
        evidence={e['id']:e for e in out['proposal']['state']['evidence']}
        self.assertEqual(evidence['flow-1-evidence']['source']['tier'],5)
        self.assertEqual(evidence['ev-001']['source']['tier'],1)
        self.assertEqual(evidence['raw-business-document']['source']['tier'],1)
        report=json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='CSV_ROW_SOURCE'))
        self.assertEqual(report['execution_contract'],'business-csv-ingestion-0.2.0')
        self.assertFalse(report['record_source_tiers_authenticated']);self.assertEqual(state,request['state'])
        self.assertEqual(out['proposal']['state']['emission_factors'],state['emission_factors'])

    def test_bad_classification_rolls_back_entire_import(self):
        for change in ('missing','extra','boolean','out_of_range','blank_reviewer','observation_as_model'):
            case,_=fixture();r=case['ingestion_request'];c=r['parameters']['source_classification_review']
            if change=='missing':c['record_tiers'].pop('row-16')
            elif change=='extra':c['record_tiers']['not-in-file']=1
            elif change=='boolean':c['record_tiers']['row-16']=True
            elif change=='out_of_range':c['record_tiers']['row-16']=6
            elif change=='blank_reviewer':c['reviewer_role']=' '
            else:c['record_tiers']['row-1']=5
            out=ingest_business_csv(r['state'],r['parameters'])
            self.assertEqual(out['result']['status'],'blocked',change);self.assertEqual(out['result']['metrics'],[])
            self.assertEqual(out['proposal']['state']['evidence'],r['state']['evidence'])
            self.assertEqual(out['proposal']['state']['assumptions'],r['state']['assumptions'])

    def test_each_shipped_fictional_csv_cannot_be_declared_ordinary(self):
        for path in (ROOT/'data/inputs').glob('fictional-*.csv'):
            case,_=fixture();r=case['ingestion_request'];p=r['parameters']
            p.pop('source_classification_review');p['fixture_mode']=False
            p['file_pin'].update(path='data/inputs/'+path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),synthetic=False)
            out=ingest_business_csv(r['state'],p)
            self.assertEqual(out['result']['status'],'blocked',path.name);self.assertEqual(out['result']['metrics'],[])

    def test_renamed_copy_and_registry_file_count_stay_bounded(self):
        case,_=fixture();r=case['ingestion_request'];raw=(ROOT/r['parameters']['file_pin']['path']).read_bytes()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inputs=root/'data/inputs';inputs.mkdir(parents=True)
            (inputs/'ordinary.csv').write_bytes(raw);(inputs/'fictional-second.csv').write_bytes(raw)
            p=r['parameters'];p.pop('source_classification_review');p['fixture_mode']=False
            p['file_pin'].update(path='data/inputs/ordinary.csv',synthetic=False)
            with patch('scripts.business_ingestion.ROOT',root),patch('scripts.business_ingestion.INPUT_ROOT',inputs):
                out=ingest_business_csv(r['state'],p)
                self.assertEqual(out['result']['status'],'blocked')
                for i in range(64):(inputs/('fictional-'+str(i)+'.csv')).write_bytes(b'')
                out=ingest_business_csv(r['state'],p)
                self.assertEqual(out['result']['status'],'blocked');self.assertIn('file count',out['result']['diagnostics'][0]['message'])


class OrganizationAcceptanceTests(unittest.TestCase):
    def test_separate_declared_oracle_and_all_22_workflow_custody_checks_pass(self):
        case,oracle=fixture();original=copy.deepcopy(case)
        out=evaluate_organization_acceptance(case,oracle)
        self.assertEqual(out['scenario_status'],'passed');self.assertEqual(len(out['checks']),22)
        self.assertTrue(all(c['passed'] for c in out['checks']));self.assertEqual(case,original)
        self.assertFalse(out['independent_organization_acceptance']);self.assertFalse(out['public_v1_readiness'])
        self.assertFalse(out['publication_authorized'])
        # The declared cash-flow oracle is a monetary comparison, not financial approval.
        self.assertEqual(next(r for r in out['manager']['proposal']['state']['results'] if r['id']=='ops-finance')['metrics'][0]['value'],0)

    def test_missing_factors_withhold_inventory_and_keep_independent_physical_branches(self):
        case,oracle=fixture()
        for step in case['manager_parameters']['operations']['steps']:
            if step['skill']=='calculate-co2e':step['parameters']['factor_id']='absent-factor'
            if step['skill']=='calculate-location-based-scope-2':
                for component in step['parameters']['components']:component['factor_id']='absent-factor'
        out=evaluate_organization_acceptance(case,oracle);checks={c['id']:c for c in out['checks']}
        self.assertEqual(out['scenario_status'],'failed');self.assertFalse(checks['ORG-03']['passed'])
        self.assertTrue(checks['ORG-04']['passed']);self.assertTrue(checks['ORG-07']['passed']);self.assertTrue(checks['CUST-10']['passed'])
        self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['manager']['result']['diagnostics']])

    def test_unknown_water_source_is_not_zero_and_other_branches_survive(self):
        case,oracle=fixture();p=case['ingestion_request']['parameters'];path=ROOT/'data/inputs/fictional-acceptance-missing-water.csv'
        p['file_pin'].update(path='data/inputs/'+path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        out=evaluate_organization_acceptance(case,oracle)
        results={r['id']:r for r in out['manager']['proposal']['state']['results']}
        self.assertEqual(results['ops-water']['status'],'blocked');self.assertEqual(results['ops-water']['metrics'],[])
        self.assertEqual(results['ops-energy']['metrics'][0]['value'],3000)
        self.assertEqual(results['operations-inventory']['metrics'][0]['value'],1500)
        self.assertTrue(next(c['passed'] for c in out['checks'] if c['id']=='CUST-10'))

    def test_source_pin_mismatch_fails_before_manager_and_real_source_mode_is_refused(self):
        case,oracle=fixture();case['ingestion_request']['parameters']['file_pin']['sha256']='0'*64
        out=evaluate_organization_acceptance(case,oracle)
        self.assertEqual(out['scenario_status'],'failed');self.assertIsNone(out['manager'])
        self.assertEqual(out['ingestion']['result']['metrics'],[])
        case,oracle=fixture();case['ingestion_request']['parameters']['fixture_mode']=False
        with self.assertRaises(ValueError):evaluate_organization_acceptance(case,oracle)

    def test_actual_cli_matches_full_evaluation_and_does_not_write_inputs(self):
        case,oracle=fixture();paths=[ROOT/'examples/organization-acceptance.json',ROOT/'examples/organization-acceptance-oracle.json'];before=[p.read_bytes() for p in paths]
        cli=subprocess.run([sys.executable,'-m','scripts.run_organization_acceptance',*[str(p) for p in paths]],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(cli.returncode,0,cli.stderr)
        self.assertEqual(json.loads(cli.stdout),evaluate_organization_acceptance(case,oracle))
        self.assertEqual([p.read_bytes() for p in paths],before)
