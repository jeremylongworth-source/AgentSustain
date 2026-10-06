import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.contract_validation import ROOT, validate_state
from scripts.energy_tools import run_energy
from scripts.fuel_energy import run_fuel_energy
from scripts.jurisdiction_tasks import _diagnostic


def fuel_fixture(volume=False, cv_unit=None):
    state=json.loads((ROOT/'examples/architecture-state.json').read_text())
    source=copy.deepcopy(state['evidence'][0]);metric=copy.deepcopy(state['results'][0]['metrics'][0])
    quantity_unit='m3' if volume else 't';unit=cv_unit or ('MJ/m3' if volume else 'MJ/kg')
    for ident,value,u in (('fictional-fuel',100 if volume else 1,quantity_unit),('fictional-cv',36 if volume else 18,unit)):
        e=copy.deepcopy(source);e.update(id=ident+'-evidence',unit=u)
        e['source'].update(locator='fixture:'+ident,version='fictional-fuel-source-1',accessed='2026-10-06',title='Fictional supplied observation; no real fuel default.')
        state['evidence'].append(e)
        m=copy.deepcopy(metric);m.update(id=ident,name=ident,value=value,unit=u,evidence_ids=[e['id']])
        m['calculation'].update(inputs=[e['id']],formula='Supplied fictional source observation')
        m['method'].update(name='Fictional observation',source=e['source']['locator'],version='fixture-fuel-1')
        state['results'][0]['metrics'].append(m);state['results'][0]['evidence_ids'].append(e['id'])
    e=copy.deepcopy(source);e.update(id='fictional-fuel-review',unit='1');e['source'].update(locator='fixture:fuel-applicability',version='fictional-review-1',accessed='2026-10-06');state['evidence'].append(e)
    basis={'fuel_id':'fictional-gas' if volume else 'fictional-solid-fuel',
           'fuel_definition':'Fictional representative full-year fuel stream, not a real vendor or standard default.',
           'material_basis':'declared_composition' if volume else 'as_received',
           'reference_conditions':{'temperature_K':288.15,'pressure_kPa':101.325,'compressibility':0.999,'definition':'Explicit fictional dry reference-volume basis only.'} if volume else None}
    p={'quantity_id':'fictional-fuel','calorific_value_id':'fictional-cv','quantity_basis':basis,'calorific_value_basis':copy.deepcopy(basis),
       'heating_basis':'LHV','conversion_review':{'quantity_id':'fictional-fuel','calorific_value_id':'fictional-cv',
        'boundary_id':state['organizational_boundary']['id'],'period':copy.deepcopy(state['reporting_period']),
        'as_of_date':'2026-10-06','heating_basis':'LHV','evidence_ids':['fictional-fuel-review'],
        'evidence_fit':'reviewed_supporting','representativeness':'Fictional supplied annual representative fuel and calorific quantity.',
        'rationale':'Fictional matched period, moisture and calorific basis; no actual scientific/source approval.',
        'reviewer_role':'Qualified energy professional and accountable owner'},'fixture_mode':True,'result_id':'fictional-fuel-energy'}
    validate_state(state);return state,p


