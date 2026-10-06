"""Compose sourced project economics and conditional business cases."""
import copy
import hashlib
import json

from .finance_tools import OPERATIONS, run_finance
from .finance_business_case import PARAMETERS as CASE_PARAMETERS
from .contract_validation import validate_state
from .manager_workflow import _empty
from .state_proposal import propose


def _ids(values):
    return isinstance(values, list) and all(isinstance(i, str) and i.strip() for i in values) and len(values) == len(set(values))


METRIC_SELECTORS = {'metric_id', 'investment_id', 'annual_savings_id', 'net_benefit_id',
    'discount_rate_id', 'incremental_cost_id', 'baseline_emissions_id', 'scenario_emissions_id',
    'quantity_id', 'price_id', 'baseline_metric_id', 'scenario_metric_id', 'reduction_metric_id'}


def _references(value):
    """Only finance selectors, never evidence IDs, project IDs or source prose."""
    refs = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {'source_contexts', 'evidence_ids', 'model_evidence_ids'}: continue
            if key == 'sensitivity_results':
                refs += [('result', row['result_id']) for row in item]
            elif key.endswith('_result_id') and item is not None: refs.append(('result', item))
            elif key in METRIC_SELECTORS and item is not None: refs.append(('metric', item))
            elif key != 'result_id': refs += _references(item)
    elif isinstance(value, list):
        for item in value: refs += _references(item)
    return refs


def _plan(state, p):
    if not isinstance(p, dict) or set(p) != {'steps', 'outputs', 'workflow_review', 'result_id'} or not isinstance(p['steps'], list) or not p['steps']:
        raise ValueError('Exact nonempty investment recipe required.')
    records = {}; known = {r['id'] for r in state['results']}
    for step in p['steps']:
        if not isinstance(step, dict) or set(step) != {'skill', 'parameters', 'depends_on'} or step['skill'] not in OPERATIONS:
            raise ValueError('Existing investment operations and explicit prerequisites required.')
        params = step['parameters']
        if not isinstance(params, dict) or (set(params) != OPERATIONS[step['skill']] and not (step['skill'] == 'build-sustainability-business-case' and set(params) == CASE_PARAMETERS)) or not _ids(step['depends_on']):
            raise ValueError('Exact existing investment fields and distinct dependency IDs required.')
        ident = params['result_id']
        if not isinstance(ident, str) or not ident.strip() or ident in known or ident in records:
            raise ValueError('Fresh distinct investment result IDs required.')
        records[ident] = step
    if not isinstance(p['result_id'], str) or not p['result_id'].strip() or p['result_id'] in known | set(records):
        raise ValueError('Fresh aggregate ID required.')
    pending = list(records); order = []; ancestors = {}
    while pending:
        ready = [i for i in pending if set(records[i]['depends_on']) <= set(order)]
        if not ready: raise ValueError('Unresolved or cyclic investment dependencies.')
        for ident in ready:
            ancestors[ident] = set(records[ident]['depends_on']) | {a for d in records[ident]['depends_on'] for a in ancestors[d]}
            order.append(ident); pending.remove(ident)
    for ident in order:
        if any(kind == 'result' and ref in records and ref not in ancestors[ident] for kind, ref in _references(records[ident]['parameters'])):
            raise ValueError('Produced investment result sources require declared ancestor dependencies.')
    if not _ids(p['outputs']) or not p['outputs'] or not set(p['outputs']) <= set(records): raise ValueError('Fresh selected investment outputs required.')
    review = p['workflow_review']; fields = {'boundary_id', 'period', 'evidence_ids', 'scope', 'reviewer_role', 'rationale', 'coverage_complete'}
    if (not isinstance(review, dict) or set(review) != fields or review['boundary_id'] != state['organizational_boundary']['id']
        or review['period'] != state['reporting_period'] or type(review['coverage_complete']) is not bool
        or not _ids(review['evidence_ids']) or not review['evidence_ids'] or not set(review['evidence_ids']) <= {e['id'] for e in state['evidence']}
        or not all(isinstance(review[k], str) and review[k].strip() for k in ('scope', 'reviewer_role', 'rationale'))):
        raise ValueError('Current reporting context and attributed workflow review required.')
    return records, order, ancestors


