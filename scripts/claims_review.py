"""Evidence-linked claim review candidates, never legal or publication approval."""
import copy
import hashlib
import json

from .climate_tools import _date, _fields, _sources, _text
from .contract_validation import validate_state
from .data_tools import number
from .gas_mass import calculate_gas_mass
from .gas_conversion import _diagnostic, convert_gas_mass
from .gas_ledger import build_gas_ledger
from .state_proposal import propose


KINDS = {'quantified','factual_content','comparative','carbon_neutral','net_zero','future_goal','general_benefit','mixed','unknown'}
BASE = {'evidence','boundary','period','method','qualifications','general_impression','jurisdiction'}
EXTRA = {'quantified':{'quantity'}, 'factual_content':{'quantity'}, 'comparative':{'baseline','comparability'},
         'carbon_neutral':{'inventory','reductions','credits','residuals'}, 'net_zero':{'inventory','reductions','credits','residuals'},
         'future_goal':{'plan','progress'}}
REPLAY = {'calculate-gas-mass':(calculate_gas_mass,'GAS_MASS_INPUTS','GAS_MASS_CALCULATION'),
          'convert-gas-mass-to-co2e':(convert_gas_mass,'GAS_CO2E_INPUTS','GAS_CO2E_CONVERSION'),
          'build-facility-gas-ledger':(build_gas_ledger,'GAS_LEDGER_INPUTS','FACILITY_GAS_LEDGER')}


def _reproduce(state, owner, result_id):
    if owner['skill'] not in REPLAY or owner['status'] != 'partial':
        return None
    fn, inputs_code, report_code = REPLAY[owner['skill']]
    args = _diagnostic(owner, inputs_code); args = copy.deepcopy(args)
    args['result_id'] = result_id + '-source-check'
    while any(r['id']==args['result_id'] for r in state['results']): args['result_id'] += '-next'
    checked = fn(state,args)['result']; metrics=copy.deepcopy(checked['metrics'])
    for m in metrics:m['id']=m['id'].replace(args['result_id'],owner['id'],1)
    report=_diagnostic(owner,report_code)
    if (checked['status']!=owner['status'] or metrics!=owner['metrics']
        or set(checked['evidence_ids'])!=set(owner['evidence_ids']) or _diagnostic(checked,report_code)!=report):
        raise ValueError('Complete claim-source quantities, metadata, uncertainty, method/report and lineage must reproduce.')
    return report


