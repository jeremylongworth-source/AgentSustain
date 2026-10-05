"""Supplied ordinal interval priorities for investigation, without risk aggregation."""
import copy
from itertools import combinations

from .climate_tools import _fields, _reproduce, _reviewed, _sources, _support, _text
from .climate_assessment import _scope


def prioritize(state, parameters, refs, result, gap):
    source=_reproduce(state,parameters['register_result_id'],refs,'build-climate-risk-register')
    review=parameters['priority_review']; as_of=_reviewed(state,review,refs,'sourced_climate_priority')
    _scope(review,source['register_review'],as_of)
    model=parameters['model']
    _fields(model, {'id','name','version','evidence_ids','evidence_fit','criteria','priority_order'}, ('id','name','version'))
    model_sources=_sources(state,model['evidence_ids'],refs)
    if (not model_sources or model['evidence_fit']!='reviewed_supporting' or any(e['source']['version'] is None for e in model_sources)
            or not _text(review.get('model_fit_rationale'))):
        raise ValueError('Supporting versioned priority model and joint physical/transition applicability rationale required; no default scales.')
    criteria={}
    if not isinstance(model['criteria'],list) or not model['criteria']:
        raise ValueError('Explicit nonempty priority criteria required.')
    for criterion in model['criteria']:
        _fields(criterion, {'id','name','definition','levels'}, ('id','name','definition'))
        if criterion['id'] in criteria or not isinstance(criterion['levels'],list) or not criterion['levels']:
            raise ValueError('Distinct criterion IDs and nonempty ascending investigation-priority levels required.')
        levels=[]
        for level in criterion['levels']:
            _fields(level, {'id','label','definition'}, ('id','label','definition'))
            if level['id'] in levels: raise ValueError('Distinct ordinal level IDs within each criterion required.')
            levels.append(level['id'])
        criteria[criterion['id']]=levels
    order=model['priority_order']
    if not isinstance(order,list) or len(order)!=len(criteria) or set(order)!=set(criteria):
        raise ValueError('Explicit lexicographic order must cover every criterion exactly once; no weights or sums.')
    entries={e['id']:e for e in source['entries']}
    contexts=review.get('entry_contexts')
    if not isinstance(contexts,dict) or set(contexts)!=set(entries):
        raise ValueError('Actual source/priority fitness context for every current register entry required.')
    context_fit={}; context_sources={}
    for ident,entry in entries.items():
        context=contexts[ident]
        _fields(context, {'evidence_ids','evidence_fit','rationale'}, ('rationale',))
        context_sources[ident]=_sources(state,context['evidence_ids'],refs)
        if (not set(entry['source_evidence_ids']+entry['evidence_ids'])<=set(context['evidence_ids'])
                or context['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}):
            raise ValueError('Priority fitness must retain actual upstream and interpretation evidence, without source substitution.')
        context_fit[ident]=context['evidence_fit']=='reviewed_supporting'
        if not context_fit[ident]: gap(ident+': priority applicability/source context unverified; no default low priority.')
    raw=parameters['ratings']
    if not isinstance(raw,list): raise ValueError('Explicit per-entry/criterion rating list required.')
    ratings={}; bounds={}
    for rating in raw:
        _fields(rating, {'entry_id','criterion_id','lower_level_id','upper_level_id','evidence_ids','evidence_fit','observed_date','rationale','source_fragment','limitations'},
            ('entry_id','criterion_id','rationale','source_fragment','limitations'))
        key=rating['entry_id'],rating['criterion_id']
        if key in ratings or key[0] not in entries or key[1] not in criteria:
            raise ValueError('Distinct current entry/criterion ratings required.')
        levels=criteria[key[1]]; lower=rating['lower_level_id']; upper=rating['upper_level_id']
        if any(x is not None and x not in levels for x in (lower,upper)):
            raise ValueError('Priority bounds must be supplied level IDs or null; no physical-class/probability conversion.')
        if lower is not None and upper is not None and levels.index(lower)>levels.index(upper):
            raise ValueError('Priority interval reversed.')
        sources=_sources(state,rating['evidence_ids'],refs); fit=_support(rating,sources,as_of,gap,key[0]+' / '+key[1]) and context_fit[key[0]]
        complete=fit and lower is not None and upper is not None
        if not complete: gap(key[0]+' / '+key[1]+': priority bounds or source fitness unresolved; no endpoint choice or lowest default.')
        ratings[key]=dict(copy.deepcopy(rating),sources=sources,assessment_status='conditional_rating' if complete else 'unassessed')
        bounds[key]=(levels.index(lower),levels.index(upper)) if complete else None
    rows=[]; eligible=set()
    for ident,entry in entries.items():
        selected=[]
        for criterion in order:
            key=ident,criterion
            if key not in ratings: gap(ident+' / '+criterion+': priority rating omitted; concern remains unassessed, not ranked last.')
            else: selected.append(ratings[key])
        complete=all(bounds.get((ident,c)) is not None for c in order)
        if complete: eligible.add(ident)
        rows.append({'entry_id':ident,'entry_snapshot':copy.deepcopy(entry),'ratings':selected,
            'context_review':copy.deepcopy(contexts[ident]),'context_sources':context_sources[ident],
            'assessment_status':'conditional_investigation_priority' if complete else 'unassessed',
            'risk_rank':None,'priority_approved':False,'risk_accepted':False})
    pairs=[]; edges={ident:set() for ident in eligible}; incoming={ident:0 for ident in eligible}
    for left,right in combinations(sorted(entries),2):
        relation='unassessed'; decisive=None
        if left in eligible and right in eligible:
            relation='exact_tie'
            for criterion in order:
                a,b=bounds[left,criterion],bounds[right,criterion]
                if a[0]>b[1]: relation='left_definitely_precedes'; decisive=criterion; break
                if b[0]>a[1]: relation='right_definitely_precedes'; decisive=criterion; break
                if not a[0]==a[1]==b[0]==b[1]: relation='unresolved_overlap'; decisive=criterion; break
            if relation in {'left_definitely_precedes','right_definitely_precedes'}:
                before,after=(left,right) if relation.startswith('left') else (right,left)
                edges[before].add(after); incoming[after]+=1
        if relation in {'unassessed','unresolved_overlap'}:
            gap(left+' / '+right+': priority comparison unresolved; later criteria, IDs or favorable endpoints cannot force an order.')
        pairs.append({'left_entry_id':left,'right_entry_id':right,'relation':relation,'decisive_criterion_id':decisive})
    fronts=[]; remaining=set(eligible)
    while remaining:
        front=sorted(i for i in remaining if incoming[i]==0)
        if not front: raise ValueError('Inconsistent definite-priority graph; no order inferred.')
        fronts.append(front); remaining-=set(front)
        for ident in front:
            for after in edges[ident]: incoming[after]-=1
    gap('Supplied investigation-priority comparisons/fronts need qualified source/model and owner review; not verified risk ranks, accepted risks or an implementation sequence.')
    if not entries or not review['coverage_complete'] or review['exclusions']:
        gap('Selected priority coverage incomplete; no organization-wide ranking or clearance.')
    return {'register_snapshot':source,'model':copy.deepcopy(model),'model_sources':model_sources,'entries':rows,
        'pairwise_comparisons':pairs,'definite_precedence_fronts':fronts,'unassessed_entry_ids':sorted(set(entries)-eligible),
        'fronts_are_not_ties_or_complete_order':True,'priority_review':copy.deepcopy(review),'review_sources':_sources(state,review['evidence_ids'],refs),
        'risk_rank':None,'priority_approved':False,'risk_accepted':False,'implementation_authorized':False,'public_claim_authorized':False}
