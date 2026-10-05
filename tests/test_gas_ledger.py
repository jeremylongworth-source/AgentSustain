import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.gas_mass import calculate_gas_mass
from scripts.gas_conversion import convert_gas_mass
from scripts.gas_ledger import build_gas_ledger
from tests.test_gas_conversion import fixture as conversion_fixture


def fixture(with_requests=False):
    _, cp, initial=conversion_fixture(with_mass_request=True);state=copy.deepcopy(initial['state']);requests=[]
    factor_e=copy.deepcopy(state['evidence'][1]);factor_e.update(id='n2o-factor-source',unit='g N2O/GJ')
    factor_e['source'].update(locator='fixture:n2o-factor',version='fictional-n2o-1')
    gwp_e=copy.deepcopy(state['evidence'][-1]);gwp_e.update(id='n2o-gwp-source',unit='kg CO2e/kg N2O')
    gwp_e['source'].update(locator='fixture:n2o-gwp',version='fictional-n2o-1')
    profile_e=copy.deepcopy(gwp_e);profile_e.update(id='ledger-profile-source',unit='1')
    profile_e['source'].update(locator='fixture:fictional-ledger-profile',version='fictional-ledger-1',accessed='2026-10-05')
    state['evidence'].extend([factor_e,gwp_e,profile_e])
    for gas in ['CH4','N2O']:
        mp=copy.deepcopy(initial['parameters']);mp['result_id']='raw-'+gas
        if gas=='N2O':
            mp['gas']=gas;mp['factor'].update(id='n2o-factor',gas=gas,value=4,unit='g N2O/GJ',evidence_ids=[factor_e['id']])
            mp['factor']['source'].update(locator=factor_e['source']['locator'],version=factor_e['source']['version'])
            mp['applicability_review']['activity_review']['gas']=gas
            mp['applicability_review']['factor_review'].update(factor_id='n2o-factor',gas=gas,confirmed_value=4,
                confirmed_unit='g N2O/GJ',evidence_ids=[factor_e['id']],source_locator=factor_e['source']['locator'],source_version=factor_e['source']['version'])
        requests.append({'contract_version':'0.1.0','skill':'calculate-gas-mass','state':state,'parameters':mp})
        mass=calculate_gas_mass(state,mp);state=mass['proposal']['state']
        p=copy.deepcopy(cp);p.update(gas_result_id=mp['result_id'],gas_metric_id=mass['result']['metrics'][0]['id'],result_id='converted-'+gas)
        p['conversion_review']['source_review'].update(gas_result_id=p['gas_result_id'],gas_metric_id=p['gas_metric_id'])
        if gas=='N2O':
            p['gwp'].update(id='n2o-gwp',gas=gas,value=5,unit='kg CO2e/kg N2O',evidence_ids=[gwp_e['id']])
            p['gwp']['source'].update(locator=gwp_e['source']['locator'],version=gwp_e['source']['version'])
            p['conversion_review'].update(gas=gas,evidence_ids=[gwp_e['id']])
            p['conversion_review']['source_review'].update(gwp_id='n2o-gwp',gas=gas,value=5,unit='kg CO2e/kg N2O',
                evidence_ids=[gwp_e['id']],source_locator=gwp_e['source']['locator'],source_version=gwp_e['source']['version'])
        requests.append({'contract_version':'0.1.0','skill':'convert-gas-mass-to-co2e','state':state,'parameters':p})
        state=convert_gas_mass(state,p)['proposal']['state']
    raw=(ROOT/'standards/jurisdictions/fixtures/fictional-gas-ledger-1.json').read_bytes()
    params={'profile_pin':{'path':'fixtures/fictional-gas-ledger-1.json','sha256':hashlib.sha256(raw).hexdigest()},
        'sources':[{'id':'source-1','facility_id':'facility-001','activity_id':'metric-001','activity_kind':initial['parameters']['factor']['activity_kind'],
            'gases':['CH4','N2O'],'evidence_ids':['ev-001'],'evidence_fit':'reviewed_supporting','rationale':'Fictional source/facility declaration.'}],
        'components':[{'source_id':'source-1','gas':g,'conversion_result_id':'converted-'+g} for g in ['CH4','N2O']],
        'ledger_review':{'facility_id':'facility-001','boundary_id':state['organizational_boundary']['id'],'period':copy.deepcopy(state['reporting_period']),
            'as_of_date':'2026-10-05','source_inventory_complete':True,'exclusions':[],'evidence_ids':[profile_e['id']],
            'evidence_fit':'reviewed_supporting','scope':'Fictional selected source ledger, not a statutory facility.',
            'reviewer_role':'Qualified GHG/source reviewer','rationale':'Fictional exact profile and roster only.'},
        'fixture_mode':True,'result_id':'gas-ledger'}
    return (state,params,requests) if with_requests else (state,params)


