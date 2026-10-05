"""Pinned, evidence-linked preliminary rule screening; never a legal determination."""
import copy
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from .climate_tools import _date, _fields, _sources, _text
from .contract_validation import ROOT, validate_state
from .state_proposal import propose


FIT = {'reviewed_supporting', 'unverified', 'irrelevant'}
TYPES = {'number', 'string', 'boolean', 'string_set'}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Finite numeric thresholds and bounds required; booleans are not numbers.')
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Finite numeric threshold required.') from error
    if not number.is_finite():
        raise ValueError('Finite numeric thresholds and bounds required.')
    return number


def _typed(value, kind):
    if kind == 'number':
        _number(value)
        return
    valid = (kind == 'boolean' and isinstance(value, bool)
             or kind == 'string' and _text(value)
             or kind == 'string_set' and isinstance(value, list)
             and all(_text(v) for v in value) and len(value) == len(set(value)))
    if not valid:
        raise ValueError('Attribute/threshold type does not match its versioned definition.')


def _expression(expression, attributes, depth=0, budget=None):
    budget = [0] if budget is None else budget
    budget[0] += 1
    if depth > 12 or budget[0] > 128 or not isinstance(expression, dict):
        raise ValueError('Bounded declarative rule expression required; no executable code.')
    if set(expression) in ({'all'}, {'any'}):
        children = next(iter(expression.values()))
        if not isinstance(children, list) or not children:
            raise ValueError('Nonempty all/any rule conditions required.')
        for child in children:
            _expression(child, attributes, depth + 1, budget)
        return
    _fields(expression, {'attribute', 'operator', 'value'}, ('attribute', 'operator'))
    definition = attributes.get(expression['attribute'])
    if definition is None:
        raise ValueError('Every predicate must reference a defined company attribute.')
    kind, op = definition['type'], expression['operator']
    allowed = {'number': {'eq', 'ne', 'gt', 'gte', 'lt', 'lte'},
               'string': {'eq', 'ne', 'in'}, 'boolean': {'eq', 'ne'},
               'string_set': {'intersects'}}[kind]
    if op not in allowed:
        raise ValueError('Unsupported predicate operator/type combination.')
    _typed(expression['value'], 'string_set' if op == 'in' else kind)


