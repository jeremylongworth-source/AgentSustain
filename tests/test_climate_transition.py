import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.climate_tools import CODE, run_climate
from scripts.contract_validation import ROOT, validate_state
from tests.test_climate import climate_fixture, report


def transition_fixture(family='policy'):
    state, physical, _ = climate_fixture()
    source = copy.deepcopy(state['evidence'][-1]); source['id'] = 'transition-source'
    source['source'].update(title='Fictional attributed transition note', locator='fixture:transition-note')
    source['method'].update(name='Fictional source excerpt', source='fixture:transition-note')
    source['uncertainty']['description'] = 'Wholly fictional note; source status and organizational effects unverified.'
    state['evidence'].append(source)
    contexts = {
        'policy': {'instrument':'Fictional consultation proposal P1','jurisdiction':'Fictional jurisdiction only',
            'source_described_status':'proposed','effective_period':None,'applicability_conditions':'Coverage thresholds and commencement not adopted; organization coverage unresolved.'},
        'market': {'signal_kind':'demand','market_segment':'Selected fictional buyer segment','geography':'Fictional region',
            'comparison_basis':'One exploratory buyer note, no representative demand sample or price series.',
            'signal_period':{'start':'2026-10-01','end':'2026-10-05'}},
        'technology': {'technology':'Fictional lower-emission process candidate','version':'fictional-pilot-1',
            'source_described_maturity':'pilot','service_requirements':'Actual required throughput and product quality untested.',
            'dependencies':'Infrastructure, skilled staff, validated performance and capital remain unresolved.'},
        'reputation': {'statement_kind':'allegation','affected_groups':'One fictional anonymous stakeholder statement',
            'representation_basis':'No representative mandate or verified underlying facts.','response_observed':False},
    }
    driver={'id':family+'-driver','name':'Fictional '+family+' transition concern',
        'climate_transition_link':'Source describes changes associated with a lower-emission economy; not physical rain damage.',
        'mechanism':'Conditional '+family+' change could affect selected service choices; no quantified loss or proven causation.',
        'affected_scope':'Selected fictional plant service','owner':'Fictional proposed source-review owner',
        'scenario':'Fictional exploratory transition case','horizon':{'start':'2030-01-01','end':'2035-12-31'},
        'context':contexts[family],'evidence_ids':['transition-source'],'evidence_fit':'reviewed_supporting',
        'observed_date':'2026-10-03','source_fragment':'Fictional selected '+family+' note; unverified future organizational effects.',
        'limitations':'No actual law, company, price, technology or stakeholder finding.'}
    review=copy.deepcopy(physical['hazard_review']); review.update(method='source_transition_register',evidence_ids=['transition-source'],
        selection_basis='One fictional selected transition note; no organization-wide coverage.',exclusions=['Other drivers and affected services'])
    return state,{'drivers':[driver],'transition_review':review,'result_id':'transition-'+family}


class TransitionDriverTests(unittest.TestCase):
    families=['policy','market','technology','reputation']

    def test_four_families_preserve_source_context_and_history_without_determinations(self):
        for family in self.families:
            state,p=transition_fixture(family); original=copy.deepcopy(state); skill='identify-'+family+'-risk'
            out=run_climate(state,skill,p); rec=report(out,CODE[skill]); row=rec['drivers'][0]
            self.assertEqual(out['result']['status'],'partial'); self.assertEqual(row['family'],family)
            self.assertEqual(row['context'],p['drivers'][0]['context']); self.assertEqual(row['sources'][0],state['evidence'][-1])
            self.assertEqual(row['source_support'],'source_transition_candidate'); self.assertEqual(out['result']['metrics'],[])
            for k in ['legal_applicability_determined','compliance_determined','organization_exposure_verified','replacement_feasible','response_causation_verified','risk_accepted','implementation_authorized']:
                self.assertFalse(row[k])
            for k in ['likelihood','financial_effect','risk_score']: self.assertIsNone(row[k])
            self.assertEqual(state,original); final=out['proposal']['state']; self.assertEqual(final['results'][:-1],state['results'])
            for k in ['evidence','energy','organization','organizational_boundary']: self.assertEqual(final[k],state[k])
            for k in ['data_gaps','review_requirements','assumptions']:
                for x in state[k]: self.assertIn(x,final[k])
            validate_state(final)

    def test_unknown_unfit_dates_versions_and_horizons_never_clear_risk(self):
        for family in self.families:
            for mode in ['date','fit','version','horizon','period']:
                state,p=transition_fixture(family); row=p['drivers'][0]
                if mode=='date': row['observed_date']=None
                if mode=='fit': row['evidence_fit']='irrelevant'
                if mode=='version': state['evidence'][-1]['source']['version']=None
                if mode=='horizon': row['horizon']=None
                if mode=='period': row['observed_date']='2026-09-30'
                out=run_climate(state,'identify-'+family+'-risk',p); rec=report(out,CODE['identify-'+family+'-risk'])
                self.assertEqual(out['result']['status'],'partial')
                if mode!='horizon': self.assertEqual(rec['drivers'][0]['source_support'],'unverified')
                self.assertFalse(rec['risk_accepted'])

    def test_bad_references_dates_shapes_and_duplicates_block(self):
        for family in self.families:
            for mode in ['source','future','duplicate','wrong-context','horizon','boundary']:
                state,p=transition_fixture(family)
                if mode=='source': p['drivers'][0]['evidence_ids']=['missing']
                if mode=='future': p['drivers'][0]['observed_date']='2026-10-06'
                if mode=='duplicate': p['drivers'].append(copy.deepcopy(p['drivers'][0]))
                if mode=='wrong-context': p['drivers'][0]['context']={'status':'safe'}
                if mode=='horizon': p['drivers'][0]['horizon']={'start':'2035-01-01','end':'2030-01-01'}
                if mode=='boundary': p['transition_review']['boundary_id']='wrong'
                out=run_climate(state,'identify-'+family+'-risk',p)
                self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_source_policy_status_never_becomes_organization_obligation(self):
        for status in ['proposed','adopted','in_force','repealed','unknown']:
            state,p=transition_fixture(); p['drivers'][0]['context']['source_described_status']=status
            rec=report(run_climate(state,'identify-policy-risk',p),CODE['identify-policy-risk'])
            self.assertFalse(rec['drivers'][0]['legal_applicability_determined']); self.assertFalse(rec['legal_determination'])

    def test_empty_selected_list_retains_coverage_and_reviews(self):
        state,p=transition_fixture(); p['drivers']=[]; p['transition_review'].update(coverage_complete=True,exclusions=[])
        out=run_climate(state,'identify-policy-risk',p); self.assertEqual(out['result']['status'],'partial')
        self.assertTrue(any('coverage incomplete' in g['reason'] for g in out['result']['data_gaps']))

    def test_cli_matches_complete_output_and_preserves_request_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'request.json'
            for family in self.families:
                state,p=transition_fixture(family); skill='identify-'+family+'-risk'
                req={'contract_version':'0.1.0','state':state,'skill':skill,'parameters':p}
                f.write_text(json.dumps(req),encoding='utf-8'); before=f.read_bytes()
                run=subprocess.run([sys.executable,'-m','scripts.run_climate',str(f)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(json.loads(run.stdout),run_climate(state,skill,p)); self.assertEqual(f.read_bytes(),before)


if __name__=='__main__': unittest.main()
