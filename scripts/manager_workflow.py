"""Connect reviewed domain helpers in one source-preserving organization recipe."""
import copy
import hashlib
import json

from .contract_validation import validate_state
from .operations_tools import RUNNERS, run_operations
from .strategy_tools import OPERATIONS as STRATEGY, run_strategy
from .framework_tools import run_framework
from .state_proposal import propose


def _ids(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value) and len(value) == len(set(value))


def _recipe(state, p):
    fields = {'baseline', 'kpis', 'operations', 'targets', 'strategy', 'transition', 'roadmap', 'disclosure', 'manager_review', 'result_id'}
    if not isinstance(p, dict) or set(p) != fields or not isinstance(p['targets'], list) or not p['targets']:
        raise ValueError('Exact nonempty organization recipe required.')
    slots = [('establish-baseline', p['baseline']), ('define-kpis', p['kpis']), ('sustainable-operations', p['operations'])]
    slots += [('develop-target', t) for t in p['targets']]
    slots += [('build-sustainability-strategy', p['strategy']), ('build-transition-plan', p['transition']),
              ('build-implementation-roadmap', p['roadmap']), ('map-framework-disclosures', p['disclosure'])]
    for skill, params in slots:
        expected = STRATEGY.get(skill, {'steps', 'opportunities', 'planning_review', 'result_id'} if skill == 'sustainable-operations'
                                else {'inventory_result_id', 'adapters', 'notes', 'mapping_review', 'fixture_mode', 'result_id'})
        if not isinstance(params, dict) or set(params) != expected:
            raise ValueError('Use the exact existing helper fields in every recipe slot.')
    ops = p['operations']['steps']
    if not isinstance(ops, list) or not ops: raise ValueError('Nonempty operational analyses required.')
    for step in ops:
        if not isinstance(step, dict) or set(step) != {'skill', 'parameters'} or step['skill'] not in RUNNERS or not isinstance(step['parameters'], dict):
            raise ValueError('Only existing bounded operational analyses are supported.')
    result_ids = [params['result_id'] for _, params in slots] + [s['parameters'].get('result_id') for s in ops] + [p['result_id']]
    if not _ids(result_ids) or set(result_ids) & {r['id'] for r in state['results']}:
        raise ValueError('Every recipe, nested analysis and aggregate needs a fresh distinct result ID.')
    review = p['manager_review']; required = {'boundary_id', 'period', 'scope', 'evidence_ids', 'reviewer_role', 'rationale', 'coverage_complete',
                                             'energy_baseline_result_id', 'inventory_result_id'}
    if (not isinstance(review, dict) or set(review) != required or review['boundary_id'] != state['organizational_boundary']['id']
        or review['period'] != state['reporting_period'] or type(review['coverage_complete']) is not bool
        or not _ids(review['evidence_ids']) or not review['evidence_ids'] or not set(review['evidence_ids']) <= {e['id'] for e in state['evidence']}
        or not all(isinstance(review[k], str) and review[k].strip() for k in ('scope', 'rationale', 'reviewer_role'))):
        raise ValueError('Attributed manager review must match current boundary/period and resolve evidence.')
    energy = next((s['parameters'] for s in ops if s['skill'] == 'build-energy-baseline' and s['parameters']['result_id'] == review['energy_baseline_result_id']), None)
    inventory = next((s['parameters'] for s in ops if s['skill'] == 'build-ghg-inventory' and s['parameters']['result_id'] == review['inventory_result_id']), None)
    if energy is None or inventory is None or not _ids(p['baseline']['metric_ids']) or set(energy['metric_ids']) != set(p['baseline']['metric_ids']):
        raise ValueError('Strategy and selected operational energy baselines must consume the same distinct raw metric IDs.')
    if p['disclosure']['inventory_result_id'] != review['inventory_result_id']:
        raise ValueError('Disclosure must select the fresh inventory declared in this operational recipe.')
    if not p['kpis']['definitions'] or any(d['baseline_result_id'] != p['baseline']['result_id'] for d in p['kpis']['definitions']):
        raise ValueError('KPI definitions must reference this recipe baseline.')
    targets = {t['result_id'] for t in p['targets']}
    if any(t['definition_result_id'] != p['kpis']['result_id'] for t in p['targets']):
        raise ValueError('Targets must reference this recipe KPI definition result.')
    selected = {i for pillar in p['strategy']['pillars'] for i in pillar['target_result_ids']}
    if not selected or not selected <= targets: raise ValueError('Strategy must select known fresh recipe targets.')
    if p['transition']['strategy_result_id'] != p['strategy']['result_id'] or p['roadmap']['transition_result_id'] != p['transition']['result_id']:
        raise ValueError('Transition and roadmap must bind this recipe strategy and transition.')
    for path in p['transition']['pathways']:
        if path['target_result_id'] is not None and path['target_result_id'] not in targets:
            raise ValueError('Transition pathways must select fresh recipe targets.')
        if any(c['target_result_id'] not in targets for c in path['checkpoints']):
            raise ValueError('Checkpoints must select fresh recipe targets.')
    return slots


