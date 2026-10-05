"""Source-linked selected organization/transition pathways, not quantified effects."""
import copy

from .climate_tools import _fields, _reproduce, _reviewed, _sources, _support, _text, _window
from .climate_assessment import _scope
from .climate_transition import FAMILIES


def assess(state, parameters, refs, result, gap):
    review = parameters['exposure_review']
    as_of = _reviewed(state, review, refs, 'source_transition_exposure')
    selections = parameters['driver_results']
    if not isinstance(selections, list):
        raise ValueError('Explicit selected transition result list required.')
    snapshots = []; drivers = {}; families = set(); results = set()
    for selected in selections:
        _fields(selected, {'result_id', 'skill'}, ('result_id', 'skill'))
        if selected['skill'] not in FAMILIES or selected['result_id'] in results:
            raise ValueError('Distinct current transition-family results required.')
        results.add(selected['result_id'])
        source = _reproduce(state, selected['result_id'], refs, selected['skill'])
        _scope(review, source['transition_review'], as_of)
        families.add(source['family'])
        snapshots.append({'result_id':selected['result_id'], 'skill':selected['skill'], 'snapshot':source})
        for driver in source['drivers']:
            drivers[selected['result_id'], driver['id']] = driver
    for family in sorted(set(FAMILIES.values()) - families):
        gap(family + ': transition-driver family not selected; risk coverage remains unknown.')
    raw = parameters['subjects']
    if not isinstance(raw, list):
        raise ValueError('Explicit organization activity/asset/dependency subject list required.')
    subjects = {}; subject_fit = {}; boundary = set(state['organizational_boundary']['facility_ids'])
    for subject in raw:
        _fields(subject, {'id','name','kind','boundary_relation','facility_id','service_scope','owner','activity_period',
            'evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
            ('id','name','service_scope','owner','source_fragment','limitations'))
        if (subject['id'] in subjects or subject['kind'] not in {'activity','asset','service_dependency','financial_product','people_group'}
                or subject['boundary_relation'] not in {'direct','value_chain'}
                or (subject['boundary_relation']=='direct' and subject['facility_id'] not in boundary)
                or (subject['boundary_relation']=='value_chain' and subject['facility_id'] is not None)):
            raise ValueError('Distinct subjects with selected direct facility or explicit external value-chain relation required.')
        if subject['activity_period'] is not None:
            _window(subject['activity_period'])
        else:
            gap(subject['id'] + ': activity period unknown; future presence cannot be inferred.')
        sources = _sources(state, subject['evidence_ids'], refs)
        subject_fit[subject['id']] = _support(subject, sources, as_of, gap, subject['id'])
        subjects[subject['id']] = dict(copy.deepcopy(subject), sources=sources)
    raw = parameters['observations']
    if not isinstance(raw, list):
        raise ValueError('Explicit selected subject/driver exposure observations required.')
    rows = []; ids = set(); pairs = set()
    for obs in raw:
        _fields(obs, {'id','subject_id','driver_result_id','driver_id','status','mechanism','effect_channels',
            'scenario','horizon','context_review','evidence_ids','evidence_fit','observed_date','source_fragment','limitations'},
            ('id','subject_id','driver_result_id','driver_id','mechanism','source_fragment','limitations'))
        key = obs['driver_result_id'], obs['driver_id']; pair = obs['subject_id'], *key
        if (obs['id'] in ids or pair in pairs or key not in drivers or obs['subject_id'] not in subjects
                or obs['status'] not in {'documented','conditional','unknown'}):
            raise ValueError('Distinct known subject/driver pairs and explicit documented/conditional/unknown observation required.')
        ids.add(obs['id']); pairs.add(pair)
        driver = drivers[key]; subject = subjects[obs['subject_id']]
        horizon = _window(obs['horizon']) if obs['horizon'] is not None else None
        if obs['scenario'] != driver['scenario'] or horizon != driver['horizon']:
            raise ValueError('Exposure must retain exact selected transition scenario and horizon, including unknowns.')
        channels = obs['effect_channels']
        if (not isinstance(channels, list) or len(channels)!=len(set(channels))
                or not set(channels)<={'operating_cost','demand','asset_value','financing','service_availability','stakeholder_relationship'}):
            raise ValueError('Explicit distinct qualitative effect channels required; no numerical financial effects.')
        if not channels:
            gap(obs['id'] + ': potential organization effect channels unassessed.')
        context = obs['context_review']
        _fields(context, {'confirmed','driver_fit','subject_fit','link_fit','driver_scope','subject_scope','evidence_ids','rationale'},
            ('driver_scope','subject_scope','rationale'))
        if (not isinstance(context['confirmed'], bool) or any(context[f] not in {'reviewed_supporting','unverified','irrelevant'} for f in ['driver_fit','subject_fit','link_fit'])
                or context['driver_scope']!=driver['affected_scope'] or context['subject_scope']!=subject['service_scope']):
            raise ValueError('Separate driver/subject/link fitness and exact original service scopes required.')
        context_sources = _sources(state, context['evidence_ids'], refs)
        if not set(driver['evidence_ids'] + subject['evidence_ids'] + obs['evidence_ids'])<=set(context['evidence_ids']):
            raise ValueError('Context review must retain actual selected driver, subject and link evidence.')
        sources = _sources(state, obs['evidence_ids'], refs)
        supported = _support(obs, sources, as_of, gap, obs['id'])
        activity = subject['activity_period']
        temporal = ('unknown' if activity is None or horizon is None else
            'overlapping' if max(activity['start'],horizon['start'])<=min(activity['end'],horizon['end']) else 'not_overlapping')
        fit = (supported and subject_fit[subject['id']] and driver['source_support']=='source_transition_candidate'
            and obs['status'] in {'documented','conditional'} and context['confirmed'] and bool(context_sources)
            and all(context[f]=='reviewed_supporting' for f in ['driver_fit','subject_fit','link_fit']))
        status = 'conditional_exposure_candidate' if fit and temporal=='overlapping' else 'unverified'
        if status=='unverified':
            gap(obs['id'] + ': actual source/link fitness or documented temporal overlap unresolved; exposure is unknown, not absent.')
        if activity and horizon and not activity['start']<=horizon['start']<=horizon['end']<=activity['end']:
            gap(obs['id'] + ': documented activity does not cover full transition horizon; no future presence assumed.')
        gap(obs['id'] + ': qualified applicability/service/causal review and potential effects remain open; no obligation, probability, loss or risk acceptance.')
        rows.append(dict(copy.deepcopy(obs), sources=sources, context_sources=context_sources, temporal_relation=temporal,
            assessment_status=status, organization_exposure_verified=False, legal_applicability_determined=False,
            financial_effect=None, probability=None, risk_score=None, risk_accepted=False, implementation_authorized=False))
    for subject_id in sorted(subjects):
        for result_id,driver_id in sorted(drivers):
            if (subject_id,result_id,driver_id) not in pairs:
                gap(subject_id+' / '+result_id+' / '+driver_id+': selected exposure pair omitted; unknown is not absence.')
    if not subjects or not drivers or not rows or not review['coverage_complete'] or review['exclusions']:
        gap('Selected transition-exposure coverage incomplete; no organization exposure total or aggregate effects.')
    return {'driver_snapshots':snapshots,'subjects':list(subjects.values()),'observations':rows,
        'exposure_review':copy.deepcopy(review),'review_sources':_sources(state,review['evidence_ids'],refs),
        'organization_total':None,'financial_effect':None,'exposure_verified':False,'legal_determination':False,
        'risk_accepted':False,'implementation_authorized':False,'public_claim_authorized':False}
