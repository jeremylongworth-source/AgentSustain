"""Fresh source calculation through separate draft maps and independent version diff."""
import copy
from tests.test_carbon_workflow import carbon_workflow_fixture
from tests.test_frameworks import framework_fixture, pin


def reporting_fixture():
    state, carbon = carbon_workflow_fixture()
    _, mapping = framework_fixture()
    steps = copy.deepcopy(carbon['steps'][:-1])
    for basis in ('location', 'market'):
        p = copy.deepcopy(mapping); p.update(inventory_result_id='batch-'+basis+'-inventory', result_id=basis+'-disclosure')
        p['mapping_review'].update(boundary_id=state['organizational_boundary']['id'], period=copy.deepcopy(state['reporting_period']))
        steps.append({'skill':'map-framework-disclosures','parameters':p,'depends_on':['batch-'+basis+'-inventory']})
    steps.append({'skill':'compare-framework-mappings','parameters':{'before':pin('fictional-review-exercise-1'),
        'after':pin('fictional-review-exercise-2'),'mapping_review':copy.deepcopy(mapping['mapping_review']),
        'result_id':'edition-diff','fixture_mode':True},'depends_on':[]})
    return state, {'steps':steps,'outputs':['location-disclosure','market-disclosure','edition-diff'],
        'reporting_review':{'boundary_id':state['organizational_boundary']['id'],'period':copy.deepcopy(state['reporting_period']),
            'evidence_ids':['ev-001'],'scope':'Fictional selected purchased electricity; fictional exercise mappings only.',
            'reviewer_role':'Qualified framework/source/rights and accountable-owner reviewer',
            'rationale':'Distinct scope accounts, missing direct emissions and external requirements retained.','coverage_complete':False},
        'result_id':'reporting-specialist'}
