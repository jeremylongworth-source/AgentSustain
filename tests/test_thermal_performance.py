import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.contract_validation import ROOT, validate_state
from scripts.fuel_energy import run_fuel_energy
from scripts.jurisdiction_tasks import _diagnostic
from scripts.thermal_performance import assess_thermal_performance
from tests.test_fuel_energy import fuel_fixture


def thermal_fixture(cop=False):
    state, fuel = fuel_fixture()
    initial = state['results'][0]['metrics'][0]
    initial['value'] = 1000 if cop else 100
    output = copy.deepcopy(initial)
    output.update(id='delivered-heat', name='Fictional metered delivered heat', value=10.8 if cop else 14.688,
                  unit='GJ', evidence_ids=['delivered-heat-source'])
    output['calculation'].update(inputs=['delivered-heat-source'], formula='Fictional supplied integrated heat meter record')
    source = copy.deepcopy(state['evidence'][0])
    source.update(id='delivered-heat-source', unit='GJ')
    source['source'].update(locator='fixture:equipment-heat-record', version='fictional-heat-1', accessed='2026-10-06')
    output['method'].update(source=source['source']['locator'])
    state['evidence'].append(source)
    state['results'][0]['metrics'].append(output)
    state['results'][0]['evidence_ids'].append(source['id'])
    quantities=[{'metric_id':initial['id'],'kind':'electrical_input','source_fragment':'electricity-meter',
                 'evidence_fit':'reviewed_supporting','fuel_result_id':None},
                {'metric_id':'delivered-heat','kind':'thermal_output','source_fragment':'delivered-heat-meter',
                 'evidence_fit':'reviewed_supporting','fuel_result_id':None}]
    if not cop:
        state=run_fuel_energy(state,fuel)['proposal']['state']
        quantities.insert(0,{'metric_id':fuel['result_id']+'-energy','kind':'fuel_input','source_fragment':'fuel-conversion',
                            'evidence_fit':'reviewed_supporting','fuel_result_id':fuel['result_id']})
    review={'boundary_id':state['organizational_boundary']['id'],'facility_id':'facility-001','equipment_id':'fictional-heater-1',
            'period':copy.deepcopy(state['reporting_period']),'as_of_date':'2026-10-06',
            'mode':'period_heating_cop' if cop else 'thermal_conversion',
            'measurement_boundary':'Fictional heater input meters and net delivered heat meter; no real measurement approval.',
            'output_definition':'Integrated net delivered useful heat, with fictional supply/return quality retained in source record.',
            'auxiliary_scope':'Declared metered compressor, fans, pumps and controls; no omitted standby load inferred.',
            'operating_conditions':'Same full-year fictional equipment/service operating interval; no rated test conditions claimed.',
            'input_coverage_complete':True,'output_coverage_complete':True,'same_operating_period':True,
            'fuel_heating_basis':None if cop else 'LHV','nonoverlap_assessment':'Distinct fictional fuel, electrical and delivered heat source fragments.',
            'evidence_ids':['fictional-fuel-review'],'evidence_fit':'reviewed_supporting','rationale':'Fictional supplied measurement/coverage review only.',
            'reviewer_role':'Qualified engineering professional and accountable owner'}
    p={'quantities':quantities,'performance_review':review,'fixture_mode':True,'result_id':'thermal-performance'}
    validate_state(state);return state,p


def report(out):return _diagnostic(out['result'],'THERMAL_PERFORMANCE')


