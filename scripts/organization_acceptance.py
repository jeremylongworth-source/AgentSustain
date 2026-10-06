"""Requirement-mapped author-led fictional workflow acceptance; no release approval."""
import copy
import hashlib
import math
from pathlib import Path
from .business_ingestion import ingest_business_csv
from .contract_validation import ROOT, validate_state
from .jurisdiction_tasks import _diagnostic
from .manager_workflow import run_manager


def evaluate_organization_acceptance(case, oracle):
    request = case['ingestion_request']; p = request['parameters']; initial = request['state']
    if request['skill'] != 'ingest-business-records' or p['fixture_mode'] is not True or p['file_pin']['synthetic'] is not True:
        raise ValueError('This acceptance scenario requires explicit fictional-source mode.')
    original = copy.deepcopy(initial)
    path = ROOT / p['file_pin']['path']
    # The importer owns path/size/hash enforcement; do not open an unvalidated path here.
    ingestion = ingest_business_csv(initial, p)
    if ingestion['result']['status'] == 'blocked':
        return {'execution_contract': 'organization-acceptance-0.1.0', 'scenario_status': 'failed',
                'checks': [{'id': 'ORG-01', 'requirement': 'Pinned business data imports', 'passed': False}],
                'ingestion': ingestion, 'manager': None, 'independent_organization_acceptance': False,
                'public_v1_readiness': False, 'publication_authorized': False}
    normalized = ingestion['proposal']['state']; recipe = case['manager_parameters']
    manager = run_manager(normalized, recipe); final = manager['proposal']['state']; validate_state(final)
    results = {r['id']: r for r in final['results']}; plan = _diagnostic(manager['result'], 'ORGANIZATION_MANAGER')
    operations = _diagnostic(results[recipe['operations']['result_id']], 'OPERATIONS_PLAN')
    checks = []
    def check(ident, requirement, passed, observed=None):
        checks.append({'id': ident, 'requirement': requirement, 'passed': bool(passed), 'observed': observed})
    def metric(ident):
        r = results.get(ident)
        return r['metrics'][0] if r and r['metrics'] else None
    def answer(ident):
        m = metric(ident); expected = oracle['expected_metrics'][ident]
        tolerance = oracle['financial_absolute_tolerance'] if expected['unit'] == 'CAD' else oracle['ratio_absolute_tolerance']
        return m is not None and m['unit'] == expected['unit'] and math.isclose(m['value'], expected['value'], rel_tol=0, abs_tol=tolerance)
    check('ORG-01', 'Pinned raw records and explicit observation/model classifications',
          len(ingestion['result']['metrics']) == 18 and _diagnostic(ingestion['result'], 'CSV_ROW_SOURCE')['source_authenticity_verified'] is False,
          {'metrics':len(ingestion['result']['metrics']),'source_version':p['file_pin']['source_version']})
    check('ORG-02', 'Sustainability baseline has declared known value and energy unit', answer('strategy-baseline'))
    check('ORG-03', 'Partial GHG inventory has declared known answer; no unknown scopes become zero',
          answer('operations-inventory') and results['operations-inventory']['status'] == 'partial')
    check('ORG-04', 'Energy/water/material/waste remain four separate known physical quantities',
          all(answer(k) for k in ('ops-energy','ops-water','ops-materials','ops-waste')))
    hotspot = results.get('operations-emission-hotspots')
    check('ORG-05', 'Selected inventory hotspot retains incomplete coverage qualification',
          bool(hotspot and hotspot['status']=='partial' and hotspot['metrics'] and hotspot['metrics'][0]['unit']=='kg CO2e'
               and hotspot['metrics'][0]['value']==oracle['expected_metrics']['operations-inventory']['value']))
    check('ORG-06', 'Four sourced opportunity candidates remain proposed',
          len(operations['opportunities'])==oracle['expected_opportunity_count'] and operations['implementation_authorized'] is False)
    check('ORG-07', 'Explicit modeled monetary cash flows reproduce the separate declared NPV', answer('ops-finance'))
    target = metric('strategy-target')
    check('ORG-08', 'Future intensity target retains service unit and its own target period',
          answer('strategy-target') and target['period']==oracle['expected_target_period'])
    roadmap = _diagnostic(results[recipe['roadmap']['result_id']], 'IMPLEMENTATION_ROADMAP')
    check('ORG-09', 'Source-linked roadmap retains unresolved delivery and funding conditions',
          roadmap['implementation_authorized'] is False and roadmap['funding_authorized'] is False and roadmap['delivery_screen']=='unresolved_conditions')
    kpi = results[recipe['kpis']['result_id']]
    definitions = _diagnostic(kpi, 'KPI_DEFINITIONS')
    check('ORG-10', 'KPI definitions resolve the selected baseline and supplied service denominator',
          kpi['status']=='partial' and bool(definitions['definitions']) and recipe['kpis']['definitions'][0]['denominator_metric_id']=='production')
    mapping = results[recipe['disclosure']['result_id']]
    check('ORG-11', 'Historical disclosure candidates remain qualified and unapproved',
          mapping['status']=='partial' and plan['framework_conformity_verified'] is False)
    valid_views = (set(plan['source_result_views']) == {r['id'] for r in final['results'][len(normalized['results']):] if r['id'] != manager['result']['id']}
                   and len(plan['stages']) == oracle['expected_manager_stage_count'])
    for view in plan['source_result_views'].values():
        ident = view['result_id']
        valid_views = valid_views and view['sha256_result_utf8_json_sorted_keys'] == _result_hash(results[ident])
    check('ORG-12', 'Evidence-backed outputs retain exact current source-result views', valid_views)
    check('CUST-01', 'Original input state and raw byte pin are unchanged', initial==original and hashlib.sha256(path.read_bytes()).hexdigest()==p['file_pin']['sha256'])
    check('CUST-02', 'Manager receives the exact normalized candidate and preserves prior result history', final['results'][:len(normalized['results'])]==normalized['results'])
    check('CUST-03', 'All prior and newly imported evidence remains unchanged', final['evidence']==normalized['evidence'])
    check('CUST-04', 'Factor registry remains supplied and unchanged', final['emission_factors']==initial['emission_factors'])
    check('CUST-05', 'Reporting period, jurisdiction, facilities and boundaries remain unchanged',
          all(final[k]==initial[k] for k in ('reporting_period','jurisdictions','facilities','organizational_boundary')))
    check('CUST-06', 'Assumptions and existing gaps remain with conditional outcomes',
          set(normalized['assumptions'])<=set(final['assumptions']) and all(g in final['data_gaps'] for g in normalized['data_gaps']))
    check('CUST-07', 'All prior review decisions survive without resolution', all(r in final['review_requirements'] for r in normalized['review_requirements']))
    check('CUST-08', 'Two source/manager proposals produce two atomic revisions', final['revision']==initial['revision']+2)
    check('CUST-09', 'Physical, monetary and future quantities are not cross-domain summed', plan['combined_cross_domain_total'] is None)
    no_authority = ('source_authenticity_verified','organization_coverage_authenticated','finance_benefit_attribution_verified',
                    'target_feasibility_verified','progress_verified','funding_or_implementation_authorized',
                    'framework_conformity_verified','publication_authorized','v1_readiness_verified')
    check('CUST-10', 'Professional/assurance review remains open without source, financial, legal, progress or publication approval',
          all(plan[k] is False for k in no_authority) and bool([r for r in final['review_requirements'] if r['status']=='open']))
    return {'execution_contract':'organization-acceptance-0.1.0','scenario_status':'passed' if all(c['passed'] for c in checks) else 'failed',
            'checks':checks,'ingestion':ingestion,'manager':manager,
            'evaluation_scope':'Author-led fictional requirement-mapped pipeline with a separately declared answer key',
            'independent_organization_acceptance':False,'public_v1_readiness':False,'publication_authorized':False}


def _result_hash(result):
    import json
    return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
