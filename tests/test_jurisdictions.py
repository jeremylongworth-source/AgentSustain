import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.contract_validation import ROOT, validate_state
from scripts.jurisdiction_tools import _evaluate, load_pack, screen_jurisdiction
from scripts.state_proposal import propose


def fixture():
    state = json.loads((ROOT / 'examples/architecture-state.json').read_text(encoding='utf-8'))
    raw = (ROOT / 'standards/jurisdictions/fixtures/fictional-1.json').read_bytes()
    pack = json.loads(raw)
    facts = []
    for attribute in pack['attributes']:
        ident = attribute['id']
        evidence = copy.deepcopy(state['evidence'][0])
        evidence['id'] = 'fact-' + ident
        evidence['source'].update(locator='fixture:' + ident, title='Fictional company attribute record', version='fictional-1')
        evidence['method'].update(name='Fictional company source record', source='fixture:' + ident)
        evidence['unit'] = attribute['unit']
        state['evidence'].append(evidence)
        value = {'operating_jurisdictions': ['ZZ', 'ZZ-AA'], 'employee_count': {'lower': 150, 'upper': 150}, 'research_only': False}[ident]
        facts.append({'attribute_id': ident, 'value': value, 'unit': attribute['unit'],
                      'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
                      'evidence_ids': [evidence['id']], 'evidence_fit': 'reviewed_supporting', 'coverage_complete': True,
                      'rationale': 'Fictional matched legal-entity source only.', 'uncertainty': 'Fictional exact count or complete stated attribute for this case.'})
    rule_reviews = []
    for rule in pack['rules']:
        evidence = copy.deepcopy(state['evidence'][0])
        evidence['id'] = 'source-' + rule['id']
        evidence['source'].update(locator=rule['source']['locator'], title='Fictional primary rule', publisher=rule['source']['authority'],
                                  version=rule['source']['version'], accessed=rule['source']['retrieved'])
        evidence['method'].update(name='Fictional source reading', source=rule['source']['locator'])
        evidence['unit'] = '1'
        evidence['period'] = {'start': '2026-10-05', 'end': '2026-10-05'}
        state['evidence'].append(evidence)
        rule_reviews.append({'pack_id': pack['id'], 'rule_id': rule['id'], 'checked_as_of': '2026-10-05',
                             'evidence_ids': [evidence['id']], 'evidence_fit': 'reviewed_supporting',
                             'rationale': 'Fictional exact source version selected for architecture testing; not real law.'})
    return state, {'pack_pins': [{'path': 'fixtures/fictional-1.json', 'sha256': hashlib.sha256(raw).hexdigest()}],
                   'facts': facts, 'rule_reviews': rule_reviews, 'screening_review': {
                       'boundary_id': state['organizational_boundary']['id'], 'period': copy.deepcopy(state['reporting_period']),
                       'as_of_date': '2026-10-05', 'scope': 'Fictional company and selected reporting rules only.',
                       'evidence_ids': ['fact-operating_jurisdictions'], 'evidence_fit': 'reviewed_supporting',
                       'rationale': 'Explicit fictional entity scope; upstream reviews remain open.', 'reviewer_role': 'Qualified legal reviewer'},
                   'fixture_mode': True, 'result_id': 'jurisdiction-fixture'}


def report(output):
    return json.loads(next(d['message'] for d in output['result']['diagnostics'] if d['code'] == 'JURISDICTION_SCREEN'))


def rows(output):
    return {r['rule']['id']: r for r in report(output)['rows']}


