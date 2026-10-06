import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.claim_comparison import assess_comparison_claim
from scripts.contract_validation import ROOT,validate_state
from scripts.ghg_foundation import calculate_result
from scripts.ghg_inventory import build_inventory
from scripts.inventory_analysis import compare_inventories
from scripts.scope_accounting import compose_scope
from scripts.state_proposal import propose
from tests.test_claim_inventory import fixture as inventory_claim_fixture
from tests.test_claims_review import report,rows
from tests.test_scope_accounting import scope_fixture


def bind(state,p,name='fictional-change',value=-100,unit='kg CO2e'):
    raw=(ROOT/'standards/claims/materials'/(name+'.json')).read_bytes();m=json.loads(raw);text=m['text'].splitlines()[1]
    e=next(e for e in state['evidence'] if e['id']=='comparison-claim-material');e['source'].update(locator='workspace:standards/claims/materials/'+name+'.json',version=m['version'])
    p['claim']['text']=text
    def span(part):
        start=m['text'].index(part);return {'start':start,'end':start+len(part)}
    p['material_pin']={'path':name+'.json','sha256':hashlib.sha256(raw).hexdigest()}
    p['material_selectors']={'claim_span':span(text),'qualification_spans':[{'text':q,'span':span(q)} for q in p['claim']['qualifications']],
        'quantity_spans':[{'criterion_id':'quantity','value_span':span(str(value)),'unit_span':span(unit)}]}
    c=next(c for c in p['criteria'] if c['id']=='quantity');c.update(unit=unit);c['quantity'].update(expected_value=value,metric_id='inventory-comparison-'+('percentage-change' if unit=='%' else 'absolute-change'))


def fixture(before=1000):
    state,sources,components,coverage=scope_fixture();period={'start':'2024-01-01','end':'2024-12-31'}
    state['reporting_period']=period
    for e in state['evidence']:e['period']=copy.deepcopy(period)
    for r in state['results']:
        for m in r['metrics']:m['period']=copy.deepcopy(period)
    state['results'][0]['metrics'][0]['value']=before;state['results'][1]['metrics'][0]['value']=before*0.5
    state=compose_scope(state,'calculate-location-based-scope-2',sources,components,coverage,'prior-energy',True)['proposal']['state']
    screening=[{'category':i,'status':'unknown','evidence_ids':['ev-001'],'rationale':'Fictional unassessed category retained.'} for i in range(1,16)]
    state=build_inventory(state,None,'prior-energy',[],screening,coverage,'prior-inventory',True)['proposal']['state'];prior=copy.deepcopy(state)
    state['reporting_period']={'start':'2025-01-01','end':'2025-12-31'}
    e=copy.deepcopy(state['evidence'][0]);e.update(id='current-evidence',period=copy.deepcopy(state['reporting_period']))
    raw=copy.deepcopy(state['results'][0]);raw.update(id='current-activity-result',assumptions=list(state['assumptions']),data_gaps=copy.deepcopy(state['data_gaps']),status='partial',review_states=['ANALYTICAL','EVIDENCE_INCOMPLETE'],evidence_ids=[e['id']])
    raw['metrics'][0].update(id='current-activity',value=800,period=copy.deepcopy(state['reporting_period']),evidence_ids=[e['id']]);raw['metrics'][0]['calculation']['inputs']=[e['id']]
    state=propose(state,raw,'Preserve prior record and add distinct fictional current activity',[e])['state']
    component=copy.deepcopy(components[0]);component['policy']['source_review']['activity_id']='current-activity';component['metric_id']='current-co2e-metric'
    source=copy.deepcopy(sources[0]);source.update(activity_id='current-activity',evidence_ids=[e['id']])
    state=calculate_result(state,'current-activity',component['factor_id'],component['policy'],'current-co2e',True)['proposal']['state']
    state=compose_scope(state,'calculate-location-based-scope-2',[source],[component],coverage,'current-energy',True)['proposal']['state']
    state=build_inventory(state,None,'current-energy',[],screening,coverage,'current-inventory',True)['proposal']['state']
    core_review={'confirmed':True,'prior_inventory_id':'prior-inventory','current_inventory_id':'current-inventory','evidence_ids':['ev-001','current-evidence'],
        'reviewer':'Fictional reviewer','rationale':'Explicit selected-stock comparison only.','boundary_changes_assessment':'Same fictional boundary.',
        'coverage_changes_assessment':'Same selected electricity source, categories unknown.','factor_changes_assessment':'Same synthetic intensity, not an attribution analysis.','restatement_assessment':'No fictional restatement; no verified reduction.'}
    state=compare_inventories(state,prior,'prior-inventory','current-inventory',core_review,'inventory-comparison',True)['proposal']['state']
    _,p=inventory_claim_fixture();v=p.pop('inventory_review');p['result_id']='comparison-claim-review'
    e=copy.deepcopy(state['evidence'][0]);e.update(id='claim-review-evidence',unit='1',period=copy.deepcopy(state['reporting_period']));state['evidence'].append(e)
    m=copy.deepcopy(e);m.update(id='comparison-claim-material',period={'start':'2026-09-01','end':'2026-10-05'});state['evidence'].append(m)
    p['claim'].update(kind='comparative',scope='selected_sources',material_evidence_ids=[m['id']],qualifications=['Selected inventory arithmetic only; no causal attribution.'])
    p['classification_review'].update(kind='comparative',evidence_ids=[m['id']])
    p['criteria']=[c for c in p['criteria'] if c['id']!='inventory']
    template=copy.deepcopy(next(c for c in p['criteria'] if c['id']=='quantity'))
    for ident in ('baseline','comparability'):
        c=copy.deepcopy(template);c.update(id=ident,quantity=None);p['criteria'].append(c)
    for c in p['criteria']:
        if c['source_result_ids']:c.update(source_result_ids=['inventory-comparison'],evidence_ids=['current-evidence'],qualifications=p['claim']['qualifications'][:])
    a=copy.deepcopy(v);a.update(inventory_result_id='prior-inventory',coverage='selected_sources',period=copy.deepcopy(prior['reporting_period']),coverage_evidence_ids=['ev-001'])
    b=copy.deepcopy(v);b.update(inventory_result_id='current-inventory',coverage='selected_sources',coverage_evidence_ids=['current-evidence'])
    p['comparison_review']={'comparison_result_id':'inventory-comparison','prior_state':prior,'prior_inventory_review':a,'current_inventory_review':b,
        'as_of_date':'2026-10-05','evidence_ids':[e['id']],'evidence_fit':'reviewed_supporting','interpretation':'observed_inventory_change','quantity_interpretation':'signed_change',
        'rationale':'Fictional observed inventory change, no project counterfactual.','reviewer_role':'Qualified comparison/source reviewer'}
    bind(state,p);return state,p


