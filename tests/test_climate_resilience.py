import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.climate_tools import run_climate
from scripts.contract_validation import ROOT, validate_state
from tests.test_climate import report
from tests.test_climate_priority import priority_fixture
from tests.test_climate_risk import risk_fixture


def resilience_fixture():
    state,priority=priority_fixture()
    state=run_climate(state,'prioritize-climate-risks',priority)['proposal']['state']
    _,_,adapt=risk_fixture(); state=run_climate(state,'identify-adaptation-options',adapt)['proposal']['state']
    note=copy.deepcopy(state['evidence'][-1]); note['id']='resilience-note'
    note['source'].update(title='Fictional owned resilience investigation proposal',locator='fixture:resilience-note')
    note['method']['source']='fixture:resilience-note'; state['evidence'].append(note)
    basis={'evidence_ids':['resilience-note'],'evidence_fit':'reviewed_supporting','observed_date':'2026-10-03',
        'source_fragment':'Fictional draft proposes investigation and review; acceptance/funding/effectiveness unknown.',
        'limitations':'Engineering, affected-party, service, funding and owner review remain open.'}
    observation=dict(copy.deepcopy(basis),id='review-condition',description='Fictional engineering review not yet conducted.',
        affected_party='Fictional plant and neighboring land users',status='unmet')
    resource=dict(copy.deepcopy(observation),id='capacity',description='Qualified staff capacity and budget unknown.',status='unknown')
    signal=dict(copy.deepcopy(basis),id='review-signal',indicator='Review site and service evidence before design.',
        baseline=None,trigger=None,review_date='2026-11-15',owner='Fictional review coordinator',response='Propose reassessment to qualified owner; no automatic action.')
    action=dict(copy.deepcopy(basis),id='investigate',name='Investigate selected climate concerns',kind='cross_cutting',
        entry_ids=['entry-0','entry-1','entry-4'],adaptation_links=[{'result_id':adapt['result_id'],'option_id':'site-investigation'}],
        objective='Investigate continuity of fictional plant service and external service dependencies.',
        mechanism='Review source evidence, site drainage and policy/reputation pathways separately.',
        effectiveness_limitations='No demonstrated capacity or response effectiveness.',residual_risk_basis='Original source concerns and unknowns remain; no residual-risk calculation.',
        selection_rationale='Evidence collection proposed despite unresolved priority overlap and missing rating; no implementation order.',
        owner=dict(copy.deepcopy(basis),name='Fictional proposed review coordinator'),timing={'start':'2026-11-01','end':'2026-11-10'},depends_on=[],
        resources=[resource],constraints=[observation],trade_offs=[],monitoring=[signal])
    second=copy.deepcopy(action); second.update(id='design-review',name='Review a conditional equipment-position concept',kind='physical_adaptation',
        entry_ids=['entry-0'],adaptation_links=[{'result_id':adapt['result_id'],'option_id':'wiring-design'}],
        depends_on=['investigate'],timing={'start':'2026-11-11','end':'2026-11-20'})
    rec=report({'result':next(r for r in state['results'] if r['id']==priority['result_id'])},'CLIMATE_RISK_PRIORITIES')
    review=copy.deepcopy(priority['priority_review']); review.update(method='sourced_resilience_proposal',evidence_ids=['resilience-note'])
    review['entry_contexts']=copy.deepcopy(priority['priority_review']['entry_contexts'])
    ar=next(r for r in state['results'] if r['id']==adapt['result_id'])
    review['adaptation_contexts']={adapt['result_id']:{'scope':adapt['adaptation_review']['scope'],'evidence_ids':ar['evidence_ids'],
        'evidence_fit':'reviewed_supporting','rationale':'Selected original physical adaptation scope retained separately from organization proposal scope.'}}
    return state,{'priority_result_id':priority['result_id'],'adaptation_result_ids':[adapt['result_id']],
        'actions':[action,second],'resilience_review':review,'result_id':'climate-resilience'}


