"""Reproduce selected strategy foundations into owned, conditional proposals."""
import copy

from .strategy_tools import _text, _reviewed, _reproduce, _record
from .strategy_stakeholders import _date, evidence
from .data_tools import period
from .operations_tools import _action_sequence


def build(state, parameters, refs, result, gap):
    known = {e['id']: e for e in state['evidence']}
    review = parameters['strategy_review']
    _reviewed(state, review, refs, ('scope', 'situation', 'selection_basis', 'coverage_limitations', 'trade_off_review'))
    if review.get('period') != state['reporting_period'] or type(review.get('coverage_complete')) is not bool:
        raise ValueError('Matched strategy reporting context and explicit coverage required.')
    as_of = _date(review.get('as_of_date'))
    strategy = parameters['strategy']
    if (not isinstance(strategy, dict) or set(strategy) != {'id', 'name', 'purpose', 'horizon', 'owner', 'review_date'}
            or any(not _text(strategy[f]) for f in ('id', 'name', 'purpose', 'owner'))):
        raise ValueError('Named proposed strategy with purpose, horizon, owner and review date required.')
    horizon = period(strategy['horizon']); revisit = _date(strategy['review_date'])
    if as_of < _date(review['period']['start']) or _date(horizon['end']) < as_of or not as_of < revisit <= _date(horizon['end']):
        raise ValueError('Live strategy horizon and future review date within horizon required.')
    pillars = parameters['pillars']
    if not isinstance(pillars, list) or not pillars: raise ValueError('Nonempty scoped strategy pillars required.')
    indexed = {}; snapshots = {}; topic_sets = {}; risk_sets = {}; opportunity_sets = {}; target_sets = {}; usage = {}
    fields = {'id', 'name', 'scope', 'selection_rationale', 'materiality_result_id', 'topic_ids', 'risk_result_id', 'risk_ids',
        'opportunity_result_id', 'opportunity_ids', 'target_result_ids', 'feasibility_result_ids', 'context_result_ids'}

    def ids(values, valid=None):
        if not isinstance(values, list) or any(not _text(v) for v in values) or len(set(values)) != len(values) or (valid is not None and not set(values) <= set(valid)):
            raise ValueError('Distinct current selected reference IDs required.')
        return set(values)

    def source(ident, skill, scope):
        if ident is None: return None
        owner, report = _reproduce(state, ident, skill, refs)
        review_key = {'identify-material-sustainability-issues':'materiality_review', 'identify-sustainability-risks':'identification_review',
            'identify-sustainability-opportunities':'identification_review', 'develop-target':'target_review',
            'evaluate-target-feasibility':'feasibility_review', 'map-stakeholders':'mapping_review',
            'assess-sustainability-maturity':'assessment_review'}[skill]
        context = report[review_key]
        if context['scope'] != scope or ('period' in context and context['period'] != review['period']):
            raise ValueError('Each strategy dependency must match its declared pillar scope and reporting context.')
        reviewed_when = context.get('as_of_date') or context.get('review_date')
        if reviewed_when and _date(reviewed_when) > as_of:
            raise ValueError('Strategy review cannot predate a dependency review.')
        snapshots[ident] = {'skill':skill, 'result_id':ident, 'report':copy.deepcopy(report), 'metrics':copy.deepcopy(owner['metrics'])}
        return report

    for pillar in pillars:
        if not isinstance(pillar, dict) or set(pillar) != fields or any(not _text(pillar[f]) for f in ('id','name','scope','selection_rationale')) or pillar['id'] in indexed:
            raise ValueError('Distinct scoped pillars with substantive selection rationale and exact source fields required.')
        ident = pillar['id']; indexed[ident] = pillar; scope = pillar['scope']
        material = source(pillar['materiality_result_id'], 'identify-material-sustainability-issues', scope)
        all_topics = {t['topic']['id'] for t in material['topic_candidates']} if material else set()
        topic_sets[ident] = ids(pillar['topic_ids'], all_topics)
        if material is None: gap(ident + ': no material-issue foundation linked; complete issue selection remains open.')
        for omitted in all_topics - topic_sets[ident]: gap(ident + ': issue ' + omitted + ' is not selected; assessment/response remains open, not immaterial.')
        risk = source(pillar['risk_result_id'], 'identify-sustainability-risks', scope)
        if risk and pillar['materiality_result_id'] is not None:
            owner = next(r for r in state['results'] if r['id']==pillar['risk_result_id'])
            source_id = _record(owner, 'STRATEGY_INPUTS')['materiality_result_id']
            if source_id is not None and source_id != pillar['materiality_result_id']:
                raise ValueError('Selected risk register must retain the selected material-issue dependency.')
        all_risks = {r['record']['id']:r for r in risk['records']} if risk else {}
        risk_sets[ident] = ids(pillar['risk_ids'], all_risks)
        if risk is None: gap(ident + ': risk identification not linked.')
        for omitted in set(all_risks) - risk_sets[ident]: gap(ident + ': risk ' + omitted + ' remains unaddressed by this selection.')
        opportunity = source(pillar['opportunity_result_id'], 'identify-sustainability-opportunities', scope)
        if opportunity:
            owner = next(r for r in state['results'] if r['id']==pillar['opportunity_result_id'])
            inputs = _record(owner, 'STRATEGY_INPUTS')
            for field in ('materiality_result_id','risk_result_id'):
                if inputs[field] is not None and pillar[field] is not None and inputs[field] != pillar[field]:
                    raise ValueError('Selected opportunity must retain the selected material-issue/risk dependencies.')
        all_opportunities = {r['record']['id']:r for r in opportunity['records']} if opportunity else {}
        opportunity_sets[ident] = ids(pillar['opportunity_ids'], all_opportunities)
        if opportunity is None: gap(ident + ': opportunity identification not linked.')
        for chosen in risk_sets[ident]:
            if material and all_risks[chosen]['record']['topic_id'] not in topic_sets[ident]:
                gap(ident + ': selected risk topic is not addressed by selected issue topics.')
        for chosen in opportunity_sets[ident]:
            if not all_opportunities[chosen]['mechanism_source_supported']:
                gap(ident + ': selected opportunity ' + chosen + ' remains an investigation, not a verified improvement.')
            if material and all_opportunities[chosen]['record']['topic_id'] not in topic_sets[ident]:
                gap(ident + ': selected opportunity topic is not addressed by selected issue topics.')
        target_sets[ident] = ids(pillar['target_result_ids'])
        if not target_sets[ident]: gap(ident + ': no quantitative proposed target linked; qualitative goals are not numeric commitments.')
        for target_id in pillar['target_result_ids']:
            target = source(target_id, 'develop-target', scope)
            window = period(target['target']['period'])
            if window['start'] < horizon['start'] or window['end'] > horizon['end']:
                raise ValueError('Strategy horizon must contain each linked target commitment period.')
            if _date(window['end']) < as_of: gap(target_id + ': target period has elapsed; performance/adoption remains unverified.')
        ids(pillar['feasibility_result_ids'])
        assessed = set()
        for feasibility_id in pillar['feasibility_result_ids']:
            screen = source(feasibility_id, 'evaluate-target-feasibility', scope)
            if screen['target_result_id'] not in target_sets[ident]: raise ValueError('Feasibility screen must address a selected target.')
            assessed.add(screen['target_result_id'])
        for missing in target_sets[ident] - assessed: gap(missing + ': no target-feasibility screen linked; delivery remains unassessed.')
        ids(pillar['context_result_ids'])
        for context_id in pillar['context_result_ids']:
            owner = next((r for r in state['results'] if r['id']==context_id), None)
            if owner is None or owner['skill'] not in {'map-stakeholders','assess-sustainability-maturity'}:
                raise ValueError('Context sources must be current stakeholder/maturity results, not arbitrary strategy drafts.')
            source(context_id, owner['skill'], scope)
        selected_sources = {pillar[f] for f in ('materiality_result_id','risk_result_id','opportunity_result_id') if pillar[f] is not None}
        selected_sources |= set(pillar['target_result_ids']+pillar['feasibility_result_ids']+pillar['context_result_ids'])
        for dependency in selected_sources: usage.setdefault(dependency, []).append(ident)

    objectives = parameters['objectives']; objective_index = {}; linked_topics = {p:set() for p in indexed}; linked_targets = {p:set() for p in indexed}
    if not isinstance(objectives, list) or not objectives: raise ValueError('Nonempty owned objective proposals required.')
    for objective in objectives:
        if (not isinstance(objective, dict) or set(objective) != {'id','pillar_id','description','topic_ids','target_result_ids','rationale','owner'}
                or any(not _text(objective[f]) for f in ('id','description','rationale','owner')) or objective['id'] in objective_index or objective['pillar_id'] not in indexed):
            raise ValueError('Distinct owned objectives with selected pillar/topic/target relationships required.')
        pid = objective['pillar_id']; objective_index[objective['id']] = objective
        linked_topics[pid] |= ids(objective['topic_ids'], topic_sets[pid]); linked_targets[pid] |= ids(objective['target_result_ids'], target_sets[pid])
    for pid in indexed:
        for topic in topic_sets[pid] - linked_topics[pid]: gap(pid + ': selected topic ' + topic + ' has no objective response.')
        for target in target_sets[pid] - linked_targets[pid]: gap(pid + ': selected target ' + target + ' has no objective link.')

    initiatives = parameters['initiatives']; initiative_rows = []; used_objectives = set(); actions = []
    if not isinstance(initiatives, list): raise ValueError('Explicit initiative proposals list required.')
    fields = {'id','pillar_id','description','mechanism','objective_ids','opportunity_ids','target_result_ids','owner','target_date',
        'depends_on','resource_review','monitoring_plan','evidence_ids','evidence_fit'}
    for initiative in initiatives:
        if (not isinstance(initiative, dict) or set(initiative) != fields or initiative['pillar_id'] not in indexed
                or any(not _text(initiative[f]) for f in ('id','description','mechanism','owner'))
                or initiative['evidence_fit'] not in {'reviewed_supporting','unverified'}):
            raise ValueError('Exact owned sourced initiative proposals and explicit mechanism required.')
        pid = initiative['pillar_id']; objective_ids = ids(initiative['objective_ids'], objective_index)
        if not objective_ids or any(objective_index[o]['pillar_id'] != pid for o in objective_ids):
            raise ValueError('Initiative needs objective links from its own pillar.')
        used_objectives |= objective_ids; ids(initiative['opportunity_ids'], opportunity_sets[pid]); ids(initiative['target_result_ids'], target_sets[pid])
        objective_targets = {t for o in objective_ids for t in objective_index[o]['target_result_ids']}
        if not set(initiative['target_result_ids']) <= objective_targets:
            raise ValueError('Initiative target links must belong to its linked objectives, not just its pillar.')
        if not initiative['opportunity_ids']: gap(initiative['id'] + ': intervention lacks a selected opportunity link; pathway needs review.')
        evidence(initiative['evidence_ids'], known, refs)
        if not initiative['evidence_ids'] or initiative['evidence_fit'] != 'reviewed_supporting': gap(initiative['id'] + ': initiative mechanism source fitness remains unverified.')
        target_date = _date(initiative['target_date'])
        if not _date(horizon['start']) <= target_date <= _date(horizon['end']): raise ValueError('Initiative target date must be within proposed strategy horizon.')
        overdue = target_date < as_of
        if overdue: gap(initiative['id'] + ': proposed date has passed; work is overdue and unverified, not completed.')
        for target in initiative['target_result_ids']:
            if initiative['target_date'] > snapshots[target]['report']['target']['period']['start']:
                gap(initiative['id'] + ': proposed date is after target-period start; full-period contribution requires timing review.')
        resource = initiative['resource_review']
        if resource is None: gap(initiative['id'] + ': resource/funding assessment is missing; no funded delivery inferred.')
        else:
            if not isinstance(resource, dict) or set(resource) != {'description','evidence_ids','evidence_fit','rationale'} or any(not _text(resource[f]) for f in ('description','rationale')) or resource['evidence_fit'] not in {'reviewed_supporting','unverified'}:
                raise ValueError('Resource context requires substantive source-fit review, not a funding approval flag.')
            evidence(resource['evidence_ids'], known, refs)
            if not resource['evidence_ids'] or resource['evidence_fit'] != 'reviewed_supporting': gap(initiative['id'] + ': resource context remains unverified.')
        monitor = initiative['monitoring_plan']
        if monitor is None: gap(initiative['id'] + ': monitoring method/ownership is missing.')
        else:
            if not isinstance(monitor, dict) or set(monitor) != {'owner','frequency','method','evidence_ids','evidence_fit'} or any(not _text(monitor[f]) for f in ('owner','frequency','method')) or monitor['evidence_fit'] not in {'reviewed_supporting','unverified'}:
                raise ValueError('Monitoring plan requires explicit owner, cadence, method and source fitness.')
            evidence(monitor['evidence_ids'], known, refs)
            if not monitor['evidence_ids'] or monitor['evidence_fit'] != 'reviewed_supporting': gap(initiative['id'] + ': monitoring method source fitness remains unverified.')
        actions.append({'id':initiative['id'],'depends_on':initiative['depends_on'],'target_date':initiative['target_date']})
        initiative_rows.append({'proposal':copy.deepcopy(initiative),'status':'overdue_unverified' if overdue else 'proposed_unsent',
            'source_context':[copy.deepcopy(known[e]) for e in initiative['evidence_ids']], 'monitoring_started':False,
            'resource_source_context':[] if resource is None else [copy.deepcopy(known[e]) for e in resource['evidence_ids']],
            'monitoring_source_context':[] if monitor is None else [copy.deepcopy(known[e]) for e in monitor['evidence_ids']],
            'owner_acceptance_verified':False,'funding_authorized':False,'delivery_feasible':False,'implementation_authorized':False})
    sequence = _action_sequence(actions)
    shared = {ident:pids for ident,pids in usage.items() if len(pids)>1}
    for dependency in shared: gap(dependency + ': source reused across pillars; effects are not independent and must not be added.')
    for omitted in set(objective_index) - used_objectives: gap(omitted + ': no initiative response proposed; objective delivery remains open.')
    if not review['coverage_complete']: gap('Selected strategy coverage is incomplete; no whole-organization strategy or approved issue universe.')
    result['review_requirements'].append({'id':result['id']+'-strategy-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
        'reason':'Review issue/target linkage, source fitness, omissions, trade-offs, resource and monitoring assumptions before strategy adoption.',
        'scope':review['scope'],'reviewer_role':'Accountable strategy owner and relevant domain specialists','status':'open','resolution':None})
    return {'strategy':copy.deepcopy(strategy),'strategy_review':copy.deepcopy(review),'pillars':copy.deepcopy(pillars),
        'objectives':copy.deepcopy(objectives),'initiatives':initiative_rows,'dependency_snapshots':snapshots,'shared_dependency_ids':shared,'proposed_sequence':sequence,
        'aggregate_reduction':None,'portfolio_benefit':None,'final_materiality':None,'strategy_adopted':False,
        'owner_acceptance_verified':False,'funding_authorized':False,'implementation_authorized':False,'public_claim_authorized':False}
