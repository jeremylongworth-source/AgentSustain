import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record
from tests.test_strategy_stakeholders import stakeholder_fixture


def materiality_fixture():
    state, mapping = stakeholder_fixture()
    state = run_strategy(state, 'map-stakeholders', mapping)['proposal']['state']
    review = copy.deepcopy(mapping['mapping_review'])
    review.update(context='Selected plant scheduling impacts on people.', identification_method='Read fictional sourced impact records, not management popularity.',
        coverage_limitations='Only selected plant and two source fragments; no complete issue universe.', model_evidence_fit='reviewed_supporting',
        model_fit_rationale='Fictional method appendix supplies separate impact thresholds appropriate for this scoped screen.')
    anchors = [{'rank':1,'label':'Lower','description':'Fictional low qualitative extent.'},{'rank':2,'label':'Higher','description':'Fictional high qualitative extent.'}]
    model = {'id':'impact-method','version':'fixture-1','evidence_ids':['manager-note'],'rule':'separate_impact_thresholds',
        'anchors':{k:copy.deepcopy(anchors) for k in ('severity','likelihood','scale','scope')},
        'thresholds':{'negative_actual_severity':2,'negative_potential_high_severity':2,'negative_potential_severity':1,
            'negative_potential_likelihood':2,'human_rights_severity':2,'positive_scale':2,'positive_scope':2,'positive_likelihood':2}}
    impact = {'id':'schedule-harm','topic_id':'work-scheduling','description':'Fictional risk of serious scheduling-related worker harm.',
        'direction':'negative','status':'potential','human_rights':True,'relationship':'caused','affected_context':'Selected fictional plant workers',
        'evidence_ids':['worker-note'],'evidence_fit':'reviewed_supporting','source_fragment':'Fictional risk note appendix paragraph 1',
        'observed_date':'2025-09-01','scale':'Serious individual effect in fictional scenario','scope':'Selected workers, extent uncertain',
        'irremediability':'Potential lasting harm needs specialist confirmation','severity_rank':2,'likelihood_rank':1,'scale_rank':None,'scope_rank':None,
        'assessment_rationale':'Fictional reviewer maps supplied harm descriptors to higher severity; low occurrence is not harm mitigation.',
        'follow_up':{'owner':'Fictional impact lead','target_date':'2026-12-01','purpose':'Review actual impact evidence, affected workers and method fitness.'}}
    return state, {'topics':[{'id':'work-scheduling','name':'Work scheduling','context':'Effects on people, not savings','evidence_ids':['worker-note']}],
        'impacts':[impact],'significance_model':model,'stakeholder_result_id':mapping['result_id'],'materiality_review':review,'result_id':'material-issues'}


