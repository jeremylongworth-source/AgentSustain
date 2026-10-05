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
from tests.test_climate_risk import risk_fixture
from tests.test_climate_transition import transition_fixture
from tests.test_transition_exposure import transition_exposure_fixture


def register_fixture():
    state,score,_=risk_fixture(); state=run_climate(state,'score-physical-risk',score)['proposal']['state']
    initial,_=transition_fixture(); state['evidence'].append(copy.deepcopy(next(e for e in initial['evidence'] if e['id']=='transition-source')))
    for family in ['policy','market','technology','reputation']:
        _,p=transition_fixture(family); state=run_climate(state,'identify-'+family+'-risk',p)['proposal']['state']
    _,exposure=transition_exposure_fixture(); state=run_climate(state,'assess-transition-exposure',exposure)['proposal']['state']
    source=copy.deepcopy(state['evidence'][-1]); source['id']='register-note'; source['source'].update(title='Fictional register investigation proposal',locator='fixture:register-note')
    source['method']['source']='fixture:register-note'; source['uncertainty']['description']='Proposed owners, actions and common-service links unverified.'; state['evidence'].append(source)
    basis={'evidence_ids':['register-note'],'evidence_fit':'reviewed_supporting','observed_date':'2026-10-03',
        'source_fragment':'Fictional proposal to investigate selected sources, not adoption or demonstrated risk reduction.',
        'limitations':'No accepted owner, verified risk, authorized response or public claim.'}
    entries=[]
    selected=[(score['result_id'],'plant-rain-risk','physical')]+[(exposure['result_id'],family+'-exposure','transition') for family in ['policy','market','technology','reputation']]
    for i,(result_id,record_id,kind) in enumerate(selected):
        owner=dict(copy.deepcopy(basis),name='Fictional proposed '+kind+' review owner')
        action=dict(copy.deepcopy(basis),id='follow-'+str(i),action='Investigate actual '+record_id+' context and affected service before response.',
            owner=owner['name'],target_date='2026-11-01')
        entry=dict(copy.deepcopy(basis),id='entry-'+str(i),source_result_id=result_id,source_record_id=record_id,
            interpretation='Selected '+kind+' source concern only; uncertainties and qualified review retained.',owner=owner,follow_ups=[action])
        entries.append(entry)
    interaction=dict(copy.deepcopy(basis),id='shared-service',entry_ids=['entry-0','entry-1'],kind='shared_asset',
        mechanism='Potential shared processing-service dependency requires investigation; distinct physical and transition scenarios do not establish joint events.')
    review=copy.deepcopy(exposure['exposure_review']); review.update(method='source_climate_register',scope='Fictional selected organization climate register',evidence_ids=['register-note'])
    review['source_contexts']={}
    for ident in [score['result_id'],exposure['result_id']]:
        parent=next(r for r in state['results'] if r['id']==ident)
        review['source_contexts'][ident]={'scope':exposure['exposure_review']['scope'],'evidence_ids':parent['evidence_ids'],
            'evidence_fit':'reviewed_supporting','rationale':'Fictional selected source scopes retained separately, not whole-organization coverage or risk comparability.'}
    return state,{'physical_results':[score['result_id']],'transition_results':[exposure['result_id']], 'entries':entries,'interactions':[interaction],
        'register_review':review,'result_id':'climate-register'}


