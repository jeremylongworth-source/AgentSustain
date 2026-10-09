"""Version-pinned disclosure candidates from reproduced core inventory, never conformity."""
import copy
import hashlib
import json
from pathlib import Path

from .contract_validation import ROOT, validate_state
from .data_tools import convert, serialize
from .climate_tools import _date, _fields, _sources, _text
from .ghg_inventory import build_inventory, _diagnostic
from .scope_accounting import compose_scope
from .scope3_accounting import calculate_category
from .state_proposal import propose


CATALOGS={'tnfd-2023-ghg-referral'}
FICTIONAL_CATALOGS={'fictional-review-exercise-1','fictional-review-exercise-2'}
OMITTED_CATALOGS={'ghgp-corporate-2004','ghgp-corporate-2004-amend2013'}


class SourcePackRequired(ValueError):
    pass


def catalog(ident, digest, fixture_mode=False):
    if ident in OMITTED_CATALOGS:
        raise SourcePackRequired('Requested real framework pack is omitted pending exact source rights/review; no replacement standard is inferred.')
    if ident not in CATALOGS | FICTIONAL_CATALOGS: raise ValueError('Supported exact framework/version identifier required.')
    try:
        raw=(ROOT/'standards'/'frameworks'/(ident+'.json')).read_bytes()
    except FileNotFoundError as error:
        raise SourcePackRequired('Selected pinned framework pack is unavailable; provide a permitted reviewed edition.') from error
    if hashlib.sha256(raw).hexdigest()!=digest: raise ValueError('Pinned mapping bytes changed; select a reviewed mapping revision explicitly.')
    value=json.loads(raw)
    if ident in FICTIONAL_CATALOGS:
        if (fixture_mode is not True or value['id']!=ident or value.get('synthetic') is not True
                or value['source_verified'] is not False or value['publication_status']!='fictional'):
            raise ValueError('Original fictional catalogs require explicit fixture mode and fictional/unverified labels.')
        return value
    if value['id']!=ident or not value['source_verified'] or value['publication_status']!='issued' or value.get('synthetic',False):
        raise ValueError('Unverified/draft standard cannot support an issued-version mapping.')
    return value


def _inventory(state, ident, refs, fixture_mode):
    owner=next((r for r in state['results'] if r['id']==ident and r['skill']=='build-ghg-inventory'),None)
    if owner is None or owner['status'] in {'blocked','invalid_input'}: raise ValueError('Current supported inventory required.')
    if any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in owner['diagnostics']):
        raise FactorRequired('Selected inventory has an unresolved emission factor.')
    selection=_diagnostic(owner,'INVENTORY_SELECTION')
    groups={s:[x['result_id'] for x in selection['included'] if x['scope']==s] for s in ['scope_1','scope_2','scope_3']}
    if len(groups['scope_1'])>1 or len(groups['scope_2'])>1: raise ValueError('One account per direct/purchased-energy scope required.')
    sources=[]
    for included in selection['included']:
        source=next((r for r in state['results'] if r['id']==included['result_id']),None)
        if source is None: raise ValueError('Every selected scope reference must resolve to a current core result.')
        code='SCOPE3_CATEGORY' if included['scope']=='scope_3' else 'SCOPE_METHOD'
        record=_diagnostic(source,code); check_id=source['id']+'-disclosure-check'
        while check_id in {r['id'] for r in state['results']}: check_id+='-next'
        args=(state,record['category'] if code=='SCOPE3_CATEGORY' else source['skill'],record['sources'],record['components'],record['coverage_review'],check_id,fixture_mode)
        checked_scope=(calculate_category if code=='SCOPE3_CATEGORY' else compose_scope)(*args)['result']
        if any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in checked_scope['diagnostics']):
            raise FactorRequired('Selected scope account has no defensible factor for this use.')
        metrics=copy.deepcopy(checked_scope['metrics'])
        for m in metrics: m['id']=m['id'].replace(check_id,source['id'],1)
        if (checked_scope['status']=='blocked' or metrics!=source['metrics'] or _diagnostic(checked_scope,code)!=record
                or set(checked_scope['evidence_ids'])!=set(source['evidence_ids'])):
            raise ValueError('Complete scope account metrics, uncertainty, method and evidence lineage must reproduce.')
        sources.append(source)
    verification=ident+'-framework-check'
    while verification in {r['id'] for r in state['results']}: verification+='-next'
    checked=build_inventory(state,next(iter(groups['scope_1']),None),next(iter(groups['scope_2']),None),groups['scope_3'],
        selection['category_screening'],selection['coverage_review'],verification,fixture_mode)['result']
    if any(d['code'] in {'EMISSION_FACTOR_REQUIRED','SYNTHETIC_INVENTORY_BLOCKED'} for d in checked['diagnostics']):
        raise FactorRequired('Core inventory cannot reproduce without a defensible factor.')
    metrics=copy.deepcopy(checked['metrics'])
    for m in metrics: m['id']=m['id'].replace(verification,ident,1)
    if (checked['status']=='blocked' or metrics!=owner['metrics'] or _diagnostic(checked,'INVENTORY_SELECTION')!=selection
            or set(checked['evidence_ids'])!=set(owner['evidence_ids'])):
        raise ValueError('Complete inventory selection, metrics and evidence lineage must reproduce.')
    refs.update(owner['evidence_ids'])
    return owner,selection,sources