class JurisdictionTests(unittest.TestCase):
    def test_numeric_interval_operators_preserve_strictness_and_uncertainty(self):
        definition = {'n': {'type': 'number'}}
        fact = {'n': {'supported': True, 'record': {'value': {'lower': 100, 'upper': 150}}}}
        checks = [('gte', 100, True), ('gt', 100, None), ('gte', 151, False), ('gt', 150, False),
                  ('lte', 150, True), ('lt', 150, None), ('lte', 99, False), ('lt', 100, False),
                  ('eq', 125, None), ('eq', 200, False), ('ne', 125, None), ('ne', 200, True)]
        for op, threshold, expected in checks:
            with self.subTest(operator=op, threshold=threshold):
                self.assertIs(_evaluate({'attribute': 'n', 'operator': op, 'value': threshold},
                                        fact, definition, set(), []), expected)

    def test_threshold_dates_overlap_and_history_remain_separate(self):
        state, parameters = fixture()
        original = copy.deepcopy(state)
        output = screen_jurisdiction(state, parameters)
        actual = rows(output)
        self.assertEqual(actual['federal-count']['preliminary_status'], 'applicable')
        provincial = actual['province-count']
        self.assertEqual(provincial['preliminary_status'], 'potentially_applicable')
        self.assertEqual(provincial['segments'], [
            {'period': {'start': '2025-01-01', 'end': '2025-06-30'}, 'within_recorded_effective_interval': False, 'preliminary_status': 'not_applicable'},
            {'period': {'start': '2025-07-01', 'end': '2025-12-31'}, 'within_recorded_effective_interval': True, 'preliminary_status': 'applicable'}])
        self.assertEqual(actual['historical-count']['preliminary_status'], 'not_applicable')
        self.assertEqual(actual['draft-count']['preliminary_status'], 'potentially_applicable')
        self.assertFalse(report(output)['rule_precedence_inferred'])
        self.assertFalse(report(output)['jurisdiction_hierarchy_inferred'])
        self.assertEqual(output['result']['status'], 'partial')
        self.assertEqual(output['result']['metrics'], [])
        self.assertEqual(state, original)
        proposed = output['proposal']['state']
        validate_state(proposed)
        for collection in ['evidence', 'results', 'review_requirements', 'assumptions', 'data_gaps']:
            for item in state[collection]: self.assertIn(item, proposed[collection])
        self.assertEqual(proposed['results'][:-1], state['results'])
        self.assertEqual(proposed['jurisdictions'], state['jurisdictions'])
        self.assertIn('LEGAL_REVIEW_REQUIRED', output['result']['review_states'])
        self.assertEqual(output['result']['review_requirements'][-1]['status'], 'open')

    def test_exact_threshold_and_uncertain_ranges(self):
        for low, high, expected in [(99, 99, 'not_applicable'), (100, 100, 'applicable'),
                                    (99, 101, 'undetermined'), (None, 101, 'undetermined')]:
            with self.subTest(bounds=(low, high)):
                state, p = fixture(); p['facts'][1]['value'] = {'lower': low, 'upper': high}
                self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], expected)

    def test_missing_unfit_incomplete_or_wrong_period_facts_stay_unknown(self):
        for change in ['missing', 'null', 'irrelevant', 'incomplete', 'period', 'source_period', 'source_version', 'source_unit']:
            with self.subTest(change=change):
                state, p = fixture()
                if change == 'missing': p['facts'].pop(1)
                elif change == 'null': p['facts'][1]['value'] = None
                elif change == 'irrelevant': p['facts'][1]['evidence_fit'] = 'irrelevant'
                elif change == 'incomplete': p['facts'][1]['coverage_complete'] = False
                elif change == 'period': p['facts'][1]['period']['end'] = '2025-06-30'
                else:
                    source = next(e for e in state['evidence'] if e['id'] == 'fact-employee_count')
                    if change == 'source_period': source['period']['end'] = '2025-06-30'
                    elif change == 'source_version': source['source']['version'] = None
                    elif change == 'source_unit': source['unit'] = 'kWh'
                self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], 'undetermined')

    def test_exception_evidence_and_missing_exception_are_not_implied_exemption(self):
        state, p = fixture(); p['facts'][2]['value'] = True
        selected = rows(screen_jurisdiction(state, p))['federal-count']
        self.assertEqual(selected['preliminary_status'], 'not_applicable')
        self.assertFalse(selected['exemption_authorized'])
        p['facts'][2]['evidence_fit'] = 'unverified'
        self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], 'undetermined')
        p['facts'].pop(2)
        self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], 'undetermined')

    def test_jurisdiction_roster_is_explicit_and_unknown_is_not_absence(self):
        state, p = fixture(); p['facts'][0]['value'] = ['ZZ-AA']
        self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], 'not_applicable')
        p['facts'][0]['coverage_complete'] = False
        self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], 'undetermined')

    def test_source_currency_review_requires_matching_primary_source(self):
        for change in ['missing', 'unfit', 'old_date', 'unrelated_source', 'global_unfit']:
            with self.subTest(change=change):
                state, p = fixture()
                if change == 'missing': p['rule_reviews'].pop(0)
                elif change == 'unfit': p['rule_reviews'][0]['evidence_fit'] = 'unverified'
                elif change == 'old_date': p['rule_reviews'][0]['checked_as_of'] = '2026-10-04'
                elif change == 'unrelated_source': p['rule_reviews'][0]['evidence_ids'] = ['ev-001']
                else: p['screening_review']['evidence_fit'] = 'unverified'
                self.assertEqual(rows(screen_jurisdiction(state, p))['federal-count']['preliminary_status'], 'undetermined')

    def test_bad_input_blocks_without_changing_history(self):
        for change in ['pin', 'path', 'fixture', 'bool_number', 'reversed_range', 'nonfinite', 'unit', 'boundary', 'duplicate_fact', 'orphan_review']:
            with self.subTest(change=change):
                state, p = fixture(); before = copy.deepcopy(state)
                if change == 'pin': p['pack_pins'][0]['sha256'] = '0' * 64
                elif change == 'path': p['pack_pins'][0]['path'] = '../frameworks/ghgp-corporate-2004.json'
                elif change == 'fixture': p['fixture_mode'] = False
                elif change == 'bool_number': p['facts'][1]['value']['lower'] = True
                elif change == 'reversed_range': p['facts'][1]['value'] = {'lower': 200, 'upper': 100}
                elif change == 'nonfinite': p['facts'][1]['value']['lower'] = float('nan')
                elif change == 'unit': p['facts'][1]['unit'] = 'kWh'
                elif change == 'boundary': p['facts'][1]['boundary_id'] = 'different-entity'
                elif change == 'duplicate_fact': p['facts'].append(copy.deepcopy(p['facts'][0]))
                else: p['rule_reviews'][0]['rule_id'] = 'unknown-rule'
                output = screen_jurisdiction(state, p)
                self.assertEqual(output['result']['status'], 'blocked')
                self.assertEqual(state, before)
                validate_state(output['proposal']['state'])

    def test_declarative_pack_validation_rejects_unsafe_or_incomplete_definitions(self):
        state, p = fixture()
        raw = (ROOT / 'standards/jurisdictions/fixtures/fictional-1.json').read_bytes()
        original = json.loads(raw)
        for change in ['operator', 'code', 'attribute', 'date', 'duplicate', 'repealed_end', 'nonempty_logic']:
            with self.subTest(change=change):
                value = copy.deepcopy(original); rule = value['rules'][0]
                if change == 'operator': rule['condition']['operator'] = 'eval'
                elif change == 'code': rule['condition'] = {'execute': 'arbitrary code'}
                elif change == 'attribute': rule['condition']['attribute'] = 'undefined'
                elif change == 'date': rule['effective_from'] = '2026-99-01'
                elif change == 'duplicate': value['rules'].append(copy.deepcopy(rule))
                elif change == 'repealed_end': rule['legal_status'] = 'repealed'
                else: rule['condition'] = {'all': []}
                bad = json.dumps(value).encode(); pin = copy.deepcopy(p['pack_pins'][0]); pin['sha256'] = hashlib.sha256(bad).hexdigest()
                with patch.object(Path, 'read_bytes', return_value=bad):
                    with self.assertRaises(ValueError): load_pack(pin, True)

    def test_historical_repeal_and_unknown_version_or_effective_date(self):
        state, p = fixture(); pack = load_pack(p['pack_pins'][0], True)
        for change in ['historical_active', 'unknown_version', 'unknown_date', 'exceptions_incomplete']:
            with self.subTest(change=change):
                altered = copy.deepcopy(pack)
                if change == 'historical_active': altered['rules'][2]['effective_to'] = '2025-12-31'
                elif change == 'unknown_version': altered['rules'][0]['source']['version'] = None
                elif change == 'unknown_date': altered['rules'][0]['effective_from'] = None
                else: altered['rules'][0]['exceptions_complete'] = False
                with patch('scripts.jurisdiction_tools.load_pack', return_value=altered):
                    actual = rows(screen_jurisdiction(state, p))
                key = 'historical-count' if change == 'historical_active' else 'federal-count'
                self.assertEqual(actual[key]['preliminary_status'], 'applicable' if change == 'historical_active' else 'undetermined')

    def test_compound_logic_retains_unknown_and_all_predicate_traces(self):
        state, p = fixture(); pack = load_pack(p['pack_pins'][0], True)
        pack['rules'][0]['condition'] = {'all': [pack['rules'][0]['condition'], {'any': [
            {'attribute': 'research_only', 'operator': 'eq', 'value': False},
            {'attribute': 'employee_count', 'operator': 'gt', 'value': 1000}]}]}
        with patch('scripts.jurisdiction_tools.load_pack', return_value=pack):
            actual = rows(screen_jurisdiction(state, p))['federal-count']
        self.assertEqual(actual['preliminary_status'], 'applicable')
        self.assertEqual(len(actual['predicate_traces']), 5)

    def test_actual_cli_reproduces_full_output_and_preserves_request_bytes(self):
        state, p = fixture(); request = {'contract_version': '0.1.0', 'skill': 'screen-jurisdiction-applicability', 'state': state, 'parameters': p}
        with tempfile.TemporaryDirectory(prefix='agentsustain-jurisdiction-cli-') as directory:
            path = Path(directory) / 'request.json'; raw = (json.dumps(request, indent=2) + '\n').encode(); path.write_bytes(raw)
            execution = subprocess.run([sys.executable, '-m', 'scripts.run_jurisdiction', str(path)], cwd=ROOT, capture_output=True)
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(json.loads(execution.stdout), screen_jurisdiction(state, p))
            self.assertEqual(path.read_bytes(), raw)

    def test_inherited_reviews_factor_gaps_and_assumptions_survive_sequential_screens(self):
        state, p = fixture()
        blocked = json.loads((ROOT / 'examples/factor-required-result.json').read_text(encoding='utf-8'))
        blocked['review_requirements'] = [{'id': 'existing-engineering-review', 'state': 'ENGINEERING_REVIEW_REQUIRED',
            'reason': 'Fictional unresolved equipment safety review.', 'scope': 'Fictional equipment',
            'reviewer_role': 'Qualified engineer', 'status': 'open', 'resolution': None}]
        blocked['review_states'].append('ENGINEERING_REVIEW_REQUIRED')
        blocked['assumptions'].append('Fictional factor applicability remains unresolved.')
        state = propose(state, blocked, 'Retain a fictional unresolved carbon and engineering case')['state']
        first = screen_jurisdiction(state, p)
        p['result_id'] = 'next-jurisdiction-screen'
        p['facts'][1]['value'] = {'lower': 99, 'upper': 101}
        second = screen_jurisdiction(first['proposal']['state'], p)
        self.assertEqual(second['proposal']['state']['results'][:-1], first['proposal']['state']['results'])
        for collection in ['evidence', 'review_requirements', 'data_gaps', 'assumptions']:
            for item in first['proposal']['state'][collection]:
                self.assertIn(item, second['proposal']['state'][collection])
        self.assertIn('ENGINEERING_REVIEW_REQUIRED', second['result']['review_states'])
        self.assertEqual(second['result']['metrics'], [])
        self.assertEqual(state['results'][-1]['diagnostics'][0]['code'], 'EMISSION_FACTOR_REQUIRED')

    def test_amended_effective_boundary_and_duplicate_versions(self):
        state, p = fixture(); pack = load_pack(p['pack_pins'][0], True)
        pack['rules'][0]['effective_to'] = '2025-06-30'
        with patch('scripts.jurisdiction_tools.load_pack', return_value=pack):
            actual = rows(screen_jurisdiction(state, p))['federal-count']
        self.assertEqual([s['preliminary_status'] for s in actual['segments']], ['applicable', 'not_applicable'])
        self.assertEqual(actual['segments'][1]['period']['start'], '2025-07-01')
        self.assertEqual(actual['preliminary_status'], 'potentially_applicable')
        p['pack_pins'].append(copy.deepcopy(p['pack_pins'][0]))
        self.assertEqual(screen_jurisdiction(state, p)['result']['status'], 'blocked')

    def test_future_source_chronology_is_not_accepted(self):
        state, p = fixture()
        p['rule_reviews'][0]['checked_as_of'] = '2026-10-06'
        self.assertEqual(screen_jurisdiction(state, p)['result']['status'], 'blocked')
        state, p = fixture(); pack = load_pack(p['pack_pins'][0], True)
        pack['rules'][0]['source']['retrieved'] = '2026-10-06'
        with patch('scripts.jurisdiction_tools.load_pack', return_value=pack):
            self.assertEqual(screen_jurisdiction(state, p)['result']['status'], 'blocked')
