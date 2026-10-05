import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import record
from tests.test_strategy_materiality import materiality_fixture


def register_fixture():
    state, material = materiality_fixture()
    state = run_strategy(state, 'identify-material-sustainability-issues', material)['proposal']['state']
    review = copy.deepcopy(material['materiality_review'])
    review.update(identification_method='Trace sourced scheduling harms and proposed prevention mechanisms.',context='Selected fictional plant risk/opportunity identification.')
    unknown = {'description':None,'evidence_ids':[],'evidence_fit':'unknown','rationale':'No defensible occurrence estimate supplied.'}
    magnitude = {'description':'Serious worker consequence, not monetary loss.','evidence_ids':['worker-note'],'evidence_fit':'reviewed_supporting',
        'rationale':'Fictional source describes a harmful prospective scheduling effect; no loss calculation.'}
    row = {'id':'schedule-risk','topic_id':'work-scheduling','category':'impact','description':'Prospective scheduling harm to selected workers.',
        'mechanism':'Abrupt restrictions could prevent rest; causal pathway needs rights/professional review.','affected_context':'Selected fictional plant workers.',
        'horizon':{'start':'2026-10-05','end':'2027-12-31'},'observed_date':'2025-09-01','evidence_ids':['worker-note'],'evidence_fit':'reviewed_supporting',
        'source_fragment':'Fictional risk record appendix','impact_ids':['schedule-harm'],'likelihood':unknown,'magnitude':magnitude,
        'dependencies':[{'id':'engagement','description':'Affected-worker engagement not yet completed.','status':'unresolved','evidence_ids':[],
            'evidence_fit':'unverified','owner':'Fictional engagement lead'}], 'trade_offs':None,'trade_off_review':'Adverse interactions have not been evaluated.',
        'follow_up':{'owner':'Fictional risk owner','target_date':'2026-12-01','purpose':'Review source fitness and worker context before action.'}}
    risks={'risks':[row],'materiality_result_id':material['result_id'],'identification_review':review,'result_id':'strategy-risks'}
    return state, risks


def opportunity_fixture():
    state, risks = register_fixture()
    state = run_strategy(state,'identify-sustainability-risks',risks)['proposal']['state']
    row=copy.deepcopy(risks['risks'][0]); row.update(id='notice-opportunity',category='impact_improvement',description='Investigate advance scheduling notice.',
        mechanism='Earlier notices could support rest planning; prevention is conditional on worker needs and implementation.',proposed_action='Develop an unsent consultation and notice trial proposal.',
        addresses_risk_ids=['schedule-risk'])
    return state, {'opportunities':[row],'materiality_result_id':risks['materiality_result_id'],'risk_result_id':risks['result_id'],
        'identification_review':copy.deepcopy(risks['identification_review']),'result_id':'strategy-opportunities'}