class ClimateRegisterTests(unittest.TestCase):
    def test_register_preserves_distinct_characterizations_sources_and_history(self):
        state,p=register_fixture(); original=copy.deepcopy(state); out=run_climate(state,'build-climate-risk-register',p); rec=report(out,'CLIMATE_RISK_REGISTER')
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(len(rec['entries']),5)
        physical=rec['entries'][0]['characterization']; self.assertEqual(physical['possible_risk_level_ids'],['R2','R3']); self.assertIsNone(physical['risk_level_selected'])
        self.assertNotEqual(physical['context_review']['scenario'],rec['entries'][1]['characterization']['scenario'])
        self.assertTrue(rec['shared_sources_non_additive']); self.assertIsNone(rec['combined_score']); self.assertIsNone(rec['aggregate_loss'])
        self.assertEqual(len(rec['source_usage']['register-note']),5); self.assertEqual(len(rec['source_usage']['transition-source']),4)
        for entry in rec['entries']:
            self.assertFalse(entry['owner_accepted']); self.assertFalse(entry['risk_verified']); self.assertFalse(entry['risk_accepted']); self.assertFalse(entry['risk_mitigated'])
            self.assertEqual(entry['status'],'registered_pending_review'); self.assertFalse(entry['follow_up_proposals'][0]['completed'])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,original); final=out['proposal']['state']
        self.assertEqual(final['results'][:-1],state['results'])
        for k,v in state.items():
            if k in ['assumptions','data_gaps','review_requirements']:
                for x in v: self.assertIn(x,final[k])
            elif k not in ['revision','results']: self.assertEqual(v,final[k])
        validate_state(final)

    def test_withheld_scope_owner_and_interpretation_never_accept_risk(self):
        for mode in ['scope','owner','entry','date']:
            state,p=register_fixture()
            if mode=='scope': p['register_review']['source_contexts']['physical-risk']['evidence_fit']='unverified'
            if mode=='owner': p['entries'][0]['owner']['evidence_fit']='unverified'
            if mode=='entry': p['entries'][0]['evidence_fit']='irrelevant'
            if mode=='date': p['entries'][0]['observed_date']=None
            rec=report(run_climate(state,'build-climate-risk-register',p),'CLIMATE_RISK_REGISTER')
            if mode!='owner': self.assertEqual(rec['entries'][0]['interpreted_source_support'],'unverified')
            self.assertFalse(rec['entries'][0]['owner_accepted']); self.assertFalse(rec['risk_accepted'])

    def test_missing_entries_families_interactions_and_followups_stay_gaps(self):
        state,p=register_fixture(); p['entries']=p['entries'][:1]; p['entries'][0]['follow_ups']=[]; p['interactions']=[]
        p['register_review'].update(coverage_complete=True,exclusions=[])
        out=run_climate(state,'build-climate-risk-register',p)
        self.assertTrue(any('omitted from register' in g['reason'] for g in out['result']['data_gaps']))
        self.assertTrue(any('not independence' in g['reason'] for g in out['result']['data_gaps']))
        p['transition_results']=[]; p['register_review']['source_contexts'].pop('transition-exposure')
        out=run_climate(state,'build-climate-risk-register',p); self.assertEqual(out['result']['status'],'partial')
        self.assertTrue(any('assessment family omitted' in g['reason'] for g in out['result']['data_gaps']))

    def test_bad_links_scope_sources_dates_and_duplicates_block(self):
        for mode in ['record','duplicate','scope','contexts','sources','future','interaction','followup','result']:
            state,p=register_fixture()
            if mode=='record': p['entries'][0]['source_record_id']='missing'
            if mode=='duplicate': p['entries'].append(copy.deepcopy(p['entries'][0]))
            if mode=='scope': p['register_review']['source_contexts']['physical-risk']['scope']='Wrong source scope'
            if mode=='contexts': p['register_review']['source_contexts'].pop('physical-risk')
            if mode=='sources': p['register_review']['source_contexts']['physical-risk']['evidence_ids']=['register-note']
            if mode=='future': p['entries'][0]['owner']['observed_date']='2026-10-06'
            if mode=='interaction': p['interactions'][0]['entry_ids']=['entry-0','missing']
            if mode=='followup': p['entries'][1]['follow_ups'][0]['id']=p['entries'][0]['follow_ups'][0]['id']
            if mode=='result': p['physical_results']=['transition-exposure']
            self.assertEqual(run_climate(state,'build-climate-risk-register',p)['result']['status'],'blocked',mode)

    def test_changed_nested_source_and_missing_factor_block(self):
        for mode in ['version','factor']:
            state,p=register_fixture()
            if mode=='version': next(e for e in state['evidence'] if e['id']=='risk-judgment-source')['source']['version']='changed'
            else: next(r for r in state['results'] if r['id']=='physical-risk')['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved factor.'})
            out=run_climate(state,'build-climate-risk-register',p); self.assertEqual(out['result']['status'],'blocked')
            if mode=='factor': self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_tampered_parent_evidence_lineage_cannot_be_relabelled_as_review_evidence(self):
        state,p=register_fixture(); owner=next(r for r in state['results'] if r['id']=='physical-risk')
        owner['evidence_ids']=['register-note']
        p['register_review']['source_contexts']['physical-risk']['evidence_ids']=['register-note']
        out=run_climate(state,'build-climate-risk-register',p)
        self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_unknown_overdue_followup_dates_do_not_imply_completion(self):
        for when in [None,'2026-10-01']:
            state,p=register_fixture(); p['entries'][0]['follow_ups'][0]['target_date']=when
            out=run_climate(state,'build-climate-risk-register',p)
            self.assertTrue(any('unknown or overdue' in g['reason'] for g in out['result']['data_gaps']))
            self.assertFalse(report(out,'CLIMATE_RISK_REGISTER')['entries'][0]['follow_up_proposals'][0]['completed'])

    def test_cli_complete_output_and_request_integrity(self):
        state,p=register_fixture(); req={'contract_version':'0.1.0','skill':'build-climate-risk-register','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'request.json'; f.write_text(json.dumps(req),encoding='utf-8'); before=f.read_bytes()
            run=subprocess.run([sys.executable,'-m','scripts.run_climate',str(f)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(json.loads(run.stdout),run_climate(state,req['skill'],p)); self.assertEqual(f.read_bytes(),before)


if __name__=='__main__': unittest.main()
