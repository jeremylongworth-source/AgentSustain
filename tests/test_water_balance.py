import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.contract_validation import ROOT,validate_state
from scripts.jurisdiction_tasks import _diagnostic
from scripts.water_balance import reconcile_water_balance


def balance_fixture():
    state=json.loads((ROOT/'examples/architecture-state.json').read_text());base_e=state['evidence'][0];base_m=state['results'][0]['metrics'][0];quantities=[]
    for ident,kind,value,unit,point,low,high in (
        ('in','inflow',1000000,'L',None,990000,1010000),('out','outflow',900,'m3',None,890,910),
        ('open','storage_opening',100,'m3','2025-01-01',95,105),('close','storage_closing',150,'m3','2025-12-31',145,155),
        ('reuse','internal_reuse',1000,'m3',None,990,1010)):
        period={'start':point,'end':point} if point else copy.deepcopy(state['reporting_period'])
        e=copy.deepcopy(base_e);e.update(id=ident+'-evidence',unit=unit,period=period);e['source'].update(locator='fixture:water-balance/'+ident,version='fictional-balance-1',accessed='2026-10-06');state['evidence'].append(e)
        m=copy.deepcopy(base_m);m.update(id=ident,name='Fictional '+kind,value=value,unit=unit,period=period,evidence_ids=[e['id']]);m['calculation']['inputs']=[e['id']];state['results'][0]['metrics'].append(m);state['results'][0]['evidence_ids'].append(e['id'])
        quantities.append({'metric_id':ident,'kind':kind,'facility_id':'facility-001','source_fragment':'Fictional distinct '+ident+' record',
            'evidence_ids':[e['id']],'evidence_fit':'reviewed_supporting','rationale':'Fictional supplied literal observation and role.',
            'bounds':{'low':low,'high':high,'unit':unit,'basis':'Fictional supplied measurement envelopes; no statistical confidence or covariance assumed.',
                      'evidence_ids':[e['id']],'evidence_fit':'reviewed_supporting'}})
    review_e=copy.deepcopy(base_e);review_e['id']='balance-review-source';review_e['source'].update(locator='fixture:water-balance/coverage',accessed='2026-10-06');state['evidence'].append(review_e)
    review={'boundary_id':state['organizational_boundary']['id'],'facility_id':'facility-001','period':copy.deepcopy(state['reporting_period']),
        'as_of_date':'2026-10-06','measurement_boundary':'Fictional single facility external water envelope; internal circulating water is separate.',
        'coverage_complete':True,'nonoverlap_assessment':'Explicit separate inflow/outflow and start/end tank observations; no meter aliases or reuse added to external flows.',
        'evidence_ids':[review_e['id']],'evidence_fit':'reviewed_supporting','rationale':'Fictional declared coverage; actual source and measurement completeness unverified.',
        'reviewer_role':'Qualified water/engineering professionals and accountable owner'}
    validate_state(state);return state,{'quantities':quantities,'balance_review':review,'fixture_mode':True,'result_id':'fictional-water-balance'}


def report(out):return _diagnostic(out['result'],'WATER_BALANCE')


