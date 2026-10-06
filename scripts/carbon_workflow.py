"""Compose existing carbon helpers; retain separate accounts and open review."""
import copy
import json

from .contract_validation import validate_state
from .operations_tools import CARBON_PARAMETERS, _run_carbon
from .state_proposal import propose


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value) and len(value) == len(set(value))


def _references(skill, parameters):
    """Selected current-state sources only; prior comparison snapshots stay separate."""
    if skill == 'calculate-co2e': return [('metric', parameters['activity_id'])]
    if skill == 'build-ghg-inventory':
        return [('result', r) for r in [parameters['scope1_result_id'], parameters['scope2_result_id'], *parameters['scope3_result_ids']] if r is not None]
    if skill == 'compare-ghg-inventories': return [('result', parameters['current_inventory_id'])]
    if skill == 'identify-emission-hotspots': return [('result', parameters['inventory_id'])]
    refs = [('metric', s['activity_id']) for s in parameters['sources'] if s.get('activity_id') is not None]
    refs += [('result', s['scope12_result_id']) for s in parameters['sources'] if s.get('scope12_result_id') is not None]
    refs += [('metric', c['metric_id']) for c in parameters.get('components', [])]
    return refs


def _graph(state, parameters):
    if not isinstance(parameters, dict) or set(parameters) != {'steps', 'outputs', 'accounting_review', 'result_id'}:
        raise ValueError('Exact carbon workflow parameters required.')
    steps = parameters['steps']
    if not isinstance(steps, list) or not steps: raise ValueError('Nonempty carbon steps required.')
    known = {r['id'] for r in state['results']}; records = {}
    for step in steps:
        if not isinstance(step, dict) or set(step) != {'skill', 'parameters', 'depends_on'} or step['skill'] not in CARBON_PARAMETERS:
            raise ValueError('Allowlisted carbon steps with explicit prerequisites required.')
        p = step['parameters']; required = CARBON_PARAMETERS[step['skill']]
        if not isinstance(p, dict) or not required <= set(p) or set(p) - required - {'fixture_mode'}:
            raise ValueError('Exact existing carbon helper parameters required.')
        ident = p['result_id']
        if not isinstance(ident, str) or not ident.strip() or ident in known or ident in records:
            raise ValueError('Fresh distinct carbon result IDs required.')
        if 'fixture_mode' in p and type(p['fixture_mode']) is not bool:
            raise ValueError('Fixture mode must be an explicit boolean per step.')
        if not _strings(step['depends_on']): raise ValueError('Distinct prerequisite IDs required.')
        records[ident] = step
    ident = parameters['result_id']
    if not isinstance(ident, str) or not ident.strip() or ident in known or ident in records:
        raise ValueError('Fresh distinct workflow result ID required.')
    pending = list(records); order = []; ancestors = {}
    while pending:
        ready = [i for i in pending if set(records[i]['depends_on']) <= set(order)]
        if not ready: raise ValueError('Unresolved or cyclic carbon prerequisites.')
        for i in ready:
            ancestors[i] = set(records[i]['depends_on']) | {a for d in records[i]['depends_on'] for a in ancestors[d]}
            order.append(i); pending.remove(i)
    # Known single-subtotal helper metric IDs and explicit result selectors must
    # declare their producing step as an ancestor before any helper runs.
    metrics = {i + '-metric': i for i, s in records.items() if s['skill'] in
                    {'calculate-co2e', 'calculate-scope-1', 'calculate-location-based-scope-2',
                     'calculate-market-based-scope-2', 'calculate-scope-3-category', 'build-ghg-inventory'}}
    known_metrics = {m['id'] for r in state['results'] for m in r['metrics']}
    if set(metrics) & (known_metrics | set(records) | {parameters['result_id']}):
        raise ValueError('Planned subtotal metric IDs must not collide with existing metrics or batch result IDs.')
    planned = {'result': {i: i for i in records}, 'metric': metrics}
    for i in order:
        refs = _references(records[i]['skill'], records[i]['parameters'])
        if any(r in planned[kind] and planned[kind][r] not in ancestors[i] for kind, r in refs):
            raise ValueError('Selected produced sources require explicit ancestor dependencies.')
    outputs = parameters['outputs']
    if not isinstance(outputs, dict) or set(outputs) != {'inventories', 'hotspots', 'comparisons'}:
        raise ValueError('Explicit separate output selections required.')
    kinds = {'inventories': 'build-ghg-inventory', 'hotspots': 'identify-emission-hotspots', 'comparisons': 'compare-ghg-inventories'}
    for kind, ids in outputs.items():
        if not _strings(ids) or any(i not in records or records[i]['skill'] != kinds[kind] for i in ids):
            raise ValueError('Select freshly requested outputs of the corresponding carbon method.')
    return records, order, ancestors


