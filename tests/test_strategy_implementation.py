import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record
from tests.test_strategy_transition import transition_fixture


def implementation_fixture():
    state, transition = transition_fixture()
    template = copy.deepcopy(state['results'][0]['metrics'][0])
    def rate(ident, value, window):
        source = copy.deepcopy(state['evidence'][0]); source.update(id=ident+'-source', unit='h/day', period=window)
        source['source'].update(title='Fictional '+ident+' daily resource estimate', locator='fixture:'+ident, tier=5)
        source['method'].update(name='Fictional constant daily planning estimate',source='fixture:'+ident)
        source['assumption']='Fictional constant daily proposal including weekends; no reservation, staffing acceptance or delivered work.'
        state['evidence'].append(source)
        metric = copy.deepcopy(template); metric.update(id=ident,value=value,unit='h/day',period=window,evidence_ids=[source['id']],method=source['method'],assumption=source['assumption'])
        metric['calculation']['inputs']=[source['id']]
        state['results'][0]['metrics'].append(metric); state['results'][0]['evidence_ids'].append(source['id'])
        for assumptions in (state['results'][0]['assumptions'],state['assumptions']):
            if source['assumption'] not in assumptions: assumptions.append(source['assumption'])
        return metric
    capacity=rate('engineer-capacity',8,{'start':'2027-02-01','end':'2027-03-01'})
    first=rate('scope-demand',5,{'start':'2027-02-01','end':'2027-02-03'})
    second=rate('service-demand',4,{'start':'2027-02-02','end':'2027-02-04'})
    last=rate('delivery-demand',3,{'start':'2029-11-20','end':'2029-12-01'})
    state=run_strategy(state,'build-transition-plan',transition)['proposal']['state']
    fit=copy.deepcopy(transition['transition_review']); fit.pop('planning_basis'); fit.pop('uncertainty_basis')
    fit.update(capacity_definition='constant_daily_capacity',calendar_basis='inclusive_calendar_days_constant_daily_rates',
        evidence_ids=capacity['evidence_ids'],rationale='Selected fictional resource estimate assessed as conditional constant daily capacity, not staffing reservation.',
        metric_contexts={capacity['id']:{'confirmed':True,'scope':fit['scope'],'evidence_ids':capacity['evidence_ids'],
        'rationale':'Fictional dedicated daily estimate inspected; no staffing reservation inferred.'}})
    resource={'id':'engineering','name':'Selected engineering planning capacity','unit':'h/day','capacity_metric_ids':[capacity['id']],'capacity_review':fit}
    task={'id':'scope-task','pathway_id':'energy-path','initiative_ids':['energy-investigation'],'milestone_ids':['engineering-decision'],
        'phase_id':'assessment','name':'Prepare source and engineering review','deliverable':'Unsent review package with documented open decisions.',
        'acceptance_criterion':'Qualified reviewers inspect source/method/service fitness and pending decision record.', 'owner':'Fictional engineering lead',
        'period':copy.deepcopy(first['period']),'depends_on':[],'resource_demands':[{'resource_id':'engineering','demand_metric_id':first['id'],
        'evidence_fit':'reviewed_supporting','rationale':'Fictional same-period daily demand estimate, not completed work.'}],
        'preconditions':None,'evidence_ids':first['evidence_ids'],'evidence_fit':'reviewed_supporting'}
    parallel=copy.deepcopy(task); parallel.update(id='service-task',name='Review accepted service comparability',period=copy.deepcopy(second['period']),evidence_ids=second['evidence_ids'])
    parallel['resource_demands'][0]['demand_metric_id']=second['id']
    delivery=copy.deepcopy(task); delivery.update(id='delivery-task',phase_id='delivery',milestone_ids=['proposed-commissioning'],
        name='Prepare gated delivery and verification work',period=copy.deepcopy(last['period']),depends_on=['scope-task','service-task'],evidence_ids=last['evidence_ids'])
    delivery['resource_demands'][0]['demand_metric_id']=last['id']
    review=copy.deepcopy(transition['transition_review']); review.pop('uncertainty_basis')
    review.update(calendar_basis='inclusive_calendar_days_constant_daily_rates',resource_basis='Sourced constant daily estimates; other commitments and later availability unknown.',
        evidence_ids=[capacity['evidence_ids'][0],first['evidence_ids'][0]],
        planning_basis='Proposed work and acceptance evidence only; no instruction to commence.')
    return state,{'transition_result_id':transition['result_id'],'roadmap':{'id':'selected-roadmap','name':'Fictional selected implementation roadmap',
        'owner':'Fictional proposed implementation owner','horizon':transition['plan']['horizon'],'review_date':'2027-03-01',
        'phases':[{'id':'assessment','name':'Review preparation','period':{'start':'2027-02-01','end':'2027-03-01'},'owner':'Fictional reviewer',
        'exit_criterion':'Documented technical, funding, service and staffing decisions; none recorded.'},
        {'id':'delivery','name':'Gated delivery preparation','period':{'start':'2029-11-01','end':'2029-12-01'},'owner':'Fictional operations reviewer',
        'exit_criterion':'Future accepted commissioning and service records reviewed; implementation authority pending.'}]},
        'work_packages':[task,parallel,delivery],'resources':[resource],'implementation_review':review,'result_id':'implementation-roadmap'}


