"""Selected sourced exposure shares and qualitative vulnerability-condition profiles."""
import copy
from decimal import localcontext

from .climate_tools import _date, _fields, _reproduce, _reviewed, _sources, _support, _text, _window, ClimateFactorRequired
from .data_tools import number, serialize
from .strategy_tools import _selected, FactorRequired


def _scope(review, source_review, as_of):
    if review['scope'] != source_review['scope'] or as_of < _date(source_review['as_of_date']):
        raise ValueError('Assessment requires matched selected scope and a current dependency review date.')


def _share(state, quantity, observation, pair, supported, hazard, refs, result, gap):
    if quantity is None:
        gap(observation['id'] + ': exposed stock quantity and denominator are unknown; box overlap is not an exposed fraction.')
        return None
    _fields(quantity, {'amount_metric_id','total_metric_id','basis','scenario','model','stock_definition','service_scope','quantity_review'},
        ('amount_metric_id','total_metric_id','stock_definition','service_scope'))
    if quantity['basis'] not in {'historical_stock_proxy','scenario_stock'}:
        raise ValueError('Declare historical_stock_proxy or scenario_stock; historical quantities cannot silently forecast exposure.')
    try:
        amount = _selected(state, quantity['amount_metric_id'], refs)
        total = _selected(state, quantity['total_metric_id'], refs)
    except FactorRequired as error:
        raise ClimateFactorRequired(str(error)) from error
    if (amount['unit'] != total['unit'] or amount['period'] != total['period']
            or amount['boundary_id'] != total['boundary_id'] or amount['boundary_id'] != state['organizational_boundary']['id']):
        raise ValueError('Exposure numerator and denominator require exact matched units, period and selected boundary; no conversion or averaging.')
    if any(m['unit'] in {'UNKNOWN_UNIT','%','dimensionless','index'} for m in (amount,total)):
        raise ValueError('Known common stock units required.')
    a = number(amount['value']); t = number(total['value'])
    if not 0 <= a <= t:
        raise ValueError('Selected exposed stock must be nonnegative and no greater than its sourced population denominator.')
    when = amount['period']; horizon = hazard['context']['horizon']
    if quantity['basis'] == 'historical_stock_proxy':
        if when != state['reporting_period'] or quantity['scenario'] is not None or quantity['model'] is not None:
            raise ValueError('Historical stock proxy requires the explicit current reporting period, not a future stock estimate.')
    elif (hazard['context']['kind'] != 'projected' or not horizon['start'] <= when['start'] <= when['end'] <= horizon['end']
            or quantity['scenario'] != hazard['context']['scenario'] or not _text(quantity['model'])):
        raise ValueError('Scenario stock requires a named supplied stock model, matched climate scenario and period within the selected hazard horizon.')
    review = quantity['quantity_review']
    _fields(review, {'confirmed','evidence_ids','rationale','population_basis','source_contexts','coverage_complete'})
    review_sources = _sources(state, review['evidence_ids'], refs)
    if not isinstance(review['confirmed'], bool) or not isinstance(review['coverage_complete'], bool) or not _text(review['rationale']) or not _text(review['population_basis']):
        raise ValueError('Explicit population comparability, source rationale and quantity review coverage required.')
    contexts = review['source_contexts']
    if not isinstance(contexts, dict) or set(contexts) != {amount['id'],total['id']}:
        raise ValueError('Source-fit review for each actual selected stock metric required.')
    fit = review['confirmed'] and bool(review_sources)
    for metric in (amount,total):
        context = contexts[metric['id']]
        _fields(context, {'evidence_ids','evidence_fit','rationale','stock_definition','service_scope'},
            ('rationale','stock_definition','service_scope'))
        _sources(state, context['evidence_ids'], refs)
        if (set(context['evidence_ids']) != set(metric['evidence_ids']) or context['stock_definition'] != quantity['stock_definition']
                or context['service_scope'] != quantity['service_scope'] or not set(context['evidence_ids']) <= set(review['evidence_ids'])
                or context['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}):
            raise ValueError('Stock contexts require the actual source evidence and identical supplied population/service definition.')
        fit = fit and context['evidence_fit'] == 'reviewed_supporting'
        metric_sources = _sources(state, metric['evidence_ids'], refs)
        if not any(e['period']['start'] <= when['start'] <= when['end'] <= e['period']['end'] for e in metric_sources):
            gap(observation['id'] + ': stock source period does not cover selected quantity period; past stock cannot be relabeled as a future projection.')
            fit = False
    accepted = supported and observation['status'] == 'documented' and pair['screening_status'] == 'possible_exposure_candidate' and fit
    record = dict(copy.deepcopy(quantity), amount_snapshot=copy.deepcopy(amount), total_snapshot=copy.deepcopy(total),
        review_sources=review_sources, share_metric_id=None, supplied_share_percent=None,
        assessment_status='withheld', future_stock_verified=False, loss=None, probability=None)
    if not accepted:
        gap(observation['id'] + ': quantity source/population fitness or exposure context is unverified; share withheld rather than set to zero.')
        return record
    if not review['coverage_complete']:
        gap(observation['id'] + ': selected stock coverage is incomplete; no whole-organization exposure share.')
    if quantity['basis'] == 'historical_stock_proxy':
        gap(observation['id'] + ': historical stock is a declared proxy, not verified future presence, growth or damage.')
    if t == 0:
        gap(observation['id'] + ': sourced total stock is zero; percentage undefined, not zero exposure or safety.')
        return record
    assumption = 'Conditional supplied selected-stock share; not hazard probability, future presence, vulnerability, financial loss or verified exposure. Channels and hazards are not additive.'
    if assumption not in result['assumptions']:
        result['assumptions'].append(assumption)
    with localcontext() as context:
        context.prec = 34
        value = serialize(a / t * 100)
    ident = result['id'] + '-' + observation['id'] + '-stock-share'
    result['metrics'].append({'id':ident,'name':'Conditional supplied stock share for ' + observation['id'] + ' (not probability/loss)',
        'value':value,'unit':'%','period':copy.deepcopy(when),'boundary_id':amount['boundary_id'],
        'evidence_ids':sorted(refs),'method':{'name':'Supplied selected exposure-stock ratio','version':'0.1.0','source':'repository:docs/climate-risk-contract.md'},
        'assumption':assumption,'uncertainty':{'kind':'unquantified','description':'Source population, stock fitness, site applicability and future operating uncertainty retained; no confidence bound.','value':None,'unit':None},
        'calculation':{'formula':'supplied selected stock / supplied comparable total stock * 100','inputs':list(dict.fromkeys([amount['id'],total['id']])),
            'conversions':[],'rounding':'Decimal precision 34; no display rounding'}})
    record.update(share_metric_id=ident, supplied_share_percent=value, assessment_status='conditional_source_share')
    return record


def exposure(state, parameters, refs, result, gap):
    mapping = _reproduce(state, parameters['mapping_result_id'], refs, 'map-assets-to-hazards')
    review = parameters['exposure_review']; as_of = _reviewed(state, review, refs, 'sourced_exposure_stock')
    _scope(review, mapping['mapping_review'], as_of)
    pairs = {(p['asset_id'],p['hazard_id']):p for p in mapping['comparisons']}
    hazards = {h['id']:h for h in mapping['hazard_snapshot']['hazards']}
    raw = parameters['observations']
    if not isinstance(raw,list):
        raise ValueError('Explicit selected exposure observations required.')
    rows=[]; ids=set(); covered=set()
    for obs in raw:
        _fields(obs, {'id','asset_id','hazard_id','channel','mechanism','status','observed_date','evidence_ids','evidence_fit','source_fragment','limitations','quantity'},
            ('id','asset_id','hazard_id','mechanism','source_fragment','limitations'))
        pair = obs['asset_id'],obs['hazard_id']
        if (obs['id'] in ids or pair not in pairs or obs['channel'] not in {'direct_site','service_disruption','ecosystem_dependency','workforce_health'}
                or obs['status'] not in {'documented','proposed','unknown','conflicting'}):
            raise ValueError('Distinct observation IDs, current mapped pairs, declared channel and source status required.')
        ids.add(obs['id']); covered.add(pair)
        sources = _sources(state, obs['evidence_ids'], refs)
        supported = _support(obs, sources, as_of, gap, obs['id'])
        status = 'source_exposure_candidate' if supported and obs['status']=='documented' and pairs[pair]['screening_status']=='possible_exposure_candidate' else 'unverified'
        if status == 'unverified':
            gap(obs['id'] + ': exposure mechanism is proposed, unknown, conflicting or mapping/source applicability is unverified.')
        quantity = _share(state, obs['quantity'], obs, pairs[pair], supported, hazards[pair[1]], refs, result, gap)
        rows.append(dict(copy.deepcopy(obs), sources=sources, source_support=status, quantity_assessment=quantity,
            exposure_verified=False, probability=None, vulnerability=None, damage=None, risk_score=None))
    for pair in sorted(set(pairs)-covered):
        gap(' / '.join(pair) + ': mapped pair lacks exposure observation; unknown is not absence.')
    if not raw or not review['coverage_complete'] or review['exclusions']:
        gap('Exposure observations and stock coverage are selected/incomplete; no organization exposure total.')
    return {'mapping_snapshot':mapping,'observations':rows,'exposure_review':copy.deepcopy(review),
        'review_sources':_sources(state,review['evidence_ids'],refs),'organization_total':None,
        'exposure_verified':False,'future_stock_verified':False,'organization_safe':False,'public_claim_authorized':False}


def vulnerability(state, parameters, refs, result, gap):
    source = _reproduce(state, parameters['exposure_result_id'], refs, 'assess-exposure')
    review = parameters['vulnerability_review']; as_of = _reviewed(state, review, refs, 'sourced_condition_profile')
    _scope(review, source['exposure_review'], as_of)
    rubric=parameters['rubric']
    _fields(rubric, {'id','name','version','evidence_ids','evidence_fit','criteria'}, ('id','name','version'))
    rubric_sources = _sources(state,rubric['evidence_ids'],refs)
    if (not rubric_sources or rubric['evidence_fit'] != 'reviewed_supporting'
            or any(s['source']['version'] is None for s in rubric_sources) or not _text(review.get('rubric_fit_rationale'))):
        raise ValueError('Supporting sourced versioned vulnerability criteria required; no model-generated default scale.')
    criteria={}; dimensions={'sensitivity','coping_capacity','adaptive_capacity'}
    if not isinstance(rubric['criteria'],list) or not rubric['criteria']:
        raise ValueError('Explicit vulnerability criteria required.')
    for criterion in rubric['criteria']:
        _fields(criterion, {'id','dimension','requirement'}, ('id','requirement'))
        if criterion['id'] in criteria or criterion['dimension'] not in dimensions:
            raise ValueError('Distinct criteria with sensitivity/coping/adaptive dimension required.')
        criteria[criterion['id']]=criterion
    if {c['dimension'] for c in criteria.values()} != dimensions:
        raise ValueError('Rubric must retain all three vulnerability dimensions; capacity cannot replace sensitivity.')
    observations={o['id']:o for o in source['observations']}
    hazards={h['id']:h for h in source['mapping_snapshot']['hazard_snapshot']['hazards']}
    factors=parameters['factors']; rows=[]; seen=set(); ids=set()
    if not isinstance(factors,list):
        raise ValueError('Explicit vulnerability factor observations required.')
    for factor in factors:
        _fields(factor, {'id','exposure_id','criterion_id','status','effect','cause_effect','effective_period','observed_date','evidence_ids','evidence_fit','source_fragment','limitations'},
            ('id','exposure_id','criterion_id','cause_effect','source_fragment','limitations'))
        pair=factor['exposure_id'],factor['criterion_id']
        if (factor['id'] in ids or pair in seen or pair[0] not in observations or pair[1] not in criteria
                or factor['status'] not in {'condition_observed','capacity_demonstrated','planned','unknown','conflicting'}
                or factor['effect'] not in {'susceptibility_increasing','susceptibility_reducing','unknown'}):
            raise ValueError('Distinct current exposure/criterion factor records with explicit condition/effect required.')
        if factor['status']=='capacity_demonstrated' and criteria[pair[1]]['dimension']=='sensitivity':
            raise ValueError('Demonstrated coping/adaptive capacity cannot replace the sensitivity condition.')
        ids.add(factor['id']); seen.add(pair)
        sources=_sources(state,factor['evidence_ids'],refs)
        supported=_support(factor,sources,as_of,gap,factor['id'])
        effective = _window(factor['effective_period']) if factor['effective_period'] is not None else None
        observation=observations[pair[0]]; horizon=hazards[observation['hazard_id']]['context']['horizon']
        covers = effective is not None and effective['start'] <= horizon['start'] <= horizon['end'] <= effective['end']
        candidate=(supported and factor['status'] in {'condition_observed','capacity_demonstrated'} and factor['effect']!='unknown'
            and covers and observation['source_support']=='source_exposure_candidate')
        if not candidate:
            gap(factor['id'] + ': source condition, exposure linkage or full horizon applicability is unresolved; plans are not demonstrated capacity.')
        rows.append(dict(copy.deepcopy(factor), sources=sources, criterion=copy.deepcopy(criteria[pair[1]]),
            source_condition_status='reviewed_source_candidate' if supported else 'unverified',
            horizon_applicability='supplied_period_covers_horizon' if covers else 'unverified',
            assessment_status='sourced_condition_candidate' if candidate else 'unverified',
            capacity_verified=False, vulnerability_score=None, risk_reduction=None))
    profiles=[]
    for ident,observation in observations.items():
        for criterion_id in sorted(criteria):
            if (ident,criterion_id) not in seen:
                gap(ident + ' / ' + criterion_id + ': vulnerability criterion unassessed; no default capacity or susceptibility.')
        dimension_status={}
        for dim in sorted(dimensions):
            expected={c['id'] for c in criteria.values() if c['dimension']==dim}
            selected=[f for f in rows if f['exposure_id']==ident and f['criterion_id'] in expected]
            dimension_status[dim]='reviewed_criterion_candidates' if len(selected)==len(expected) and all(f['assessment_status']=='sourced_condition_candidate' for f in selected) else 'conditions_unresolved'
        profiles.append({'exposure_id':ident,'asset_id':observation['asset_id'],'hazard_id':observation['hazard_id'],
            'dimension_status':dimension_status,'vulnerability_score':None,'capacity_offsets_sensitivity':False,
            'risk_reduction':None,'safe':False})
    if not factors or not observations or not review['coverage_complete'] or review['exclusions']:
        gap('Vulnerability condition/criterion coverage is selected or incomplete; no organization score or resilience determination.')
    return {'exposure_snapshot':source,'rubric':copy.deepcopy(rubric),'rubric_sources':rubric_sources,'factors':rows,'profiles':profiles,
        'vulnerability_review':copy.deepcopy(review),'review_sources':_sources(state,review['evidence_ids'],refs),
        'organization_vulnerability_score':None,'organization_safe':False,'capacity_verified':False,
        'implementation_authorized':False,'public_claim_authorized':False}
