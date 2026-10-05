import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.climate_tools import run_climate
from scripts.contract_validation import ROOT, validate_state
from tests.test_climate import climate_fixture, report


def assessment_fixture():
    state,hazards,mapping=climate_fixture()
    for ident,title in [('stock-source','Fictional selected machinery stock log'),('condition-source','Fictional selected site-condition inspection'),('vulnerability-rubric','Fictional source-review criteria')]:
        e=copy.deepcopy(state['evidence'][1]); e['id']=ident; e['source'].update(title=title,locator='fixture:'+ident)
        e['method']['source']='fixture:'+ident
        if ident=='stock-source':
            e.update(unit='count',period=copy.deepcopy(state['reporting_period']))
            e['method']['name']='Fictional selected stock inventory fixture'
            e['uncertainty']['description']='Fictional stock population/source fitness and future presence remain unquantified.'
        state['evidence'].append(e)
    for ident,value in [('selected-stock',40),('total-stock',100)]:
        metric=copy.deepcopy(state['results'][0]['metrics'][0]); metric.update(id=ident,name='Fictional '+ident,value=value,unit='count',evidence_ids=['stock-source'])
        metric['calculation']['inputs']=['stock-source']; state['results'][0]['metrics'].append(metric)
        stock_source=next(e for e in state['evidence'] if e['id']=='stock-source')
        metric['method']=copy.deepcopy(stock_source['method']); metric['uncertainty']=copy.deepcopy(stock_source['uncertainty'])
    state['results'][0]['evidence_ids'].append('stock-source')
    state=run_climate(state,'identify-climate-hazards',hazards)['proposal']['state']
    state=run_climate(state,'map-assets-to-hazards',mapping)['proposal']['state']
    qty={'amount_metric_id':'selected-stock','total_metric_id':'total-stock','basis':'historical_stock_proxy',
        'scenario':None,'model':None,
        'stock_definition':'Unique selected processing equipment units in the same fictional inventory population.',
        'service_scope':'Fictional selected plant processing service only.',
        'quantity_review':{'confirmed':True,'evidence_ids':['stock-source'],'rationale':'Fictional identical stock population, not shifts or sales and not a modelled future inventory.',
            'population_basis':'Supplied selected 40-unit subset of the identical 100-unit inventory; no addition across hazards/channels.',
            'coverage_complete':False,'source_contexts':{}}}
    for ident in ['selected-stock','total-stock']:
        qty['quantity_review']['source_contexts'][ident]={'evidence_ids':['stock-source'],'evidence_fit':'reviewed_supporting',
            'rationale':'Fictional selected inventory units share one population/service definition.',
            'stock_definition':qty['stock_definition'],'service_scope':qty['service_scope']}
    observation={'id':'plant-stock-exposure','asset_id':'plant-site','hazard_id':'rain-cell','channel':'direct_site',
        'mechanism':'Selected equipment inventory linked by supplied site review to a potential drainage/service concern; no damage estimate.',
        'status':'documented','observed_date':'2026-10-03','evidence_ids':['condition-source'],'evidence_fit':'reviewed_supporting',
        'source_fragment':'Fictional selected equipment subset under a supplied site condition review, not confirmed inundation.',
        'limitations':'Historic stock proxy, coarse domain and unknown site intensity/future presence remain.', 'quantity':qty}
    review=copy.deepcopy(mapping['mapping_review']); review.update(method='sourced_exposure_stock',evidence_ids=['condition-source','stock-source'])
    exposure={'mapping_result_id':mapping['result_id'],'observations':[observation],'exposure_review':review,'result_id':'climate-exposure'}
    rubric={'id':'condition-checklist','name':'Fictional condition checklist','version':'fictional-1','evidence_ids':['vulnerability-rubric'],
        'evidence_fit':'reviewed_supporting','criteria':[
            {'id':'sensitive-equipment','dimension':'sensitivity','requirement':'Review susceptibility of selected service/equipment to the hazard mechanism.'},
            {'id':'response-capacity','dimension':'coping_capacity','requirement':'Inspect actual exercised immediate response capacity and remaining constraints.'},
            {'id':'long-term-capacity','dimension':'adaptive_capacity','requirement':'Inspect implemented durable changes and future capacity constraints separately from plans.'}]}
    factor={'id':'equipment-condition','exposure_id':observation['id'],'criterion_id':'sensitive-equipment','status':'condition_observed',
        'effect':'susceptibility_increasing','cause_effect':'Fictional sensitive equipment condition may increase interruption susceptibility; no causal loss probability.',
        'effective_period':{'start':'2026-01-01','end':'2050-12-31'},'observed_date':'2026-10-03','evidence_ids':['condition-source'],
        'evidence_fit':'reviewed_supporting','source_fragment':'Fictional supplied equipment-condition record with explicit applicability window.',
        'limitations':'Applicability window is caller-supplied and not professional verification of future conditions.'}
    coping=copy.deepcopy(factor); coping.update(id='response-plan',criterion_id='response-capacity',status='planned',effect='susceptibility_reducing',
        effective_period=None,cause_effect='Proposed response drill, not demonstrated coping capacity.',source_fragment='Fictional draft drill proposal; not exercised.')
    adaptive=copy.deepcopy(coping); adaptive.update(id='adaptation-unknown',criterion_id='long-term-capacity',status='unknown',effect='unknown',observed_date=None,
        cause_effect='Durable adaptation capability has not been assessed.',source_fragment='Fictional evidence contains no durable capacity determination.')
    vreview=copy.deepcopy(review); vreview.update(method='sourced_condition_profile',evidence_ids=['condition-source','vulnerability-rubric'],
        rubric_fit_rationale='Fictional sourced checklist separately retains sensitivity, coping and adaptive capacity without numerical score.')
    vulnerability={'exposure_result_id':exposure['result_id'],'rubric':rubric,'factors':[factor,coping,adaptive],
        'vulnerability_review':vreview,'result_id':'climate-vulnerability'}
    return state,exposure,vulnerability


