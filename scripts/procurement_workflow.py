"""Compose supplier decision support and sourced purchase mapping; no buying."""
import copy
import hashlib
import json

from .contract_validation import validate_state
from .supplier_tools import OPERATIONS, run_suppliers
from .operations_tools import CARBON_PARAMETERS, _run_carbon
from .carbon_workflow import _references as carbon_references
from .manager_workflow import _empty
from .state_proposal import propose


CARBON = {'calculate-co2e', 'classify-scope-3-emissions', 'calculate-scope-3-category'}


def _ids(value):
    return isinstance(value, list) and all(isinstance(i, str) and i.strip() for i in value) and len(value) == len(set(value))


def _references(skill, p):
    if skill in CARBON: return carbon_references(skill, p)
    refs = []
    for field in ('assessment_result_ids', 'mapping_result_ids'):
        refs += [('result', i) for i in p.get(field, [])]
    if 'assessment_result_id' in p: refs.append(('result', p['assessment_result_id']))
    if skill == 'map-supply-chain-emissions':
        for row in p['links']: refs += [('result', row['category_result_id']), ('metric', row['purchase_metric_id'])]
    if skill == 'evaluate-low-carbon-procurement-option':
        for key in ('baseline', 'alternative'):
            option = p[key]; refs += [('result', option['mapping_result_id']), ('metric', option['functional_metric_id'])]
            if option['cost_metric_id'] is not None: refs.append(('metric', option['cost_metric_id']))
    return refs


def _plan(state, p):
    if not isinstance(p, dict) or set(p) != {'steps', 'outputs', 'procurement_review', 'result_id'}:
        raise ValueError('Exact procurement recipe fields required.')
    if not isinstance(p['steps'], list) or not p['steps']: raise ValueError('Nonempty procurement steps required.')
    records = {}; known = {r['id'] for r in state['results']}
    for step in p['steps']:
        if not isinstance(step, dict) or set(step) != {'skill', 'parameters', 'depends_on'} or step['skill'] not in set(OPERATIONS) | CARBON:
            raise ValueError('Allowlisted supplier/carbon steps and explicit dependencies required.')
        skill = step['skill']; params = step['parameters']; required = CARBON_PARAMETERS[skill] if skill in CARBON else OPERATIONS[skill]
        optional = {'fixture_mode'} if skill in CARBON | {'map-supply-chain-emissions', 'identify-scope-3-hotspots', 'evaluate-low-carbon-procurement-option'} else set()
        if not isinstance(params, dict) or not required <= set(params) or set(params) - required - optional:
            raise ValueError('Exact existing helper fields required.')
        if 'fixture_mode' in params and type(params['fixture_mode']) is not bool: raise ValueError('Per-step fixture mode must be boolean.')
        ident = params['result_id']
        if not isinstance(ident, str) or not ident.strip() or ident in known or ident in records or not _ids(step['depends_on']):
            raise ValueError('Fresh step IDs and distinct prerequisite IDs required.')
        records[ident] = step
    if not isinstance(p['result_id'], str) or not p['result_id'].strip() or p['result_id'] in known | set(records):
        raise ValueError('Fresh aggregate ID required.')
    pending = list(records); order = []; ancestors = {}
    while pending:
        ready = [i for i in pending if set(records[i]['depends_on']) <= set(order)]
        if not ready: raise ValueError('Unresolved or cyclic procurement prerequisites.')
        for i in ready:
            ancestors[i] = set(records[i]['depends_on']) | {a for d in records[i]['depends_on'] for a in ancestors[d]}
            order.append(i); pending.remove(i)
    metric_producers = {i + '-metric': i for i in records if records[i]['skill'] in {'calculate-co2e', 'calculate-scope-3-category'}}
    existing_metrics = {m['id'] for r in state['results'] for m in r['metrics']}
    if set(metric_producers) & (existing_metrics | set(records) | {p['result_id']}): raise ValueError('Planned subtotal metric identities collide.')
    producers = {'result': {i: i for i in records}, 'metric': metric_producers}
    for i in order:
        if any(ref in producers[kind] and producers[kind][ref] not in ancestors[i] for kind, ref in _references(records[i]['skill'], records[i]['parameters'])):
            raise ValueError('Selected produced sources need explicit ancestor dependencies.')
    if not _ids(p['outputs']) or not p['outputs'] or any(i not in records or records[i]['skill'] not in OPERATIONS for i in p['outputs']):
        raise ValueError('Select distinct freshly requested supplier/procurement outputs.')
    review = p['procurement_review']; fields = {'boundary_id', 'period', 'evidence_ids', 'scope', 'reviewer_role', 'rationale', 'coverage_complete'}
    if (not isinstance(review, dict) or set(review) != fields or review['boundary_id'] != state['organizational_boundary']['id']
        or review['period'] != state['reporting_period'] or type(review['coverage_complete']) is not bool
        or not _ids(review['evidence_ids']) or not review['evidence_ids'] or not set(review['evidence_ids']) <= {e['id'] for e in state['evidence']}
        or not all(isinstance(review[k], str) and review[k].strip() for k in ('scope', 'reviewer_role', 'rationale'))):
        raise ValueError('Current buyer boundary/period and attributed source review required.')
    return records, order, ancestors


