import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.climate_tools import run_climate
from scripts.contract_validation import ROOT, validate_state


def report(output, code):
    return json.loads(next(d['message'] for d in output['result']['diagnostics'] if d['code'] == code))


def climate_fixture():
    state = json.loads((ROOT / 'examples/architecture-state.json').read_text(encoding='utf-8'))
    for ident, title in [('hazard-source', 'Fictional coarse regional climate grid'), ('asset-source', 'Fictional asset and service location record')]:
        e = copy.deepcopy(state['evidence'][0])
        e.update(id=ident, unit='UNKNOWN_UNIT', period={'start':'2026-10-01', 'end':'2026-10-05'})
        e['source'].update(locator='fixture:'+ident, title=title, accessed='2026-10-05', version='fixture-1')
        e['method'].update(name='Fictional selected source extract', source='fixture:'+ident)
        e['quality'].update(reliability='unknown', completeness='partial', fitness_notes='Fictional screening fixture; no authenticated climate or site dataset.')
        e['uncertainty']['description'] = 'Coarse resolution and future operating/site conditions are unverified.'
        state['evidence'].append(e)
    box = lambda bounds: {'crs':'OGC:CRS84', 'bounds':bounds, 'representation':'bounding_box', 'resolution':'Fictional selected regional cell/envelope, not a hazard footprint or surveyed building.'}
    hazard = {'id':'rain-cell', 'name':'Fictional heavy-rain candidate', 'physical_type':'acute',
        'mechanism':'Supplied regional extreme-rain study suggests investigation of drainage and service disruption; no flood depth.',
        'context':{'kind':'projected', 'scenario':'Fictional exploratory scenario A', 'model':'Fictional coarse grid v1',
            'baseline_period':{'start':'2000-01-01','end':'2020-12-31'}, 'horizon':{'start':'2030-01-01','end':'2050-12-31'}},
        'spatial_extent':box([10,10,20,20]), 'evidence_ids':['hazard-source'], 'evidence_fit':'reviewed_supporting',
        'source_fragment':'Fictional supplied grid extent under scenario A; not site inundation data.', 'observed_date':'2026-10-02',
        'limitations':'Unknown local drainage, ground elevation, climate attribution, intensity and probability.'}
    review = {'confirmed':True, 'reviewer_role':'Fictional source screener', 'rationale':'Fictional extracts reviewed for selected screening only.',
        'evidence_ids':['hazard-source'], 'boundary_id':state['organizational_boundary']['id'], 'period':state['reporting_period'],
        'scope':'Fictional selected plant and service dependency', 'selection_basis':'One selected regional grid, no complete hazard coverage.',
        'limitations':'No specialist model or provider/site authentication.', 'as_of_date':'2026-10-05', 'coverage_complete':False,
        'exclusions':['Other hazards and locations'], 'method':'source_hazard_register'}
    identify = {'hazards':[hazard], 'hazard_review':review, 'result_id':'climate-hazards'}
    asset = {'id':'plant-site','name':'Fictional plant location envelope', 'asset_type':'physical_asset', 'boundary_relation':'direct',
        'facility_id':'facility-001', 'function':'Selected processing service', 'owner':'Fictional plant source-review owner',
        'location':box([12,12,12,12]), 'operating_period':{'start':'2027-01-01','end':'2035-12-31'},
        'evidence_ids':['asset-source'], 'evidence_fit':'reviewed_supporting', 'source_fragment':'Fictional supplied location and proposed operating-window extract.',
        'observed_date':'2026-10-03', 'limitations':'No surveyed footprint, verified future availability, vulnerability or damage function.'}
    outside = copy.deepcopy(asset); outside.update(id='external-service', name='Fictional service envelope', asset_type='service_dependency',
        boundary_relation='value_chain', facility_id=None, location=box([30,30,31,31]))
    pair = {'asset_id':'plant-site','hazard_id':'rain-cell','evidence_ids':['hazard-source','asset-source'],
        'spatial_fit':'reviewed_supporting','context_fit':'reviewed_supporting','rationale':'Fictional same-CRS, selected scenario/window envelope comparison; no building hazard inference.'}
    second = copy.deepcopy(pair); second['asset_id']='external-service'
    map_review = copy.deepcopy(review); map_review.update(method='bounding_box_screen', evidence_ids=['hazard-source','asset-source'])
    mapping = {'hazard_result_id':'climate-hazards','assets':[asset,outside], 'comparisons':[pair,second],
        'mapping_review':map_review,'result_id':'climate-map'}
    return state, identify, mapping


def mapping_fixture():
    state, identify, mapping = climate_fixture()
    return run_climate(state,'identify-climate-hazards',identify)['proposal']['state'], mapping


