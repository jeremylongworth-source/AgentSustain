"""Draft real-source GHGRP predicates; no statutory quantity or legal decision."""
import copy
import json
import re
from .contract_validation import validate_state
from .jurisdiction_subjects import load_subject_pack, screen_subject_jurisdiction
from .jurisdiction_tools import _number
from .state_proposal import propose


PATHS = {'canada/ghgrp/notice-2023.json', 'canada/ghgrp/notice-2023-amended2025.json'}


def screen_canada_ghgrp(state, parameters):
    validate_state(state)
    if not isinstance(parameters,dict) or not isinstance(parameters.get('pack_pins'),list) or len(parameters['pack_pins']) != 1:
        raise ValueError('Select exactly one original or amended Canada GHGRP edition; no implicit migration.')
    pin=parameters['pack_pins'][0]
    if not isinstance(pin,dict) or pin.get('path') not in PATHS:
        raise ValueError('Select an exact supported Canadian GHGRP draft module path.')
    pack=load_subject_pack(pin,parameters.get('fixture_mode',False))
    definitions={a['id']:a for a in pack['attributes']}
    allowed={}
    for rule in pack['rules']:
        expression=rule['condition']
        for child in expression.get('all',[expression]):
            if child.get('operator')=='intersects':allowed[child['attribute']]=set(child['value'])
    for fact in parameters.get('facts',[]):
        ident=fact.get('attribute_id');value=fact.get('value')
        if ident not in definitions:raise ValueError('Only the selected module attributes are supported.')
        if value is None:continue
        if ident=='operating_jurisdictions' and (not isinstance(value,list) or any(not isinstance(v,str) or re.fullmatch(r'[A-Z]{2}',v) is None for v in value)):
            raise ValueError('Explicit country codes required; provincial jurisdiction strings do not establish a country roster.')
        if ident=='threshold_emissions' and isinstance(value,dict):
            if any(_number(value[k])<0 for k in ('lower','upper')):
                raise ValueError('Threshold gross emission bounds cannot be negative; net reductions are not this quantity.')
        if ident in allowed and (not isinstance(value,list) or not set(value)<=allowed[ident]):
            raise ValueError('Explicit supported classification/activity identifiers required; no NAICS prefix or narrative inference.')
    out=screen_subject_jurisdiction(state,copy.deepcopy(parameters));result=copy.deepcopy(out['result'])
    result['diagnostics'].append({'code':'CANADA_GHGRP_DRAFT','message':json.dumps({
        'execution_contract':'canada-ghgrp-screen-0.1.0','selected_version':pack['version'],
        'pack_activated_or_approved':False,'statutory_quantity_reproduced':False,'legal_applicability_determined':False,
        'source_currentness_authenticated':False,'commercial_use_authorized':False,'filing_authorized':False,
        'primary_source_chain':['https://gazette.gc.ca/rp-pr/p1/2023/2023-12-09/html/sup1-eng.html',
            'https://gazette.gc.ca/rp-pr/p1/2025/2025-12-06/html/notice-avis-eng.html'],
        'limits':'Declared threshold, grouping, classification, activity and operator facts remain conditional; gas/method/coverage, tasks and qualified source/legal/reuse review remain open.'},sort_keys=True)})
    return {'result':result,'proposal':propose(state,result,'Draft Canadian source predicates only; no statutory quantity or legal determination')}
