"""Sourced qualitative risk/opportunity mechanisms with unverified future delivery."""
import copy

from .strategy_tools import _text, _reviewed, _reproduce
from .strategy_stakeholders import _date, evidence
from .data_tools import period


def identify(state, skill, parameters, refs, result, gap):
    opportunity = skill == 'identify-sustainability-opportunities'
    label = 'Opportunity' if opportunity else 'Risk'
    known = {e['id']: e for e in state['evidence']}
    review = parameters['identification_review']
    _reviewed(state, review, refs, ('scope', 'context', 'identification_method', 'coverage_limitations'))
    if review.get('period') != state['reporting_period'] or type(review.get('coverage_complete')) is not bool:
        raise ValueError('Matched reporting period and explicit identification coverage required.')
    as_of = _date(review.get('as_of_date'))
    if as_of < _date(review['period']['start']):
        raise ValueError('Identification review cannot predate selected period.')
    materiality = None; impacts = {}; topics = set()
    if parameters['materiality_result_id'] is not None:
        _, materiality = _reproduce(state, parameters['materiality_result_id'], 'identify-material-sustainability-issues', refs)
        if materiality['materiality_review']['scope'] != review['scope'] or materiality['materiality_review']['period'] != review['period']:
            raise ValueError('Material-issue dependency must match selected scope and reporting period.')
        impacts = {r['impact']['id']: r for r in materiality['impacts']}
        topics = {r['topic']['id'] for r in materiality['topic_candidates']}
    else:
        gap('No material-issue register linked; issue universe and impact significance remain unestablished.')
    risk_report = None; risks = {}
    if opportunity and parameters['risk_result_id'] is not None:
        _, risk_report = _reproduce(state, parameters['risk_result_id'], 'identify-sustainability-risks', refs)
        if risk_report['identification_review']['scope'] != review['scope'] or risk_report['identification_review']['period'] != review['period']:
            raise ValueError('Risk dependency must match selected scope and reporting period.')
        risks = {r['record']['id']: r for r in risk_report['records']}
    register = parameters['opportunities' if opportunity else 'risks']
    if not isinstance(register, list):
        raise ValueError('Explicit register required; empty selected records do not establish absence.')
    fields = {'id', 'topic_id', 'category', 'description', 'mechanism', 'affected_context', 'horizon', 'observed_date',
        'evidence_ids', 'evidence_fit', 'source_fragment', 'impact_ids', 'likelihood', 'magnitude', 'dependencies',
        'trade_offs', 'trade_off_review', 'follow_up'}
    if opportunity: fields |= {'proposed_action', 'addresses_risk_ids'}
    categories = {'impact_improvement', 'organization_benefit', 'delivery_improvement'} if opportunity else {'impact', 'organization', 'delivery'}
    ids = set(); rows = []

    def assessment(item, context):
        if (not isinstance(item, dict) or set(item) != {'description', 'evidence_ids', 'evidence_fit', 'rationale'}
                or (item['description'] is not None and not _text(item['description'])) or not _text(item['rationale'])
                or item['evidence_fit'] not in {'reviewed_supporting', 'unverified', 'unknown'}):
            raise ValueError('Qualitative assessment requires description/null, source fit and substantive rationale.')
        evidence(item['evidence_ids'], known, refs)
        supported = item['description'] is not None and bool(item['evidence_ids']) and item['evidence_fit'] == 'reviewed_supporting'
        if not supported: gap(context + ' remains unknown or unverified; no default rating or quantified effect.')
        return {'record': copy.deepcopy(item), 'source_supported': supported,
            'source_context': [copy.deepcopy(known[e]) for e in item['evidence_ids']]}

    for row in register:
        if (not isinstance(row, dict) or set(row) != fields or row['id'] in ids or row['category'] not in categories
                or any(not _text(row[f]) for f in ('id', 'topic_id', 'description', 'mechanism', 'affected_context', 'source_fragment', 'trade_off_review'))
                or row['evidence_fit'] not in {'reviewed_supporting', 'proxy', 'unverified', 'irrelevant'}):
            raise ValueError('Distinct exact sourced mechanisms, affected context and selected categories required.')
        ids.add(row['id']); evidence(row['evidence_ids'], known, refs)
        if materiality and row['topic_id'] not in topics:
            raise ValueError('Linked topic must resolve to the selected material-issue register.')
        impact_ids = row['impact_ids']
        if not isinstance(impact_ids, list) or any(not _text(i) for i in impact_ids) or len(set(impact_ids)) != len(impact_ids) or not set(impact_ids) <= set(impacts):
            raise ValueError('Distinct impact links require a reproducible material-issue register.')
        if any(impacts[i]['impact']['topic_id'] != row['topic_id'] for i in impact_ids):
            raise ValueError('Linked impacts must belong to the candidate topic.')
        if not opportunity and any(impacts[i]['impact']['direction'] != 'negative' for i in impact_ids):
            raise ValueError('Positive impacts cannot be substituted for adverse risk evidence.')
        impact_backing = bool(impact_ids) and all(impacts[i]['source_supported'] for i in impact_ids)
        impact_category = row['category'] in {'impact', 'impact_improvement'}
        if impact_category and not impact_backing:
            gap(row['id'] + ': impact pathway requires current supporting linked impacts; unresolved impacts remain unresolved.')
        when = _date(row['observed_date']) if row['observed_date'] is not None else None
        if when and when > as_of: raise ValueError('Mechanism source observation postdates identification as-of.')
        current = when is not None and when >= _date(review['period']['start'])
        horizon = period(row['horizon']) if row['horizon'] is not None else None
        live_horizon = horizon is not None and _date(horizon['end']) >= as_of
        if not live_horizon: gap(row['id'] + ': prospective horizon is missing or elapsed; realization remains unverified.')
        supported = bool(row['evidence_ids']) and row['evidence_fit'] == 'reviewed_supporting' and current and live_horizon and (not impact_category or impact_backing)
        if not supported: gap(row['id'] + ': mechanism remains a source/date/impact-fitness hypothesis, not an established effect.')
        likelihood = assessment(row['likelihood'], row['id'] + ' likelihood')
        magnitude = assessment(row['magnitude'], row['id'] + ' magnitude')
        dependencies = row['dependencies']
        if not isinstance(dependencies, list): raise ValueError('Explicit delivery/evidence dependencies list required.')
        dep_ids = set(); conditions = []
        for dep in dependencies:
            if (not isinstance(dep, dict) or set(dep) != {'id', 'description', 'status', 'evidence_ids', 'evidence_fit', 'owner'}
                    or any(not _text(dep[f]) for f in ('id', 'description', 'owner')) or dep['id'] in dep_ids
                    or dep['status'] not in {'known_supported', 'known_unmet', 'unresolved'} or dep['evidence_fit'] not in {'reviewed_supporting', 'unverified'}):
                raise ValueError('Distinct owned dependencies with known/unresolved evidence status required.')
            dep_ids.add(dep['id']); evidence(dep['evidence_ids'], known, refs)
            backed = bool(dep['evidence_ids']) and dep['evidence_fit'] == 'reviewed_supporting'
            if dep['status'] != 'unresolved' and not backed:
                raise ValueError('Known supported/unmet dependency status needs reviewed supporting source evidence.')
            if dep['status'] != 'known_supported': gap(row['id'] + ': dependency ' + dep['id'] + ' remains ' + dep['status'] + '; no delivery confirmation.')
            conditions.append({'record': copy.deepcopy(dep), 'source_context': [copy.deepcopy(known[e]) for e in dep['evidence_ids']], 'completion_verified': False})
        trades = row['trade_offs']; trade_rows = None
        if trades is None: gap(row['id'] + ': trade-offs and adverse interactions have not been assessed.')
        elif isinstance(trades, list): trade_rows = [assessment(t, row['id'] + ' trade-off') for t in trades]
        else: raise ValueError('Trade-offs must be explicit qualitative records or null for unknown.')
        addressed = []
        if opportunity:
            if not _text(row['proposed_action']): raise ValueError('Substantive proposed action required, not implementation approval.')
            links = row['addresses_risk_ids']
            if not isinstance(links, list) or any(not _text(i) for i in links) or len(set(links)) != len(links) or not set(links) <= set(risks):
                raise ValueError('Risk-response links require distinct current risk IDs.')
            if any(risks[i]['record']['topic_id'] != row['topic_id'] for i in links):
                raise ValueError('Addressed risks must match opportunity topic.')
            addressed = [copy.deepcopy(risks[i]) for i in links]
            if any(not risks[i]['mechanism_source_supported'] for i in links):
                gap(row['id'] + ': addressed risk has unresolved source fitness; response does not establish risk truth or mitigation.')
        follow = row['follow_up']
        if not isinstance(follow, dict) or set(follow) != {'owner', 'target_date', 'purpose'} or any(not _text(follow[f]) for f in ('owner', 'purpose')):
            raise ValueError('Owned dated review/evidence follow-up required.')
        target = _date(follow['target_date'])
        if target <= _date(review['period']['end']): raise ValueError('Follow-up must follow the selected reporting period.')
        overdue = target < as_of
        if overdue: gap(row['id'] + ': follow-up is overdue and unverified, not failed or completed.')
        rows.append({'record': copy.deepcopy(row), 'horizon': horizon, 'source_context': [copy.deepcopy(known[e]) for e in row['evidence_ids']],
            'linked_impacts': [copy.deepcopy(impacts[i]) for i in impact_ids], 'addressed_risks': addressed,
            'mechanism_source_supported': supported, 'candidate_status': 'sourced_conditional_candidate' if supported else 'investigation_required',
            'likelihood': likelihood, 'magnitude': magnitude, 'dependencies': conditions, 'trade_offs': trade_rows,
            'follow_up_status': 'overdue_unverified' if overdue else 'proposed_unsent',
            'effect_realized': False, 'mitigation_verified': False, 'delivery_feasible': False, 'implementation_authorized': False})
    if not register or not review['coverage_complete']: gap(label + ' identification coverage is empty or incomplete; absence is not proof of no risks/opportunities.')
    result['review_requirements'].append({'id': result['id']+'-identification-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
        'reason': 'Review source fitness, causal/effect pathways, horizons, dependencies and trade-offs before strategy or action decisions.',
        'scope': review['scope'], 'reviewer_role': 'Sustainability strategy reviewer and accountable owner', 'status': 'open', 'resolution': None})
    return {'identification_review': copy.deepcopy(review), 'records': rows, 'material_issue_register': copy.deepcopy(materiality),
        'risk_register': copy.deepcopy(risk_report), 'financial_materiality': None, 'risk_acceptance': None, 'selected_opportunity': None,
        'ranking': None, 'portfolio_benefit': None, 'framework_conformance': False, 'public_claim_authorized': False}
