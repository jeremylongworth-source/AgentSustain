import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record, strategy_fixture
from tests.test_strategy_stakeholders import stakeholder_fixture
from tests.test_strategy_materiality import materiality_fixture
from tests.test_strategy_registers import register_fixture, opportunity_fixture


def composition_fixture():
    state, base, kpis, target = strategy_fixture()
    qualitative, mapping = stakeholder_fixture()
    state['evidence'].extend(copy.deepcopy([e for e in qualitative['evidence'] if e['id'] in {'worker-note','manager-note'}]))
    for skill,p in [('establish-baseline',base),('define-kpis',kpis),('develop-target',target),('map-stakeholders',mapping)]:
        state=run_strategy(state,skill,p)['proposal']['state']
    _,material=materiality_fixture(); _,risks=register_fixture(); _,opportunities=opportunity_fixture()
    for skill,p in [('identify-material-sustainability-issues',material),('identify-sustainability-risks',risks),('identify-sustainability-opportunities',opportunities)]:
        state=run_strategy(state,skill,p)['proposal']['state']
    empty={'materiality_result_id':None,'topic_ids':[],'risk_result_id':None,'risk_ids':[],'opportunity_result_id':None,'opportunity_ids':[],
        'target_result_ids':[],'feasibility_result_ids':[],'context_result_ids':[]}
    people=dict(empty,id='people',name='Scheduling interests',scope=mapping['mapping_review']['scope'],selection_rationale='Retain worker harm and missing engagement, not management popularity.',
        materiality_result_id=material['result_id'],topic_ids=['work-scheduling'],risk_result_id=risks['result_id'],risk_ids=['schedule-risk'],
        opportunity_result_id=opportunities['result_id'],opportunity_ids=['notice-opportunity'],context_result_ids=[mapping['result_id']])
    energy=dict(empty,id='energy',name='Selected purchased electricity',scope=target['target_review']['scope'],selection_rationale='Preserve intensity target and gross baseline context without implying worker harm mitigation.',target_result_ids=[target['result_id']])
    objectives=[{'id':'worker-objective','pillar_id':'people','description':'Investigate worker scheduling needs and prevention pathways.','topic_ids':['work-scheduling'],
        'target_result_ids':[],'rationale':'Selected prospective impact requires source and affected-group review.','owner':'Fictional people lead'},
        {'id':'energy-objective','pillar_id':'energy','description':'Investigate delivery of proposed selected electricity intensity endpoint.','topic_ids':[],
        'target_result_ids':[target['result_id']],'rationale':'Proposed 8 kWh/count endpoint is not a delivery forecast or gross reduction claim.','owner':'Fictional energy lead'}]
    action={'id':'worker-review','pillar_id':'people','description':'Prepare an unsent worker review and trial proposal.','mechanism':'Review participation and advance notice before assessing actual prevention.',
        'objective_ids':['worker-objective'],'opportunity_ids':['notice-opportunity'],'target_result_ids':[],'owner':'Fictional engagement lead','target_date':'2027-02-01',
        'depends_on':[],'resource_review':None,'monitoring_plan':None,'evidence_ids':['worker-note'],'evidence_fit':'reviewed_supporting'}
    energy_action=copy.deepcopy(action); energy_action.update(id='energy-investigation',pillar_id='energy',description='Investigate a technically supported energy delivery scenario.',
        mechanism='Collect equipment and service evidence before claiming intensity delivery.',objective_ids=['energy-objective'],opportunity_ids=[],target_result_ids=[target['result_id']],
        owner='Fictional engineering lead',target_date='2028-01-01',evidence_ids=['ev-001'],monitoring_plan={'owner':'Fictional meter analyst','frequency':'annual',
        'method':'Use matched meter and equivalent-output records; no observation cycle has started.','evidence_ids':['ev-001','service-record'],'evidence_fit':'reviewed_supporting'})
    review={'confirmed':True,'reviewer_role':'Fictional strategy analyst','rationale':'Selected two-pillar source linkage, not approval or verified delivery.',
        'evidence_ids':['worker-note','ev-001'],'boundary_id':state['organizational_boundary']['id'],'scope':'Selected fictional plant strategy',
        'situation':'Separate scheduling impacts and electricity objectives with incomplete coverage.','selection_basis':'Source-linked selected concerns and proposed targets.',
        'coverage_limitations':'Other sites/topics and delivery/funding are not assessed.','trade_off_review':'No quantified cross-pillar interactions or offsets are assumed.',
        'period':state['reporting_period'],'as_of_date':'2026-10-05','coverage_complete':False}
    return state,{'strategy':{'id':'plant-strategy','name':'Fictional selected plant strategy','purpose':'Prepare issue-linked decisions without claiming implementation.',
        'horizon':{'start':'2026-10-05','end':'2030-12-31'},'owner':'Fictional proposed strategy owner','review_date':'2027-03-01'},
        'pillars':[people,energy],'objectives':objectives,'initiatives':[action,energy_action],'strategy_review':review,'result_id':'strategy-proposal'}