def load_pack(pin, fixture_mode):
    _fields(pin, {'path', 'sha256'}, ('path', 'sha256'))
    base = (ROOT / 'standards/jurisdictions').resolve()
    relative = Path(pin['path'])
    path = (base / relative).resolve()
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(base) or path.suffix != '.json':
        raise ValueError('Pack must resolve within standards/jurisdictions; no external paths.')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Pack bytes differ from the explicit version pin.')
    pack = json.loads(raw)
    _fields(pack, {'id', 'version', 'synthetic', 'jurisdiction_attribute', 'attributes', 'rules', 'scope', 'limitations'},
            ('id', 'version', 'jurisdiction_attribute', 'scope', 'limitations'))
    if not isinstance(pack['synthetic'], bool) or pack['synthetic'] and not fixture_mode:
        raise ValueError('Synthetic jurisdiction rules require explicit fixture mode.')
    if not isinstance(pack['attributes'], list) or not pack['attributes'] or not isinstance(pack['rules'], list) or not pack['rules']:
        raise ValueError('Nonempty versioned attribute and rule definitions required.')
    attributes = {}
    for attribute in pack['attributes']:
        _fields(attribute, {'id', 'type', 'unit', 'definition'}, ('id', 'type', 'unit', 'definition'))
        if attribute['id'] in attributes or attribute['type'] not in TYPES:
            raise ValueError('Distinct supported attribute definitions required.')
        attributes[attribute['id']] = attribute
    if attributes.get(pack['jurisdiction_attribute'], {}).get('type') != 'string_set':
        raise ValueError('Explicit string-set jurisdiction attribute required; no inferred hierarchy.')
    ids = set()
    for rule in pack['rules']:
        _fields(rule, {'id', 'jurisdiction', 'subject', 'source', 'legal_status', 'effective_from', 'effective_to',
                       'condition', 'exceptions', 'exceptions_complete', 'uncertainty', 'reviewer_requirement'},
                ('id', 'jurisdiction', 'subject', 'legal_status', 'uncertainty', 'reviewer_requirement'))
        if rule['id'] in ids or rule['legal_status'] not in {'in_force', 'proposed', 'repealed', 'unknown'}:
            raise ValueError('Distinct rule IDs and explicit supported legal status required.')
        ids.add(rule['id'])
        source = rule['source']
        _fields(source, {'authority', 'locator', 'clause', 'version', 'retrieved'}, ('authority', 'locator', 'clause', 'retrieved'))
        if source['version'] is not None and not _text(source['version']):
            raise ValueError('Source version must be substantive or explicitly unknown.')
        if not pack['synthetic'] and not source['locator'].startswith('https://'):
            raise ValueError('Real modules require primary-source HTTPS locators.')
        _date(source['retrieved'])
        start = _date(rule['effective_from']) if rule['effective_from'] is not None else None
        end = _date(rule['effective_to']) if rule['effective_to'] is not None else None
        if start and end and start > end:
            raise ValueError('Rule effective interval is reversed.')
        if rule['legal_status'] == 'repealed' and end is None:
            raise ValueError('Repealed rule requires its last effective date; history is not silently discarded.')
        _expression(rule['condition'], attributes)
        if not isinstance(rule['exceptions'], list) or not isinstance(rule['exceptions_complete'], bool):
            raise ValueError('Explicit exception list and coverage required.')
        exception_ids = set()
        for exception in rule['exceptions']:
            _fields(exception, {'id', 'description', 'condition'}, ('id', 'description'))
            if exception['id'] in exception_ids:
                raise ValueError('Distinct exception IDs required.')
            exception_ids.add(exception['id'])
            _expression(exception['condition'], attributes)
    return pack


def _combine(values, mode):
    if mode == 'all':
        return False if False in values else None if None in values else True
    return True if True in values else None if None in values else False


def _evaluate(expression, facts, definitions, used, traces):
    if set(expression) in ({'all'}, {'any'}):
        mode = next(iter(expression))
        return _combine([_evaluate(x, facts, definitions, used, traces) for x in expression[mode]], mode)
    ident, op, target = expression['attribute'], expression['operator'], expression['value']
    used.add(ident)
    fact = facts.get(ident)
    verdict = None
    if fact and fact['supported'] and fact['record']['value'] is not None:
        value = fact['record']['value']
        if definitions[ident]['type'] == 'number':
            low, high = value['lower'], value['upper']
            if low is not None and high is not None:
                low, high, threshold = _number(low), _number(high), _number(target)
                if op == 'gte': verdict = True if low >= threshold else False if high < threshold else None
                elif op == 'gt': verdict = True if low > threshold else False if high <= threshold else None
                elif op == 'lte': verdict = True if high <= threshold else False if low > threshold else None
                elif op == 'lt': verdict = True if high < threshold else False if low >= threshold else None
                else:
                    verdict = True if low == high == threshold else False if threshold < low or threshold > high else None
                    if op == 'ne' and verdict is not None: verdict = not verdict
        elif op == 'intersects': verdict = bool(set(value) & set(target))
        elif op == 'in': verdict = value in target
        elif op == 'eq': verdict = value == target
        elif op == 'ne': verdict = value != target
    traces.append({'predicate': copy.deepcopy(expression), 'verdict': verdict,
                   'fact': copy.deepcopy(fact), 'definition': copy.deepcopy(definitions[ident])})
    return verdict


