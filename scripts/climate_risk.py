"""Sourced ordinal physical-risk matrix and conditional adaptation proposals."""
import copy

from .climate_tools import _date, _fields, _reproduce, _reviewed, _sources, _support, _text, _window
from .climate_assessment import _scope


def _model(state, model, refs, review):
    _fields(model, {'id','name','version','evidence_ids','evidence_fit','likelihood_levels','consequence_levels','risk_levels','cells'}, ('id','name','version'))
    sources = _sources(state, model['evidence_ids'], refs)
    if (not sources or model['evidence_fit'] != 'reviewed_supporting' or any(s['source']['version'] is None for s in sources)
            or not _text(review.get('model_fit_rationale'))):
        raise ValueError('Supporting versioned sourced matrix and substantive applicability rationale required; no default risk scale.')
    axes={}
    for axis in ['likelihood_levels','consequence_levels','risk_levels']:
        raw=model[axis]; ids=[]
        if not isinstance(raw,list) or not raw:
            raise ValueError('Explicit ordered likelihood, consequence and risk level definitions required.')
        for level in raw:
            _fields(level, {'id','label','definition'}, ('id','label','definition'))
            if level['id'] in ids:
                raise ValueError('Distinct level IDs within each ascending axis required.')
            ids.append(level['id'])
        axes[axis]=ids
    cells={}
    if not isinstance(model['cells'],list):
        raise ValueError('Explicit complete likelihood/consequence matrix required.')
    for cell in model['cells']:
        _fields(cell, {'likelihood_id','consequence_id','risk_level_id'})
        pair=cell['likelihood_id'],cell['consequence_id']
        if (pair in cells or pair[0] not in axes['likelihood_levels'] or pair[1] not in axes['consequence_levels']
                or cell['risk_level_id'] not in axes['risk_levels']):
            raise ValueError('Unique cells must select current axis/risk IDs.')
        cells[pair]=cell['risk_level_id']
    if set(cells) != {(l,c) for l in axes['likelihood_levels'] for c in axes['consequence_levels']}:
        raise ValueError('Matrix must cover every supplied likelihood/consequence pair; missing cells cannot be inferred.')
    ranks={ident:index for index,ident in enumerate(axes['risk_levels'])}
    for li,l in enumerate(axes['likelihood_levels']):
        for ci,c in enumerate(axes['consequence_levels']):
            rank=ranks[cells[l,c]]
            if ((li and rank < ranks[cells[axes['likelihood_levels'][li-1],c]])
                    or (ci and rank < ranks[cells[l,axes['consequence_levels'][ci-1]]])):
                raise ValueError('Ascending risk matrix cannot decrease with supplied increasing likelihood or consequence.')
    return axes,cells,sources


def _rating(state, rating, levels, refs, as_of, gap, label):
    _fields(rating, {'lower_level_id','upper_level_id','evidence_ids','evidence_fit','observed_date','rationale','source_fragment','limitations'},
        ('rationale','source_fragment','limitations'))
    sources=_sources(state,rating['evidence_ids'],refs)
    supported=_support(rating,sources,as_of,gap,label)
    lower,upper=rating['lower_level_id'],rating['upper_level_id']
    if any(i is not None and i not in levels for i in (lower,upper)):
        raise ValueError('Rating bounds must use supplied axis levels or null; no unit/probability conversion.')
    if lower is not None and upper is not None and levels.index(lower)>levels.index(upper):
        raise ValueError('Ordinal rating interval reversed.')
    if lower is None or upper is None:
        gap(label + ': rating bounds unknown; no lowest/highest default or finite class inferred.')
        supported=False
    selected=levels[levels.index(lower):levels.index(upper)+1] if supported else []
    return dict(copy.deepcopy(rating),sources=sources,source_support='reviewed_source_candidate' if supported else 'unverified'),selected


