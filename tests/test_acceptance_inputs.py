import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import ValidationError
from scripts.contract_validation import ROOT
from scripts.organization_acceptance import evaluate_organization_acceptance
from tests.test_organization_acceptance import fixture


class AcceptanceInputTests(unittest.TestCase):
    def reject_before_ingestion(self, case, oracle):
        with patch('scripts.organization_acceptance.ingest_business_csv') as parser:
            with self.assertRaises((ValueError, ValidationError, OverflowError)):
                evaluate_organization_acceptance(case, oracle)
            parser.assert_not_called()

    def test_infinite_nan_negative_boolean_and_widened_tolerance_rejected(self):
        for field in ('financial_absolute_tolerance','ratio_absolute_tolerance'):
            for value in (float('inf'),float('-inf'),float('nan'),-1,True,1,10**1000,'1e-9',None):
                case,oracle=fixture();oracle[field]=value
                self.reject_before_ingestion(case,oracle)

    def test_unknown_case_request_or_oracle_version_rejected(self):
        for version in ('case','request','oracle'):
            case,oracle=fixture()
            if version=='case':case['contract_version']='future'
            elif version=='request':case['ingestion_request']['contract_version']='future'
            else:oracle['oracle_version']='future'
            self.reject_before_ingestion(case,oracle)

    def test_missing_extra_and_malformed_input_fields_rejected(self):
        for change in ('case_extra','case_missing','oracle_extra','oracle_missing','manager_type','request_extra','authorship','basis'):
            case,oracle=fixture()
            if change=='case_extra':case['future_instruction']='publish'
            elif change=='case_missing':case.pop('contract_version')
            elif change=='oracle_extra':oracle['approval']=True
            elif change=='oracle_missing':oracle.pop('authorship')
            elif change=='manager_type':case['manager_parameters']=[]
            elif change=='request_extra':case['ingestion_request']['future_instruction']='publish'
            elif change=='authorship':oracle['authorship']=' '
            else:oracle['known_answer_basis']=[' ']
            self.reject_before_ingestion(case,oracle)

    def test_metric_roster_types_units_and_nonfinite_answers_rejected(self):
        for change in ('missing','extra','unit','boolean','nan','infinite','negative_physical','metric_extra'):
            case,oracle=fixture();metric=oracle['expected_metrics']['ops-water']
            if change=='missing':oracle['expected_metrics'].pop('ops-finance')
            elif change=='extra':oracle['expected_metrics']['invented']={'value':0,'unit':'CAD'}
            elif change=='unit':metric['unit']='L'
            elif change=='boolean':metric['value']=True
            elif change=='nan':metric['value']=float('nan')
            elif change=='infinite':metric['value']=float('inf')
            elif change=='negative_physical':metric['value']=-1
            else:metric['tolerance']=float('inf')
            self.reject_before_ingestion(case,oracle)

    def test_count_and_target_period_controls_reject_ambiguous_inputs(self):
        for change in ('count_bool','count_fraction','count_negative','count_unbounded','period_extra','period_reverse','period_noncanonical'):
            case,oracle=fixture()
            if change=='count_bool':oracle['expected_manager_stage_count']=True
            elif change=='count_fraction':oracle['expected_opportunity_count']=4.5
            elif change=='count_negative':oracle['expected_opportunity_count']=-1
            elif change=='count_unbounded':oracle['expected_opportunity_count']=101
            elif change=='period_extra':oracle['expected_target_period']['future_date']='2031-01-01'
            elif change=='period_reverse':oracle['expected_target_period'].update(start='2031-01-01')
            else:oracle['expected_target_period']['start']='20300101'
            self.reject_before_ingestion(case,oracle)

    def test_valid_incorrect_answer_fails_and_tighter_tolerance_can_pass(self):
        case,oracle=fixture();oracle['expected_metrics']['ops-finance']['value']=9999
        out=evaluate_organization_acceptance(case,oracle)
        self.assertEqual(out['scenario_status'],'failed')
        self.assertFalse(next(c['passed'] for c in out['checks'] if c['id']=='ORG-07'))
        case,oracle=fixture();oracle['financial_absolute_tolerance']=0;oracle['ratio_absolute_tolerance']=0
        self.assertEqual(evaluate_organization_acceptance(case,oracle)['scenario_status'],'passed')

    def test_actual_cli_invalid_oracle_returns_two_without_writing_inputs(self):
        case,oracle=fixture();oracle['financial_absolute_tolerance']=1
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'case.json';o=Path(d)/'oracle.json';raw=json.dumps(case).encode();answer=json.dumps(oracle).encode()
            p.write_bytes(raw);o.write_bytes(answer)
            cli=subprocess.run([sys.executable,'-m','scripts.run_organization_acceptance',str(p),str(o)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,2);self.assertEqual(json.loads(cli.stdout)['error'],'INVALID_ACCEPTANCE_INPUT')
            self.assertEqual(p.read_bytes(),raw);self.assertEqual(o.read_bytes(),answer)