def _segments(rule, period, condition, supported):
    start, end = _date(period['start']), _date(period['end'])
    effective = _date(rule['effective_from']) if rule['effective_from'] is not None else None
    last = _date(rule['effective_to']) if rule['effective_to'] is not None else None
    cuts = {start, end + timedelta(days=1)}
    for cut in [effective, last + timedelta(days=1) if last else None]:
        if cut and start < cut <= end:
            cuts.add(cut)
    ordered = sorted(cuts)
    output = []
    for a, b in zip(ordered, ordered[1:]):
        within = None if effective is None else a >= effective and (last is None or a <= last)
        status = 'undetermined'
        if supported:
            if rule['legal_status'] in {'unknown', 'proposed'}:
                status = 'potentially_applicable' if condition is True and rule['legal_status'] == 'proposed' else 'undetermined'
            elif within is not None:
                status = ('not_applicable' if within is False or condition is False
                          else 'applicable' if condition is True else 'undetermined')
        output.append({'period': {'start': a.isoformat(), 'end': (b - timedelta(days=1)).isoformat()},
                       'within_recorded_effective_interval': within, 'preliminary_status': status})
    return output


def screen_jurisdiction(state, parameters):
    validate_state(state)
    required = {'pack_pins', 'facts', 'rule_reviews', 'screening_review', 'fixture_mode', 'result_id'}
    if not isinstance(parameters, dict) or set(parameters) != required or not _text(parameters['result_id']):
        raise ValueError('Exact jurisdiction-screen parameters and substantive result ID required.')
    result = {'id': parameters['result_id'], 'skill': 'screen-jurisdiction-applicability', 'contract_version': '0.1.0',
              'status': 'partial', 'review_states': ['ADVISORY'], 'review_requirements': copy.deepcopy(state['review_requirements']),
              'metrics': [], 'evidence_ids': [], 'assumptions': list(state['assumptions']),
              'data_gaps': copy.deepcopy(state['data_gaps']), 'diagnostics': [], 'next_actions': []}
    refs = set()
    def gap(reason):
        result['data_gaps'].append({'id': result['id'] + '-gap-' + str(len(result['data_gaps'])), 'field': 'jurisdiction_screen',
                                   'reason': reason, 'impact': 'Preliminary screening cannot establish obligations, exemption or compliance.',
                                   'remedy': 'Inspect current primary sources and matched company facts with qualified legal review.'})
    try:
        if not isinstance(parameters['fixture_mode'], bool):
            raise ValueError('Explicit boolean fixture mode required.')
        review = parameters['screening_review']
        _fields(review, {'boundary_id', 'period', 'as_of_date', 'scope', 'evidence_ids', 'evidence_fit', 'rationale', 'reviewer_role'},
                ('scope', 'rationale', 'reviewer_role'))
        _sources(state, review['evidence_ids'], refs)
        if review['boundary_id'] != state['organizational_boundary']['id'] or review['period'] != state['reporting_period'] or review['evidence_fit'] not in FIT:
            raise ValueError('Matched company boundary/reporting period and explicit screening fitness required.')
        as_of = _date(review['as_of_date'])
        if as_of < _date(review['period']['start']):
            raise ValueError('Screening review cannot predate its reporting period.')
        review_fit = bool(review['evidence_ids']) and review['evidence_fit'] == 'reviewed_supporting'
        pins = parameters['pack_pins']
        if not isinstance(pins, list) or not pins:
            raise ValueError('At least one explicit pinned pack required.')
        packs = [load_pack(pin, parameters['fixture_mode']) for pin in pins]
        if len({p['id'] for p in packs}) != len(packs):
            raise ValueError('One explicitly selected version per pack ID required; no automatic amendment precedence.')
        definitions = {}
        for pack in packs:
            for attribute in pack['attributes']:
                if attribute['id'] in definitions and definitions[attribute['id']] != attribute:
                    raise ValueError('Conflicting company-attribute definitions across selected packs.')
                definitions[attribute['id']] = attribute
        facts = {}
        if not isinstance(parameters['facts'], list):
            raise ValueError('Explicit fact list required; missing facts remain unknown.')
        for fact in parameters['facts']:
            _fields(fact, {'attribute_id', 'value', 'unit', 'boundary_id', 'period', 'evidence_ids', 'evidence_fit',
                           'rationale', 'uncertainty', 'coverage_complete'}, ('attribute_id', 'unit', 'rationale', 'uncertainty'))
            ident = fact['attribute_id']
            if ident in facts or ident not in definitions or fact['evidence_fit'] not in FIT or not isinstance(fact['coverage_complete'], bool):
                raise ValueError('Distinct defined facts with explicit fitness and coverage required.')
            definition = definitions[ident]
            if fact['unit'] != definition['unit'] or fact['boundary_id'] != review['boundary_id']:
                raise ValueError('Fact unit and legal-entity/company boundary must match the selected definition/review.')
            if set(fact['period']) != {'start', 'end'} or _date(fact['period']['start']) > _date(fact['period']['end']):
                raise ValueError('Valid explicit fact coverage period required.')
            value = fact['value']
            if value is not None:
                if definition['type'] == 'number':
                    _fields(value, {'lower', 'upper'})
                    for bound in value.values():
                        if bound is not None: _number(bound)
                    if value['lower'] is not None and value['upper'] is not None and _number(value['lower']) > _number(value['upper']):
                        raise ValueError('Numeric source range is reversed.')
                else: _typed(value, definition['type'])
            sources = _sources(state, fact['evidence_ids'], refs)
            support = (bool(sources) and fact['evidence_fit'] == 'reviewed_supporting' and fact['coverage_complete']
                       and fact['period']['start'] <= review['period']['start'] and fact['period']['end'] >= review['period']['end'])
            support = support and all(e['boundary_id'] == fact['boundary_id'] and e['unit'] == fact['unit']
                and e['source']['version'] is not None and e['source']['accessed'] <= review['as_of_date']
                and e['period']['start'] <= fact['period']['start'] and e['period']['end'] >= fact['period']['end'] for e in sources)
            facts[ident] = {'record': copy.deepcopy(fact), 'supported': support, 'source_snapshots': sources}
            if not support or value is None: gap(ident + ': missing, incomplete, period-mismatched or unfit company fact.')
        rule_reviews, rule_review_sources = {}, {}
        if not isinstance(parameters['rule_reviews'], list):
            raise ValueError('Explicit per-rule source-currency review list required.')
        for item in parameters['rule_reviews']:
            _fields(item, {'pack_id', 'rule_id', 'checked_as_of', 'evidence_ids', 'evidence_fit', 'rationale'},
                    ('pack_id', 'rule_id', 'rationale'))
            key = (item['pack_id'], item['rule_id'])
            if key in rule_reviews or item['evidence_fit'] not in FIT:
                raise ValueError('Distinct explicit rule source-fitness reviews required.')
            _date(item['checked_as_of'])
            if _date(item['checked_as_of']) > as_of:
                raise ValueError('Rule source review cannot postdate the screening review.')
            rule_review_sources[key] = _sources(state, item['evidence_ids'], refs)
            rule_reviews[key] = item
        rows, used, seen_reviews = [], set(), set()
        for pack, pin in zip(packs, pins):
            for rule in pack['rules']:
                key = (pack['id'], rule['id'])
                if key in rule_reviews: seen_reviews.add(key)
                source_review = rule_reviews.get(key)
                if _date(rule['source']['retrieved']) > as_of:
                    raise ValueError('Screening cannot predate pinned primary-source retrieval.')
                supported = (review_fit and source_review is not None and bool(source_review['evidence_ids'])
                             and source_review['evidence_fit'] == 'reviewed_supporting'
                             and source_review['checked_as_of'] == review['as_of_date'] and rule['source']['version'] is not None)
                source_records = rule_review_sources.get(key, [])
                supported = supported and all(e['source']['accessed'] <= review['as_of_date'] for e in source_records)
                supported = supported and any(e['source']['locator'] == rule['source']['locator']
                    and e['source']['version'] == rule['source']['version'] for e in source_records)
                if not supported: gap(pack['id'] + '/' + rule['id'] + ': current source, version or organization screening fitness is unverified.')
                if not rule['exceptions_complete']: gap(pack['id'] + '/' + rule['id'] + ': exception coverage is incomplete.')
                traces = []
                location = _evaluate({'attribute': pack['jurisdiction_attribute'], 'operator': 'intersects',
                                      'value': [rule['jurisdiction']]}, facts, definitions, used, traces)
                base = _evaluate(rule['condition'], facts, definitions, used, traces)
                exceptions = [{'id': x['id'], 'description': x['description'],
                               'verdict': _evaluate(x['condition'], facts, definitions, used, traces)} for x in rule['exceptions']]
                excluded = _combine([x['verdict'] for x in exceptions], 'any') if rule['exceptions_complete'] else None
                # A proven exception is still an exclusion when other exceptions are unknown.
                if any(x['verdict'] is True for x in exceptions): excluded = True
                condition = _combine([location, base, None if excluded is None else not excluded], 'all')
                segments = _segments(rule, review['period'], condition, supported)
                statuses = {s['preliminary_status'] for s in segments}
                status = (next(iter(statuses)) if len(statuses) == 1 else 'potentially_applicable'
                          if statuses & {'applicable', 'potentially_applicable'} else 'undetermined')
                if condition is None: gap(pack['id'] + '/' + rule['id'] + ': threshold, jurisdiction or exception conditions are unresolved.')
                if status in {'undetermined', 'potentially_applicable'}: gap(pack['id'] + '/' + rule['id'] + ': date/status/source or partial-period applicability requires legal review.')
                rows.append({'pack_id': pack['id'], 'pack_version': pack['version'], 'pack_sha256': pin['sha256'],
                             'rule': copy.deepcopy(rule), 'source_review': copy.deepcopy(source_review),
                             'primary_source_snapshots': copy.deepcopy(source_records), 'predicate_traces': traces,
                             'exception_verdicts': exceptions, 'combined_condition': condition, 'segments': segments,
                             'preliminary_status': status, 'legal_applicability_determined': False, 'compliance_verified': False,
                             'exemption_authorized': False, 'qualified_legal_review_required': True})
        if set(rule_reviews) != seen_reviews:
            raise ValueError('Rule reviews must reference actual selected pack/rule IDs.')
        for ident in sorted(set(definitions) - set(facts)):
            if ident in used: gap(ident + ': required company fact is absent; no default value inferred.')
        report = {'packs': copy.deepcopy(packs), 'pins': copy.deepcopy(pins), 'facts': copy.deepcopy(facts),
                  'screening_review': copy.deepcopy(review), 'rows': rows, 'unused_fact_ids': sorted(set(facts) - used),
                  'jurisdiction_hierarchy_inferred': False, 'rule_precedence_inferred': False,
                  'legal_applicability_determined': False, 'compliance_verified': False, 'obligation_adopted': False,
                  'publication_authorized': False, 'whole_organization_coverage_verified': False}
        if any(p['synthetic'] for p in packs):
            result['assumptions'] = list(dict.fromkeys(result['assumptions'] + ['Fictional jurisdiction fixture only; no real regulation is implemented by this screen.']))
        gap('Qualified legal review remains required; screening is not a legal determination, exemption or compliance assessment.')
        result['review_requirements'].append({'id': result['id'] + '-legal-review', 'state': 'LEGAL_REVIEW_REQUIRED',
                                             'reason': 'Review current primary sources, selected versions, entity scope, dates, thresholds, exceptions and overlapping jurisdictions.',
                                             'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
        result['diagnostics'].append({'code': 'JURISDICTION_SCREEN', 'message': json.dumps(report, sort_keys=True)})
    except (ValueError, TypeError, KeyError, OSError) as error:
        result['status'] = 'blocked'
        gap(str(error))
        result['diagnostics'].append({'code': 'JURISDICTION_DATA_REQUIRED', 'message': str(error)})
    result['evidence_ids'] = sorted(refs)
    result['diagnostics'].append({'code': 'JURISDICTION_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + [r['state'] for r in result['review_requirements'] if r['status'] == 'open'] + ['EVIDENCE_INCOMPLETE']))
    result['next_actions'] = list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result': result, 'proposal': propose(state, result, 'Record pinned preliminary jurisdiction screens with all legal and historical obligations preserved')}