class ClimateTests(unittest.TestCase):
    def test_geographic_known_answers_and_state_preservation(self):
        state, params = mapping_fixture(); old = copy.deepcopy(state)
        out = run_climate(state,'map-assets-to-hazards',params); row = report(out,'ASSET_HAZARD_MAP')
        self.assertEqual([r['screening_status'] for r in row['comparisons']], ['possible_exposure_candidate','outside_selected_extent_screen'])
        self.assertEqual([r['candidate_spatial_relation'] for r in row['comparisons']], ['intersects_selected_boxes','outside_selected_box'])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(out['result']['status'],'partial')
        for c in row['comparisons']:
            self.assertFalse(c['exposure_verified']); self.assertFalse(c['asset_safe'])
            for k in ['probability','damage','risk_score','vulnerability']: self.assertIsNone(c[k])
        for k in ['organization_safe','specialist_model_validated','implementation_authorized','public_claim_authorized']: self.assertFalse(row[k])
        candidate=out['proposal']['state']; self.assertEqual(state,old); self.assertEqual(candidate['results'][:-1],old['results'])
        for k in ['evidence','organization','facilities','reporting_period','organizational_boundary']: self.assertEqual(candidate[k],old[k])
        for r in old['review_requirements']: self.assertIn(r,candidate['review_requirements'])
        for g in old['data_gaps']: self.assertIn(g,candidate['data_gaps'])
        self.assertEqual(candidate['revision'],old['revision']+1); validate_state(candidate)

    def test_edge_touch_is_candidate_not_safe_or_damage(self):
        state,p=mapping_fixture(); p['assets'][0]['location']['bounds']=[20,20,21,21]
        row=report(run_climate(state,'map-assets-to-hazards',p),'ASSET_HAZARD_MAP')['comparisons'][0]
        self.assertEqual(row['screening_status'],'possible_exposure_candidate'); self.assertIsNone(row['damage'])

    def test_unknown_geometry_dates_and_source_fit_never_negative(self):
        for field,value in [('location',None),('operating_period',None),('observed_date',None),('evidence_fit','unverified'),('evidence_fit','irrelevant')]:
            with self.subTest(field=field,value=value):
                state,p=mapping_fixture(); p['assets'][0][field]=value
                row=report(run_climate(state,'map-assets-to-hazards',p),'ASSET_HAZARD_MAP')['comparisons'][0]
                self.assertEqual(row['screening_status'],'unverified'); self.assertFalse(row['asset_safe'])
        state,p=mapping_fixture(); p['comparisons'][1]['spatial_fit']='unverified'
        row=report(run_climate(state,'map-assets-to-hazards',p),'ASSET_HAZARD_MAP')['comparisons'][1]
        self.assertEqual(row['candidate_spatial_relation'],'outside_selected_box'); self.assertEqual(row['screening_status'],'unverified')

    def test_inclusive_temporal_overlap_and_historical_window(self):
        state,p=mapping_fixture(); p['assets'][0]['operating_period']={'start':'2025-01-01','end':'2029-12-31'}
        row=report(run_climate(state,'map-assets-to-hazards',p),'ASSET_HAZARD_MAP')['comparisons'][0]
        self.assertEqual(row['screening_status'],'no_documented_temporal_overlap'); self.assertFalse(row['asset_safe'])
        p['assets'][0]['operating_period']['end']='2030-01-01'
        row=report(run_climate(state,'map-assets-to-hazards',p),'ASSET_HAZARD_MAP')['comparisons'][0]
        self.assertEqual(row['screening_status'],'possible_exposure_candidate')

    def test_observation_cannot_become_projection(self):
        state,p,_=climate_fixture(); h=p['hazards'][0]; h['context']={'kind':'observed','scenario':None,'model':None,
            'baseline_period':{'start':'2025-01-01','end':'2025-12-31'},'horizon':{'start':'2025-01-01','end':'2025-12-31'}}
        out=run_climate(state,'identify-climate-hazards',p); self.assertNotEqual(out['result']['status'],'blocked')
        self.assertIsNone(report(out,'CLIMATE_HAZARDS')['hazards'][0]['probability'])
        h['context']['scenario']='invented future'; self.assertEqual(run_climate(state,'identify-climate-hazards',p)['result']['status'],'blocked')

    def test_invalid_crs_ranges_nonfinite_and_axis_ambiguity_block(self):
        for bounds in [[20,10,10,20],[10,30,20,20],[181,10,182,20],[10,-91,20,20],[True,10,20,20],['NaN',10,20,20],[10,10,20]]:
            with self.subTest(bounds=bounds):
                state,p,_=climate_fixture(); p['hazards'][0]['spatial_extent']['bounds']=bounds
                out=run_climate(state,'identify-climate-hazards',p); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])
        state,p,_=climate_fixture(); p['hazards'][0]['spatial_extent']['crs']='EPSG:4326'
        self.assertEqual(run_climate(state,'identify-climate-hazards',p)['result']['status'],'blocked')

    def test_source_version_period_and_observation_unknown(self):
        for mode in ['version','period','date','source']:
            with self.subTest(mode=mode):
                state,p,_=climate_fixture()
                if mode=='version': state['evidence'][1]['source']['version']=None
                if mode=='period': state['evidence'][1]['period']={'start':'2025-01-01','end':'2025-12-31'}
                if mode=='date': p['hazards'][0]['observed_date']=None
                if mode=='source': p['hazards'][0]['evidence_ids']=[]
                row=report(run_climate(state,'identify-climate-hazards',p),'CLIMATE_HAZARDS')['hazards'][0]
                self.assertEqual(row['source_support'],'unverified')

    def test_changed_hazard_metadata_invalidates_dependency_and_factor_flag_survives(self):
        for change in ['version','uncertainty','fragment','factor']:
            with self.subTest(change=change):
                state,p=mapping_fixture()
                if change=='version': state['evidence'][1]['source']['version']='different'
                if change=='uncertainty': state['evidence'][1]['uncertainty']['description']='Changed bounds confidence'
                if change=='fragment':
                    d=next(d for d in state['results'][-1]['diagnostics'] if d['code']=='CLIMATE_INPUTS'); inputs=json.loads(d['message']); inputs['hazards'][0]['source_fragment']='changed'
                    d['message']=json.dumps(inputs)
                if change=='factor': state['results'][-1]['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved source factor retained.'})
                out=run_climate(state,'map-assets-to-hazards',p); self.assertEqual(out['result']['status'],'blocked')
                if change=='factor': self.assertIn('EMISSION_FACTOR_REQUIRED',[d['code'] for d in out['result']['diagnostics']])

    def test_structural_references_boundary_and_pair_review(self):
        for change in ['asset','hazard','facility','external','sources','duplicate','method','scope','date']:
            with self.subTest(change=change):
                state,p=mapping_fixture()
                if change=='asset': p['comparisons'][0]['asset_id']='unknown'
                if change=='hazard': p['comparisons'][0]['hazard_id']='unknown'
                if change=='facility': p['assets'][0]['facility_id']='outside-boundary'
                if change=='external': p['assets'][1]['facility_id']='facility-001'
                if change=='sources': p['comparisons'][0]['evidence_ids']=['hazard-source']
                if change=='duplicate': p['comparisons'].append(copy.deepcopy(p['comparisons'][0]))
                if change=='method': p['mapping_review']['method']='specialist_model'
                if change=='scope': p['mapping_review']['scope']='unrelated'
                if change=='date': p['mapping_review']['as_of_date']='2026-10-04'
                self.assertEqual(run_climate(state,'map-assets-to-hazards',p)['result']['status'],'blocked')

    def test_omissions_and_empty_lists_do_not_close_coverage(self):
        state,p=mapping_fixture(); p['comparisons']=[]
        out=run_climate(state,'map-assets-to-hazards',p)
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(report(out,'ASSET_HAZARD_MAP')['comparisons'],[])
        self.assertTrue(any('selected pair omitted' in g['reason'] for g in out['result']['data_gaps']))
        state,h,p=climate_fixture(); h['hazards']=[]; state=run_climate(state,'identify-climate-hazards',h)['proposal']['state']; p['assets']=[]; p['comparisons']=[]
        out=run_climate(state,'map-assets-to-hazards',p); self.assertEqual(out['result']['status'],'partial')

    def test_projection_and_observation_structural_failures(self):
        for field,value in [('scenario',None),('model',None),('kind','policy')]:
            state,p,_=climate_fixture(); p['hazards'][0]['context'][field]=value
            self.assertEqual(run_climate(state,'identify-climate-hazards',p)['result']['status'],'blocked')
        state,p,_=climate_fixture(); p['hazards'][0]['observed_date']='2026-10-06'
        self.assertEqual(run_climate(state,'identify-climate-hazards',p)['result']['status'],'blocked')
        state,p,_=climate_fixture(); p['hazards'][0]['physical_type']='policy'
        self.assertEqual(run_climate(state,'identify-climate-hazards',p)['result']['status'],'blocked')

    def test_cli_output_is_complete_helper_output_and_request_unchanged(self):
        state,h,p=climate_fixture()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'request.json'
            for skill,params in [('identify-climate-hazards',h),('map-assets-to-hazards',p)]:
                request={'contract_version':'0.1.0','skill':skill,'state':state,'parameters':params}
                path.write_text(json.dumps(request),encoding='utf-8'); before=path.read_bytes()
                run=subprocess.run([sys.executable,'-m','scripts.run_climate',str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(path.read_bytes(),before)
                out=run_climate(state,skill,params); self.assertEqual(json.loads(run.stdout),out); state=out['proposal']['state']

    def test_saved_author_capture_replays(self):
        path=ROOT/'evaluations/sus16-physical-screening.json'
        capture=json.loads(path.read_text(encoding='utf-8'))
        for entry in capture['executions']:
            request=entry['request']; self.assertEqual(run_climate(request['state'],request['skill'],request['parameters']),entry['output'])
