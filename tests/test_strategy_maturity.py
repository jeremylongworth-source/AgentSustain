import copy
import json
import unittest

from scripts.contract_validation import validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record
from tests.test_strategy_stakeholders import stakeholder_fixture


def maturity_fixture():
    state, unused = stakeholder_fixture()
    review = copy.deepcopy(unused['mapping_review'])
    review.update(selection_basis='Selected plant practice, not organization performance.', limitations='Two fictional records, not independent audit.',
        rubric_evidence_fit='reviewed_supporting', rubric_fit_rationale='Fictional memo appendix supplies the selected plant practice rubric; its criteria fit this selected governance assessment.')
    rubric = {'id': 'plant-practice', 'version': 'fixture-1', 'name': 'Fictional plant management practice rubric', 'evidence_ids': ['manager-note'],
        'dimensions': [{'id': 'measurement', 'name': 'Measurement governance', 'levels': [
            {'id': 'defined', 'label': 'Defined responsibilities', 'criteria': [{'id': 'owner', 'requirement': 'A named measurement owner is documented.'}]},
            {'id': 'operating', 'label': 'Operating review', 'criteria': [{'id': 'review', 'requirement': 'Dated source records demonstrate completed measurement review.'}]}]}]}
    obs = {'criterion_id': 'owner', 'status': 'demonstrated', 'evidence_ids': ['manager-note'], 'source_fragment': 'Fictional owner assignment, paragraph 1',
        'evidence_fit': 'reviewed_supporting', 'observed_date': '2025-09-01', 'rationale': 'Named owner in selected plant record; not evidence of operating reviews.',
        'follow_up': {'owner': 'Fictional practice lead', 'target_date': '2026-12-01', 'purpose': 'Collect completed review records.'}}
    planned = copy.deepcopy(obs); planned.update(criterion_id='review',status='planned',source_fragment='Fictional review schedule, paragraph 2',rationale='Schedule only; completion unknown.')
    return state, {'rubric': rubric, 'observations': [obs, planned], 'assessment_review': review, 'result_id': 'maturity'}


class MaturityTests(unittest.TestCase):
    def execute(self, params, state=None):
        return run_strategy(state or maturity_fixture()[0], 'assess-sustainability-maturity', params)

    def test_cumulative_profile_and_preservation(self):
        state, params = maturity_fixture(); before = copy.deepcopy(state)
        out = self.execute(params,state); report = record(out,'MATURITY_ASSESSMENT')
        self.assertEqual(report['dimension_profiles'][0]['highest_supported_level'],'defined')
        self.assertFalse(report['dimension_profiles'][0]['levels'][1]['demonstrated'])
        for key in ('overall_score','organization_maturity','environmental_performance','certification'): self.assertIsNone(report[key])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,before)
        for r in before['review_requirements']: self.assertIn(r,out['result']['review_requirements'])
        for g in before['data_gaps']: self.assertIn(g,out['result']['data_gaps'])
        self.assertEqual(out['proposal']['state']['evidence'],before['evidence'])
        validate_state(out['proposal']['state'])

    def test_high_level_cannot_bypass_unknown_lower(self):
        _, p = maturity_fixture(); p['observations'][0]['status']='unknown'; p['observations'][1]['status']='demonstrated'
        r=record(self.execute(p),'MATURITY_ASSESSMENT')
        self.assertIsNone(r['dimension_profiles'][0]['highest_supported_level'])
        self.assertTrue(r['criteria']['review']['criterion_demonstrated'])

    def test_source_fit_dates_and_conflicts(self):
        for field,value in [('observed_date',None),('observed_date','2024-09-01'),('evidence_fit','unverified'),('evidence_fit','irrelevant'),('status','conflicting'),('status','not_demonstrated'),('evidence_ids',[])]:
            with self.subTest(field=field,value=value):
                _,p=maturity_fixture(); p['observations'][0][field]=value
                r=record(self.execute(p),'MATURITY_ASSESSMENT')
                self.assertFalse(r['criteria']['owner']['criterion_demonstrated']); self.assertIsNone(r['dimension_profiles'][0]['highest_supported_level'])

    def test_missing_observation_unknown_and_overdue_unsent(self):
        _,p=maturity_fixture(); p['observations']=p['observations'][:1]; p['observations'][0]['follow_up']['target_date']='2026-02-01'
        r=record(self.execute(p),'MATURITY_ASSESSMENT')
        self.assertIsNone(r['criteria']['review']['observation']); self.assertEqual(r['criteria']['owner']['follow_up_status'],'overdue_unverified')
        self.assertFalse(r['implementation_authorized'])

    def test_complete_selected_profile_is_not_certification(self):
        _,p=maturity_fixture(); p['observations'][1]['status']='demonstrated'; p['assessment_review']['coverage_complete']=True
        out=self.execute(p); r=record(out,'MATURITY_ASSESSMENT')
        self.assertEqual(r['dimension_profiles'][0]['highest_supported_level'],'operating'); self.assertFalse(r['coverage_verified'])
        self.assertTrue(any(x['id']=='maturity-maturity-review' and x['status']=='open' for x in out['result']['review_requirements']))

    def test_invalid_records_block(self):
        mutations=[lambda p:p['rubric'].update(evidence_ids=[]),lambda p:p['observations'][0].update(observed_date='2026-01-01'),
            lambda p:p['observations'][0].update(evidence_ids=['missing']),lambda p:p['observations'][0]['follow_up'].update(owner=''),
            lambda p:p['observations'].append(copy.deepcopy(p['observations'][0])),lambda p:p['rubric']['dimensions'][0]['levels'][1]['criteria'][0].update(id='owner'),
            lambda p:p['assessment_review'].update(boundary_id='other'),
            lambda p:p['assessment_review'].update(rubric_evidence_fit='unverified'),
            lambda p:p['assessment_review'].update(rubric_fit_rationale='')]
        for mutation in mutations:
            _,p=maturity_fixture(); mutation(p); self.assertEqual(self.execute(p)['result']['status'],'blocked')

    def test_saved_capture_replays(self):
        from scripts.contract_validation import ROOT
        path=ROOT/'evaluations/sus15-maturity-workflow.json'
        capture=json.loads(path.read_text()); req=capture['request']
        self.assertEqual(run_strategy(req['state'],req['skill'],req['parameters']),capture['output'])
