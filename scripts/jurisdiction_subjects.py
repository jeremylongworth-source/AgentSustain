"""Draft subject/year jurisdiction candidates with explicit event-date facts."""
import copy
import json

from .climate_tools import _date, _fields, _sources, _text
from .contract_validation import validate_state
from .jurisdiction_tools import FIT, _combine, _evaluate, _number, _typed, read_pinned_pack, validate_pack
from .state_proposal import propose


CONTRACT = 'subject-screen-0.1.0'
KINDS = {'facility', 'facility_group', 'legal_entity'}
BASES = {'reporting_year', 'operating_interval', 'responsibility_event'}


def load_subject_pack(pin, fixture_mode):
    original = read_pinned_pack(pin)
    normalized = copy.deepcopy(original)
    if not isinstance(normalized, dict): raise ValueError('Structured subject pack required.')
    if normalized.pop('execution_contract', None) != CONTRACT:
        raise ValueError('Explicit subject-screen execution contract required; no automatic pack migration.')
    if not isinstance(normalized.get('attributes'), list) or not normalized['attributes'] or not isinstance(normalized.get('rules'), list) or not normalized['rules']:
        raise ValueError('Nonempty structured subject attribute/rule definitions required.')
    for attribute in normalized['attributes']:
        if not isinstance(attribute, dict): raise ValueError('Structured subject attribute required.')
        if attribute.pop('temporal_basis', None) not in BASES:
            raise ValueError('Every subject attribute needs its explicit supported temporal basis.')
    definitions = {a['id']: a for a in original['attributes']}
    for rule in normalized['rules']:
        if not isinstance(rule, dict): raise ValueError('Structured subject rule required.')
        years = rule.pop('reporting_years', None)
        if (not isinstance(years, list) or not years or any(type(y) is not int or not 1 <= y <= 9999 for y in years)
                or len(years) != len(set(years))):
            raise ValueError('Distinct explicit calendar reporting years required; not inferred from legal dates.')
        if rule.pop('subject_kind', None) not in KINDS:
            raise ValueError('Explicit supported rule subject kind required.')
        operator = rule.pop('operator_attribute', None)
        if (operator not in definitions or definitions[operator]['type'] != 'string'
                or definitions[operator]['temporal_basis'] != 'responsibility_event'):
            raise ValueError('Rule operator attribute must be a responsibility-event string record.')
    validate_pack(normalized, fixture_mode)
    return original


def _period(value):
    _fields(value, {'start', 'end'})
    if _date(value['start']) > _date(value['end']):
        raise ValueError('Explicit ordered subject/fact period required.')
    return value


def _operating_context(subject, reporting_period):
    operation = subject['operation_period']
    if operation is None or subject['end_basis'] == 'unknown':
        return None, None
    if operation['end'] < reporting_period['start'] or operation['start'] > reporting_period['end']:
        return None, False
    if subject['end_basis'] == 'observed_through' and operation['end'] < reporting_period['end']:
        # The last observed date is not a cessation date or a forecast of year-end presence.
        return None, None
    interval = {'start': max(operation['start'], reporting_period['start']),
                'end': min(operation['end'], reporting_period['end'])}
    return interval, True


