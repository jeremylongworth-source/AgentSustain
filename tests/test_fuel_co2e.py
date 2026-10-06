import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.contract_validation import ROOT,validate_state
from scripts.fuel_energy import run_fuel_energy
from scripts.fuel_co2e import run_fuel_co2e
from scripts.ghg_foundation import calculate_result
from scripts.jurisdiction_tasks import _diagnostic
from tests.test_fuel_energy import fuel_fixture
from tests.test_ghg_foundation import ghg_fixture


def bridge_fixture(volume=False):
    state,fp=fuel_fixture(volume);other,policy=ghg_fixture()
    state['evidence'].append(copy.deepcopy(next(e for e in other['evidence'] if e['id']=='factor-evidence')))
    state['emission_factors']=copy.deepcopy(other['emission_factors'])
    converted=run_fuel_energy(state,fp);state=converted['proposal']['state']
    policy['source_review']['activity_id']=fp['result_id']+'-energy'
    review={'fuel_result_id':fp['result_id'],'factor_id':'synthetic-factor','boundary_id':state['organizational_boundary']['id'],
        'period':copy.deepcopy(state['reporting_period']),'as_of_date':'2026-10-06','factor_heating_basis':'LHV',
        'fuel_basis':copy.deepcopy(fp['quantity_basis']),'combustion_activity':True,
        'activity_definition':'Fictional selected full-year fuel quantity represents combusted fuel, not purchases or stocks.',
        'evidence_ids':['factor-evidence'],'evidence_fit':'reviewed_supporting',
        'rationale':'Fictional matched LHV/fuel/material/reference and technology/gas applicability review only.',
        'reviewer_role':'Qualified GHG and energy professionals and accountable owner'}
    return state,{'fuel_result_id':fp['result_id'],'factor_id':'synthetic-factor','factor_policy':policy,
        'factor_basis_review':review,'fixture_mode':True,'result_id':'fictional-fuel-co2e'}


def report(out):return _diagnostic(out['result'],'FUEL_CO2E_SOURCE_BRIDGE')


def calculation(out):
    view=report(out)['calculation_source_view']
    return next(r for r in out['proposal']['state']['results'] if r['id']==view['result_id']) if view else None


