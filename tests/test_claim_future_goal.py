import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.claim_future_goal import assess_future_goal_claim
from scripts.claims_review import BASE
from scripts.contract_validation import ROOT,validate_state
from tests.test_claims_review import report,rows


def bind(state,p,name='fictional-future-goal',value=8,year_text='2030'):
    raw=(ROOT/'standards/claims/materials'/(name+'.json')).read_bytes();m=json.loads(raw);text=m['text'].splitlines()[1]
    e=next(e for e in state['evidence'] if e['id']=='future-claim-material');e['source'].update(locator='workspace:standards/claims/materials/'+name+'.json',version=m['version'])
    p['claim']['text']=text
    def span(part):
        start=m['text'].index(part);return {'start':start,'end':start+len(part)}
    p['material_pin']={'path':name+'.json','sha256':hashlib.sha256(raw).hexdigest()}
    p['material_selectors']={'claim_span':span(text),'qualification_spans':[{'text':q,'span':span(q)} for q in p['claim']['qualifications']],
        'quantity_spans':[{'criterion_id':'quantity','value_span':span(str(value)),'unit_span':span('kWh/count')}]}
    p['goal_review']['target_year_span']=span(year_text)
    next(c for c in p['criteria'] if c['id']=='quantity')['quantity']['expected_value']=value


def fixture():
    state=json.loads((ROOT/'evaluations/sus15-implementation-workflow.json').read_bytes())['output']['proposal']['state']
    e=copy.deepcopy(state['evidence'][0]);e.update(id='future-review-evidence',unit='1');e['source'].update(locator='fixture:future-goal-review',version='fictional-review-1');state['evidence'].append(e)
    m=copy.deepcopy(e);m.update(id='future-claim-material',period={'start':'2026-09-01','end':'2026-10-05'});state['evidence'].append(m)
    qualifier='Proposed target only; resource conditions are unmet and delivery and progress remain unverified.'
    claim={'id':'fictional-future-claim','text':'pending material selection','kind':'future_goal','subject_kind':'organization','subject_id':state['organization']['id'],
        'scope':'selected_sources','period':copy.deepcopy(state['reporting_period']),'boundary_id':state['organizational_boundary']['id'],'material_evidence_ids':[m['id']],
        'representation_dates':['2026-09-01'],'channel':'Fictional draft statement','audience':'Fictional stakeholders','purpose':'Evaluate a proposed future target','qualifications':[qualifier]}
    criteria=[]
    for ident in sorted(BASE|{'quantity','plan','progress'}):
        c={'id':ident,'assertion':'Fictional '+ident+' observation','boundary_id':claim['boundary_id'],'period':copy.deepcopy(claim['period']),
            'unit':'1','evidence_ids':[e['id']],'source_result_ids':[],'evidence_fit':'reviewed_supporting','verdict':'supports','quantity':None,
            'qualifications':[],'qualification_visible':False,'rationale':'Fictional reviewer record, not authenticated judgment.'}
        if ident in {'plan','progress'}:c.update(evidence_ids=['strategy-source'],source_result_ids=['implementation-roadmap'],verdict='qualified',qualifications=[qualifier],qualification_visible=True)
        if ident=='quantity':c.update(unit='kWh/count',evidence_ids=['ev-001'],source_result_ids=['strategy-target'],verdict='qualified',qualifications=[qualifier],qualification_visible=True,quantity={'metric_id':'strategy-target-target','expected_value':8})
        criteria.append(c)
    p={'claim':claim,'classification_review':{'kind':'future_goal','evidence_ids':[m['id']],'evidence_fit':'reviewed_supporting','rationale':'Fictional original interpretation.','reviewer_role':'Qualified claim reviewer'},
        'criteria':criteria,'claim_review':{'boundary_id':claim['boundary_id'],'period':copy.deepcopy(claim['period']),'as_of_date':'2026-10-05','evidence_ids':[e['id']],
            'evidence_fit':'reviewed_supporting','scope':'Fictional selected electricity intensity proposal','rationale':'Fictional source/claim review.','reviewer_role':'Qualified claim reviewer'},
        'fixture_mode':True,'result_id':'future-claim-review','goal_review':{'transition_result_id':'transition-plan','roadmap_result_id':'implementation-roadmap','pathway_id':'energy-path',
            'target_result_id':'strategy-target','target_period':{'start':'2030-01-01','end':'2030-12-31'},'as_of_date':'2026-10-05','boundary_id':claim['boundary_id'],
            'period':copy.deepcopy(claim['period']),'subject_id':claim['subject_id'],'evidence_ids':[e['id']],'evidence_fit':'reviewed_supporting','interpretation':'proposed_target','target_year_span':None,
            'rationale':'Fictional proposed target only; unresolved conditions and no performance observation.','reviewer_role':'Qualified planning/source reviewer'}}
    # Select source IDs from the actual frozen planning record, never a guessed source label.
    roadmap=next(r for r in state['results'] if r['id']=='implementation-roadmap');target=next(r for r in state['results'] if r['id']=='strategy-target')
    for c in criteria:
        if c['id'] in {'plan','progress'}:c['evidence_ids']=[roadmap['evidence_ids'][0]]
        if c['id']=='quantity':c['evidence_ids']=[target['evidence_ids'][0]]
    bind(state,p);return state,p


def proof(out):return json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='CLAIM_FUTURE_GOAL_SOURCE_CHECK'))


