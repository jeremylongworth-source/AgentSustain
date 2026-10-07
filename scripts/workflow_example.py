"""Reconstruct a bounded fictional source-to-manager example; no acceptance decision."""
import copy

from .business_ingestion import ingest_business_csv
from .contract_validation import validate_shape, validate_state
from .fuel_energy import run_fuel_energy
from .manager_workflow import run_manager


FIELDS = {'record_type', 'version', 'source_ingestion_request', 'sequential_fuel_parameters',
          'supplied_factor_evidence', 'supplied_emission_factors', 'manager_parameters',
          'instructions', 'independent_evaluation_status', 'external_action_authorized'}


def run_workflow_example(bundle, omit_factor_ids=()):
    if not isinstance(bundle, dict) or set(bundle) != FIELDS:
        raise ValueError('Exact supported fictional example fields required')
    if (bundle['record_type'] != 'prepared_blind_food_workflow_input' or bundle['version'] != '0.1.0'
            or bundle['external_action_authorized'] is not False):
        raise ValueError('Supported fictional example version and authority boundary required')
    request = bundle['source_ingestion_request']
    validate_shape('input.schema.json', request)
    if request['skill'] != 'ingest-business-records' or request['parameters'].get('fixture_mode') is not True:
        raise ValueError('Explicit fictional CSV ingestion required')
    steps = bundle['sequential_fuel_parameters']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 16:
        raise ValueError('Bounded sequential fuel parameters required')
    evidence = bundle['supplied_factor_evidence']
    factors = bundle['supplied_emission_factors']
    if not isinstance(evidence, list) or not isinstance(factors, list) or len(evidence) > 64 or len(factors) > 64:
        raise ValueError('Bounded explicit factor/evidence records required')
    if not isinstance(omit_factor_ids, (list, tuple)) or any(not isinstance(n, str) or not n.strip() for n in omit_factor_ids):
        raise ValueError('Explicit factor identities required')
    supplied_ids = [f['id'] for f in factors]
    if len(set(omit_factor_ids)) != len(omit_factor_ids) or not set(omit_factor_ids) <= set(supplied_ids):
        raise ValueError('Distinct omitted factors must be explicitly supplied')

    # Work on a private candidate, never mutate the caller's records or invent
    # a coefficient. The underlying helpers retain their normal refusal rules.
    initial = copy.deepcopy(request)
    output = ingest_business_csv(initial['state'], initial['parameters'])
    state = output['proposal']['state']
    preparation_ids = [output['result']['id']]
    for parameters in steps:
        output = run_fuel_energy(state, copy.deepcopy(parameters))
        state = output['proposal']['state']
        preparation_ids.append(output['result']['id'])
    state = copy.deepcopy(state)
    state['evidence'].extend(copy.deepcopy(evidence))
    state['emission_factors'].extend(copy.deepcopy([f for f in factors if f['id'] not in omit_factor_ids]))
    validate_state(state)
    manager = run_manager(state, copy.deepcopy(bundle['manager_parameters']))
    return {'workflow_example_version': '0.1.0', 'execution_status': manager['result']['status'],
            'preparation_result_ids': preparation_ids, 'omitted_factor_ids': list(omit_factor_ids),
            'manager_output': manager, 'example_data_authenticated': False,
            'independent_acceptance': False, 'publication_authorized': False,
            'public_v1_readiness': False}
