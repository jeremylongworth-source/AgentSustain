"""Reproduced facility/source/species ledger candidates, never statutory totals."""
import copy
from decimal import DecimalException, Underflow, localcontext
import json

from .climate_tools import _date, _fields, _sources, _text
from .contract_validation import validate_state
from .data_tools import number, serialize
from .gas_conversion import _diagnostic, convert_gas_mass
from .jurisdiction_tools import read_pinned_pack
from .state_proposal import propose


def load_profile(pin, fixture_mode):
    profile = read_pinned_pack(pin)
    _fields(profile, {'id','version','execution_contract','synthetic','gases','basis','time_horizon_years','source','scope','limitations'},
            ('id','version','execution_contract','basis','scope','limitations'))
    if profile['execution_contract'] != 'gas-ledger-0.1.0' or type(profile['synthetic']) is not bool or profile['synthetic'] and not fixture_mode:
        raise ValueError('Explicit ledger profile; synthetic content requires fixture mode.')
    gases = profile['gases']
    if not isinstance(gases,list) or not gases or any(not _text(g) for g in gases) or len(set(gases)) != len(gases):
        raise ValueError('Distinct explicit species roster required.')
    if type(profile['time_horizon_years']) is not int or not 1 <= profile['time_horizon_years'] <= 1000:
        raise ValueError('Explicit profile time horizon required.')
    _fields(profile['source'], {'locator','version','accessed'}, ('locator','version','accessed'))
    _date(profile['source']['accessed'])
    if not profile['synthetic'] and not profile['source']['locator'].startswith('https://'):
        raise ValueError('Real profile requires primary HTTPS source.')
    return profile


