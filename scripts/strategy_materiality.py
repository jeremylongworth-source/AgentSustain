"""Conditional impact-significance candidates; no netting or final materiality."""
import copy

from .strategy_tools import _reviewed, _reproduce, _text
from .strategy_stakeholders import _date, evidence
from .supplier_risk import _anchors


def identify(state, parameters, refs, result, gap):
    known = {e['id']: e for e in state['evidence']}
    review = parameters['materiality_review']
    _reviewed(state, review, refs, ('scope', 'context', 'identification_method', 'coverage_limitations', 'model_fit_rationale'))
    if (review.get('period') != state['reporting_period'] or not isinstance(review.get('coverage_complete'), bool)
            or review.get('model_evidence_fit') != 'reviewed_supporting'):
        raise ValueError('Matched period, coverage and substantive supporting significance-model fitness required.')
    as_of = _date(review.get('as_of_date'))
    if as_of < _date(review['period']['start']):
        raise ValueError('Materiality review cannot predate its period.')
    model = parameters['significance_model']
    fields = {'id', 'version', 'evidence_ids', 'anchors', 'thresholds', 'rule'}
    if not isinstance(model, dict) or set(model) != fields or any(not _text(model[f]) for f in ('id', 'version')) or model['rule'] != 'separate_impact_thresholds':
        raise ValueError('Explicit versioned sourced separate-impact threshold method required.')
    evidence(model['evidence_ids'], known, refs)
    if not model['evidence_ids']:
        raise ValueError('Significance method source required; no default thresholds.')
    names = {'severity', 'likelihood', 'scale', 'scope'}
    if not isinstance(model['anchors'], dict) or set(model['anchors']) != names:
        raise ValueError('Explicit severity, likelihood, benefit scale and scope ordinal anchors required.')
    anchors = {name: _anchors(model['anchors'][name]) for name in names}
    thresholds = model['thresholds']
    keys = {'negative_actual_severity', 'negative_potential_high_severity', 'negative_potential_severity',
        'negative_potential_likelihood', 'human_rights_severity', 'positive_scale', 'positive_scope', 'positive_likelihood'}
    if not isinstance(thresholds, dict) or set(thresholds) != keys:
        raise ValueError('Every separate impact threshold must be explicitly supplied.')
    for key, value in thresholds.items():
        axis = 'severity' if 'severity' in key else 'likelihood' if 'likelihood' in key else 'scale' if key.endswith('scale') else 'scope'
        if type(value) is not int or value not in anchors[axis]:
            raise ValueError('Threshold must resolve to its declared ordinal anchor.')
    if thresholds['negative_potential_high_severity'] < thresholds['negative_potential_severity']:
        raise ValueError('High-severity override cannot be below the combined negative threshold.')
    stakeholder = None
    if parameters['stakeholder_result_id'] is not None:
        _, stakeholder = _reproduce(state, parameters['stakeholder_result_id'], 'map-stakeholders', refs)
        if stakeholder['mapping_review']['scope'] != review['scope'] or stakeholder['mapping_review']['period'] != review['period']:
            raise ValueError('Stakeholder dependency must match selected scope and period.')
    else:
        gap('No stakeholder map linked; affected-group perspectives and missing voices require review.')
    topics = parameters['topics']; topic_ids = set(); topic_rows = []
    if not isinstance(topics, list) or not topics:
        raise ValueError('Explicit nonempty topic register required.')
    for topic in topics:
        if (not isinstance(topic, dict) or set(topic) != {'id', 'name', 'context', 'evidence_ids'}
                or any(not _text(topic[f]) for f in ('id', 'name', 'context')) or topic['id'] in topic_ids):
            raise ValueError('Distinct contextualized topic IDs and source references required.')
        topic_ids.add(topic['id']); evidence(topic['evidence_ids'], known, refs)
        if not topic['evidence_ids']:
            gap(topic['id'] + ': topic identification has no sourced context; grouping requires review.')
        topic_rows.append(copy.deepcopy(topic))
    impacts = parameters['impacts']
    if not isinstance(impacts, list):
        raise ValueError('Impact register required; empty does not prove no material issues.')
    rows = []; ids = set()
    for impact in impacts:
        fields = {'id', 'topic_id', 'description', 'direction', 'status', 'human_rights', 'relationship', 'affected_context',
            'evidence_ids', 'evidence_fit', 'source_fragment', 'observed_date', 'scale', 'scope', 'irremediability',
            'severity_rank', 'likelihood_rank', 'scale_rank', 'scope_rank', 'assessment_rationale', 'follow_up'}
        if (not isinstance(impact, dict) or set(impact) != fields or impact['id'] in ids or impact['topic_id'] not in topic_ids
                or any(not _text(impact[f]) for f in ('id', 'description', 'affected_context', 'source_fragment', 'scale', 'scope', 'irremediability', 'assessment_rationale'))
                or impact['direction'] not in {'negative', 'positive'} or impact['status'] not in {'actual', 'potential', 'unknown'}
                or type(impact['human_rights']) is not bool or impact['relationship'] not in {'caused', 'contributed', 'directly_linked', 'unknown'}
                or impact['evidence_fit'] not in {'reviewed_supporting', 'proxy', 'unverified', 'irrelevant'}):
            raise ValueError('Exact distinct contextualized impact records and declared source fitness required.')
        ids.add(impact['id']); evidence(impact['evidence_ids'], known, refs)
        for axis in names:
            rank = impact[axis+'_rank']
            if rank is not None and (type(rank) is not int or rank not in anchors[axis]):
                raise ValueError('Impact ordinal rating must match declared anchor or remain null.')
        if impact['status'] == 'actual' and impact['likelihood_rank'] is not None:
            raise ValueError('Actual impacts have no occurrence likelihood rating.')
        if impact['direction'] == 'positive' and impact['severity_rank'] is not None:
            raise ValueError('Positive benefit scale/scope are separate from adverse severity.')
        if impact['direction'] == 'negative' and (impact['scale_rank'] is not None or impact['scope_rank'] is not None):
            raise ValueError('Negative significance uses reviewed severity with separate harm descriptors, not benefit scores.')
        when = _date(impact['observed_date']) if impact['observed_date'] is not None else None
        if when and when > min(as_of, _date(review['period']['end'])):
            raise ValueError('Impact observation postdates selected period or review as-of.')
        current = when is not None and when >= _date(review['period']['start'])
        supported = bool(impact['evidence_ids']) and impact['evidence_fit'] == 'reviewed_supporting' and current and impact['status'] != 'unknown'
        sig = None; basis = 'Evidence, timing or occurrence status unresolved.'
        if supported:
            severity = impact['severity_rank']; likelihood = impact['likelihood_rank']
            if impact['direction'] == 'negative':
                if severity is not None:
                    if impact['status'] == 'actual':
                        sig = severity >= thresholds['negative_actual_severity']; basis = 'Actual adverse severity threshold.'
                    elif impact['human_rights']:
                        sig = severity >= thresholds['human_rights_severity']; basis = 'Potential human-rights adverse severity takes precedence; low likelihood does not discount it.'
                    elif severity >= thresholds['negative_potential_high_severity']:
                        sig = True; basis = 'Potential adverse high-severity override.'
                    elif likelihood is not None:
                        sig = severity >= thresholds['negative_potential_severity'] and likelihood >= thresholds['negative_potential_likelihood']; basis = 'Potential adverse severity and likelihood thresholds.'
            else:
                scale = impact['scale_rank']; scope = impact['scope_rank']
                if scale is not None and scope is not None and (impact['status'] == 'actual' or likelihood is not None):
                    sig = scale >= thresholds['positive_scale'] and scope >= thresholds['positive_scope']
                    if impact['status'] == 'potential': sig = sig and likelihood >= thresholds['positive_likelihood']
                    basis = 'Separate positive scale/scope and potential occurrence thresholds; no harm offset.'
        if sig is None:
            gap(impact['id'] + ': significance remains unresolved; no rating means unknown, not immaterial.')
        if impact['status'] == 'potential' and impact['likelihood_rank'] is None:
            gap(impact['id'] + ': potential occurrence likelihood remains unknown even where severity warrants candidacy.')
        if impact['relationship'] == 'unknown': gap(impact['id'] + ': organizational relationship to impact is unresolved.')
        follow = impact['follow_up']
        if not isinstance(follow, dict) or set(follow) != {'owner', 'target_date', 'purpose'} or any(not _text(follow[f]) for f in ('owner', 'purpose')):
            raise ValueError('Owned dated impact evidence/review follow-up required.')
        target = _date(follow['target_date'])
        if target <= _date(review['period']['end']): raise ValueError('Follow-up must follow screening period.')
        overdue = target < as_of
        if overdue: gap(impact['id'] + ': follow-up is overdue and unverified.')
        rows.append({'impact': copy.deepcopy(impact), 'source_context': [copy.deepcopy(known[e]) for e in impact['evidence_ids']],
            'source_supported': supported, 'significance_threshold_met': sig, 'basis': basis,
            'follow_up_status': 'overdue_unverified' if overdue else 'proposed_unsent'})
    candidates = []
    for topic in topic_rows:
        if stakeholder and not stakeholder['issue_perspectives'].get(topic['id']):
            gap(topic['id'] + ': linked map has no issue-specific perspective; absence is not stakeholder agreement.')
        selected = [r for r in rows if r['impact']['topic_id'] == topic['id']]
        significant = [r['impact']['id'] for r in selected if r['significance_threshold_met'] is True]
        unknown = [r['impact']['id'] for r in selected if r['significance_threshold_met'] is None]
        if not selected: gap(topic['id'] + ': no impact evidence; absence is not immateriality.')
        candidates.append({'topic': topic, 'significant_impact_ids': significant, 'unresolved_impact_ids': unknown,
            'candidate_status': 'proposed_significant' if significant else 'investigation_required' if unknown or not selected else 'below_supplied_threshold',
            'stakeholder_perspectives': copy.deepcopy(stakeholder['issue_perspectives'].get(topic['id'], [])) if stakeholder else [],
            'final_materiality': None})
    if not review['coverage_complete']: gap('Selected material-issue coverage is incomplete; whole-organization determination remains open.')
    result['review_requirements'].append({'id': result['id']+'-materiality-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
        'reason': 'Review significance method, impact source fitness, affected-group gaps, topic grouping and coverage before materiality determination.',
        'scope': review['scope'], 'reviewer_role': 'Impact/materiality specialist and accountable decision owner', 'status': 'open', 'resolution': None})
    return {'materiality_review': copy.deepcopy(review), 'significance_model': copy.deepcopy(model), 'impacts': rows, 'topic_candidates': candidates,
        'stakeholder_map': copy.deepcopy(stakeholder), 'financial_materiality': None, 'final_material_topics': None,
        'positive_negative_netting': False, 'materiality_approved': False, 'framework_conformance': False, 'public_claim_authorized': False}