def _blocked(state, step, sources, reason):
    result = _empty(state, step['skill'], step['parameters']['result_id']); result['status'] = 'blocked'
    result['review_states'] = list(dict.fromkeys(result['review_states'] + ['EVIDENCE_INCOMPLETE']))
    result['evidence_ids'] = sorted({e for r in sources for e in r['evidence_ids']})
    result['data_gaps'].append({'id': result['id'] + '-investment-workflow-gap', 'field': 'investment_recipe', 'reason': reason,
        'impact': 'No dependent financial or physical decision support follows.', 'remedy': 'Reconcile selected source/context inputs and blocked prerequisites.'})
    result['diagnostics'] = [{'code': 'INVESTMENT_WORKFLOW_STEP_BLOCKED', 'message': reason},
        {'code': 'INVESTMENT_WORKFLOW_STEP_INPUTS', 'message': json.dumps(step['parameters'], sort_keys=True)}]
    if any(d['code'] == 'EMISSION_FACTOR_REQUIRED' for r in sources for d in r['diagnostics']):
        result['diagnostics'].append({'code': 'EMISSION_FACTOR_REQUIRED', 'message': 'Selected prerequisite retains missing defensible factors.'})
    result['next_actions'] = [result['data_gaps'][-1]['remedy']]
    return {'result': result, 'proposal': propose(state, result, 'Retain blocked investment prerequisite without fabricated returns')}


def run_investment_workflow(state, p):
    validate_state(state); records, order, ancestors = _plan(state, p)
    working = copy.deepcopy(state); executed = {}; trace = []
    for ident in order:
        step = records[ident]; sources = [executed[d] for d in step['depends_on']]
        skipped = any(r['status'] in {'blocked', 'invalid_input'} for r in sources)
        if skipped: out = _blocked(working, step, sources, 'Explicit prerequisite blocked; helper not invoked.')
        else:
            owners = {m['id']: r['id'] for r in working['results'] for m in r['metrics']}
            actual = [owners.get(ref) if kind == 'metric' else ref for kind, ref in _references(step['parameters'])]
            if any(owner in records and owner not in ancestors[ident] for owner in actual): raise ValueError('Produced source lacks its declared ancestor.')
            try: out = run_finance(working, step['skill'], copy.deepcopy(step['parameters']))
            except (ValueError, KeyError, TypeError) as error: out = _blocked(working, step, sources, str(error))
        working = out['proposal']['state']; executed[ident] = out['result']
        trace.append({'skill': step['skill'], 'result_id': ident, 'depends_on': step['depends_on'], 'helper_invoked': not skipped, 'status': out['result']['status']})
    result = _empty(working, 'sustainability-business-case', p['result_id']); review = p['workflow_review']
    result['evidence_ids'] = sorted(set(review['evidence_ids']) | {e for r in executed.values() for e in r['evidence_ids']})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + ['PROFESSIONAL_REVIEW_REQUIRED']))
    result['review_requirements'].append({'id': result['id'] + '-specialist-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
        'reason': 'Review monetary/physical definitions, source fitness, tax/currency/timing, sensitivity, interactions, feasibility and actual budget decisions.',
        'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
    views = {i: {'result_id': i, 'skill': r['skill'], 'status': r['status'], 'metric_ids': [m['id'] for m in r['metrics']],
        'sha256_result_utf8_json_sorted_keys': hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()} for i, r in executed.items()}
    report = {'execution_contract': 'investment-workflow-0.1.0', 'workflow_review': copy.deepcopy(review), 'trace': trace,
        'source_result_views': views, 'selected_output_ids': list(p['outputs']), 'portfolio_total': None,
        'selected_investment_id': None, 'source_authenticity_verified': False,
        'realized_savings_verified': False, 'physical_reduction_verified': False,
        'funding_authorized': False, 'implementation_authorized': False, 'publication_authorized': False}
    if not review['coverage_complete']:
        result['data_gaps'].append({'id': result['id'] + '-coverage-gap', 'field': 'investment_workflow_coverage',
            'reason': 'Selected investment/organization coverage is declared incomplete.', 'impact': 'No full investment or portfolio assessment follows.',
            'remedy': 'Reconcile missing costs, physical scopes, sources, sensitivity, engineering and finance review.'})
    if result['data_gaps'] or any(r['status'] != 'completed' for r in executed.values()):
        result['status'] = 'partial'; result['review_states'].append('EVIDENCE_INCOMPLETE')
    if all(r['status'] in {'blocked', 'invalid_input'} for r in executed.values()): result['status'] = 'blocked'
    for source in executed.values():
        result['diagnostics'].extend(copy.deepcopy(d) for d in source['diagnostics'] if d['code'] == 'EMISSION_FACTOR_REQUIRED' and d not in result['diagnostics'])
    result['diagnostics'].extend([{'code': 'INVESTMENT_WORKFLOW', 'message': json.dumps(report, sort_keys=True)},
                                 {'code': 'INVESTMENT_WORKFLOW_INPUTS', 'message': json.dumps(p, sort_keys=True)}])
    result['next_actions'] = ['Review retained conditional financial/physical outputs and obtain engineering, finance and budget-owner decisions.']
    final = propose(working, result, 'Compose separate investment views without funding or realized benefit claims')['state']
    final['revision'] = state['revision'] + 1; validate_state(final)
    return {'result': result, 'proposal': {'base_revision': state['revision'], 'reason': 'Atomic investment candidate; no external action or source/state write', 'state': final}}