def build_gas_ledger(state, parameters):
    validate_state(state)
    _fields(parameters, {'profile_pin','sources','components','ledger_review','fixture_mode','result_id'}, ('result_id',))
    if type(parameters['fixture_mode']) is not bool or any(r['id']==parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused ledger ID required.')
    result={'id':parameters['result_id'],'skill':'build-facility-gas-ledger','contract_version':'0.1.0','status':'partial',
        'review_states':['ANALYTICAL'],'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],
        'evidence_ids':[],'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),
        'diagnostics':[],'next_actions':[]}
    refs=set()
    def gap(message,code='GAS_LEDGER_DATA_REQUIRED'):
        result['data_gaps'].append({'id':result['id']+'-gap-'+str(len(result['data_gaps'])),'field':'gas_source_ledger',
            'reason':message,'impact':'Facility/species coverage is incomplete or unverified; no statutory total follows.',
            'remedy':'Reconcile source/species coverage and obtain qualified source/method/legal review.'})
        result['diagnostics'].append({'code':code,'message':message})
    try:
        profile=load_profile(parameters['profile_pin'],parameters['fixture_mode'])
        review=parameters['ledger_review']
        _fields(review, {'facility_id','boundary_id','period','as_of_date','source_inventory_complete','exclusions',
            'evidence_ids','evidence_fit','scope','reviewer_role','rationale'}, ('facility_id','scope','reviewer_role','rationale'))
        when=_date(review['as_of_date']); primary=_sources(state,review['evidence_ids'],refs)
        if (review['facility_id'] not in state['organizational_boundary']['facility_ids'] or review['boundary_id']!=state['organizational_boundary']['id']
            or review['period']!=state['reporting_period'] or type(review['source_inventory_complete']) is not bool
            or not isinstance(review['exclusions'],list) or any(not _text(x) for x in review['exclusions'])):
            raise ValueError('Known in-boundary facility, matched period and explicit coverage/exclusions required.')
        if _date(profile['source']['accessed'])>when:
            raise ValueError('Assessment cannot precede selected profile retrieval.')
        fit=(bool(primary) and review['evidence_fit']=='reviewed_supporting'
            and any(e['source']['locator']==profile['source']['locator'] and e['source']['version']==profile['source']['version'] for e in primary)
            and all(e['boundary_id']==review['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in primary))
        if review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:
            raise ValueError('Explicit ledger source fitness required.')
        if not isinstance(parameters['sources'],list) or not parameters['sources'] or not isinstance(parameters['components'],list):
            raise ValueError('Nonempty declared source inventory and explicit component list required.')
        sources={}; pairs=set()
        for source in parameters['sources']:
            _fields(source, {'id','facility_id','activity_id','activity_kind','gases','evidence_ids','evidence_fit','rationale'},
                    ('id','facility_id','activity_id','activity_kind','rationale'))
            if source['id'] in sources or source['facility_id']!=review['facility_id'] or set(source['gases'])!=set(profile['gases']) or len(source['gases'])!=len(set(source['gases'])):
                raise ValueError('Distinct source IDs in one facility and complete selected-profile gas roster required.')
            evidence=_sources(state,source['evidence_ids'],refs)
            if source['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:
                raise ValueError('Explicit source-to-facility fitness required.')
            supported=(fit and bool(evidence) and source['evidence_fit']=='reviewed_supporting'
                and all(e['boundary_id']==review['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in evidence))
            sources[source['id']]={'record':copy.deepcopy(source),'evidence':evidence,'supported':supported}
            pairs.update((source['id'],g) for g in profile['gases'])
        selected={}; used_results=set(); activity_gases=set(); activity_evidence_gases=set(); rows=[]; totals={g:0 for g in profile['gases']}; co2e=0; contributing=[]
        for component in parameters['components']:
            _fields(component, {'source_id','gas','conversion_result_id'}, ('source_id','gas'))
            key=(component['source_id'],component['gas']); ident=component['conversion_result_id']
            if key not in pairs or key in selected or ident is not None and not _text(ident):
                raise ValueError('Distinct actual source/species slots and explicit result ID or unknown required.')
            selected[key]=component
        with localcontext() as context:
            context.prec=34;context.traps[Underflow]=True
            for key in sorted(pairs):
                source=sources[key[0]]; component=selected.get(key); ident=component['conversion_result_id'] if component else None
                owner=next((r for r in state['results'] if r['id']==ident),None) if ident is not None else None
                row={'source_id':key[0],'gas':key[1],'conversion_result_id':ident,'included':False,'conversion_snapshot':None}
                if owner is not None and owner['skill']!='convert-gas-mass-to-co2e':
                    raise ValueError('Only source-species conversion results may occupy ledger slots.')
                if owner is None or owner['status']=='blocked':
                    row['blocked_result_snapshot']=copy.deepcopy(owner)
                    if owner:
                        refs.update(owner['evidence_ids'])
                        raw_id=_diagnostic(owner,'GAS_CO2E_INPUTS')['gas_result_id']
                        raw=next((r for r in state['results'] if r['id']==raw_id),None)
                        row['unconverted_raw_result_snapshot']=copy.deepcopy(raw)
                        row['raw_snapshot_reproduced']=False
                        if raw:refs.update(raw['evidence_ids'])
                    code='EMISSION_FACTOR_REQUIRED' if owner and any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in owner['diagnostics']) else 'GAS_LEDGER_DATA_REQUIRED'
                    gap('/'.join(key)+': source quantity/conversion missing or blocked; not counted as zero.',code)
                    rows.append(row);continue
                if owner['skill']!='convert-gas-mass-to-co2e' or owner['status']!='partial' or ident in used_results:
                    raise ValueError('Distinct supported species-conversion results required, not corporate/scope subtotals.')
                inputs=_diagnostic(owner,'GAS_CO2E_INPUTS')
                if inputs['fixture_mode'] and not parameters['fixture_mode']:
                    raise ValueError('Fictional upstream conversions cannot enter real ledgers.')
                args=copy.deepcopy(inputs);args['result_id']=result['id']+'-component-check'
                while any(r['id']==args['result_id'] for r in state['results']):args['result_id']+='-next'
                checked=convert_gas_mass(state,args)['result'];metrics=copy.deepcopy(checked['metrics'])
                for m in metrics:m['id']=m['id'].replace(args['result_id'],owner['id'],1)
                record=_diagnostic(owner,'GAS_CO2E_CONVERSION')
                if (checked['status']!=owner['status'] or metrics!=owner['metrics'] or set(checked['evidence_ids'])!=set(owner['evidence_ids'])
                    or _diagnostic(checked,'GAS_CO2E_CONVERSION')!=record):
                    raise ValueError('Complete conversion metric/report/uncertainty/source/evidence lineage must reproduce.')
                gas_record=record['gas_report_snapshot']; activity=gas_record['activity_snapshot']; gwp=record['gwp_snapshot']
                if (gwp['gas']!=key[1] or gwp['basis']!=profile['basis'] or gwp['time_horizon_years']!=profile['time_horizon_years']
                    or record['conversion_review']['as_of_date']!=review['as_of_date'] or activity['id']!=source['record']['activity_id']
                    or gas_record['factor_snapshot']['activity_kind']!=source['record']['activity_kind']
                    or not set(activity['evidence_ids'])<=set(source['record']['evidence_ids'])):
                    raise ValueError('Exact species/basis/horizon/date/activity/kind and source-bound activity evidence required.')
                activity_pair=(activity['id'],key[1])
                if activity_pair in activity_gases:
                    raise ValueError('Same activity/species cannot be counted through another source or alternative conversion.')
                evidence_pairs={(e,key[1]) for e in activity['evidence_ids']}
                if evidence_pairs & activity_evidence_gases:
                    raise ValueError('Shared activity evidence/species requires explicit non-overlapping partitions; no reallocation inferred.')
                activity_evidence_gases.update(evidence_pairs)
                used_results.add(ident);activity_gases.add(activity_pair);refs.update(owner['evidence_ids'])
                row['conversion_snapshot']=record
                if source['supported']:
                    row['included']=True;totals[key[1]]+=number(record['gas_metric_snapshot']['value']);co2e+=number(owner['metrics'][0]['value'])
                    contributing.append(owner['metrics'][0]['id'])
                else:gap('/'.join(key)+': source/profile facility attribution is unverified; quantity withheld.')
                rows.append(row)
        complete=all(r['included'] for r in rows) and review['source_inventory_complete'] and not review['exclusions'] and fit
        if not complete:gap('Declared source/species coverage incomplete or unfit; known subtotal is not a complete facility total.')
        report={'execution_contract':'gas-ledger-0.1.0','profile':profile,'profile_pin':copy.deepcopy(parameters['profile_pin']),
            'ledger_review':copy.deepcopy(review),'primary_source_snapshots':primary,'sources':sources,'rows':rows,
            'included_species_mass_kg':{g:serialize(number(v)) if any(r['included'] and r['gas']==g for r in rows) else None for g,v in totals.items()},
            'known_co2e_kg':serialize(number(co2e)) if contributing else None,
            'declared_coverage_reproduced':complete,'regulatory_quantity_verified':False,'facility_attribution_authenticated':False,
            'whole_organization_coverage_verified':False,'statutory_threshold_authorized':False,'scope_account_created':False}
        if contributing:
            result['assumptions']=list(dict.fromkeys(result['assumptions']+['Selected declared sources only; no verified regulatory or organizational total.']))
            result['metrics']=[{'id':result['id']+'-metric','name':'Selected facility-source CO2e subtotal','value':serialize(number(co2e)),
                'unit':'kg CO2e','period':copy.deepcopy(review['period']),'boundary_id':review['boundary_id'],'evidence_ids':sorted(refs),
                'method':{'name':'Reproduced source/species ledger subtotal','version':'gas-ledger-0.1.0','source':profile['source']['locator']},
                'assumption':'Selected declared sources only; no verified regulatory or organizational total.',
                'uncertainty':{'kind':'unquantified','description':'Parent/source uncertainty and missing coverage retained; combined uncertainty not quantified.','value':None,'unit':None},
                'calculation':{'formula':'sum distinct reproduced selected source/species CO2e contributions','inputs':contributing,
                    'conversions':[],'rounding':'34-digit Decimal sum of reproduced JSON metrics; final JSON number only'}}]
        result['diagnostics'].append({'code':'FACILITY_GAS_LEDGER','message':json.dumps(report,sort_keys=True)})
        result['review_requirements'].append({'id':result['id']+'-ledger-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
            'reason':'Review facility/source identity, complete species coverage, non-overlap, source methods and profile applicability.',
            'scope':review['scope'],'reviewer_role':review['reviewer_role'],'status':'open','resolution':None})
    except (ValueError,TypeError,KeyError,OSError,DecimalException) as error:
        result['status']='blocked';result['metrics']=[];gap(str(error))
    result['evidence_ids']=sorted(refs)
    result['diagnostics'].append({'code':'GAS_LEDGER_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    result['review_states']=list(dict.fromkeys(result['review_states']+[r['state'] for r in result['review_requirements'] if r['status']=='open']+['EVIDENCE_INCOMPLETE']))
    result['next_actions']=list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result':result,'proposal':propose(state,result,'Record distinct facility/source/species subtotals with explicit omissions; no statutory total or review resolution')}
