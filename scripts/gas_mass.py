"""Explicit species mass from supplied factors; no built-in factors, GWP or law."""
import copy
from decimal import DecimalException, Underflow, localcontext
import json
import re

from .climate_tools import _date, _fields, _sources, _text
from .contract_validation import validate_state
from .data_tools import convert, number, serialize
from .state_proposal import propose


class FactorRequired(ValueError):
    pass


def calculate_gas_mass(state, parameters):
    validate_state(state)
    _fields(parameters, {'activity_id', 'gas', 'factor', 'applicability_review', 'fixture_mode', 'result_id'},
            ('activity_id', 'gas', 'result_id'))
    if type(parameters['fixture_mode']) is not bool or any(r['id'] == parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused result ID required.')
    result = {'id': parameters['result_id'], 'skill': 'calculate-gas-mass', 'contract_version': '0.1.0',
        'status': 'partial', 'review_states': ['ANALYTICAL'], 'review_requirements': copy.deepcopy(state['review_requirements']),
        'metrics': [], 'evidence_ids': [], 'assumptions': list(state['assumptions']),
        'data_gaps': copy.deepcopy(state['data_gaps']), 'diagnostics': [], 'next_actions': []}
    refs = set()
    def gap(message, code):
        result['data_gaps'].append({'id': result['id'] + '-gap-' + str(len(result['data_gaps'])),
            'field': 'gas_mass', 'reason': message, 'impact': 'Species-mass calculation or method fitness remains unavailable.',
            'remedy': 'Supply matched quantity/species/factor evidence and obtain qualified method/source review.'})
        result['diagnostics'].append({'code': code, 'message': message})
    try:
        gas = parameters['gas']
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', gas) or gas.casefold() in {'hfc', 'hfcs', 'pfc', 'pfcs', 'ghg', 'ghgs', 'co2e'}:
            raise ValueError('Explicit individual species identifier required; no family or CO2e mass substitution.')
        owner, activity = next(((r, m) for r in state['results'] for m in r['metrics'] if m['id'] == parameters['activity_id']), (None, None))
        if owner is None or owner['status'] in {'blocked', 'invalid_input'} or activity['value'] is None or number(activity['value']) < 0:
            raise ValueError('Current nonnegative known activity from a supported result required.')
        review = parameters['applicability_review']
        _fields(review, {'boundary_id', 'period', 'as_of_date', 'geography', 'acceptable_vintages', 'activity_kind',
                         'activity_review', 'factor_review', 'scope', 'reviewer_role', 'rationale'},
                ('geography', 'activity_kind', 'scope', 'reviewer_role', 'rationale'))
        as_of = _date(review['as_of_date'])
        if review['boundary_id'] != state['organizational_boundary']['id'] or review['period'] != state['reporting_period'] or activity['period'] != review['period'] or _date(review['period']['end']) > as_of:
            raise ValueError('Matched boundary/reporting period and nonfuture activity required; no annualization.')
        ar = review['activity_review']
        _fields(ar, {'metric_id', 'gas', 'activity_kind', 'value', 'unit', 'period', 'boundary_id', 'evidence_ids', 'evidence_fit', 'rationale'}, ('rationale',))
        expected_activity = {'metric_id': activity['id'], 'gas': gas, 'activity_kind': review['activity_kind'],
            **{k: activity[k] for k in ['value', 'unit', 'period', 'boundary_id', 'evidence_ids']}}
        number(ar['value'])
        activity_sources = _sources(state, ar['evidence_ids'], refs)
        if any(ar[k] != v for k, v in expected_activity.items()) or ar['evidence_fit'] != 'reviewed_supporting' or not activity_sources:
            raise ValueError('Activity quantity, kind, species context and complete lineage must match the supporting source review.')
        if any(e['boundary_id'] != review['boundary_id'] or e['unit'] != activity['unit'] or e['source']['version'] is None
               or _date(e['source']['accessed']) > as_of or _date(e['period']['start']) > _date(activity['period']['start'])
               or _date(e['period']['end']) < _date(activity['period']['end']) for e in activity_sources):
            raise ValueError('Activity sources must match unit/boundary, cover the period and have nonfuture versioned access.')
        factor = parameters['factor']
        try:
            if factor is None:
                raise ValueError('No defensible species-mass factor supplied.')
            _fields(factor, {'id', 'gas', 'activity_kind', 'value', 'unit', 'source', 'method', 'geography',
                             'vintage_year', 'valid_period', 'status', 'evidence_ids'},
                    ('id', 'gas', 'activity_kind', 'unit', 'geography', 'status'))
            source = factor['source']; method = factor['method']
            _fields(source, {'locator', 'publisher', 'version', 'accessed'}, ('locator', 'publisher', 'version', 'accessed'))
            _fields(method, {'name', 'version', 'source'}, ('name', 'version', 'source'))
            vintages = review['acceptable_vintages']
            if not isinstance(vintages, list) or not vintages or any(type(y) is not int for y in vintages) or type(factor['vintage_year']) is not int:
                raise ValueError('Explicit integer vintage policy required.')
            if factor['vintage_year'] not in vintages or factor['geography'] != review['geography'] or factor['gas'] != gas or factor['activity_kind'] != review['activity_kind']:
                raise ValueError('Factor species, activity kind, geographic basis and vintage must match the selected review.')
            if factor['status'] != 'reviewed' and not (parameters['fixture_mode'] and factor['status'] == 'synthetic'):
                raise ValueError('Factor must be reviewed; synthetic factors require fixture mode.')
            _fields(factor['valid_period'], {'start', 'end'})
            if _date(factor['valid_period']['start']) > _date(activity['period']['start']) or _date(factor['valid_period']['end']) < _date(activity['period']['end']) or _date(source['accessed']) > as_of:
                raise ValueError('Factor validity/source access must support the exact activity period and review date.')
            value = number(factor['value'])
            if value < 0:
                raise ValueError('Negative factor is not gross emitted species mass.')
            parts = factor['unit'].split('/')
            if len(parts) != 2 or not re.fullmatch(r'(g|kg|t) ' + re.escape(gas), parts[0]):
                raise ValueError('Factor numerator must express g/kg/t of the exact species, never CO2e.')
            mass_unit = parts[0].split(' ')[0]
            activity_conversion = convert(activity['value'], activity['unit'], parts[1])
            factor_sources = _sources(state, factor['evidence_ids'], refs)
            fr = review['factor_review']
            _fields(fr, {'factor_id', 'activity_id', 'gas', 'activity_kind', 'source_locator', 'source_version', 'confirmed_value',
                         'confirmed_unit', 'evidence_ids', 'evidence_fit', 'checked_as_of', 'rationale'}, ('rationale',))
            expected_factor = {'factor_id': factor['id'], 'activity_id': activity['id'], 'gas': gas, 'activity_kind': review['activity_kind'],
                'source_locator': source['locator'], 'source_version': source['version'], 'confirmed_value': factor['value'],
                'confirmed_unit': factor['unit'], 'evidence_ids': factor['evidence_ids']}
            number(fr['confirmed_value'])
            if any(fr[k] != v for k, v in expected_factor.items()) or fr['evidence_fit'] != 'reviewed_supporting' or fr['checked_as_of'] != review['as_of_date'] or not factor_sources:
                raise ValueError('Exact current source/species/value/unit and evidence review required for factor use.')
            if any(e['boundary_id'] != review['boundary_id'] or e['unit'] != factor['unit'] or e['source']['version'] is None or _date(e['source']['accessed']) > as_of for e in factor_sources) or not any(e['source']['locator'] == source['locator'] and e['source']['version'] == source['version'] for e in factor_sources):
                raise ValueError('Selected factor evidence must match source version, compound units, boundary and nonfuture access.')
            if not parameters['fixture_mode'] and (not source['locator'].startswith('https://') or not method['source'].startswith('https://') or any(e['source']['locator'].startswith('fixture:') for e in activity_sources + factor_sources)):
                raise ValueError('Fictional source evidence cannot be promoted to real gas-mass use.')
        except (ValueError, TypeError, KeyError) as error:
            raise FactorRequired(str(error)) from error
        with localcontext() as context:
            context.prec = 34
            context.traps[Underflow] = True
            raw_mass = activity_conversion['value'] * value
            output = convert(raw_mass, mass_unit, 'kg')
        result['metrics'] = [{'id': result['id'] + '-metric', 'name': 'Calculated ' + gas + ' mass',
            'value': serialize(output['value']), 'unit': 'kg ' + gas, 'period': copy.deepcopy(activity['period']),
            'boundary_id': activity['boundary_id'], 'evidence_ids': sorted(refs), 'method': copy.deepcopy(method),
            'assumption': activity['assumption'], 'uncertainty': {'kind': 'unquantified',
                'description': 'Input/source uncertainty retained; combined numerical uncertainty is not quantified.', 'value': None, 'unit': None},
            'calculation': {'formula': 'activity * explicit unit conversion * supplied species factor * mass conversion',
                'inputs': list(dict.fromkeys([activity['id']] + sorted(refs))),
                'conversions': [f"{activity['unit']} -> {parts[1]}: {activity_conversion['factor']}; {activity_conversion['source']}",
                                f"{mass_unit} -> kg: {output['factor']}; {output['source']}"], 'rounding': '34-digit Decimal arithmetic; final JSON number only'}}]
        report = {'execution_contract': 'gas-mass-0.1.0', 'activity_snapshot': copy.deepcopy(activity),
            'activity_source_snapshots': activity_sources, 'factor_snapshot': copy.deepcopy(factor), 'factor_source_snapshots': factor_sources,
            'applicability_review': copy.deepcopy(review), 'gas': gas, 'raw_mass_unit': mass_unit,
            'raw_mass': serialize(raw_mass), 'output_mass_kg': serialize(output['value']),
            'gwp_applied': False, 'co2e_produced': False, 'regulatory_method_verified': False,
            'whole_facility_coverage_verified': False, 'source_authenticity_verified': False}
        result['diagnostics'].append({'code': 'GAS_MASS_CALCULATION', 'message': json.dumps(report, sort_keys=True)})
        if parameters['fixture_mode']:
            result['assumptions'] = list(dict.fromkeys(result['assumptions'] + ['Fictional species factor/quantity demonstration only; no actual factor or GWP supplied.']))
        gap('Source, method, gas/fuel context and any statutory coverage remain subject to qualified review.', 'GAS_METHOD_REVIEW_REQUIRED')
        result['review_requirements'].append({'id': result['id'] + '-method-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
            'reason': 'Review species/fuel identity, source factor, quantity method, coverage, units and uncertainty.',
            'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
    except (ValueError, TypeError, KeyError, DecimalException) as error:
        result['status'] = 'blocked'
        result['metrics'] = []
        gap(str(error), 'EMISSION_FACTOR_REQUIRED' if isinstance(error, FactorRequired) else 'GAS_ACTIVITY_DATA_REQUIRED')
    result['evidence_ids'] = sorted(refs)
    result['diagnostics'].append({'code': 'GAS_MASS_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + [r['state'] for r in result['review_requirements'] if r['status'] == 'open'] + ['EVIDENCE_INCOMPLETE']))
    result['next_actions'] = list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result': result, 'proposal': propose(state, result, 'Record sourced species mass separately; no GWP, CO2e, regulatory coverage or review resolution')}