class StrategyRegisterTests(unittest.TestCase):
    def test_composed_risk_opportunity_preserve_history_and_unquantified_effects(self):
        state,p=opportunity_fixture(); before=copy.deepcopy(state); out=run_strategy(state,'identify-sustainability-opportunities',p)
        r=record(out,'SUSTAINABILITY_OPPORTUNITIES'); row=r['records'][0]
        self.assertTrue(row['mechanism_source_supported']); self.assertFalse(row['likelihood']['source_supported'])
        self.assertEqual(row['candidate_status'],'sourced_conditional_candidate'); self.assertEqual(len(row['addressed_risks']),1)
        for field in ('effect_realized','mitigation_verified','delivery_feasible','implementation_authorized'): self.assertFalse(row[field])
        for field in ('ranking','portfolio_benefit','selected_opportunity','financial_materiality','risk_acceptance'): self.assertIsNone(r[field])
        self.assertEqual(out['result']['metrics'],[]); self.assertEqual(state,before); validate_state(out['proposal']['state'])
        self.assertEqual(out['proposal']['state']['evidence'],before['evidence'])
        for review in before['review_requirements']: self.assertIn(review,out['result']['review_requirements'])
        for gap in before['data_gaps']: self.assertIn(gap,out['result']['data_gaps'])

    def test_source_fit_unknown_dates_and_elapsed_horizon(self):
        for key,value in [('evidence_fit','proxy'),('evidence_fit','irrelevant'),('evidence_ids',[]),('observed_date',None),
            ('observed_date','2024-09-01'),('horizon',None),('horizon',{'start':'2026-01-01','end':'2026-02-01'})]:
            state,p=register_fixture(); p['risks'][0][key]=value
            r=record(run_strategy(state,'identify-sustainability-risks',p),'SUSTAINABILITY_RISKS')
            self.assertFalse(r['records'][0]['mechanism_source_supported']); self.assertEqual(r['records'][0]['candidate_status'],'investigation_required')

    def test_organization_effect_is_separate_from_impact_significance(self):
        state,p=register_fixture(); row=p['risks'][0]; row.update(category='organization',impact_ids=[],mechanism='Service interruption may increase operating cost, no supplied valuation.')
        row['observed_date']='2026-02-01'
        r=record(run_strategy(state,'identify-sustainability-risks',p),'SUSTAINABILITY_RISKS')
        self.assertTrue(r['records'][0]['mechanism_source_supported']); self.assertIsNone(r['financial_materiality'])

    def test_unresolved_impacts_and_addressed_risks_cannot_be_upgraded(self):
        state,p=register_fixture(); material=next(x for x in state['results'] if x['skill']=='identify-material-sustainability-issues')
        params=json.loads(next(d['message'] for d in material['diagnostics'] if d['code']=='STRATEGY_INPUTS')); params['impacts'][0]['evidence_fit']='unverified'
        # Construct a fresh, valid unresolved dependency rather than mutate a saved accepted report.
        base,_=materiality_fixture(); replacement=run_strategy(base,'identify-material-sustainability-issues',params)
        out=run_strategy(replacement['proposal']['state'],'identify-sustainability-risks',p)
        self.assertFalse(record(out,'SUSTAINABILITY_RISKS')['records'][0]['mechanism_source_supported'])
        opp=copy.deepcopy(p['risks'][0]); opp.update(id='response',category='impact_improvement',proposed_action='Investigate worker context.',addresses_risk_ids=['schedule-risk'])
        q={'opportunities':[opp],'materiality_result_id':p['materiality_result_id'],'risk_result_id':p['result_id'],'identification_review':p['identification_review'],'result_id':'response-register'}
        self.assertFalse(record(run_strategy(out['proposal']['state'],'identify-sustainability-opportunities',q),'SUSTAINABILITY_OPPORTUNITIES')['records'][0]['mechanism_source_supported'])

    def test_dependencies_tradeoffs_and_followups_remain_conditional(self):
        state,p=opportunity_fixture(); row=p['opportunities'][0]
        row['dependencies'][0].update(status='known_unmet',evidence_fit='reviewed_supporting',evidence_ids=['manager-note'])
        row['trade_offs']=[{'description':'Advance notice may reduce staffing flexibility.','evidence_ids':[],'evidence_fit':'unverified','rationale':'Not assessed by affected workers.'}]
        row['follow_up']['target_date']='2026-02-01'
        r=record(run_strategy(state,'identify-sustainability-opportunities',p),'SUSTAINABILITY_OPPORTUNITIES'); item=r['records'][0]
        self.assertFalse(item['trade_offs'][0]['source_supported']); self.assertFalse(item['dependencies'][0]['completion_verified'])
        self.assertEqual(item['follow_up_status'],'overdue_unverified'); self.assertFalse(item['delivery_feasible'])

    def test_invalid_fields_source_dependencies_and_links_block(self):
        mutations=[lambda p:p['opportunities'][0].update(evidence_ids=['missing']),lambda p:p['opportunities'][0].update(observed_date='2027-01-01'),
            lambda p:p['opportunities'][0].update(addresses_risk_ids=['missing']),lambda p:p['opportunities'][0].update(topic_id='other-topic'),
            lambda p:p['opportunities'][0].update(impact_ids=['missing']),lambda p:p['opportunities'][0].update(proposed_action=''),
            lambda p:p['opportunities'][0]['dependencies'][0].update(status='known_supported'),lambda p:p['opportunities'][0]['follow_up'].update(owner=''),
            lambda p:p['opportunities'][0]['likelihood'].update(description=0.5),lambda p:p['identification_review'].update(scope='Other site')]
        for mutation in mutations:
            state,p=opportunity_fixture(); mutation(p)
            self.assertEqual(run_strategy(state,'identify-sustainability-opportunities',p)['result']['status'],'blocked')

    def test_changed_source_rejects_dependencies(self):
        state,p=opportunity_fixture(); state['evidence'][-1]['source']['title']='Changed title'
        self.assertEqual(run_strategy(state,'identify-sustainability-opportunities',p)['result']['status'],'blocked')

    def test_empty_register_does_not_establish_absence(self):
        state,p=register_fixture(); p.update(risks=[],materiality_result_id=None)
        out=run_strategy(state,'identify-sustainability-risks',p); r=record(out,'SUSTAINABILITY_RISKS')
        self.assertEqual(r['records'],[]); self.assertEqual(out['result']['status'],'partial'); self.assertIsNone(r['risk_acceptance'])

    def test_saved_composed_capture_replays(self):
        capture=json.loads((ROOT/'evaluations/sus15-risk-opportunity-workflow.json').read_text(encoding='utf-8'))
        for step in capture['steps']:
            req=step['request']; self.assertEqual(run_strategy(req['state'],req['skill'],req['parameters']),step['output'])