class ClimateResilienceTests(unittest.TestCase):
    def test_composition_retains_uncertainty_and_proposes_dependencies_without_authority(self):
        state,p=resilience_fixture(); old=copy.deepcopy(state); out=run_climate(state,'develop-climate-resilience-plan',p)
        self.assertEqual(out['result']['status'],'partial'); rec=report(out,'CLIMATE_RESILIENCE_PLAN')
        self.assertEqual(rec['dependency_layers'],[['investigate'],['design-review']]); self.assertEqual(rec['unaddressed_entry_ids'],['entry-2','entry-3'])
        self.assertEqual(rec['priority_snapshot']['unassessed_entry_ids'],['entry-4'])
        self.assertEqual(rec['priority_snapshot']['pairwise_comparisons'][0]['relation'],'unresolved_overlap')
        self.assertEqual(rec['actions'][0]['entry_snapshots'][0]['characterization']['possible_risk_level_ids'],['R2','R3'])
        self.assertEqual(rec['actions'][1]['adaptation_snapshots'][0]['option_snapshot']['status'],'proposed_pending_review')
        self.assertEqual(rec['actions'][0]['resource_observations'][0]['status'],'unknown')
        self.assertIsNone(rec['actions'][0]['monitoring_proposals'][0]['baseline'])
        for a in rec['actions']:
            for key in ['owner_accepted','funding_authorized','resources_reserved','implementation_authorized','started','completed','effectiveness_verified','residual_risk_verified']: self.assertFalse(a[key])
        for key in ['schedule_verified','portfolio_optimized','risk_accepted','resilience_verified','organization_safe','implementation_authorized','public_claim_authorized']: self.assertFalse(rec[key])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,old); final=out['proposal']['state']; validate_state(final)
        self.assertEqual(final['results'][:-1],state['results'])
        for k,v in state.items():
            if k in ['assumptions','data_gaps','review_requirements']:
                for x in v: self.assertIn(x,final[k])
            elif k not in ['revision','results']: self.assertEqual(v,final[k])

    def test_unknown_source_owner_context_timing_and_monitoring_stay_proposals(self):
        for mode in ['source','owner','entry','adaptation','timing','monitoring']:
            state,p=resilience_fixture(); a=p['actions'][0]
            if mode=='source': a['evidence_fit']='unverified'
            elif mode=='owner': a['owner']['observed_date']=None
            elif mode=='entry': p['resilience_review']['entry_contexts']['entry-0']['evidence_fit']='irrelevant'
            elif mode=='adaptation': p['resilience_review']['adaptation_contexts']['adaptation-options']['evidence_fit']='unverified'
            elif mode=='timing': a['timing']=None
            else: a['monitoring'][0].update(observed_date=None,review_date=None)
            out=run_climate(state,'develop-climate-resilience-plan',p); self.assertEqual(out['result']['status'],'partial',mode)
            rec=report(out,'CLIMATE_RESILIENCE_PLAN'); self.assertFalse(rec['resilience_verified']); self.assertFalse(rec['actions'][0]['owner_accepted'])
            if mode in ['source','entry','adaptation']: self.assertEqual(rec['actions'][0]['source_support'],'unverified')

    def test_invalid_dependencies_and_timing_block(self):
        for mode in ['unknown','self','cycle','overlap','reverse','date']:
            state,p=resilience_fixture(); a,b=p['actions']
            if mode=='unknown': a['depends_on']=['absent']
            elif mode=='self': a['depends_on']=['investigate']
            elif mode=='cycle': a.update(depends_on=['design-review'],timing=None); b['timing']=None
            elif mode=='overlap': b['timing']['start']='2026-11-10'
            elif mode=='reverse': a['timing']['end']='2026-10-30'
            else: a['monitoring'][0]['observed_date']='2027-01-01'
            self.assertEqual(run_climate(state,'develop-climate-resilience-plan',p)['result']['status'],'blocked',mode)

    def test_invalid_source_links_and_contexts_block(self):
        for mode in ['entry','option','duplicate','physical','transition','scope','evidence','context','model','mismatch','investigation']:
            state,p=resilience_fixture(); a=p['actions'][0]
            if mode=='entry': a['entry_ids']=['absent']
            elif mode=='option': a['adaptation_links'][0]['option_id']='absent'
            elif mode=='duplicate': p['actions'].append(copy.deepcopy(a))
            elif mode=='physical': p['actions'][1]['adaptation_links']=[]
            elif mode=='transition': a['kind']='transition_response'
            elif mode=='scope': p['resilience_review']['adaptation_contexts']['adaptation-options']['scope']='Different'
            elif mode=='evidence': p['resilience_review']['entry_contexts']['entry-0']['evidence_ids']=['resilience-note']
            elif mode=='context': del p['resilience_review']['entry_contexts']['entry-4']
            elif mode=='mismatch': a['entry_ids']=['entry-1']
            elif mode=='investigation': p['actions'][1]['adaptation_links'][0]['option_id']='site-investigation'
            else: p['resilience_review']['scope']='Other organization'
            self.assertEqual(run_climate(state,'develop-climate-resilience-plan',p)['result']['status'],'blocked',mode)

    def test_source_timing_and_missing_original_prerequisite_remain_gaps(self):
        state,p=resilience_fixture(); p['actions'][1]['depends_on']=[]
        out=run_climate(state,'develop-climate-resilience-plan',p); self.assertEqual(out['result']['status'],'partial')
        reasons=[g['reason'] for g in out['result']['data_gaps']]
        self.assertTrue(any('dates differ from the source adaptation' in r for r in reasons))
        self.assertTrue(any('site-investigation is not a direct proposed dependency' in r for r in reasons))
        rec=report(out,'CLIMATE_RESILIENCE_PLAN')
        source=rec['actions'][1]['adaptation_snapshots'][0]['option_snapshot']
        self.assertEqual(source['timing'],{'start':'2031-02-01','end':'2031-02-10'})
        self.assertEqual(source['prerequisites'],['site-investigation']); self.assertFalse(rec['schedule_verified'])

    def test_monitoring_and_resource_source_requirements_reject_invalid_assumptions(self):
        for mode in ['trigger','duplicate','resource','reference']:
            state,p=resilience_fixture(); a=p['actions'][0]
            if mode=='trigger': a['monitoring'][0]['trigger']=10
            elif mode=='duplicate': a['monitoring'].append(copy.deepcopy(a['monitoring'][0]))
            elif mode=='resource': a['resources'][0]['status']='approved'
            else: a['monitoring'][0]['evidence_ids']=['absent']
            self.assertEqual(run_climate(state,'develop-climate-resilience-plan',p)['result']['status'],'blocked',mode)

    def test_empty_actions_preserve_all_unaddressed_concerns(self):
        state,p=resilience_fixture(); p['actions']=[]; p['adaptation_result_ids']=[]; p['resilience_review']['adaptation_contexts']={}
        out=run_climate(state,'develop-climate-resilience-plan',p); self.assertEqual(out['result']['status'],'partial')
        rec=report(out,'CLIMATE_RESILIENCE_PLAN'); self.assertEqual(len(rec['unaddressed_entry_ids']),5); self.assertEqual(rec['dependency_layers'],[])

    def test_parent_tampering_and_missing_factor_block(self):
        for mode in ['lineage','report','factor']:
            state,p=resilience_fixture(); owner=next(r for r in state['results'] if r['id']==p['priority_result_id'])
            if mode=='lineage': owner['evidence_ids']=['resilience-note']
            elif mode=='report':
                d=next(d for d in owner['diagnostics'] if d['code']=='CLIMATE_RISK_PRIORITIES'); r=json.loads(d['message']); r['priority_approved']=True; d['message']=json.dumps(r)
            else: owner['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'No defensible factor.'})
            out=run_climate(state,'develop-climate-resilience-plan',p); self.assertEqual(out['result']['status'],'blocked')
            if mode=='factor': self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_actual_cli_preserves_input_bytes_and_complete_output(self):
        state,p=resilience_fixture(); expected=run_climate(state,'develop-climate-resilience-plan',p)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json'; path.write_text(json.dumps({'contract_version':'0.1.0','state':state,'skill':'develop-climate-resilience-plan','parameters':p}),encoding='utf-8'); original=path.read_bytes()
            execution=subprocess.run([sys.executable,'-m','scripts.run_climate',str(path)],cwd=ROOT,capture_output=True,text=True,check=True)
            self.assertEqual(execution.stderr,''); self.assertEqual(json.loads(execution.stdout),expected); self.assertEqual(path.read_bytes(),original)