def vulnerability_fixture():
    state,e,v=assessment_fixture()
    return run_climate(state,'assess-exposure',e)['proposal']['state'],v


class ClimateAssessmentTests(unittest.TestCase):
    def test_sourced_share_is_40_percent_with_historical_period_not_probability(self):
        state,e,_=assessment_fixture(); old=copy.deepcopy(state)
        out=run_climate(state,'assess-exposure',e); row=report(out,'CLIMATE_EXPOSURE')
        self.assertEqual(out['result']['metrics'][0]['value'],40); self.assertEqual(out['result']['metrics'][0]['unit'],'%')
        self.assertEqual(out['result']['metrics'][0]['period'],state['reporting_period'])
        self.assertIsNone(row['organization_total']); self.assertFalse(row['future_stock_verified']); self.assertFalse(row['exposure_verified'])
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(state,old)
        final=out['proposal']['state']; self.assertEqual(final['results'][:-1],old['results']); self.assertEqual(final['evidence'],old['evidence'])
        for k in ['review_requirements','data_gaps','assumptions']:
            for item in old[k]: self.assertIn(item,final[k])
        validate_state(final)

    def test_unknown_unfit_proposed_and_conflicting_quantity_withheld(self):
        for mode in ['quantity','source','proposed','conflicting','population']:
            state,e,_=assessment_fixture()
            if mode=='quantity': e['observations'][0]['quantity']=None
            if mode=='source': e['observations'][0]['evidence_fit']='unverified'
            if mode in {'proposed','conflicting'}: e['observations'][0]['status']=mode
            if mode=='population': e['observations'][0]['quantity']['quantity_review']['source_contexts']['selected-stock']['evidence_fit']='unverified'
            out=run_climate(state,'assess-exposure',e); self.assertEqual(out['result']['metrics'],[]); self.assertEqual(out['result']['status'],'partial')

    def test_zero_total_is_undefined_and_known_zero_stock_can_be_zero_share(self):
        state,e,_=assessment_fixture(); metrics=state['results'][0]['metrics']; metrics[-2]['value']=0; metrics[-1]['value']=0
        out=run_climate(state,'assess-exposure',e); self.assertEqual(out['result']['metrics'],[])
        self.assertIsNone(report(out,'CLIMATE_EXPOSURE')['observations'][0]['quantity_assessment']['supplied_share_percent'])
        metrics[-1]['value']=100
        out=run_climate(state,'assess-exposure',e); self.assertEqual(out['result']['metrics'][0]['value'],0)
        self.assertFalse(report(out,'CLIMATE_EXPOSURE')['organization_safe'])

    def test_amount_units_population_and_period_contradictions_block(self):
        for mode in ['amount','negative','units','definition','sources','basis','period']:
            state,e,_=assessment_fixture(); q=e['observations'][0]['quantity']
            if mode=='amount': state['results'][0]['metrics'][-2]['value']=101
            if mode=='negative': state['results'][0]['metrics'][-2]['value']=-1
            if mode=='units': state['results'][0]['metrics'][-1]['unit']='kg'
            if mode=='definition': q['quantity_review']['source_contexts']['selected-stock']['stock_definition']='Shift events, not equipment'
            if mode=='sources': q['quantity_review']['source_contexts']['selected-stock']['evidence_ids']=['asset-source']
            if mode=='basis': q['basis']='guaranteed_future'
            if mode=='period': state['results'][0]['metrics'][-1]['period']={'start':'2024-01-01','end':'2024-12-31'}
            out=run_climate(state,'assess-exposure',e); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_scenario_stock_requires_horizon_and_declared_source_period(self):
        state,e,_=assessment_fixture(); q=e['observations'][0]['quantity']; q.update(basis='scenario_stock',scenario='Fictional exploratory scenario A',model='Fictional stock projection v1')
        self.assertEqual(run_climate(state,'assess-exposure',e)['result']['status'],'blocked')
        for metric in state['results'][0]['metrics'][-2:]: metric['period']={'start':'2030-01-01','end':'2035-12-31'}
        self.assertEqual(run_climate(state,'assess-exposure',e)['result']['metrics'],[])
        next(s for s in state['evidence'] if s['id']=='stock-source')['period']={'start':'2030-01-01','end':'2035-12-31'}
        out=run_climate(state,'assess-exposure',e); self.assertEqual(out['result']['metrics'][0]['value'],40)
        self.assertEqual(out['result']['metrics'][0]['period']['start'],'2030-01-01')
        self.assertFalse(report(out,'CLIMATE_EXPOSURE')['future_stock_verified'])

    def test_multiple_channels_are_not_aggregated(self):
        state,e,_=assessment_fixture(); second=copy.deepcopy(e['observations'][0]); second.update(id='service-channel',channel='service_disruption')
        e['observations'].append(second); out=run_climate(state,'assess-exposure',e)
        self.assertEqual([m['value'] for m in out['result']['metrics']],[40,40]); self.assertIsNone(report(out,'CLIMATE_EXPOSURE')['organization_total'])

    def test_later_bad_observation_clears_earlier_metrics(self):
        state,e,_=assessment_fixture(); second=copy.deepcopy(e['observations'][0]); second.update(id='invalid-channel',asset_id='missing')
        e['observations'].append(second); out=run_climate(state,'assess-exposure',e)
        self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_vulnerability_retains_sensitivity_plan_unknown_and_no_offset(self):
        state,v=vulnerability_fixture(); out=run_climate(state,'assess-vulnerability',v); row=report(out,'CLIMATE_VULNERABILITY')
        self.assertEqual([f['assessment_status'] for f in row['factors']],['sourced_condition_candidate','unverified','unverified'])
        profile=row['profiles'][0]; self.assertEqual(profile['dimension_status']['sensitivity'],'reviewed_criterion_candidates')
        self.assertEqual(profile['dimension_status']['coping_capacity'],'conditions_unresolved'); self.assertFalse(profile['capacity_offsets_sensitivity'])
        self.assertIsNone(profile['vulnerability_score']); self.assertIsNone(profile['risk_reduction']); self.assertFalse(profile['safe'])
        self.assertEqual(out['result']['metrics'],[]); self.assertFalse(row['capacity_verified'])

    def test_time_limited_conditions_do_not_cover_future_horizon(self):
        state,v=vulnerability_fixture(); v['factors'][0]['effective_period']={'start':'2026-01-01','end':'2030-12-31'}
        row=report(run_climate(state,'assess-vulnerability',v),'CLIMATE_VULNERABILITY')['factors'][0]
        self.assertEqual(row['horizon_applicability'],'unverified'); self.assertEqual(row['assessment_status'],'unverified')
        v['factors'][0]['effective_period']=None
        self.assertEqual(report(run_climate(state,'assess-vulnerability',v),'CLIMATE_VULNERABILITY')['factors'][0]['assessment_status'],'unverified')

    def test_missing_criteria_and_unfit_rubric_remain_open_or_block(self):
        state,v=vulnerability_fixture(); v['factors']=[]
        out=run_climate(state,'assess-vulnerability',v); self.assertEqual(out['result']['status'],'partial')
        self.assertTrue(any('criterion unassessed' in g['reason'] for g in out['result']['data_gaps']))
        v['rubric']['evidence_fit']='irrelevant'; self.assertEqual(run_climate(state,'assess-vulnerability',v)['result']['status'],'blocked')
        state,v=vulnerability_fixture(); v['rubric']['criteria']=v['rubric']['criteria'][:1]
        self.assertEqual(run_climate(state,'assess-vulnerability',v)['result']['status'],'blocked')

    def test_unknown_factor_reference_future_date_and_duplicate_criterion_block(self):
        for mode in ['exposure','criterion','date','duplicate','capacity']:
            state,v=vulnerability_fixture()
            if mode=='exposure': v['factors'][0]['exposure_id']='unknown'
            if mode=='criterion': v['factors'][0]['criterion_id']='unknown'
            if mode=='date': v['factors'][0]['observed_date']='2026-10-06'
            if mode=='duplicate': v['factors'].append(dict(v['factors'][0],id='duplicate'))
            if mode=='capacity': v['factors'][0]['status']='capacity_demonstrated'
            out=run_climate(state,'assess-vulnerability',v); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_source_change_and_unresolved_factor_block_without_shares(self):
        for mode in ['hazard','mapping','stock','factor']:
            state,v=vulnerability_fixture()
            if mode=='hazard': state['evidence'][1]['source']['version']='changed'
            if mode=='mapping': state['evidence'][2]['uncertainty']['description']='Changed site uncertainty'
            if mode=='stock': state['results'][0]['metrics'][-2]['value']=50
            if mode=='factor':
                state['results'][0]['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved source quantity factor.'})
                state['results'][0]['status']='partial'
                state['results'][0]['review_states'].append('EVIDENCE_INCOMPLETE')
                state['results'][0]['data_gaps']=copy.deepcopy(state['data_gaps'])
            out=run_climate(state,'assess-vulnerability',v); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])
            if mode=='factor': self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_cli_exact_outputs_and_state_handoff(self):
        state,e,v=assessment_fixture()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'request.json'
            for skill,params in [('assess-exposure',e),('assess-vulnerability',v)]:
                request={'contract_version':'0.1.0','skill':skill,'state':state,'parameters':params}; path.write_text(json.dumps(request),encoding='utf-8'); before=path.read_bytes()
                execution=subprocess.run([sys.executable,'-m','scripts.run_climate',str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(execution.returncode,0,execution.stderr); self.assertEqual(path.read_bytes(),before)
                out=run_climate(state,skill,params); self.assertEqual(json.loads(execution.stdout),out); state=out['proposal']['state']

    def test_saved_author_capture_fully_replays(self):
        capture=json.loads((ROOT/'evaluations/sus16-exposure-vulnerability.json').read_text(encoding='utf-8'))
        for item in capture['executions']:
            req=item['request']; self.assertEqual(run_climate(req['state'],req['skill'],req['parameters']),item['output'])