def report(out):return json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='FACILITY_GAS_LEDGER'))


class GasLedgerTests(unittest.TestCase):
    def test_known_answer_two_gases_full_reproduction_and_preservation(self):
        state,p=fixture();before=copy.deepcopy(state);out=build_gas_ledger(state,p);r=report(out)
        self.assertEqual(out['result']['metrics'][0]['value'],0.14)
        self.assertEqual(r['included_species_mass_kg'],{'CH4':0.01,'N2O':0.008})
        self.assertTrue(r['declared_coverage_reproduced']);self.assertFalse(r['regulatory_quantity_verified'])
        self.assertFalse(r['statutory_threshold_authorized']);self.assertFalse(r['facility_attribution_authenticated'])
        self.assertEqual(state,before);validate_state(out['proposal']['state'])
        for k in ['results','evidence','review_requirements','data_gaps','assumptions','emission_factors']:
            for item in state[k]:self.assertIn(item,out['proposal']['state'][k])
        self.assertEqual(state['ghg'],out['proposal']['state']['ghg'])
        self.assertTrue(all(r['status']=='open' for r in out['result']['review_requirements']))

    def test_missing_species_and_all_missing_are_unknown_not_zero(self):
        state,p=fixture();p['components'].pop()
        out=build_gas_ledger(state,p);r=report(out)
        self.assertEqual(out['result']['metrics'][0]['value'],0.1);self.assertIsNone(r['included_species_mass_kg']['N2O'])
        self.assertFalse(r['declared_coverage_reproduced'])
        p['components']=[];out=build_gas_ledger(state,p)
        self.assertEqual(out['result']['metrics'],[]);self.assertIsNone(report(out)['known_co2e_kg'])

    def test_blocked_missing_gwp_preserves_required_factor_and_subtotal(self):
        state,p=fixture();owner=next(r for r in state['results'] if r['id']=='converted-N2O')
        args=json.loads(next(d['message'] for d in owner['diagnostics'] if d['code']=='GAS_CO2E_INPUTS'))
        args.update(gwp=None,result_id='missing-n2o-gwp');state=convert_gas_mass(state,args)['proposal']['state']
        p['components'][1]['conversion_result_id']=args['result_id'];out=build_gas_ledger(state,p)
        self.assertEqual(out['result']['metrics'][0]['value'],0.1)
        self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])
        self.assertIsNone(report(out)['included_species_mass_kg']['N2O'])
        row=next(r for r in report(out)['rows'] if r['gas']=='N2O')
        self.assertEqual(row['unconverted_raw_result_snapshot']['metrics'][0]['value'],0.008)
        self.assertFalse(row['raw_snapshot_reproduced'])

    def test_duplicate_slot_result_and_activity_species_are_blocked(self):
        for change in ['slot','result','activity']:
            state,p=fixture()
            if change=='slot':p['components'].append(copy.deepcopy(p['components'][0]))
            elif change=='result':p['components'][1]['conversion_result_id']='converted-CH4'
            else:
                src=copy.deepcopy(p['sources'][0]);src['id']='source-2';p['sources'].append(src)
                p['components'].extend([{'source_id':'source-2','gas':g,'conversion_result_id':'converted-'+g} for g in ['CH4','N2O']])
            self.assertEqual(build_gas_ledger(state,p)['result']['status'],'blocked')

    def test_distinct_conversion_ids_cannot_duplicate_the_same_activity_species(self):
        state,p=fixture();owner=next(r for r in state['results'] if r['id']=='converted-CH4')
        args=json.loads(next(d['message'] for d in owner['diagnostics'] if d['code']=='GAS_CO2E_INPUTS'))
        args['result_id']='another-ch4-conversion';state=convert_gas_mass(state,args)['proposal']['state']
        src=copy.deepcopy(p['sources'][0]);src['id']='source-2';p['sources'].append(src)
        p['components'].append({'source_id':'source-2','gas':'CH4','conversion_result_id':args['result_id']})
        out=build_gas_ledger(state,p)
        self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])

    def test_distinct_activity_ids_cannot_duplicate_whole_record_evidence_species(self):
        state,p=fixture();metric=copy.deepcopy(state['results'][0]['metrics'][0]);metric['id']='other-activity'
        state['results'][0]['metrics'].append(metric)
        raw=next(r for r in state['results'] if r['id']=='raw-CH4')
        args=json.loads(next(d['message'] for d in raw['diagnostics'] if d['code']=='GAS_MASS_INPUTS'))
        args.update(activity_id=metric['id'],result_id='other-raw')
        args['applicability_review']['activity_review']['metric_id']=metric['id']
        args['applicability_review']['factor_review']['activity_id']=metric['id']
        state=calculate_gas_mass(state,args)['proposal']['state']
        owner=next(r for r in state['results'] if r['id']=='converted-CH4')
        cp=json.loads(next(d['message'] for d in owner['diagnostics'] if d['code']=='GAS_CO2E_INPUTS'))
        cp.update(gas_result_id='other-raw',gas_metric_id='other-raw-metric',result_id='other-conversion')
        cp['conversion_review']['source_review'].update(gas_result_id='other-raw',gas_metric_id='other-raw-metric')
        state=convert_gas_mass(state,cp)['proposal']['state']
        src=copy.deepcopy(p['sources'][0]);src.update(id='source-2',activity_id=metric['id']);p['sources'].append(src)
        p['components'].append({'source_id':'source-2','gas':'CH4','conversion_result_id':'other-conversion'})
        out=build_gas_ledger(state,p)
        self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])

    def test_changed_conversion_report_metric_and_source_are_blocked(self):
        for change in ['metric','report','source','uncertainty','lineage']:
            state,p=fixture();owner=next(r for r in state['results'] if r['id']=='converted-CH4')
            if change=='metric':owner['metrics'][0]['value']=4
            elif change=='source':state['evidence'][0]['quality']['fitness_notes']='Altered original source.'
            elif change=='uncertainty':owner['metrics'][0]['uncertainty']['description']='No uncertainty.'
            elif change=='lineage':owner['evidence_ids'].append('ledger-profile-source')
            else:
                d=next(d for d in owner['diagnostics'] if d['code']=='GAS_CO2E_CONVERSION');r=json.loads(d['message']);r['co2e_kg']=4;d['message']=json.dumps(r)
            self.assertEqual(build_gas_ledger(state,p)['result']['status'],'blocked')

    def test_unfit_source_profile_exclusions_and_incomplete_inventory(self):
        for change in ['source','profile','exclusions','incomplete']:
            state,p=fixture()
            if change=='source':p['sources'][0]['evidence_fit']='unverified'
            elif change=='profile':p['ledger_review']['evidence_fit']='unverified'
            elif change=='exclusions':p['ledger_review']['exclusions']=['Fictional omitted source']
            else:p['ledger_review']['source_inventory_complete']=False
            out=build_gas_ledger(state,p);self.assertFalse(report(out)['declared_coverage_reproduced'])
            if change in ['source','profile']:self.assertEqual(out['result']['metrics'],[])

    def test_pin_facility_roster_activity_kind_date_and_source_binding(self):
        for change in ['pin','fixture','facility','gas_roster','activity','kind','date','binding','corporate']:
            state,p=fixture()
            if change=='pin':p['profile_pin']['sha256']='0'*64
            elif change=='fixture':p['fixture_mode']=False
            elif change=='facility':p['ledger_review']['facility_id']='not-in-boundary'
            elif change=='gas_roster':p['sources'][0]['gases']=['CH4']
            elif change=='activity':p['sources'][0]['activity_id']='not-selected'
            elif change=='kind':p['sources'][0]['activity_kind']='other-fuel'
            elif change=='date':p['ledger_review']['as_of_date']='2026-10-06'
            elif change=='binding':p['sources'][0]['evidence_ids']=['ledger-profile-source']
            else:p['components'][0]['conversion_result_id']='res-001'
            self.assertEqual(build_gas_ledger(state,p)['result']['status'],'blocked')

    def test_wrong_selected_profile_basis_and_horizon_are_blocked(self):
        from unittest.mock import patch
        from scripts.gas_ledger import load_profile
        for change in ['basis','horizon']:
            state,p=fixture();profile=load_profile(p['profile_pin'],True)
            if change=='basis':profile['basis']='other'
            else:profile['time_horizon_years']=20
            with patch('scripts.gas_ledger.load_profile',return_value=profile):
                self.assertEqual(build_gas_ledger(state,p)['result']['status'],'blocked')

    def test_actual_cli_complete_output_preserves_request(self):
        state,p=fixture();expected=build_gas_ledger(state,p)
        request={'contract_version':'0.1.0','skill':'build-facility-gas-ledger','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'request.json';raw=(json.dumps(request,indent=2)+'\n').encode();path.write_bytes(raw)
            run=subprocess.run([sys.executable,'-m','scripts.run_gas_mass',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(run.stderr,'')
            self.assertEqual(json.loads(run.stdout),expected);self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':unittest.main()
