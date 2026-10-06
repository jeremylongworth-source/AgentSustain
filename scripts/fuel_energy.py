"""Source-supplied fuel calorific energy; no defaults, emissions or useful-heat inference."""
import copy
from decimal import localcontext
import hashlib
import json

from .climate_tools import _date, _fields, _sources
from .contract_validation import validate_state
from .data_tools import convert, number, serialize
from .manager_workflow import _empty
from .state_proposal import propose

CONTRACT = 'fuel-energy-0.1.0'
SOURCE = 'https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf'
CV_UNITS = {'MJ/kg': ('kg', 'MJ'), 'GJ/t': ('t', 'GJ'),
            'MJ/m3': ('m3', 'MJ'), 'MJ/L': ('L', 'MJ')}


def _basis(item):
    _fields(item, {'fuel_id', 'fuel_definition', 'material_basis', 'reference_conditions'},
            ('fuel_id', 'fuel_definition', 'material_basis'))
    if item['material_basis'] not in {'as_received', 'dry', 'declared_composition'}:
        raise ValueError('Explicit received/dry/composition material basis required.')
    conditions = item['reference_conditions']
    if conditions is not None:
        _fields(conditions, {'temperature_K', 'pressure_kPa', 'compressibility', 'definition'}, ('definition',))
        if any(number(conditions[k]) <= 0 for k in ('temperature_K', 'pressure_kPa', 'compressibility')):
            raise ValueError('Positive finite absolute temperature, pressure and compressibility required.')


