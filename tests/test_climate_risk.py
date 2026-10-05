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
from tests.test_climate_assessment import assessment_fixture


def risk_fixture():
    state,e,v=assessment_fixture()
    for ident,title in [('risk-matrix-source','Fictional ordinal screening matrix'),('risk-judgment-source','Fictional conditional source judgments'),('adaptation-note','Fictional option investigation note')]:
        source=copy.deepcopy(next(x for x in state['evidence'] if x['id']=='condition-source'))
        source['id']=ident; source['source'].update(locator='fixture:'+ident,title=title); source['method']['source']='fixture:'+ident
        state['evidence'].append(source)
    state=run_climate(state,'assess-exposure',e)['proposal']['state']
    state=run_climate(state,'assess-vulnerability',v)['proposal']['state']
    level=lambda ident,label,definition: {'id':ident,'label':label,'definition':definition}
    model={'id':'selected-risk-matrix','name':'Fictional ascending conditional matrix','version':'fictional-1',
        'evidence_ids':['risk-matrix-source'],'evidence_fit':'reviewed_supporting',
        'likelihood_levels':[level('L1','Lower likelihood','Supplied lower ordinal event category, not a probability.'),level('L2','Higher likelihood','Supplied higher ordinal event category, no percentage conversion.')],
        'consequence_levels':[level('C1','Limited','Supplied limited service-consequence category.'),level('C2','Major','Supplied major service-consequence category.'),level('C3','Severe','Supplied severe service-consequence category; not monetized loss.')],
        'risk_levels':[level('R1','Limited screen','Supplied lowest screening class, not safe.'),level('R2','Heightened screen','Supplied intermediate screening class, qualified investigation remains.'),level('R3','Severe screen','Supplied highest screening class, not risk acceptance or prediction.')],
        'cells':[{'likelihood_id':l,'consequence_id':c,'risk_level_id':r} for l,c,r in [('L1','C1','R1'),('L1','C2','R2'),('L1','C3','R3'),('L2','C1','R2'),('L2','C2','R3'),('L2','C3','R3')]]}
    judgment={'lower_level_id':'L1','upper_level_id':'L2','evidence_ids':['risk-judgment-source'],'evidence_fit':'reviewed_supporting',
        'observed_date':'2026-10-03','rationale':'Fictional explicit ordinal source range for scenario A/horizon only; not the 40% stock share.',
        'source_fragment':'Fictional supplied exploratory L1-L2 range; no numeric probability or professional model validation.',
        'limitations':'Coarse selected scenario; site/model fitness and capacities remain unverified.'}
    consequence=copy.deepcopy(judgment); consequence.update(lower_level_id='C2',upper_level_id='C3',
        source_fragment='Fictional supplied C2-C3 conditional service-impact range if the hazard reaches sensitive equipment; no protection from plans assumed.')
    rating={'id':'plant-rain-risk','exposure_id':'plant-stock-exposure',
        'consequence_pathway':'Potential rain/drainage condition reaching sensitive equipment could interrupt selected plant service; no loss forecast.',
        'likelihood':judgment,'consequence':consequence,'context_review':{'confirmed':True,'evidence_ids':['condition-source'],
            'exposure_fit':'reviewed_supporting','vulnerability_fit':'reviewed_supporting','scenario':'Fictional exploratory scenario A',
            'horizon':{'start':'2030-01-01','end':'2050-12-31'},'rationale':'Selected candidate inputs only; planned coping and unknown adaptive capacity remain unresolved, no net protection.'}}
    review=copy.deepcopy(v['vulnerability_review']); review.update(method='ordinal_matrix_screen',evidence_ids=['risk-matrix-source','risk-judgment-source','condition-source'],
        model_fit_rationale='Fictional supplied complete ascending matrix; an initial ordinal screen, no default or scientific calibration.')
    score={'vulnerability_result_id':v['result_id'],'model':model,'ratings':[rating],'risk_review':review,'result_id':'physical-risk'}
    note={'id':'engineering-condition','description':'Qualified drainage/site and engineering investigation has not been completed.',
        'affected_party':'Fictional plant and affected neighboring land users','status':'unmet','evidence_ids':['adaptation-note'],
        'evidence_fit':'reviewed_supporting','observed_date':'2026-10-03','source_fragment':'Fictional note requires review before any physical change.',
        'limitations':'No feasibility, permit, resource or funding approval.'}
    trade=copy.deepcopy(note); trade.update(id='runoff-tradeoff',description='Potential runoff displacement to adjacent land needs affected-party investigation.',
        status='identified',source_fragment='Fictional note flags possible runoff displacement, not observed or quantified harm.')
    option={'id':'site-investigation','name':'Fictional site and dependency investigation','kind':'investigation',
        'target_links':[{'risk_id':rating['id'],'criterion_ids':['sensitive-equipment','response-capacity','long-term-capacity']}],
        'mechanism':'Investigate actual drainage, susceptible equipment and coping/adaptive constraints before design.',
        'intended_effect':'Improve evidence and investigate appropriate responses; no direct quantified risk reduction.',
        'effectiveness_limitations':'No site design, tested capacity or protected future operation.',
        'residual_risk_basis':'Unknown actual intensity, future service and residual disruption remain.',
        'owner':'Fictional proposed investigation owner','timing':{'start':'2029-10-01','end':'2029-10-10'},'prerequisites':[],
        'evidence_ids':['adaptation-note'],'evidence_fit':'reviewed_supporting','observed_date':'2026-10-03',
        'source_fragment':'Fictional investigation proposal, no implementation decision.', 'limitations':'Owner acceptance, funding, resources and qualified review remain open.',
        'constraints':[note],'trade_offs':[trade],'monitoring':None}
    physical=copy.deepcopy(option); physical.update(id='wiring-design',name='Fictional equipment-position design investigation',kind='physical_change',
        mechanism='Propose reviewing equipment position after site investigation, without engineering design prescription.',
        intended_effect='Potential susceptibility reduction if qualified design proves suitable; no guaranteed efficacy.',
        timing={'start':'2031-02-01','end':'2031-02-10'},prerequisites=['site-investigation'])
    adaptation_review=copy.deepcopy(review); adaptation_review.update(method='sourced_adaptation_candidates',evidence_ids=['adaptation-note'])
    adapt={'risk_result_id':score['result_id'],'options':[option,physical],'adaptation_review':adaptation_review,'result_id':'adaptation-options'}
    return state,score,adapt


