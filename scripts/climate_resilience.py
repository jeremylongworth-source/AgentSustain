"""Source-linked resilience work proposals; no demonstrated resilience or action authority."""
import copy
import json

from .climate_tools import _date, _fields, _reproduce, _reviewed, _sources, _support, _text, _window
from .climate_assessment import _scope
from .climate_risk import _observations


def _ids(value, known, label, nonempty=False):
    if (not isinstance(value,list) or any(not _text(x) for x in value)
            or len(set(value))!=len(value) or not set(value)<=set(known) or (nonempty and not value)):
        raise ValueError('Distinct current '+label+' IDs required.')


def develop(state, parameters, refs, result, gap):
    priority=_reproduce(state,parameters['priority_result_id'],refs,'prioritize-climate-risks')
    review=parameters['resilience_review']; as_of=_reviewed(state,review,refs,'sourced_resilience_proposal')
    _scope(review,priority['priority_review'],as_of)
    entries={e['id']:e for e in priority['register_snapshot']['entries']}
    priority_rows={e['entry_id']:e for e in priority['entries']}
    contexts=review.get('entry_contexts')
    if not isinstance(contexts,dict) or set(contexts)!=set(entries):
        raise ValueError('Resilience applicability context for every actual register entry required.')
    context_fit={}; context_sources={}
    for ident,entry in entries.items():
        c=contexts[ident]; _fields(c, {'evidence_ids','evidence_fit','rationale'}, ('rationale',))
        context_sources[ident]=_sources(state,c['evidence_ids'],refs)
        if (not set(entry['source_evidence_ids']+entry['evidence_ids'])<=set(c['evidence_ids'])
                or c['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}):
            raise ValueError('Resilience context must retain actual upstream and interpretation evidence.')
        context_fit[ident]=c['evidence_fit']=='reviewed_supporting'
        if not context_fit[ident]: gap(ident+': resilience applicability unresolved; concern remains in plan coverage.')
    _ids(parameters['adaptation_result_ids'],{r['id'] for r in state['results']},'adaptation result')
    adaptation_contexts=review.get('adaptation_contexts')
    if not isinstance(adaptation_contexts,dict) or set(adaptation_contexts)!=set(parameters['adaptation_result_ids']):
        raise ValueError('Exact selected adaptation applicability contexts required.')
    adaptations={}; snapshots=[]; adaptation_fit={}
    for ident in parameters['adaptation_result_ids']:
        source=_reproduce(state,ident,refs,'identify-adaptation-options')
        owner=next(r for r in state['results'] if r['id']==ident)
        c=adaptation_contexts[ident]
        _fields(c, {'scope','evidence_ids','evidence_fit','rationale'}, ('scope','rationale'))
        _sources(state,c['evidence_ids'],refs)
        if (c['scope']!=source['adaptation_review']['scope'] or set(c['evidence_ids'])!=set(owner['evidence_ids'])
                or as_of<_date(source['adaptation_review']['as_of_date'])
                or c['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}):
            raise ValueError('Retain exact adaptation scope/evidence and current review date.')
        adaptation_fit[ident]=c['evidence_fit']=='reviewed_supporting'
        if not adaptation_fit[ident]: gap(ident+': adaptation inclusion/applicability unresolved; no verified response.')
        inputs=next(d for d in owner['diagnostics'] if d['code']=='CLIMATE_INPUTS')
        risk_result_id=json.loads(inputs['message'])['risk_result_id']
        for option in source['options']:
            adaptations[ident,option['id']]=(risk_result_id,option)
        snapshots.append({'result_id':ident,'snapshot':source})
    raw=parameters['actions']
    if not isinstance(raw,list): raise ValueError('Explicit resilience action list required.')
    actions=[]; ids=set(); covered=set()
    for action in raw:
        _fields(action, {'id','name','kind','entry_ids','adaptation_links','objective','mechanism','effectiveness_limitations',
            'residual_risk_basis','selection_rationale','owner','timing','depends_on','resources','constraints','trade_offs','monitoring',
            'evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
            ('id','name','objective','mechanism','effectiveness_limitations','residual_risk_basis','selection_rationale','source_fragment','limitations'))
        if action['id'] in ids or action['kind'] not in {'investigation','physical_adaptation','transition_response','cross_cutting'}:
            raise ValueError('Distinct resilience action IDs and explicit proposal kind required.')
        ids.add(action['id']); _ids(action['entry_ids'],entries,'register entry',True); covered.update(action['entry_ids'])
        if action['kind']=='physical_adaptation' and any(entries[i]['kind']!='physical' for i in action['entry_ids']):
            raise ValueError('Physical adaptation must target physical entries.')
        if action['kind']=='transition_response' and any(entries[i]['kind']!='transition' for i in action['entry_ids']):
            raise ValueError('Transition response must target transition entries.')
        sources=_sources(state,action['evidence_ids'],refs)
        fit=_support(action,sources,as_of,gap,action['id']) and all(context_fit[i] for i in action['entry_ids'])
        owner=action['owner']
        _fields(owner, {'name','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'}, ('name','source_fragment','limitations'))
        owner_sources=_sources(state,owner['evidence_ids'],refs); owner_fit=_support(owner,owner_sources,as_of,gap,action['id']+' owner')
        timing=_window(action['timing']) if action['timing'] is not None else None
        if timing is None or _date(timing['start'])<as_of:
            gap(action['id']+': dates unknown or already elapsed; work completion not inferred.')
        links=action['adaptation_links']; linked=[]; linked_physical=set(); seen=set()
        if not isinstance(links,list): raise ValueError('Explicit adaptation link list required.')
        for link in links:
            _fields(link, {'result_id','option_id'}); key=link['result_id'],link['option_id']
            if key in seen or key not in adaptations: raise ValueError('Distinct actual adaptation option links required.')
            seen.add(key); risk_result_id,option=adaptations[key]
            fit=fit and adaptation_fit[key[0]]
            matched={i for i in action['entry_ids'] if entries[i]['kind']=='physical'
                and entries[i]['source_result_id']==risk_result_id
                and entries[i]['source_record_id'] in {l['risk_id'] for l in option['target_links']}}
            if not matched: raise ValueError('Adaptation link must target the exact physical result/record in this action.')
            if action['kind']=='physical_adaptation' and option['kind']=='investigation':
                raise ValueError('Investigation-only option cannot support a physical adaptation proposal.')
            if action['timing']!=option['timing']:
                gap(action['id']+': proposed dates differ from the source adaptation option; source timing and prerequisites remain unresolved.')
            linked_physical.update(matched); linked.append({'result_id':key[0],'option_id':key[1],'option_snapshot':copy.deepcopy(option)})
        if action['kind']=='physical_adaptation' and linked_physical!=set(action['entry_ids']):
            raise ValueError('Every physical adaptation target requires a reproduced matching option.')
        constraints=_observations(state,action['constraints'],refs,as_of,gap,action['id']+' constraints')
        tradeoffs=_observations(state,action['trade_offs'],refs,as_of,gap,action['id']+' trade-offs')
        resources=_observations(state,action['resources'],refs,as_of,gap,action['id']+' resources')
        signals=action['monitoring']
        if not isinstance(signals,list): raise ValueError('Explicit monitoring/reassessment proposal list required.')
        monitoring=[]; signal_ids=set()
        for signal in signals:
            _fields(signal, {'id','indicator','baseline','trigger','review_date','owner','response','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
                ('id','indicator','owner','response','source_fragment','limitations'))
            if signal['id'] in signal_ids or any(signal[k] is not None and not _text(signal[k]) for k in ['baseline','trigger']):
                raise ValueError('Distinct monitoring IDs; explicit sourced baseline/trigger descriptions or null required.')
            signal_ids.add(signal['id']); ss=_sources(state,signal['evidence_ids'],refs)
            supported=_support(signal,ss,as_of,gap,action['id']+' monitoring '+signal['id'])
            when=_date(signal['review_date']) if signal['review_date'] is not None else None
            if not supported or signal['baseline'] is None or signal['trigger'] is None or when is None or when<as_of:
                gap(action['id']+' / '+signal['id']+': monitoring basis/trigger/review timing unresolved; no observed effectiveness or automatic response.')
            monitoring.append(dict(copy.deepcopy(signal),sources=ss,source_support='source_monitoring_candidate' if supported else 'unverified',
                monitoring_started=False,trigger_observed=False,response_authorized=False))
        if not monitoring: gap(action['id']+': monitoring and reassessment not supplied; effectiveness remains unknown.')
        if any(priority_rows[i]['assessment_status']=='unassessed' for i in action['entry_ids']):
            gap(action['id']+': unassessed investigation priority retained; action selection is a separate unapproved rationale.')
        gap(action['id']+': owner acceptance, resources, funding, technical effectiveness and residual risk remain unverified; no implementation authority.')
        actions.append(dict(copy.deepcopy(action),sources=sources,owner_sources=owner_sources,
            source_support='source_action_candidate' if fit else 'unverified',owner_source_support='source_owner_candidate' if owner_fit else 'unverified',
            entry_snapshots=[copy.deepcopy(entries[i]) for i in action['entry_ids']],adaptation_snapshots=linked,
            resource_observations=resources,constraint_observations=constraints,trade_off_observations=tradeoffs,monitoring_proposals=monitoring,
            status='proposed_pending_review',owner_accepted=False,funding_authorized=False,resources_reserved=False,
            implementation_authorized=False,started=False,completed=False,effectiveness_verified=False,residual_risk_verified=False))
    by_id={a['id']:a for a in actions}; incoming={i:0 for i in ids}; edges={i:[] for i in ids}
    for action in actions:
        _ids(action['depends_on'],ids,'dependency')
        for linked in action['adaptation_snapshots']:
            for prerequisite in linked['option_snapshot']['prerequisites']:
                key={'result_id':linked['result_id'],'option_id':prerequisite}
                if not any(key in by_id[parent]['adaptation_links'] for parent in action['depends_on']):
                    gap(action['id']+': source adaptation prerequisite '+prerequisite+' is not a direct proposed dependency; no feasibility inferred.')
        for parent in action['depends_on']:
            if parent==action['id']: raise ValueError('Self dependency rejected.')
            before=by_id[parent]['timing']; after=action['timing']
            if before is not None and after is not None and _date(before['end'])>=_date(after['start']):
                raise ValueError('Inclusive prerequisite work must finish before dependent action starts.')
            if before is None or after is None: gap(action['id']+': dependency timing unresolved; no feasible schedule inferred.')
            edges[parent].append(action['id']); incoming[action['id']]+=1
    layers=[]; remaining=set(ids)
    while remaining:
        layer=sorted(i for i in remaining if incoming[i]==0)
        if not layer: raise ValueError('Resilience action dependency cycle rejected.')
        layers.append(layer); remaining-=set(layer)
        for ident in layer:
            for child in edges[ident]: incoming[child]-=1
    omissions=sorted(set(entries)-covered)
    for ident in omissions: gap(ident+': no selected response/investigation; concern remains untreated, not accepted or absent.')
    if not actions or not review['coverage_complete'] or review['exclusions']:
        gap('Selected resilience plan coverage incomplete; no complete organization response.')
    gap('Qualified climate/site/domain, affected-party and accountable-owner review required; proposed dependencies are not priority ranks or a feasible funded schedule.')
    return {'priority_snapshot':priority,'adaptation_source_snapshots':snapshots,'entry_contexts':copy.deepcopy(contexts),
        'context_sources':context_sources,'actions':actions,'dependency_layers':layers,'unaddressed_entry_ids':omissions,
        'resilience_review':copy.deepcopy(review),'review_sources':_sources(state,review['evidence_ids'],refs),
        'schedule_verified':False,'portfolio_optimized':False,'risk_accepted':False,'resilience_verified':False,
        'organization_safe':False,'implementation_authorized':False,'public_claim_authorized':False}
