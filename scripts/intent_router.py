"""Plan development routes from user intent; never execute or approve a skill."""
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

from .contract_validation import ROOT, validate_state
from .state_proposal import propose


CATALOG = ROOT / 'router/catalog.json'
APPROVED_REVISION = '903a089e3993cbab3c950ad5e11defbf76a4de73'
PATTERNS = {
    'operations': r'\b(cut|reduce|lower|improve|efficiency)\b.*\b(carbon|footprint|energy|water|waste|factory|operations)\b',
    'regulatory': r'\b(csrd|regulation|regulatory|legal|reporting obligation|mandatory reporting|apply to my company)\b',
    'claims': r'\b(claim|claims|carbon neutral|net[ -]zero|greenwashing|substantiat\w*)\b',
}


def _fields(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('Exact router fields required.')


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value) and len(value) == len(set(value))


def load_catalog(pin):
    _fields(pin, {'path', 'sha256'})
    if pin['path'] != 'router/catalog.json':
        raise ValueError('Only the local development catalog is supported.')
    raw = CATALOG.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Catalog bytes differ from the selected pin.')
    catalog = json.loads(raw)
    _fields(catalog, {'id', 'version', 'status', 'capabilities', 'routes'})
    if (catalog['id'], catalog['version'], catalog['status']) != ('development-router', '0.1.0', 'draft_router_not_release_approved'):
        raise ValueError('Explicit draft development catalog required.')
    for capability in catalog['capabilities'].values():
        _fields(capability, {'operation', 'kind', 'path', 'sha256_utf8_lf', 'reviewed_revision', 'approval_scope'})
        if capability['reviewed_revision'] != APPROVED_REVISION or capability['approval_scope'] != 'development_only':
            raise ValueError('Capability must reference the recorded development approval.')
        path = Path(capability['path'])
        if path.is_absolute() or '..' in path.parts or not (ROOT / path).resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Capability paths must stay inside the repository.')
        if capability['kind'] not in {'skill', 'skillset', 'helper'}:
            raise ValueError('Supported capability kind required.')
        approved = subprocess.run(['git', 'show', APPROVED_REVISION + ':' + capability['path']], cwd=ROOT,
                                  capture_output=True, timeout=10)
        if approved.returncode or hashlib.sha256(approved.stdout.replace(b'\r\n', b'\n')).hexdigest() != capability['sha256_utf8_lf']:
            raise ValueError('Declared capability content is absent from the actual approved Git revision.')
        if capability['kind'] in {'skill', 'skillset'}:
            prefix = 'skills/' if capability['kind'] == 'skill' else 'skillsets/'
            match = re.search(r'^name: (.+)$', approved.stdout.decode('utf-8').replace('\r\n', '\n'), re.M)
            if not capability['path'].startswith(prefix) or not capability['path'].endswith('/SKILL.md') or match is None or match.group(1) != capability['operation']:
                raise ValueError('Approved entrypoint name and capability kind must match.')
        elif {'scripts/jurisdiction_tools.py': 'screen-jurisdiction-applicability',
              'scripts/claims_review.py': 'assess-claim-evidence'}.get(capability['path']) != capability['operation']:
            raise ValueError('Unsupported helper mapping.')
    if set(catalog['routes']) != set(PATTERNS):
        raise ValueError('Exactly the documented intent routes are supported.')
    for route in catalog['routes'].values():
        _fields(route, {'review_states', 'steps'})
        if not route['steps'] or not _strings(route['review_states']):
            raise ValueError('Nonempty route and review states required.')
        if not set(route['review_states']) <= {'PROFESSIONAL_REVIEW_REQUIRED', 'LEGAL_REVIEW_REQUIRED'}:
            raise ValueError('Supported route review obligations required.')
        steps = route['steps']; ids = [s['id'] for s in steps]
        if not _strings(ids): raise ValueError('Distinct route step IDs required.')
        for step in steps:
            _fields(step, {'id', 'capability', 'depends_on', 'required_inputs'})
            if step['capability'] not in catalog['capabilities'] or not _strings(step['depends_on']) or not _strings(step['required_inputs']):
                raise ValueError('Known capabilities and distinct dependencies/inputs required.')
            if not set(step['depends_on']) <= set(ids): raise ValueError('Unresolved route dependency.')
        _ordered(steps)
    return catalog


