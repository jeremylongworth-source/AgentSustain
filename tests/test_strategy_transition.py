import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record
from tests.test_strategy_composition import composition_fixture
from tests.test_strategy_feasibility import feasibility_fixture


def transition_fixture():
    state, feasibility = feasibility_fixture()
    state = run_strategy(state, 'evaluate-target-feasibility', feasibility)['proposal']['state']
    _, composition = composition_fixture()
    composition['pillars'] = [composition['pillars'][1]]
    composition['pillars'][0]['feasibility_result_ids'] = [feasibility['result_id']]
    composition['objectives'] = [composition['objectives'][1]]
    composition['initiatives'] = [composition['initiatives'][1]]
    composition['strategy_review']['evidence_ids'] = ['ev-001']
    composition['strategy_review'].update(situation='Selected electricity objective only; other plant issues are outside this composed case.',
        rationale='Selected one-pillar source linkage, not approval or verified delivery.',
        trade_off_review='Other plant issues and cross-domain interactions remain unassessed; no offsets assumed.')
    state = run_strategy(state, 'build-sustainability-strategy', composition)['proposal']['state']
    owner = next(r for r in state['results'] if r['skill'] == 'develop-target')
    interim = json.loads(next(d['message'] for d in owner['diagnostics'] if d['code'] == 'STRATEGY_INPUTS'))
    interim['result_id'] = 'interim-target'; interim['target'].update(id='interim-2028', value=10, period={'start':'2028-01-01','end':'2028-12-31'})
    interim['target_review']['ambition_basis']='Proposed 10 percent interim reduction for 2028; ambition and delivery are not validated.'
    state = run_strategy(state, 'develop-target', interim)['proposal']['state']
    pathway = {'id':'energy-path', 'pillar_id':'energy', 'objective_ids':['energy-objective'], 'initiative_ids':['energy-investigation'],
        'target_result_id':'strategy-target', 'checkpoints':[{'target_result_id':'interim-target','feasibility_result_id':None,'scenario_id':None},
        {'target_result_id':'strategy-target','feasibility_result_id':'target-feasibility','scenario_id':'joint-upgrade'}],
        'mechanism':'Investigate a sourced engineering case; no implemented reduction is verified.', 'evidence_ids':['joint-outcome-evidence'],
        'evidence_fit':'reviewed_supporting', 'interaction_review':'Retain one joint modeled case; do not add project savings or interim reductions.',
        'external_dependency_review':'Equipment, market and workforce dependencies require investigation.', 'external_dependencies':None}
    decision = {'id':'engineering-decision','pathway_id':'energy-path','initiative_ids':['energy-investigation'],'kind':'decision',
        'description':'Prepare an unsent engineering and funding decision package.','acceptance_criterion':'Qualified reviewers document method fitness, resource needs and pending owner decision.',
        'owner':'Fictional engineering lead','due_date':'2027-03-01','depends_on':[],'evidence_ids':['joint-outcome-evidence'],'evidence_fit':'reviewed_supporting'}
    commissioning = copy.deepcopy(decision); commissioning.update(id='proposed-commissioning',kind='commissioning',
        description='Proposed commissioning subject to engineering, worker and funding decisions.',
        acceptance_criterion='Future commissioning records and accepted-service validation reviewed; no records currently exist.',
        due_date='2029-12-01',depends_on=['engineering-decision'],evidence_fit='unverified')
    review = copy.deepcopy(composition['strategy_review']); review.pop('situation'); review.pop('selection_basis')
    review.update(planning_basis='Selected proposed checkpoints and separately modeled case, not approved investment.',
        uncertainty_basis='Retain supplied bounds, growth, budget deficit and unresolved conditions; no delivery probability.')
    return state, {'strategy_result_id':composition['result_id'], 'plan':dict(composition['strategy'],id='plant-transition',name='Fictional selected transition'),
        'pathways':[pathway], 'milestones':[decision,commissioning], 'governance':{'owner':'Fictional transition reviewer','cadence':'annual',
        'reassessment_triggers':['Method or service changes','Funding decision','Missed milestones','Source corrections'],
        'evidence_ids':['ev-001'],'evidence_fit':'unverified'}, 'transition_review':review,'result_id':'transition-plan'}