def proof(out):return json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='CLAIM_COMPARISON_SOURCE_CHECK'))


class ClaimComparisonTests(unittest.TestCase):
    def test_observed_signed_change_both_sources_reproduce_without_causal_or_whole_promotion(self):
        state,p=fixture();before=copy.deepcopy(state);out=assess_comparison_claim(state,p);check=proof(out)
        self.assertEqual([m['value'] for m in check['result']['metrics']],[-100,-20])
        self.assertTrue(check['source_fit']);self.assertFalse(check['declared_scope_coverage_reproduced'])
        for k in ('project_causation_verified','avoided_emissions_verified','source_authenticity_verified','publication_authorized'):self.assertFalse(check[k])
        for ident in ('quantity','baseline','comparability'):self.assertEqual(rows(out)[ident]['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(report(out)['claim_state'],'PROFESSIONAL_REVIEW_REQUIRED');self.assertEqual(state,before);validate_state(out['proposal']['state'])
        reference=rows(out)['quantity']['source_results'][0]['reproduced_report']
        self.assertEqual(reference['diagnostic_code'],'CLAIM_COMPARISON_SOURCE_CHECK')
        self.assertEqual(reference['sha256'],hashlib.sha256(json.dumps(check,sort_keys=True).encode('utf-8')).hexdigest())
        self.assertEqual(out['result']['metrics'],[])
        for key in ('results','evidence','data_gaps','review_requirements'):
            for item in state[key]:self.assertIn(item,out['proposal']['state'][key])

    def test_actual_conflict_causation_unknown_and_whole_partial_claims(self):
        for change in ('conflict','causal','unknown','whole','date','documentary_baseline','missing_quantity'):
            with self.subTest(change=change):
                state,p=fixture()
                if change=='conflict':bind(state,p,'fictional-change-conflict',-200)
                elif change=='causal':bind(state,p,'fictional-change-causal');p['comparison_review']['interpretation']='attributed_project_reduction'
                elif change=='unknown':p['comparison_review']['evidence_fit']='unverified'
                elif change=='whole':p['claim']['scope']='whole_subject'
                elif change=='date':p['comparison_review']['as_of_date']='2026-10-04'
                elif change=='documentary_baseline':
                    c=next(c for c in p['criteria'] if c['id']=='baseline');c.update(unit='1',source_result_ids=[],evidence_ids=['claim-review-evidence'])
                else:p['criteria']=[c for c in p['criteria'] if c['id']!='quantity'];p['material_selectors']['quantity_spans']=[]
                out=assess_comparison_claim(state,p)
                self.assertEqual(report(out)['claim_state'],'POTENTIALLY_MISLEADING' if change=='conflict' else 'INSUFFICIENT_EVIDENCE')

    def test_percentage_zero_baseline_is_unknown_not_zero(self):
        state,p=fixture(before=0);bind(state,p,'fictional-change-percent',-20,'%');out=assess_comparison_claim(state,p)
        self.assertEqual([m['value'] for m in proof(out)['result']['metrics']],[400])
        self.assertEqual(rows(out)['quantity']['assessment_state'],'INSUFFICIENT_EVIDENCE')
        self.assertTrue(any('zero' in g['reason'] for g in out['result']['data_gaps']))

    def test_comparison_metric_report_and_prior_leaf_tampering_blocks(self):
        initial,original=fixture()
        for change in ('metric','report','prior_leaf','period','history'):
            with self.subTest(change=change):
                state,p=copy.deepcopy(initial),copy.deepcopy(original);owner=next(r for r in state['results'] if r['id']=='inventory-comparison')
                if change=='metric':owner['metrics'][0]['uncertainty']['description']='Certain.'
                elif change=='report':
                    d=next(d for d in owner['diagnostics'] if d['code']=='INVENTORY_COMPARISON');r=json.loads(d['message']);r['limits']='Verified project reduction';d['message']=json.dumps(r)
                elif change=='prior_leaf':p['comparison_review']['prior_state']['results'][1]['metrics'][0]['uncertainty']['description']='Certain.'
                elif change=='period':p['comparison_review']['prior_state']['reporting_period']=state['reporting_period']
                else:
                    state['data_gaps']=[]
                    with self.assertRaises(ValueError):assess_comparison_claim(state,p)
                    continue
                out=assess_comparison_claim(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
                self.assertEqual(out['result']['diagnostics'][0]['code'],'CLAIM_COMPARISON_REQUIRED')

    def test_selected_percentage_and_missing_factor(self):
        state,p=fixture();bind(state,p,'fictional-change-percent',-20,'%');out=assess_comparison_claim(state,p)
        self.assertEqual(rows(out)['quantity']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        state['emission_factors']=[];out=assess_comparison_claim(state,p)
        self.assertEqual(out['result']['status'],'blocked');self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_explicit_decrease_magnitude_preserves_positive_original_number_and_signed_source(self):
        state,p=fixture();bind(state,p,'fictional-change-decrease',100)
        p['comparison_review']['quantity_interpretation']='decrease_magnitude'
        out=assess_comparison_claim(state,p)
        self.assertEqual(rows(out)['quantity']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(rows(out)['quantity']['criterion']['quantity']['expected_value'],100)
        self.assertEqual(proof(out)['result']['metrics'][0]['value'],-100)
        p['comparison_review']['quantity_interpretation']='unknown'
        self.assertEqual(report(assess_comparison_claim(state,p))['claim_state'],'INSUFFICIENT_EVIDENCE')
        state,p=fixture(before=0);bind(state,p,'fictional-change-decrease',100)
        p['comparison_review']['quantity_interpretation']='decrease_magnitude'
        self.assertEqual(report(assess_comparison_claim(state,p))['claim_state'],'POTENTIALLY_MISLEADING')

    def test_actual_cli_full_output_matches_helper(self):
        state,p=fixture();request={'contract_version':'0.1.0','skill':'assess-comparison-claim-evidence','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json';path.write_text(json.dumps(request),encoding='utf-8')
            run=subprocess.run([sys.executable,'-m','scripts.run_claims',str(path)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr);self.assertEqual(json.loads(run.stdout),assess_comparison_claim(state,p))
