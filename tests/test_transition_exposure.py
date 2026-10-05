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
from tests.test_climate_transition import transition_fixture


def transition_exposure_fixture():
    state,_=transition_fixture(); selected=[]; observations=[]
    channels={'policy':'operating_cost','market':'demand','technology':'service_availability','reputation':'stakeholder_relationship'}
    for family in channels:
        _,p=transition_fixture(family); skill='identify-'+family+'-risk'
        state=run_climate(state,skill,p)['proposal']['state']; selected.append({'result_id':p['result_id'],'skill':skill})
        driver=p['drivers'][0]
        observations.append({'id':family+'-exposure','subject_id':'plant-service','driver_result_id':p['result_id'],'driver_id':driver['id'],
            'status':'conditional','mechanism':'Selected '+family+' change may affect the plant service under the supplied case; actual magnitude and applicability unresolved.',
            'effect_channels':[channels[family]],'scenario':driver['scenario'],'horizon':driver['horizon'],
            'context_review':{'confirmed':True,'driver_fit':'reviewed_supporting','subject_fit':'reviewed_supporting','link_fit':'reviewed_supporting',
                'driver_scope':driver['affected_scope'],'subject_scope':'Selected fictional processing service',
                'evidence_ids':['transition-source','asset-source'],'rationale':'Fictional selected service/driver pathway only, not law, efficacy or loss validation.'},
            'evidence_ids':['transition-source','asset-source'],'evidence_fit':'reviewed_supporting','observed_date':'2026-10-03',
            'source_fragment':'Fictional pathway proposal and proposed service-window excerpt; no guaranteed effect.',
            'limitations':'Unverified actual legal, market, technology and stakeholder effects.'})
    subject={'id':'plant-service','name':'Fictional selected processing service','kind':'activity','boundary_relation':'direct','facility_id':'facility-001',
        'service_scope':'Selected fictional processing service','owner':'Fictional proposed source-review owner',
        'activity_period':{'start':'2030-01-01','end':'2032-12-31'},'evidence_ids':['asset-source'],'evidence_fit':'reviewed_supporting',
        'observed_date':'2026-10-03','source_fragment':'Fictional documented proposed service period, not verified future operation.',
        'limitations':'Future availability, control and losses unverified.'}
    review=copy.deepcopy(p['transition_review']); review.update(method='source_transition_exposure',evidence_ids=['transition-source','asset-source'])
    return state,{'driver_results':selected,'subjects':[subject],'observations':observations,'exposure_review':review,'result_id':'transition-exposure'}


