"""Byte-pinned plain-text claim binding; no inferred meaning or publication approval."""
import copy
import hashlib
import json
from pathlib import Path

from .climate_tools import _fields
from .contract_validation import ROOT, validate_state
from .data_tools import number
from .claims_review import assess_claim
from .state_proposal import propose


def _span(text, span):
    _fields(span, {'start','end'})
    start,end=span['start'],span['end']
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(text):
        raise ValueError('Explicit nonempty Unicode character spans inside exact material text required.')
    return text[start:end]


def bind_material(state, parameters):
    pin=parameters['material_pin'];_fields(pin, {'path','sha256'}, ('path','sha256'))
    base=(ROOT/'standards/claims/materials').resolve();relative=Path(pin['path']);path=(base/relative).resolve()
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(base) or path.suffix!='.json':
        raise ValueError('Claim material must resolve within standards/claims/materials; no external paths.')
    if path.stat().st_size>131072:raise ValueError('Bounded claim material file required.')
    raw=path.read_bytes()
    if len(raw)>131072:raise ValueError('Bounded claim material file required.')
    if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Material bytes differ from explicit source pin.')
    material=json.loads(raw)
    _fields(material, {'id','version','synthetic','format','text'}, ('id','version','format','text'))
    if material['format']!='plain_text' or type(material['synthetic']) is not bool or material['synthetic'] and not parameters['fixture_mode']:
        raise ValueError('Explicit plain-text source; synthetic material requires fixture mode.')
    claim=parameters['claim'];ids=claim['material_evidence_ids']
    if not isinstance(ids,list) or len(ids)!=1:raise ValueError('One exact bound material evidence record required.')
    evidence=next((e for e in state['evidence'] if e['id']==ids[0]),None)
    locator='workspace:standards/claims/materials/'+relative.as_posix()
    if evidence is None or evidence['source']['locator']!=locator or evidence['source']['version']!=material['version']:
        raise ValueError('Evidence locator/version must bind this exact selected workspace material.')
    selectors=parameters['material_selectors'];_fields(selectors, {'claim_span','qualification_spans','quantity_spans'})
    text=material['text'];selected=_span(text,selectors['claim_span'])
    if selected!=claim['text']:raise ValueError('Declared original statement must equal the selected source text exactly; no rewriting/normalization.')
    if not isinstance(selectors['qualification_spans'],list) or not isinstance(selectors['quantity_spans'],list):
        raise ValueError('Explicit qualification and quantity selector lists required.')
    qualifications=[]
    for item in selectors['qualification_spans']:
        _fields(item, {'text','span'}, ('text',))
        if _span(text,item['span'])!=item['text']:raise ValueError('Qualification must match actual source characters.')
        qualifications.append(item['text'])
    if len(set(qualifications))!=len(qualifications) or set(qualifications)!=set(claim['qualifications']):
        raise ValueError('All declared original qualifications must be bound; no invented qualifier or inferred visibility.')
    criteria={c['id']:c for c in parameters['criteria'] if c['quantity'] is not None};quantities=[];seen=set()
    for item in selectors['quantity_spans']:
        _fields(item, {'criterion_id','value_span','unit_span'}, ('criterion_id',))
        ident=item['criterion_id']
        if ident in seen or ident not in criteria:raise ValueError('Distinct quantity selectors for exact active criterion interpretations required.')
        seen.add(ident);value_text=_span(text,item['value_span']);unit_text=_span(text,item['unit_span'])
        a,b=item['value_span'],item['unit_span'];cs=selectors['claim_span']
        if not cs['start']<=a['start']<a['end']<=b['start']<b['end']<=cs['end'] or text[a['end']:b['start']].strip():
            raise ValueError('A value followed directly by its unit must be inside the original statement span.')
        if a['start'] and (text[a['start']-1].isalnum() or text[a['start']-1] in '.+-'):
            raise ValueError('Quantity selector cannot truncate a larger numeric token.')
        if b['end']<len(text) and (text[b['end']].isalnum() or text[b['end']] in '_/^'):
            raise ValueError('Unit selector cannot truncate a larger unit token.')
        criterion=criteria[ident]
        if criterion['quantity']['expected_value'] is None or number(value_text)!=number(criterion['quantity']['expected_value']) or unit_text!=criterion['unit']:
            raise ValueError('Numeric interpretation and unit must match actual selected text; no fabricated value or implicit conversion.')
        quantities.append({'criterion_id':ident,'selected_value_text':value_text,'selected_unit_text':unit_text,'selectors':copy.deepcopy(item)})
    if seen!=set(criteria):raise ValueError('Every supplied numerical interpretation requires an exact material selector.')
    return {'material_pin':copy.deepcopy(pin),'material_snapshot':material,'evidence_snapshot':copy.deepcopy(evidence),
        'selectors':copy.deepcopy(selectors),'selected_original_text':selected,'bound_qualifications':qualifications,
        'bound_quantities':quantities,'byte_integrity_verified':True,'exact_text_match_verified':True,
        'format':'plain_text','semantic_interpretation_verified':False,'visual_prominence_verified':False,
        'authorship_or_actual_publication_verified':False,'source_authenticity_verified':False}


def assess_bound_claim(state, parameters):
    validate_state(state)
    _fields(parameters, {'claim','classification_review','criteria','claim_review','fixture_mode','result_id','material_pin','material_selectors'}, ('result_id',))
    if type(parameters['fixture_mode']) is not bool or any(r['id']==parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused claim result ID required.')
    try:
        binding=bind_material(state,parameters)
    except (ValueError,TypeError,KeyError,OSError) as error:
        result={'id':parameters['result_id'],'skill':'assess-bound-claim-evidence','contract_version':'0.1.0','status':'blocked',
            'review_states':list(dict.fromkeys(['ADVISORY','EVIDENCE_INCOMPLETE']+[r['state'] for r in state['review_requirements'] if r['status']=='open'])),
            'review_requirements':copy.deepcopy(state['review_requirements']),'metrics':[],'evidence_ids':[],
            'assumptions':list(state['assumptions']),'data_gaps':copy.deepcopy(state['data_gaps']),
            'diagnostics':[{'code':'CLAIM_MATERIAL_REQUIRED','message':str(error)}],'next_actions':['Reconcile exact source bytes, original text and selectors before claim review.']}
        result['data_gaps'].append({'id':result['id']+'-material-gap','field':'claim_material','reason':str(error),
            'impact':'Original wording/quantity binding is unavailable; no evidence support or public claim follows.',
            'remedy':result['next_actions'][0]})
        return {'result':result,'proposal':propose(state,result,'Block unbound claim text; preserve all source records and reviews')}
    legacy={k:copy.deepcopy(v) for k,v in parameters.items() if k not in {'material_pin','material_selectors'}}
    output=assess_claim(state,legacy);result=output['result'];result['skill']='assess-bound-claim-evidence'
    for d in result['diagnostics']:
        if d['code']=='CLAIM_EVIDENCE_REVIEW':
            report=json.loads(d['message']);report['execution_contract']='claim-evidence-0.2.0';report['material_binding']=binding
            d['message']=json.dumps(report,sort_keys=True)
    result['diagnostics'].append({'code':'BOUND_CLAIM_INPUTS','message':json.dumps(parameters,sort_keys=True)})
    return {'result':result,'proposal':propose(state,result,'Record byte-bound original claim and scoped evidence; no meaning, legal or publication approval')}
