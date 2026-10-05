"""Reproduce selected inventory lineage for original claims; no neutrality approval."""
import copy
import json

from .climate_tools import _date, _fields, _sources
from .contract_validation import validate_state
from .ghg_foundation import calculate_result
from .ghg_inventory import build_inventory, _diagnostic
from .scope_accounting import compose_scope
from .scope3_accounting import calculate_category
from .claim_material import assess_bound_claim
from .state_proposal import propose


def _check(state, source, checked, report_code=None):
    factor_gaps=[d['message'] for d in checked['diagnostics'] if d['code']=='EMISSION_FACTOR_REQUIRED']
    if factor_gaps:raise ValueError('EMISSION_FACTOR_REQUIRED: '+' '.join(factor_gaps))
    metrics=copy.deepcopy(checked['metrics'])
    for metric in metrics:
        metric['id']=metric['id'].replace(checked['id'],source['id'],1)
    new_gaps={g['id'] for g in checked['data_gaps']}-{g['id'] for g in state['data_gaps']}
    if (checked['status']=='blocked' or source['status']=='completed' and new_gaps or metrics!=source['metrics']
        or set(checked['evidence_ids'])!=set(source['evidence_ids'])
        or report_code and _diagnostic(checked,report_code)!=_diagnostic(source,report_code)):
        raise ValueError('Full inventory/account/component metrics, uncertainty, method, report and evidence lineage must reproduce.')


