import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from jsonschema.exceptions import ValidationError

from scripts.claim_inventory import assess_inventory_claim
from scripts.claims_review import BASE
from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.ghg_inventory import build_inventory
from scripts.scope_accounting import compose_scope
from scripts.state_proposal import propose
from tests.test_claims_review import report, rows
from tests.test_scope_accounting import scope_fixture


def material_args(state, p, name, text, value=None):
    raw=(ROOT/'standards/claims/materials'/ (name+'.json')).read_bytes();m=json.loads(raw)
    e=next(e for e in state['evidence'] if e['id']==p['claim']['material_evidence_ids'][0])
    e['source'].update(locator='workspace:standards/claims/materials/'+name+'.json',version=m['version'])
    p['claim']['text']=text
    def span(part):
        start=m['text'].index(part);return {'start':start,'end':start+len(part)}
    p['material_pin']={'path':name+'.json','sha256':hashlib.sha256(raw).hexdigest()}
    p['material_selectors']={'claim_span':span(text),'qualification_spans':[{'text':q,'span':span(q)} for q in p['claim']['qualifications']],
        'quantity_spans':[] if value is None else [{'criterion_id':'quantity','value_span':span(str(value)),'unit_span':span('kg CO2e')}]}


def fixture(partial=False, neutral=False):
    state,sources,components,coverage=scope_fixture()
    if not partial:
        raw=copy.deepcopy(state['results'][0]);raw['id']='direct-activity-result';raw['metrics'][0].update(id='direct-activity',name='Fictional fuel heat input',value=100,evidence_ids=['direct-activity-evidence'])
        raw['metrics'][0]['calculation']['inputs']=['direct-activity-evidence'];raw['evidence_ids']=['direct-activity-evidence']
        raw['assumptions']=list(state['assumptions']);raw['data_gaps']=copy.deepcopy(state['data_gaps']);raw['review_requirements']=copy.deepcopy(state['review_requirements'])
        e=copy.deepcopy(state['evidence'][0]);e['id']='direct-activity-evidence';e['source']['locator']='fixture:direct-activity'
        state=propose(state,raw,'Add separate fictional fuel input before inventory composition',[e])['state']
        component=copy.deepcopy(components[0]);component['policy']['source_review']['activity_id']='direct-activity'
        component['policy'].update(activity_kind='direct',scope_basis='direct');component.update(metric_id='direct-co2e-metric',basis='direct',source_id='direct-source')
        source=copy.deepcopy(sources[0]);source.update(id='direct-source',scope='scope_1',kind='direct',activity_id='direct-activity',evidence_ids=[e['id']])
        state=calculate_result(state,'direct-activity',component['factor_id'],component['policy'],'direct-co2e',True)['proposal']['state']
        state=compose_scope(state,'calculate-scope-1',[source],[component],coverage,'direct-scope',True)['proposal']['state']
    state=compose_scope(state,'calculate-location-based-scope-2',sources,components,coverage,'energy-scope',True)['proposal']['state']
    screening=[{'category':i,'status':'not_applicable','evidence_ids':['ev-001'],'rationale':'Fictional explicitly reviewed non-applicability; no actual organization assertion.'} for i in range(1,16)]
    state=build_inventory(state,None if partial else 'direct-scope','energy-scope',[],screening,coverage,'claim-inventory',True)['proposal']['state']
    e=copy.deepcopy(state['evidence'][0]);e.update(id='claim-review-evidence',unit='1');e['source'].update(locator='fixture:inventory-claim-coverage',version='fictional-review-1');state['evidence'].append(e)
    m=copy.deepcopy(e);m.update(id='inventory-claim-material',period={'start':'2026-09-01','end':'2026-10-05'});state['evidence'].append(m)
    qualification='Fictional scope/category coverage; not independently authenticated.'
    claim={'id':'fictional-inventory-claim','text':'pending material selection','kind':'carbon_neutral' if neutral else 'quantified',
        'subject_kind':'organization','subject_id':state['organization']['id'],'scope':'whole_subject','period':copy.deepcopy(state['reporting_period']),
        'boundary_id':state['organizational_boundary']['id'],'material_evidence_ids':[m['id']],'representation_dates':['2026-09-01'],
        'channel':'Fictional draft statement','audience':'Fictional stakeholders','purpose':'Fictional claim evaluation','qualifications':[qualification]}
    criteria=[]
    for ident in sorted(BASE|({'inventory','reductions','credits','residuals'} if neutral else {'inventory','quantity'})):
        c={'id':ident,'assertion':'Fictional '+ident+' observation','boundary_id':claim['boundary_id'],'period':copy.deepcopy(claim['period']),
            'unit':'1','evidence_ids':[e['id']],'source_result_ids':[],'evidence_fit':'reviewed_supporting','verdict':'supports','quantity':None,
            'qualifications':[],'qualification_visible':False,'rationale':'Fictional reviewer record, not authenticated approval.'}
        if ident in {'inventory','quantity'}:
            c.update(unit='kg CO2e',evidence_ids=['ev-001'],source_result_ids=['claim-inventory'],verdict='qualified',qualifications=[qualification],qualification_visible=True)
        if ident=='quantity':c['quantity']={'metric_id':'claim-inventory-metric','expected_value':550}
        criteria.append(c)
    p={'claim':claim,'classification_review':{'kind':claim['kind'],'evidence_ids':[m['id']],'evidence_fit':'reviewed_supporting','rationale':'Fictional original statement interpretation.','reviewer_role':'Qualified claim reviewer'},
        'criteria':criteria,'claim_review':{'boundary_id':claim['boundary_id'],'period':copy.deepcopy(claim['period']),'as_of_date':'2026-10-05','evidence_ids':[e['id']],
            'evidence_fit':'reviewed_supporting','scope':'Fictional organization inventory claim','rationale':'Fictional scope review only.','reviewer_role':'Qualified claim reviewer'},
        'fixture_mode':True,'result_id':'inventory-claim-review','inventory_review':{'inventory_result_id':'claim-inventory','boundary_id':claim['boundary_id'],'period':copy.deepcopy(claim['period']),
            'as_of_date':'2026-10-05','subject_id':state['organization']['id'],'coverage':'whole_subject','facility_ids':list(state['organizational_boundary']['facility_ids']),
            'coverage_evidence_ids':[e['id']],'evidence_fit':'reviewed_supporting','scope_2_method':'location','gwp_basis':coverage['gwp_basis'],
            'rationale':'Fictional source/organizational scope assessment only.','gas_coverage_assessment':'Declared fictional source gas rosters reviewed; no actual organization completeness established.',
            'reviewer_role':'Qualified inventory/source reviewer'}}
    material_args(state,p,'fictional-neutrality' if neutral else 'fictional-inventory',
        'Our organization is carbon neutral.' if neutral else 'The declared organization inventory was 550 kg CO2e in 2025.',None if neutral else 550)
    return state,p