def screen_subject_jurisdiction(state, parameters):
    validate_state(state)
    required = {'pack_pins', 'subjects', 'facts', 'rule_reviews', 'screening_review', 'fixture_mode', 'result_id'}
    if not isinstance(parameters, dict) or set(parameters) != required or not _text(parameters['result_id']):
        raise ValueError('Exact subject-screen parameters and substantive result ID required.')
    result = {'id': parameters['result_id'], 'skill': 'screen-subject-jurisdiction-applicability', 'contract_version': '0.1.0',
              'status': 'partial', 'review_states': ['ADVISORY'], 'review_requirements': copy.deepcopy(state['review_requirements']),
              'metrics': [], 'evidence_ids': [], 'assumptions': list(state['assumptions']),
              'data_gaps': copy.deepcopy(state['data_gaps']), 'diagnostics': [], 'next_actions': []}
    refs = set()
    def gap(reason):
        result['data_gaps'].append({'id': result['id'] + '-gap-' + str(len(result['data_gaps'])), 'field': 'jurisdiction_subject',
            'reason': reason, 'impact': 'Subject, period or responsibility remains conditional; no legal obligation or clearance follows.',
            'remedy': 'Inspect matched subject, event, quantity and primary-source records with qualified legal review.'})
    try:
        if not isinstance(parameters['fixture_mode'], bool):
            raise ValueError('Explicit boolean fixture mode required.')
        review = parameters['screening_review']
        _fields(review, {'boundary_id', 'period', 'as_of_date', 'scope', 'evidence_ids', 'evidence_fit', 'rationale', 'reviewer_role'},
                ('scope', 'rationale', 'reviewer_role'))
        _sources(state, review['evidence_ids'], refs)
        period = _period(review['period']); year = _date(period['start']).year
        if (review['boundary_id'] != state['organizational_boundary']['id'] or period != state['reporting_period']
                or period != {'start': f'{year:04d}-01-01', 'end': f'{year:04d}-12-31'} or review['evidence_fit'] not in FIT):
            raise ValueError('Matched organization boundary and full calendar reporting year required.')
        as_of = _date(review['as_of_date'])
        if as_of < _date(period['start']): raise ValueError('Review cannot predate its reporting year.')
        review_fit = bool(review['evidence_ids']) and review['evidence_fit'] == 'reviewed_supporting'
        pins = parameters['pack_pins']
        if not isinstance(pins, list) or not pins: raise ValueError('Explicit nonempty subject-pack pins required.')
        packs = [load_subject_pack(p, parameters['fixture_mode']) for p in pins]
        if len({p['id'] for p in packs}) != len(packs): raise ValueError('One selected version per pack ID required.')
        definitions = {}
        for pack in packs:
            for definition in pack['attributes']:
                if definition['id'] in definitions and definitions[definition['id']] != definition:
                    raise ValueError('Conflicting subject attribute definitions across packs.')
                definitions[definition['id']] = definition
        if not isinstance(parameters['subjects'], list) or not parameters['subjects']:
            raise ValueError('Nonempty explicit subject list required; no implicit organization/facility selection.')
        subjects = {}; known_facilities = {f['id'] for f in state['facilities']}
        bounded_facilities = set(state['organizational_boundary']['facility_ids'])
        for subject in parameters['subjects']:
            _fields(subject, {'id', 'kind', 'facility_ids', 'candidate_operator_id', 'operation_period', 'end_basis',
                              'definition', 'evidence_ids', 'evidence_fit', 'rationale', 'uncertainty'},
                    ('id', 'kind', 'candidate_operator_id', 'definition', 'rationale', 'uncertainty'))
            ids = subject['facility_ids']
            if (subject['id'] in subjects or subject['kind'] not in KINDS or subject['end_basis'] not in {'ceased', 'observed_through', 'unknown'}
                    or subject['evidence_fit'] not in FIT or not isinstance(ids, list) or any(not _text(i) for i in ids)
                    or len(ids) != len(set(ids)) or not set(ids) <= known_facilities or not set(ids) <= bounded_facilities
                    or subject['kind'] == 'facility' and len(ids) != 1 or subject['kind'] == 'facility_group' and not ids):
                raise ValueError('Distinct scoped subjects, resolved facility IDs and explicit observation-end basis required.')
            if subject['operation_period'] is not None: _period(subject['operation_period'])
            if subject['end_basis'] != 'unknown' and subject['operation_period'] is None:
                raise ValueError('Known cessation/observation basis requires its explicit operation interval.')
            if subject['end_basis'] != 'unknown' and _date(subject['operation_period']['end']) > as_of:
                raise ValueError('Observed operation or actual cessation cannot postdate the review.')
            sources = _sources(state, subject['evidence_ids'], refs)
            supported = bool(sources) and subject['evidence_fit'] == 'reviewed_supporting'
            supported = supported and all(e['boundary_id'] == review['boundary_id'] and e['source']['version'] is not None
                and _date(e['source']['accessed']) <= as_of for e in sources)
            interval, operating = _operating_context(subject, period)
            if not supported: gap(subject['id'] + ': subject definition/grouping or source fitness is unverified.')
            if operating is None: gap(subject['id'] + ': observed-through/unknown operation cannot establish cessation or year-end presence.')
            subjects[subject['id']] = {'record': copy.deepcopy(subject), 'source_snapshots': sources,
                'supported': supported, 'operating_interval': interval, 'operated_in_year': operating,
                'responsibility_event': interval['end'] if interval else None}
        if not isinstance(parameters['facts'], list): raise ValueError('Explicit subject fact list required.')
        facts = {ident: {} for ident in subjects}
        for fact in parameters['facts']:
            _fields(fact, {'subject_id', 'attribute_id', 'value', 'unit', 'boundary_id', 'period', 'evidence_ids',
                          'evidence_fit', 'rationale', 'uncertainty', 'coverage_complete'},
                    ('subject_id', 'attribute_id', 'unit', 'rationale', 'uncertainty'))
            sid, ident = fact['subject_id'], fact['attribute_id']
            if (sid not in subjects or ident not in definitions or ident in facts[sid]
                    or fact['evidence_fit'] not in FIT or not isinstance(fact['coverage_complete'], bool)):
                raise ValueError('Distinct defined facts on explicit current subjects required.')
            definition = definitions[ident]; subject = subjects[sid]
            if fact['unit'] != definition['unit'] or fact['boundary_id'] != review['boundary_id']:
                raise ValueError('Fact unit and enclosing organization boundary must match exactly.')
            _period(fact['period'])
            value = fact['value']
            if value is not None:
                if definition['type'] == 'number':
                    _fields(value, {'lower', 'upper'})
                    for bound in value.values():
                        if bound is not None: _number(bound)
                    if value['lower'] is not None and value['upper'] is not None and _number(value['lower']) > _number(value['upper']):
                        raise ValueError('Source numeric interval is reversed.')
                else: _typed(value, definition['type'])
            sources = _sources(state, fact['evidence_ids'], refs)
            if not set(fact['evidence_ids']) <= set(subject['record']['evidence_ids']):
                raise ValueError('Fact evidence must be explicitly bound to this subject; no cross-subject borrowing.')
            basis = definition['temporal_basis']
            expected = (period if basis == 'reporting_year' else subject['operating_interval'] if basis == 'operating_interval'
                        else {'start': subject['responsibility_event'], 'end': subject['responsibility_event']}
                        if subject['responsibility_event'] else None)
            supported = (subject['supported'] and bool(sources) and fact['evidence_fit'] == 'reviewed_supporting'
                         and fact['coverage_complete'] and expected is not None and fact['period'] == expected
                         and _date(fact['period']['end']) <= as_of)
            supported = supported and all(e['boundary_id'] == review['boundary_id'] and e['unit'] == fact['unit']
                and e['source']['version'] is not None and _date(e['source']['accessed']) <= as_of
                and e['period']['start'] <= fact['period']['start'] and e['period']['end'] >= fact['period']['end'] for e in sources)
            if not supported or value is None: gap(sid + '/' + ident + ': source scope, temporal basis, completeness or fitness is unresolved.')
            facts[sid][ident] = {'record': copy.deepcopy(fact), 'supported': supported, 'expected_period': expected,
                                'temporal_basis': basis, 'source_snapshots': sources}
        reviews = {}; review_sources = {}
        if not isinstance(parameters['rule_reviews'], list): raise ValueError('Explicit rule-review list required.')
        for item in parameters['rule_reviews']:
            _fields(item, {'pack_id', 'rule_id', 'checked_as_of', 'evidence_ids', 'evidence_fit', 'rationale'},
                    ('pack_id', 'rule_id', 'rationale'))
            key = (item['pack_id'], item['rule_id'])
            if key in reviews or item['evidence_fit'] not in FIT or _date(item['checked_as_of']) > as_of:
                raise ValueError('Distinct nonfuture rule fitness reviews required.')
            reviews[key] = item; review_sources[key] = _sources(state, item['evidence_ids'], refs)
        rows = []; used = {sid: set() for sid in subjects}; seen = set()
        for pack, pin in zip(packs, pins):
            for rule in pack['rules']:
                key = (pack['id'], rule['id']); source_review = reviews.get(key); primary = review_sources.get(key, [])
                if source_review: seen.add(key)
                if _date(rule['source']['retrieved']) > as_of: raise ValueError('Review cannot predate primary source retrieval.')
                source_fit = (review_fit and source_review is not None and source_review['evidence_fit'] == 'reviewed_supporting'
                    and source_review['checked_as_of'] == review['as_of_date'] and rule['source']['version'] is not None
                    and all(_date(e['source']['accessed']) <= as_of for e in primary)
                    and any(e['source']['locator'] == rule['source']['locator'] and e['source']['version'] == rule['source']['version'] for e in primary))
                for sid, subject in subjects.items():
                    traces = []; selected = facts[sid]
                    location = _evaluate({'attribute': pack['jurisdiction_attribute'], 'operator': 'intersects', 'value': [rule['jurisdiction']]}, selected, definitions, used[sid], traces)
                    condition = _evaluate(rule['condition'], selected, definitions, used[sid], traces)
                    exceptions = [{'id': x['id'], 'description': x['description'], 'verdict': _evaluate(x['condition'], selected, definitions, used[sid], traces)} for x in rule['exceptions']]
                    excluded = _combine([x['verdict'] for x in exceptions], 'any') if rule['exceptions_complete'] else None
                    if any(x['verdict'] is True for x in exceptions): excluded = True
                    operator = rule['operator_attribute']; used[sid].add(operator); operator_fact = selected.get(operator)
                    operator_match = (operator_fact['record']['value'] == subject['record']['candidate_operator_id']
                        if operator_fact and operator_fact['supported'] and operator_fact['record']['value'] is not None else None)
                    verdict = _combine([location, condition, operator_match, subject['operated_in_year'],
                        None if excluded is None else not excluded, subject['record']['kind'] == rule['subject_kind']], 'all')
                    covered = year in rule['reporting_years']; status = 'undetermined'
                    if source_fit and subject['supported'] and rule['legal_status'] != 'unknown':
                        if not covered or verdict is False: status = 'not_applicable'
                        elif verdict is True and rule['legal_status'] != 'unknown': status = 'potentially_applicable'
                    if status != 'not_applicable': gap(sid + '/' + rule['id'] + ': year/subject/operator conditions remain conditional and require legal review.')
                    if not source_fit: gap(sid + '/' + rule['id'] + ': source/version/currency fitness is unverified.')
                    if not rule['exceptions_complete']: gap(sid + '/' + rule['id'] + ': exception coverage is incomplete.')
                    rows.append({'subject_id': sid, 'subject_snapshot': copy.deepcopy(subject), 'pack_id': pack['id'], 'pack_version': pack['version'],
                        'pack_sha256': pin['sha256'], 'rule': copy.deepcopy(rule), 'source_review': copy.deepcopy(source_review),
                        'primary_source_snapshots': copy.deepcopy(primary), 'predicate_traces': traces, 'exception_verdicts': exceptions,
                        'operator_attribute': operator, 'operator_fact': copy.deepcopy(operator_fact), 'operator_identity_match': operator_match,
                        'reporting_year': year, 'reporting_year_in_selected_version': covered, 'combined_condition': verdict,
                        'preliminary_status': status, 'legal_applicability_determined': False, 'compliance_verified': False,
                        'operator_authority_adopted': False, 'quantity_method_reproduced': False, 'annualization_applied': False})
        if set(reviews) != seen: raise ValueError('Rule reviews must reference actual selected rules.')
        for sid in subjects:
            for ident in sorted(used[sid] - set(facts[sid])): gap(sid + '/' + ident + ': required fact absent; no identity, quantity or date inferred.')
        report = {'execution_contract': CONTRACT, 'packs': packs, 'pins': copy.deepcopy(pins), 'subjects': subjects, 'facts': facts,
            'screening_review': copy.deepcopy(review), 'rows': rows, 'subject_totals_combined': False,
            'shared_evidence_ids': sorted(i for i in refs if sum(i in s['record']['evidence_ids'] for s in subjects.values()) > 1),
            'unselected_facility_ids': sorted(known_facilities - {i for s in subjects.values() for i in s['record']['facility_ids']}),
            'legal_commencement_inferred_from_reporting_year': False, 'regulatory_quantity_verified': False,
            'whole_organization_coverage_verified': False, 'legal_applicability_determined': False, 'publication_authorized': False}
        if any(p['synthetic'] for p in packs):
            result['assumptions'] = list(dict.fromkeys(result['assumptions'] + ['Fictional subject-screen fixture only; no actual regulation or regulated emission account implemented.']))
        gap('Qualified subject/source/legal review remains open; quantities are declared ranges, not reproduced regulated totals.')
        result['review_requirements'].append({'id': result['id'] + '-legal-review', 'state': 'LEGAL_REVIEW_REQUIRED',
            'reason': 'Review subject grouping, operator identity/event, reporting-year versions, quantity method, exceptions and primary-source currency.',
            'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
        result['diagnostics'].append({'code': 'JURISDICTION_SUBJECT_SCREEN', 'message': json.dumps(report, sort_keys=True)})
    except (ValueError, TypeError, KeyError, OSError) as error:
        result['status'] = 'blocked'; gap(str(error))
        result['diagnostics'].append({'code': 'JURISDICTION_SUBJECT_DATA_REQUIRED', 'message': str(error)})
    result['evidence_ids'] = sorted(refs)
    result['diagnostics'].append({'code': 'JURISDICTION_SUBJECT_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + [r['state'] for r in result['review_requirements'] if r['status'] == 'open'] + ['EVIDENCE_INCOMPLETE']))
    result['next_actions'] = list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result': result, 'proposal': propose(state, result, 'Record distinct subject/year candidates without legal authority, quantity aggregation or annualization')}