class TransitionExposureTests(unittest.TestCase):
    def test_four_pathways_preserve_full_context_history_and_horizon_gaps(self):
        state,p=transition_exposure_fixture(); original=copy.deepcopy(state); out=run_climate(state,'assess-transition-exposure',p)
        rec=report(out,'TRANSITION_EXPOSURE'); self.assertEqual(out['result']['status'],'partial'); self.assertEqual(len(rec['driver_snapshots']),4)
        self.assertEqual([o['assessment_status'] for o in rec['observations']],['conditional_exposure_candidate']*4)
        for o in rec['observations']:
            self.assertEqual(o['temporal_relation'],'overlapping'); self.assertFalse(o['organization_exposure_verified']); self.assertFalse(o['legal_applicability_determined'])
            self.assertIsNone(o['financial_effect']); self.assertIsNone(o['probability']); self.assertFalse(o['risk_accepted'])
        self.assertTrue(any('full transition horizon' in g['reason'] for g in out['result']['data_gaps']))
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,original); final=out['proposal']['state']
        self.assertEqual(final['results'][:-1],state['results'])
        for k,v in state.items():
            if k in ['assumptions','data_gaps','review_requirements']:
                for x in v: self.assertIn(x,final[k])
            elif k not in ['revision','results']: self.assertEqual(v,final[k])
        validate_state(final)

    def test_unknown_disjoint_period_and_unfit_link_withhold_without_clearance(self):
        for mode in ['unknown','disjoint','fit','confirmed','status','date']:
            state,p=transition_exposure_fixture()
            if mode=='unknown': p['subjects'][0]['activity_period']=None
            if mode=='disjoint': p['subjects'][0]['activity_period']={'start':'2025-01-01','end':'2025-12-31'}
            if mode=='fit': p['observations'][0]['context_review']['link_fit']='irrelevant'
            if mode=='confirmed': p['observations'][0]['context_review']['confirmed']=False
            if mode=='status': p['observations'][0]['status']='unknown'
            if mode=='date': p['observations'][0]['observed_date']=None
            out=run_climate(state,'assess-transition-exposure',p); rec=report(out,'TRANSITION_EXPOSURE')
            self.assertEqual(rec['observations'][0]['assessment_status'],'unverified'); self.assertFalse(rec['exposure_verified'])
            self.assertIsNone(rec['organization_total'])

    def test_invalid_pair_scope_scenario_evidence_channels_and_facility_block(self):
        for mode in ['result','driver','subject','duplicate','scope','scenario','horizon','evidence','channels','facility','future']:
            state,p=transition_exposure_fixture(); obs=p['observations'][0]
            if mode=='result': obs['driver_result_id']='missing'
            if mode=='driver': obs['driver_id']='missing'
            if mode=='subject': obs['subject_id']='missing'
            if mode=='duplicate': p['observations'].append(copy.deepcopy(obs))
            if mode=='scope': obs['context_review']['subject_scope']='Another service'
            if mode=='scenario': obs['scenario']='Different case'
            if mode=='horizon': obs['horizon']['end']='2034-12-31'
            if mode=='evidence': obs['context_review']['evidence_ids']=['asset-source']
            if mode=='channels': obs['effect_channels']=['guaranteed_profit']
            if mode=='facility': p['subjects'][0]['facility_id']='outside'
            if mode=='future': obs['observed_date']='2026-10-06'
            out=run_climate(state,'assess-transition-exposure',p); self.assertEqual(out['result']['status'],'blocked',mode); self.assertEqual(out['result']['metrics'],[])

    def test_empty_omitted_and_external_subjects_retain_unknown_coverage(self):
        state,p=transition_exposure_fixture(); external=copy.deepcopy(p['subjects'][0]); external.update(id='external',boundary_relation='value_chain',facility_id=None,activity_period=None)
        p['subjects'].append(external); p['observations']=p['observations'][:1]
        out=run_climate(state,'assess-transition-exposure',p)
        self.assertTrue(any('external /' in g['reason'] for g in out['result']['data_gaps']))
        p['driver_results']=[]; p['observations']=[]; p['exposure_review'].update(coverage_complete=True,exclusions=[])
        out=run_climate(state,'assess-transition-exposure',p); self.assertEqual(out['result']['status'],'partial')
        self.assertEqual(len([g for g in out['result']['data_gaps'] if 'family not selected' in g['reason']]),4)

    def test_changed_parent_source_blocked_and_factor_obligation_survives(self):
        for mode in ['version','fragment','factor']:
            state,p=transition_exposure_fixture()
            parent=next(r for r in state['results'] if r['id']==p['driver_results'][0]['result_id'])
            if mode=='version': state['evidence'][-1]['source']['version']='changed'
            if mode=='fragment': next(d for d in parent['diagnostics'] if d['code']=='CLIMATE_INPUTS')['message']='{}'
            if mode=='factor': parent['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved selected factor.'})
            out=run_climate(state,'assess-transition-exposure',p); self.assertEqual(out['result']['status'],'blocked')
            if mode=='factor': self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_scope_review_and_selected_skill_must_match_current_parents(self):
        for mode in ['scope','date','skill','duplicate']:
            state,p=transition_exposure_fixture()
            if mode=='scope': p['exposure_review']['scope']='Another organization'
            if mode=='date': p['exposure_review']['as_of_date']='2026-10-04'
            if mode=='skill': p['driver_results'][0]['skill']='identify-climate-hazards'
            if mode=='duplicate': p['driver_results'].append(copy.deepcopy(p['driver_results'][0]))
            self.assertEqual(run_climate(state,'assess-transition-exposure',p)['result']['status'],'blocked')

    def test_cli_complete_output_and_request_integrity(self):
        state,p=transition_exposure_fixture(); req={'contract_version':'0.1.0','skill':'assess-transition-exposure','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'request.json'; f.write_text(json.dumps(req),encoding='utf-8'); before=f.read_bytes()
            run=subprocess.run([sys.executable,'-m','scripts.run_climate',str(f)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(json.loads(run.stdout),run_climate(state,req['skill'],p)); self.assertEqual(f.read_bytes(),before)


if __name__=='__main__': unittest.main()