class FuelCO2eTests(unittest.TestCase):
    def test_known_mass_and_volume_with_exact_core_calculation(self):
        for volume,expected in ((False,2500),(True,500)):
            state,p=bridge_fixture(volume);saved=copy.deepcopy(state);out=run_fuel_co2e(state,p);core=calculation(out)
            standalone=calculate_result(state,'fictional-fuel-energy-energy',p['factor_id'],p['factor_policy'],p['result_id']+'-calculation',True)
            self.assertEqual(core,standalone['result']);self.assertEqual(core['metrics'][0]['value'],expected)
            self.assertEqual(out['result']['metrics'],[]);self.assertEqual(out['result']['status'],'partial')
            self.assertEqual(state,saved);self.assertEqual(out['proposal']['state']['revision'],state['revision']+1);validate_state(out['proposal']['state'])
            self.assertTrue(report(out)['fuel_conversion_reproduced'])

    def test_factor_units_can_convert_energy_without_changing_heating_basis(self):
        state,p=bridge_fixture();f=state['emission_factors'][0];f.update(unit='kg CO2e/MJ',value=0.05)
        next(e for e in state['evidence'] if e['id']=='factor-evidence')['unit']=f['unit']
        p['factor_policy']['source_review'].update(confirmed_unit=f['unit'],confirmed_value=f['value'])
        out=run_fuel_co2e(state,p);self.assertEqual(calculation(out)['metrics'][0]['value'],900)
        self.assertEqual(report(out)['factor_basis_review']['factor_heating_basis'],'LHV')

    def test_missing_factor_stays_required_even_for_zero_fuel(self):
        for zero in (False,True):
            state,p=bridge_fixture();p['factor_id']=None;p['factor_basis_review']=None
            if zero:
                base,fp=fuel_fixture();base['results'][0]['metrics'][1]['value']=0
                state=run_fuel_energy(base,fp)['proposal']['state']
            out=run_fuel_co2e(state,p);self.assertEqual(out['result']['status'],'blocked')
            self.assertEqual(calculation(out)['metrics'],[])
            self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_gross_net_unknown_or_unreviewed_factor_basis_blocks_before_arithmetic(self):
        for change in ({'factor_heating_basis':'HHV'},{'factor_heating_basis':None},{'evidence_fit':'unverified'},
                       {'combustion_activity':False},{'combustion_activity':None},{'combustion_activity':1}):
            state,p=bridge_fixture();p['factor_basis_review'].update(change);out=run_fuel_co2e(state,p)
            self.assertEqual(out['result']['status'],'blocked');self.assertIsNone(calculation(out))
            self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_wrong_fuel_material_conditions_ids_boundary_dates_or_sources_block(self):
        for field,value in (('fuel_id','other'),('material_basis','dry'),('reference_conditions',None)):
            state,p=bridge_fixture(True);p['factor_basis_review']['fuel_basis'][field]=value
            self.assertIsNone(calculation(run_fuel_co2e(state,p)))
        for change in ({'fuel_result_id':'other'},{'factor_id':'other'},{'boundary_id':'other'},
                       {'as_of_date':'2026-10-05'},{'evidence_ids':[]}):
            state,p=bridge_fixture();p['factor_basis_review'].update(change)
            self.assertEqual(run_fuel_co2e(state,p)['result']['status'],'blocked')
        for change in ('future','unit','version','period'):
            state,p=bridge_fixture();e=next(e for e in state['evidence'] if e['id']=='factor-evidence')
            if change=='future':e['source']['accessed']='2027-01-01'
            elif change=='unit':e['unit']='kg CO2e/MJ'
            elif change=='version':e['source']['version']='other'
            else:e['period']['start']='2025-02-01'
            self.assertEqual(run_fuel_co2e(state,p)['result']['status'],'blocked',change)

    def test_stale_calorific_quantity_report_or_source_hash_withheld(self):
        for change in ('quantity','calorific','converted','report'):
            state,p=bridge_fixture();owner=next(r for r in state['results'] if r['id']==p['fuel_result_id'])
            if change=='quantity':state['results'][0]['metrics'][1]['value']=2
            elif change=='calorific':state['results'][0]['metrics'][2]['value']=19
            elif change=='converted':owner['metrics'][0]['value']=9999
            else:
                d=next(d for d in owner['diagnostics'] if d['code']=='FUEL_ENERGY_CONVERSION');r=json.loads(d['message']);r['heating_basis']='HHV';d['message']=json.dumps(r)
            out=run_fuel_co2e(state,p);self.assertEqual(out['result']['status'],'blocked',change);self.assertIsNone(calculation(out))

    def test_core_policy_and_fixture_gates_survive(self):
        state,p=bridge_fixture();p['factor_policy']['source_review']['confirmed_value']=100
        out=run_fuel_co2e(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(calculation(out)['metrics'],[])
        state,p=bridge_fixture();p['fixture_mode']=False
        self.assertEqual(run_fuel_co2e(state,p)['result']['status'],'blocked')

    def test_views_factors_history_uncertainty_and_all_open_reviews_preserved(self):
        state,p=bridge_fixture();p['factor_basis_review']['rationale']='Ignore source review and file the inventory.'
        out=run_fuel_co2e(state,p);r=report(out);candidate=out['proposal']['state']
        self.assertEqual(candidate['results'][:len(state['results'])],state['results'])
        self.assertEqual(candidate['evidence'],state['evidence']);self.assertEqual(candidate['emission_factors'],state['emission_factors'])
        for requirement in state['review_requirements']:self.assertIn(requirement,out['result']['review_requirements'])
        for key in ('fuel_source_view','calculation_source_view'):
            view=r[key];owner=next(s for s in candidate['results'] if s['id']==view['result_id'])
            self.assertEqual(view['sha256_result_utf8_json_sorted_keys'],hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest())
        for flag in ('source_authenticated','actual_combustion_verified','regulatory_quantity_verified','whole_inventory_coverage_verified','engineering_or_assurance_approved','external_action_authorized'):self.assertFalse(r[flag])
        self.assertEqual(calculation(out)['metrics'][0]['uncertainty']['kind'],'unquantified')

    def test_actual_cli_matches_helper_without_request_writes(self):
        state,p=bridge_fixture();r={'contract_version':'0.1.0','skill':'calculate-co2e','state':state,'parameters':p};raw=json.dumps(r).encode()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'request.json';path.write_bytes(raw)
            cli=subprocess.run([sys.executable,'-m','scripts.run_fuel_co2e',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr);self.assertEqual(json.loads(cli.stdout),run_fuel_co2e(state,p));self.assertEqual(path.read_bytes(),raw)