class TransitionTests(unittest.TestCase):
    def test_sourced_checkpoints_growth_budget_and_history(self):
        state, p = transition_fixture(); before = copy.deepcopy(state)
        out = run_strategy(state, 'build-transition-plan', p); r = record(out, 'TRANSITION_PLAN')
        self.assertEqual(out['result']['status'], 'partial'); self.assertEqual(out['result']['metrics'], [])
        points = r['pathways'][0]['checkpoints']; self.assertEqual([c['endpoint_metric']['value'] for c in points], [9,8])
        self.assertEqual(points[1]['target_snapshot']['baseline_absolute_quantity']['value'],1000)
        self.assertIsNone(points[1]['target_snapshot']['absolute_future_quantity'])
        model = points[1]['modeled_case']; self.assertTrue(model['point_meets_proposed_objective'])
        self.assertEqual(model['source_outcome']['value'],1500); self.assertEqual(model['future_service']['value'],200)
        self.assertEqual(model['delivery_screen'],'known_conditions_not_met'); self.assertEqual(model['investment']['budget_minus_cost'],-100)
        self.assertIsNone(r['trajectory']); self.assertIsNone(r['portfolio_total'])
        self.assertEqual(r['proposed_sequence']['action_ids'],['engineering-decision','proposed-commissioning'])
        self.assertFalse(r['proposed_sequence']['completion_verified'])
        for flag in ('plan_adopted','funding_plan_approved','implementation_authorized','monitoring_started','public_claim_authorized','science_based_validated','net_zero_validated'):
            self.assertFalse(r[flag])
        self.assertEqual(state,before); after=out['proposal']['state']; validate_state(after)
        self.assertEqual(after['evidence'],before['evidence']); self.assertEqual(after['results'][:-1],before['results'])
        for key in ('review_requirements','data_gaps'):
            for item in before[key]: self.assertIn(item,after[key])

    def test_timing_reconciliation_and_missing_assessments(self):
        state,p=transition_fixture(); r=record(run_strategy(state,'build-transition-plan',p),'TRANSITION_PLAN')
        self.assertEqual(r['timing_conditions'][0]['target_result_id'],'interim-target')
        p['milestones'][1]['due_date']='2030-06-01'
        out=run_strategy(state,'build-transition-plan',p); r=record(out,'TRANSITION_PLAN')
        self.assertTrue(any(c['status']=='known_unmet_timing_assumption' for c in r['timing_conditions']))
        reasons=' '.join(g['reason'] for g in out['result']['data_gaps'])
        for text in ('no checkpoint feasibility','external technology','Governance proposal','differs from source strategy','known_conditions_not_met'):
            self.assertIn(text,reasons)

    def test_alternative_pathways_do_not_add_reused_sources(self):
        state,p=transition_fixture(); other=copy.deepcopy(p['pathways'][0]); other['id']='alternative-path'; p['pathways'].append(other)
        r=record(run_strategy(state,'build-transition-plan',p),'TRANSITION_PLAN')
        self.assertEqual(r['shared_dependency_ids']['strategy-target'],['alternative-path','energy-path'])
        self.assertIsNone(r['portfolio_total']); self.assertFalse(r['pathways'][1]['delivery_feasible'])

    def test_qualitative_pathway_omissions_and_overdue_proposals(self):
        state,composition=composition_fixture(); state=run_strategy(state,'build-sustainability-strategy',composition)['proposal']['state']
        _,p=transition_fixture(); p['pathways']=[dict(p['pathways'][0],id='people-path',pillar_id='people',objective_ids=['worker-objective'],
            initiative_ids=['worker-review'],target_result_id=None,checkpoints=[],evidence_ids=['worker-note'])]
        p['plan']['horizon']['start']='2026-10-05'; p['milestones']=[]; p['governance']=None
        out=run_strategy(state,'build-transition-plan',p); r=record(out,'TRANSITION_PLAN')
        self.assertEqual(r['pathways'][0]['checkpoints'],[]); self.assertIsNone(r['proposed_sequence'])
        self.assertTrue(any('energy-objective: strategy objective omitted' in g['reason'] for g in out['result']['data_gaps']))
        state,p=transition_fixture(); p['transition_review']['as_of_date']='2027-04-01'; p['plan']['review_date']='2027-06-01'
        r=record(run_strategy(state,'build-transition-plan',p),'TRANSITION_PLAN')
        self.assertEqual(r['milestones'][0]['status'],'overdue_unverified'); self.assertFalse(r['milestones'][0]['completion_verified'])

    def test_invalid_links_dates_scope_and_scenarios_block(self):
        state,original=transition_fixture()
        mutations=[lambda p:p['pathways'][0].update(objective_ids=[]),lambda p:p['pathways'][0].update(initiative_ids=['unknown']),
            lambda p:p['pathways'][0].update(target_result_id='interim-target'),lambda p:p['pathways'][0]['checkpoints'].reverse(),
            lambda p:p['pathways'][0]['checkpoints'][1].update(scenario_id='unknown'),
            lambda p:p['pathways'][0]['checkpoints'][0].update(scenario_id='unbacked'),
            lambda p:p['pathways'][0]['checkpoints'][0].update(feasibility_result_id='target-feasibility',scenario_id='joint-upgrade'),
            lambda p:p['milestones'][0].update(depends_on=['proposed-commissioning']),
            lambda p:p['milestones'][0].update(depends_on=['engineering-decision']),
            lambda p:p['milestones'][0].update(acceptance_criterion=''),lambda p:p['milestones'][0].update(due_date='2031-01-01'),
            lambda p:p['transition_review'].update(scope='Different organization'),lambda p:p['transition_review'].update(as_of_date='2026-01-01'),
            lambda p:p['plan']['horizon'].update(end='2031-12-31'),lambda p:p['governance'].update(reassessment_triggers=[])]
        for mutation in mutations:
            p=copy.deepcopy(original); mutation(p); out=run_strategy(state,'build-transition-plan',p)
            self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_external_conditions_and_cyclic_milestones(self):
        state,p=transition_fixture(); p['pathways'][0]['external_dependencies']=[{'id':'funding-market','domain':'market',
            'description':'Selected budget is less than quote; external financing is not recorded.','owner':'Fictional finance lead','status':'known_unmet',
            'evidence_ids':['available-budget-evidence'],'evidence_fit':'reviewed_supporting'}]
        out=run_strategy(state,'build-transition-plan',p); r=record(out,'TRANSITION_PLAN')
        self.assertFalse(r['pathways'][0]['external_dependencies'][0]['fulfilment_verified'])
        self.assertTrue(any('external condition remains known_unmet' in g['reason'] for g in out['result']['data_gaps']))
        p['pathways'][0]['external_dependencies'][0]['evidence_fit']='unverified'
        self.assertEqual(run_strategy(state,'build-transition-plan',p)['result']['status'],'blocked')
        state,p=transition_fixture(); p['milestones'][0]['due_date']=p['milestones'][1]['due_date']; p['milestones'][0]['depends_on']=['proposed-commissioning']
        out=run_strategy(state,'build-transition-plan',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any('cycle' in d['message'] for d in out['result']['diagnostics']))

    def test_changed_source_and_missing_factor_ancestry_block(self):
        state,p=transition_fixture(); state['evidence'][0]['source']['title']='Changed raw source'
        self.assertEqual(run_strategy(state,'build-transition-plan',p)['result']['status'],'blocked')
        state,p=transition_fixture(); owner=state['results'][0]; owner['status']='partial'; owner['review_states'].append('EVIDENCE_INCOMPLETE')
        owner['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved factor lineage.'})
        missing={'id':'factor-gap','field':'emission_factor','reason':'Missing factor.','impact':'No defensible calculation.','remedy':'Obtain defensible factor.'}
        owner['data_gaps'].append(missing); state['data_gaps'].append(copy.deepcopy(missing))
        out=run_strategy(state,'build-transition-plan',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))
        strategy_owner=next(r for r in state['results'] if r['id']==p['strategy_result_id'])
        strategy_inputs=json.loads(next(d['message'] for d in strategy_owner['diagnostics'] if d['code']=='STRATEGY_INPUTS'))
        strategy_inputs['result_id']='blocked-strategy'
        blocked=run_strategy(state,'build-sustainability-strategy',strategy_inputs)
        self.assertEqual(blocked['result']['status'],'blocked'); self.assertEqual(blocked['result']['metrics'],[])
        p['strategy_result_id']='blocked-strategy'
        out=run_strategy(blocked['proposal']['state'],'build-transition-plan',p)
        self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_checkpoint_definition_cannot_change_service_or_overlap(self):
        state,p=transition_fixture(); target=next(r for r in state['results'] if r['id']=='interim-target')
        inputs=json.loads(next(d['message'] for d in target['diagnostics'] if d['code']=='STRATEGY_INPUTS'))
        inputs['result_id']='overlapping-target'; inputs['target']['period']={'start':'2030-01-01','end':'2030-12-31'}
        state=run_strategy(state,'develop-target',inputs)['proposal']['state']; p['pathways'][0]['checkpoints'][0]['target_result_id']='overlapping-target'
        self.assertEqual(run_strategy(state,'build-transition-plan',p)['result']['status'],'blocked')
        state,p=transition_fixture(); definition_owner=next(r for r in state['results'] if r['skill']=='define-kpis')
        definitions=json.loads(next(d['message'] for d in definition_owner['diagnostics'] if d['code']=='STRATEGY_INPUTS'))
        definitions['result_id']='absolute-definition'; definitions['definitions'][0].update(id='absolute-kpi',kind='absolute',denominator_metric_id=None,denominator_review=None)
        state=run_strategy(state,'define-kpis',definitions)['proposal']['state']
        target_owner=next(r for r in state['results'] if r['id']=='interim-target')
        inputs=json.loads(next(d['message'] for d in target_owner['diagnostics'] if d['code']=='STRATEGY_INPUTS'))
        inputs.update(result_id='incompatible-target',definition_result_id='absolute-definition',kpi_id='absolute-kpi'); inputs['target']['kind']='absolute'
        state=run_strategy(state,'develop-target',inputs)['proposal']['state']; p['pathways'][0]['checkpoints'][0]['target_result_id']='incompatible-target'
        out=run_strategy(state,'build-transition-plan',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any('physical service and accounting definition' in d['message'] for d in out['result']['diagnostics']))

    def test_saved_capture_replays(self):
        path=ROOT/'evaluations/sus15-transition-workflow.json'
        capture=json.loads(path.read_text(encoding='utf-8')); request=capture['request']
        self.assertEqual(run_strategy(request['state'],request['skill'],request['parameters']),capture['output'])