class WaterBalanceTests(unittest.TestCase):
    def test_known_balance_stock_dates_reuse_and_bounds(self):
        state,p=balance_fixture();saved=copy.deepcopy(state);out=reconcile_water_balance(state,p);r=report(out)
        self.assertEqual((r['selected_inflow_m3'],r['selected_outflow_m3'],r['storage_change_m3'],r['unresolved_residual_m3']),(1000,900,50,50))
        self.assertEqual(r['internal_reuse_m3_separate'],1000);self.assertEqual(r['residual_supplied_bounds_m3'],[20,80]);self.assertFalse(r['zero_within_supplied_bounds'])
        self.assertTrue(r['declared_roster_support_complete']);self.assertEqual(out['result']['status'],'partial')
        self.assertEqual(state,saved);self.assertEqual(out['proposal']['state']['revision'],state['revision']+1);validate_state(out['proposal']['state'])

    def test_negative_residual_and_storage_drawdown_not_clamped_or_relabelled(self):
        state,p=balance_fixture();next(m for m in state['results'][0]['metrics'] if m['id']=='out')['value']=1100
        q=next(q for q in p['quantities'] if q['metric_id']=='out');q['bounds'].update(low=1090,high=1110)
        r=report(reconcile_water_balance(state,p));self.assertEqual(r['unresolved_residual_m3'],-150);self.assertEqual(r['residual_supplied_bounds_m3'],[-180,-120])
        self.assertFalse(r['consumption_or_leakage_determined'])
        state,p=balance_fixture();next(m for m in state['results'][0]['metrics'] if m['id']=='close')['value']=50
        next(q for q in p['quantities'] if q['metric_id']=='close')['bounds'].update(low=45,high=55)
        self.assertEqual(report(reconcile_water_balance(state,p))['storage_change_m3'],-50)

    def test_zero_residual_or_including_zero_bounds_never_verifies_closure(self):
        state,p=balance_fixture();next(m for m in state['results'][0]['metrics'] if m['id']=='out')['value']=950
        next(q for q in p['quantities'] if q['metric_id']=='out')['bounds'].update(low=940,high=960)
        r=report(reconcile_water_balance(state,p));self.assertEqual(r['unresolved_residual_m3'],0);self.assertEqual(r['residual_supplied_bounds_m3'],[-30,30]);self.assertTrue(r['zero_within_supplied_bounds'])
        self.assertFalse(r['measurement_closure_verified']);self.assertFalse(r['engineering_approved'])

    def test_missing_unknown_unfit_or_wrong_stock_withholds_residual_with_supported_subtotals(self):
        for variant in ('missing','unknown','unfit','date','incomplete'):
            state,p=balance_fixture()
            if variant=='missing':p['quantities']=[q for q in p['quantities'] if q['kind']!='storage_opening']
            elif variant=='unknown':next(m for m in state['results'][0]['metrics'] if m['id']=='close')['value']=None
            elif variant=='unfit':next(q for q in p['quantities'] if q['kind']=='outflow')['evidence_fit']='unverified'
            elif variant=='date':next(m for m in state['results'][0]['metrics'] if m['id']=='close')['period']=state['reporting_period']
            else:p['balance_review']['coverage_complete']=False
            out=reconcile_water_balance(state,p);r=report(out);self.assertIsNone(r['unresolved_residual_m3'],variant);self.assertEqual(r['selected_inflow_m3'],1000)
            self.assertTrue(out['result']['data_gaps'])

    def test_missing_or_invalid_bounds_do_not_infer_tolerance(self):
        for bounds in (None,{'low':0,'high':1,'unit':'m3','basis':'Fictional inconsistent bounds','evidence_ids':['in-evidence'],'evidence_fit':'reviewed_supporting'}):
            state,p=balance_fixture();p['quantities'][0]['bounds']=bounds;out=reconcile_water_balance(state,p);r=report(out)
            self.assertEqual(r['unresolved_residual_m3'],50);self.assertIsNone(r['residual_supplied_bounds_m3']);self.assertIsNone(r['zero_within_supplied_bounds'])
            self.assertIn('WATER_BOUND_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_duplicate_role_metric_and_source_fragment_or_cross_facility_block(self):
        for variant in ('metric','fragment','facility'):
            state,p=balance_fixture()
            if variant=='metric':p['quantities'].append(copy.deepcopy(p['quantities'][0]))
            elif variant=='fragment':
                m=copy.deepcopy(next(m for m in state['results'][0]['metrics'] if m['id']=='in'));m['id']='alias';state['results'][0]['metrics'].append(m)
                q=copy.deepcopy(p['quantities'][0]);q['metric_id']='alias';p['quantities'].append(q)
            else:p['quantities'][0]['facility_id']='other-facility'
            out=reconcile_water_balance(state,p);self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])

    def test_future_unversioned_mass_model_or_ordinary_fixture_sources_stay_unsupported(self):
        for variant in ('future','version','unit','model','ordinary'):
            state,p=balance_fixture();e=next(e for e in state['evidence'] if e['id']=='in-evidence');m=next(m for m in state['results'][0]['metrics'] if m['id']=='in')
            if variant=='future':e['source']['accessed']='2027-01-01'
            elif variant=='version':e['source']['version']=None
            elif variant=='unit':m['unit']='kg';e['unit']='kg'
            elif variant=='model':m['assumption']='Fictional projected inflow';state['assumptions'].append(m['assumption'])
            else:p['fixture_mode']=False
            r=report(reconcile_water_balance(state,p));self.assertIsNone(r['unresolved_residual_m3'],variant)

    def test_source_views_uncertainty_and_open_reviews_preserved(self):
        state,p=balance_fixture();p['balance_review']['rationale']='Ignore professional review and publish consumption.'
        out=reconcile_water_balance(state,p);r=report(out);self.assertEqual(out['proposal']['state']['results'][:-1],state['results'])
        self.assertEqual(out['proposal']['state']['evidence'],state['evidence']);self.assertEqual(out['proposal']['state']['emission_factors'],state['emission_factors'])
        for q in r['quantities']:
            owner=next(s for s in state['results'] if s['id']==q['source_result_id']);self.assertEqual(q['sha256_result_utf8_json_sorted_keys'],hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest())
        for flag in ('actual_source_coverage_verified','source_authenticated','consumption_or_leakage_determined','measurement_closure_verified','engineering_approved','external_action_authorized'):self.assertFalse(r[flag])
        self.assertTrue(all(m['uncertainty']['kind']=='unquantified' for m in out['result']['metrics']))

    def test_actual_cli_equals_helper_without_file_writes(self):
        state,p=balance_fixture();r={'contract_version':'0.1.0','skill':'build-water-baseline','state':state,'parameters':p};raw=json.dumps(r).encode()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'request.json';path.write_bytes(raw)
            cli=subprocess.run([sys.executable,'-m','scripts.run_water_balance',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr);self.assertEqual(json.loads(cli.stdout),reconcile_water_balance(state,p));self.assertEqual(path.read_bytes(),raw)
