"""Reproduce one species-mass result and apply a supplied, source-reviewed GWP."""
import copy
from decimal import DecimalException, Underflow, localcontext
import json

from .climate_tools import _date, _fields, _sources
from .contract_validation import validate_state
from .data_tools import number, serialize
from .gas_mass import calculate_gas_mass
from .state_proposal import propose


class ConversionRequired(ValueError):
    pass


class ConversionArithmeticRequired(ValueError):
    pass


def _diagnostic(result, code):
    messages = [d['message'] for d in result['diagnostics'] if d['code'] == code]
    if len(messages) != 1:
        raise ValueError('Exactly one complete current gas diagnostic required.')
    return json.loads(messages[0])


def convert_gas_mass(state, parameters):
    validate_state(state)
    _fields(parameters, {'gas_result_id', 'gas_metric_id', 'gwp', 'conversion_review', 'fixture_mode', 'result_id'},
            ('gas_result_id', 'gas_metric_id', 'result_id'))
    if type(parameters['fixture_mode']) is not bool or any(r['id'] == parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused conversion result ID required.')
    result = {'id': parameters['result_id'], 'skill': 'convert-gas-mass-to-co2e', 'contract_version': '0.1.0',
        'status': 'partial', 'review_states': ['ANALYTICAL'], 'review_requirements': copy.deepcopy(state['review_requirements']),
        'metrics': [], 'evidence_ids': [], 'assumptions': list(state['assumptions']),
        'data_gaps': copy.deepcopy(state['data_gaps']), 'diagnostics': [], 'next_actions': []}
    refs = set()
    def gap(message, code):
        result['data_gaps'].append({'id': result['id'] + '-gap-' + str(len(result['data_gaps'])),
            'field': 'gas_co2e_conversion', 'reason': message, 'impact': 'Species conversion or its method fitness remains unavailable.',
            'remedy': 'Supply exact species/basis/horizon conversion evidence and obtain qualified source/method review.'})
        result['diagnostics'].append({'code': code, 'message': message})
    try:
        owner = next((r for r in state['results'] if r['id'] == parameters['gas_result_id']), None)
        if owner is None or owner['skill'] != 'calculate-gas-mass' or owner['status'] != 'partial':
            raise ValueError('Current supported gas-mass result required, not arbitrary mass or company CO2e.')
        inputs = _diagnostic(owner, 'GAS_MASS_INPUTS')
        if inputs['fixture_mode'] and not parameters['fixture_mode']:
            raise ConversionRequired('Fictional upstream gas mass cannot be promoted to real conversion.')
        check = copy.deepcopy(inputs)
        check['result_id'] = parameters['result_id'] + '-gas-reproduction'
        while any(r['id'] == check['result_id'] for r in state['results']):
            check['result_id'] += '-next'
        reproduced = calculate_gas_mass(state, check)['result']
        metrics = copy.deepcopy(reproduced['metrics'])
        for m in metrics:
            m['id'] = m['id'].replace(check['result_id'], owner['id'], 1)
        gas_report = _diagnostic(owner, 'GAS_MASS_CALCULATION')
        if (reproduced['status'] != owner['status'] or metrics != owner['metrics']
                or set(reproduced['evidence_ids']) != set(owner['evidence_ids'])
                or _diagnostic(reproduced, 'GAS_MASS_CALCULATION') != gas_report):
            raise ValueError('Complete gas mass, method, metric metadata and source/evidence lineage must reproduce.')
        metric = next((m for m in owner['metrics'] if m['id'] == parameters['gas_metric_id']), None)
        gas = gas_report['gas']
        if metric is None or metric['unit'] != 'kg ' + gas or metric['value'] is None or number(metric['value']) < 0:
            raise ValueError('Selected reproduced kilogram species metric required; no gas-family or unit relabeling.')
        refs.update(owner['evidence_ids'])
        review = parameters['conversion_review']
        _fields(review, {'boundary_id', 'period', 'as_of_date', 'gas', 'basis', 'time_horizon_years', 'scope',
                         'evidence_ids', 'evidence_fit', 'source_review', 'reviewer_role', 'rationale'},
                ('gas', 'basis', 'scope', 'reviewer_role', 'rationale'))
        as_of = _date(review['as_of_date'])
        review_sources = _sources(state, review['evidence_ids'], refs)
        if review['boundary_id'] != state['organizational_boundary']['id'] or review['period'] != state['reporting_period'] or metric['period'] != review['period'] or review['gas'] != gas:
            raise ValueError('Matched species, organization boundary and reporting period required.')
        if gas_report['applicability_review']['as_of_date'] != review['as_of_date']:
            raise ValueError('Refresh gas-source screening for the exact conversion assessment date.')
        try:
            gwp = parameters['gwp']
            if gwp is None:
                raise ValueError('No defensible species-specific GWP supplied; none is inferred from memory.')
            _fields(gwp, {'id', 'gas', 'value', 'unit', 'basis', 'time_horizon_years', 'source', 'status', 'evidence_ids'},
                    ('id', 'gas', 'unit', 'basis', 'status'))
            source = gwp['source']
            _fields(source, {'locator', 'publisher', 'version', 'accessed'}, ('locator', 'publisher', 'version', 'accessed'))
            value = number(gwp['value'])
            if value < 0 or type(gwp['time_horizon_years']) is not int or not 1 <= gwp['time_horizon_years'] <= 1000 or type(review['time_horizon_years']) is not int:
                raise ValueError('Finite nonnegative conversion and explicit integer time horizon required.')
            if gwp['gas'] != gas or gwp['unit'] != 'kg CO2e/kg ' + gas or gwp['basis'] != review['basis'] or gwp['time_horizon_years'] != review['time_horizon_years']:
                raise ValueError('Exact species, mass ratio, selected source basis and time horizon required.')
            if gwp['status'] != 'reviewed' and not (parameters['fixture_mode'] and gwp['status'] == 'synthetic'):
                raise ValueError('GWP must be reviewed; synthetic values require fixture mode.')
            if _date(source['accessed']) > as_of or review['evidence_fit'] != 'reviewed_supporting' or not review_sources:
                raise ValueError('Current supported conversion applicability evidence required.')
            if any(e['boundary_id'] != review['boundary_id'] or e['source']['version'] is None or _date(e['source']['accessed']) > as_of for e in review_sources):
                raise ValueError('Versioned nonfuture applicability evidence must match the boundary.')
            sources = _sources(state, gwp['evidence_ids'], refs)
            sr = review['source_review']
            _fields(sr, {'gwp_id', 'gas_result_id', 'gas_metric_id', 'gas', 'value', 'unit', 'basis', 'time_horizon_years',
                         'source_locator', 'source_version', 'evidence_ids', 'evidence_fit', 'checked_as_of', 'rationale'}, ('rationale',))
            number(sr['value'])
            expected = {'gwp_id': gwp['id'], 'gas_result_id': owner['id'], 'gas_metric_id': metric['id'],
                **{k: gwp[k] for k in ['gas', 'value', 'unit', 'basis', 'time_horizon_years', 'evidence_ids']},
                'source_locator': source['locator'], 'source_version': source['version']}
            if any(sr[k] != v for k, v in expected.items()) or type(sr['time_horizon_years']) is not int or sr['evidence_fit'] != 'reviewed_supporting' or sr['checked_as_of'] != review['as_of_date'] or not sources:
                raise ValueError('Exact current GWP value/unit/species/basis/horizon/source and input-result confirmation required.')
            if any(e['boundary_id'] != review['boundary_id'] or e['unit'] != gwp['unit'] or e['source']['version'] is None or _date(e['source']['accessed']) > as_of for e in sources) or not any(e['source']['locator'] == source['locator'] and e['source']['version'] == source['version'] for e in sources):
                raise ValueError('Selected GWP evidence must match ratio units, boundary and primary source/version.')
            if not parameters['fixture_mode'] and (not source['locator'].startswith('https://') or any(e['source']['locator'].startswith('fixture:') for e in sources + review_sources)):
                raise ValueError('Fictional GWP evidence cannot enter real conversion.')
        except (ValueError, TypeError, KeyError) as error:
            raise ConversionRequired(str(error)) from error
        try:
            with localcontext() as context:
                context.prec = 34
                context.traps[Underflow] = True
                co2e = number(metric['value']) * value
            co2e_value = serialize(co2e)
        except (DecimalException, ValueError) as error:
            raise ConversionArithmeticRequired('Conversion exceeds supported Decimal/JSON representation; no zero or numeric output inferred.') from error
        result['metrics'] = [{'id': result['id'] + '-metric', 'name': gas + ' source-basis CO2e',
            'value': co2e_value, 'unit': 'kg CO2e', 'period': copy.deepcopy(metric['period']),
            'boundary_id': metric['boundary_id'], 'evidence_ids': sorted(refs),
            'method': {'name': 'Reproduced species mass times explicitly sourced GWP', 'version': 'gas-co2e-0.1.0', 'source': source['locator']},
            'assumption': metric['assumption'], 'uncertainty': {'kind': 'unquantified',
                'description': 'Gas mass and conversion source uncertainty retained; combined uncertainty is not quantified.', 'value': None, 'unit': None},
            'calculation': {'formula': 'reproduced kg species * explicitly supplied kg CO2e/kg species',
                'inputs': list(dict.fromkeys([metric['id']] + sorted(refs))), 'conversions': [],
                'rounding': '34-digit Decimal multiplication of the reproduced JSON metric; final JSON number only'}}]
        report = {'execution_contract': 'gas-co2e-0.1.0', 'gas_result_id': owner['id'], 'gas_metric_snapshot': copy.deepcopy(metric),
            'gas_report_snapshot': gas_report, 'gwp_snapshot': copy.deepcopy(gwp), 'gwp_source_snapshots': sources,
            'conversion_review': copy.deepcopy(review), 'applicability_source_snapshots': review_sources,
            'co2e_kg': co2e_value, 'gwp_applied': True, 'co2e_produced': True,
            'regulatory_method_verified': False, 'whole_facility_coverage_verified': False,
            'source_authenticity_verified': False, 'scope_account_created': False}
        result['diagnostics'].append({'code': 'GAS_CO2E_CONVERSION', 'message': json.dumps(report, sort_keys=True)})
        if parameters['fixture_mode']:
            result['assumptions'] = list(dict.fromkeys(result['assumptions'] + ['Fictional gas/GWP conversion only; the supplied demonstration value is not an actual GWP.']))
        gap('Species/basis/horizon/source applicability and any regulatory coverage remain under qualified review.', 'GWP_METHOD_REVIEW_REQUIRED')
        result['review_requirements'].append({'id': result['id'] + '-gwp-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
            'reason': 'Review exact species, source GWP basis/time horizon, reproduced gas quantity and conversion applicability.',
            'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
    except (ValueError, TypeError, KeyError) as error:
        result['status'] = 'blocked'; result['metrics'] = []
        code = ('EMISSION_FACTOR_REQUIRED' if isinstance(error, ConversionRequired) else
                'GAS_CONVERSION_DATA_REQUIRED' if isinstance(error, ConversionArithmeticRequired) else 'GAS_MASS_REPRODUCTION_REQUIRED')
        gap(str(error), code)
    result['evidence_ids'] = sorted(refs)
    result['diagnostics'].append({'code': 'GAS_CO2E_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + [r['state'] for r in result['review_requirements'] if r['status'] == 'open'] + ['EVIDENCE_INCOMPLETE']))
    result['next_actions'] = list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result': result, 'proposal': propose(state, result, 'Record source-reviewed species conversion separately; no scope account, regulated total or review resolution')}
