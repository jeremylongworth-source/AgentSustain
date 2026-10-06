"""Proposed target/plan evidence for future claims; never delivered progress."""
import copy
import json

from .climate_tools import _fields, _date, _sources
from .contract_validation import validate_state
from .strategy_tools import _execute, _record, CODE
from .claim_material import assess_bound_claim, bind_material, _span
from .state_proposal import propose


class MaterialRequired(ValueError):
    pass


def _strategy(state, ident, skill):
    owner=next((r for r in state['results'] if r['id']==ident and r['skill']==skill),None)
    if owner is None or owner['status'] not in {'completed','partial'}:raise ValueError('Supported exact strategy source required.')
    checked,report=_execute(state,skill,_record(owner,'STRATEGY_INPUTS'))
    if any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in checked['diagnostics']):raise ValueError('EMISSION_FACTOR_REQUIRED: selected planning source retains missing factors.')
    if (report is None or checked['status']=='blocked' or report!=_record(owner,CODE[skill])
        or checked['metrics']!=owner['metrics'] or set(checked['evidence_ids'])!=set(owner['evidence_ids'])):
        raise ValueError('Full proposed source report, metrics/uncertainty and evidence lineage must reproduce.')
    return {'result':copy.deepcopy(owner),'report':report}


def reproduce_future_goal(state, review):
    _fields(review, {'transition_result_id','roadmap_result_id','pathway_id','target_result_id','target_period','as_of_date',
        'boundary_id','period','subject_id','evidence_ids','evidence_fit','interpretation','target_year_span','rationale','reviewer_role'},
        ('transition_result_id','roadmap_result_id','pathway_id','target_result_id','subject_id','rationale','reviewer_role'))
    if review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'} or review['interpretation'] not in {'proposed_target','committed_target','guaranteed_achievement','unknown'}:
        raise ValueError('Explicit source fitness and proposal/commitment/guarantee interpretation required.')
    transition=_strategy(state,review['transition_result_id'],'build-transition-plan')
    roadmap=_strategy(state,review['roadmap_result_id'],'build-implementation-roadmap')
    target=_strategy(state,review['target_result_id'],'develop-target')
    if roadmap['report']['transition_result_id']!=transition['result']['id']:
        raise ValueError('Roadmap must reference the selected transition, not an unrelated plan.')
    path=next((p for p in transition['report']['pathways'] if p['pathway']['id']==review['pathway_id']),None)
    if path is None or path['pathway']['target_result_id']!=target['result']['id'] or path['checkpoints'][-1]['references']['target_result_id']!=target['result']['id']:
        raise ValueError('Exact pathway/final checkpoint/target binding required.')
    if review['target_period']!=target['report']['target']['period'] or path['checkpoints'][-1]['target_snapshot']!=target['report']:
        raise ValueError('The stated goal period and source target must match; planned dates are not evidence periods.')
    when=_date(review['as_of_date']);sources=[transition,roadmap,target];refs=set(review['evidence_ids'])
    for source in sources:refs.update(source['result']['evidence_ids'])
    evidence=_sources(state,sorted(refs),set())
    fit=(bool(review['evidence_ids']) and review['evidence_fit']=='reviewed_supporting' and review['interpretation']=='proposed_target'
        and review['subject_id']==state['organization']['id'] and review['boundary_id']==state['organizational_boundary']['id']
        and review['period']==state['reporting_period'] and when<=_date(transition['report']['plan']['review_date'])
        and when<=_date(roadmap['report']['roadmap']['review_date'])
        and transition['report']['transition_review']['as_of_date']==roadmap['report']['implementation_review']['as_of_date']==review['as_of_date']
        and all(e['boundary_id']==review['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in evidence))
    monitoring=[m for m in transition['report']['milestones'] if m['proposal']['kind']=='monitoring']
    return {'execution_contract':'claim-future-goal-0.1.0','goal_review':copy.deepcopy(review),'sources':sources,
        'pathway':copy.deepcopy(path),'evidence_snapshots':evidence,'source_fit':bool(fit),
        'delivery_screen':roadmap['report']['delivery_screen'],'known_unmet_conditions':copy.deepcopy(roadmap['report']['known_unmet_conditions']),
        'unresolved_conditions':copy.deepcopy(roadmap['report']['unresolved_conditions']),'monitoring_proposals':monitoring,
        'observed_progress':None,'progress_verified':False,'target_adoption_verified':False,'future_performance_guaranteed':False,
        'funding_or_implementation_authorized':False,'absolute_emissions_reduction_verified':False,'publication_authorized':False}


def assess_future_goal_claim(state, parameters):
    validate_state(state)
    _fields(parameters, {'claim','classification_review','criteria','claim_review','fixture_mode','result_id','material_pin','material_selectors','goal_review'}, ('result_id',))
    if type(parameters['fixture_mode']) is not bool or any(r['id']==parameters['result_id'] for r in state['results']):raise ValueError('Explicit fixture mode and unused result ID required.')
    try:
        proof=reproduce_future_goal(state,parameters['goal_review'])
        base={k:copy.deepcopy(v) for k,v in parameters.items() if k!='goal_review'}
        try:
            binding=bind_material(state,base);span=parameters['goal_review']['target_year_span'];claim_span=base['material_selectors']['claim_span']
            year=_span(binding['material_snapshot']['text'],span);target_period=parameters['goal_review']['target_period']
            text=binding['material_snapshot']['text']
            if (span['start'] and (text[span['start']-1].isalnum() or text[span['start']-1] in '-_/.:–—')
                or span['end']<len(text) and (text[span['end']].isalnum() or text[span['end']] in '-_/:–—'
                    or text[span['end']]=='.' and span['end']+1<len(text) and text[span['end']+1].isdigit())):
                raise ValueError('Goal year selector cannot truncate a larger year, date or range token.')
            if (target_period!={'start':year+'-01-01','end':year+'-12-31'} or len(year)!=4 or not year.isascii() or not year.isdigit()
                or not claim_span['start']<=span['start']<span['end']<=claim_span['end']):
                raise ValueError('Literal goal year inside original statement must bind the exact annual target period; no implied or different deadline.')
        except (ValueError,TypeError,KeyError,OSError) as error:
            raise MaterialRequired(str(error)) from error
        if not parameters['fixture_mode'] and any(e['source']['locator'].startswith('fixture:') for e in proof['evidence_snapshots']):proof['source_fit']=False
    except (ValueError,TypeError,KeyError,OSError) as error:
        result={'id':parameters['result_id'],'skill':'assess-future-goal-claim-evidence','contract_version':'0.1.0','status':'blocked',
            'review_states':list(dict.fromkeys(['ADVISORY','EVIDENCE_INCOMPLETE']+[r['state'] for r in state['review_requirements'] if r['status']=='open'])),
            'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],'evidence_ids':[],
            'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),
            'diagnostics':[{'code':'CLAIM_MATERIAL_REQUIRED' if isinstance(error,MaterialRequired) else 'CLAIM_FUTURE_GOAL_REQUIRED','message':str(error)}],'next_actions':['Reconcile original proposal/target/period and source lineage; obtain actual progress and qualified owner review.']}
        result['data_gaps'].append({'id':result['id']+'-future-gap','field':'future_goal','reason':str(error),'impact':'No commitment, future delivery or measured progress follows.','remedy':result['next_actions'][0]})
        if str(error).startswith('EMISSION_FACTOR_REQUIRED:'):result['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':str(error)})
    else:
        base={k:copy.deepcopy(v) for k,v in parameters.items() if k!='goal_review'}
        context={s['result']['id']:proof for s in proof['sources']}
        result=assess_bound_claim(state,base,context)['result'];result['skill']='assess-future-goal-claim-evidence'
        for d in result['diagnostics']:
            if d['code']=='CLAIM_EVIDENCE_REVIEW':
                report=json.loads(d['message']);report['execution_contract']='claim-evidence-0.5.0';d['message']=json.dumps(report,sort_keys=True)
        result['diagnostics'].append({'code':'CLAIM_FUTURE_GOAL_SOURCE_CHECK','message':json.dumps(proof,sort_keys=True)})
    result['diagnostics'].append({'code':'CLAIM_FUTURE_GOAL_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    return {'result':result,'proposal':propose(state,result,'Preserve original future goal and reproduced proposals; no progress, guarantee or publication approval')}
