"""Conditional Canada quantity/screen/task composition; no reporting or storage action."""
import copy
import hashlib
import json
from .climate_tools import _fields,_sources,_date,_text
from .contract_validation import validate_state
from .canada_quantity_bridge import run_canada_quantity_bridge
from .jurisdiction_tasks import prepare_jurisdiction_tasks,load_task_catalog,_diagnostic,_retention_date
from .manager_workflow import _empty
from .state_proposal import propose


CATALOGS={'canada/ghgrp/tasks-notice2023-1.json','canada/ghgrp/tasks-amended2025-1.json',
          'canada/ghgrp/tasks-notice2023-history-1.json','canada/ghgrp/tasks-amended2025-history-1.json'}


def run_canada_tasks(state,p):
    validate_state(state);_fields(p,{'quantity_parameters','task_parameters','storage_review','result_id'},('result_id',))
    qp=p['quantity_parameters'];tp=p['task_parameters'];storage=p['storage_review']
    if tp['task_catalog_pin']['path'] not in CATALOGS:raise ValueError('Explicit source-versioned Canada task catalog required.')
    catalog=load_task_catalog(tp['task_catalog_pin'],tp['fixture_mode'])
    if catalog['screen_pack_pin'] not in qp['screen_parameters']['pack_pins']:raise ValueError('Task and quantity screen must select the same exact notice edition.')
    if tp['screen_result_id']!=qp['screen_parameters']['result_id'] or tp['planning_review']['as_of_date']!=qp['quantity_review']['as_of_date']:raise ValueError('Fresh exact source screen and same assessment date required.')
    ids=[lp['result_id'] for lp in qp['ledger_parameters']]+[qp['screen_parameters']['result_id'],qp['result_id'],tp['result_id'],p['result_id']]
    if len(ids)!=len(set(ids)) or set(ids)&{r['id'] for r in state['results']}:raise ValueError('Fresh distinct workflow result IDs required.')
    _fields(storage,{'subject_id','boundary_id','period','as_of_date','choice','country','parent_address','evidence_ids','evidence_fit','rationale','reviewer_role'},('subject_id','choice','rationale','reviewer_role'))
    if storage['subject_id']!=qp['subject_id'] or storage['boundary_id']!=state['organizational_boundary']['id'] or storage['period']!=state['reporting_period'] or storage['as_of_date']!=tp['planning_review']['as_of_date'] or storage['choice'] not in {'at_facility','parent_in_canada','unassessed'} or storage['evidence_fit'] not in {'reviewed_supporting','unverified','irrelevant'}:raise ValueError('Matched selected subject/time/boundary and explicit storage choice/fitness required.')
    if storage['country'] is not None and not _text(storage['country']) or storage['parent_address'] is not None and not _text(storage['parent_address']):raise ValueError('Storage country/address must be substantive or null.')
    quantity=run_canada_quantity_bridge(state,copy.deepcopy(qp));working=quantity['proposal']['state']
    tasks=prepare_jurisdiction_tasks(working,copy.deepcopy(tp));working=tasks['proposal']['state'];result=_empty(working,'prepare-jurisdiction-task-register',p['result_id']);result['status']='partial'
    refs=set();ev=_sources(working,storage['evidence_ids'],refs);when=_date(storage['as_of_date'])
    storage_fit=(storage['evidence_fit']=='reviewed_supporting' and bool(ev) and all(e['boundary_id']==storage['boundary_id'] and e['source']['version'] is not None and _date(e['source']['accessed'])<=when for e in ev))
    contexts={'historical_retention_candidates':[],'storage_location_candidate':None,'parent_address_notification_candidate':None}
    task_report=None
    if tasks['result']['status']!='blocked':
        task_report=_diagnostic(tasks['result'],'JURISDICTION_TASK_REGISTER')
        report_task=next(t for t in catalog['tasks'] if t['kind']=='report');retain=next(t for t in catalog['tasks'] if t['kind']=='retain')
        retain_rows=[r for r in task_report['rows'] if r['subject_id']==qp['subject_id'] and r['task']['kind']=='retain']
        retention_source_fit=bool(retain_rows) and all(r['source_fit'] for r in retain_rows)
        for history in task_report['history']:
            h=history['record']
            if h['subject_id']!=qp['subject_id'] or h['reporting_year']>=int(state['reporting_period']['start'][:4]):continue
            due=report_task['deadlines'].get(str(h['reporting_year']));supported=(retention_source_fit and history['supported'] and h['submitted'] is True and due is not None)
            contexts['historical_retention_candidates'].append({'history':copy.deepcopy(history),'reporting_year':h['reporting_year'],
                'candidate_status':'potential_task' if supported else 'undetermined','required_submission_anchor':due if supported else None,
                'candidate_until':_retention_date(due,retain['retention_years']) if supported else None,
                'actual_submission_date_separate':h['submitted_date'],'source':copy.deepcopy(retain['source']),
                'legal_obligation_determined':False,'retention_completed_or_storage_verified':False})
        retain_rows=[r for r in task_report['rows'] if r['subject_id']==qp['subject_id'] and r['task']['kind']=='retain']
        required=any(r['candidate_status']=='potential_task' for r in retain_rows) or any(r['candidate_status']=='potential_task' for r in contexts['historical_retention_candidates'])
        if required:
            supported=storage_fit and storage['choice']!='unassessed' and (storage['choice']=='at_facility' or storage['country']=='CA' and _text(storage['parent_address']))
            contexts['storage_location_candidate']={'choice':storage['choice'],'declared_country':storage['country'],'candidate_status':'potential_task' if supported else 'undetermined',
                'source_locator':'https://gazette.gc.ca/rp-pr/p1/2023/2023-12-09/html/sup1-eng.html','source_clause':'Opening retention/storage paragraphs',
                'evidence_ids':list(storage['evidence_ids']),'actual_storage_verified':False,'location_approved':False}
            if storage['choice']=='parent_in_canada':
                contexts['parent_address_notification_candidate']={'candidate_status':'potential_task' if supported else 'undetermined',
                    'declared_parent_address':storage['parent_address'],'evidence_ids':list(storage['evidence_ids']),
                    'source_locator':'https://gazette.gc.ca/rp-pr/p1/2023/2023-12-09/html/sup1-eng.html','source_clause':'Opening parent-company civic-address paragraph',
                    'notification_sent_or_authorized':False,'legal_obligation_determined':False}
    else:result['status']='blocked'
    result['evidence_ids']=sorted(refs|set(tasks['result']['evidence_ids'])|set(quantity['result']['evidence_ids']))
    result['review_states']=list(dict.fromkeys(result['review_states']+['LEGAL_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['review_requirements'].append({'id':result['id']+'-legal-storage-review','state':'LEGAL_REVIEW_REQUIRED','reason':'Assess source edition, all reporting/history/operator conditions, certification authority, retention anchors, storage and parent address; no legal action is adopted.',
        'scope':tp['planning_review']['scope'],'reviewer_role':storage['reviewer_role'],'status':'open','resolution':None})
    if not storage_fit or storage['choice']=='unassessed' or storage['choice']=='parent_in_canada' and (storage['country']!='CA' or not _text(storage['parent_address'])):result['data_gaps'].append({'id':result['id']+'-storage-gap','field':'storage_context','reason':'Actual storage/address evidence or selection remains unassessed.',
        'impact':'No storage choice, address notification or retention compliance is verified.','remedy':'Obtain source/legal/owner review of actual records, storage and address context.'})
    for source in (quantity['result'],tasks['result']):result['diagnostics'].extend(copy.deepcopy(d) for d in source['diagnostics'] if d['code'] in {'EMISSION_FACTOR_REQUIRED','GWP_REQUIRED'})
    views=[{'result_id':r['id'],'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()} for r in (quantity['result'],tasks['result'])]
    report={'execution_contract':'canada-task-workflow-0.1.0','source_result_views':views,'storage_review':copy.deepcopy(storage),**contexts,
        'report_filed':False,'notification_sent':False,'certification_performed':False,'authorized_signatory_verified':False,'storage_verified':False,
        'legal_obligation_determined':False,'regulatory_quantity_verified':False,'pack_activated_or_approved':False,'commercial_use_authorized':False,'external_action_authorized':False}
    result['diagnostics'].extend([{'code':'CANADA_TASK_WORKFLOW','message':json.dumps(report,sort_keys=True)},{'code':'CANADA_TASK_WORKFLOW_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Review all conditional source/history/operator/report/certification/retention/storage candidates with qualified legal and accountable owner reviewers before any action.']
    final=propose(working,result,'Compose separate conditional Canadian tasks and retention/storage context without external action')['state'];final['revision']=state['revision']+1;validate_state(final)
    return {'result':result,'proposal':{'base_revision':state['revision'],'reason':'Atomic conditional Canada task candidate; no filing, notification, certification or storage action','state':final}}
