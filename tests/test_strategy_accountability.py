import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record
from tests.test_strategy_implementation import implementation_fixture


def accountability_fixture():
    state,implementation=implementation_fixture()
    for ident,title in [('role-note','Fictional role and limited review mandate'),('acceptance-note','Fictional scoped engineering acceptance')]:
        source=copy.deepcopy(state['evidence'][0]); source.update(id=ident,unit='UNKNOWN_UNIT',period={'start':'2026-10-01','end':'2026-10-05'})
        source['source'].update(title=title,locator='fixture:'+ident); source['method'].update(name='Fictional role/acceptance record',source='fixture:'+ident)
        source['quality']['fitness_notes']='Fictional source; identity, authority and acceptance are not independently authenticated.'
        state['evidence'].append(source)
    state=run_strategy(state,'build-implementation-roadmap',implementation)['proposal']['state']
    actor={'id':'engineering-lead','name':'Fictional engineering lead','role':'Fictional engineering lead','role_scope':'Selected proposed engineering source review only.',
        'evidence_ids':['role-note'],'evidence_fit':'reviewed_supporting','mandate':{'description':'Prepare source review; no budget or work-start authority.',
        'limitations':'Technical qualifications, identity, funding, owner decisions and implementation remain unverified.','observed_date':'2026-10-02',
        'valid_until':'2027-03-01','evidence_ids':['role-note'],'evidence_fit':'reviewed_supporting'},
        'availability':{'description':'Selected engineering pool remains overallocated or unavailable; no reservation or workload acceptance.',
        'resource_ids':['engineering'],'evidence_ids':['engineer-capacity-source'],'evidence_fit':'unverified'}}
    sponsor=copy.deepcopy(actor); sponsor.update(id='sponsor',name='Fictional proposed implementation owner',role='Fictional proposed implementation owner',
        role_scope='Proposed governance owner, authority and assignment acceptance unknown.',mandate=None,availability=None)
    reviewer=copy.deepcopy(sponsor); reviewer.update(id='reviewer',name='Fictional reviewer',role='Fictional reviewer',role_scope='Proposed independent source and acceptance review, qualifications unknown.')
    acceptance={'actor_id':'engineering-lead','role':'responsible','item_type':'work_package','item_id':'scope-task',
        'statement':'Accept preparing the selected scope-task source review, conditional on staffing and future owner decision; no work start.',
        'observed_date':'2026-10-03','evidence_ids':['acceptance-note'],'evidence_fit':'reviewed_supporting'}
    assignment={'id':'scope-roles','item_type':'work_package','item_id':'scope-task','responsible':['engineering-lead'],'accountable':['sponsor'],
        'consulted':[],'informed':['reviewer'],'acceptance_records':[acceptance],'reviewer_actor_id':'reviewer','evidence_ids':['role-note'],'evidence_fit':'reviewed_supporting'}
    service=copy.deepcopy(assignment); service.update(id='service-roles',item_id='service-task',acceptance_records=[])
    delivery=copy.deepcopy(assignment); delivery.update(id='delivery-roles',item_id='delivery-task',acceptance_records=[])
    right={'id':'engineering-review-role','item_type':'work_package','item_id':'scope-task','decision':'technical_review','actor_id':'engineering-lead',
        'mandate_description':'Proposed review preparation only; no power to accept own output, fund delivery or start work.',
        'required_review_ids':[r['id'] for r in state['review_requirements'] if r['status']=='open'],'evidence_ids':['role-note'],'evidence_fit':'reviewed_supporting'}
    route={'id':'scope-escalation','item_type':'work_package','item_id':'scope-task','from_actor_id':'engineering-lead','to_actor_id':'sponsor',
        'trigger':'Unresolved acceptance, source mismatch, missed date or staffing/funding condition.','response_days':5,
        'evidence_ids':['role-note'],'evidence_fit':'unverified'}
    review=copy.deepcopy(implementation['implementation_review']); review.pop('planning_basis'); review.pop('calendar_basis'); review.pop('resource_basis')
    review.update(method='raci_proposal',responsibility_basis='Selected proposed task roles linked to current source owners.',
        authority_basis='Scoped sources do not grant budget, implementation or professional acceptance authority.',
        acceptance_basis='One sourced conditional responsibility candidate; no broader sponsor or workforce acceptance.',
        conflict_policy='Independent qualified review remains required; multiple accountable proposals and self-review stay unresolved.',evidence_ids=['role-note','acceptance-note'])
    return state,{'roadmap_result_id':implementation['result_id'],'actors':[actor,sponsor,reviewer],
        'assignments':[assignment,service,delivery],'decision_rights':[right],'escalation_routes':[route],'accountability_review':review,'result_id':'accountability-register'}


