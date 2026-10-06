"""Conditional source-backed equipment heat/input ratios; no certified efficiency."""
import copy
from decimal import Decimal, DecimalException, localcontext
import hashlib
import json
from .climate_tools import _date, _fields, _sources
from .contract_validation import validate_state
from .data_tools import convert, number, serialize
from .fuel_energy import run_fuel_energy
from .jurisdiction_tasks import _diagnostic
from .manager_workflow import _empty
from .state_proposal import propose

CONTRACT = 'thermal-performance-0.1.0'
SOURCE = 'https://www.energy.gov/cmei/femp/incorporate-minimum-efficiency-requirements-heating-and-cooling-products-federal'


def assess_thermal_performance(state, p):
    validate_state(state)
    _fields(p, {'quantities', 'performance_review', 'fixture_mode', 'result_id'}, ('result_id',))
    ids = {r['id'] for r in state['results']}
    if (type(p['fixture_mode']) is not bool or p['result_id'] in ids
        or any(m['id'] in {p['result_id']+'-'+suffix for suffix in ('input', 'output', 'ratio')} for r in state['results'] for m in r['metrics'])):
        raise ValueError('Explicit fixture mode and fresh performance result required.')
    result = _empty(state, 'analyze-energy-usage', p['result_id'])
    result['status'] = 'partial'
    refs = set()
    report = {'execution_contract': CONTRACT, 'review': copy.deepcopy(p['performance_review']),
              'quantities': [], 'supported_input_kWh': None, 'supported_output_kWh': None,
              'ratio': None, 'ratio_definition': None, 'declared_selection_supported': False,
              'actual_coverage_verified': False, 'source_authenticated': False,
              'certified_efficiency_or_rating': False, 'energy_conservation_verified': False,
              'savings_or_emissions_determined': False, 'engineering_approved': False,
              'external_action_authorized': False}

    def gap(code, message):
        result['diagnostics'].append({'code': code, 'message': message})
        result['data_gaps'].append({'id': p['result_id']+'-gap-'+str(len(result['data_gaps'])),
            'field': 'thermal_performance', 'reason': message,
            'impact': 'The affected performance interpretation remains unsupported.',
            'remedy': 'Reconcile current meter, equipment, operating, coverage and heating-basis evidence with qualified engineering review.'})

    try:
        review = p['performance_review']
        _fields(review, {'boundary_id', 'facility_id', 'equipment_id', 'period', 'as_of_date', 'mode',
                         'measurement_boundary', 'output_definition', 'auxiliary_scope', 'operating_conditions',
                         'input_coverage_complete', 'output_coverage_complete', 'same_operating_period',
                         'fuel_heating_basis', 'nonoverlap_assessment', 'evidence_ids', 'evidence_fit',
                         'rationale', 'reviewer_role'},
                ('equipment_id', 'measurement_boundary', 'output_definition', 'auxiliary_scope',
                 'operating_conditions', 'nonoverlap_assessment', 'rationale', 'reviewer_role'))
        if (review['boundary_id'] != state['organizational_boundary']['id']
            or review['facility_id'] not in state['organizational_boundary']['facility_ids']
            or review['period'] != state['reporting_period']
            or review['mode'] not in {'thermal_conversion', 'period_heating_cop'}
            or review['evidence_fit'] != 'reviewed_supporting'
            or review['fuel_heating_basis'] not in {None, 'LHV', 'HHV'}
            or any(type(review[k]) is not bool for k in ('input_coverage_complete', 'output_coverage_complete', 'same_operating_period'))):
            raise ValueError('Matched equipment/facility/boundary/period, explicit mode/basis and supporting review required.')
        when = _date(review['as_of_date'])
        if when < _date(state['reporting_period']['end']):
            raise ValueError('Full observed reporting period must end before the review date.')

        def sources_fit(sources):
            if not sources or any(e['boundary_id'] != review['boundary_id'] or e['source']['version'] is None
                    or _date(e['source']['accessed']) > when
                    or e['period']['start'] > review['period']['start'] or e['period']['end'] < review['period']['end']
                    or e['source']['tier'] == 5 or e['assumption'] is not None
                    or (not p['fixture_mode'] and e['source']['locator'].startswith('fixture:')) for e in sources):
                raise ValueError('Versioned current full-period observed sources and explicit synthetic isolation required.')

        review_sources = _sources(state, review['evidence_ids'], refs)
        sources_fit(review_sources)
        report['review_source_snapshots'] = review_sources
        rows = p['quantities']
        if not isinstance(rows, list) or not rows or len(rows) > 100:
            raise ValueError('Explicit bounded nonempty equipment energy selection required.')
        seen = set(); fragments = set(); totals = {'input': Decimal(0), 'output': Decimal(0)}
        known = {'input': 0, 'output': 0}; requested = {'input': 0, 'output': 0}; fuel_count = 0
        with localcontext() as context:
            context.prec = 34
            for row in rows:
                _fields(row, {'metric_id', 'kind', 'source_fragment', 'evidence_fit', 'fuel_result_id'}, ('metric_id', 'source_fragment'))
                if row['kind'] not in {'electrical_input', 'fuel_input', 'thermal_output'} or row['metric_id'] in seen:
                    raise ValueError('Distinct supported electrical/fuel-input or thermal-output metric roles required.')
                seen.add(row['metric_id'])
                side = 'output' if row['kind'] == 'thermal_output' else 'input'
                requested[side] += 1
                fuel_count += row['kind'] == 'fuel_input'
                if review['mode'] == 'period_heating_cop' and row['kind'] == 'fuel_input':
                    raise ValueError('Electrical heating COP cannot mix fuel or absorption equipment inputs.')
                if row['kind'] != 'fuel_input' and row['fuel_result_id'] is not None:
                    raise ValueError('Fuel replay is only available for a fuel input.')
                pair = next(((r, m) for r in state['results'] for m in r['metrics'] if m['id'] == row['metric_id']), None)
                view = {'selection': copy.deepcopy(row), 'supported': False, 'energy_kWh': None, 'source_view': None}
                report['quantities'].append(view)
                if pair is None:
                    gap('THERMAL_SOURCE_REQUIRED', 'Missing or unfit selected metric '+row['metric_id']); continue
                owner, metric = pair
                sources = _sources(state, metric['evidence_ids'], refs)
                view['source_view'] = {'result_id': owner['id'], 'metric': copy.deepcopy(metric),
                    'evidence_snapshots': sources,
                    'sha256_result_utf8_json_sorted_keys': hashlib.sha256(json.dumps(owner, sort_keys=True).encode()).hexdigest()}
                for evidence in sources:
                    key = (evidence['id'], row['source_fragment'])
                    if key in fragments: raise ValueError('A source fragment cannot supply more than one selected quantity.')
                    fragments.add(key)
                if row['evidence_fit'] != 'reviewed_supporting':
                    gap('THERMAL_SOURCE_REQUIRED', 'Unfit selected metric '+row['metric_id']); continue
                if owner['status'] not in {'partial', 'completed'} or metric['boundary_id'] != review['boundary_id'] or metric['period'] != review['period']:
                    raise ValueError('Current nonblocked same-period/boundary energy metrics required.')
                for diagnostic in owner['diagnostics']:
                    if diagnostic['code'] == 'BUSINESS_INGESTION_INPUTS':
                        ancestry = json.loads(diagnostic['message'])
                        if not p['fixture_mode'] and (ancestry['fixture_mode'] or ancestry['file_pin']['synthetic']):
                            raise ValueError('Synthetic raw-source ancestry cannot enter ordinary performance mode.')
                if row['fuel_result_id'] is not None:
                    if row['fuel_result_id'] != owner['id'] or len(owner['metrics']) != 1:
                        raise ValueError('The fuel input must select its complete original conversion.')
                    original = _diagnostic(owner, 'FUEL_ENERGY_INPUTS')
                    if original['fixture_mode'] and not p['fixture_mode']:
                        raise ValueError('Synthetic fuel ancestry cannot enter ordinary performance mode.')
                    replay = copy.deepcopy(original)
                    replay['result_id'] = p['result_id']+'-fuel-check'
                    while replay['result_id'] in ids or any(m['id'] == replay['result_id']+'-energy' for r in state['results'] for m in r['metrics']):
                        replay['result_id'] += '-next'
                    checked = run_fuel_energy(state, replay)['result']
                    checked_metric = copy.deepcopy(checked['metrics'][0]) if checked['metrics'] else None
                    if checked_metric is not None: checked_metric['id'] = metric['id']
                    if (checked['status'] != 'partial' or checked_metric != metric
                        or _diagnostic(checked, 'FUEL_ENERGY_CONVERSION') != _diagnostic(owner, 'FUEL_ENERGY_CONVERSION')
                        or set(checked['evidence_ids']) != set(owner['evidence_ids'])
                        or original['heating_basis'] != review['fuel_heating_basis']
                        or original['conversion_review']['as_of_date'] != review['as_of_date']):
                        raise ValueError('Full current fuel arithmetic/source/basis/review reproduction required.')
                    view['fuel_conversion_reproduced'] = True
                else:
                    if not set(metric['calculation']['inputs']) <= set(metric['evidence_ids']) or any(e['unit'] != metric['unit'] for e in sources):
                        raise ValueError('Direct observed energy source leaf required; arbitrary derived energy cannot substitute.')
                sources_fit(sources)
                if metric['value'] is None or metric['assumption'] is not None:
                    gap('THERMAL_SOURCE_REQUIRED', 'Unknown or modeled selected energy '+metric['id']); continue
                value = number(metric['value'])
                if value < 0: raise ValueError('Negative equipment energy cannot be used as observed consumption or delivery.')
                energy = convert(value, metric['unit'], 'kWh')['value']
                view.update(supported=True, energy_kWh=serialize(energy))
                totals[side] += energy; known[side] += 1
            if not requested['input'] or not requested['output']:
                raise ValueError('Both declared input and thermal delivery rosters are required.')
            if (fuel_count == 0) != (review['fuel_heating_basis'] is None):
                raise ValueError('A fuel roster needs one retained LHV/HHV basis; electrical-only mode has no fuel basis.')
            complete = (known == requested and review['input_coverage_complete'] and review['output_coverage_complete'] and review['same_operating_period'])
            report['declared_selection_supported'] = complete
            for side in ('input', 'output'):
                if known[side]: report['supported_'+side+'_kWh'] = serialize(totals[side])
            if complete and totals['input'] > 0:
                report['ratio'] = serialize(totals['output']/totals['input'])
                report['ratio_definition'] = 'Selected delivered thermal energy / selected total electrical energy' if review['mode'] == 'period_heating_cop' else 'Selected delivered thermal energy / selected fuel and auxiliary electrical energy'
            else:
                gap('THERMAL_DENOMINATOR_REQUIRED' if complete else 'THERMAL_COVERAGE_REQUIRED',
                    'Zero input leaves the ratio undefined.' if complete else 'Incomplete supported coverage or mismatched operating periods withholds the ratio.')
            for side in ('input', 'output'):
                if known[side]:
                    result['metrics'].append(_metric(state, p['result_id']+'-'+side, 'Supported selected thermal-performance '+side+' energy', totals[side], 'kWh', refs, [q['selection']['metric_id'] for q in report['quantities'] if q['supported'] and ('output' if q['selection']['kind'] == 'thermal_output' else 'input') == side]))
            if report['ratio'] is not None:
                result['metrics'].append(_metric(state, p['result_id']+'-ratio', 'Conditional period heating COP' if review['mode'] == 'period_heating_cop' else 'Conditional delivered thermal/input ratio'+(' ('+review['fuel_heating_basis']+')' if review['fuel_heating_basis'] else ' (electrical input)'), number(report['ratio']), '1', refs, [p['result_id']+'-output', p['result_id']+'-input']))
                if report['ratio'] > 1 and review['mode'] == 'thermal_conversion':
                    gap('THERMAL_ABOVE_UNITY_REVIEW_REQUIRED', 'Ratio above unity retained without clamping; heating convention, storage, unselected heat and meter boundaries require review. No conservation finding is made.')
    except (ValueError, TypeError, KeyError, DecimalException) as error:
        result['status'] = 'blocked'; result['metrics'] = []
        report.update(ratio=None, ratio_definition=None, supported_input_kWh=None, supported_output_kWh=None, declared_selection_supported=False)
        gap('THERMAL_PERFORMANCE_DATA_REQUIRED', str(error))
    result['evidence_ids'] = sorted(refs)
    result['review_requirements'].append({'id': p['result_id']+'-engineering-review', 'state': 'ENGINEERING_REVIEW_REQUIRED',
        'reason': 'Review meter coverage, delivered heat quality, heating basis, auxiliary scope and operating conditions; no certified efficiency, savings or engineering acceptance supplied.',
        'scope': 'Selected equipment thermal performance', 'reviewer_role': 'Qualified energy/engineering professional and accountable owner', 'status': 'open', 'resolution': None})
    result['review_states'] = list(dict.fromkeys(result['review_states']+['ENGINEERING_REVIEW_REQUIRED', 'EVIDENCE_INCOMPLETE']))
    result['diagnostics'].extend([{'code': 'THERMAL_PERFORMANCE', 'message': json.dumps(report, sort_keys=True)},
                                 {'code': 'THERMAL_PERFORMANCE_INPUTS', 'message': json.dumps(p, sort_keys=True)}])
    result['next_actions'] = ['Review measurement and service definitions; do not relabel conditional ratios as AFUE, HSPF, certified efficiency, verified savings or emissions.']
    proposal = propose(state, result, 'Assess declared heat/input performance with source and engineering qualifications')
    if result['metrics']: proposal['state']['energy'].append(result['id']); validate_state(proposal['state'])
    return {'result': result, 'proposal': proposal}


def _metric(state, ident, name, value, unit, refs, inputs):
    return {'id': ident, 'name': name, 'value': serialize(value), 'unit': unit,
        'period': copy.deepcopy(state['reporting_period']), 'boundary_id': state['organizational_boundary']['id'],
        'evidence_ids': sorted(refs), 'method': {'name': 'Supplied equipment energy selection and ratio', 'version': CONTRACT, 'source': SOURCE},
        'assumption': None, 'uncertainty': {'kind': 'unquantified', 'description': 'Original meter/source uncertainty and unverified heat quality, coverage and operating definitions remain; no confidence interval inferred.', 'value': None, 'unit': None},
        'calculation': {'formula': 'Sum supported selected energy, or delivered thermal energy / declared input energy',
                        'inputs': inputs, 'conversions': ['Supported energy units to kWh; fuel LHV/HHV retained without conversion'],
                        'rounding': '34-digit Decimal arithmetic; JSON serialization'}}