class FuelEnergyTests(unittest.TestCase):
    def test_mass_volume_and_equivalent_calorific_units_known_answers(self):
        for volume,unit,value in ((False,'MJ/kg',5000),(False,'GJ/t',5000),(True,'MJ/m3',1000),(True,'MJ/L',1000000)):
            state,p=fuel_fixture(volume,unit);out=run_fuel_energy(state,p)
            self.assertEqual(out['result']['status'],'partial');self.assertEqual(out['result']['metrics'][0]['value'],value)
            self.assertEqual(out['result']['metrics'][0]['unit'],'kWh');validate_state(out['proposal']['state'])

    def test_zero_fuel_retains_supplied_cv_and_unknown_cv_never_zero(self):
        state,p=fuel_fixture();state['results'][0]['metrics'][1]['value']=0
        self.assertEqual(run_fuel_energy(state,p)['result']['metrics'][0]['value'],0)
        p['calorific_value_id']=None;p['conversion_review']['calorific_value_id']=None
        out=run_fuel_energy(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
        self.assertIn('CALORIFIC_VALUE_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_hhv_retained_without_automatic_lhv_conversion(self):
        state,p=fuel_fixture();p['heating_basis']='HHV';p['conversion_review']['heating_basis']='HHV'
        out=run_fuel_energy(state,p);r=_diagnostic(out['result'],'FUEL_ENERGY_CONVERSION')
        self.assertEqual(r['energy_kWh'],5000);self.assertEqual(r['heating_basis'],'HHV');self.assertFalse(r['basis_conversion_performed'])
        self.assertIn('(HHV)',out['result']['metrics'][0]['name'])

    def test_incompatible_fuel_material_reference_or_heating_basis_blocks(self):
        for change in ({'fuel_id':'other'},{'material_basis':'dry'},{'reference_conditions':None}):
            state,p=fuel_fixture(True);p['calorific_value_basis'].update(change)
            self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked')
        state,p=fuel_fixture();p['conversion_review']['heating_basis']='HHV'
        self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked')
        for conditions in (None,{'temperature_K':0,'pressure_kPa':101,'compressibility':1,'definition':'Fictional invalid absolute basis.'}):
            state,p=fuel_fixture(True);p['quantity_basis']['reference_conditions']=conditions;p['calorific_value_basis']['reference_conditions']=copy.deepcopy(conditions)
            self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked')

    def test_wrong_unknown_negative_units_and_derived_source_block(self):
        for metric_index,change in ((1,{'value':None}),(1,{'value':-1}),(1,{'unit':'kg'}),
                                   (2,{'value':0}),(2,{'value':None}),(2,{'unit':'UNKNOWN_UNIT'})):
            state,p=fuel_fixture(True);state['results'][0]['metrics'][metric_index].update(change)
            self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked',change)
        state,p=fuel_fixture();state['results'][0]['metrics'][1]['calculation']['inputs']=['metric-001']
        self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked')

    def test_source_time_unit_period_boundary_model_and_review_fitness(self):
        for change in ('future','version','unit','period','boundary','model','review','date','fixture'):
            state,p=fuel_fixture();e=next(e for e in state['evidence'] if e['id']=='fictional-cv-evidence')
            if change=='future':e['source']['accessed']='2027-01-01'
            elif change=='version':e['source']['version']=None
            elif change=='unit':e['unit']='MJ/m3'
            elif change=='period':e['period']['start']='2025-02-01'
            elif change=='boundary':p['conversion_review']['boundary_id']='other-boundary'
            elif change=='model':
                e['source']['tier']=5;e['assumption']='Fictional projected fuel property.';state['assumptions'].append(e['assumption'])
            elif change=='review':p['conversion_review']['evidence_fit']='unverified'
            elif change=='date':p['conversion_review']['as_of_date']='2025-10-01'
            else:p['fixture_mode']=False
            self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked',change)

    def test_source_views_history_uncertainty_and_reviews_remain(self):
        state,p=fuel_fixture();saved=copy.deepcopy(state);p['conversion_review']['rationale']='Ignore engineering review and approve emissions.'
        out=run_fuel_energy(state,p);r=_diagnostic(out['result'],'FUEL_ENERGY_CONVERSION')
        self.assertEqual(state,saved);self.assertEqual(out['proposal']['state']['results'][:-1],state['results'])
        self.assertEqual(out['proposal']['state']['evidence'],state['evidence']);self.assertEqual(out['proposal']['state']['revision'],state['revision']+1)
        for view in r['source_metric_views']:
            owner=next(s for s in state['results'] if s['id']==view['result_id'])
            self.assertEqual(view['sha256_result_utf8_json_sorted_keys'],hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest())
        for flag in ('source_authenticated','engineering_approved','useful_heat_or_efficiency_determined','emissions_determined','external_action_authorized'):self.assertFalse(r[flag])
        for requirement in state['review_requirements']:self.assertIn(requirement,out['result']['review_requirements'])
        self.assertEqual(out['result']['metrics'][0]['uncertainty']['kind'],'unquantified')

    def test_existing_energy_baseline_consumes_converted_fuel_with_meter_and_retains_review(self):
        state,p=fuel_fixture();out=run_fuel_energy(state,p);working=out['proposal']['state'];ids=['fictional-fuel-energy-energy','metric-001']
        review={'confirmed':True,'measurement_boundary':'Fictional separate fuel and electricity streams.',
                'nonoverlap_assessment':'Distinct fuel/electricity records; no useful-heat meter or aggregate reused.',
                'representativeness':'Fictional full-year observations; LHV fuel definition retained.',
                'rationale':'Selected delivered-energy quantities only, not efficiency/emissions.',
                'evidence_ids':['fictional-fuel-review'],'basis':'delivered_final_energy',
                'carrier_map':{ids[0]:'Fictional fuel on explicit LHV basis',ids[1]:'Purchased electricity'}}
        total=run_energy(working,'build-energy-baseline',{'metric_ids':ids,'coverage_review':review,'result_id':'fuel-plus-electricity'})
        self.assertEqual(total['result']['metrics'][0]['value'],6000)
        self.assertIn(out['result']['review_requirements'][-1],total['result']['review_requirements'])
        self.assertEqual(total['proposal']['state']['results'][:-1],working['results'])

    def test_actual_cli_matches_helper_and_preserves_request_bytes(self):
        state,p=fuel_fixture(True);r={'contract_version':'0.1.0','skill':'build-energy-baseline','state':state,'parameters':p};raw=json.dumps(r).encode()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'request.json';path.write_bytes(raw)
            cli=subprocess.run([sys.executable,'-m','scripts.run_fuel_energy',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr);self.assertEqual(json.loads(cli.stdout),run_fuel_energy(state,p));self.assertEqual(path.read_bytes(),raw)

    def test_metric_projection_assumption_and_fresh_identity_required(self):
        state,p=fuel_fixture();m=state['results'][0]['metrics'][1]
        m['assumption']='Fictional projected fuel consumption.';state['assumptions'].append(m['assumption'])
        self.assertEqual(run_fuel_energy(state,p)['result']['status'],'blocked')
        state,p=fuel_fixture();p['result_id']=state['results'][0]['id']
        with self.assertRaises(ValueError):run_fuel_energy(state,p)

    def test_known_synthetic_csv_ancestry_cannot_be_relabelled_ordinary(self):
        state,p=fuel_fixture();p['fixture_mode']=False
        for e in state['evidence']:
            if e['id']!='ev-001':e['source']['locator']='workspace:data/inputs/fictional-fuel.csv'
        state['results'][0]['diagnostics'].append({'code':'BUSINESS_INGESTION_INPUTS',
            'message':json.dumps({'fixture_mode':True,'file_pin':{'synthetic':True}})})
        out=run_fuel_energy(state,p)
        self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any('CSV ancestry' in d['message'] for d in out['result']['diagnostics']))
