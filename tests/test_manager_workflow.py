import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.contract_validation import ROOT, validate_state
from scripts.manager_workflow import run_manager
from scripts.operations_tools import run_operations, _run_carbon
from scripts.strategy_tools import run_strategy
from scripts.framework_tools import run_framework
from tests.manager_fixture import manager_fixture


def report(output):
    return json.loads(next(d['message'] for d in output['result']['diagnostics'] if d['code'] == 'ORGANIZATION_MANAGER'))


class ManagerWorkflowTests(unittest.TestCase):
    def test_coherent_known_answers_and_preserved_units(self):
        state, p = manager_fixture(); original = copy.deepcopy(state); output = run_manager(state, p)
        final = output['proposal']['state']; indexed = {r['id']: r for r in final['results']}; plan = report(output)
        expected = {'strategy-baseline': (1500, 'kWh'), 'ops-energy': (1500, 'kWh'), 'ops-water': (15, 'm3'),
                    'ops-waste': (1000, 'kg'), 'ops-materials': (2000, 'kg'), 'operations-inventory': (750, 'kg CO2e'),
                    'strategy-target': (4, 'kWh/count')}
        for ident, value in expected.items():
            with self.subTest(ident=ident): self.assertEqual((indexed[ident]['metrics'][0]['value'], indexed[ident]['metrics'][0]['unit']), value)
        self.assertAlmostEqual(indexed['ops-finance']['metrics'][0]['value'], 41.32231404958678)
        self.assertEqual(indexed['ops-finance']['metrics'][0]['unit'], 'CAD')
        self.assertEqual(len(plan['opportunity_ids']), 4); self.assertEqual(len(plan['stages']), 8)
        self.assertEqual(output['result']['metrics'], []); self.assertEqual(output['result']['status'], 'partial')
        self.assertEqual(final['revision'], state['revision'] + 1); self.assertEqual(state, original); validate_state(final)
        self.assertEqual(indexed['strategy-target']['metrics'][0]['period']['start'], '2030-01-01')
        self.assertEqual(indexed['operations-inventory']['metrics'][0]['period'], state['reporting_period'])
        self.assertIsNone(plan['combined_cross_domain_total'])

    def test_each_existing_stage_result_matches_standalone_execution(self):
        state, p = manager_fixture(); output = run_manager(state, p); indexed = {r['id']: r for r in output['proposal']['state']['results']}
        slots = [('establish-baseline', p['baseline']), ('define-kpis', p['kpis']), ('sustainable-operations', p['operations']),
                 ('develop-target', p['targets'][0]), ('build-sustainability-strategy', p['strategy']),
                 ('build-transition-plan', p['transition']), ('build-implementation-roadmap', p['roadmap']), ('map-framework-disclosures', p['disclosure'])]
        working = copy.deepcopy(state)
        for skill, params in slots:
            single = run_operations(working, params) if skill == 'sustainable-operations' else (
                run_framework(working, skill, params) if skill == 'map-framework-disclosures' else run_strategy(working, skill, params))
            self.assertEqual(single['result'], indexed[params['result_id']], skill)
            working = single['proposal']['state']

    def test_missing_factors_withhold_inventory_mapping_but_keep_physical_and_target_branches(self):
        state, p = manager_fixture()
        for step in p['operations']['steps']:
            if step['skill'] == 'calculate-co2e': step['parameters']['factor_id'] = 'missing'
            if step['skill'] == 'calculate-location-based-scope-2':
                for component in step['parameters']['components']: component['factor_id'] = 'missing'
        output = run_manager(state, p); plan = report(output); indexed = {r['id']: r for r in output['proposal']['state']['results']}
        disclosure = next(s for s in plan['stages'] if s['skill'] == 'map-framework-disclosures')
        self.assertFalse(disclosure['helper_invoked']); self.assertEqual(disclosure['status'], 'blocked')
        self.assertEqual(indexed['operations-inventory']['metrics'], [])
        self.assertEqual(indexed['ops-water']['metrics'][0]['value'], 15)
        self.assertEqual(indexed['strategy-target']['metrics'][0]['value'], 4)
        self.assertIn('EMISSION_FACTOR_REQUIRED', [d['code'] for d in output['result']['diagnostics']])

    def test_scope_and_recipe_source_substitution_rejected_before_execution(self):
        state, original = manager_fixture()
        for variant in ('energy-subset', 'old-inventory', 'old-baseline', 'old-kpis', 'old-strategy', 'old-transition', 'duplicate', 'wrong-period'):
            p = copy.deepcopy(original)
            if variant == 'energy-subset': p['baseline']['metric_ids'] = ['metric-001']
            elif variant == 'old-inventory': p['disclosure']['inventory_result_id'] = 'old-inventory'
            elif variant == 'old-baseline': p['kpis']['definitions'][0]['baseline_result_id'] = 'res-001'
            elif variant == 'old-kpis': p['targets'][0]['definition_result_id'] = 'res-001'
            elif variant == 'old-strategy': p['transition']['strategy_result_id'] = 'res-001'
            elif variant == 'old-transition': p['roadmap']['transition_result_id'] = 'res-001'
            elif variant == 'duplicate': p['targets'][0]['result_id'] = p['baseline']['result_id']
            else: p['manager_review']['period'] = {'start': '2026-01-01', 'end': '2026-12-31'}
            with self.subTest(variant=variant), self.assertRaises(ValueError): run_manager(state, p)

    def test_invalid_service_source_blocks_dependent_plans_without_stopping_operations(self):
        state, p = manager_fixture(); p['kpis']['definitions'][0]['denominator_metric_id'] = 'missing-production'
        output = run_manager(state, p); stages = {s['skill']: s for s in report(output)['stages']}
        self.assertEqual(stages['define-kpis']['status'], 'blocked')
        self.assertFalse(stages['develop-target']['helper_invoked']); self.assertFalse(stages['build-transition-plan']['helper_invoked'])
        self.assertTrue(stages['sustainable-operations']['helper_invoked']); self.assertTrue(stages['map-framework-disclosures']['helper_invoked'])
        self.assertEqual(stages['map-framework-disclosures']['status'], 'partial')

    def test_source_views_resolve_exact_results_and_every_history_review_survives(self):
        state, p = manager_fixture(); state['review_requirements'].append({'id': 'existing-legal', 'state': 'LEGAL_REVIEW_REQUIRED',
            'reason': 'Fictional existing obligation', 'scope': 'Original source context', 'reviewer_role': 'Qualified legal reviewer', 'status': 'open', 'resolution': None})
        output = run_manager(state, p); final = output['proposal']['state']; indexed = {r['id']: r for r in final['results']}
        for ident, view in report(output)['source_result_views'].items():
            self.assertEqual(view['sha256_result_utf8_json_sorted_keys'], hashlib.sha256(json.dumps(indexed[ident], sort_keys=True).encode()).hexdigest())
        self.assertEqual(final['results'][:len(state['results'])], state['results'])
        self.assertEqual(final['evidence'], state['evidence']); self.assertEqual(final['emission_factors'], state['emission_factors'])
        self.assertIn(state['review_requirements'][0], output['result']['review_requirements'])
        self.assertIn('LEGAL_REVIEW_REQUIRED', output['result']['review_states'])
        self.assertTrue(all(r['status'] == 'open' for r in output['result']['review_requirements']))

    def test_complete_declaration_and_old_mapping_pin_do_not_grant_readiness(self):
        state, p = manager_fixture(); p['manager_review']['coverage_complete'] = True
        output = run_manager(state, p); plan = report(output)
        for key in ('source_authenticity_verified', 'organization_coverage_authenticated', 'finance_benefit_attribution_verified',
                    'target_feasibility_verified', 'progress_verified', 'funding_or_implementation_authorized', 'framework_conformity_verified',
                    'publication_authorized', 'v1_readiness_verified', 'raw_business_data_ingestion_performed'):
            self.assertFalse(plan[key], key)
        p['disclosure']['adapters'][0]['catalog_sha256'] = '0' * 64
        output = run_manager(state, p)
        self.assertEqual(report(output)['stages'][-1]['status'], 'blocked')
        self.assertEqual(output['result']['status'], 'partial')

    def test_read_only_cli_equals_helper(self):
        state, p = manager_fixture(); request = {'contract_version': '0.1.0', 'skill': 'sustainability-manager', 'state': state, 'parameters': p}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'request.json'; raw = json.dumps(request).encode(); path.write_bytes(raw)
            run = subprocess.run([sys.executable, '-m', 'scripts.run_manager', str(path)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stdout); self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(json.loads(run.stdout), run_manager(state, p))

    def test_prior_derived_context_is_retained_without_relabeling_it_as_business_data(self):
        state, p = manager_fixture()
        params = copy.deepcopy(next(s['parameters'] for s in p['operations']['steps'] if s['skill'] == 'calculate-co2e'))
        params['result_id'] = 'prior-derived-carbon'
        state = _run_carbon(state, 'calculate-co2e', params)['proposal']['state']
        output = run_manager(state, p); plan = report(output)
        self.assertIn('prior-derived-carbon', plan['input_result_ids'])
        self.assertNotIn('prior-derived-carbon', plan['normalized_input_result_ids'])
        self.assertEqual(output['proposal']['state']['results'][:len(state['results'])], state['results'])
