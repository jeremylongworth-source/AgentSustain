"""Source-reproduced climate-risk register with distinct characterization bases."""
import copy

from .climate_tools import _date, _fields, _reproduce, _reviewed, _sources, _support, _text


def build(state, parameters, refs, result, gap):
    review=parameters['register_review']; as_of=_reviewed(state,review,refs,'source_climate_register')
    selected={}; records={}; snapshots=[]
    for field,skill,kind,review_key,rows_key in [
            ('physical_results','score-physical-risk','physical','risk_review','risks'),
            ('transition_results','assess-transition-exposure','transition','exposure_review','observations')]:
        ids=parameters[field]
        if not isinstance(ids,list) or any(not _text(i) for i in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Explicit distinct current physical/transition result IDs required.')
        if not ids:
            gap(kind+': assessment family omitted; organization risk coverage unknown.')
        for ident in ids:
            if ident in selected:
                raise ValueError('Each selected result must have one physical or transition basis.')
            source=_reproduce(state,ident,refs,skill)
            if _date(source[review_key]['as_of_date'])>as_of:
                raise ValueError('Register review cannot predate a selected source review.')
            owner=next(r for r in state['results'] if r['id']==ident)
            selected[ident]=(kind,source[review_key]['scope'],owner['evidence_ids'])
            snapshots.append({'result_id':ident,'kind':kind,'snapshot':source})
            for row in source[rows_key]: records[ident,row['id']]=(kind,row)
    contexts=review.get('source_contexts')
    if not isinstance(contexts,dict) or set(contexts)!=set(selected):
        raise ValueError('Scope/fitness review for every actual selected source result required.')
    scope_fit={}
    for ident,(kind,scope,evidence) in selected.items():
        context=contexts[ident]
        _fields(context, {'scope','evidence_ids','evidence_fit','rationale'}, ('scope','rationale'))
        _sources(state,context['evidence_ids'],refs)
        if (context['scope']!=scope or set(context['evidence_ids'])!=set(evidence)
                or context['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}):
            raise ValueError('Source contexts must retain exact original scope and actual source evidence.')
        scope_fit[ident]=context['evidence_fit']=='reviewed_supporting'
        if not scope_fit[ident]: gap(ident+': source inclusion/applicability fitness unresolved; retained without verified organization coverage.')
    raw=parameters['entries']
    if not isinstance(raw,list): raise ValueError('Explicit source-linked register entry list required.')
    entries=[]; ids=set(); pairs=set(); followups=set(); usage={}
    for entry in raw:
        _fields(entry, {'id','source_result_id','source_record_id','interpretation','owner','follow_ups','evidence_ids',
            'evidence_fit','observed_date','source_fragment','limitations'},
            ('id','source_result_id','source_record_id','interpretation','source_fragment','limitations'))
        key=entry['source_result_id'],entry['source_record_id']
        if entry['id'] in ids or key in pairs or key not in records:
            raise ValueError('Distinct known source-record entries required; no duplicate risk counting.')
        ids.add(entry['id']); pairs.add(key); kind,row=records[key]
        sources=_sources(state,entry['evidence_ids'],refs)
        supported=_support(entry,sources,as_of,gap,entry['id']) and scope_fit[key[0]]
        owner=entry['owner']
        _fields(owner, {'name','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'}, ('name','source_fragment','limitations'))
        owner_sources=_sources(state,owner['evidence_ids'],refs)
        owner_fit=_support(owner,owner_sources,as_of,gap,entry['id']+' owner')
        raw_follow=entry['follow_ups']
        if not isinstance(raw_follow,list): raise ValueError('Explicit proposed follow-up list required.')
        proposed=[]
        for action in raw_follow:
            _fields(action, {'id','action','owner','target_date','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
                ('id','action','owner','source_fragment','limitations'))
            if action['id'] in followups: raise ValueError('Distinct register follow-up IDs required.')
            followups.add(action['id']); action_sources=_sources(state,action['evidence_ids'],refs)
            _support(action,action_sources,as_of,gap,action['id'])
            when=_date(action['target_date']) if action['target_date'] is not None else None
            if when is None or when<as_of: gap(action['id']+': follow-up date unknown or overdue; completion not inferred.')
            proposed.append(dict(copy.deepcopy(action),sources=action_sources,status='proposed_pending_review',
                owner_accepted=False,started=False,completed=False,implementation_authorized=False))
        if not proposed: gap(entry['id']+': no owned investigation/response follow-up supplied; risk remains unresolved.')
        for evidence_id in sorted(set(entry['evidence_ids']+selected[key[0]][2])):
            usage.setdefault(evidence_id,[]).append(entry['id'])
        gap(entry['id']+': owner acceptance, source characterization and qualified climate/domain review remain open; no accepted or mitigated risk.')
        entries.append(dict(copy.deepcopy(entry),kind=kind,source_scope=selected[key[0]][1],characterization=copy.deepcopy(row),
            source_evidence_ids=copy.deepcopy(selected[key[0]][2]),
            sources=sources,owner_sources=owner_sources,owner_source_support='source_owner_candidate' if owner_fit else 'unverified',
            interpreted_source_support='source_interpretation_candidate' if supported else 'unverified',follow_up_proposals=proposed,
            status='registered_pending_review',owner_accepted=False,risk_verified=False,risk_accepted=False,risk_mitigated=False))
    for ident,record in sorted(set(records)-pairs): gap(ident+' / '+record+': selected source risk omitted from register; not absent or accepted.')
    raw=parameters['interactions']
    if not isinstance(raw,list): raise ValueError('Explicit proposed interaction list required.')
    interactions=[]; interaction_ids=set()
    for note in raw:
        _fields(note, {'id','entry_ids','kind','mechanism','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
            ('id','mechanism','source_fragment','limitations'))
        links=note['entry_ids']
        if (note['id'] in interaction_ids or not isinstance(links,list) or len(links)<2 or len(set(links))!=len(links)
                or not set(links)<=ids or note['kind'] not in {'common_driver','shared_asset','dependency','response_tradeoff','unknown'}):
            raise ValueError('Distinct interaction IDs with at least two current entry links and explicit kind required.')
        interaction_ids.add(note['id']); sources=_sources(state,note['evidence_ids'],refs)
        _support(note,sources,as_of,gap,note['id'])
        gap(note['id']+': interaction/scenario compatibility and double counting require qualified review; no joint probability or aggregate effect.')
        interactions.append(dict(copy.deepcopy(note),sources=sources,status='hypothesis_pending_review',interaction_verified=False,aggregate_effect=None))
    if not interactions: gap('Interactions and shared-asset/common-driver effects unassessed; absence of notes is not independence.')
    if not entries or not review['coverage_complete'] or review['exclusions']:
        gap('Selected climate register coverage incomplete; no complete organization risk register or clearance.')
    return {'source_snapshots':snapshots,'entries':entries,'interactions':interactions,'source_usage':usage,
        'register_review':copy.deepcopy(review),'review_sources':_sources(state,review['evidence_ids'],refs),
        'shared_sources_non_additive':True,'combined_score':None,'aggregate_loss':None,'coverage_verified':False,
        'risk_accepted':False,'implementation_authorized':False,'public_claim_authorized':False}