def run_fuel_energy(state, p):
    validate_state(state)
    _fields(p, {'quantity_id', 'calorific_value_id', 'quantity_basis', 'calorific_value_basis',
                'heating_basis', 'conversion_review', 'fixture_mode', 'result_id'}, ('quantity_id', 'result_id'))
    if type(p['fixture_mode']) is not bool or any(r['id']==p['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and fresh result identity required.')
    result = _empty(state, 'build-energy-baseline', p['result_id']); result['status'] = 'partial'
    refs = set(); selected = []; report = {'execution_contract': CONTRACT, 'heating_basis': p['heating_basis'],
        'source_metric_views': [], 'energy_kWh': None, 'basis_conversion_performed': False,
        'source_authenticated': False, 'useful_heat_or_efficiency_determined': False,
        'emissions_determined': False, 'engineering_approved': False, 'external_action_authorized': False}
    def resolve(ident, calorific=False):
        pair = next(((r,m) for r in state['results'] for m in r['metrics'] if m['id']==ident), None)
        if pair is None:
            raise ValueError('CALORIFIC_VALUE_REQUIRED' if calorific else 'Resolved supplied fuel quantity required.')
        owner, m = pair
        for diagnostic in owner['diagnostics']:
            if diagnostic['code'] == 'BUSINESS_INGESTION_INPUTS':
                ingestion = json.loads(diagnostic['message'])
                if not p['fixture_mode'] and (ingestion['fixture_mode'] or ingestion['file_pin']['synthetic']):
                    raise ValueError('Fictional CSV ancestry cannot enter ordinary fuel-energy mode.')
        if (owner['status'] not in {'completed','partial'} or m['value'] is None
            or m['boundary_id'] != state['organizational_boundary']['id'] or m['period'] != state['reporting_period']
            or m['assumption'] is not None or not m['evidence_ids']
            or not set(m['calculation']['inputs']) <= set(m['evidence_ids'])):
            raise ValueError('Current matched source-leaf metric and complete evidence lineage required.')
        value = number(m['value'])
        if value < 0 or calorific and value == 0:
            raise ValueError('Nonnegative fuel quantity and positive supplied calorific value required.')
        sources = _sources(state, m['evidence_ids'], refs)
        selected.append((owner,m,sources))
        return m
    try:
        _basis(p['quantity_basis']); _basis(p['calorific_value_basis'])
        if p['quantity_basis'] != p['calorific_value_basis'] or p['heating_basis'] not in {'LHV','HHV'}:
            raise ValueError('Exact same fuel/material/reference conditions and explicit LHV/HHV required; no inferred transformation.')
        review = p['conversion_review']
        _fields(review, {'quantity_id', 'calorific_value_id', 'boundary_id', 'period', 'as_of_date',
                         'heating_basis', 'evidence_ids', 'evidence_fit', 'representativeness', 'rationale', 'reviewer_role'},
                ('representativeness', 'rationale', 'reviewer_role'))
        if (review['quantity_id'] != p['quantity_id'] or review['calorific_value_id'] != p['calorific_value_id']
            or review['boundary_id'] != state['organizational_boundary']['id'] or review['period'] != state['reporting_period']
            or review['heating_basis'] != p['heating_basis'] or review['evidence_fit'] != 'reviewed_supporting'):
            raise ValueError('Matched source identities/boundary/period/heating basis and supporting conversion review required.')
        when = _date(review['as_of_date'])
        if when < _date(state['reporting_period']['end']):
            raise ValueError('Complete reporting-period fuel conversion required; no future observed total inferred.')
        review_sources = _sources(state,review['evidence_ids'],refs)
        if not review_sources:
            raise ValueError('Source-backed calorific applicability review required.')
        quantity = resolve(p['quantity_id']); cv = resolve(p['calorific_value_id'], True)
        if cv['unit'] not in CV_UNITS:
            raise ValueError('Explicit supported calorific units required; no density, dry-mass or gross/net conversion inferred.')
        denominator, energy_unit = CV_UNITS[cv['unit']]
        volume = denominator in {'m3','L'}
        if volume != (p['quantity_basis']['reference_conditions'] is not None):
            raise ValueError('Volume requires matched reference conditions; mass uses explicit material basis with no volume conditions.')
        sources = [e for _,_,es in selected for e in es] + review_sources
        if any(e['boundary_id'] != review['boundary_id'] or e['source']['version'] is None
               or _date(e['source']['accessed']) > when for e in sources):
            raise ValueError('Versioned nonfuture matched-boundary evidence required.')
        if any(e['period']['start'] > state['reporting_period']['start'] or e['period']['end'] < state['reporting_period']['end']
               or e['unit'] != m['unit'] for _,m,es in selected for e in es):
            raise ValueError('Selected source units and full applicability period must support each input metric.')
        if any(e['source']['tier']==5 or e['assumption'] is not None for e in sources):
            raise ValueError('This observed-source contract requires supplied representative observations, not projected fuel models.')
        if not p['fixture_mode'] and any(e['source']['locator'].startswith('fixture:') for e in sources):
            raise ValueError('Fictional fuel/calorific sources require explicit fixture mode.')
        for owner,m,es in selected:
            report['source_metric_views'].append({'result_id':owner['id'], 'metric':copy.deepcopy(m),
                'evidence_snapshots':es, 'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest()})
        with localcontext() as context:
            context.prec = 34
            amount = convert(quantity['value'],quantity['unit'],denominator)['value']
            energy = convert(amount*number(cv['value']),energy_unit,'kWh')['value']
        result['metrics'].append({'id':p['result_id']+'-energy','name':'Supplied fuel calorific energy ('+p['heating_basis']+')',
            'value':serialize(energy),'unit':'kWh','period':copy.deepcopy(state['reporting_period']),
            'boundary_id':review['boundary_id'],'evidence_ids':sorted(refs),
            'method':{'name':'Supplied compatible fuel quantity times calorific value','version':CONTRACT,'source':SOURCE},
            'assumption':None,'uncertainty':{'kind':'unquantified','description':'Input and representativeness uncertainty remains; no useful heat, efficiency or source authenticity established.','value':None,'unit':None},
            'calculation':{'formula':'Compatible fuel quantity * supplied calorific value, converted to kWh',
                'inputs':[quantity['id'],cv['id']], 'conversions':[quantity['unit']+' to '+denominator,energy_unit+' to kWh; LHV/HHV and material/reference basis retained'],
                'rounding':'34-digit Decimal arithmetic; JSON serialization'}})
        report.update(quantity_basis=copy.deepcopy(p['quantity_basis']),calorific_value_basis=copy.deepcopy(p['calorific_value_basis']),
                      conversion_review=copy.deepcopy(review),review_source_snapshots=review_sources,energy_kWh=serialize(energy))
    except (ValueError, TypeError, KeyError) as error:
        result['status']='blocked'; result['metrics']=[]
        code = 'CALORIFIC_VALUE_REQUIRED' if str(error)=='CALORIFIC_VALUE_REQUIRED' else 'FUEL_ENERGY_DATA_REQUIRED'
        result['diagnostics'].append({'code':code,'message':str(error)})
        result['data_gaps'].append({'id':p['result_id']+'-source-gap','field':'fuel_energy','reason':str(error),
            'impact':'No defensible fuel-energy conversion is produced.','remedy':'Supply compatible source-backed fuel and calorific observations with qualified applicability review; no default is inferred.'})
    result['evidence_ids']=sorted(refs)
    result['review_requirements'].append({'id':p['result_id']+'-engineering-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
        'reason':'Review fuel identity, full-period calorific representativeness, moisture/reference and heating basis before engineering use or downstream aggregation.',
        'scope':'Selected fuel-energy conversion only','reviewer_role':'Qualified energy professional and accountable owner','status':'open','resolution':None})
    result['review_states']=list(dict.fromkeys(result['review_states']+['PROFESSIONAL_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['diagnostics'].extend([{'code':'FUEL_ENERGY_CONVERSION','message':json.dumps(report,sort_keys=True)},
                                 {'code':'FUEL_ENERGY_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Review source fitness, calorific basis and nonoverlapping energy coverage; emissions require separate defensible emission factors.']
    proposal=propose(state,result,'Record source-supplied calorific fuel energy without emissions or engineering approval')
    if result['metrics']:
        proposal['state']['energy'].append(result['id']);validate_state(proposal['state'])
    return {'result':result,'proposal':proposal}
