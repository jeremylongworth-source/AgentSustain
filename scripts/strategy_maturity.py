"""Selected-scope cumulative maturity rubric; no default scale or certification."""
import copy

from .strategy_tools import _reviewed, _text
from .strategy_stakeholders import _date, evidence


def assess(state, parameters, refs, result, gap):
    known = {e['id']: e for e in state['evidence']}
    review = parameters['assessment_review']
    _reviewed(state, review, refs, ('scope', 'selection_basis', 'limitations'))
    if review.get('period') != state['reporting_period'] or not isinstance(review.get('coverage_complete'), bool):
        raise ValueError('Matched assessment period and explicit selected coverage required.')
    as_of = _date(review.get('as_of_date'))
    if as_of < _date(review['period']['start']):
        raise ValueError('Assessment cannot predate its reporting period.')
    rubric = parameters['rubric']
    if (not isinstance(rubric, dict) or set(rubric) != {'id', 'version', 'name', 'evidence_ids', 'dimensions'}
            or any(not _text(rubric[f]) for f in ('id', 'version', 'name'))):
        raise ValueError('Explicit versioned sourced maturity rubric required.')
    evidence(rubric['evidence_ids'], known, refs)
    if not rubric['evidence_ids']:
        raise ValueError('Rubric source required; no model-generated default maturity scale.')
    if not _text(review.get('rubric_fit_rationale')):
        raise ValueError('Substantive rubric source and selected-scope fitness rationale required.')
    if review.get('rubric_evidence_fit') != 'reviewed_supporting':
        raise ValueError('Rubric source fitness is unverified or irrelevant; no maturity levels may be assessed.')
    dimensions = rubric['dimensions']; criteria = {}; dimension_ids = set()
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError('Nonempty scoped rubric dimensions required.')
    for dim in dimensions:
        if (not isinstance(dim, dict) or set(dim) != {'id', 'name', 'levels'}
                or any(not _text(dim[f]) for f in ('id', 'name')) or dim['id'] in dimension_ids
                or not isinstance(dim['levels'], list) or not dim['levels']):
            raise ValueError('Distinct named dimensions and ordered nonempty levels required.')
        dimension_ids.add(dim['id']); level_ids = set()
        for level in dim['levels']:
            if (not isinstance(level, dict) or set(level) != {'id', 'label', 'criteria'}
                    or any(not _text(level[f]) for f in ('id', 'label')) or level['id'] in level_ids
                    or not isinstance(level['criteria'], list) or not level['criteria']):
                raise ValueError('Distinct ordered level IDs and explicit cumulative criteria required.')
            level_ids.add(level['id'])
            for criterion in level['criteria']:
                if (not isinstance(criterion, dict) or set(criterion) != {'id', 'requirement'}
                        or any(not _text(criterion[f]) for f in ('id', 'requirement')) or criterion['id'] in criteria):
                    raise ValueError('Globally distinct criterion IDs and substantive requirements required.')
                criteria[criterion['id']] = criterion
    observations = parameters['observations']
    if not isinstance(observations, list):
        raise ValueError('Explicit observations list required; absent observations remain unknown.')
    rows = {}
    for obs in observations:
        fields = {'criterion_id', 'status', 'evidence_ids', 'source_fragment', 'evidence_fit', 'observed_date', 'rationale', 'follow_up'}
        if (not isinstance(obs, dict) or set(obs) != fields or obs['criterion_id'] not in criteria or obs['criterion_id'] in rows
                or obs['status'] not in {'demonstrated', 'not_demonstrated', 'planned', 'unknown', 'conflicting'}
                or obs['evidence_fit'] not in {'reviewed_supporting', 'unverified', 'irrelevant'}
                or any(not _text(obs[f]) for f in ('source_fragment', 'rationale'))):
            raise ValueError('Distinct known criterion observations with status, source fit and rationale required.')
        evidence(obs['evidence_ids'], known, refs)
        when = _date(obs['observed_date']) if obs['observed_date'] is not None else None
        if when and when > min(as_of, _date(review['period']['end'])):
            raise ValueError('Practice observation postdates assessment period or as-of date.')
        current = when is not None and when >= _date(review['period']['start'])
        supported = bool(obs['evidence_ids']) and obs['evidence_fit'] == 'reviewed_supporting' and current
        attained = supported and obs['status'] == 'demonstrated'
        follow = obs['follow_up']
        if (not isinstance(follow, dict) or set(follow) != {'owner', 'target_date', 'purpose'}
                or any(not _text(follow[f]) for f in ('owner', 'purpose'))):
            raise ValueError('Owned dated evidence/improvement follow-up required.')
        target = _date(follow['target_date'])
        if target <= _date(review['period']['end']):
            raise ValueError('Follow-up must follow assessment period.')
        overdue = target < as_of
        if not attained:
            gap('Criterion ' + obs['criterion_id'] + ' remains ' + obs['status'] + ' or lacks current supporting evidence; unknown is not absent practice.')
        if overdue:
            gap('Criterion ' + obs['criterion_id'] + ' follow-up is overdue and unverified, not completed or failed.')
        rows[obs['criterion_id']] = {'observation': copy.deepcopy(obs), 'source_context': [copy.deepcopy(known[e]) for e in obs['evidence_ids']],
            'current_source_supported': supported, 'criterion_demonstrated': attained,
            'follow_up_status': 'overdue_unverified' if overdue else 'proposed_unsent', 'implementation_verified': False}
    for ident in criteria.keys() - rows.keys():
        gap('Criterion ' + ident + ' has no observation; practice remains unknown.')
        rows[ident] = {'observation': None, 'source_context': [], 'current_source_supported': False, 'criterion_demonstrated': False,
            'follow_up_status': 'evidence_required', 'implementation_verified': False}
    profiles = []
    for dim in dimensions:
        cumulative = []; levels = []; highest = None
        for level in dim['levels']:
            cumulative.extend(c['id'] for c in level['criteria'])
            attained = all(rows[i]['criterion_demonstrated'] for i in cumulative)
            levels.append({'id': level['id'], 'label': level['label'], 'cumulative_criteria': list(cumulative), 'demonstrated': attained})
            if attained:
                highest = level['id']
        profiles.append({'dimension_id': dim['id'], 'levels': levels, 'highest_supported_level': highest,
            'interpretation': 'No supported level is unknown/unmet criteria, not a zero maturity score.'})
    if not review['coverage_complete']:
        gap('Selected maturity assessment coverage is incomplete; no organization-wide maturity conclusion.')
    result['review_requirements'].append({'id': result['id']+'-maturity-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
        'reason': 'Review rubric fitness, scope, current practice evidence, contradictions and coverage before strategy use.',
        'scope': review['scope'], 'reviewer_role': 'Sustainability practice reviewer and accountable owner', 'status': 'open', 'resolution': None})
    return {'rubric': copy.deepcopy(rubric), 'assessment_review': copy.deepcopy(review), 'criteria': rows, 'dimension_profiles': profiles,
        'overall_score': None, 'organization_maturity': None, 'environmental_performance': None, 'certification': None,
        'coverage_verified': False, 'public_claim_authorized': False, 'implementation_authorized': False}
