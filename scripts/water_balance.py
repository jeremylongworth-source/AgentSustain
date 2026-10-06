"""Declared facility water-volume reconciliation; no consumption/leakage inference."""
import copy
from decimal import Decimal,localcontext
import hashlib
import json
from .climate_tools import _date,_fields,_sources
from .contract_validation import validate_state
from .data_tools import convert,number,serialize
from .manager_workflow import _empty
from .state_proposal import propose

CONTRACT='water-balance-0.1.0'
SOURCE='https://pubs.usgs.gov/publication/cir1308'
KINDS={'inflow','outflow','storage_opening','storage_closing','internal_reuse'}


def reconcile_water_balance(state,p):
    validate_state(state);_fields(p,{'quantities','balance_review','fixture_mode','result_id'},('result_id',))
    if type(p['fixture_mode']) is not bool or any(r['id']==p['result_id'] for r in state['results']):raise ValueError('Explicit fixture mode and fresh balance identity required.')
    result=_empty(state,'build-water-baseline',p['result_id']);result['status']='partial';refs=set()
    report={'execution_contract':CONTRACT,'review':copy.deepcopy(p['balance_review']),'quantities':[],
        'selected_inflow_m3':None,'selected_outflow_m3':None,'internal_reuse_m3_separate':None,'storage_change_m3':None,
        'unresolved_residual_m3':None,'residual_supplied_bounds_m3':None,'zero_within_supplied_bounds':None,
        'declared_roster_support_complete':False,'actual_source_coverage_verified':False,'source_authenticated':False,
        'consumption_or_leakage_determined':False,'measurement_closure_verified':False,'engineering_approved':False,'external_action_authorized':False}
    def gap(code,message):
        result['diagnostics'].append({'code':code,'message':message})
        result['data_gaps'].append({'id':p['result_id']+'-gap-'+str(len(result['data_gaps'])),'field':'water_balance','reason':message,
            'impact':'Selected water balance/uncertainty remains conditional or unavailable.','remedy':'Reconcile source meters, stock snapshots, shared coverage and qualified facility/period/uncertainty review.'})
    def emit(suffix,name,value,inputs,formula):
        result['metrics'].append({'id':p['result_id']+'-'+suffix,'name':name,'value':serialize(value),'unit':'m3',
            'period':copy.deepcopy(state['reporting_period']),'boundary_id':state['organizational_boundary']['id'],'evidence_ids':sorted(refs),
            'method':{'name':'Explicit selected inflow/outflow/storage volume reconciliation','version':CONTRACT,'source':SOURCE},
            'assumption':None,'uncertainty':{'kind':'unquantified','description':'Input snapshots and supplied bounds retained; no statistical covariance/confidence or actual closure inferred.','value':None,'unit':None},
            'calculation':{'formula':formula,'inputs':inputs,'conversions':['Supported L/m3 volume conversions only; no density, consumption, loss or stock-zero inference.'],
                'rounding':'34-digit Decimal arithmetic; finite JSON number representation'}})
    try:
        review=p['balance_review'];_fields(review,{'boundary_id','facility_id','period','as_of_date','measurement_boundary','coverage_complete','nonoverlap_assessment',
            'evidence_ids','evidence_fit','rationale','reviewer_role'},('facility_id','measurement_boundary','nonoverlap_assessment','rationale','reviewer_role'))
        if (review['boundary_id']!=state['organizational_boundary']['id'] or review['facility_id'] not in state['organizational_boundary']['facility_ids']
            or review['period']!=state['reporting_period'] or type(review['coverage_complete']) is not bool or review['evidence_fit']!='reviewed_supporting'):
            raise ValueError('Matched explicit facility/boundary/period and qualified balance review required.')
        when=_date(review['as_of_date']);period=state['reporting_period']
        if when<_date(period['end']):raise ValueError('Complete observed-period balance required; no future flows inferred.')
        def source_fit(evidence,target):
            return bool(evidence) and all(e['source']['version'] is not None and _date(e['source']['accessed'])<=when
                and e['period']['start']<=target['start'] and e['period']['end']>=target['end'] for e in evidence)
        reviewed=_sources(state,review['evidence_ids'],refs)
        if not source_fit(reviewed,period):raise ValueError('Versioned nonfuture full-period source/coverage review required.')
        if not isinstance(p['quantities'],list) or not p['quantities']:raise ValueError('Explicit nonempty water-role register required.')
        metrics={m['id']:(r,m) for r in state['results'] for m in r['metrics']};ids=set();fragments=set();groups={k:[] for k in KINDS}
        for q in p['quantities']:
            _fields(q,{'metric_id','kind','facility_id','source_fragment','evidence_ids','evidence_fit','rationale','bounds'},
                    ('metric_id','kind','facility_id','source_fragment','rationale'))
            if q['kind'] not in KINDS or q['facility_id']!=review['facility_id'] or q['metric_id'] in ids:
                raise ValueError('Distinct explicit stream/stock roles for the same selected facility required.')
            ids.add(q['metric_id']);context=_sources(state,q['evidence_ids'],refs);pair=metrics.get(q['metric_id'])
            if pair is None:raise ValueError('Selected current water metric must resolve.')
            owner,m=pair;source=_sources(state,m['evidence_ids'],refs)
            for evidence_id in m['evidence_ids']:
                key=(evidence_id,q['source_fragment'])
                if key in fragments:raise ValueError('Repeated source/fragment coverage cannot supply different balance terms.')
                fragments.add(key)
            target=period
            if q['kind'].startswith('storage_'):
                endpoint=period['start'] if q['kind']=='storage_opening' else period['end'];target={'start':endpoint,'end':endpoint}
            supported=(owner['status'] in {'completed','partial'} and m['period']==target and m['boundary_id']==review['boundary_id']
                and m['value'] is not None and m['assumption'] is None and q['evidence_fit']=='reviewed_supporting'
                and source_fit(source,target) and source_fit(context,target) and all(e['unit']==m['unit'] and e['source']['tier']!=5 and e['assumption'] is None for e in source)
                and set(m['calculation']['inputs'])<=set(m['evidence_ids']))
            if not p['fixture_mode'] and any(e['source']['locator'].startswith('fixture:') for e in source+context+reviewed):supported=False
            for d in owner['diagnostics']:
                if d['code']=='BUSINESS_INGESTION_INPUTS':
                    ancestry=json.loads(d['message'])
                    if not p['fixture_mode'] and (ancestry['fixture_mode'] or ancestry['file_pin']['synthetic']):supported=False
            value=None
            if supported:
                try:
                    if number(m['value'])<0:raise ValueError('Nonnegative raw volume required.')
                    value=convert(m['value'],m['unit'],'m3')['value']
                except (ValueError,TypeError):supported=False
            bounds=None
            if q['bounds'] is not None:
                b=q['bounds'];_fields(b,{'low','high','unit','basis','evidence_ids','evidence_fit'},('unit','basis'))
                bound_sources=_sources(state,b['evidence_ids'],refs)
                try:
                    low=convert(b['low'],b['unit'],'m3')['value'];high=convert(b['high'],b['unit'],'m3')['value']
                    if supported and 0<=low<=value<=high and b['evidence_fit']=='reviewed_supporting' and source_fit(bound_sources,target):bounds=(low,high)
                except (ValueError,TypeError):pass
                if bounds is None:gap('WATER_BOUND_REQUIRED',q['metric_id']+': supplied bound is unsupported or does not enclose the source quantity.')
            item={'binding':copy.deepcopy(q),'metric':copy.deepcopy(m),'source_result_id':owner['id'],
                'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(owner,sort_keys=True).encode()).hexdigest(),
                'sources':source,'context_sources':context,'supported':supported,'value_m3':serialize(value) if supported else None,
                'supplied_bounds_m3':[serialize(x) for x in bounds] if bounds else None,'stock_snapshot_period':target if q['kind'].startswith('storage_') else None}
            report['quantities'].append(item);groups[q['kind']].append((q,m,value if supported else None,bounds))
            if not supported:gap('WATER_BALANCE_SOURCE_REQUIRED',q['metric_id']+': unknown/unfit period/source/unit/measurement context is retained, never assigned zero.')
        def summed(kind):
            entries=groups[kind];values=[v for _,_,v,_ in entries if v is not None]
            return sum(values,Decimal(0)) if values else None
        with localcontext() as ctx:
            ctx.prec=34
            for kind,key in (('inflow','selected_inflow_m3'),('outflow','selected_outflow_m3'),('internal_reuse','internal_reuse_m3_separate')):
                total=summed(kind)
                if total is not None:
                    report[key]=serialize(total);emit(kind,'Supported selected '+kind.replace('_',' ')+' volume',total,[m['id'] for _,m,v,_ in groups[kind] if v is not None],'Sum of supported selected same-role volumes; internal reuse kept separate')
            stocks=groups['storage_opening']+groups['storage_closing'];delta=None
            if len(groups['storage_opening'])==1 and len(groups['storage_closing'])==1 and all(x[2] is not None for x in stocks):
                delta=groups['storage_closing'][0][2]-groups['storage_opening'][0][2]
                report['storage_change_m3']=serialize(delta);emit('storage-change','Selected closing minus opening water stock',delta,[m['id'] for _,m,_,_ in stocks],'Closing stock - opening stock at explicit reporting-period endpoints')
            else:gap('WATER_STORAGE_REQUIRED','One supported opening and closing stock snapshot required; no missing or repeated stock substituted.')
            required=groups['inflow']+groups['outflow']+stocks
            complete=bool(groups['inflow'] and groups['outflow']) and delta is not None and all(e[2] is not None for e in required) and review['coverage_complete']
            report['declared_roster_support_complete']=complete
            if complete:
                residual=summed('inflow')-summed('outflow')-delta;report['unresolved_residual_m3']=serialize(residual)
                emit('residual','Unresolved selected water-balance residual',residual,[m['id'] for _,m,_,_ in required],'Selected inflow - selected outflow - (closing stock - opening stock); excludes internal reuse')
                if all(e[3] is not None for e in required):
                    positive=groups['inflow']+groups['storage_opening'];negative=groups['outflow']+groups['storage_closing']
                    low=sum((e[3][0] for e in positive),Decimal(0))-sum((e[3][1] for e in negative),Decimal(0))
                    high=sum((e[3][1] for e in positive),Decimal(0))-sum((e[3][0] for e in negative),Decimal(0))
                    report['residual_supplied_bounds_m3']=[serialize(low),serialize(high)];report['zero_within_supplied_bounds']=low<=0<=high
                else:gap('WATER_BOUND_REQUIRED','Complete supported input bounds required for residual-bound comparison; no zero tolerance or confidence interval inferred.')
                gap('WATER_RESIDUAL_REVIEW_REQUIRED','Residual and any supplied bounds require source/engineering interpretation; no leakage, consumption or actual closure inferred.')
            else:gap('WATER_BALANCE_COVERAGE_REQUIRED','Incomplete declared inflow/outflow/stock support withholds the residual; supported selected subtotals remain qualified.')
    except (ValueError,TypeError,KeyError) as error:
        result['status']='blocked';result['metrics']=[];gap('WATER_BALANCE_DATA_REQUIRED',str(error))
    result['evidence_ids']=sorted(refs)
    result['review_requirements'].append({'id':p['result_id']+'-engineering-review','state':'ENGINEERING_REVIEW_REQUIRED',
        'reason':'Review selected facility/flow/stock coverage, meter timing, reuse/overlap and uncertainty before water-consumption, leakage, closure or engineering claims.',
        'scope':'Conditional selected water balance only','reviewer_role':'Qualified water/engineering professionals and accountable owner','status':'open','resolution':None})
    result['review_states']=list(dict.fromkeys(result['review_states']+['ENGINEERING_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['diagnostics'].extend([{'code':'WATER_BALANCE','message':json.dumps(report,sort_keys=True)},{'code':'WATER_BALANCE_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Reconcile outstanding source/coverage/residual/uncertainty review; do not relabel residual as consumption or leakage.']
    proposal=propose(state,result,'Reconcile declared water roles and stock snapshots without loss/consumption/closure claims')
    if result['metrics']:proposal['state']['water'].append(result['id']);validate_state(proposal['state'])
    return {'result':result,'proposal':proposal}