def _blocked(state, step, reason, sources):
    p = step['parameters']; result = _empty(state, step['skill'], p['result_id']); result['status'] = 'blocked'
    result['review_states'] = list(dict.fromkeys(result['review_states'] + ['EVIDENCE_INCOMPLETE']))
    result['evidence_ids'] = sorted({e for r in sources for e in r['evidence_ids']})
    result['data_gaps'].append({'id': result['id'] + '-procurement-gap', 'field': 'procurement_recipe', 'reason': reason,
        'impact': 'No supported dependent outcome or purchase authority follows.', 'remedy': 'Reconcile blocked sources and domain inputs.'})
    result['diagnostics'] = [{'code': 'PROCUREMENT_STEP_BLOCKED', 'message': reason}, {'code': 'PROCUREMENT_STEP_INPUTS', 'message': json.dumps(p, sort_keys=True)}]
    if any(d['code'] == 'EMISSION_FACTOR_REQUIRED' for r in sources for d in r['diagnostics']):
        result['diagnostics'].append({'code': 'EMISSION_FACTOR_REQUIRED', 'message': 'A selected prerequisite retains missing defensible factors.'})
    result['next_actions'] = [result['data_gaps'][-1]['remedy']]
    return {'result': result, 'proposal': propose(state, result, 'Retain blocked procurement dependency without buying or a fabricated quantity')}


def run_procurement(state, p):
    validate_state(state); records, order, ancestors = _plan(state, p)
    working = copy.deepcopy(state); executed = {}; trace = []
    for ident in order:
        step = records[ident]; sources = [executed[d] for d in step['depends_on']]
        skipped = any(r['status'] in {'blocked', 'invalid_input'} for r in sources)
        if skipped: out = _blocked(working, step, 'Explicit prerequisite blocked; helper not invoked.', sources)
        else:
            owners = {m['id']: r['id'] for r in working['results'] for m in r['metrics']}
            actual = [owners.get(ref) if kind == 'metric' else ref for kind, ref in _references(step['skill'], step['parameters'])]
            if any(owner in records and owner not in ancestors[ident] for owner in actual): raise ValueError('Produced source lacks its declared ancestor.')
            try:
                function = _run_carbon if step['skill'] in CARBON else run_suppliers
                out = function(working, step['skill'], copy.deepcopy(step['parameters']))
            except (ValueError, TypeError, KeyError) as error: out = _blocked(working, step, str(error), sources)
        working = out['proposal']['state']; executed[ident] = out['result']
        trace.append({'skill': step['skill'], 'result_id': ident, 'depends_on': step['depends_on'], 'helper_invoked': not skipped, 'status': out['result']['status']})
    result = _empty(working, 'sustainable-procurement', p['result_id']); review = p['procurement_review']
    result['evidence_ids'] = sorted(set(review['evidence_ids']) | {e for r in executed.values() for e in r['evidence_ids']})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + ['PROFESSIONAL_REVIEW_REQUIRED']))
    result['review_requirements'].append({'id': result['id'] + '-buyer-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
        'reason': 'Review buyer criteria, source fitness, mapped lifecycle/service scope, unknowns, risk tradeoffs and actual procurement decisions.',
        'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
    views = {i: {'result_id': i, 'skill': r['skill'], 'status': r['status'], 'metric_ids': [m['id'] for m in r['metrics']],
                 'sha256_result_utf8_json_sorted_keys': hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()} for i, r in executed.items()}
    report = {'execution_contract': 'procurement-workflow-0.1.0', 'procurement_review': copy.deepcopy(review), 'trace': trace,
        'source_result_views': views, 'selected_output_ids': list(p['outputs']), 'selected_supplier_id': None, 'portfolio_total': None,
        'buyer_ratings_are_environmental_quantities': False, 'risk_allegations_verified': False, 'supplier_coverage_authenticated': False,
        'implemented_reduction_verified': False, 'procurement_authorized': False, 'external_communication_authorized': False, 'publication_authorized': False}
    if not review['coverage_complete']:
        result['data_gaps'].append({'id': result['id'] + '-coverage-gap', 'field': 'supplier_coverage', 'reason': 'Selected supplier/purchase coverage is declared incomplete.',
            'impact': 'No full value-chain account or procurement readiness is established.', 'remedy': 'Reconcile missing suppliers/purchases, source fitness and independent buyer review.'})
    if result['data_gaps'] or any(r['status'] != 'completed' for r in executed.values()):
        result['status'] = 'partial'; result['review_states'].append('EVIDENCE_INCOMPLETE')
    if all(r['status'] in {'blocked', 'invalid_input'} for r in executed.values()): result['status'] = 'blocked'
    for source in executed.values():
        result['diagnostics'].extend(copy.deepcopy(d) for d in source['diagnostics'] if d['code'] == 'EMISSION_FACTOR_REQUIRED' and d not in result['diagnostics'])
    result['diagnostics'].extend([{'code': 'PROCUREMENT_WORKFLOW', 'message': json.dumps(report, sort_keys=True)},
                                 {'code': 'PROCUREMENT_WORKFLOW_INPUTS', 'message': json.dumps(p, sort_keys=True)}])
    result['next_actions'] = ['Review qualified source outputs and obtain actual buyer/source decisions before engagement, selection, implementation or disclosure.']
    final = propose(working, result, 'Compose procurement analysis without supplier selection or external action')['state']
    final['revision'] = state['revision'] + 1; validate_state(final)
    return {'result': result, 'proposal': {'base_revision': state['revision'], 'reason': 'Atomic procurement candidate; no source/state writes or buying', 'state': final}}