class CompositionTests(unittest.TestCase):
    def execute(self,p,state=None): return run_strategy(state or composition_fixture()[0],'build-sustainability-strategy',p)

    def test_source_reproduced_two_pillar_proposal_preserves_state(self):
        state,p=composition_fixture(); before=copy.deepcopy(state); out=self.execute(p,state); r=record(out,'STRATEGY_PROPOSAL')
        target=r['dependency_snapshots']['strategy-target']; self.assertEqual(target['metrics'][0]['value'],8); self.assertEqual(target['metrics'][0]['unit'],'kWh/count')
        self.assertEqual(target['report']['baseline_absolute_quantity']['value'],1000); self.assertIsNone(target['report']['absolute_future_quantity'])
        self.assertEqual(len(r['pillars']),2); self.assertEqual(out['result']['metrics'],[])
        for flag in ('strategy_adopted','owner_acceptance_verified','funding_authorized','implementation_authorized','public_claim_authorized'): self.assertFalse(r[flag])
        self.assertIsNone(r['aggregate_reduction']); self.assertIsNone(r['portfolio_benefit']); self.assertEqual(state,before)
        self.assertEqual(out['proposal']['state']['evidence'],before['evidence']); validate_state(out['proposal']['state'])
        for item in before['review_requirements']: self.assertIn(item,out['result']['review_requirements'])
        for item in before['data_gaps']: self.assertIn(item,out['result']['data_gaps'])

    def test_missing_funding_monitoring_feasibility_and_open_delivery(self):
        _,p=composition_fixture(); out=self.execute(p); r=record(out,'STRATEGY_PROPOSAL')
        self.assertFalse(r['initiatives'][0]['monitoring_started']); self.assertFalse(r['initiatives'][1]['delivery_feasible'])
        for substring in ('resource/funding','monitoring method/ownership','no target-feasibility'):
            self.assertTrue(any(substring in g['reason'] for g in out['result']['data_gaps']))

    def test_omitted_topics_and_risks_retained_not_immaterial(self):
        _,p=composition_fixture(); p['pillars'][0].update(topic_ids=[],risk_ids=[]); p['objectives'][0]['topic_ids']=[]
        out=self.execute(p); self.assertEqual(out['result']['status'],'partial')
        self.assertTrue(any('not selected' in g['reason'] for g in out['result']['data_gaps']))
        self.assertTrue(any('unaddressed' in g['reason'] for g in out['result']['data_gaps']))

    def test_sequence_dependencies_and_overdue_proposal(self):
        _,p=composition_fixture(); p['initiatives'][1]['depends_on']=['worker-review']
        r=record(self.execute(p),'STRATEGY_PROPOSAL'); self.assertEqual(r['proposed_sequence']['action_ids'],['worker-review','energy-investigation'])
        p['strategy']['horizon']['start']='2026-01-01'; p['initiatives'][0]['target_date']='2026-02-01'
        self.assertEqual(record(self.execute(p),'STRATEGY_PROPOSAL')['initiatives'][0]['status'],'overdue_unverified')

    def test_invalid_graph_scope_horizon_and_reference_links_block(self):
        mutations=[lambda p:p['initiatives'][0].update(depends_on=['energy-investigation']),
            lambda p:p['initiatives'][0].update(objective_ids=['energy-objective']),lambda p:p['initiatives'][0].update(opportunity_ids=['missing']),
            lambda p:p['pillars'][1].update(scope='Other meter'),lambda p:p['strategy']['horizon'].update(end='2029-12-31'),
            lambda p:p['strategy'].update(review_date='2026-01-01'),lambda p:p['initiatives'][0].update(owner=''),
            lambda p:p['pillars'][0]['context_result_ids'].append('strategy-target'),lambda p:p['objectives'][1].update(target_result_ids=[])]
        for mutation in mutations:
            _,p=composition_fixture(); mutation(p); self.assertEqual(self.execute(p)['result']['status'],'blocked')

    def test_changed_sources_and_missing_factor_ancestry_block(self):
        state,p=composition_fixture(); state['evidence'][-1]['source']['title']='Changed source'
        self.assertEqual(self.execute(p,state)['result']['status'],'blocked')
        state,p=composition_fixture(); owner=next(r for r in state['results'] if r['id']=='strategy-risks')
        inputs=json.loads(next(d['message'] for d in owner['diagnostics'] if d['code']=='STRATEGY_INPUTS')); inputs['result_id']='other-risks'
        state=run_strategy(state,'identify-sustainability-risks',inputs)['proposal']['state']; p['pillars'][0]['risk_result_id']='other-risks'
        self.assertEqual(self.execute(p,state)['result']['status'],'blocked')
        state,p=composition_fixture(); state['results'][0]['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Source quantity factor ancestry unresolved.'})
        state['results'][0]['status']='partial'
        state['results'][0]['review_states'].append('EVIDENCE_INCOMPLETE')
        factor_gap={'id':'source-factor-gap','field':'emission_factor','reason':'Factor ancestry unresolved.','impact':'No defensible quantity claim.','remedy':'Supply a defensible factor.'}
        state['results'][0]['data_gaps'].append(factor_gap); state['data_gaps'].append(copy.deepcopy(factor_gap))
        out=self.execute(p,state); self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_shared_target_source_not_independent_effects(self):
        _,p=composition_fixture(); duplicate=copy.deepcopy(p['pillars'][1]); duplicate.update(id='other-energy',name='Second view of same meter')
        p['pillars'].append(duplicate)
        r=record(self.execute(p),'STRATEGY_PROPOSAL'); self.assertEqual(r['shared_dependency_ids']['strategy-target'],['energy','other-energy'])
        self.assertIsNone(r['aggregate_reduction'])

    def test_unserved_objectives_and_empty_initiatives_stay_open(self):
        _,p=composition_fixture(); p['initiatives']=[]; out=self.execute(p)
        self.assertEqual(out['result']['status'],'partial'); self.assertTrue(any('no initiative response' in g['reason'] for g in out['result']['data_gaps']))

    def test_feasibility_numerical_coverage_does_not_approve_funding(self):
        from tests.test_strategy_feasibility import feasibility_fixture
        state,screen=feasibility_fixture(); state=run_strategy(state,'evaluate-target-feasibility',screen)['proposal']['state']
        _,p=composition_fixture(); p['pillars']=p['pillars'][1:]; p['objectives']=p['objectives'][1:]; p['initiatives']=p['initiatives'][1:]
        p['strategy_review']['evidence_ids']=['ev-001']; p['pillars'][0]['feasibility_result_ids']=[screen['result_id']]
        r=record(self.execute(p,state),'STRATEGY_PROPOSAL'); snapshot=r['dependency_snapshots']['target-feasibility']['report']
        self.assertTrue(snapshot['scenarios'][0]['point_meets_proposed_objective']); self.assertIsNone(snapshot['selected_scenario_id'])
        self.assertEqual(snapshot['scenarios'][0]['delivery_screen'],'known_conditions_not_met'); self.assertFalse(r['funding_authorized'])
        self.assertFalse(r['initiatives'][0]['delivery_feasible'])

    def test_saved_capture_replays(self):
        capture=json.loads((ROOT/'evaluations/sus15-strategy-composition.json').read_text(encoding='utf-8')); req=capture['request']
        self.assertEqual(run_strategy(req['state'],req['skill'],req['parameters']),capture['output'])
