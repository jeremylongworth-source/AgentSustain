"""Pinned seven-specialist development routing with caller-supplied recipes."""
import ast
import copy
import hashlib
import importlib
import json
import re
import subprocess
from jsonschema.exceptions import ValidationError
from .climate_tools import _fields
from .contract_validation import ROOT, validate_state
from .manager_workflow import _empty
from .state_proposal import propose

REVISION='7bad9dd3a07069b7a99979f80fd509ad0eb40486'
CATALOG_PATH='router/specialists-0.1.json'
ENDPOINTS={
    'sustainable-operations':('operations_tools','run_operations'),
    'carbon-accounting':('carbon_workflow','run_carbon_workflow'),
    'sustainability-manager':('manager_workflow','run_manager'),
    'sustainable-procurement':('procurement_workflow','run_procurement'),
    'climate-risk':('climate_workflow','run_climate_workflow'),
    'sustainability-business-case':('investment_workflow','run_investment_workflow'),
    'sustainability-reporting':('reporting_workflow','run_reporting_workflow')}
PATTERNS={
    'sustainable-operations':r'\b(sustainable[- ]operations|operational efficiency|factory operations|energy efficiency|water efficiency|waste reduction)\b',
    'carbon-accounting':r'\b(carbon[- ]accounting|ghg inventory|carbon inventory|scope [123]|emissions inventory|carbon footprint)\b',
    'sustainability-manager':r'\b(sustainability[- ]manager|organization sustainability|organisation sustainability|coordinate sustainability|sustainability roadmap)\b',
    'sustainable-procurement':r'\b(sustainable[- ]procurement|supplier sustainability|compare suppliers|supplier risk|procurement)\b',
    'climate-risk':r'\b(climate[- ]risk|physical climate|transition risk|climate resilience|adaptation plan)\b',
    'sustainability-business-case':r'\b(sustainability[- ]business[- ]case|investment business case|investment ranking|compare investments|npv|payback)\b',
    'sustainability-reporting':r'\b(sustainability[- ]reporting|sustainability disclosure|disclosure mapping|framework mapping|sustainability report)\b'}
NEGATED=r"\b(?:don't|do not|never|avoid|skip)\s+(?:\w+\s+){0,3}(?:calculat\w*|build\w*|prepar\w*|analy[sz]\w*|assess\w*|rout\w*|execut\w*|run\w*|compar\w*|manag\w*|coordinat\w*|improv\w*|prioritiz\w*)"


def _approved_files():
    proc=subprocess.run(['git','ls-tree','-r','--name-only',REVISION,'--','scripts','schemas','skills','skillsets','requirements-dev.txt'],cwd=ROOT,capture_output=True,check=True)
    paths=proc.stdout.decode().splitlines()
    request=''.join(REVISION+':'+p+'\n' for p in paths).encode()
    result=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=request,capture_output=True,check=True)
    data=result.stdout;offset=0;files={}
    for path in paths:
        end=data.index(b'\n',offset);header=data[offset:end].split()
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('Complete actual approved Git blobs required.')
        size=int(header[2]);start=end+1;files[path]=data[start:start+size]
        if len(files[path])!=size or data[start+size:start+size+1]!=b'\n':raise ValueError('Complete Git blob bytes required.')
        offset=start+size+1
    return files


def _assets(role, files):
    module,_=ENDPOINTS[role];pending=['scripts/'+module+'.py'];seen=set()
    while pending:
        path=pending.pop()
        if path in seen:continue
        if path not in files:raise ValueError('Every local runtime import must exist in approved Git content.')
        seen.add(path);tree=ast.parse(files[path].decode('utf-8'))
        for node in ast.walk(tree):
            modules=[]
            if isinstance(node,ast.ImportFrom):
                if node.level==1:modules=[node.module] if node.module else [a.name for a in node.names]
                elif node.level>1:raise ValueError('Unsupported local runtime package escape.')
                elif node.module and node.module.startswith('scripts.'):modules=[node.module[8:]]
            elif isinstance(node,ast.Import):modules=[a.name[8:] for a in node.names if a.name.startswith('scripts.')]
            for name in modules:pending.append('scripts/'+name.replace('.','/')+'.py')
    seen.update(p for p in files if p.startswith('schemas/') and p.endswith('.json'))
    seen.update(p for p in ('scripts/__init__.py','requirements-dev.txt') if p in files)
    pending=['skillsets/'+role+'/SKILL.md','skillsets/'+role+'/manifest.json']
    while pending:
        path=pending.pop()
        if path in seen:continue
        if path not in files:raise ValueError('Complete approved manifest/skill dependency required.')
        seen.add(path)
        if path.endswith('.json'):
            def walk(value):
                if isinstance(value,dict):
                    ref=value.get('path')
                    if isinstance(ref,str) and ref.startswith(('skills/','skillsets/')):
                        if '..' in ref.split('/') or '\\' in ref:raise ValueError('Bounded skill dependency path required.')
                        pending.append(ref)
                        if ref.startswith('skillsets/') and ref.endswith('/SKILL.md'):pending.append(ref[:-8]+'manifest.json')
                    for child in value.values():walk(child)
                elif isinstance(value,list):
                    for child in value:walk(child)
            walk(json.loads(files[path]))
    for path in ('skillsets/'+role+'/SKILL.md','skillsets/'+role+'/manifest.json'):
        if path.endswith('SKILL.md'):
            match=re.search(r'^name: (.+)$',files[path].decode().replace('\r\n','\n'),re.M)
            if not match or match[1]!=role:raise ValueError('Exact approved specialist name required.')
        elif json.loads(files[path])['name']!=role:raise ValueError('Exact approved specialist manifest identity required.')
    return {p:hashlib.sha256(files[p].replace(b'\r\n',b'\n')).hexdigest() for p in sorted(seen)}