def _blocked(state, skill, ident, reason, code, parameters, dependency_results):
    result = {'id': ident, 'skill': skill, 'contract_version': '0.1.0', 'status': 'blocked',
              'review_states': list(dict.fromkeys(['ANALYTICAL', 'EVIDENCE_INCOMPLETE'] + [r['state'] for r in state['review_requirements'] if r['status'] == 'open'])),
              'review_requirements': copy.deepcopy(state['review_requirements']), 'metrics': [],
              'evidence_ids': sorted({e for r in dependency_results for e in r['evidence_ids']}),
              'assumptions': list(state['assumptions']), 'data_gaps': copy.deepcopy(state['data_gaps']),
              'diagnostics': [{'code': code, 'message': reason}, {'code': 'CARBON_STEP_INPUTS', 'message': json.dumps(parameters, sort_keys=True)}],
              'next_actions': ['Reconcile selected source inputs and blocked prerequisites before dependent calculation.']}
    result['data_gaps'].append({'id': ident + '-workflow-gap', 'field': 'carbon_workflow', 'reason': reason,
                               'impact': 'This step supplies no metric.', 'remedy': result['next_actions'][0]})
    if any(d['code'] == 'EMISSION_FACTOR_REQUIRED' for r in dependency_results for d in r['diagnostics']):
        result['diagnostics'].append({'code': 'EMISSION_FACTOR_REQUIRED', 'message': 'A selected prerequisite retains missing defensible factors.'})
    return {'result': result, 'proposal': propose(state, result, 'Retain blocked carbon dependency without a fabricated metric')}


