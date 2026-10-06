import copy
import json
import unittest
from scripts.contract_validation import ROOT,validate_state
from scripts.business_ingestion import ingest_business_csv
from scripts.fuel_energy import run_fuel_energy
from scripts.manager_workflow import run_manager
from scripts.jurisdiction_tasks import _diagnostic


def food_fixture():
    request=json.loads((ROOT/'examples/food-manufacturer-ingestion-v2.json').read_text())
    normalized=ingest_business_csv(request['state'],request['parameters']);state=normalized['proposal']['state']
    for p in json.loads((ROOT/'examples/food-manufacturer-fuel-conversion-requests.json').read_text())['steps']:
        out=run_fuel_energy(state,p)
        if out['result']['status']!='partial':raise AssertionError('Supplied source conversion did not reproduce.')
        state=out['proposal']['state']
    manager=json.loads((ROOT/'examples/food-manufacturer-manager-request.json').read_text())
    if state['results']!=manager['state']['results'] or state['evidence']!=manager['state']['evidence'][:-1]:
        raise AssertionError('Exact source/conversion candidate differs from the manager input.')
    state['evidence'].append(copy.deepcopy(manager['state']['evidence'][-1]))
    state['emission_factors']=copy.deepcopy(manager['state']['emission_factors'])
    return state,manager['parameters']


class FoodManufacturerTests(unittest.TestCase):
    def test_required_food_source_and_complete_selected_manager_sequence(self):
        state,p=food_fixture();original=copy.deepcopy(state);out=run_manager(state,p);final=out['proposal']['state'];results={r['id']:r for r in final['results']}
        self.assertEqual(len(state['facilities']),2)
        metrics={m['id']:m for r in state['results'] for m in r['metrics']}
        self.assertEqual(metrics['food-employees']['value'],150)
        self.assertIsNone(metrics['food-south-refrigerant']['value'])
        self.assertEqual(sum(metrics['food-'+site+'-'+kind]['value'] for site in ('north','south') for kind in ('packaging','ingredients')),227000)
        self.assertEqual(results['ops-materials']['metrics'][0]['value'],209000)
        expected={'ops-energy':430000,'ops-water':3200,'ops-waste':3400,'ops-finance':0,'operations-inventory':75000}
        for ident,value in expected.items():self.assertEqual(results[ident]['metrics'][0]['value'],value,ident)
        self.assertAlmostEqual(results['strategy-target']['metrics'][0]['value'],12.285714285714286)
        self.assertEqual(results['strategy-target']['metrics'][0]['unit'],'kWh/count')
        plan=_diagnostic(out['result'],'ORGANIZATION_MANAGER')
        self.assertEqual(len(plan['stages']),8);self.assertTrue(all(s['status']=='partial' for s in plan['stages']))
        blocked=[r for r in final['results'] if r['id'].endswith('-co2e-unresolved')]
        self.assertEqual(len(blocked),14);self.assertTrue(all(r['status']=='blocked' and r['metrics']==[] for r in blocked))
        self.assertEqual(sum(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in r['diagnostics']) for r in blocked),13)
        self.assertEqual(len(_diagnostic(results['food-scope3-classification'],'SCOPE3_CLASSIFICATION')['sources']),8)
        self.assertEqual(state,original);self.assertEqual(final['revision'],state['revision']+1)
        self.assertEqual(final['results'][:len(state['results'])],state['results'])
        self.assertEqual(final['evidence'],state['evidence']);self.assertEqual(final['emission_factors'],state['emission_factors'])
        self.assertFalse(plan['publication_authorized']);self.assertFalse(plan['v1_readiness_verified'])
        self.assertIsNone(plan['combined_cross_domain_total']);validate_state(final)

    def test_selected_electricity_factor_missing_withholds_emissions_without_losing_physical_targets(self):
        state,p=food_fixture();p=copy.deepcopy(p)
        for step in p['operations']['steps']:
            if step['skill']=='calculate-co2e':step['parameters']['factor_id']='missing-selected-factor'
            if step['skill']=='calculate-location-based-scope-2':
                for component in step['parameters']['components']:component['factor_id']='missing-selected-factor'
        out=run_manager(state,p);results={r['id']:r for r in out['proposal']['state']['results']}
        self.assertEqual(results['operations-inventory']['status'],'blocked');self.assertEqual(results['operations-inventory']['metrics'],[])
        self.assertEqual(results['ops-energy']['metrics'][0]['value'],430000)
        self.assertEqual(results['ops-finance']['metrics'][0]['value'],0)
        self.assertEqual(results['strategy-target']['status'],'partial')
        self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])
        self.assertEqual(results['framework-map']['status'],'blocked')
        self.assertFalse(_diagnostic(out['result'],'ORGANIZATION_MANAGER')['publication_authorized'])
