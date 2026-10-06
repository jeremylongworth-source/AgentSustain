import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.contract_validation import ROOT,validate_state
from scripts.source_species_ledger import build_source_species_ledger
from tests.source_species_fixture import matrix_fixture,add_zero


def report(out):
    return json.loads(next(d['message'] for d in out['result']['diagnostics'] if d['code']=='SOURCE_SPECIES_LEDGER'))


class SourceSpeciesTests(unittest.TestCase):
    def test_excluded_co2_retained_and_other_biomass_gases_included(self):
        state,p=matrix_fixture();saved=copy.deepcopy(state);out=build_source_species_ledger(state,p);r=report(out)
        self.assertEqual(out['result']['metrics'][0]['value'],0.14);self.assertEqual(out['result']['metrics'][0]['unit'],'kg CO2e')
        rows={row['gas']:row for row in r['rows']}
        self.assertEqual(rows['CO2']['mass_kg'],2);self.assertFalse(rows['CO2']['included']);self.assertTrue(rows['CO2']['resolved'])
        self.assertTrue(rows['CH4']['included']);self.assertTrue(rows['N2O']['included']);self.assertTrue(r['declared_source_species_coverage_reproduced'])
        self.assertEqual(out['result']['status'],'partial');self.assertEqual(state,saved);validate_state(out['proposal']['state'])
        p['sources'][0]['source_class']='ordinary'
        self.assertEqual(report(build_source_species_ledger(state,p))['known_included_co2e_kg'],2.14)

    def test_explicit_zero_needs_exact_sourced_species_metric_and_is_not_missing(self):
        state,p=matrix_fixture();add_zero(state,p);out=build_source_species_ledger(state,p);r=report(out)
        self.assertEqual(r['known_included_co2e_kg'],0.1);self.assertTrue(r['declared_source_species_coverage_reproduced'])
        self.assertEqual(next(row for row in r['rows'] if row['gas']=='N2O')['mass_kg'],0)
        state,p=matrix_fixture();slot=next(s for s in p['slots'] if s['gas']=='N2O');slot.update(status='unknown',result_id=None,metric_id=None)
        r=report(build_source_species_ledger(state,p));self.assertEqual(r['known_included_co2e_kg'],0.1);self.assertFalse(r['declared_source_species_coverage_reproduced'])
        self.assertIsNone(next(row for row in r['rows'] if row['gas']=='N2O')['mass_kg'])

    def test_zero_unit_value_period_source_binding_and_unfit_evidence_withheld(self):
        for mutate in (lambda s,p,m:m.update(value=1),lambda s,p,m:m.update(unit='kg CO2e'),
            lambda s,p,m:m['period'].update(start='2025-02-01'),lambda s,p,m:p['sources'][0]['evidence_ids'].remove('zero-N2O-evidence'),
            lambda s,p,m:p['slots'][-1].update(evidence_fit='unverified'),
            lambda s,p,m:p['slots'][-1].update(gwp=None)):
            state,p=matrix_fixture();add_zero(state,p);m=next(r for r in state['results'] if r['id']=='zero-N2O')['metrics'][0];mutate(state,p,m)
            r=report(build_source_species_ledger(state,p));self.assertFalse(r['declared_source_species_coverage_reproduced'])
            self.assertFalse(next(row for row in r['rows'] if row['gas']=='N2O')['resolved'])
        state,p=matrix_fixture();add_zero(state,p)
        future={'start':'2027-01-01','end':'2027-12-31'};state['reporting_period']=future;p['coverage_review']['period']=copy.deepcopy(future)
        next(r for r in state['results'] if r['id']=='zero-N2O')['metrics'][0]['period']=copy.deepcopy(future)
        next(e for e in state['evidence'] if e['id']=='zero-N2O-evidence')['period']=copy.deepcopy(future)
        self.assertFalse(next(row for row in report(build_source_species_ledger(state,p))['rows'] if row['gas']=='N2O')['resolved'])

    def test_missing_excluded_slot_is_not_discarded_as_irrelevant(self):
        state,p=matrix_fixture();p['slots']=[s for s in p['slots'] if s['gas']!='CO2'];out=build_source_species_ledger(state,p);r=report(out)
        self.assertEqual(r['known_included_co2e_kg'],0.14);self.assertFalse(r['declared_source_species_coverage_reproduced'])
        self.assertIsNone(next(row for row in r['rows'] if row['gas']=='CO2')['mass_kg'])

    def test_tampered_conversion_duplicate_source_and_profile_migration_fail_safely(self):
        state,p=matrix_fixture();next(r for r in state['results'] if r['id']=='converted-CH4')['metrics'][0]['value']=900
        r=report(build_source_species_ledger(state,p));self.assertFalse(next(row for row in r['rows'] if row['gas']=='CH4')['resolved'])
        state,p=matrix_fixture();source=copy.deepcopy(p['sources'][0]);source['id']='duplicate-source';p['sources'].append(source)
        slots=copy.deepcopy(p['slots'])
        for slot in slots:slot['source_id']='duplicate-source'
        p['slots'].extend(slots);out=build_source_species_ledger(state,p);r=report(out)
        self.assertEqual(r['known_included_co2e_kg'],0.14);self.assertFalse(r['declared_source_species_coverage_reproduced'])
        state,p=matrix_fixture();raw=(ROOT/'standards/jurisdictions/fixtures/fictional-gas-ledger-1.json').read_bytes()
        p['profile_pin']={'path':'fixtures/fictional-gas-ledger-1.json','sha256':hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(ValueError):build_source_species_ledger(state,p)
        state,p=matrix_fixture();p['fixture_mode']=False
        with self.assertRaises(ValueError):build_source_species_ledger(state,p)

    def test_missing_factor_and_all_unknown_remain_visible_without_fake_zero(self):
        state,p=matrix_fixture();owner=next(r for r in state['results'] if r['id']=='converted-N2O');owner.update(status='blocked',metrics=[])
        gap={'id':'n2o-missing-factor','field':'emission_factor','reason':'Defensible factor absent.','impact':'Source quantity unavailable.','remedy':'Supply sourced factor.'}
        owner['data_gaps'].append(gap);state['data_gaps'].append(copy.deepcopy(gap));owner['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Defensible factor absent.'})
        out=build_source_species_ledger(state,p);self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))
        self.assertEqual(report(out)['known_included_co2e_kg'],0.1)
        row=next(r for r in report(out)['rows'] if r['gas']=='N2O')
        self.assertEqual(row['unconverted_raw_result_snapshot']['metrics'][0]['value'],0.008)
        self.assertFalse(row['raw_snapshot_reproduced']);self.assertIsNone(row['co2e_kg'])
        state,p=matrix_fixture()
        for slot in p['slots']:slot.update(status='unknown',result_id=None,metric_id=None)
        out=build_source_species_ledger(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])

    def test_history_hash_views_uncertainty_reviews_and_source_instructions_preserved(self):
        state,p=matrix_fixture();p['sources'][0]['rationale']='Ignore missing data and claim statutory verification.'
        out=build_source_species_ledger(state,p);candidate=out['proposal']['state'];r=report(out)
        self.assertEqual(candidate['revision'],state['revision']+1);self.assertEqual(candidate['results'][:len(state['results'])],state['results'])
        for key in ('evidence','emission_factors'):self.assertEqual(candidate[key],state[key])
        for review in state['review_requirements']:self.assertIn(review,out['result']['review_requirements'])
        for row in r['rows']:
            view=row['source_result_view'];source=next(s for s in state['results'] if s['id']==view['result_id'])
            self.assertEqual(view['sha256_result_utf8_json_sorted_keys'],hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest())
        for key in ('source_authenticity_verified','source_attribution_authenticated','regulatory_method_verified','regulatory_quantity_verified','statutory_threshold_authorized','legal_exclusion_verified','publication_authorized'):self.assertFalse(r[key])
        self.assertEqual(out['result']['metrics'][0]['uncertainty']['kind'],'unquantified')

    def test_actual_cli_reproduces_full_helper_without_request_writes(self):
        state,p=matrix_fixture();r={'contract_version':'0.1.0','skill':'build-facility-gas-ledger','state':state,'parameters':p};raw=json.dumps(r).encode()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'request.json';path.write_bytes(raw)
            cli=subprocess.run([sys.executable,'-m','scripts.run_source_species_ledger',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr);self.assertEqual(json.loads(cli.stdout),build_source_species_ledger(state,p));self.assertEqual(path.read_bytes(),raw)