def reproduce_inventory(state, review, result_id, fixture_mode):
    _fields(review, {'inventory_result_id','boundary_id','period','as_of_date','subject_id','coverage','facility_ids',
        'coverage_evidence_ids','evidence_fit','scope_2_method','gwp_basis','rationale','gas_coverage_assessment','reviewer_role'},
        ('inventory_result_id','subject_id','rationale','gas_coverage_assessment','reviewer_role','gwp_basis'))
    if review['coverage'] not in {'selected_sources','whole_subject','unknown'} or review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:
        raise ValueError('Explicit inventory coverage and evidence fitness required.')
    if review['scope_2_method'] not in {'location','market','unknown'}:
        raise ValueError('One explicit scope 2 method or unknown required; alternatives are never summed.')
    if not isinstance(review['facility_ids'],list) or len(set(review['facility_ids']))!=len(review['facility_ids']) or not set(review['facility_ids'])<=set(state['organizational_boundary']['facility_ids']):
        raise ValueError('Distinct current boundary facility references required.')
    refs=set();coverage_sources=_sources(state,review['coverage_evidence_ids'],refs);when=_date(review['as_of_date'])
    results={r['id']:r for r in state['results']}
    source=results.get(review['inventory_result_id'])
    if source is None or source['skill']!='build-ghg-inventory' or source['status'] not in {'completed','partial'} or len(source['metrics'])!=1:
        raise ValueError('A supported selected inventory is required; missing/blocked results never imply zero.')
    selection=_diagnostic(source,'INVENTORY_SELECTION');included=selection['included']
    direct=[x['result_id'] for x in included if x['scope']=='scope_1']
    energy=[x['result_id'] for x in included if x['scope']=='scope_2']
    categories=[x['result_id'] for x in included if x['scope']=='scope_3']
    if len(direct)>1 or len(energy)>1 or len(included)!=len(direct)+len(energy)+len(categories):
        raise ValueError('One selected scope 1/2 account and distinct scope 3 categories required.')
    serial=0
    def verification_id():
        nonlocal serial
        serial+=1;ident=result_id+'-inventory-check-'+str(serial)
        while ident in results:ident+='-next'
        return ident
    accounts=[];leaf_records=[];factors={};unsupported_components=[];account_facilities={'scope_1':set(),'scope_2':set()}
    for item in included:
        account=results.get(item['result_id'])
        if account is None:raise ValueError('Inventory source account must resolve.')
        code='SCOPE3_CATEGORY' if item['scope']=='scope_3' else 'SCOPE_METHOD'
        record=_diagnostic(account,code)
        accepted_metrics={c['metric_id'] for c in record['accepted']}
        for component in record['components']:
            if component['metric_id'] not in accepted_metrics:
                unsupported_components.append({'account_result_id':account['id'],'component':copy.deepcopy(component)})
                continue
            leaf=next((r for r in state['results'] if any(m['id']==component['metric_id'] for m in r['metrics'])),None)
            if leaf is None or leaf['skill']!='calculate-co2e' or len(leaf['metrics'])!=1:
                raise ValueError('Inventory component must resolve to one supported CO2e calculation.')
            activity_id=component['policy']['source_review']['activity_id']
            checked=calculate_result(state,activity_id,component['factor_id'],component['policy'],verification_id(),fixture_mode)['result']
            _check(state,leaf,checked);refs.update(leaf['evidence_ids'])
            leaf_records.append({'result':copy.deepcopy(leaf),'policy':copy.deepcopy(component['policy']),'activity_id':activity_id})
            factor=next((f for f in state['emission_factors'] if f['id']==component['factor_id']),None)
            if factor is None:raise ValueError('Explicit defensible factor is required; no model-memory factor.')
            factors[factor['id']]=copy.deepcopy(factor)
        if item['scope']=='scope_3':
            checked=calculate_category(state,record['category'],record['sources'],record['components'],record['coverage_review'],verification_id(),fixture_mode)['result']
        else:
            checked=compose_scope(state,account['skill'],record['sources'],record['components'],record['coverage_review'],verification_id(),fixture_mode)['result']
            account_facilities[item['scope']].update(s['facility_id'] for s in record['sources'])
        _check(state,account,checked,code);refs.update(account['evidence_ids'])
        accounts.append({'result':copy.deepcopy(account),'reproduced_report':record})
    checked=build_inventory(state,direct[0] if direct else None,energy[0] if energy else None,categories,
        selection['category_screening'],selection['coverage_review'],verification_id(),fixture_mode)['result']
    _check(state,source,checked,'INVENTORY_SELECTION');refs.update(source['evidence_ids'])
    evidence=_sources(state,sorted(refs),set())
    source_fit=(bool(coverage_sources) and review['evidence_fit']=='reviewed_supporting'
        and review['boundary_id']==state['organizational_boundary']['id'] and review['period']==state['reporting_period']
        and review['subject_id']==state['organization']['id'] and review['gwp_basis']==selection['gwp_basis']
        and all(e['boundary_id']==review['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in evidence))
    source_fit=source_fit and all(e['period']['start']<=review['period']['start'] and e['period']['end']>=review['period']['end'] for e in coverage_sources)
    if energy:source_fit=source_fit and review['scope_2_method']==next(x['scope_2_method'] for x in included if x['scope']=='scope_2')
    synthetic=any(d['code']=='SYNTHETIC_FIXTURE' for r in [source]+[a['result'] for a in accounts]+[l['result'] for l in leaf_records] for d in r['diagnostics'])
    if synthetic and not fixture_mode:source_fit=False
    complete=(source_fit and review['coverage']=='whole_subject' and source['status']=='completed'
        and not source['data_gaps'] and all(a['result']['status']=='completed' and not a['result']['data_gaps'] for a in accounts)
        and all(l['result']['status']=='completed' and not l['result']['data_gaps'] for l in leaf_records) and len(direct)==len(energy)==1
        and review['scope_2_method']==next(x['scope_2_method'] for x in included if x['scope']=='scope_2')
        and set(review['facility_ids'])==set(state['organizational_boundary']['facility_ids'])
        and all(ids==set(review['facility_ids']) for ids in account_facilities.values())
        and not state['organizational_boundary']['exclusions']
        and len(selection['category_screening'])==15
        and all(c['status'] in {'applicable','not_applicable'} for c in selection['category_screening']))
    return {'execution_contract':'claim-inventory-0.1.0','claim_inventory_review':copy.deepcopy(review),
        'result':copy.deepcopy(source),'selection':selection,'source_accounts':accounts,'leaf_results':leaf_records,
        'unsupported_component_snapshots':unsupported_components,
        'factor_snapshots':list(factors.values()),'evidence_snapshots':evidence,'source_fit':bool(source_fit),
        'declared_scope_coverage_reproduced':bool(complete),'external_completeness_verified':False,
        'source_authenticity_verified':False,'net_emissions_or_neutrality_determined':False,'publication_authorized':False}


def assess_inventory_claim(state, parameters):
    validate_state(state)
    _fields(parameters, {'claim','classification_review','criteria','claim_review','fixture_mode','result_id','material_pin','material_selectors','inventory_review'}, ('result_id',))
    if type(parameters['fixture_mode']) is not bool or any(r['id']==parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused result ID required.')
    try:
        proof=reproduce_inventory(state,parameters['inventory_review'],parameters['result_id'],parameters['fixture_mode'])
    except (ValueError,TypeError,KeyError,OSError) as error:
        result={'id':parameters['result_id'],'skill':'assess-inventory-claim-evidence','contract_version':'0.1.0','status':'blocked',
            'review_states':list(dict.fromkeys(['ADVISORY','EVIDENCE_INCOMPLETE']+[r['state'] for r in state['review_requirements'] if r['status']=='open'])),
            'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],'evidence_ids':[],
            'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),
            'diagnostics':[{'code':'CLAIM_INVENTORY_REQUIRED','message':str(error)}],
            'next_actions':['Reconcile original inventory, full source lineage, explicit factors and claim coverage before review.']}
        result['data_gaps'].append({'id':result['id']+'-inventory-gap','field':'claim_inventory','reason':str(error),
            'impact':'Inventory substantiation is unavailable; no whole-subject, zero or neutral claim follows.','remedy':result['next_actions'][0]})
        if str(error).startswith('EMISSION_FACTOR_REQUIRED:') or any(d['code']=='EMISSION_FACTOR_REQUIRED' for r in state['results'] for d in r['diagnostics']):
            result['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Outstanding factor gaps remain; no defensible factor is inferred. '+str(error)})
    else:
        base={k:copy.deepcopy(v) for k,v in parameters.items() if k!='inventory_review'}
        result=assess_bound_claim(state,base,{proof['result']['id']:proof})['result']
        result['skill']='assess-inventory-claim-evidence'
        for d in result['diagnostics']:
            if d['code']=='CLAIM_EVIDENCE_REVIEW':
                report=json.loads(d['message']);report['execution_contract']='claim-evidence-0.3.0'
                d['message']=json.dumps(report,sort_keys=True)
        result['diagnostics'].append({'code':'CLAIM_INVENTORY_SOURCE_CHECK','message':json.dumps(proof,sort_keys=True)})
    result['diagnostics'].append({'code':'CLAIM_INVENTORY_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    return {'result':result,'proposal':propose(state,result,'Retain original material and reproduced inventory context; no neutrality or publication approval')}
