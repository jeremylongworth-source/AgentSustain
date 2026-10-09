import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.framework_tools import run_framework
from scripts.ghg_inventory import build_inventory
from scripts.scope_accounting import compose_scope
from tests.test_scope_accounting import scope_fixture


def pin(ident):
    raw=(ROOT/'standards/frameworks'/ (ident+'.json')).read_bytes()
    return {'adapter_id':ident,'catalog_sha256':hashlib.sha256(raw).hexdigest()}


def framework_fixture():
    state,sources,components,coverage=scope_fixture()
    state=compose_scope(state,'calculate-location-based-scope-2',sources,components,coverage,'selected-energy',True)['proposal']['state']
    screening=[{'category':i,'status':'unknown','evidence_ids':['ev-001'],'rationale':'Fictional selected electricity only; value-chain coverage not known.'} for i in range(1,16)]
    review={'confirmed':True,'evidence_ids':['ev-001'],'rationale':'Fictional selected account only, scope 1 missing and not zero.','gwp_basis':coverage['gwp_basis']}
    state=build_inventory(state,None,'selected-energy',[],screening,review,'selected-inventory',True)['proposal']['state']
    mapping={'boundary_id':state['organizational_boundary']['id'],'period':copy.deepcopy(state['reporting_period']),'as_of_date':'2026-10-05',
        'scope':'Fictional selected inventory draft mapping','evidence_ids':['ev-001'],'evidence_fit':'reviewed_supporting',
        'rationale':'Original fictional exercise and a TNFD referral, not complete external compliance.','reviewer_role':'Qualified framework/source/rights and accountable-owner reviewer'}
    adapters=[]
    for ident in ['fictional-review-exercise-2','tnfd-2023-ghg-referral']:
        adapters.append(dict(pin(ident),version_rationale='Fictional selected source edition only; later guidance, license and current applicability require review.',
            evidence_ids=['ev-001'],evidence_fit='reviewed_supporting',requested_requirement_ids=[]))
    return state,{'inventory_result_id':'selected-inventory','adapters':adapters,'notes':[],
        'mapping_review':mapping,'fixture_mode':True,'result_id':'framework-map'}


def record(output,code='FRAMEWORK_DISCLOSURE_MAP'):
    return json.loads(next(d['message'] for d in output['result']['diagnostics'] if d['code']==code))