class ImplementationTests(unittest.TestCase):
    def test_resource_overlap_known_answer_and_history(self):
        state,p=implementation_fixture(); before=copy.deepcopy(state); out=run_strategy(state,'build-implementation-roadmap',p)
        r=record(out,'IMPLEMENTATION_ROADMAP'); self.assertEqual(out['result']['status'],'partial'); self.assertEqual(out['result']['metrics'],[])
        conflict=next(s for s in r['resource_screens'] if s['status']=='overallocated')
        self.assertEqual(conflict['period'],{'start':'2027-02-02','end':'2027-02-03'})
        self.assertEqual(conflict['daily_demand'],9); self.assertEqual(conflict['daily_capacity'],8); self.assertEqual(conflict['daily_capacity_minus_demand'],-1)
        self.assertEqual(conflict['unit'],'h/day'); self.assertEqual(conflict['task_ids'],['scope-task','service-task'])
        unknown=next(s for s in r['resource_screens'] if s['status']=='unresolved_capacity'); self.assertIsNone(unknown['daily_capacity'])
        self.assertEqual(unknown['daily_demand'],3); self.assertEqual(r['delivery_screen'],'known_conditions_not_met')
        self.assertFalse(r['resource_optimized']); self.assertFalse(r['resources_reserved']); self.assertFalse(r['roadmap_adopted']); self.assertFalse(r['implementation_authorized'])
        self.assertEqual(r['proposed_sequence']['action_ids'],['scope-task','service-task','delivery-task'])
        self.assertEqual(state,before); after=out['proposal']['state']; validate_state(after)
        self.assertEqual(after['results'][:-1],before['results']); self.assertEqual(after['evidence'],before['evidence'])
        for key in ('review_requirements','data_gaps'):
            for item in before[key]: self.assertIn(item,after[key])

    def test_zero_capacity_is_unavailable_not_unknown(self):
        state,p=implementation_fixture(); metric=next(m for m in state['results'][0]['metrics'] if m['id']=='engineer-capacity'); metric['value']=0
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP')
        first=r['resource_screens'][0]; self.assertEqual(first['daily_capacity'],0); self.assertEqual(first['status'],'overallocated')
        p['resources'][0]['capacity_metric_ids']=[]; p['resources'][0]['capacity_review']['metric_contexts']={}
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP')
        self.assertTrue(all(s['daily_capacity'] is None for s in r['resource_screens']))

    def test_invalid_references_units_calendar_and_dependency_dates_block(self):
        state,original=implementation_fixture()
        mutations=[lambda p:p['work_packages'][0].update(depends_on=['delivery-task']),lambda p:p['work_packages'][1].update(depends_on=['scope-task']),
            lambda p:p['work_packages'][0].update(milestone_ids=['unknown']),lambda p:p['work_packages'][0].update(initiative_ids=[]),
            lambda p:p['work_packages'][0].update(phase_id='unknown'),lambda p:p['work_packages'][0].update(acceptance_criterion=''),
            lambda p:p['resources'][0].update(unit='h/week'),lambda p:p['resources'][0]['capacity_review'].update(calendar_basis='weekdays'),
            lambda p:p['implementation_review'].update(scope='Another plant'),lambda p:p['roadmap'].update(review_date='2026-10-01'),
            lambda p:p['resources'][0]['capacity_review']['metric_contexts']['engineer-capacity'].update(confirmed=False)]
        for mutation in mutations:
            p=copy.deepcopy(original); mutation(p); out=run_strategy(state,'build-implementation-roadmap',p)
            self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])
        state,p=implementation_fixture(); next(m for m in state['results'][0]['metrics'] if m['id']=='scope-demand')['period']['end']='2027-02-04'
        self.assertEqual(run_strategy(state,'build-implementation-roadmap',p)['result']['status'],'blocked')

    def test_source_milestone_prerequisites_and_finish_reconciliation(self):
        state,p=implementation_fixture(); p['work_packages'][2]['depends_on']=['scope-task']
        out=run_strategy(state,'build-implementation-roadmap',p)
        self.assertTrue(any('source prerequisite work is not retained' in s for s in record(out,'IMPLEMENTATION_ROADMAP')['known_unmet_conditions']))
        state,p=implementation_fixture(); p['work_packages']=p['work_packages'][2:]; p['work_packages'][0]['depends_on']=[]
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP')
        self.assertTrue(any('source prerequisite milestone' in s for s in r['unresolved_conditions']))
        state,p=implementation_fixture(); p['work_packages'][2]['resource_demands']=None; p['work_packages'][2]['period']['end']='2029-12-02'
        p['roadmap']['phases'][1]['period']['end']='2029-12-02'
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP')
        self.assertTrue(any('finish follows source milestone' in s for s in r['known_unmet_conditions']))

    def test_capacity_windows_do_not_double_count_availability(self):
        state,p=implementation_fixture(); existing=next(m for m in state['results'][0]['metrics'] if m['id']=='engineer-capacity')
        extra=copy.deepcopy(existing); extra['id']='second-capacity'; state['results'][0]['metrics'].append(extra)
        p['resources'][0]['capacity_metric_ids'].append(extra['id']); p['resources'][0]['capacity_review']['metric_contexts'][extra['id']]=copy.deepcopy(p['resources'][0]['capacity_review']['metric_contexts'][existing['id']])
        out=run_strategy(state,'build-implementation-roadmap',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any('overlapping capacity windows' in d['message'] for d in out['result']['diagnostics']))
        state,p=implementation_fixture(); other=copy.deepcopy(p['resources'][0]); other['id']='renamed-engineering'; p['resources'].append(other)
        out=run_strategy(state,'build-implementation-roadmap',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any('multiple renamed resource pools' in d['message'] for d in out['result']['diagnostics']))

    def test_preconditions_require_sources_and_remain_unfulfilled(self):
        state,p=implementation_fixture(); condition={'id':'staffing','domain':'organizational','description':'Staffing acceptance not recorded.',
            'owner':'Fictional staffing reviewer','status':'unresolved','evidence_ids':[],'evidence_fit':'unverified'}
        p['work_packages'][0]['preconditions']=[condition]
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP')
        self.assertFalse(r['work_packages'][0]['preconditions'][0]['fulfilled_verified'])
        condition['status']='sourced_assumption'
        self.assertEqual(run_strategy(state,'build-implementation-roadmap',p)['result']['status'],'blocked')

    def test_empty_and_overdue_plans_do_not_close_milestones(self):
        state,p=implementation_fixture(); p['work_packages']=[]
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP'); self.assertIsNone(r['proposed_sequence'])
        self.assertTrue(any('milestone omitted' in s for s in r['unresolved_conditions']))
        state,p=implementation_fixture(); p['implementation_review']['as_of_date']='2027-02-05'; p['roadmap']['review_date']='2027-04-01'
        r=record(run_strategy(state,'build-implementation-roadmap',p),'IMPLEMENTATION_ROADMAP')
        self.assertEqual(r['work_packages'][0]['status'],'overdue_unverified'); self.assertFalse(r['work_packages'][0]['completion_verified'])

    def test_changed_sources_and_blocked_factor_dependency(self):
        state,p=implementation_fixture(); state['evidence'][0]['source']['title']='Changed source'
        self.assertEqual(run_strategy(state,'build-implementation-roadmap',p)['result']['status'],'blocked')
        state,p=implementation_fixture(); owner=next(r for r in state['results'] if r['id']==p['transition_result_id'])
        owner['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Historical unresolved factor.'})
        owner['status']='partial'
        out=run_strategy(state,'build-implementation-roadmap',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_saved_capture_replays(self):
        saved=json.loads((ROOT/'evaluations/sus15-implementation-workflow.json').read_text(encoding='utf-8')); req=saved['request']
        self.assertEqual(run_strategy(req['state'],req['skill'],req['parameters']),saved['output'])