def score(state, parameters, refs, result, gap):
    source=_reproduce(state,parameters['vulnerability_result_id'],refs,'assess-vulnerability')
    review=parameters['risk_review']; as_of=_reviewed(state,review,refs,'ordinal_matrix_screen')
    _scope(review,source['vulnerability_review'],as_of)
    axes,cells,model_sources=_model(state,parameters['model'],refs,review)
    observations={o['id']:o for o in source['exposure_snapshot']['observations']}
    profiles={p['exposure_id']:p for p in source['profiles']}
    hazards={h['id']:h for h in source['exposure_snapshot']['mapping_snapshot']['hazard_snapshot']['hazards']}
    rows=[]; ids=set(); covered=set()
    if not isinstance(parameters['ratings'],list):
        raise ValueError('Explicit selected physical-risk rating list required.')
    for rating in parameters['ratings']:
        _fields(rating, {'id','exposure_id','consequence_pathway','likelihood','consequence','context_review'},
            ('id','exposure_id','consequence_pathway'))
        ident=rating['exposure_id']
        if rating['id'] in ids or ident not in observations or ident in covered:
            raise ValueError('Distinct risk IDs and one current exposure rating per selected observation required.')
        ids.add(rating['id']); covered.add(ident)
        context=rating['context_review']
        _fields(context, {'confirmed','evidence_ids','exposure_fit','vulnerability_fit','scenario','horizon','rationale'}, ('rationale',))
        context_sources=_sources(state,context['evidence_ids'],refs)
        if not isinstance(context['confirmed'],bool) or any(context[f] not in {'reviewed_supporting','unverified','irrelevant'} for f in ['exposure_fit','vulnerability_fit']):
            raise ValueError('Explicit exposure/vulnerability context fitness required.')
        actual=set(observations[ident]['evidence_ids'])
        for factor in source['factors']:
            if factor['exposure_id']==ident:
                actual.update(factor['evidence_ids'])
        if not actual <= set(context['evidence_ids']):
            raise ValueError('Risk context review must retain actual selected exposure and condition evidence.')
        hazard=hazards[observations[ident]['hazard_id']]
        if context['scenario']!=hazard['context']['scenario'] or _window(context['horizon'])!=hazard['context']['horizon']:
            raise ValueError('Risk source review must retain the exact selected climate scenario and horizon; no cross-case likelihood transfer.')
        likelihood,ls=_rating(state,rating['likelihood'],axes['likelihood_levels'],refs,as_of,gap,rating['id']+' likelihood')
        consequence,cs=_rating(state,rating['consequence'],axes['consequence_levels'],refs,as_of,gap,rating['id']+' consequence')
        fit=(context['confirmed'] and bool(context_sources) and context['exposure_fit']==context['vulnerability_fit']=='reviewed_supporting'
            and observations[ident]['source_support']=='source_exposure_candidate')
        class_ids={cells[l,c] for l in ls for c in cs} if fit else set()
        ordered=[r for r in axes['risk_levels'] if r in class_ids]
        unresolved=any(v=='conditions_unresolved' for v in profiles[ident]['dimension_status'].values())
        if not ordered:
            gap(rating['id'] + ': source ratings or exposure/vulnerability context unresolved; no risk class assigned.')
        else:
            gap(rating['id'] + ': supplied matrix classes are conditional screening only; qualified site/source and uncertainty review remains required.')
        if unresolved:
            gap(rating['id'] + ': unassessed/planned/horizon-limited vulnerability conditions retained; class does not validate capacity or loss.')
        rows.append({'id':rating['id'],'exposure_id':ident,'asset_id':observations[ident]['asset_id'],'hazard_id':observations[ident]['hazard_id'],
            'consequence_pathway':rating['consequence_pathway'],'likelihood':likelihood,'consequence':consequence,
            'context_review':copy.deepcopy(context),'context_sources':context_sources,'input_conditions_unresolved':unresolved,
            'screening_status':'conditional_matrix_screen' if ordered else 'unclassified',
            'possible_risk_level_ids':ordered,'lower_risk_level_id':ordered[0] if ordered else None,'upper_risk_level_id':ordered[-1] if ordered else None,
            'risk_level_selected':None,'probability':None,'expected_loss':None,'risk_verified':False,'risk_accepted':False,'safe':False})
    for ident in sorted(set(observations)-covered):
        gap(ident + ': exposure omitted from physical-risk rating; no default low risk.')
    if not rows or not review['coverage_complete'] or review['exclusions']:
        gap('Selected risk/matrix coverage incomplete; no organization risk score, ranking or aggregate loss.')
    return {'vulnerability_snapshot':source,'model':copy.deepcopy(parameters['model']),'model_sources':model_sources,
        'risks':rows,'risk_review':copy.deepcopy(review),'review_sources':_sources(state,review['evidence_ids'],refs),
        'organization_risk_score':None,'organization_safe':False,'risk_accepted':False,'public_claim_authorized':False}


