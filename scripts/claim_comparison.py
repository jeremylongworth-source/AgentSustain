"""Observed inventory-change evidence for original claims, without causal inference."""
import copy
import json

from .climate_tools import _fields, _sources, _date
from .contract_validation import validate_state
from .claim_inventory import reproduce_inventory, _check
from .claim_material import assess_bound_claim
from .ghg_inventory import _diagnostic
from .inventory_analysis import compare_inventories
from .state_proposal import propose


def reproduce_comparison(state, review, result_id, fixture_mode):
    _fields(review, {'comparison_result_id','prior_state','prior_inventory_review','current_inventory_review',
        'as_of_date','evidence_ids','evidence_fit','interpretation','quantity_interpretation','rationale','reviewer_role'},
        ('comparison_result_id','rationale','reviewer_role'))
    prior=review['prior_state'];validate_state(prior);_date(review['as_of_date'])
    if review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'} or review['interpretation'] not in {'observed_inventory_change','attributed_project_reduction','unknown'}:
        raise ValueError('Explicit evidence fitness and observed-versus-causal interpretation required.')
    if review['quantity_interpretation'] not in {'signed_change','decrease_magnitude','unknown'}:
        raise ValueError('Explicit signed-change, decrease-magnitude or unknown numerical interpretation required.')
    for key in ('data_gaps','review_requirements','assumptions'):
        if any(item not in state[key] for item in prior[key]):
            raise ValueError('Prior gaps, reviews and assumptions must remain in current state; comparison does not resolve them.')
    before=reproduce_inventory(prior,review['prior_inventory_review'],result_id+'-prior',fixture_mode)
    after=reproduce_inventory(state,review['current_inventory_review'],result_id+'-current',fixture_mode)
    source=next((r for r in state['results'] if r['id']==review['comparison_result_id']),None)
    if source is None or source['skill']!='compare-ghg-inventories' or source['status'] not in {'completed','partial'}:
        raise ValueError('Supported inventory comparison result required; no missing change or percentage inferred.')
    record=_diagnostic(source,'INVENTORY_COMPARISON')
    if record['prior_inventory_id']!=before['result']['id'] or record['current_inventory_id']!=after['result']['id']:
        raise ValueError('The comparison must bind both exact reviewed inventory selections.')
    verification_id=result_id+'-comparison-check'
    while any(r['id']==verification_id for r in state['results']):verification_id+='-next'
    checked=compare_inventories(state,prior,before['result']['id'],after['result']['id'],record['comparability_review'],verification_id,fixture_mode)['result']
    _check(state,source,checked,'INVENTORY_COMPARISON')
    evidence=_sources(state,review['evidence_ids'],set());when=review['as_of_date']
    fit=(before['source_fit'] and after['source_fit'] and review['evidence_fit']=='reviewed_supporting'
        and review['interpretation']=='observed_inventory_change' and review['quantity_interpretation']!='unknown' and bool(evidence)
        and review['prior_inventory_review']['as_of_date']==review['current_inventory_review']['as_of_date']==when
        and all(e['boundary_id']==state['organizational_boundary']['id'] and e['source']['version'] is not None and e['source']['accessed']<=when for e in evidence))
    return {'execution_contract':'claim-comparison-0.1.0','comparison_review':copy.deepcopy(review),
        'claim_inventory_review':copy.deepcopy(review['current_inventory_review']),'result':copy.deepcopy(source),
        'comparison_record':record,'prior_inventory':before,'current_inventory':after,'evidence_snapshots':evidence,
        'source_fit':bool(fit),'quantity_interpretation':review['quantity_interpretation'],
        'declared_scope_coverage_reproduced':bool(fit and before['declared_scope_coverage_reproduced'] and after['declared_scope_coverage_reproduced']),
        'project_causation_verified':False,'avoided_emissions_verified':False,'external_completeness_verified':False,
        'source_authenticity_verified':False,'publication_authorized':False}


def assess_comparison_claim(state, parameters):
    validate_state(state)
    _fields(parameters, {'claim','classification_review','criteria','claim_review','fixture_mode','result_id','material_pin','material_selectors','comparison_review'}, ('result_id',))
    if type(parameters['fixture_mode']) is not bool or any(r['id']==parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused result ID required.')
    try:
        proof=reproduce_comparison(state,parameters['comparison_review'],parameters['result_id'],parameters['fixture_mode'])
    except (ValueError,TypeError,KeyError,OSError) as error:
        result={'id':parameters['result_id'],'skill':'assess-comparison-claim-evidence','contract_version':'0.1.0','status':'blocked',
            'review_states':list(dict.fromkeys(['ADVISORY','EVIDENCE_INCOMPLETE']+[r['state'] for r in state['review_requirements'] if r['status']=='open'])),
            'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],'evidence_ids':[],
            'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),
            'diagnostics':[{'code':'CLAIM_COMPARISON_REQUIRED','message':str(error)}],
            'next_actions':['Reconcile original material, prior/current inventories, source lineage and comparability; keep causal attribution unresolved.']}
        result['data_gaps'].append({'id':result['id']+'-comparison-gap','field':'claim_comparison','reason':str(error),
            'impact':'Change substantiation is unavailable; no zero, percentage or project reduction is inferred.','remedy':result['next_actions'][0]})
        if str(error).startswith('EMISSION_FACTOR_REQUIRED:'):
            result['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':str(error)})
    else:
        base={k:copy.deepcopy(v) for k,v in parameters.items() if k!='comparison_review'}
        result=assess_bound_claim(state,base,{proof['result']['id']:proof})['result'];result['skill']='assess-comparison-claim-evidence'
        for d in result['diagnostics']:
            if d['code']=='CLAIM_EVIDENCE_REVIEW':
                r=json.loads(d['message']);r['execution_contract']='claim-evidence-0.4.0';d['message']=json.dumps(r,sort_keys=True)
        result['diagnostics'].append({'code':'CLAIM_COMPARISON_SOURCE_CHECK','message':json.dumps(proof,sort_keys=True)})
    result['diagnostics'].append({'code':'CLAIM_COMPARISON_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    return {'result':result,'proposal':propose(state,result,'Preserve original comparison claim, paired inventories and unknown attribution; no publication approval')}