def adaptation_fixture():
    state,score,adapt=risk_fixture()
    return run_climate(state,'score-physical-risk',score)['proposal']['state'],adapt


class PhysicalRiskTests(unittest.TestCase):
    def test_matrix_range_has_all_possible_classes_and_preserves_uncertainty(self):
        state,p,_=risk_fixture(); old=copy.deepcopy(state); out=run_climate(state,'score-physical-risk',p); row=report(out,'PHYSICAL_RISK_SCREEN')['risks'][0]
        self.assertEqual(row['possible_risk_level_ids'],['R2','R3']); self.assertEqual(row['lower_risk_level_id'],'R2'); self.assertEqual(row['upper_risk_level_id'],'R3')
        self.assertIsNone(row['risk_level_selected']); self.assertIsNone(row['probability']); self.assertIsNone(row['expected_loss'])
        self.assertTrue(row['input_conditions_unresolved']); self.assertFalse(row['risk_verified']); self.assertFalse(row['risk_accepted']); self.assertFalse(row['safe'])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,old); final=out['proposal']['state']
        self.assertEqual(final['results'][:-1],old['results']); self.assertEqual(final['evidence'],old['evidence'])
        for key in ['review_requirements','data_gaps','assumptions']:
            for item in old[key]: self.assertIn(item,final[key])
        validate_state(final)

    def test_low_likelihood_severe_consequence_not_default_low_risk(self):
        state,p,_=risk_fixture(); p['ratings'][0]['likelihood']['upper_level_id']='L1'; p['ratings'][0]['consequence']['lower_level_id']='C3'
        row=report(run_climate(state,'score-physical-risk',p),'PHYSICAL_RISK_SCREEN')['risks'][0]
        self.assertEqual(row['possible_risk_level_ids'],['R3']); self.assertIsNone(row['risk_level_selected'])

    def test_unknown_and_unfit_bounds_do_not_become_a_default_class(self):
        for mode in ['lower','upper','fit','context']:
            state,p,_=risk_fixture()
            if mode=='lower': p['ratings'][0]['likelihood']['lower_level_id']=None
            if mode=='upper': p['ratings'][0]['consequence']['upper_level_id']=None
            if mode=='fit': p['ratings'][0]['likelihood']['evidence_fit']='unverified'
            if mode=='context': p['ratings'][0]['context_review']['vulnerability_fit']='unverified'
            row=report(run_climate(state,'score-physical-risk',p),'PHYSICAL_RISK_SCREEN')['risks'][0]
            self.assertEqual(row['screening_status'],'unclassified'); self.assertEqual(row['possible_risk_level_ids'],[]); self.assertIsNone(row['lower_risk_level_id'])

    def test_missing_duplicate_nonmonotone_and_unfit_matrix_block(self):
        for mode in ['missing','duplicate','nonmonotone','source','version']:
            state,p,_=risk_fixture()
            if mode=='missing': p['model']['cells'].pop()
            if mode=='duplicate': p['model']['cells'].append(copy.deepcopy(p['model']['cells'][0]))
            if mode=='nonmonotone': p['model']['cells'][-1]['risk_level_id']='R1'
            if mode=='source': p['model']['evidence_fit']='irrelevant'
            if mode=='version': next(e for e in state['evidence'] if e['id']=='risk-matrix-source')['source']['version']=None
            out=run_climate(state,'score-physical-risk',p); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_invalid_rating_reference_range_date_and_scenario_block(self):
        for mode in ['exposure','range','level','date','duplicate','scenario','horizon','source']:
            state,p,_=risk_fixture(); r=p['ratings'][0]
            if mode=='exposure': r['exposure_id']='unknown'
            if mode=='range': r['likelihood'].update(lower_level_id='L2',upper_level_id='L1')
            if mode=='level': r['consequence']['lower_level_id']='invented'
            if mode=='date': r['likelihood']['observed_date']='2026-10-06'
            if mode=='duplicate': p['ratings'].append(dict(copy.deepcopy(r),id='duplicate'))
            if mode=='scenario': r['context_review']['scenario']='Different scenario'
            if mode=='horizon': r['context_review']['horizon']['end']='2040-12-31'
            if mode=='source': r['context_review']['evidence_ids']=[]
            self.assertEqual(run_climate(state,'score-physical-risk',p)['result']['status'],'blocked')

    def test_empty_risk_ratings_keep_omissions_open(self):
        state,p,_=risk_fixture(); p['ratings']=[]; out=run_climate(state,'score-physical-risk',p)
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(report(out,'PHYSICAL_RISK_SCREEN')['risks'],[])
        self.assertTrue(any('omitted from physical-risk' in g['reason'] for g in out['result']['data_gaps']))

    def test_adaptation_tradeoffs_constraints_lag_and_authority_preserved(self):
        state,p=adaptation_fixture(); out=run_climate(state,'identify-adaptation-options',p); row=report(out,'ADAPTATION_OPTIONS')
        self.assertEqual(row['options'][0]['constraint_observations'][0]['status'],'unmet')
        self.assertEqual(row['options'][0]['trade_off_observations'][0]['status'],'identified')
        self.assertTrue(any('early-period protection' in g['reason'] for g in out['result']['data_gaps']))
        self.assertIsNone(row['preferred_option_id']); self.assertFalse(row['resilience_verified'])
        for option in row['options']:
            self.assertEqual(option['status'],'proposed_pending_review'); self.assertIsNone(option['expected_risk_reduction']); self.assertIsNone(option['residual_risk'])
            for field in ['effectiveness_verified','monitoring_started','owner_accepted','funding_authorized','resources_reserved','implementation_authorized']: self.assertFalse(option[field])
        self.assertEqual(out['result']['metrics'],[])

    def test_unclassified_risk_still_allows_investigation_not_effectiveness(self):
        state,s,p=risk_fixture(); s['ratings'][0]['likelihood']['lower_level_id']=None
        state=run_climate(state,'score-physical-risk',s)['proposal']['state']; out=run_climate(state,'identify-adaptation-options',p)
        self.assertEqual(out['result']['status'],'partial'); self.assertFalse(report(out,'ADAPTATION_OPTIONS')['options'][0]['effectiveness_verified'])
        self.assertTrue(any('target risk is unclassified' in g['reason'] for g in out['result']['data_gaps']))

    def test_cycles_unknown_dependencies_and_inclusive_conflicts_block(self):
        for mode in ['cycle','unknown','same_day']:
            state,p=adaptation_fixture()
            if mode=='cycle':
                p['options'][0]['prerequisites']=['wiring-design']
                for option in p['options']: option['timing']=None
            if mode=='unknown': p['options'][1]['prerequisites']=['missing']
            if mode=='same_day': p['options'][1]['timing']={'start':'2029-10-10','end':'2029-10-12'}
            out=run_climate(state,'identify-adaptation-options',p); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_unknown_constraints_tradeoffs_monitoring_and_dates_not_feasibility(self):
        state,p=adaptation_fixture(); p['options'][0].update(constraints=[],trade_offs=[],timing=None)
        out=run_climate(state,'identify-adaptation-options',p); self.assertEqual(out['result']['status'],'partial')
        self.assertFalse(report(out,'ADAPTATION_OPTIONS')['options'][0]['implementation_authorized'])
        self.assertTrue(any('no condition/side-effect' in g['reason'] for g in out['result']['data_gaps']))

    def test_option_source_criterion_references_and_observation_dates_block(self):
        for mode in ['criterion','risk','date','source','duplicate']:
            state,p=adaptation_fixture()
            if mode=='criterion': p['options'][0]['target_links'][0]['criterion_ids']=['missing']
            if mode=='risk': p['options'][0]['target_links'][0]['risk_id']='missing'
            if mode=='date': p['options'][0]['trade_offs'][0]['observed_date']='2026-10-06'
            if mode=='source': p['options'][0]['evidence_ids']=['missing']
            if mode=='duplicate': p['options'].append(copy.deepcopy(p['options'][0]))
            self.assertEqual(run_climate(state,'identify-adaptation-options',p)['result']['status'],'blocked')

    def test_changed_source_matrix_and_factor_obligation_block(self):
        for mode in ['judgment','matrix','factor']:
            state,p=adaptation_fixture()
            if mode=='judgment': next(e for e in state['evidence'] if e['id']=='risk-judgment-source')['uncertainty']['description']='Changed source uncertainty'
            if mode=='matrix': next(e for e in state['evidence'] if e['id']=='risk-matrix-source')['source']['version']='changed'
            if mode=='factor': state['results'][-1]['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved selected source factor.'})
            out=run_climate(state,'identify-adaptation-options',p); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])
            if mode=='factor': self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_cli_full_outputs_and_exact_state_handoff(self):
        state,s,p=risk_fixture()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'request.json'
            for skill,params in [('score-physical-risk',s),('identify-adaptation-options',p)]:
                req={'contract_version':'0.1.0','skill':skill,'state':state,'parameters':params}; path.write_text(json.dumps(req),encoding='utf-8'); before=path.read_bytes()
                execution=subprocess.run([sys.executable,'-m','scripts.run_climate',str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(execution.returncode,0,execution.stderr); self.assertEqual(path.read_bytes(),before)
                out=run_climate(state,skill,params); self.assertEqual(json.loads(execution.stdout),out); state=out['proposal']['state']

    def test_saved_author_capture_fully_replays(self):
        capture=json.loads((ROOT/'evaluations/sus16-risk-adaptation.json').read_text(encoding='utf-8'))
        for item in capture['executions']:
            req=item['request']; self.assertEqual(run_climate(req['state'],req['skill'],req['parameters']),item['output'])
