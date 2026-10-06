"""Fictional alternatives; freshly recompute every selected finance result."""
import copy
import json
from tests.test_finance_business_case import business_case_fixture


def investment_fixture():
    state, case = business_case_fixture()
    ids = {'a-npv', 'b-npv', 'comparison', 'ranking', 'a-sensitivity', 'b-sensitivity'}
    source = {r['id']: r for r in state['results'] if r['id'] in ids}
    state['results'] = [r for r in state['results'] if r['id'] not in ids]
    state['revision'] = 0
    dependencies = {'a-npv': [], 'b-npv': [], 'a-sensitivity': [], 'b-sensitivity': [],
                    'comparison': ['a-npv', 'b-npv'], 'ranking': ['comparison']}
    steps = []
    for ident in ('a-npv', 'b-npv', 'a-sensitivity', 'b-sensitivity', 'comparison', 'ranking'):
        r = source[ident]
        basis = json.loads(next(d['message'] for d in r['diagnostics'] if d['code'] == 'FINANCIAL_ANALYSIS_BASIS'))
        steps.append({'skill': r['skill'], 'parameters': copy.deepcopy(basis), 'depends_on': dependencies[ident]})
    steps.append({'skill': 'build-sustainability-business-case', 'parameters': copy.deepcopy(case),
        'depends_on': ['ranking', 'a-sensitivity', 'b-sensitivity']})
    return state, {'steps': steps, 'outputs': ['business-case'], 'result_id': 'investment-specialist',
        'workflow_review': {'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
            'evidence_ids': ['annual-net-evidence'], 'scope': 'Fictional alternative investment screening; no portfolio or funding decision.',
            'reviewer_role': 'Qualified engineering and finance reviewer', 'rationale': 'Conditional source models and pending human decision.',
            'coverage_complete': False}}