def run_carbon_workflow(state, parameters):
    validate_state(state)
    records, order, ancestors = _graph(state, parameters)
    review = parameters['accounting_review']; required = {'boundary_id', 'period', 'evidence_ids', 'scope', 'rationale', 'reviewer_role', 'coverage_complete'}
    if (not isinstance(review, dict) or set(review) != required or review['boundary_id'] != state['organizational_boundary']['id']
        or review['period'] != state['reporting_period'] or type(review['coverage_complete']) is not bool
        or not _strings(review['evidence_ids']) or not review['evidence_ids'] or not set(review['evidence_ids']) <= {e['id'] for e in state['evidence']}
        or not all(isinstance(review[k], str) and review[k].strip() for k in ('scope', 'rationale', 'reviewer_role'))):
        raise ValueError('Explicit current boundary/period, evidence and attributed accounting review required.')
    working = copy.deepcopy(state); trace = []; executed = {}
    for ident in order:
        step = records[ident]; dependencies = [executed[d] for d in step['depends_on']]
        skipped = any(r['status'] in {'blocked', 'invalid_input'} for r in dependencies)
        if skipped:
            output = _blocked(working, step['skill'], ident, 'An explicit prerequisite is blocked; the helper was not invoked.',
                              'CARBON_DEPENDENCY_BLOCKED', step['parameters'], dependencies)
        else:
            owners = {m['id']: r['id'] for r in working['results'] for m in r['metrics']}
            refs = _references(step['skill'], step['parameters'])
            producers = [owners.get(r) if kind == 'metric' else r for kind, r in refs]
            if any(owner in records and owner not in ancestors[ident] for owner in producers):
                raise ValueError('Produced metric source is missing its declared ancestor dependency.')
            try:
                output = _run_carbon(working, step['skill'], copy.deepcopy(step['parameters']))
            except (ValueError, KeyError, TypeError) as error:
                output = _blocked(working, step['skill'], ident, str(error), 'CARBON_STEP_INPUT_REQUIRED', step['parameters'], dependencies)
        working = output['proposal']['state']; executed[ident] = output['result']
        trace.append({'result_id': ident, 'skill': step['skill'], 'depends_on': list(step['depends_on']),
                      'helper_invoked': not skipped, 'status': output['result']['status'],
                      'metric_ids': [m['id'] for m in output['result']['metrics']],
                      'diagnostics': copy.deepcopy(output['result']['diagnostics'])})
    ident = parameters['result_id']
    result = {'id': ident, 'skill': 'carbon-accounting', 'contract_version': '0.1.0', 'status': 'completed',
              'review_states': list(dict.fromkeys(['ANALYTICAL', 'PROFESSIONAL_REVIEW_REQUIRED', 'ASSURANCE_REQUIRED'] +
                  [r['state'] for r in working['review_requirements'] if r['status'] == 'open'])),
              'review_requirements': copy.deepcopy(working['review_requirements']), 'metrics': [],
              'evidence_ids': sorted(set(review['evidence_ids']) | {e for r in executed.values() for e in r['evidence_ids']}),
              'assumptions': list(working['assumptions']), 'data_gaps': copy.deepcopy(working['data_gaps']), 'diagnostics': [], 'next_actions': []}
    for review_state, role in [('PROFESSIONAL_REVIEW_REQUIRED', review['reviewer_role']), ('ASSURANCE_REQUIRED', 'Qualified assurance practitioner')]:
        result['review_requirements'].append({'id': ident + '-' + review_state.lower(), 'state': review_state,
            'reason': 'Review actual source fitness, boundaries, exclusions, method selection, coverage and assurance needs; execution is not authentication.',
            'scope': review['scope'], 'reviewer_role': role, 'status': 'open', 'resolution': None})
    snapshots = {kind: [copy.deepcopy(executed[i]) for i in ids] for kind, ids in parameters['outputs'].items()}
    report = {'execution_contract': 'carbon-accounting-workflow-0.1.0', 'accounting_review': copy.deepcopy(review),
              'ordered_step_ids': order, 'trace': trace, 'selected_outputs': snapshots, 'combined_inventory_total': None,
              'coverage_complete_authenticated': False, 'source_authenticity_verified': False, 'assurance_performed': False,
              'statutory_total_verified': False, 'project_reduction_verified': False, 'publication_authorized': False}
    if not review['coverage_complete']:
        result['data_gaps'].append({'id': ident + '-coverage-gap', 'field': 'carbon_workflow_coverage',
            'reason': 'Selected accounting workflow coverage is declared incomplete.', 'impact': 'No full organization or statutory account is established.',
            'remedy': 'Reconcile missing scopes, sources, categories and independent coverage review.'})
    if result['data_gaps'] or any(r['status'] != 'completed' for r in executed.values()):
        result['status'] = 'partial'; result['review_states'].append('EVIDENCE_INCOMPLETE')
    if all(r['status'] in {'blocked', 'invalid_input'} for r in executed.values()):
        result['status'] = 'blocked'
    for source in executed.values():
        for diagnostic in source['diagnostics']:
            if diagnostic['code'] == 'EMISSION_FACTOR_REQUIRED' and diagnostic not in result['diagnostics']:
                result['diagnostics'].append(copy.deepcopy(diagnostic))
    result['diagnostics'].extend([{'code': 'CARBON_ACCOUNTING_WORKFLOW', 'message': json.dumps(report, sort_keys=True)},
                                  {'code': 'CARBON_ACCOUNTING_INPUTS', 'message': json.dumps(parameters, sort_keys=True)}])
    result['next_actions'] = ['Review separate selected accounts and retained gaps; obtain source and professional/assurance review before reliance or disclosure.']
    final = propose(working, result, 'Preserve separate carbon accounts and workflow trace without assurance or combined totals')['state']
    final['revision'] = state['revision'] + 1
    validate_state(final)
    return {'result': result, 'proposal': {'base_revision': state['revision'], 'reason': 'Atomic carbon workflow candidate; no state write or publication', 'state': final}}
