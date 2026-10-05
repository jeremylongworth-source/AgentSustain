"""Separate source-attributed transition drivers; no applicability or loss determination."""
import copy

from .climate_tools import _fields, _sources, _support, _reviewed, _text, _window


FAMILIES = {
    'identify-policy-risk': 'policy',
    'identify-market-risk': 'market',
    'identify-technology-risk': 'technology',
    'identify-reputation-risk': 'reputation',
}
CONTEXT = {
    'policy': {'instrument', 'jurisdiction', 'source_described_status', 'effective_period', 'applicability_conditions'},
    'market': {'signal_kind', 'market_segment', 'geography', 'comparison_basis', 'signal_period'},
    'technology': {'technology', 'version', 'source_described_maturity', 'service_requirements', 'dependencies'},
    'reputation': {'statement_kind', 'affected_groups', 'representation_basis', 'response_observed'},
}


def identify(state, skill, parameters, refs, result, gap):
    family = FAMILIES[skill]
    review = parameters['transition_review']
    as_of = _reviewed(state, review, refs, 'source_transition_register')
    raw = parameters['drivers']
    if not isinstance(raw, list):
        raise ValueError('Explicit selected transition-driver list required.')
    rows = []; ids = set()
    for driver in raw:
        _fields(driver, {'id', 'name', 'climate_transition_link', 'mechanism', 'affected_scope', 'owner',
            'scenario', 'horizon', 'context', 'evidence_ids', 'evidence_fit', 'observed_date', 'source_fragment', 'limitations'},
            ('id', 'name', 'climate_transition_link', 'mechanism', 'affected_scope', 'owner', 'source_fragment', 'limitations'))
        if driver['id'] in ids:
            raise ValueError('Distinct selected transition-driver IDs required.')
        ids.add(driver['id'])
        if driver['scenario'] is not None and not _text(driver['scenario']):
            raise ValueError('Scenario must be a supplied substantive name or null, without inferred certainty.')
        horizon = _window(driver['horizon']) if driver['horizon'] is not None else None
        if horizon is None:
            gap(driver['id'] + ': transition horizon unknown; no short/medium/long default or exposure forecast.')
        context = driver['context']
        texts = CONTEXT[family] - {'effective_period', 'signal_period', 'response_observed'}
        _fields(context, CONTEXT[family], texts)
        if family == 'policy':
            if context['source_described_status'] not in {'proposed', 'adopted', 'in_force', 'repealed', 'unknown'}:
                raise ValueError('Explicit source-described instrument status required; no legal status inference.')
            effective = _window(context['effective_period']) if context['effective_period'] is not None else None
            if effective is None:
                gap(driver['id'] + ': instrument effective period unknown; no applicability or obligation inferred.')
            if context['source_described_status'] in {'proposed', 'unknown', 'repealed'}:
                gap(driver['id'] + ': proposed/unknown/repealed instrument is not a current applicable obligation.')
            gap(driver['id'] + ': qualified current primary-source and jurisdiction/applicability review required; source status is not a legal determination.')
        elif family == 'market':
            if context['signal_kind'] not in {'demand', 'price', 'financing', 'supply', 'unknown'}:
                raise ValueError('Explicit demand/price/financing/supply/unknown signal required.')
            if context['signal_period'] is not None:
                _window(context['signal_period'])
            else:
                gap(driver['id'] + ': market signal period unknown; no price/demand forecast or transferable trend.')
            gap(driver['id'] + ': selected market segment/comparison and scenario require review; no organization revenue, cost or financing effect quantified.')
        elif family == 'technology':
            if context['source_described_maturity'] not in {'proposed', 'pilot', 'commercial', 'unknown'}:
                raise ValueError('Explicit source-described technology maturity required.')
            gap(driver['id'] + ': service equivalence, maturity, infrastructure, lifetime and deployment constraints require qualified review; no feasible replacement or obsolescence inferred.')
        else:
            if context['statement_kind'] not in {'allegation', 'opinion', 'survey', 'observed_response', 'unknown'}:
                raise ValueError('Explicit attributed reputation statement kind required.')
            if not isinstance(context['response_observed'], bool):
                raise ValueError('Explicit source-described response observation required.')
            gap(driver['id'] + ': attribution, affected-group inclusion, representation and response causation require review; no consensus, misconduct finding or reputation loss inferred.')
        sources = _sources(state, driver['evidence_ids'], refs)
        supported = _support(driver, sources, as_of, gap, driver['id'])
        rows.append(dict(copy.deepcopy(driver), family=family, sources=sources,
            source_support='source_transition_candidate' if supported else 'unverified',
            organization_exposure_verified=False, likelihood=None, financial_effect=None, risk_score=None,
            legal_applicability_determined=False, compliance_determined=False, response_causation_verified=False,
            replacement_feasible=False, risk_accepted=False, implementation_authorized=False))
    if not rows or not review['coverage_complete'] or review['exclusions']:
        gap('Selected ' + family + ' driver coverage incomplete; omissions do not establish absent transition risk.')
    return {'family': family, 'drivers': rows, 'transition_review': copy.deepcopy(review),
        'review_sources': _sources(state, review['evidence_ids'], refs),
        'organization_exposure': None, 'organization_risk_score': None, 'legal_determination': False,
        'risk_accepted': False, 'implementation_authorized': False, 'public_claim_authorized': False}
