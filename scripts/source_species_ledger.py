"""Source/species accounting with supplied zero measurements and explicit exclusions."""
import copy
from decimal import Underflow, localcontext
import hashlib
import json
from .climate_tools import _fields, _sources, _date, _text
from .contract_validation import validate_state
from .data_tools import number, serialize
from .gas_conversion import _diagnostic, convert_gas_mass
from .jurisdiction_tools import read_pinned_pack
from .manager_workflow import _empty
from .state_proposal import propose


def load_matrix(pin, fixture_mode):
    p=read_pinned_pack(pin)
    _fields(p, {'id','version','execution_contract','synthetic','gases','basis','time_horizon_years','treatments','source','scope','limitations'},
        ('id','version','execution_contract','basis','scope','limitations'))
    if p['execution_contract'] not in {'source-species-ledger-0.2.0','source-species-ledger-0.3.0'} or type(p['synthetic']) is not bool or p['synthetic'] and not fixture_mode:
        raise ValueError('Explicit matrix contract and per-request synthetic opt-in required.')
    if not isinstance(p['gases'],list) or not p['gases'] or any(not _text(g) for g in p['gases']) or len(set(p['gases']))!=len(p['gases']):
        raise ValueError('Distinct explicit profile species required.')
    if type(p['time_horizon_years']) is not int or not 1<=p['time_horizon_years']<=1000 or not isinstance(p['treatments'],dict) or not p['treatments']:
        raise ValueError('Explicit horizon and source-class treatments required.')
    for kind,treatments in p['treatments'].items():
        if not _text(kind) or not isinstance(treatments,dict) or set(treatments)!=set(p['gases']) or any(t not in {'include','exclude'} for t in treatments.values()):
            raise ValueError('Every source class must explicitly cover all profile species.')
    _fields(p['source'],{'locator','version','accessed'},('locator','version','accessed'));_date(p['source']['accessed'])
    if not p['synthetic'] and not p['source']['locator'].startswith('https://'):raise ValueError('Real profile requires primary HTTPS source.')
    return p