class MaterialityTests(unittest.TestCase):
    def execute(self,p,state=None): return run_strategy(state or materiality_fixture()[0],'identify-material-sustainability-issues',p)

    def test_severe_low_likelihood_rights_candidate_preserves_state(self):
        state,p=materiality_fixture(); before=copy.deepcopy(state); out=self.execute(p,state); r=record(out,'MATERIAL_ISSUE_CANDIDATES')
        self.assertTrue(r['impacts'][0]['significance_threshold_met']); self.assertEqual(r['topic_candidates'][0]['candidate_status'],'proposed_significant')
        self.assertFalse(r['materiality_approved']); self.assertIsNone(r['final_material_topics']); self.assertIsNone(r['financial_materiality'])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,before); validate_state(out['proposal']['state'])
        for item in before['review_requirements']: self.assertIn(item,out['result']['review_requirements'])
        for item in before['data_gaps']: self.assertIn(item,out['result']['data_gaps'])
        self.assertEqual(out['proposal']['state']['evidence'],before['evidence'])
        self.assertFalse(r['stakeholder_map']['stakeholder_importance_ranking'])

    def test_unknowns_proxies_dates_and_no_absence_inference(self):
        for key,value in [('evidence_fit','proxy'),('evidence_fit','irrelevant'),('evidence_ids',[]),('observed_date',None),('observed_date','2024-09-01'),('status','unknown'),('severity_rank',None)]:
            with self.subTest(key=key):
                _,p=materiality_fixture(); p['impacts'][0][key]=value; r=record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES')
                self.assertIsNone(r['impacts'][0]['significance_threshold_met']); self.assertEqual(r['topic_candidates'][0]['candidate_status'],'investigation_required')

    def test_positive_does_not_net_negative(self):
        _,p=materiality_fixture(); benefit=copy.deepcopy(p['impacts'][0]); benefit.update(id='benefit',direction='positive',status='actual',human_rights=False,
            severity_rank=None,likelihood_rank=None,scale_rank=2,scope_rank=2,description='Fictional benefit distinct from harm.')
        p['impacts'].append(benefit); r=record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES')
        self.assertEqual(r['topic_candidates'][0]['significant_impact_ids'],['schedule-harm','benefit']); self.assertFalse(r['positive_negative_netting'])

    def test_actual_and_potential_negative_rules(self):
        _,p=materiality_fixture(); p['impacts'][0].update(status='actual',likelihood_rank=None,severity_rank=1)
        self.assertFalse(record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES')['impacts'][0]['significance_threshold_met'])
        p['impacts'][0].update(status='potential',human_rights=False,severity_rank=1,likelihood_rank=2)
        self.assertTrue(record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES')['impacts'][0]['significance_threshold_met'])
        p['impacts'][0]['likelihood_rank']=None
        self.assertIsNone(record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES')['impacts'][0]['significance_threshold_met'])
        p['impacts'][0]['severity_rank']=2
        r=record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES'); self.assertTrue(r['impacts'][0]['significance_threshold_met'])

    def test_empty_impact_topic_remains_investigation_and_followups_unsent(self):
        _,p=materiality_fixture(); p['impacts']=[]; p['stakeholder_result_id']=None
        r=record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES'); self.assertEqual(r['topic_candidates'][0]['candidate_status'],'investigation_required')
        _,p=materiality_fixture(); p['impacts'][0]['follow_up']['target_date']='2026-02-01'
        self.assertEqual(record(self.execute(p),'MATERIAL_ISSUE_CANDIDATES')['impacts'][0]['follow_up_status'],'overdue_unverified')
        _,p=materiality_fixture(); p['topics'].append({'id':'other-issue','name':'Other issue','context':'Uninvestigated fictional activity','evidence_ids':[]})
        out=self.execute(p); r=record(out,'MATERIAL_ISSUE_CANDIDATES')
        self.assertEqual(r['topic_candidates'][1]['candidate_status'],'investigation_required')
        self.assertTrue(any('issue-specific perspective' in g['reason'] for g in out['result']['data_gaps']))

    def test_stakeholder_change_and_scope_mismatch_block(self):
        state,p=materiality_fixture(); state['evidence'][-1]['source']['title']='Changed source'
        self.assertEqual(self.execute(p,state)['result']['status'],'blocked')
        _,p=materiality_fixture(); p['materiality_review']['scope']='Other plant'
        self.assertEqual(self.execute(p)['result']['status'],'blocked')

    def test_invalid_model_impact_and_authority_block(self):
        mutations=[lambda p:p['materiality_review'].update(model_evidence_fit='unverified'),lambda p:p['significance_model'].update(evidence_ids=[]),
            lambda p:p['significance_model']['thresholds'].update(human_rights_severity=True),lambda p:p['impacts'][0].update(observed_date='2026-02-01'),
            lambda p:p['impacts'][0].update(topic_id='missing'),lambda p:p['impacts'][0].update(evidence_ids=['missing']),
            lambda p:p['impacts'][0].update(status='actual'),lambda p:p['impacts'][0].update(scale_rank=2),
            lambda p:p['impacts'][0]['follow_up'].update(owner=''),lambda p:p['impacts'].append(copy.deepcopy(p['impacts'][0]))]
        for mutation in mutations:
            _,p=materiality_fixture(); mutation(p); self.assertEqual(self.execute(p)['result']['status'],'blocked')

    def test_saved_capture_replay(self):
        capture=json.loads((ROOT/'evaluations/sus15-materiality-workflow.json').read_text(encoding='utf-8')); req=capture['request']
        self.assertEqual(run_strategy(req['state'],req['skill'],req['parameters']),capture['output'])
