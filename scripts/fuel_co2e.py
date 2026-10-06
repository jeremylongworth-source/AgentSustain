"""Reproduced calorific fuel energy plus explicit emission-factor basis review."""
import copy
import hashlib
import json
from .climate_tools import _date, _fields, _sources
from .contract_validation import validate_state
from .fuel_energy import run_fuel_energy
from .ghg_foundation import calculate_result
from .jurisdiction_tasks import _diagnostic
from .manager_workflow import _empty
from .state_proposal import propose

CONTRACT = 'fuel-co2e-0.1.0'


def run_fuel_co2e(state, p):
    validate_state(state)
    _fields(p, {'fuel_result_id','factor_id','factor_policy','factor_basis_review','fixture_mode','result_id'},
            ('fuel_result_id','result_id'))
    if type(p['fixture_mode']) is not bool or not isinstance(p['factor_policy'],dict):
        raise ValueError('Explicit fixture mode and factor policy required.')
    ids={r['id'] for r in state['results']}
    if p['result_id'] in ids or p['result_id']+'-calculation' in ids:
        raise ValueError('Fresh aggregate and calculation identities required.')
    result=_empty(state,'calculate-co2e',p['result_id']);result['status']='partial';working=state;refs=set();parent=None
    report={'execution_contract':CONTRACT,'fuel_result_id':p['fuel_result_id'],'selected_factor_id':p['factor_id'],
        'fuel_source_view':None,'factor_snapshot':None,'factor_basis_review':copy.deepcopy(p['factor_basis_review']),
        'factor_basis_source_snapshots':[],'calculation_source_view':None,'fuel_conversion_reproduced':False,
        'source_authenticated':False,'actual_combustion_verified':False,'regulatory_quantity_verified':False,
        'whole_inventory_coverage_verified':False,'engineering_or_assurance_approved':False,'external_action_authorized':False}
    def gap(code,message):
        result['status']='blocked'
        result['diagnostics'].append({'code':code,'message':message})
        result['data_gaps'].append({'id':p['result_id']+'-gap-'+str(len(result['data_gaps'])),
            'field':'fuel_emissions','reason':message,'impact':'No supported fuel emissions calculation is produced.',
            'remedy':'Reconcile current fuel sources, actual combustion and heating/material/reference basis with a defensible emission factor and qualified review.'})
    try:
        owner=next((r for r in state['results'] if r['id']==p['fuel_result_id']),None)
        if owner is None or owner['skill']!='build-energy-baseline' or owner['status']!='partial' or len(owner['metrics'])!=1:
            raise ValueError('Current successful complete fuel conversion result required.')
        original=_diagnostic(owner,'FUEL_ENERGY_INPUTS');fuel=_diagnostic(owner,'FUEL_ENERGY_CONVERSION')
        if original['fixture_mode'] and not p['fixture_mode']:
            raise ValueError('Fictional upstream fuel conversion cannot enter ordinary emissions mode.')
        replay=copy.deepcopy(original);replay['result_id']=p['result_id']+'-fuel-reproduction'
        while replay['result_id'] in ids or any(m['id']==replay['result_id']+'-energy' for r in state['results'] for m in r['metrics']):
            replay['result_id']+='-next'
        checked=run_fuel_energy(state,replay)['result'];metric=copy.deepcopy(checked['metrics'][0]) if checked['metrics'] else None
        if metric is not None:metric['id']=owner['metrics'][0]['id']
        if checked['status']!='partial' or metric!=owner['metrics'][0] or _diagnostic(checked,'FUEL_ENERGY_CONVERSION')!=fuel or set(checked['evidence_ids'])!=set(owner['evidence_ids']):
            raise ValueError('Full current fuel arithmetic, source snapshots, units, basis and evidence must reproduce.')
        report['fuel_conversion_reproduced']=True
        report['fuel_source_view']={'result_id':owner['id'],'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest()}
        refs.update(owner['evidence_ids']);factor=next((f for f in state['emission_factors'] if f['id']==p['factor_id']),None)
        report['factor_snapshot']=copy.deepcopy(factor)
        if factor is not None:
            refs.update(factor['evidence_ids'])
            review=p['factor_basis_review']
            try:
                _fields(review, {'fuel_result_id','factor_id','boundary_id','period','as_of_date','factor_heating_basis',
                                 'fuel_basis','combustion_activity','activity_definition','evidence_ids','evidence_fit','rationale','reviewer_role'},
                        ('activity_definition','rationale','reviewer_role'))
                if (review['fuel_result_id']!=owner['id'] or review['factor_id']!=factor['id']
                    or review['boundary_id']!=state['organizational_boundary']['id'] or review['period']!=state['reporting_period']
                    or review['as_of_date']!=original['conversion_review']['as_of_date']
                    or review['factor_heating_basis'] not in {'LHV','HHV'} or review['factor_heating_basis']!=fuel['heating_basis']
                    or review['fuel_basis']!=original['quantity_basis'] or review['combustion_activity'] is not True
                    or review['evidence_fit']!='reviewed_supporting'):
                    raise ValueError('Matched current fuel/factor/time/boundary/heating/material/reference basis and explicit combusted-quantity support required.')
                when=_date(review['as_of_date']);sources=_sources(state,review['evidence_ids'],refs)
                factor_sources=_sources(state,factor['evidence_ids'],refs)
                report['factor_basis_source_snapshots']=copy.deepcopy(sources)
                if (not sources or not set(factor['evidence_ids'])<=set(review['evidence_ids'])
                    or _date(factor['source']['accessed'])>when
                    or any(e['source']['version'] is None or _date(e['source']['accessed'])>when
                           or e['period']['start']>state['reporting_period']['start'] or e['period']['end']<state['reporting_period']['end'] for e in sources)
                    or not any(e['source']['locator']==factor['source']['locator'] and e['source']['version']==factor['source']['version']
                               and e['unit']==factor['unit'] for e in factor_sources)):
                    raise ValueError('Versioned nonfuture full-period factor/basis sources with exact factor source/unit identity required.')
            except (ValueError,TypeError,KeyError) as error:
                gap('EMISSION_FACTOR_REQUIRED',str(error))
        if result['status']!='blocked':
            parent=calculate_result(state,owner['metrics'][0]['id'],p['factor_id'],copy.deepcopy(p['factor_policy']),p['result_id']+'-calculation',p['fixture_mode'])
            working=parent['proposal']['state'];source=parent['result']
            report['calculation_source_view']={'result_id':source['id'],'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()}
            result=_empty(working,'calculate-co2e',p['result_id']);result['status']='blocked' if source['status']=='blocked' else 'partial'
            refs.update(source['evidence_ids'])
            result['diagnostics'].extend(copy.deepcopy(d) for d in source['diagnostics'] if d['code']=='EMISSION_FACTOR_REQUIRED')
    except (ValueError,TypeError,KeyError) as error:
        gap('FUEL_EMISSIONS_DATA_REQUIRED',str(error))
    result['evidence_ids']=sorted(refs)
    result['review_requirements'].append({'id':p['result_id']+'-fuel-factor-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
        'reason':'Review actual combusted activity, heating/material/reference basis, fuel/technology/gas coverage and source-specific factor applicability before inventory or claims use.',
        'scope':'Selected conditional fuel CO2e calculation only','reviewer_role':'Qualified GHG and energy professionals and accountable owner','status':'open','resolution':None})
    result['review_states']=list(dict.fromkeys(result['review_states']+['PROFESSIONAL_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['diagnostics'].extend([{'code':'FUEL_CO2E_SOURCE_BRIDGE','message':json.dumps(report,sort_keys=True)},
                                 {'code':'FUEL_CO2E_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Review source/combustion and factor-basis fitness; preserve all factor, engineering, legal and assurance requirements before actual inventory or publication.']
    final=propose(working,result,'Compose reproduced fuel energy and a separately basis-reviewed sourced CO2e factor')['state']
    final['revision']=state['revision']+1;validate_state(final)
    return {'result':result,'proposal':{'base_revision':state['revision'],'state':final,'reason':'Compose reproduced fuel energy and a separately basis-reviewed sourced CO2e factor'}}