def build_source_species_ledger(state,p):
    validate_state(state);_fields(p,{'profile_pin','sources','slots','coverage_review','fixture_mode','result_id'},('result_id',))
    if type(p['fixture_mode']) is not bool or any(r['id']==p['result_id'] for r in state['results']):raise ValueError('Boolean fixture mode and fresh result ID required.')
    profile=load_matrix(p['profile_pin'],p['fixture_mode']);review=p['coverage_review']
    _fields(review,{'facility_id','boundary_id','period','as_of_date','source_inventory_complete','evidence_ids','evidence_fit','scope','reviewer_role','rationale'},('facility_id','scope','reviewer_role','rationale'))
    if review['facility_id'] not in state['organizational_boundary']['facility_ids'] or review['boundary_id']!=state['organizational_boundary']['id'] or review['period']!=state['reporting_period'] or type(review['source_inventory_complete']) is not bool:
        raise ValueError('Explicit matched facility, boundary, period and declared source inventory required.')
    when=_date(review['as_of_date']);result=_empty(state,'build-facility-gas-ledger',p['result_id']);refs=set()
    def supported(eids,unit=None,period=None):
        evidence=_sources(state,eids,refs)
        return bool(evidence) and all(e['boundary_id']==review['boundary_id'] and e['source']['version'] is not None
            and _date(e['source']['accessed'])<=when and (unit is None or e['unit']==unit) and (period is None or e['period']==period)
            and (p['fixture_mode'] or not e['source']['locator'].startswith('fixture:')) for e in evidence)
    primary=_sources(state,review['evidence_ids'],refs)
    fit=(review['evidence_fit']=='reviewed_supporting' and supported(review['evidence_ids']) and _date(profile['source']['accessed'])<=when
        and any(e['source']['locator']==profile['source']['locator'] and e['source']['version']==profile['source']['version'] for e in primary))
    if review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:raise ValueError('Explicit source fitness required.')
    if not isinstance(p['sources'],list) or not p['sources'] or not isinstance(p['slots'],list):raise ValueError('Nonempty sources and explicit slot list required.')
    sources={};pairs=set()
    for s in p['sources']:
        _fields(s,{'id','facility_id','activity_id','activity_kind','source_class','evidence_ids','evidence_fit','rationale'},('id','facility_id','activity_id','activity_kind','source_class','rationale'))
        if s['id'] in sources or s['facility_id']!=review['facility_id'] or s['source_class'] not in profile['treatments'] or s['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:raise ValueError('Distinct matched source IDs, supported classes and explicit fitness required.')
        sources[s['id']]={'record':copy.deepcopy(s),'supported':fit and s['evidence_fit']=='reviewed_supporting' and supported(s['evidence_ids'])}
        pairs.update((s['id'],gas) for gas in profile['gases'])
    selected={}
    for slot in p['slots']:
        _fields(slot,{'source_id','gas','status','result_id','metric_id','evidence_ids','evidence_fit','rationale','gwp','gwp_review'},('source_id','gas','status','rationale'))
        key=(slot['source_id'],slot['gas'])
        if key not in pairs or key in selected or slot['status'] not in ({'converted','measured_zero','unknown','measured_mass'} if profile['execution_contract']=='source-species-ledger-0.3.0' else {'converted','measured_zero','unknown'}) or slot['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:raise ValueError('Distinct actual source/species slots and explicit quantity status required.')
        if slot['status'] not in {'measured_zero','measured_mass'} and (slot['gwp'] is not None or slot['gwp_review'] is not None):raise ValueError('Only direct zero slots select a separate supplied GWP.')
        if slot['status']=='unknown' and (slot['result_id'] is not None or slot['metric_id'] is not None):raise ValueError('Unknown slot cannot carry a quantity selector.')
        selected[key]=slot
    rows=[];total=number(0);used=set();evidence_gases=set();included=[];complete=fit and review['source_inventory_complete']
    def gap(message,code='SOURCE_SPECIES_DATA_REQUIRED'):
        result['data_gaps'].append({'id':result['id']+'-matrix-gap-'+str(len(result['data_gaps'])),'field':'source_species_matrix','reason':message,
            'impact':'Selected quantity or coverage remains incomplete; no statutory total or threshold follows.','remedy':'Reconcile explicit source/species measurements, conversions, treatment and qualified method/source review.'})
        result['diagnostics'].append({'code':code,'message':message})
    with localcontext() as context:
        context.prec=34;context.traps[Underflow]=True
        for key in sorted(pairs):
            source=sources[key[0]];slot=selected.get(key);treatment=profile['treatments'][source['record']['source_class']][key[1]]
            row={'source_id':key[0],'gas':key[1],'treatment':treatment,'input':copy.deepcopy(slot),'resolved':False,'included':False,
                 'mass_kg':None,'co2e_kg':None,'source_result_view':None,'source_quantity_snapshot':None}
            try:
                if slot is None or slot['status']=='unknown':raise ValueError('Missing or declared unknown slot; never inferred zero.')
                if not source['supported'] or slot['evidence_fit']!='reviewed_supporting' or not supported(slot['evidence_ids']):raise ValueError('Source/profile/slot fitness is unresolved.')
                owner=next((r for r in state['results'] if r['id']==slot['result_id']),None)
                if owner is None or owner['status'] in {'blocked','invalid_input'}:
                    if owner:
                        refs.update(owner['evidence_ids']);row['blocked_quantity_result_snapshot']=copy.deepcopy(owner)
                        row['unconverted_raw_result_snapshot']=None;row['raw_snapshot_reproduced']=False
                        if owner['skill']=='convert-gas-mass-to-co2e':
                            try:
                                raw_id=_diagnostic(owner,'GAS_CO2E_INPUTS')['gas_result_id']
                                raw=next((r for r in state['results'] if r['id']==raw_id),None)
                                row['unconverted_raw_result_snapshot']=copy.deepcopy(raw)
                                if raw:refs.update(raw['evidence_ids'])
                            except (ValueError,KeyError,TypeError):pass
                    if owner and any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in owner['diagnostics']):gap('/'.join(key)+': selected factor remains required.','EMISSION_FACTOR_REQUIRED')
                    raise ValueError('Selected source quantity is missing or blocked.')
                if (owner['id'],key[1]) in used:raise ValueError('Quantity cannot be reused in another source slot.')
                if slot['status']=='converted':
                    if slot['metric_id'] is not None or owner['skill']!='convert-gas-mass-to-co2e':raise ValueError('Converted slot selects one existing complete conversion result, not a metric relabeling.')
                    inputs=_diagnostic(owner,'GAS_CO2E_INPUTS');args=copy.deepcopy(inputs)
                    if inputs['fixture_mode'] and not p['fixture_mode']:raise ValueError('Synthetic conversion requires explicit fixture opt-in.')
                    args['result_id']=result['id']+'-replay'
                    while any(r['id']==args['result_id'] for r in state['results']):args['result_id']+='-next'
                    checked=convert_gas_mass(state,args)['result'];metrics=copy.deepcopy(checked['metrics'])
                    for m in metrics:m['id']=m['id'].replace(args['result_id'],owner['id'],1)
                    record=_diagnostic(owner,'GAS_CO2E_CONVERSION')
                    if checked['status']!=owner['status'] or metrics!=owner['metrics'] or set(checked['evidence_ids'])!=set(owner['evidence_ids']) or _diagnostic(checked,'GAS_CO2E_CONVERSION')!=record:raise ValueError('Complete current conversion/mass/report/lineage must reproduce.')
                    gas_report=record['gas_report_snapshot'];activity=gas_report['activity_snapshot'];gwp=record['gwp_snapshot']
                    if gwp['gas']!=key[1] or gwp['basis']!=profile['basis'] or gwp['time_horizon_years']!=profile['time_horizon_years'] or record['conversion_review']['as_of_date']!=review['as_of_date'] or activity['id']!=source['record']['activity_id'] or gas_report['factor_snapshot']['activity_kind']!=source['record']['activity_kind'] or not set(activity['evidence_ids'])<=set(source['record']['evidence_ids']):raise ValueError('Exact gas/basis/horizon/date/activity/kind/source context required.')
                    row['mass_kg']=record['gas_metric_snapshot']['value'];row['co2e_kg']=owner['metrics'][0]['value'];row['source_quantity_snapshot']=record
                    refs.update(owner['evidence_ids']);identity_evidence=activity['evidence_ids']
                else:
                    metric=next((m for m in owner['metrics'] if m['id']==slot['metric_id']),None)
                    if metric is None or metric['value'] is None or (number(metric['value'])!=0 if slot['status']=='measured_zero' else number(metric['value'])<0) or metric['unit']!='kg '+key[1] or metric['period']!=review['period'] or _date(metric['period']['end'])>when or metric['boundary_id']!=review['boundary_id'] or not set(metric['evidence_ids'])<=set(source['record']['evidence_ids']) or not supported(metric['evidence_ids'],metric['unit'],metric['period']):raise ValueError('Explicit sourced zero kilogram species metric with exact period/boundary required; absence prose is insufficient.' if slot['status']=='measured_zero' else 'Explicit nonnegative sourced kilogram species measurement with exact past period/boundary required.')
                    row['source_quantity_snapshot']={('zero_metric_snapshot' if slot['status']=='measured_zero' else 'measured_metric_snapshot'):copy.deepcopy(metric),'gwp_snapshot':copy.deepcopy(slot['gwp'])}
                    gwp=slot['gwp'];sr=slot['gwp_review']
                    if gwp is None or sr is None:
                        gap('/'.join(key)+(': no defensible species GWP supplied for the zero observation.' if slot['status']=='measured_zero' else ': no defensible species GWP supplied for the measured mass.'),'GWP_REQUIRED')
                        raise ValueError('Zero observations do not bypass supplied GWP provenance.' if slot['status']=='measured_zero' else 'Measured mass does not bypass supplied GWP provenance.')
                    _fields(gwp,{'id','gas','value','unit','basis','time_horizon_years','source','status','evidence_ids'},('id','gas','unit','basis','status'))
                    _fields(gwp['source'],{'locator','publisher','version','accessed'},('locator','publisher','version','accessed'))
                    ratio=number(gwp['value'])
                    if ratio<0 or gwp['gas']!=key[1] or gwp['unit']!='kg CO2e/kg '+key[1] or gwp['basis']!=profile['basis'] or type(gwp['time_horizon_years']) is not int or gwp['time_horizon_years']!=profile['time_horizon_years'] or _date(gwp['source']['accessed'])>when or gwp['status']!='reviewed' and not (p['fixture_mode'] and gwp['status']=='synthetic'):
                        raise ValueError('Exact finite species/unit/basis/horizon/date and reviewed GWP required.')
                    _fields(sr,{'gwp_id','gas_result_id','gas_metric_id','gas','value','unit','basis','time_horizon_years','source_locator','source_version','evidence_ids','evidence_fit','checked_as_of','rationale'},('rationale',))
                    number(sr['value'])
                    expected={'gwp_id':gwp['id'],'gas_result_id':owner['id'],'gas_metric_id':metric['id'],
                        **{k:gwp[k] for k in ('gas','value','unit','basis','time_horizon_years','evidence_ids')},
                        'source_locator':gwp['source']['locator'],'source_version':gwp['source']['version']}
                    if any(sr[k]!=v for k,v in expected.items()) or type(sr['time_horizon_years']) is not int or sr['evidence_fit']!='reviewed_supporting' or sr['checked_as_of']!=review['as_of_date'] or not supported(sr['evidence_ids'],gwp['unit']):raise ValueError('Exact source/value/species/basis/horizon/direct-quantity GWP confirmation required.')
                    ge=_sources(state,gwp['evidence_ids'],refs)
                    if not supported(gwp['evidence_ids'],gwp['unit']) or not any(e['source']['locator']==gwp['source']['locator'] and e['source']['version']==gwp['source']['version'] for e in ge) or not p['fixture_mode'] and not gwp['source']['locator'].startswith('https://'):raise ValueError('Current versioned GWP evidence must match its source and ratio units.')
                    row['source_quantity_snapshot']['gwp_source_snapshots']=copy.deepcopy(ge)
                    row['source_quantity_snapshot']['gwp_review']=copy.deepcopy(sr)
                    row['mass_kg']=0 if slot['status']=='measured_zero' else serialize(number(metric['value']));row['co2e_kg']=serialize(number(metric['value'])*ratio);identity_evidence=metric['evidence_ids']
                    refs.update(owner['evidence_ids'])
                keys={(e,key[1]) for e in identity_evidence}
                if keys & evidence_gases:raise ValueError('Shared quantity evidence/species requires explicit non-overlapping source partitions.')
                evidence_gases.update(keys);used.add((owner['id'],key[1]))
                row['source_result_view']={'result_id':owner['id'],'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest()}
                row['resolved']=True;row['included']=treatment=='include'
                if row['included']:
                    total+=number(row['co2e_kg']);included.append(owner['metrics'][0]['id'] if slot['status']=='converted' else slot['metric_id'])
            except (ValueError,KeyError,TypeError) as error:
                row['mass_kg']=None;row['co2e_kg']=None
                complete=False;gap('/'.join(key)+': '+str(error))
            rows.append(row)
    if not complete:gap('Declared source/species inventory or a required included/excluded slot remains incomplete.')
    result['evidence_ids']=sorted(refs);result['review_states']=list(dict.fromkeys(result['review_states']+['PROFESSIONAL_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['review_requirements'].append({'id':result['id']+'-matrix-review','state':'PROFESSIONAL_REVIEW_REQUIRED','reason':'Review source identities, direct zero observations, conversions, species completeness, treatment/exclusion interpretation and uncertainty.',
        'scope':review['scope'],'reviewer_role':review['reviewer_role'],'status':'open','resolution':None})
    result['status']='partial'
    if included:
        template=next(m for r in state['results'] for m in r['metrics'] if m['id']==included[0]);metric=copy.deepcopy(template)
        metric.update(id=result['id']+'-metric',name='Selected source/species included CO2e subtotal',value=serialize(total),unit='kg CO2e',period=copy.deepcopy(review['period']),boundary_id=review['boundary_id'],evidence_ids=sorted(refs),
            method={'name':'Explicit source/species treatment subtotal','version':profile['execution_contract'],'source':profile['source']['locator']},
            assumption='Selected declared sources and treatment only; no authenticated statutory quantity.',
            uncertainty={'kind':'unquantified','description':'Full parent/source uncertainty preserved; no combined interval or confidence inferred.','value':None,'unit':None},
            calculation={'formula':'sum distinct supported included source/species CO2e contributions; excluded quantities remain separate','inputs':included,'conversions':[json.dumps({'from': 'kg '+r['gas'], 'to':'kg CO2e', 'factor':r['input']['gwp']['value'], 'evidence_ids':r['input']['gwp']['evidence_ids']},sort_keys=True) for r in rows if r['included'] and r['input']['status'] in {'measured_zero','measured_mass'}],'rounding':'34-digit Decimal sum; final JSON number only'})
        result['metrics']=[metric];result['assumptions']=list(dict.fromkeys(result['assumptions']+[metric['assumption']]))
    elif not any(r['resolved'] for r in rows):result['status']='blocked'
    report={'execution_contract':profile['execution_contract'],'profile':profile,'profile_pin':copy.deepcopy(p['profile_pin']),'coverage_review':copy.deepcopy(review),'sources':sources,'rows':rows,
        'known_included_co2e_kg':serialize(total) if included else None,'declared_source_species_coverage_reproduced':complete,
        'source_authenticity_verified':False,'source_attribution_authenticated':False,'regulatory_method_verified':False,'regulatory_quantity_verified':False,'statutory_threshold_authorized':False,'legal_exclusion_verified':False,'publication_authorized':False}
    result['diagnostics'].extend([{'code':'SOURCE_SPECIES_LEDGER','message':json.dumps(report,sort_keys=True)}, {'code':'SOURCE_SPECIES_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Reconcile all source/species and excluded quantities, direct zero observations, interpretation and qualified source/method/legal review before any threshold or disclosure use.']
    return {'result':result,'proposal':propose(state,result,'Preserve included/excluded/unknown source-species views without a statutory total')}