class ThermalPerformanceTests(unittest.TestCase):
    def test_fuel_replay_auxiliary_input_and_known_thermal_ratio(self):
        state,p=thermal_fixture();original=copy.deepcopy(state)
        out=assess_thermal_performance(state,p);r=report(out)
        self.assertEqual((r['supported_input_kWh'],r['supported_output_kWh'],r['ratio']),(5100,4080,0.8))
        self.assertTrue(r['quantities'][0]['fuel_conversion_reproduced'])
        self.assertEqual(state,original);self.assertEqual(out['result']['status'],'partial')
        self.assertEqual(out['proposal']['state']['revision'],state['revision']+1)
        self.assertEqual(out['proposal']['state']['results'][:-1],state['results'])
        self.assertEqual(out['proposal']['state']['emission_factors'],state['emission_factors'])
        self.assertIn('ENGINEERING_REVIEW_REQUIRED',out['result']['review_states'])
        self.assertFalse(r['certified_efficiency_or_rating']);validate_state(out['proposal']['state'])

    def test_period_cop_above_one_and_unit_equivalence(self):
        state,p=thermal_fixture(True)
        self.assertEqual(report(assess_thermal_performance(state,p))['ratio'],3)
        m=state['results'][0]['metrics'][0];m.update(value=1,unit='MWh')
        next(e for e in state['evidence'] if e['id'] in m['evidence_ids'])['unit']='MWh'
        self.assertEqual(report(assess_thermal_performance(state,p))['ratio'],3)
        p['performance_review']['mode']='thermal_conversion'
        out=assess_thermal_performance(state,p)
        self.assertEqual(report(out)['ratio'],3)
        self.assertIn('THERMAL_ABOVE_UNITY_REVIEW_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_zero_unknown_and_incomplete_coverage_remain_distinct(self):
        for value,ratio in ((0,None),(None,None),(1000,3)):
            state,p=thermal_fixture(True);state['results'][0]['metrics'][0]['value']=value
            out=assess_thermal_performance(state,p);self.assertEqual(report(out)['ratio'],ratio)
            self.assertEqual(report(out)['supported_output_kWh'],3000)
        state,p=thermal_fixture(True);state['results'][0]['metrics'][-1]['value']=0
        self.assertEqual(report(assess_thermal_performance(state,p))['ratio'],0)
        for field in ('input_coverage_complete','output_coverage_complete','same_operating_period'):
            state,p=thermal_fixture(True);p['performance_review'][field]=False
            r=report(assess_thermal_performance(state,p))
            self.assertIsNone(r['ratio']);self.assertEqual(r['supported_input_kWh'],1000)

    def test_tampered_fuel_report_source_value_or_basis_withheld(self):
        for change in ('metric','source','report','basis','cop'):
            state,p=thermal_fixture()
            if change=='metric':state['results'][-1]['metrics'][0]['value']=9999
            elif change=='source':next(e for e in state['evidence'] if e['id']=='fictional-cv-evidence')['source']['version']='changed'
            elif change=='report':
                d=next(d for d in state['results'][-1]['diagnostics'] if d['code']=='FUEL_ENERGY_CONVERSION')
                r=json.loads(d['message']);r['energy_kWh']=9999;d['message']=json.dumps(r)
            elif change=='basis':p['performance_review']['fuel_heating_basis']='HHV'
            else:p['performance_review']['mode']='period_heating_cop'
            out=assess_thermal_performance(state,p)
            self.assertEqual(out['result']['status'],'blocked',change);self.assertEqual(out['result']['metrics'],[])

    def test_duplicate_source_fragment_and_unsupported_derived_inputs_block(self):
        for change in ('duplicate','fragment','derived','negative','unit','future','model','period','ordinary','facility'):
            state,p=thermal_fixture(True);m=state['results'][0]['metrics'][-1]
            if change=='duplicate':p['quantities'].append(copy.deepcopy(p['quantities'][0]))
            elif change=='fragment':
                m['evidence_ids']=state['results'][0]['metrics'][0]['evidence_ids'][:]
                m['calculation']['inputs']=m['evidence_ids'][:];p['quantities'][1]['source_fragment']='electricity-meter'
            elif change=='derived':m['calculation']['inputs']=[state['results'][0]['metrics'][0]['id']]
            elif change=='negative':m['value']=-1
            elif change=='unit':m['unit']='UNKNOWN_UNIT'
            elif change=='future':next(e for e in state['evidence'] if e['id']=='delivered-heat-source')['source']['accessed']='2027-01-01'
            elif change=='model':
                e=next(e for e in state['evidence'] if e['id']=='delivered-heat-source');e['source']['tier']=5;e['assumption']='Fictional modeled thermal energy.';state['assumptions'].append(e['assumption'])
            elif change=='period':m['period']['start']='2025-02-01'
            elif change=='ordinary':p['fixture_mode']=False
            else:p['performance_review']['facility_id']='unknown-facility'
            self.assertEqual(assess_thermal_performance(state,p)['result']['status'],'blocked',change)

    def test_unfit_selection_preserves_supported_side_and_original_uncertainty(self):
        state,p=thermal_fixture(True);p['quantities'][0]['evidence_fit']='unverified'
        out=assess_thermal_performance(state,p);r=report(out)
        self.assertIsNone(r['ratio']);self.assertIsNone(r['supported_input_kWh']);self.assertEqual(r['supported_output_kWh'],3000)
        self.assertEqual(r['quantities'][1]['source_view']['metric']['uncertainty'],state['results'][0]['metrics'][-1]['uncertainty'])

    def test_synthetic_ingestion_ancestry_without_fixture_locator_blocks(self):
        state,p=thermal_fixture(True);p['fixture_mode']=False
        for e in state['evidence']:e['source']['locator']='https://example.invalid/fictional-source'
        state['results'][0]['diagnostics'].append({'code':'BUSINESS_INGESTION_INPUTS','message':json.dumps({'fixture_mode':True,'file_pin':{'synthetic':True}})})
        self.assertEqual(assess_thermal_performance(state,p)['result']['status'],'blocked')

    def test_pinned_raw_csv_fuel_and_meter_handoff(self):
        from scripts.business_ingestion import ingest_business_csv
        import hashlib
        state,p=thermal_fixture(True)
        removed={'fictional-fuel','fictional-cv'}
        evidence={'fictional-fuel-evidence','fictional-cv-evidence'}
        state['results'][0]['metrics']=[m for m in state['results'][0]['metrics'] if m['id'] not in removed]
        state['results'][0]['evidence_ids']=[e for e in state['results'][0]['evidence_ids'] if e not in evidence]
        state['evidence']=[e for e in state['evidence'] if e['id'] not in evidence]
        path=ROOT/'data/inputs/fictional-fuel-energy.csv';raw=path.read_bytes()
        ingestion={'file_pin':{'path':'data/inputs/fictional-fuel-energy.csv','sha256':hashlib.sha256(raw).hexdigest(),
                              'source_version':'fictional-thermal-fuel-1','synthetic':True},
                   'source_metadata':{'title':'Fictional fuel source for thermal assessment','publisher':'Fictional Example Company','accessed':'2026-10-06','tier':1},
                   'fixture_mode':True,'result_id':'thermal-csv-import','document_evidence_id':'thermal-csv-document'}
        normalized=ingest_business_csv(state,ingestion)['proposal']['state']
        _,fuel=fuel_fixture();converted=run_fuel_energy(normalized,fuel)['proposal']['state']
        p['performance_review']['mode']='thermal_conversion';p['performance_review']['fuel_heating_basis']='LHV'
        p['quantities'].insert(0,{'metric_id':fuel['result_id']+'-energy','kind':'fuel_input','source_fragment':'fuel-conversion',
                               'evidence_fit':'reviewed_supporting','fuel_result_id':fuel['result_id']})
        out=assess_thermal_performance(converted,p)
        self.assertEqual(report(out)['ratio'],0.5)
        self.assertTrue(report(out)['quantities'][0]['fuel_conversion_reproduced'])
        self.assertEqual(out['proposal']['state']['results'][:-1],converted['results'])
        self.assertEqual(out['proposal']['state']['emission_factors'],state['emission_factors'])
        self.assertEqual(path.read_bytes(),raw)

    def test_unrepresentable_ratio_and_fresh_id_controls(self):
        state,p=thermal_fixture(True)
        state['results'][0]['metrics'][0]['value']=1e-308
        state['results'][0]['metrics'][-1].update(value=1e308,unit='kWh')
        next(e for e in state['evidence'] if e['id']=='delivered-heat-source')['unit']='kWh'
        out=assess_thermal_performance(state,p)
        self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
        self.assertIsNone(report(out)['ratio']);self.assertIsNone(report(out)['supported_input_kWh'])
        state,p=thermal_fixture(True);p['result_id']=state['results'][0]['id']
        with self.assertRaises(ValueError):assess_thermal_performance(state,p)

    def test_actual_cli_full_helper_equality_and_request_bytes(self):
        for cop in (False,True):
            state,p=thermal_fixture(cop);request={'contract_version':'0.1.0','skill':'analyze-energy-usage','state':state,'parameters':p}
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'request.json';raw=json.dumps(request).encode();path.write_bytes(raw)
                cli=subprocess.run([sys.executable,'-m','scripts.run_thermal_performance',str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr)
                self.assertEqual(json.loads(cli.stdout),assess_thermal_performance(state,p));self.assertEqual(path.read_bytes(),raw)