class AccountabilityTests(unittest.TestCase):
    def test_scoped_acceptance_candidate_preserves_history_and_gates(self):
        state,p=accountability_fixture(); before=copy.deepcopy(state); out=run_strategy(state,'assign-accountability',p); r=record(out,'ACCOUNTABILITY_REGISTER')
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(out['result']['metrics'],[])
        candidate=r['assignments'][0]['acceptance_records'][0]; self.assertEqual(candidate['status'],'sourced_acceptance_candidate'); self.assertFalse(candidate['acceptance_verified'])
        self.assertEqual(r['actors'][0]['mandate']['status'],'sourced_mandate_candidate'); self.assertFalse(r['actors'][0]['mandate']['authority_verified'])
        self.assertEqual(r['decision_rights'][0]['status'],'proposed_pending_authority_review'); self.assertIsNone(r['decision_rights'][0]['decision_record'])
        self.assertFalse(r['escalation_routes'][0]['contacted']); self.assertEqual(r['delivery_screen'],'known_conditions_not_met')
        for flag in ('assignments_adopted','authority_verified','funding_authorized','resources_reserved','implementation_authorized','public_claim_authorized','review_requirements_resolved'): self.assertFalse(r[flag])
        self.assertEqual(state,before); after=out['proposal']['state']; validate_state(after)
        self.assertEqual(after['evidence'],before['evidence']); self.assertEqual(after['results'][:-1],before['results'])
        for key in ('review_requirements','data_gaps'):
            for value in before[key]: self.assertIn(value,after[key])

    def test_missing_ambiguous_accountability_and_self_review(self):
        state,p=accountability_fixture(); p['assignments'][0]['accountable']=['sponsor','reviewer']; p['assignments'][0]['reviewer_actor_id']='engineering-lead'
        out=run_strategy(state,'assign-accountability',p); r=record(out,'ACCOUNTABILITY_REGISTER')
        self.assertEqual(r['assignments'][0]['status'],'ambiguous_accountability')
        self.assertTrue(any('independence needs review' in g['reason'] for g in out['result']['data_gaps']))
        p['assignments'][0]['accountable']=[]; p['assignments'][0]['responsible']=[]; p['assignments'][0]['acceptance_records']=[]
        r=record(run_strategy(state,'assign-accountability',p),'ACCOUNTABILITY_REGISTER')
        self.assertEqual(r['assignments'][0]['status'],'unassigned_accountability')

    def test_acceptance_date_source_period_and_expired_mandate(self):
        state,p=accountability_fixture(); p['assignments'][0]['acceptance_records'][0]['observed_date']=None
        p['actors'][0]['mandate']['valid_until']='2026-10-03'
        r=record(run_strategy(state,'assign-accountability',p),'ACCOUNTABILITY_REGISTER')
        self.assertEqual(r['assignments'][0]['acceptance_records'][0]['status'],'unverified'); self.assertEqual(r['actors'][0]['mandate']['status'],'expired_source')
        state,p=accountability_fixture(); p['assignments'][0]['acceptance_records'][0]['observed_date']='2025-09-01'
        out=run_strategy(state,'assign-accountability',p)
        self.assertTrue(any('observation/source-period fit' in g['reason'] for g in out['result']['data_gaps']))
        self.assertEqual(record(out,'ACCOUNTABILITY_REGISTER')['assignments'][0]['acceptance_records'][0]['status'],'unverified')
        p['accountability_review']['as_of_date']='2027-04-01'
        out=run_strategy(state,'assign-accountability',p)
        self.assertTrue(any('Source roadmap review/horizon has elapsed' in g['reason'] for g in out['result']['data_gaps']))

    def test_invalid_actors_items_acceptance_and_dates_block(self):
        state,original=accountability_fixture()
        changes=[lambda p:p['assignments'][0].update(responsible=['unknown']),lambda p:p['assignments'][0].update(item_id='unknown'),
            lambda p:p['assignments'][0]['acceptance_records'][0].update(item_id='service-task'),
            lambda p:p['assignments'][0]['acceptance_records'][0].update(role='accountable'),
            lambda p:p['assignments'][0]['acceptance_records'][0].update(observed_date='2026-10-06'),
            lambda p:p['actors'][0]['mandate'].update(valid_until='2026-01-01'),lambda p:p['assignments'][0].update(reviewer_actor_id='unknown'),
            lambda p:p['decision_rights'][0].update(required_review_ids=['unknown']),lambda p:p['escalation_routes'][0].update(response_days=True),
            lambda p:p['actors'][0]['availability'].update(resource_ids=['unknown']),lambda p:p['accountability_review'].update(scope='Other plant')]
        for change in changes:
            p=copy.deepcopy(original); change(p); out=run_strategy(state,'assign-accountability',p)
            self.assertEqual(out['result']['status'],'blocked'); self.assertEqual(out['result']['metrics'],[])

    def test_escalation_cycles_and_duplicate_item_records_block(self):
        state,p=accountability_fixture(); back=copy.deepcopy(p['escalation_routes'][0]); back.update(id='cycle-back',from_actor_id='sponsor',to_actor_id='engineering-lead'); p['escalation_routes'].append(back)
        out=run_strategy(state,'assign-accountability',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any('cycle' in d['message'] for d in out['result']['diagnostics']))
        state,p=accountability_fixture(); duplicate=copy.deepcopy(p['assignments'][0]); duplicate['id']='duplicate'; p['assignments'].append(duplicate)
        self.assertEqual(run_strategy(state,'assign-accountability',p)['result']['status'],'blocked')

    def test_missing_review_refs_shared_capacity_and_coverage_remain_open(self):
        state,p=accountability_fixture(); p['decision_rights'][0]['required_review_ids']=[]
        p['actors'][1]['availability']=copy.deepcopy(p['actors'][0]['availability'])
        out=run_strategy(state,'assign-accountability',p); r=record(out,'ACCOUNTABILITY_REGISTER')
        self.assertEqual(r['shared_resource_actor_ids']['engineering'],['engineering-lead','sponsor'])
        reasons=' '.join(g['reason'] for g in out['result']['data_gaps'])
        for text in ('omitted open review references','accountability item omitted','lacks a sourced scoped acceptance','multiple actors link the same resource pool'):
            self.assertIn(text,reasons)
        p['assignments']=[]; p['actors']=[]; p['decision_rights']=[]; p['escalation_routes']=[]
        out=run_strategy(state,'assign-accountability',p); self.assertEqual(out['result']['status'],'partial')
        self.assertFalse(record(out,'ACCOUNTABILITY_REGISTER')['assignments_adopted'])

    def test_changed_roadmap_and_factor_dependency_block(self):
        state,p=accountability_fixture(); next(m for m in state['results'][0]['metrics'] if m['id']=='engineer-capacity')['value']=99
        self.assertEqual(run_strategy(state,'assign-accountability',p)['result']['status'],'blocked')
        state,p=accountability_fixture(); owner=next(r for r in state['results'] if r['id']==p['roadmap_result_id'])
        owner['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Upstream unresolved factor.'})
        out=run_strategy(state,'assign-accountability',p); self.assertEqual(out['result']['status'],'blocked')
        self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_saved_capture_replays(self):
        saved=json.loads((ROOT/'evaluations/sus15-accountability-workflow.json').read_text(encoding='utf-8')); req=saved['request']
        self.assertEqual(run_strategy(req['state'],req['skill'],req['parameters']),saved['output'])