def _observations(state, raw, refs, as_of, gap, label):
    if not isinstance(raw,list):
        raise ValueError('Explicit adaptation constraint/trade-off observations required.')
    rows=[]; ids=set()
    for item in raw:
        _fields(item, {'id','description','affected_party','status','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
            ('id','description','affected_party','source_fragment','limitations'))
        if item['id'] in ids or item['status'] not in {'identified','unmet','unknown'}:
            raise ValueError('Distinct adaptation observations with identified/unmet/unknown status required.')
        ids.add(item['id']); sources=_sources(state,item['evidence_ids'],refs)
        supported=_support(item,sources,as_of,gap,label+' '+item['id'])
        if not supported or item['status'] in {'unknown','unmet'}:
            gap(label+' '+item['id'] + ': adaptation condition/side-effect remains unresolved or unmet.')
        rows.append(dict(copy.deepcopy(item),sources=sources,source_support='reviewed_source_candidate' if supported else 'unverified',resolved=False))
    if not raw:
        gap(label + ': no condition/side-effect observations supplied; absence does not establish feasibility or no maladaptation.')
    return rows


def adaptation(state, parameters, refs, result, gap):
    source=_reproduce(state,parameters['risk_result_id'],refs,'score-physical-risk')
    review=parameters['adaptation_review']; as_of=_reviewed(state,review,refs,'sourced_adaptation_candidates')
    _scope(review,source['risk_review'],as_of)
    known={r['id']:r for r in source['risks']}; criteria={c['id']:c for c in source['vulnerability_snapshot']['rubric']['criteria']}
    hazards={h['id']:h for h in source['vulnerability_snapshot']['exposure_snapshot']['mapping_snapshot']['hazard_snapshot']['hazards']}
    raw=parameters['options']
    if not isinstance(raw,list):
        raise ValueError('Explicit owned adaptation proposal list required.')
    rows=[]; ids=set(); covered=set()
    for option in raw:
        _fields(option, {'id','name','kind','target_links','mechanism','intended_effect','effectiveness_limitations','residual_risk_basis','owner','timing',
            'prerequisites','evidence_ids','evidence_fit','observed_date','source_fragment','limitations','constraints','trade_offs','monitoring'},
            ('id','name','mechanism','intended_effect','effectiveness_limitations','residual_risk_basis','owner','source_fragment','limitations'))
        if option['id'] in ids or option['kind'] not in {'investigation','physical_change','operational_change','ecosystem_action'}:
            raise ValueError('Distinct adaptation IDs and explicit investigation/physical/operational/ecosystem kind required.')
        ids.add(option['id'])
        links=option['target_links']
        if not isinstance(links,list) or not links:
            raise ValueError('Adaptation must link selected physical risks and vulnerability criteria explicitly.')
        linked=set()
        for link in links:
            _fields(link, {'risk_id','criterion_ids'})
            if link['risk_id'] not in known or link['risk_id'] in linked or not isinstance(link['criterion_ids'],list):
                raise ValueError('Distinct current target risk links required.')
            names=link['criterion_ids']
            if any(not _text(i) for i in names) or len(set(names))!=len(names) or not set(names)<=set(criteria):
                raise ValueError('Distinct current vulnerability criterion IDs required.')
            if not names:
                gap(option['id'] + ': targeted sensitivity/capacity criteria unspecified; effectiveness unresolved.')
            linked.add(link['risk_id']); covered.add(link['risk_id'])
            if known[link['risk_id']]['screening_status']=='unclassified':
                gap(option['id'] + ': target risk is unclassified; proposal cannot establish effectiveness or priority.')
        sources=_sources(state,option['evidence_ids'],refs)
        supported=_support(option,sources,as_of,gap,option['id'])
        timing=_window(option['timing']) if option['timing'] is not None else None
        if timing is None or _date(timing['end'])<as_of:
            gap(option['id'] + ': proposed implementation date unknown or overdue; no work completion inferred.')
        for link in links:
            horizon=hazards[known[link['risk_id']]['hazard_id']]['context']['horizon']
            if timing and timing['end']>horizon['start']:
                gap(option['id'] + ': proposed completion follows hazard-horizon start; early-period protection is not established.')
            if timing and timing['end']>horizon['end']:
                gap(option['id'] + ': proposed completion follows the full selected risk horizon; no in-horizon protection established.')
        predecessors=option['prerequisites']
        if not isinstance(predecessors,list) or any(not _text(p) for p in predecessors) or len(set(predecessors))!=len(predecessors):
            raise ValueError('Explicit distinct prerequisite option IDs required.')
        monitoring=option['monitoring']; monitoring_sources=[]
        if monitoring is None:
            gap(option['id'] + ': effectiveness/residual-risk monitoring unplanned or unknown.')
        else:
            _fields(monitoring, {'definition','owner','frequency','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
                ('definition','owner','frequency','source_fragment','limitations'))
            monitoring_sources=_sources(state,monitoring['evidence_ids'],refs)
            _support(monitoring,monitoring_sources,as_of,gap,option['id']+' monitoring')
        constraints=_observations(state,option['constraints'],refs,as_of,gap,option['id']+' constraints')
        tradeoffs=_observations(state,option['trade_offs'],refs,as_of,gap,option['id']+' trade-offs')
        gap(option['id'] + ': proposed adaptation needs engineering/affected-party/effectiveness, cost, resource, funding and owner review before action.')
        rows.append(dict(copy.deepcopy(option),sources=sources,source_support='source_option_candidate' if supported else 'unverified',
            constraint_observations=constraints,trade_off_observations=tradeoffs,monitoring_sources=monitoring_sources,
            status='proposed_pending_review',effectiveness_verified=False,expected_risk_reduction=None,residual_risk=None,
            monitoring_started=False,owner_accepted=False,funding_authorized=False,resources_reserved=False,implementation_authorized=False))
    by_id={o['id']:o for o in rows}; indegree={i:0 for i in ids}; edges={i:[] for i in ids}
    for option in rows:
        for parent in option['prerequisites']:
            if parent not in ids or parent==option['id']:
                raise ValueError('Known nonself adaptation prerequisites required.')
            before=by_id[parent]['timing']; after=option['timing']
            if before and after and before['end']>=after['start']:
                raise ValueError('Inclusive prerequisite work must finish before dependent adaptation starts.')
            edges[parent].append(option['id']); indegree[option['id']]+=1
    queue=sorted(i for i in ids if indegree[i]==0); visited=0
    while queue:
        current=queue.pop(); visited+=1
        for child in edges[current]:
            indegree[child]-=1
            if indegree[child]==0: queue.append(child)
    if visited!=len(ids):
        raise ValueError('Adaptation prerequisite cycle rejected; no feasible ordering inferred.')
    for ident in sorted(set(known)-covered):
        gap(ident + ': no adaptation response selected; no acceptance of untreated/residual risk.')
    if not rows or not review['coverage_complete'] or review['exclusions']:
        gap('Adaptation option coverage incomplete; no preferred portfolio, verified resilience or complete response.')
    return {'risk_snapshot':source,'options':rows,'adaptation_review':copy.deepcopy(review),
        'review_sources':_sources(state,review['evidence_ids'],refs),'preferred_option_id':None,
        'organization_safe':False,'resilience_verified':False,'implementation_authorized':False,'public_claim_authorized':False}