class ClaimFutureGoalTests(unittest.TestCase):
    def test_proposed_intensity_endpoint_and_plan_are_not_actual_progress(self):
        state,p=fixture();before=copy.deepcopy(state);out=assess_future_goal_claim(state,p);r=report(out);check=proof(out)
        self.assertTrue(check['source_fit']);self.assertEqual(check['delivery_screen'],'known_conditions_not_met')
        self.assertEqual(rows(out)['quantity']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(rows(out)['plan']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(rows(out)['progress']['assessment_state'],'INSUFFICIENT_EVIDENCE');self.assertEqual(r['claim_state'],'INSUFFICIENT_EVIDENCE')
        self.assertIsNone(check['observed_progress']);self.assertEqual(check['monitoring_proposals'],[])
        for k in ('progress_verified','target_adoption_verified','future_performance_guaranteed','funding_or_implementation_authorized','absolute_emissions_reduction_verified','publication_authorized'):self.assertFalse(check[k])
        self.assertEqual(check['goal_review']['target_period']['end'],'2030-12-31');self.assertEqual(r['claim_snapshot']['period'],state['reporting_period'])
        self.assertEqual(state,before);self.assertEqual(out['result']['metrics'],[]);validate_state(out['proposal']['state'])
        for key in ('results','evidence','data_gaps','review_requirements'):
            for item in state[key]:self.assertIn(item,out['proposal']['state'][key])
        reference=rows(out)['quantity']['source_results'][0]['reproduced_report'];self.assertEqual(reference['sha256'],hashlib.sha256(json.dumps(check,sort_keys=True).encode()).hexdigest())

    def test_actual_conflicting_endpoint_commitment_guarantee_and_scope(self):
        for change in ('conflict','committed','guaranteed','unverified','whole','prominence','quantity_source','plan_source'):
            with self.subTest(change=change):
                state,p=fixture()
                if change=='conflict':bind(state,p,'fictional-future-conflict',7)
                elif change in ('committed','guaranteed'):
                    p['goal_review']['interpretation']='committed_target' if change=='committed' else 'guaranteed_achievement'
                    if change=='guaranteed':bind(state,p,'fictional-future-guarantee')
                elif change=='unverified':p['goal_review']['evidence_fit']='unverified'
                elif change=='whole':p['claim']['scope']='whole_subject'
                elif change=='prominence':next(c for c in p['criteria'] if c['id']=='quantity')['qualification_visible']=False
                elif change=='quantity_source':next(c for c in p['criteria'] if c['id']=='quantity')['source_result_ids']=['implementation-roadmap']
                else:next(c for c in p['criteria'] if c['id']=='plan')['source_result_ids']=['strategy-target']
                out=assess_future_goal_claim(state,p);self.assertEqual(report(out)['claim_state'],'POTENTIALLY_MISLEADING' if change=='conflict' else 'INSUFFICIENT_EVIDENCE')

    def test_target_period_binding_and_modified_source_reports_metrics_lineage_block(self):
        initial,original=fixture()
        for change in ('period','path','target','metric','report','lineage'):
            with self.subTest(change=change):
                state,p=copy.deepcopy(initial),copy.deepcopy(original)
                if change=='period':p['goal_review']['target_period']['end']='2029-12-31'
                elif change=='path':p['goal_review']['pathway_id']='unknown-path'
                elif change=='target':p['goal_review']['target_result_id']='interim-target'
                elif change=='metric':next(r for r in state['results'] if r['id']=='strategy-target')['metrics'][0]['uncertainty']['description']='Certain.'
                elif change=='report':
                    d=next(d for r in state['results'] if r['id']=='implementation-roadmap' for d in r['diagnostics'] if d['code']=='IMPLEMENTATION_ROADMAP');r=json.loads(d['message']);r['implementation_authorized']=True;d['message']=json.dumps(r)
                else:next(r for r in state['results'] if r['id']=='strategy-target')['evidence_ids'].append('future-review-evidence')
                out=assess_future_goal_claim(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
                self.assertEqual(out['result']['diagnostics'][0]['code'],'CLAIM_FUTURE_GOAL_REQUIRED')

    def test_original_wrong_unit_and_missing_literal_binding_cannot_supply_goal(self):
        state,p=fixture();next(c for c in p['criteria'] if c['id']=='quantity')['unit']='kWh'
        out=assess_future_goal_claim(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertIn('CLAIM_MATERIAL_REQUIRED',[d['code'] for d in out['result']['diagnostics']])
        state,p=fixture();p['material_pin']['sha256']='0'*64;out=assess_future_goal_claim(state,p)
        self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
        state,p=fixture();p['goal_review']['target_year_span']=p['material_selectors']['quantity_spans'][0]['value_span']
        out=assess_future_goal_claim(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['diagnostics'][0]['code'],'CLAIM_MATERIAL_REQUIRED')
        for name,year_text in [('fictional-future-other-year','2031'),('fictional-future-year-token','2030')]:
            state,p=fixture();bind(state,p,name,year_text=year_text);out=assess_future_goal_claim(state,p)
            self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['diagnostics'][0]['code'],'CLAIM_MATERIAL_REQUIRED')

    def test_source_date_and_fixture_context_cannot_be_refreshed_or_promoted(self):
        for change in ('date','fixture','subject'):
            state,p=fixture()
            if change=='date':p['goal_review']['as_of_date']='2026-10-06'
            elif change=='fixture':p['fixture_mode']=False
            else:p['goal_review']['subject_id']='other-organization'
            out=assess_future_goal_claim(state,p)
            if out['result']['status']!='blocked':self.assertEqual(report(out)['claim_state'],'INSUFFICIENT_EVIDENCE')
            self.assertEqual(out['result']['metrics'],[])

    def test_actual_cli_full_output_equals_helper(self):
        state,p=fixture();request={'contract_version':'0.1.0','skill':'assess-future-goal-claim-evidence','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json';path.write_text(json.dumps(request),encoding='utf-8')
            run=subprocess.run([sys.executable,'-m','scripts.run_claims',str(path)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr);self.assertEqual(json.loads(run.stdout),assess_future_goal_claim(state,p))
