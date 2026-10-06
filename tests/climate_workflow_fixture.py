import copy
import json
from scripts.contract_validation import ROOT, validate_state


def climate_workflow_fixture():
    frozen = json.loads((ROOT / 'evaluations/sus16-climate-resilience.json').read_text(encoding='utf-8'))
    original = frozen['request']['state']; state = copy.deepcopy(original)
    state['results'] = [copy.deepcopy(original['results'][0])]
    state['data_gaps'] = copy.deepcopy(state['results'][0]['data_gaps'])
    state['assumptions'] = list(state['results'][0]['assumptions'])
    state['review_requirements'] = copy.deepcopy(state['results'][0]['review_requirements'])
    state['revision'] = 0
    for name in ('energy', 'water', 'materials', 'waste'): state[name] = [i for i in state[name] if i == state['results'][0]['id']]
    for name in state['ghg']: state['ghg'][name] = []
    climate = original['results'][1:]
    dependencies = {
        'climate-hazards': [], 'climate-map': ['climate-hazards'], 'climate-exposure': ['climate-map'],
        'climate-vulnerability': ['climate-exposure'], 'physical-risk': ['climate-vulnerability'],
        'transition-policy': [], 'transition-market': [], 'transition-technology': [], 'transition-reputation': [],
        'transition-exposure': ['transition-policy', 'transition-market', 'transition-technology', 'transition-reputation'],
        'climate-register': ['physical-risk', 'transition-exposure'], 'climate-priorities': ['climate-register'],
        'adaptation-options': ['physical-risk'],
    }
    steps = []
    for result in climate:
        params = json.loads(next(d['message'] for d in result['diagnostics'] if d['code'] == 'CLIMATE_INPUTS'))
        steps.append({'skill': result['skill'], 'parameters': params, 'depends_on': dependencies[result['id']]})
    request = frozen['request']; params = copy.deepcopy(request['parameters'])
    steps.append({'skill': request['skill'], 'parameters': params, 'depends_on': ['climate-priorities', 'adaptation-options']})
    review = {'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
        'evidence_ids': ['ev-001'], 'scope': 'Selected fictional physical/transition screening and prospective resilience.',
        'rationale': 'One coherent current source set; no probability, loss, legal determination or verified resilience.',
        'reviewer_role': 'Fictional climate/site specialist', 'coverage_complete': False}
    validate_state(state)
    return state, {'steps': steps, 'outputs': ['climate-register', 'climate-priorities', params['result_id']], 'workflow_review': review, 'result_id': 'climate-specialist'}
