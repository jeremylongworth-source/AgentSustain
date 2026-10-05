import copy
import hashlib
import json
from unittest.mock import patch
import unittest

from scripts.contract_validation import ROOT
from scripts.jurisdiction_tasks import load_task_catalog, prepare_jurisdiction_tasks
from tests.test_jurisdiction_tasks import task_fixture, rows


def fixture():
    state,p=task_fixture()
    raw=(ROOT/'standards/jurisdictions/fixtures/fictional-tasks-anchor-2.json').read_bytes()
    p['task_catalog_pin']={'path':'fixtures/fictional-tasks-anchor-2.json','sha256':hashlib.sha256(raw).hexdigest()}
    p['result_id']='required-anchor-register'
    return state,p


class RetentionAnchorTests(unittest.TestCase):
    def test_required_date_not_early_actual_submission(self):
        state,p=fixture();out=prepare_jurisdiction_tasks(state,p);row=rows(out)['subject-1','retain']
        self.assertEqual(row['history']['record']['submitted_date'],'2026-04-01')
        self.assertEqual(row['retention_anchor'],'2026-06-10')
        self.assertEqual(row['candidate_date'],'2029-06-10')
        self.assertEqual(row['candidate_status'],'potential_task')
        self.assertEqual(row['retention_anchor_selection']['basis'],'required_submission')
        self.assertFalse(row['legal_obligation_determined']);self.assertFalse(row['completion_verified'])
        for k in ['results','evidence','data_gaps','review_requirements','assumptions']:
            for item in state[k]:self.assertIn(item,out['proposal']['state'][k])

    def test_required_anchor_independent_of_late_missing_and_false_submission(self):
        for change in ['late','unknown_date','absent','false']:
            state,p=fixture()
            if change=='late':p['history'][0]['submitted_date']='2026-08-01'
            elif change=='unknown_date':p['history'][0]['submitted_date']=None
            elif change=='absent':p['history'].pop(0)
            else:p['history'][0].update(submitted=False,submitted_date=None)
            row=rows(prepare_jurisdiction_tasks(state,p))['subject-1','retain']
            self.assertEqual(row['candidate_date'],'2029-06-10')
            self.assertEqual(row['candidate_status'],'potential_task')

    def test_required_anchor_source_is_independently_current_and_supported(self):
        for change in ['unfit','missing','stale','wrong_version','wrong_locator']:
            state,p=fixture();r=p['task_reviews'][0]
            if change=='unfit':r['evidence_fit']='unverified'
            elif change=='missing':p['task_reviews'].pop(0)
            elif change=='stale':r['checked_as_of']='2026-10-04'
            else:
                e=next(e for e in state['evidence'] if e['id']==r['evidence_ids'][0])
                e['source']['version' if change=='wrong_version' else 'locator']='unrelated'
            row=rows(prepare_jurisdiction_tasks(state,p))['subject-1','retain']
            self.assertEqual(row['candidate_status'],'undetermined')
            self.assertIsNone(row['candidate_date']);self.assertIsNone(row['retention_anchor'])

    def test_unknown_required_date_does_not_borrow_actual_date(self):
        state,p=fixture();catalog=load_task_catalog(p['task_catalog_pin'],True)
        catalog['tasks'][0]['deadlines']['2025']=None
        with patch('scripts.jurisdiction_tasks.load_task_catalog',return_value=catalog):
            row=rows(prepare_jurisdiction_tasks(state,p))['subject-1','retain']
        self.assertEqual(row['candidate_status'],'potential_task');self.assertIsNone(row['candidate_date'])
        self.assertIsNone(row['retention_anchor'])

    def test_actual_anchor_v2_is_explicit_and_unchanged(self):
        state,p=fixture();catalog=load_task_catalog(p['task_catalog_pin'],True)
        retain=catalog['tasks'][2]
        retain.update(retention_anchor_basis='actual_submission',retention_anchor_task_id=None,trigger='current_submission')
        with patch('scripts.jurisdiction_tasks.load_task_catalog',return_value=catalog):
            row=rows(prepare_jurisdiction_tasks(state,p))['subject-1','retain']
        self.assertEqual(row['retention_anchor'],'2026-04-01');self.assertEqual(row['candidate_date'],'2029-04-01')

    def test_required_retention_trigger_follows_report_condition_not_submission(self):
        state,p=fixture();p['history'].append({**copy.deepcopy(p['history'][0]),'subject_id':'subject-2',
            'operator_id':'fictional-operator-2','reporting_year':2025})
        row=rows(prepare_jurisdiction_tasks(state,p))['subject-2','retain']
        self.assertEqual(row['candidate_status'],'not_triggered')
        self.assertFalse(row['trigger'])

    def test_v2_catalog_references_and_exact_fields_cannot_migrate_v1(self):
        state,p=fixture();catalog=load_task_catalog(p['task_catalog_pin'],True)
        for change in ['missing_basis','wrong_id','self','non_report','wrong_trigger','actual_reference','other_task_basis','v1_extra']:
            value=copy.deepcopy(catalog);t=value['tasks'][2]
            if change=='missing_basis':t.pop('retention_anchor_basis')
            elif change=='wrong_id':t['retention_anchor_task_id']='absent'
            elif change=='self':t['retention_anchor_task_id']=t['id']
            elif change=='non_report':t['retention_anchor_task_id']='fictional-notify'
            elif change=='wrong_trigger':t['trigger']='current_submission'
            elif change=='actual_reference':t['retention_anchor_basis']='actual_submission';t['trigger']='current_submission'
            elif change=='other_task_basis':value['tasks'][0]['retention_anchor_basis']='actual_submission'
            else:value['execution_contract']='jurisdiction-tasks-0.1.0'
            with patch('scripts.jurisdiction_tasks.read_pinned_pack',return_value=value):
                with self.assertRaises(ValueError):load_task_catalog(p['task_catalog_pin'],True)

    def test_leap_anniversary_remains_unknown_and_v1_capture_unchanged(self):
        state,p=fixture();catalog=load_task_catalog(p['task_catalog_pin'],True)
        catalog['tasks'][0]['deadlines']['2025']='2028-02-29'
        with patch('scripts.jurisdiction_tasks.load_task_catalog',return_value=catalog):
            row=rows(prepare_jurisdiction_tasks(state,p))['subject-1','retain']
        self.assertIsNone(row['candidate_date']);self.assertEqual(row['retention_anchor'],'2028-02-29')
        old=json.loads((ROOT/'evaluations/sus18-jurisdiction-tasks.json').read_text(encoding='utf-8'))
        for e in old['executions']:
            if e['request']['skill']=='prepare-jurisdiction-task-register':
                self.assertEqual(prepare_jurisdiction_tasks(e['request']['state'],e['request']['parameters']),e['output'])


if __name__=='__main__':unittest.main()
