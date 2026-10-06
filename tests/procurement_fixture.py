import copy
import json
from scripts.contract_validation import ROOT


def procurement_fixture():
    frozen = json.loads((ROOT / 'evaluations/sus14-procurement-options.json').read_text(encoding='utf-8'))
    state = copy.deepcopy(frozen['state'])
    category = next(r for r in state['results'] if r['id'] == 'two-purchases')
    report = json.loads(next(d['message'] for d in category['diagnostics'] if d['code'] == 'SCOPE3_CATEGORY'))
    steps = []
    for index, component in enumerate(report['components'], 1):
        source = next(s for s in report['sources'] if s['id'] == component['source_id'])
        ident = 'procurement-leaf-' + str(index)
        steps.append({'skill': 'calculate-co2e', 'parameters': {'activity_id': source['activity_id'], 'factor_id': component['factor_id'],
            'policy': copy.deepcopy(component['policy']), 'fixture_mode': True, 'result_id': ident}, 'depends_on': []})
        component['metric_id'] = ident + '-metric'
    steps.append({'skill': 'calculate-scope-3-category', 'parameters': {'category': report['category'], 'sources': report['sources'],
        'components': report['components'], 'coverage_review': report['coverage_review'], 'fixture_mode': True, 'result_id': 'procurement-category'},
        'depends_on': [s['parameters']['result_id'] for s in steps]})
    original_map = next(r for r in state['results'] if r['id'] == 'supply-chain-mapping')
    mapping = json.loads(next(d['message'] for d in original_map['diagnostics'] if d['code'] == 'SUPPLIER_INPUTS'))
    mapping['result_id'] = 'procurement-mapping'
    for link in mapping['links']: link['category_result_id'] = 'procurement-category'
    steps.append({'skill': 'map-supply-chain-emissions', 'parameters': mapping, 'depends_on': ['procurement-category']})
    option = copy.deepcopy(frozen['parameters']); option['result_id'] = 'procurement-option'
    for key in ('baseline', 'alternative'): option[key]['mapping_result_id'] = 'procurement-mapping'
    steps.append({'skill': 'evaluate-low-carbon-procurement-option', 'parameters': option, 'depends_on': ['procurement-mapping']})
    review = {'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
        'scope': 'Fictional selected buyer purchases and conditional equal-service alternatives.', 'evidence_ids': ['ev-001'],
        'reviewer_role': 'Fictional buyer reviewer', 'rationale': 'Exact supplied physical factors and buyer review; no source authentication, purchase or implemented benefit.',
        'coverage_complete': False}
    return state, {'steps': steps, 'outputs': ['procurement-mapping', 'procurement-option'], 'procurement_review': review, 'result_id': 'procurement-batch'}


def supplier_planning_fixture():
    frozen = json.loads((ROOT / 'evaluations/sus14-supplier-planning.json').read_text(encoding='utf-8'))
    state = copy.deepcopy(frozen['state']); steps = []
    for record in state['results']:
        if record['skill'] != 'score-supplier-sustainability': continue
        params = json.loads(next(d['message'] for d in record['diagnostics'] if d['code'] == 'SUPPLIER_INPUTS'))
        params['result_id'] = 'fresh-' + record['id']
        steps.append({'skill': record['skill'], 'parameters': params, 'depends_on': []})
    for original in frozen['steps']:
        params = copy.deepcopy(original['parameters'])
        if 'assessment_result_ids' in params: params['assessment_result_ids'] = ['fresh-' + i for i in params['assessment_result_ids']]
        if 'assessment_result_id' in params: params['assessment_result_id'] = 'fresh-' + params['assessment_result_id']
        dependencies = params.get('assessment_result_ids', [params['assessment_result_id']] if 'assessment_result_id' in params else [])
        steps.append({'skill': original['skill'], 'parameters': params, 'depends_on': dependencies})
    review = {'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
        'scope': 'Fictional buyer rubric and unsent evidence/implementation proposals.', 'evidence_ids': ['ev-001'],
        'reviewer_role': 'Fictional buyer reviewer', 'rationale': 'Preserve unknown ratings, ties, ownership and proposed actions; no contact or selection.', 'coverage_complete': False}
    return state, {'steps': steps, 'outputs': [s['parameters']['result_id'] for s in steps[-2:]], 'procurement_review': review, 'result_id': 'supplier-planning-batch'}