def _ordered(steps):
    remaining = list(steps); ordered = []; seen = set()
    while remaining:
        ready = [s for s in remaining if set(s['depends_on']) <= seen]
        if not ready: raise ValueError('Cyclic route dependencies.')
        for step in ready:
            ordered.append(step); seen.add(step['id']); remaining.remove(step)
    return ordered


def route_request(state, parameters):
    validate_state(state)
    _fields(parameters, {'request', 'intent', 'catalog_pin', 'supplied_inputs', 'upstream_result_ids', 'selections', 'result_id'})
    if not isinstance(parameters['request'], str) or not parameters['request'].strip() or len(parameters['request']) > 10000:
        raise ValueError('A bounded original user request is required.')
    if parameters['intent'] not in {'auto', 'unknown', *PATTERNS}:
        raise ValueError('Supported explicit intent or auto required.')
    if not _strings(parameters['supplied_inputs']) or not isinstance(parameters['upstream_result_ids'], dict):
        raise ValueError('Distinct declared inputs and selected upstream results required.')
    _fields(parameters['selections'], {'method', 'framework', 'jurisdiction'})
    for selection in parameters['selections'].values():
        if selection is not None:
            _fields(selection, {'name', 'version'})
            if not all(isinstance(v, str) and v.strip() for v in selection.values()):
                raise ValueError('Selected method/framework/jurisdiction requires an explicit name and version.')
    ident = parameters['result_id']
    if not isinstance(ident, str) or not ident.strip() or any(r['id'] == ident for r in state['results']):
        raise ValueError('Unused result ID required.')
    result = {'id': ident, 'skill': 'route-sustainability-request', 'contract_version': '0.1.0', 'status': 'partial',
              'review_states': list(dict.fromkeys(['ADVISORY'] + [r['state'] for r in state['review_requirements'] if r['status'] == 'open'])),
              'review_requirements': copy.deepcopy(state['review_requirements']), 'metrics': [],
              'evidence_ids': [], 'assumptions': list(state['assumptions']), 'data_gaps': copy.deepcopy(state['data_gaps']),
              'diagnostics': [], 'next_actions': []}
    def gap(field, reason, code='ROUTE_INPUT_REQUIRED'):
        result['data_gaps'].append({'id': ident + '-route-gap-' + str(len(result['data_gaps'])), 'field': field,
                                   'reason': reason, 'impact': 'No dependent execution is authorized.', 'remedy': 'Reconcile inputs and obtain the required review.'})
        result['diagnostics'].append({'code': code, 'message': reason})
    report = {'execution_contract': 'intent-router-0.1.0', 'original_request': parameters['request'],
              'intent_source': 'bounded lexical candidates' if parameters['intent'] == 'auto' else 'caller-selected classification; unverified',
              'candidates': [], 'selected_intent': None, 'steps': [], 'catalog_pin': copy.deepcopy(parameters['catalog_pin']),
              'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
              'selections': copy.deepcopy(parameters['selections']), 'selection_applicability_verified': False,
              'declared_inputs': list(parameters['supplied_inputs']), 'input_fitness_verified': False,
              'workflow_executed': False, 'execution_authorized': False, 'publication_authorized': False}
    try:
        catalog = load_catalog(parameters['catalog_pin'])
        candidates = [k for k, pattern in PATTERNS.items() if re.search(pattern, parameters['request'], re.I | re.S)] if parameters['intent'] == 'auto' else ([] if parameters['intent'] == 'unknown' else [parameters['intent']])
        report['candidates'] = candidates
        if len(candidates) != 1:
            gap('intent', 'Clarify the requested workflow; multiple or no supported intents were identified.', 'ROUTE_CLARIFICATION_REQUIRED')
        else:
            selected = candidates[0]; report['selected_intent'] = selected; route = catalog['routes'][selected]
            result['review_states'] = list(dict.fromkeys(result['review_states'] + route['review_states']))
            for review_state in route['review_states']:
                result['review_requirements'].append({'id': ident + '-' + review_state.lower(), 'state': review_state,
                    'reason': 'Review route scope, source fitness and applicability before relying on workflow outputs.',
                    'scope': 'Proposed ' + selected + ' route for ' + state['organization']['id'],
                    'reviewer_role': 'Qualified legal reviewer' if review_state == 'LEGAL_REVIEW_REQUIRED' else 'Qualified sustainability reviewer',
                    'status': 'open', 'resolution': None})
            ids = {s['id'] for s in route['steps']}
            if not set(parameters['upstream_result_ids']) <= ids: raise ValueError('Upstream selection refers to an unrelated route step.')
            indexed = {r['id']: r for r in state['results']}; statuses = {}
            for step in _ordered(route['steps']):
                cap = catalog['capabilities'][step['capability']]; path = ROOT / cap['path']
                available = path.is_file() and hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == cap['sha256_utf8_lf']
                missing = sorted(set(step['required_inputs']) - set(parameters['supplied_inputs']))
                if selected == 'regulatory':
                    missing = sorted(set(missing) | {key for key in ('framework', 'framework_version', 'jurisdiction', 'jurisdiction_version')
                        if parameters['selections'][key.removesuffix('_version')] is None})
                sources = parameters['upstream_result_ids'].get(step['id'], [])
                if not _strings(sources) or not set(sources) <= set(indexed): raise ValueError('Selected upstream result must resolve exactly.')
                if any(indexed[r]['skill'] != cap['operation'] for r in sources): raise ValueError('Upstream result belongs to a different capability.')
                blocked = any(indexed[r]['status'] in {'blocked', 'invalid_input'} for r in sources)
                factor_blocked = any(d['code'] == 'EMISSION_FACTOR_REQUIRED' for r in sources for d in indexed[r]['diagnostics'])
                blocked = blocked or factor_blocked
                result['evidence_ids'] = sorted(set(result['evidence_ids']) | {e for r in sources for e in indexed[r]['evidence_ids']})
                dependencies_blocked = any(statuses[d] != 'planned_unverified' for d in step['depends_on'])
                status = 'unavailable' if not available else 'blocked_source' if blocked else 'blocked_dependency' if dependencies_blocked else 'missing_inputs' if missing else 'planned_unverified'
                statuses[step['id']] = status
                if not available: gap(step['id'], 'Installed capability differs from its recorded reviewed content or is missing.', 'ROUTE_CAPABILITY_UNAVAILABLE')
                if missing: gap(step['id'], 'Missing declared inputs: ' + ', '.join(missing))
                if factor_blocked or 'emission_factors' in missing: gap(step['id'], 'A selected emissions branch requires defensible factors; no factor is inferred.', 'EMISSION_FACTOR_REQUIRED')
                if blocked: gap(step['id'], 'Selected upstream result is blocked; it cannot supply a dependent result.', 'ROUTE_SOURCE_BLOCKED')
                report['steps'].append({**copy.deepcopy(step), 'selected_capability': copy.deepcopy(cap), 'available_at_reviewed_content': available,
                                        'status': status, 'missing_inputs': missing, 'upstream_result_ids': sources,
                                        'upstream_sources_reproduced': False})
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as error:
        result['status'] = 'blocked'; report['steps'] = []; report['selected_intent'] = None
        gap('catalog_or_route', str(error), 'ROUTE_CATALOG_REQUIRED')
    result['diagnostics'].append({'code': 'ROUTE_PLAN', 'message': json.dumps(report, sort_keys=True)})
    result['diagnostics'].append({'code': 'ROUTE_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    if result['data_gaps']:
        result['review_states'] = list(dict.fromkeys(result['review_states'] + ['EVIDENCE_INCOMPLETE']))
    result['next_actions'] = ['Review the proposed route, reconcile inputs and run each approved capability with its own validation.']
    return {'result': result, 'proposal': propose(state, result, 'Preserve request and proposed route; no skill execution or approval')}