def _empty(state, skill, ident):
    return {'id': ident, 'skill': skill, 'contract_version': '0.1.0', 'status': 'completed', 'metrics': [],
            'review_states': list(dict.fromkeys(['ADVISORY'] + [r['state'] for r in state['review_requirements'] if r['status'] == 'open'])),
            'review_requirements': copy.deepcopy(state['review_requirements']), 'evidence_ids': [],
            'assumptions': list(state['assumptions']), 'data_gaps': copy.deepcopy(state['data_gaps']), 'diagnostics': [], 'next_actions': []}


def _blocked(state, skill, params, sources, reason):
    result = _empty(state, skill, params['result_id']); result['status'] = 'blocked'
    result['review_states'] = list(dict.fromkeys(result['review_states'] + ['EVIDENCE_INCOMPLETE']))
    result['evidence_ids'] = sorted({e for r in sources if r is not None for e in r['evidence_ids']})
    result['data_gaps'].append({'id': result['id'] + '-manager-gap', 'field': 'organization_recipe', 'reason': reason,
        'impact': 'This stage supplies no supported result.', 'remedy': 'Reconcile selected source inputs and prior blocked dependencies.'})
    result['diagnostics'] = [{'code': 'MANAGER_STAGE_BLOCKED', 'message': reason}, {'code': 'MANAGER_STAGE_INPUTS', 'message': json.dumps(params, sort_keys=True)}]
    if any(d['code'] == 'EMISSION_FACTOR_REQUIRED' for r in sources if r is not None for d in r['diagnostics']):
        result['diagnostics'].append({'code': 'EMISSION_FACTOR_REQUIRED', 'message': 'A selected recipe prerequisite retains missing defensible factors.'})
    result['next_actions'] = [result['data_gaps'][-1]['remedy']]
    return {'result': result, 'proposal': propose(state, result, 'Retain blocked organization stage without a substituted outcome')}


