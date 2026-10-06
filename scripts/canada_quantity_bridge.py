"""Bind primary-profile arithmetic and supplied uncertainty bounds to a draft screen."""
import copy
import hashlib
import json
from decimal import localcontext
from .climate_tools import _fields,_sources,_date
from .contract_validation import validate_state
from .data_tools import number,serialize
from .gas_conversion import _diagnostic
from .jurisdiction_tools import read_pinned_pack
from .source_species_ledger import build_source_species_ledger
from .canada_ghgrp import screen_canada_ghgrp
from .manager_workflow import _empty
from .state_proposal import propose


PROFILE='canada/ghgrp/threshold-species-profile-1.json'
GWP='canada/ghgrp/schedule1-gwp-transcription-1.json'


def run_canada_quantity_bridge(state,p):
    validate_state(state);_fields(p,{'ledger_parameters','screen_parameters','subject_id','quantity_review','gwp_pin','result_id'},('subject_id','result_id'))
    if not isinstance(p['ledger_parameters'],list) or not p['ledger_parameters']:raise ValueError('Explicit nonempty selected facility ledgers required.')
    registry=read_pinned_pack(p['gwp_pin'])
    if p['gwp_pin']['path']!=GWP:raise ValueError('Select the explicit GHGRP Schedule 1 transcription.')
    sp=copy.deepcopy(p['screen_parameters']);subjects=[s for s in sp['subjects'] if s['id']==p['subject_id']]
    if len(subjects)!=1:raise ValueError('Exact selected subject required.')
    subject=subjects[0];review=p['quantity_review'];when=_date(sp['screening_review']['as_of_date'])
    _fields(review,{'boundary_id','period','as_of_date','evidence_ids','evidence_fit','quantity_basis','method_evidence_fit','range','scope','reviewer_role','rationale'},('quantity_basis','scope','reviewer_role','rationale'))
    if review['boundary_id']!=state['organizational_boundary']['id'] or review['period']!=state['reporting_period'] or review['as_of_date']!=sp['screening_review']['as_of_date'] or review['quantity_basis']!='emitted_species_mass':raise ValueError('Matched emitted-species boundary/period/assessment required; captured throughput is not emissions.')
    if review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'} or review['method_evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:raise ValueError('Explicit source and method fitness required.')
    ids=[lp['result_id'] for lp in p['ledger_parameters']]+[sp['result_id'],p['result_id']]
    if len(ids)!=len(set(ids)) or set(ids)&{r['id'] for r in state['results']}:raise ValueError('Fresh distinct ledger/screen/bridge IDs required.')
    working=copy.deepcopy(state);reports=[];views=[];complete=True;reasons=[];facilities=[];seen=set();total=number(0)
    with localcontext() as context:
        context.prec=34
        for lp in p['ledger_parameters']:
            if lp['profile_pin']['path']!=PROFILE:raise ValueError('Full explicit Canadian source/species profile required, not a corporate or selected fictional roster.')
            profile=read_pinned_pack(lp['profile_pin'])
            if profile['basis']!=registry['basis'] or profile['time_horizon_years']!=registry['time_horizon_years'] or set(profile['gases'])!=set(registry['values_kg_co2e_per_kg_species']):raise ValueError('Profile and GWP transcription must describe the same complete species/basis/horizon.')
            facility=lp['coverage_review']['facility_id'];facilities.append(facility)
            if lp['coverage_review']['as_of_date']!=review['as_of_date']:raise ValueError('Ledger and quantity assessment dates must match exactly.')
            out=build_source_species_ledger(working,copy.deepcopy(lp));working=out['proposal']['state'];ledger=out['result'];record=_diagnostic(ledger,'SOURCE_SPECIES_LEDGER')
            reports.append(record);views.append({'result_id':ledger['id'],'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(ledger,sort_keys=True).encode()).hexdigest()})
            eligible=record['declared_source_species_coverage_reproduced'] and ledger['status']!='blocked' and len(ledger['metrics'])==1
            for row in record['rows']:
                if not row['resolved']:eligible=False;continue
                quantity=row['source_quantity_snapshot']
                gwp=quantity['gwp_snapshot'];expected=registry['values_kg_co2e_per_kg_species'][row['gas']]
                if (number(gwp['value'])!=number(expected) or gwp['source']['locator']!=registry['source']['locator'] or gwp['source']['version']!=registry['version']):eligible=False;reasons.append('Species GWP/source/version differs from the selected primary transcription.')
                if row['input']['status']=='converted':identity=quantity['gas_report_snapshot']['activity_snapshot']['evidence_ids']
                else:identity=quantity.get('measured_metric_snapshot',quantity.get('zero_metric_snapshot'))['evidence_ids']
                pairs={(e,row['gas']) for e in identity}
                if pairs&seen:eligible=False;reasons.append('Shared source/species evidence across facility ledgers; no implicit partition or duplicate counting.')
                seen.update(pairs)
            if eligible:total+=number(ledger['metrics'][0]['value'])
            else:complete=False;reasons.append('A selected full-profile ledger is incomplete or unfit; no known-subtotal threshold fallback.')
    if len(facilities)!=len(set(facilities)) or set(facilities)!=set(subject['facility_ids']):raise ValueError('Distinct ledgers must exactly cover the selected subject facility roster.')
    refs=set();primary=_sources(working,review['evidence_ids'],refs)
    fit=(review['evidence_fit']=='reviewed_supporting' and review['method_evidence_fit']=='reviewed_supporting' and bool(primary)
        and all(e['boundary_id']==review['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in primary))
    bounds=review['range'];bounds_fit=False;bound_refs=[]
    with localcontext() as context:
        context.prec=34;tonnes=serialize(total/number(1000)) if complete else None
    if bounds is not None:
        _fields(bounds,{'lower','upper','unit','evidence_ids','evidence_fit','rationale'},('unit','rationale'))
        lower,upper=number(bounds['lower']),number(bounds['upper'])
        if lower<0 or upper<lower or bounds['unit']!='t CO2e' or bounds['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:raise ValueError('Explicit nonnegative ordered sourced tonne-CO2e bounds required.')
        evidence=_sources(working,bounds['evidence_ids'],refs);bound_refs=list(bounds['evidence_ids'])
        bounds_fit=(bounds['evidence_fit']=='reviewed_supporting' and bool(evidence) and tonnes is not None and lower<=number(tonnes)<=upper
            and all(e['boundary_id']==review['boundary_id'] and e['period']==review['period'] and e['unit']=='t CO2e' and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in evidence))
    supported=complete and fit and bounds_fit
    facts=[f for f in sp['facts'] if not (f['subject_id']==p['subject_id'] and f['attribute_id']=='threshold_emissions')]
    facts.append({'subject_id':p['subject_id'],'attribute_id':'threshold_emissions','value':{'lower':bounds['lower'],'upper':bounds['upper']} if supported else None,
        'unit':'t CO2e','boundary_id':review['boundary_id'],'period':copy.deepcopy(review['period']),'evidence_ids':bound_refs if supported else list(review['evidence_ids']),
        'evidence_fit':'reviewed_supporting' if supported else 'unverified','rationale':review['rationale'],
        'uncertainty':'Externally supplied engineering bounds; no statistical confidence inferred. All original parent uncertainty retained; no authenticated statutory quantity.',
        'coverage_complete':supported})
    subjects[0]['evidence_ids']=list(dict.fromkeys(subjects[0]['evidence_ids']+bound_refs+list(review['evidence_ids'])))
    sp['facts']=facts;screen=screen_canada_ghgrp(working,sp);working=screen['proposal']['state']
    result=_empty(working,'screen-subject-jurisdiction-applicability',p['result_id']);result['evidence_ids']=sorted(refs|set(screen['result']['evidence_ids']));result['status']='partial'
    result['review_states']=list(dict.fromkeys(result['review_states']+['PROFESSIONAL_REVIEW_REQUIRED','LEGAL_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['review_requirements'].append({'id':result['id']+'-quantity-review','state':'PROFESSIONAL_REVIEW_REQUIRED','reason':'Review actual emitted species, full source/facility/method scope, GWP transcription, biomass classification, external bounds and legal threshold fitness.',
        'scope':review['scope'],'reviewer_role':review['reviewer_role'],'status':'open','resolution':None})
    result['review_requirements'].append({'id':result['id']+'-legal-review','state':'LEGAL_REVIEW_REQUIRED','reason':'Assess actual notice applicability, source/facility/operator/method interpretation and any reporting or retention duties; no legal decision is adopted.',
        'scope':review['scope'],'reviewer_role':'Qualified legal reviewer','status':'open','resolution':None})
    if not supported:
        result['data_gaps'].append({'id':result['id']+'-binding-gap','field':'threshold_quantity_binding','reason':'Full quantity/profile/source/method/bounds support missing; original caller threshold amount is withheld.',
            'impact':'No positive or negative emission threshold conclusion from a known subtotal.','remedy':'Reconcile all declared source/species/facility quantities and provide qualified source/method/uncertainty review.'})
    for lp in p['ledger_parameters']:
        owner=next(r for r in working['results'] if r['id']==lp['result_id'])
        result['diagnostics'].extend(copy.deepcopy(d) for d in owner['diagnostics'] if d['code'] in {'EMISSION_FACTOR_REQUIRED','GWP_REQUIRED'})
    report={'execution_contract':'canada-quantity-screen-0.1.0','subject_id':p['subject_id'],'gwp_pin':copy.deepcopy(p['gwp_pin']),'ledger_result_views':views,
        'screen_result_view':{'result_id':screen['result']['id'],'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(screen['result'],sort_keys=True).encode()).hexdigest()},
        'quantity_review':copy.deepcopy(review),'complete_declared_profile_arithmetic_reproduced':complete,'central_quantity_t_co2e':tonnes,
        'supplied_bounds_bound_to_screen':supported,'binding_reasons':reasons,'derived_screen_parameters':sp,
        'source_authenticity_verified':False,'facility_grouping_authenticated':False,'sector_method_applicability_verified':False,
        'regulatory_quantity_verified':False,'legal_applicability_determined':False,'pack_activated_or_approved':False,'commercial_use_authorized':False,'filing_authorized':False}
    result['diagnostics'].extend([{'code':'CANADA_QUANTITY_SCREEN','message':json.dumps(report,sort_keys=True)},{'code':'CANADA_QUANTITY_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Inspect retained quantities/exclusions/uncertainty and obtain source/method/legal/owner review before any actual reporting decision.']
    final=propose(working,result,'Compose sourced declared-profile quantities and external bounds into preliminary Canadian screening')['state'];final['revision']=state['revision']+1;validate_state(final)
    return {'result':result,'proposal':{'base_revision':state['revision'],'reason':'Atomic qualified quantity/screen candidate; no statutory verification or external action','state':final}}