def proof(out):return json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='CLAIM_INVENTORY_SOURCE_CHECK'))


class ClaimInventoryTests(unittest.TestCase):
    def test_whole_declared_inventory_full_replay_remains_qualified_and_professional(self):
        state,p=fixture();before=copy.deepcopy(state);out=assess_inventory_claim(state,p);r=report(out);check=proof(out)
        self.assertEqual(check['result']['metrics'][0]['value'],550)
        self.assertTrue(check['declared_scope_coverage_reproduced']);self.assertTrue(check['source_fit'])
        self.assertEqual(len(check['source_accounts']),2);self.assertEqual(len(check['leaf_results']),2)
        self.assertEqual(rows(out)['inventory']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(rows(out)['quantity']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(r['claim_state'],'PROFESSIONAL_REVIEW_REQUIRED');self.assertEqual(r['execution_contract'],'claim-evidence-0.3.0')
        for key in ('external_completeness_verified','source_authenticity_verified','net_emissions_or_neutrality_determined','publication_authorized'):self.assertFalse(check[key])
        self.assertEqual(out['result']['metrics'],[]);self.assertEqual(state,before);validate_state(out['proposal']['state'])
        for key in ('results','evidence','data_gaps','review_requirements'):
            for item in state[key]:self.assertIn(item,out['proposal']['state'][key])

    def test_partial_inventory_cannot_support_whole_subject_even_with_favourable_observations(self):
        state,p=fixture(partial=True);out=assess_inventory_claim(state,p)
        self.assertEqual(proof(out)['result']['metrics'][0]['value'],500)
        self.assertFalse(proof(out)['declared_scope_coverage_reproduced'])
        self.assertEqual(report(out)['claim_state'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(rows(out)['inventory']['assessment_state'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(rows(out)['quantity']['assessment_state'],'INSUFFICIENT_EVIDENCE')

    def test_selected_partial_subtotal_is_qualified_without_completeness_promotion(self):
        state,p=fixture(partial=True);p['claim']['scope']='selected_sources';p['inventory_review']['coverage']='selected_sources'
        p['criteria']=[c for c in p['criteria'] if c['id']!='inventory'];next(c for c in p['criteria'] if c['id']=='quantity')['quantity']['expected_value']=500
        material_args(state,p,'fictional-partial-inventory','The selected electricity inventory subtotal was 500 kg CO2e in 2025.',500)
        out=assess_inventory_claim(state,p)
        self.assertFalse(proof(out)['declared_scope_coverage_reproduced'])
        self.assertEqual(rows(out)['quantity']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(report(out)['claim_state'],'PROFESSIONAL_REVIEW_REQUIRED')

    def test_neutrality_requires_distinct_reduction_credit_and_residual_methods(self):
        state,p=fixture(neutral=True);out=assess_inventory_claim(state,p)
        self.assertTrue(proof(out)['declared_scope_coverage_reproduced'])
        self.assertEqual(rows(out)['inventory']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        for name in ('reductions','credits','residuals'):self.assertEqual(rows(out)[name]['assessment_state'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(report(out)['claim_state'],'INSUFFICIENT_EVIDENCE');self.assertFalse(report(out)['publication_authorized'])

    def test_actual_bound_number_can_conflict_with_full_inventory(self):
        state,p=fixture();next(c for c in p['criteria'] if c['id']=='quantity')['quantity']['expected_value']=999
        material_args(state,p,'fictional-inventory-conflict','The declared organization inventory was 999 kg CO2e in 2025.',999)
        out=assess_inventory_claim(state,p)
        self.assertEqual(report(out)['claim_state'],'POTENTIALLY_MISLEADING');self.assertTrue(rows(out)['quantity']['quantity_mismatch'])

    def test_known_partial_subtotal_retains_unaccepted_component_without_inventing_zero(self):
        state,p=fixture(partial=True);old=next(r for r in state['results'] if r['id']=='energy-scope')
        method=json.loads(next(d['message'] for d in old['diagnostics'] if d['code']=='SCOPE_METHOD'))
        missing_source=copy.deepcopy(method['sources'][0]);missing_source.update(id='unavailable-source',activity_id='unavailable-activity')
        method['sources'].append(missing_source)
        missing=copy.deepcopy(method['components'][0]);missing.update(metric_id='unavailable-component',source_id='unavailable-source')
        method['components'].append(missing)
        state=compose_scope(state,old['skill'],method['sources'],method['components'],method['coverage_review'],'partial-energy-with-gap',True)['proposal']['state']
        inv=next(r for r in state['results'] if r['id']=='claim-inventory')
        selection=json.loads(next(d['message'] for d in inv['diagnostics'] if d['code']=='INVENTORY_SELECTION'))
        state=build_inventory(state,None,'partial-energy-with-gap',[],selection['category_screening'],selection['coverage_review'],'partial-inventory-with-gap',True)['proposal']['state']
        p['inventory_review'].update(inventory_result_id='partial-inventory-with-gap',coverage='selected_sources');p['claim']['scope']='selected_sources'
        p['criteria']=[c for c in p['criteria'] if c['id']!='inventory'];q=next(c for c in p['criteria'] if c['id']=='quantity')
        q.update(source_result_ids=['partial-inventory-with-gap']);q['quantity'].update(metric_id='partial-inventory-with-gap-metric',expected_value=500)
        material_args(state,p,'fictional-partial-inventory','The selected electricity inventory subtotal was 500 kg CO2e in 2025.',500)
        out=assess_inventory_claim(state,p)
        self.assertEqual(proof(out)['unsupported_component_snapshots'][0]['component']['metric_id'],'unavailable-component')
        self.assertFalse(proof(out)['declared_scope_coverage_reproduced']);self.assertEqual(rows(out)['quantity']['assessment_state'],'SUPPORTED_WITH_QUALIFICATION')
        self.assertEqual(proof(out)['result']['metrics'][0]['value'],500)
        for gap in state['data_gaps']:self.assertIn(gap,out['proposal']['state']['data_gaps'])

    def test_inventory_account_leaf_uncertainty_report_and_factor_tampering_blocked(self):
        initial,original=fixture()
        for change in ('inventory_metric','inventory_report','scope_uncertainty','scope_report','leaf_uncertainty','leaf_inputs','blocked_leaf','factor','missing_factor'):
            with self.subTest(change=change):
                state,p=copy.deepcopy(initial),copy.deepcopy(original);results={r['id']:r for r in state['results']}
                if change=='inventory_metric':results['claim-inventory']['metrics'][0]['value']=999
                elif change=='inventory_report':
                    d=next(d for d in results['claim-inventory']['diagnostics'] if d['code']=='INVENTORY_SELECTION');r=json.loads(d['message']);r['limits']='Authenticated.';d['message']=json.dumps(r)
                elif change=='scope_uncertainty':results['energy-scope']['metrics'][0]['uncertainty']['description']='Certain.'
                elif change=='scope_report':
                    d=next(d for d in results['energy-scope']['diagnostics'] if d['code']=='SCOPE_METHOD');r=json.loads(d['message']);r['limitations']='Approved.';d['message']=json.dumps(r)
                elif change=='leaf_uncertainty':results['component']['metrics'][0]['uncertainty']['description']='Certain.'
                elif change=='leaf_inputs':results['component']['metrics'][0]['calculation']['inputs'].append('claim-review-evidence')
                elif change=='blocked_leaf':
                    results['component']['status']='blocked'
                    with self.assertRaises(ValidationError):assess_inventory_claim(state,p)
                    continue
                elif change=='factor':state['emission_factors'][0]['value']=99
                else:state['emission_factors']=[]
                out=assess_inventory_claim(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
                self.assertEqual(out['result']['diagnostics'][0]['code'],'CLAIM_INVENTORY_REQUIRED');validate_state(out['proposal']['state'])
                if change in ('factor','missing_factor'):self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_unknown_coverage_facility_subject_method_period_date_and_synthetic_context(self):
        initial,original=fixture()
        for change in ('coverage','fitness','facility','subject','method','basis','period','date','claim_facility','fixture_mode','missing_inventory_criterion'):
            with self.subTest(change=change):
                state,p=copy.deepcopy(initial),copy.deepcopy(original);v=p['inventory_review']
                if change=='coverage':v['coverage']='unknown'
                elif change=='fitness':v['evidence_fit']='unverified'
                elif change=='facility':v['facility_ids']=[]
                elif change=='subject':v['subject_id']='other-organization'
                elif change=='method':v['scope_2_method']='market'
                elif change=='basis':v['gwp_basis']='other basis'
                elif change=='period':v['period']={'start':'2024-01-01','end':'2024-12-31'}
                elif change=='date':v['as_of_date']='2026-10-04'
                elif change=='claim_facility':p['claim'].update(subject_kind='facility',subject_id='facility-001')
                elif change=='fixture_mode':p['fixture_mode']=False
                else:p['criteria']=[c for c in p['criteria'] if c['id']!='inventory']
                out=assess_inventory_claim(state,p);self.assertEqual(out['result']['metrics'],[])
                if out['result']['status']!='blocked':self.assertEqual(report(out)['claim_state'],'INSUFFICIENT_EVIDENCE')

    def test_actual_cli_complete_output_equals_helper(self):
        state,p=fixture();request={'contract_version':'0.1.0','skill':'assess-inventory-claim-evidence','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json';path.write_text(json.dumps(request),encoding='utf-8')
            run=subprocess.run([sys.executable,'-m','scripts.run_claims',str(path)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr);self.assertEqual(json.loads(run.stdout),assess_inventory_claim(state,p))