def run_manager(state, parameters):
    validate_state(state); slots = _recipe(state, parameters)
    p = parameters; working = copy.deepcopy(state); trace = []
    for skill, params in slots:
        dependencies = []
        if skill == 'define-kpis': dependencies = [p['baseline']['result_id']]
        elif skill == 'develop-target': dependencies = [p['kpis']['result_id']]
        elif skill == 'build-sustainability-strategy': dependencies = sorted({i for pillar in params['pillars'] for i in pillar['target_result_ids']})
        elif skill == 'build-transition-plan': dependencies = [p['strategy']['result_id']] + sorted({c['target_result_id'] for path in params['pathways'] for c in path['checkpoints']})
        elif skill == 'build-implementation-roadmap': dependencies = [p['transition']['result_id']]
        elif skill == 'map-framework-disclosures': dependencies = [p['manager_review']['inventory_result_id']]
        indexed = {r['id']: r for r in working['results']}; sources = [indexed.get(i) for i in dependencies]
        skipped = any(r is None or r['status'] in {'blocked', 'invalid_input'} for r in sources)
        if skipped:
            output = _blocked(working, skill, params, sources, 'A selected prerequisite is missing or blocked; this helper was not invoked.')
        else:
            try:
                output = run_operations(working, copy.deepcopy(params)) if skill == 'sustainable-operations' else (
                    run_framework(working, skill, copy.deepcopy(params)) if skill == 'map-framework-disclosures' else run_strategy(working, skill, copy.deepcopy(params)))
            except (ValueError, KeyError, TypeError) as error:
                output = _blocked(working, skill, params, sources, str(error))
        working = output['proposal']['state']
        trace.append({'skill': skill, 'result_id': params['result_id'], 'source_result_ids': dependencies,
                      'helper_invoked': not skipped, 'status': output['result']['status']})
    result = _empty(working, 'sustainability-manager', p['result_id']); review = p['manager_review']
    produced = working['results'][len(state['results']):]
    result['evidence_ids'] = sorted(set(review['evidence_ids']) | {e for r in produced for e in r['evidence_ids']})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + ['PROFESSIONAL_REVIEW_REQUIRED', 'ASSURANCE_REQUIRED']))
    for flag, role in [('PROFESSIONAL_REVIEW_REQUIRED', review['reviewer_role']), ('ASSURANCE_REQUIRED', 'Qualified assurance practitioner')]:
        result['review_requirements'].append({'id': result['id'] + '-' + flag.lower(), 'state': flag,
            'reason': 'Review actual cross-domain source fitness, measurement coverage, service definitions, model applicability and accountable-owner decisions.',
            'scope': review['scope'], 'reviewer_role': role, 'status': 'open', 'resolution': None})
    views = {}
    for source in produced:
        views[source['id']] = {'result_id': source['id'], 'skill': source['skill'], 'status': source['status'],
            'metric_ids': [m['id'] for m in source['metrics']], 'evidence_ids': list(source['evidence_ids']),
            'sha256_result_utf8_json_sorted_keys': hashlib.sha256(json.dumps(source, sort_keys=True).encode('utf-8')).hexdigest()}
        result['diagnostics'].extend(copy.deepcopy(d) for d in source['diagnostics'] if d['code'] == 'EMISSION_FACTOR_REQUIRED' and d not in result['diagnostics'])
    report = {'execution_contract': 'organization-manager-0.1.0', 'manager_review': copy.deepcopy(review), 'stages': trace,
              'source_result_views': views, 'raw_business_data_ingestion_performed': False,
              'input_result_ids': [r['id'] for r in state['results']],
              'normalized_input_result_ids': [r['id'] for r in state['results'] if r['skill'] == 'normalize-sustainability-data'],
              'opportunity_ids': [o['id'] for o in working['opportunities'] if o['id'] not in {x['id'] for x in state['opportunities']}],
              'selected_inventory_result_id': review['inventory_result_id'], 'selected_energy_baseline_result_id': review['energy_baseline_result_id'],
              'combined_cross_domain_total': None, 'source_authenticity_verified': False, 'organization_coverage_authenticated': False,
              'finance_benefit_attribution_verified': False, 'target_feasibility_verified': False, 'progress_verified': False,
              'funding_or_implementation_authorized': False, 'framework_conformity_verified': False, 'publication_authorized': False, 'v1_readiness_verified': False}
    if not review['coverage_complete']:
        result['data_gaps'].append({'id': result['id'] + '-coverage-gap', 'field': 'organization_coverage',
            'reason': 'Selected organization workflow coverage is declared incomplete.', 'impact': 'The full organization and v1 readiness remain unverified.',
            'remedy': 'Reconcile missing domains, scopes, source/rights decisions, independent evaluation and release review.'})
    if result['data_gaps'] or any(r['status'] != 'completed' for r in produced):
        result['status'] = 'partial'; result['review_states'].append('EVIDENCE_INCOMPLETE')
    if all(r['status'] in {'blocked', 'invalid_input'} for r in produced): result['status'] = 'blocked'
    result['diagnostics'].extend([{'code': 'ORGANIZATION_MANAGER', 'message': json.dumps(report, sort_keys=True)},
                                  {'code': 'MANAGER_INPUTS', 'message': json.dumps(p, sort_keys=True)}])
    result['next_actions'] = ['Review qualified source views and unresolved cross-domain, organization and owner requirements before relying on or disclosing outputs.']
    final = propose(working, result, 'Connect selected organization analyses and prospective plans without approval')['state']
    final['revision'] = state['revision'] + 1; validate_state(final)
    return {'result': result, 'proposal': {'base_revision': state['revision'], 'reason': 'Atomic organization recipe; no state-file write or publication', 'state': final}}