def assess_claim(state, parameters, inventory_sources=None):
    validate_state(state)
    _fields(parameters, {'claim','classification_review','criteria','claim_review','fixture_mode','result_id'}, ('result_id',))
    if type(parameters['fixture_mode']) is not bool or any(r['id']==parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused claim result ID required.')
    result={'id':parameters['result_id'],'skill':'assess-claim-evidence','contract_version':'0.1.0','status':'partial',
        'review_states':['ADVISORY'],'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],
        'evidence_ids':[],'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),
        'diagnostics':[],'next_actions':[]}
    refs=set()
    def gap(message,code='CLAIM_EVIDENCE_REQUIRED'):
        result['data_gaps'].append({'id':result['id']+'-gap-'+str(len(result['data_gaps'])),'field':'claim_evidence',
            'reason':message,'impact':'Claim scope or substantiation is incomplete/unverified; no stronger marketing statement follows.',
            'remedy':'Inspect the original material, reconcile scoped evidence and obtain qualified claim/legal/owner review.'})
        result['diagnostics'].append({'code':code,'message':message})
    try:
        claim=parameters['claim'];review=parameters['claim_review'];classification=parameters['classification_review']
        _fields(claim, {'id','text','kind','subject_kind','subject_id','scope','period','boundary_id','material_evidence_ids',
            'representation_dates','channel','audience','purpose','qualifications'},
            ('id','text','kind','subject_kind','subject_id','scope','channel','audience','purpose'))
        _fields(review, {'boundary_id','period','as_of_date','evidence_ids','evidence_fit','scope','rationale','reviewer_role'},
            ('scope','rationale','reviewer_role'))
        when=_date(review['as_of_date']);review_sources=_sources(state,review['evidence_ids'],refs)
        if claim['kind'] not in KINDS or claim['subject_kind'] not in {'organization','facility','product'} or claim['scope'] not in {'whole_subject','selected_sources','unknown'}:
            raise ValueError('Explicit supported claim kind, subject and scope required; no text classification inferred.')
        if (claim['boundary_id']!=state['organizational_boundary']['id'] or review['boundary_id']!=claim['boundary_id']
            or claim['period']!=state['reporting_period'] or review['period']!=claim['period']):
            raise ValueError('Matched organization boundary and evidence/reporting period required.')
        if claim['subject_kind']=='facility' and claim['subject_id'] not in state['organizational_boundary']['facility_ids']:
            raise ValueError('Selected claim facility must be in the current boundary.')
        if claim['subject_kind']=='organization' and claim['subject_id']!=state['organization']['id']:
            raise ValueError('Selected claim organization must match current state.')
        if not isinstance(claim['representation_dates'],list) or len(set(claim['representation_dates']))!=len(claim['representation_dates']) or any(_date(d)>when for d in claim['representation_dates']):
            raise ValueError('Distinct nonfuture representation dates required, separate from evidence period.')
        if not isinstance(claim['qualifications'],list) or any(not _text(q) for q in claim['qualifications']):
            raise ValueError('Explicit original qualification list required; no marketing rewrite.')
        material=_sources(state,claim['material_evidence_ids'],refs)
        _fields(classification, {'kind','evidence_ids','evidence_fit','rationale','reviewer_role'}, ('kind','rationale','reviewer_role'))
        _sources(state,classification['evidence_ids'],refs)
        if classification['kind']!=claim['kind'] or not set(classification['evidence_ids'])<=set(claim['material_evidence_ids']):
            raise ValueError('Classification must bind the unchanged original material and declared kind.')
        fits={'reviewed_supporting','unverified','irrelevant'}
        if review['evidence_fit'] not in fits or classification['evidence_fit'] not in fits:
            raise ValueError('Explicit assessment/classification source fitness required.')
        current=lambda es:bool(es) and all(e['boundary_id']==claim['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in es)
        context_fit=(current(material) and current(review_sources) and bool(claim['representation_dates'])
            and all(_date(e['period']['start'])<=_date(d)<=_date(e['period']['end']) for e in material for d in claim['representation_dates'])
            and review['evidence_fit']=='reviewed_supporting' and classification['evidence_fit']=='reviewed_supporting'
            and bool(classification['evidence_ids']) and claim['kind'] not in {'unknown','mixed'} and claim['scope']!='unknown')
        if not parameters['fixture_mode'] and any(e['source']['locator'].startswith('fixture:') for e in material+review_sources):
            context_fit=False;gap('Fictional material/assessment cannot support real claims.')
        if not context_fit:gap('Original material, representation dates, scope/classification or current source fitness remains unverified.')
        if not isinstance(parameters['criteria'],list):raise ValueError('Explicit criterion review list required.')
        required=BASE|EXTRA.get(claim['kind'],set())
        if inventory_sources is not None and claim['scope']=='whole_subject':required=required|{'inventory'}
        comparison_ids={i for i,v in (inventory_sources or {}).items() if v.get('execution_contract')=='claim-comparison-0.1.0'}
        future_ids={i for i,v in (inventory_sources or {}).items() if v.get('execution_contract')=='claim-future-goal-0.1.0'}
        if comparison_ids:
            required=required|{'quantity'}
        if future_ids:required=required|{'quantity'}
        seen=set();rows=[];cache={}
        for criterion in parameters['criteria']:
            _fields(criterion, {'id','assertion','boundary_id','period','unit','evidence_ids','source_result_ids','evidence_fit',
                'verdict','quantity','qualifications','qualification_visible','rationale'}, ('id','assertion','unit','rationale'))
            if criterion['id'] in seen or criterion['id'] not in required or criterion['evidence_fit'] not in fits or criterion['verdict'] not in {'supports','qualified','unknown','contradicts'}:
                raise ValueError('Distinct applicable criteria, explicit source fitness and supported observation verdict required.')
            seen.add(criterion['id']);evidence=_sources(state,criterion['evidence_ids'],refs)
            if not isinstance(criterion['source_result_ids'],list) or len(set(criterion['source_result_ids']))!=len(criterion['source_result_ids']) or any(not _text(i) for i in criterion['source_result_ids']):
                raise ValueError('Distinct current source result references required.')
            if type(criterion['qualification_visible']) is not bool or not isinstance(criterion['qualifications'],list) or any(not _text(q) for q in criterion['qualifications']):
                raise ValueError('Explicit qualification prominence and original qualification strings required.')
            fit=context_fit and current(evidence) and criterion['evidence_fit']=='reviewed_supporting' and criterion['boundary_id']==claim['boundary_id'] and criterion['period']==claim['period']
            if comparison_ids and criterion['id'] in {'quantity','baseline','comparability','inventory'}:
                fit=fit and len(criterion['source_result_ids'])==1 and criterion['source_result_ids'][0] in comparison_ids
            if future_ids and criterion['id'] in {'quantity','plan','progress'}:
                fit=fit and len(criterion['source_result_ids'])==1 and criterion['source_result_ids'][0] in future_ids
            if not parameters['fixture_mode'] and any(e['source']['locator'].startswith('fixture:') for e in evidence):fit=False
            sources=[]
            for ident in criterion['source_result_ids']:
                owner=next((r for r in state['results'] if r['id']==ident),None)
                if owner is None:raise ValueError('Every selected claim source result must resolve.')
                refs.update(owner['evidence_ids'])
                if ident not in cache:
                    cache[ident]=(inventory_sources.get(ident) if inventory_sources is not None and owner['skill'] in {'build-ghg-inventory','compare-ghg-inventories','develop-target','build-transition-plan','build-implementation-roadmap'}
                                  else _reproduce(state,owner,result['id']))
                record=cache[ident];sources.append({'result':copy.deepcopy(owner),'reproduced_report':copy.deepcopy(record)})
                if record is None or owner['status']=='blocked':
                    fit=False
                    if any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in owner['diagnostics']):gap('Selected claim source has no defensible factor.','EMISSION_FACTOR_REQUIRED')
                elif ident not in future_ids and any(m['period']!=claim['period'] or m['boundary_id']!=claim['boundary_id'] for m in owner['metrics']):fit=False
                if record and ident in future_ids:
                    fit=fit and record['source_fit'] and claim['kind']=='future_goal' and claim['subject_kind']=='organization' and claim['subject_id']==state['organization']['id'] and claim['scope']=='selected_sources'
                    fit=fit and record['goal_review']['as_of_date']==review['as_of_date']
                    if criterion['id']=='quantity':fit=fit and owner['id']==record['goal_review']['target_result_id']
                    elif criterion['id']=='plan':fit=fit and owner['skill'] in {'build-transition-plan','build-implementation-roadmap'}
                    elif criterion['id']=='progress':fit=False  # Proposed checkpoints/acceptance are not observed performance.
                elif record and owner['skill'] in {'build-ghg-inventory','compare-ghg-inventories'}:
                    fit=fit and record['source_fit'] and claim['subject_kind']=='organization' and claim['subject_id']==state['organization']['id']
                    fit=fit and record['claim_inventory_review']['as_of_date']==review['as_of_date']
                    if claim['scope']=='whole_subject':fit=fit and record['declared_scope_coverage_reproduced']
                    elif claim['scope']!='selected_sources':fit=False
                elif record:
                    date_key={'calculate-gas-mass':'applicability_review','convert-gas-mass-to-co2e':'conversion_review',
                              'build-facility-gas-ledger':'ledger_review'}[owner['skill']]
                    if record[date_key]['as_of_date']!=review['as_of_date']:fit=False
                if record and owner['skill']=='build-facility-gas-ledger':
                    if (claim['subject_kind']!='facility' or record['ledger_review']['facility_id']!=claim['subject_id']
                        or claim['scope']!='selected_sources' or not record['declared_coverage_reproduced']):fit=False
                elif record and ident not in future_ids and owner['skill'] not in {'build-ghg-inventory','compare-ghg-inventories'} and (claim['subject_kind']!='organization' or claim['scope']!='selected_sources'):
                    fit=False  # Raw gas results have organization-bound activity, not a product/facility attribution bridge.
                if record and ident not in future_ids and owner['skill'] not in {'build-ghg-inventory','compare-ghg-inventories'} and not parameters['fixture_mode']:
                    inputs_code=REPLAY[owner['skill']][1]
                    if _diagnostic(owner,inputs_code)['fixture_mode']:fit=False
            if criterion['source_result_ids']:
                fit=fit and bool(sources) and all(s['reproduced_report'] is not None and
                    (criterion['unit']=='1' if s['result']['id'] in future_ids and criterion['id'] in {'plan','progress'} else any(m['unit']==criterion['unit'] for m in s['result']['metrics'])) for s in sources)
                fit=fit and all(set(criterion['evidence_ids']) & set(s['result']['evidence_ids']) for s in sources)
            else:
                fit=fit and all(e['unit']==criterion['unit'] and _date(e['period']['start'])<=_date(claim['period']['start']) and _date(e['period']['end'])>=_date(claim['period']['end']) for e in evidence)
            if criterion['id']=='quantity' and not criterion['source_result_ids']:fit=False
            quantity_mismatch=False
            if criterion['quantity'] is not None:
                _fields(criterion['quantity'], {'metric_id','expected_value'}, ('metric_id',))
                selected_metrics=[m for s in sources for m in s['result']['metrics'] if m['id']==criterion['quantity']['metric_id']]
                if len(selected_metrics)!=1 or criterion['quantity']['expected_value'] is None:fit=False
                else:
                    expected_value=number(criterion['quantity']['expected_value'])
                    if any(s['reproduced_report'] and s['reproduced_report'].get('quantity_interpretation')=='decrease_magnitude'
                           and any(m['id']==criterion['quantity']['metric_id'] for m in s['result']['metrics']) for s in sources):
                        if expected_value<0:fit=False
                        expected_value=-expected_value  # Explicit supplied direction, never a text-derived polarity guess.
                    quantity_mismatch=expected_value!=number(selected_metrics[0]['value'])
                    fit=fit and selected_metrics[0]['unit']==criterion['unit']
            elif criterion['id']=='quantity':fit=False
            if criterion['id']=='inventory':
                fit=fit and inventory_sources is not None and len(sources)==1 and sources[0]['result']['skill'] in {'build-ghg-inventory','compare-ghg-inventories'} and bool(sources[0]['reproduced_report']) and sources[0]['reproduced_report']['declared_scope_coverage_reproduced']
            if inventory_sources is not None and criterion['id'] in {'reductions','credits','residuals'}:
                fit=False  # Inventory arithmetic supplies none of these distinct substantiation methods.
            if criterion['id']=='jurisdiction':fit=False  # Core assessment never determines legal applicability.
            state_name='INSUFFICIENT_EVIDENCE'
            if criterion['id']=='jurisdiction':state_name='PROFESSIONAL_REVIEW_REQUIRED'
            elif fit and (criterion['verdict']=='contradicts' or quantity_mismatch):state_name='POTENTIALLY_MISLEADING'
            elif fit and criterion['verdict']=='supports':state_name='SUPPORTED'
            elif fit and criterion['verdict']=='qualified' and criterion['qualifications'] and criterion['qualification_visible'] and set(criterion['qualifications'])<=set(claim['qualifications']):state_name='SUPPORTED_WITH_QUALIFICATION'
            if state_name=='INSUFFICIENT_EVIDENCE':gap(criterion['id']+': evidence/context/method or visible qualification is insufficient; no support inferred.')
            recorded_sources=copy.deepcopy(sources)
            for s in recorded_sources:
                proof=s['reproduced_report']
                if proof and proof.get('execution_contract') in {'claim-comparison-0.1.0','claim-future-goal-0.1.0'}:
                    s['reproduced_report']={'execution_contract':proof['execution_contract'],'source_result_id':s['result']['id'],
                        'diagnostic_code':'CLAIM_FUTURE_GOAL_SOURCE_CHECK' if s['result']['id'] in future_ids else 'CLAIM_COMPARISON_SOURCE_CHECK',
                        'sha256':hashlib.sha256(json.dumps(proof,sort_keys=True).encode('utf-8')).hexdigest()}
            rows.append({'criterion':copy.deepcopy(criterion),'source_snapshots':evidence,'source_results':recorded_sources,'assessment_state':state_name,'source_fit':fit,'quantity_mismatch':quantity_mismatch})
        for ident in sorted(required-seen):
            gap(ident+': required criterion was not assessed.');rows.append({'criterion':{'id':ident},'source_snapshots':[],'source_results':[],'assessment_state':'INSUFFICIENT_EVIDENCE','source_fit':False})
        states=[r['assessment_state'] for r in rows]
        aggregate=('POTENTIALLY_MISLEADING' if 'POTENTIALLY_MISLEADING' in states else 'INSUFFICIENT_EVIDENCE' if 'INSUFFICIENT_EVIDENCE' in states else 'PROFESSIONAL_REVIEW_REQUIRED')
        report={'execution_contract':'claim-evidence-0.1.0','claim_snapshot':copy.deepcopy(claim),'material_source_snapshots':material,
            'classification_review':copy.deepcopy(classification),'claim_review':copy.deepcopy(review),'assessment_source_snapshots':review_sources,
            'required_criteria':sorted(required),'rows':rows,'claim_state':aggregate,'legal_applicability_determined':False,
            'source_authenticity_verified':False,'publication_authorized':False,'marketing_text_changed':False,'professional_judgments_authenticated':False}
        result['diagnostics'].append({'code':'CLAIM_EVIDENCE_REVIEW','message':json.dumps(report,sort_keys=True)})
        result['review_requirements'].append({'id':result['id']+'-claim-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
            'reason':'Review original claim/general impression, criterion completeness, evidence fit, classification and qualifications.',
            'scope':review['scope'],'reviewer_role':review['reviewer_role'],'status':'open','resolution':None})
        result['review_requirements'].append({'id':result['id']+'-legal-review','state':'LEGAL_REVIEW_REQUIRED',
            'reason':'Select actual jurisdiction/source editions and representation context; no legal or public claim approval inferred.',
            'scope':review['scope'],'reviewer_role':'Qualified jurisdiction/claims legal reviewer','status':'open','resolution':None})
    except (ValueError,TypeError,KeyError,OSError) as error:
        result['status']='blocked';gap(str(error))
    result['evidence_ids']=sorted(refs)
    result['diagnostics'].append({'code':'CLAIM_REVIEW_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    result['review_states']=list(dict.fromkeys(result['review_states']+[r['state'] for r in result['review_requirements'] if r['status']=='open']+['EVIDENCE_INCOMPLETE']))
    result['next_actions']=list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result':result,'proposal':propose(state,result,'Preserve original claim and scoped evidence/unknowns; no stronger wording, legal or publication approval')}