def approved_catalog():
    files=_approved_files()
    return {'id':'development-specialists','version':'0.1.0','execution_contract':'specialist-router-0.1.0',
        'reviewed_capability_revision':REVISION,'approval_scope':'development_only','router_scoped_owner_approved':False,
        'roles':{r:{'operation':r,'module':ENDPOINTS[r][0],'function':ENDPOINTS[r][1],'sha256_utf8_lf':_assets(r,files)} for r in ENDPOINTS}}


def load_specialist_catalog(pin):
    _fields(pin,{'path','sha256'},('path','sha256'))
    if pin['path']!=CATALOG_PATH:raise ValueError('Explicit bounded specialist catalog required.')
    raw=(ROOT/CATALOG_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Exact catalog byte pin required.')
    catalog=json.loads(raw)
    if catalog!=approved_catalog():raise ValueError('Catalog must match complete actual approved role/runtime/manifest/schema Git content.')
    available={r:all((ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h
                     for p,h in entry['sha256_utf8_lf'].items()) for r,entry in catalog['roles'].items()}
    return catalog,available


def run_specialist_route(state,p):
    validate_state(state);_fields(p,{'request','role','catalog_pin','recipe','result_id'},('request','role','result_id'))
    if len(p['request'])>10000 or p['role'] not in {'auto',*ENDPOINTS} or p['recipe'] is not None and not isinstance(p['recipe'],dict):
        raise ValueError('Bounded original request, supported role and explicit recipe object or null required.')
    if any(r['id']==p['result_id'] for r in state['results']):raise ValueError('Fresh router identity required.')
    result=_empty(state,'route-sustainability-request',p['result_id']);result['status']='partial';working=state;refs=set()
    report={'execution_contract':'specialist-router-0.1.0','original_request':p['request'],'classification_source':'original-request-only bounded cues',
        'boundary_id':state['organizational_boundary']['id'],'period':copy.deepcopy(state['reporting_period']),
        'candidates':[],'selected_role':None,'catalog_pin':copy.deepcopy(p['catalog_pin']),'capability_snapshot':None,
        'reviewed_runtime_available':False,'recipe_inferred':False,'helper_invoked':False,'source_result_view':None,
        'source_result_status':None,'factor_requirement_sources':[],'input_fitness_verified':False,'workflow_or_organization_acceptance_verified':False,
        'router_scoped_owner_approved':False,'external_action_authorized':False,'publication_authorized':False}
    def gap(code,message):
        result['data_gaps'].append({'id':p['result_id']+'-gap-'+str(len(result['data_gaps'])),'field':'specialist_route',
            'reason':message,'impact':'Selected routing/analysis remains unresolved or conditional.','remedy':'Clarify original intent and supply the selected approved helper recipe and qualified source review.'})
        result['diagnostics'].append({'code':code,'message':message})
    try:
        catalog,available=load_specialist_catalog(p['catalog_pin'])
        candidates=[role for role,pattern in PATTERNS.items() if re.search(pattern,p['request'],re.I)]
        report['candidates']=candidates
        selected=candidates[0] if p['role']=='auto' and len(candidates)==1 else p['role'] if p['role']!='auto' and (not candidates or p['role'] in candidates) else None
        if re.search(NEGATED,p['request'],re.I):selected=None
        if selected is None:gap('ROUTE_CLARIFICATION_REQUIRED','Mixed, negated, unsupported or contradictory original intent requires clarification; no helper invoked.')
        else:
            report['selected_role']=selected;report['capability_snapshot']=copy.deepcopy(catalog['roles'][selected]);report['reviewed_runtime_available']=available[selected]
            if p['role']!='auto':report['classification_source']='caller-selected role; attribution retained, semantic fitness unverified'
            if not available[selected]:
                result['status']='blocked';gap('ROUTE_CAPABILITY_UNAVAILABLE','Selected reviewed entrypoint, manifest, schema or local runtime content has drifted; no replacement or downgrade inferred.')
            elif p['recipe'] is None:gap('ROUTE_RECIPE_REQUIRED','Route selected; explicit capability-specific recipe is required before analytical invocation.')
            else:
                if p['recipe'].get('result_id')==p['result_id']:raise ValueError('Router and selected helper identities must be distinct.')
                module,function=ENDPOINTS[selected]
                report['helper_invoked']=True
                out=getattr(importlib.import_module('scripts.'+module),function)(copy.deepcopy(state),copy.deepcopy(p['recipe']))
                validate_state(out['proposal']['state'])
                immutable=('contract_version','organization','facilities','jurisdictions','reporting_period','organizational_boundary','evidence','emission_factors')
                if any(out['proposal']['state'][key]!=state[key] for key in immutable) or any(r not in out['proposal']['state']['review_requirements'] for r in state['review_requirements']):
                    raise ValueError('Selected specialist must preserve original sources, factors, boundary, period and review decisions.')
                if out['result']['skill']!=selected or out['result']!=out['proposal']['state']['results'][-1] or out['proposal']['state']['results'][:len(state['results'])]!=state['results']:
                    raise ValueError('Exact selected capability output and original result history required.')
                _,post=load_specialist_catalog(p['catalog_pin'])
                if not post[selected]:raise ValueError('Selected runtime changed during invocation; candidate withheld.')
                if any(r['id']==p['result_id'] for r in out['proposal']['state']['results']):raise ValueError('Nested helper identity collides with router aggregate.')
                working=out['proposal']['state'];source=out['result'];result=_empty(working,'route-sustainability-request',p['result_id'])
                result['status']='blocked' if source['status'] in {'blocked','invalid_input'} else 'partial';refs.update(source['evidence_ids'])
                report['source_result_status']=source['status'];report['source_result_view']={'result_id':source['id'],
                    'sha256_result_utf8_json_sorted_keys':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()}
                for produced in working['results'][len(state['results']):]:
                    required=[d for d in produced['diagnostics'] if d['code'] in {'EMISSION_FACTOR_REQUIRED','GWP_REQUIRED'}]
                    if required:report['factor_requirement_sources'].append(produced['id'])
                    for diagnostic in required:
                        if diagnostic not in result['diagnostics']:result['diagnostics'].append(copy.deepcopy(diagnostic))
                if len(candidates)>1:gap('ROUTE_UNHANDLED_INTENT','Other original intent candidates remain unhandled by the caller-selected single role.')
    except (ValueError,TypeError,KeyError,OSError,subprocess.SubprocessError,ValidationError) as error:
        working=state;result=_empty(state,'route-sustainability-request',p['result_id']);result['status']='blocked'
        report['source_result_view']=None;report['source_result_status']=None
        gap('ROUTE_CATALOG_OR_RECIPE_REQUIRED',str(error))
    result['evidence_ids']=sorted(refs)
    result['review_requirements'].append({'id':p['result_id']+'-route-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
        'reason':'Review original role selection, actual recipe/source fitness and all selected capability obligations before relying on analytical output.',
        'scope':'Conditional specialist route only','reviewer_role':'Qualified sustainability professional and accountable owner','status':'open','resolution':None})
    result['review_states']=list(dict.fromkeys(result['review_states']+['PROFESSIONAL_REVIEW_REQUIRED','EVIDENCE_INCOMPLETE']))
    result['diagnostics'].extend([{'code':'SPECIALIST_ROUTE','message':json.dumps(report,sort_keys=True)},
                                 {'code':'SPECIALIST_ROUTE_INPUTS','message':json.dumps(p,sort_keys=True)}])
    result['next_actions']=['Review conditional route/helper output and preserve all source/legal/engineering/assurance requirements; no external action authorized.']
    final=propose(working,result,'Route explicit analytical recipes to byte-verified development specialists')['state'];final['revision']=state['revision']+1;validate_state(final)
    return {'result':result,'proposal':{'base_revision':state['revision'],'reason':'Atomic source-preserving specialist analytical route; no external action','state':final}}