class FrameworkTests(unittest.TestCase):
    def test_two_frameworks_preserve_one_core_lineage_and_missing_scope(self):
        state,p=framework_fixture(); old=copy.deepcopy(state); out=run_framework(state,'map-framework-disclosures',p)
        self.assertEqual(out['result']['status'],'partial'); r=record(out); self.assertEqual(len(r['adapters']),2)
        gross=next(x for x in r['adapters'][0]['rows'] if x['requirement']['id']=='exercise-account')
        self.assertEqual(gross['missing_core_fields'],['scope_1','gross_basis']); self.assertNotIn('scope_1',gross['core_values'])
        original=state['results'][-2]['metrics'][0]
        selected=gross['core_values']['scope_2'][0]
        self.assertEqual(selected['original_metrics'][0],original)
        self.assertEqual(selected['display_t_CO2e'],0.5)
        referral=r['adapters'][1]['rows'][0]; self.assertEqual(referral['status'],'reference_only_external_requirements_pending')
        self.assertEqual(referral['core_values']['inventory_reference']['metrics'],state['results'][-1]['metrics'])
        self.assertEqual(r['calculation_lineage_result_ids'],['selected-energy','selected-inventory'])
        self.assertFalse(referral['fulfillment_verified']); self.assertEqual(out['result']['metrics'],[])
        for k in ['conformity_verified','legal_applicability_determined','assurance_verified','public_claim_authorized','publication_authorized','commercial_use_authorized']: self.assertFalse(r[k])
        self.assertEqual(state,old); final=out['proposal']['state']; validate_state(final)
        self.assertEqual(final['results'][:-1],state['results'])
        for k,v in state.items():
            if k in ['data_gaps','assumptions','review_requirements']:
                for x in v: self.assertIn(x,final[k])
            elif k not in ['results','revision']: self.assertEqual(v,final[k])

    def test_unverified_applicability_and_notes_cannot_fulfill_missing_fields(self):
        state,p=framework_fixture(); p['adapters'][0]['evidence_fit']='unverified'
        p['notes']=[{'adapter_id':p['adapters'][0]['adapter_id'],'requirement_id':'exercise-question',
            'text':'Fictional copied source claims every gas is covered; no gas-resolved measurement supplied.',
            'evidence_ids':['ev-001'],'evidence_fit':'unverified','observed_date':None,'limitations':'Source data absent.'}]
        r=record(run_framework(state,'map-framework-disclosures',p))
        row=next(x for x in r['adapters'][0]['rows'] if x['requirement']['id']=='exercise-question')
        self.assertEqual(row['source_fit'],'unverified'); self.assertEqual(row['missing_core_fields'],['reviewer_answer']); self.assertFalse(row['fulfillment_verified'])
        self.assertEqual(row['note'],p['notes'][0])

    def test_unsupported_requirements_are_retained_as_gaps(self):
        state,p=framework_fixture(); p['adapters'][0]['requested_requirement_ids']=['unimplemented-claims']
        out=run_framework(state,'map-framework-disclosures',p); self.assertEqual(out['result']['status'],'partial')
        self.assertEqual(record(out)['adapters'][0]['unsupported_requirement_ids'],['unimplemented-claims'])
        self.assertTrue(any('unimplemented-claims' in g['reason'] for g in out['result']['data_gaps']))

    def test_pinned_diff_retains_original_fictional_versions(self):
        state,p=framework_fixture(); args={'before':pin('fictional-review-exercise-1'),'after':pin('fictional-review-exercise-2'),
            'mapping_review':p['mapping_review'],'result_id':'mapping-diff','fixture_mode':True}
        old=copy.deepcopy(state); out=run_framework(state,'compare-framework-mappings',args)
        self.assertEqual(out['result']['status'],'partial'); r=record(out,'FRAMEWORK_MAPPING_DIFF')
        self.assertEqual(r['changed_ids'],['exercise-question']); self.assertEqual(r['added_ids'],['exercise-context']); self.assertEqual(r['removed_ids'],[])
        self.assertTrue(r['before']['synthetic']); self.assertTrue(r['after']['synthetic']); self.assertFalse(r['after']['source_verified'])
        self.assertFalse(r['migration_applied']); self.assertEqual(state,old)

    def test_diff_rejects_source_chronology_same_version_and_different_framework(self):
        for mode in ['date','same','framework']:
            state,p=framework_fixture(); args={'before':pin('fictional-review-exercise-1'),'after':pin('fictional-review-exercise-2'),
                'mapping_review':p['mapping_review'],'result_id':'bad-diff','fixture_mode':True}
            if mode=='date': args['mapping_review']['as_of_date']='2026-10-04'
            elif mode=='same': args['after']=copy.deepcopy(args['before'])
            else: args['after']=pin('tnfd-2023-ghg-referral')
            self.assertEqual(run_framework(state,'compare-framework-mappings',args)['result']['status'],'blocked',mode)

    def test_bad_pin_scope_date_unknown_adapter_and_notes_block(self):
        for mode in ['pin','adapter','scope','period','date','duplicate','note','future','fixture']:
            state,p=framework_fixture()
            if mode=='pin': p['adapters'][0]['catalog_sha256']='0'*64
            elif mode=='adapter': p['adapters'][0]['adapter_id']='../other'
            elif mode=='scope': p['mapping_review']['boundary_id']='other'
            elif mode=='period': p['mapping_review']['period']['start']='2024-01-01'
            elif mode=='date': p['mapping_review']['as_of_date']='2026-10-04'
            elif mode=='duplicate': p['adapters'].append(copy.deepcopy(p['adapters'][0]))
            elif mode in ['note','future']:
                p['notes']=[{'adapter_id':p['adapters'][0]['adapter_id'],'requirement_id':'unknown' if mode=='note' else 'exercise-trace',
                    'text':'Fictional copied claim.','evidence_ids':['ev-001'],'evidence_fit':'reviewed_supporting','observed_date':'2027-01-01' if mode=='future' else None,'limitations':'Needs review.'}]
            else: p['fixture_mode']='yes'
            self.assertEqual(run_framework(state,'map-framework-disclosures',p)['result']['status'],'blocked',mode)

    def test_changed_inventory_metric_record_lineage_and_factor_block(self):
        for mode in ['metric','record','lineage','factor','source-reference']:
            state,p=framework_fixture(); owner=state['results'][-1]
            if mode=='metric': owner['metrics'][0]['value']=999
            elif mode=='record':
                d=next(d for d in owner['diagnostics'] if d['code']=='INVENTORY_SELECTION'); r=json.loads(d['message']); r['limits']='Complete verified inventory.'; d['message']=json.dumps(r)
            elif mode=='source-reference':
                d=next(d for d in owner['diagnostics'] if d['code']=='INVENTORY_SELECTION'); r=json.loads(d['message']); r['included'][0]['result_id']='absent'; d['message']=json.dumps(r)
            elif mode=='lineage':
                ev=copy.deepcopy(state['evidence'][0]); ev['id']='unrelated'; state['evidence'].append(ev); owner['evidence_ids'].append('unrelated')
            else: owner['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Missing defensible factor.'})
            out=run_framework(state,'map-framework-disclosures',p); self.assertEqual(out['result']['status'],'blocked',mode)
            if mode=='factor': self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_scope_uncertainty_method_and_extra_lineage_tampering_block(self):
        for mode in ['uncertainty','method','lineage']:
            state,p=framework_fixture(); scope=state['results'][-2]
            if mode=='uncertainty': scope['metrics'][0]['uncertainty']['description']='Verified exact without uncertainty.'
            elif mode=='method': scope['metrics'][0]['method']['version']='unrecorded-revision'
            else:
                ev=copy.deepcopy(state['evidence'][0]); ev['id']='unrelated'; state['evidence'].append(ev); scope['evidence_ids'].append('unrelated')
            out=run_framework(state,'map-framework-disclosures',p); self.assertEqual(out['result']['status'],'blocked',mode)
            self.assertEqual(out['result']['metrics'],[])

    def test_fixture_factor_not_usable_in_normal_mode(self):
        state,p=framework_fixture(); p['fixture_mode']=False
        out=run_framework(state,'map-framework-disclosures',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_actual_cli_equal_and_request_unchanged(self):
        state,p=framework_fixture(); req={'contract_version':'0.1.0','state':state,'skill':'map-framework-disclosures','parameters':p}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'request.json'; path.write_text(json.dumps(req),encoding='utf-8'); before=path.read_bytes()
            cli=subprocess.run([sys.executable,'-m','scripts.run_framework',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stderr); self.assertEqual(json.loads(cli.stdout),run_framework(state,req['skill'],p)); self.assertEqual(path.read_bytes(),before)