class FactorRequired(ValueError):
    pass


def run_framework(state, skill, parameters):
    validate_state(state)
    required={'inventory_result_id','adapters','notes','mapping_review','fixture_mode','result_id'} if skill=='map-framework-disclosures' else {'before','after','mapping_review','result_id'}
    optional={'fixture_mode'} if skill=='compare-framework-mappings' else set()
    if (skill not in {'map-framework-disclosures','compare-framework-mappings'} or not isinstance(parameters,dict)
            or not required <= set(parameters) or set(parameters)-required-optional or not _text(parameters['result_id'])):
        raise ValueError('Supported framework operation with exact parameters required.')
    result={'id':parameters['result_id'],'skill':skill,'contract_version':'0.1.0','status':'partial','review_states':['ADVISORY'],
        'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],'evidence_ids':[],
        'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),'diagnostics':[],'next_actions':[]}
    refs=set(); report=None
    def gap(message,code='DISCLOSURE_DATA_REQUIRED'):
        result['data_gaps'].append({'id':result['id']+'-gap-'+str(len(result['data_gaps'])),'field':'disclosure_mapping',
            'reason':message,'impact':'Draft disclosure is incomplete or unverified; no conformity, obligation or public claim follows.',
            'remedy':'Inspect scoped source/version and obtain qualified reporting, rights and accountable-owner review.'})
        result['diagnostics'].append({'code':code,'message':message})
    try:
        if 'fixture_mode' in parameters and type(parameters['fixture_mode']) is not bool:
            raise ValueError('Explicit boolean fixture mode required.')
        review=parameters['mapping_review']
        _fields(review, {'boundary_id','period','as_of_date','scope','evidence_ids','evidence_fit','rationale','reviewer_role'}, ('scope','rationale','reviewer_role'))
        _sources(state,review['evidence_ids'],refs)
        if review['boundary_id']!=state['organizational_boundary']['id'] or review['period']!=state['reporting_period']:
            raise ValueError('Matched reporting period and organization boundary required.')
        as_of=_date(review['as_of_date'])
        if as_of<_date(state['reporting_period']['start']) or review['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:
            raise ValueError('Current reporting review date and explicit source fitness required.')
        if not review['evidence_ids'] or review['evidence_fit']!='reviewed_supporting': gap('Reporting applicability/source fitness withheld; draft fields remain unverified.')
        if skill=='compare-framework-mappings':
            versions=[]
            for key in ['before','after']:
                pin=parameters[key]; _fields(pin, {'adapter_id','catalog_sha256'}, ('adapter_id','catalog_sha256'))
                versions.append(catalog(pin['adapter_id'],pin['catalog_sha256'],parameters.get('fixture_mode',False)))
            a,b=versions
            if any(v.get('synthetic') for v in versions):
                gap('Fictional worksheet version comparison only; not an external standard change.','FICTIONAL_FRAMEWORK_ONLY')
                result['assumptions'].append('Original fictional review exercise; not an externally issued framework.')
            if any(_date(v['retrieved'])>as_of for v in versions):
                raise ValueError('Version-diff review cannot predate either source retrieval.')
            if a['framework']!=b['framework'] or a['id']==b['id']: raise ValueError('Distinct versions of the same framework required for mapping diff.')
            before={r['id']:r for r in a['requirements']}; after={r['id']:r for r in b['requirements']}
            report={'before':a,'after':b,'added_ids':sorted(after.keys()-before.keys()),'removed_ids':sorted(before.keys()-after.keys()),
                'changed_ids':sorted(i for i in before.keys()&after.keys() if before[i]!=after[i]),
                'metadata_changes':{k:{'before':a.get(k),'after':b.get(k)} for k in set(a)|set(b) if k!='requirements' and a.get(k)!=b.get(k)},
                'migration_applied':False,'prior_mappings_preserved':True,'conformity_verified':False}
        else:
            if not isinstance(parameters['fixture_mode'],bool): raise ValueError('Explicit boolean fixture mode required.')
            owner,selection,sources=_inventory(state,parameters['inventory_result_id'],refs,parameters['fixture_mode'])
            if parameters['fixture_mode']:
                result['assumptions']=list(dict.fromkeys(result['assumptions']+['Synthetic disclosure fixture only; not an actual organization report.']))
            if owner['status']=='partial': gap('Selected inventory is partial; unknown scopes/coverage cannot become complete gross organization emissions.')
            adapters=parameters['adapters']; notes=parameters['notes']
            if not isinstance(adapters,list) or not adapters or not isinstance(notes,list): raise ValueError('Nonempty explicit adapter selections and note list required.')
            mapped=[]; ids=set(); note_keys=set(); used=set()
            for note in notes:
                _fields(note, {'adapter_id','requirement_id','text','evidence_ids','evidence_fit','observed_date','limitations'}, ('adapter_id','requirement_id','text','limitations'))
                key=note['adapter_id'],note['requirement_id']
                if key in note_keys: raise ValueError('Distinct source note per adapter/requirement required.')
                note_keys.add(key)
                _sources(state,note['evidence_ids'],refs)
                if note['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}: raise ValueError('Explicit note source fitness required.')
                if note['observed_date'] is not None and _date(note['observed_date'])>as_of: raise ValueError('Note observation cannot postdate review.')
            for requested in adapters:
                _fields(requested, {'adapter_id','catalog_sha256','version_rationale','evidence_ids','evidence_fit','requested_requirement_ids'}, ('adapter_id','catalog_sha256','version_rationale'))
                if requested['adapter_id'] in ids: raise ValueError('Distinct selected adapter versions required.')
                ids.add(requested['adapter_id']); definition=catalog(requested['adapter_id'],requested['catalog_sha256'],parameters['fixture_mode'])
                if definition.get('synthetic'):
                    result['assumptions']=list(dict.fromkeys(result['assumptions']+['Original fictional review exercise; not an externally issued framework.']))
                    gap('Fictional worksheet mapping only; external-framework conformity cannot be inferred.','FICTIONAL_FRAMEWORK_ONLY')
                if _date(definition['retrieved'])>as_of: raise ValueError('Mapping cannot predate pinned source retrieval.')
                _sources(state,requested['evidence_ids'],refs)
                if requested['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}: raise ValueError('Explicit edition applicability fitness required.')
                fit=bool(requested['evidence_ids']) and requested['evidence_fit']==review['evidence_fit']=='reviewed_supporting' and bool(review['evidence_ids'])
                if not fit: gap(definition['id']+': edition/organization applicability unverified; no active authoritative mapping.')
                gap(definition['id']+': selected historical edition, later guidance, applicability, rights and complete framework coverage require review.')
                wanted=requested['requested_requirement_ids']; known={r['id'] for r in definition['requirements']}
                if not isinstance(wanted,list) or any(not _text(x) for x in wanted) or len(set(wanted))!=len(wanted): raise ValueError('Distinct explicitly requested requirement IDs required.')
                unsupported=sorted(set(wanted)-known)
                for i in unsupported: gap(definition['id']+' / '+i+': unsupported requirement; not satisfied or omitted silently.')
                rows=[]
                for requirement in definition['requirements']:
                    values={}; linked=set(); evidence=set(); missing=[]
                    for field in requirement['required_core_fields']:
                        if field=='organizational_boundary': values[field]=copy.deepcopy(state['organizational_boundary'])
                        elif field=='reporting_period': values[field]=copy.deepcopy(state['reporting_period'])
                        elif field=='scope_selection': values[field]=copy.deepcopy(selection)
                        elif field=='inventory_reference':
                            values[field]={'result_id':owner['id'],'metrics':copy.deepcopy(owner['metrics']),'status':owner['status']}; linked.add(owner['id']); evidence.update(owner['evidence_ids'])
                        elif field in {'scope_1','scope_2'}:
                            selected=[s for s in sources if any(x['result_id']==s['id'] and x['scope']==field for x in selection['included'])]
                            if not selected: missing.append(field); continue
                            values[field]=[]
                            for s in selected:
                                linked.add(s['id']); evidence.update(s['evidence_ids'])
                                values[field].append({'result_id':s['id'],'original_metrics':copy.deepcopy(s['metrics']),
                                    'display_t_CO2e':serialize(convert(s['metrics'][0]['value'],s['metrics'][0]['unit'],'t CO2e')['value']),
                                    'source_status':s['status'],'qualification':'Selected source amount only; not verified complete gross organization coverage.'})
                        elif field=='method': values[field]=[{'result_id':s['id'],'metrics':copy.deepcopy(s['metrics'])} for s in sources]; linked.update(s['id'] for s in sources)
                        else: missing.append(field)
                    note=next((n for n in notes if (n['adapter_id'],n['requirement_id'])==(definition['id'],requirement['id'])),None)
                    if note:
                        used.add((note['adapter_id'],note['requirement_id']))
                        evidence.update(note['evidence_ids'])
                        gap(definition['id']+' / '+requirement['id']+': narrative note is a source proposal, not verified disclosure fulfillment.')
                    if values and not evidence: evidence.update(owner['evidence_ids']); linked.add(owner['id'])
                    if missing: gap(definition['id']+' / '+requirement['id']+': missing '+', '.join(missing)+'; unknown is not zero or not applicable.')
                    if requirement['external_requirement_pending']: gap(definition['id']+' / '+requirement['id']+': external standard access/rights/requirements pending; inventory is context only.')
                    rows.append({'requirement':copy.deepcopy(requirement),'core_values':values,'missing_core_fields':missing,'mapped_result_ids':sorted(linked),
                        'evidence_ids':sorted(evidence),'note':copy.deepcopy(note),'source_fit':'source_mapping_candidate' if fit else 'unverified',
                        'status':'reference_only_external_requirements_pending' if requirement['external_requirement_pending'] else 'draft_incomplete' if missing else 'draft_source_candidate',
                        'fulfillment_verified':False,'qualified_review_required':True})
                mapped.append({'catalog':definition,'catalog_sha256':requested['catalog_sha256'],'selection_review':copy.deepcopy(requested),'rows':rows,
                    'unsupported_requirement_ids':unsupported,'active_authoritative_mapping':False,'conformity_verified':False})
            if note_keys-used: raise ValueError('Narrative notes must reference actual selected catalog requirements; no orphan claims.')
            report={'inventory_snapshot':copy.deepcopy(owner),'scope_source_snapshots':copy.deepcopy(sources),'inventory_selection':selection,
                'adapters':mapped,'calculation_lineage_result_ids':sorted({owner['id']}|{s['id'] for s in sources}),
                'mapping_review':copy.deepcopy(review),'conformity_verified':False,'legal_applicability_determined':False,
                'assurance_verified':False,'public_claim_authorized':False,'publication_authorized':False,'commercial_use_authorized':False}
        gap('Qualified framework, source, rights and accountable-owner review remains required; draft mapping is not conformity or assurance.')
        result['review_requirements'].append({'id':result['id']+'-framework-review','state':'PROFESSIONAL_REVIEW_REQUIRED','reason':'Review pinned edition, mapping, evidence, omissions, rights and applicability; no conformity, assurance or publication.',
            'scope':review['scope'],'reviewer_role':review['reviewer_role'],'status':'open','resolution':None})
        result['diagnostics'].append({'code':'FRAMEWORK_DISCLOSURE_MAP' if skill=='map-framework-disclosures' else 'FRAMEWORK_MAPPING_DIFF','message':json.dumps(report,sort_keys=True)})
    except (ValueError,TypeError,KeyError) as error:
        result['status']='blocked'; gap(str(error),'EMISSION_FACTOR_REQUIRED' if isinstance(error,FactorRequired) else 'SOURCE_PACK_REQUIRED' if isinstance(error,SourcePackRequired) else 'DISCLOSURE_DATA_REQUIRED')
    result['evidence_ids']=sorted(refs)
    result['diagnostics'].append({'code':'FRAMEWORK_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    result['review_states']=list(dict.fromkeys(result['review_states']+[r['state'] for r in result['review_requirements'] if r['status']=='open']+(['EVIDENCE_INCOMPLETE'] if result['data_gaps'] else [])))
    result['next_actions']=list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result':result,'proposal':propose(state,result,'Record versioned source-linked draft mappings without duplicating core calculations or authorizing disclosures')}
