"""Source-pinned conditional task candidates, never filings or legal decisions."""
import copy
from datetime import date
import json

from .climate_tools import _date, _fields, _sources, _text
from .contract_validation import validate_state
from .jurisdiction_subjects import screen_subject_jurisdiction
from .jurisdiction_tools import FIT, read_pinned_pack
from .state_proposal import propose


CONTRACT = 'jurisdiction-tasks-0.1.0'


def _retention_date(anchor, years):
    start = _date(anchor)
    try:
        return date(start.year + years, start.month, start.day).isoformat()
    except ValueError:
        return None  # No inferred February-end substitution or overflowing date.


def _diagnostic(result, code):
    values = [d['message'] for d in result['diagnostics'] if d['code'] == code]
    if len(values) != 1:
        raise ValueError('Exactly one complete screening diagnostic required.')
    return json.loads(values[0])


def load_task_catalog(pin, fixture_mode):
    catalog = read_pinned_pack(pin)
    _fields(catalog, {'id', 'version', 'execution_contract', 'synthetic', 'screen_pack_pin',
                     'rule_ids', 'tasks', 'scope', 'limitations'},
            ('id', 'version', 'execution_contract', 'scope', 'limitations'))
    if catalog['execution_contract'] != CONTRACT or not isinstance(catalog['synthetic'], bool):
        raise ValueError('Explicit task execution contract and synthetic flag required.')
    if catalog['synthetic'] and not fixture_mode:
        raise ValueError('Fictional task catalogs require explicit fixture mode.')
    _fields(catalog['screen_pack_pin'], {'path', 'sha256'}, ('path', 'sha256'))
    ids = catalog['rule_ids']
    if not isinstance(ids, list) or not ids or any(not _text(i) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Distinct complete screening rule roster required.')
    if not isinstance(catalog['tasks'], list) or not catalog['tasks']:
        raise ValueError('Nonempty task catalog required.')
    seen = set()
    for task in catalog['tasks']:
        _fields(task, {'id', 'kind', 'trigger', 'deadlines', 'retention_years', 'source', 'uncertainty'},
                ('id', 'kind', 'trigger', 'uncertainty'))
        expected = {'report': 'reporting_condition', 'notify': 'prior_report_no_current_condition',
                    'certify': 'reporting_condition', 'retain': 'current_submission'}
        if task['id'] in seen or expected.get(task['kind']) != task['trigger']:
            raise ValueError('Distinct supported task kinds and matching triggers required.')
        seen.add(task['id'])
        deadlines = task['deadlines']
        if not isinstance(deadlines, dict) or not deadlines:
            raise ValueError('Explicit year-specific deadline roster required, including unknown dates.')
        for year, due in deadlines.items():
            if not isinstance(year, str) or not year.isdigit() or str(int(year)) != year or not 1 <= int(year) <= 9999:
                raise ValueError('Canonical reporting years required.')
            if due is not None:
                _date(due)
        years = task['retention_years']
        if task['kind'] == 'retain':
            if type(years) is not int or not 1 <= years <= 100:
                raise ValueError('Explicit bounded retention years required.')
            if any(d is not None for d in deadlines.values()):
                raise ValueError('Retention dates derive only from supported actual submission, not a deadline.')
        elif years is not None:
            raise ValueError('Retention arithmetic belongs only to retention tasks.')
        source = task['source']
        _fields(source, {'authority', 'locator', 'clause', 'version', 'retrieved'},
                ('authority', 'locator', 'clause', 'retrieved'))
        if source['version'] is not None and not _text(source['version']):
            raise ValueError('Substantive or explicitly unknown source version required.')
        if not catalog['synthetic'] and not source['locator'].startswith('https://'):
            raise ValueError('Real task sources require primary HTTPS locators.')
        _date(source['retrieved'])
    return catalog


def prepare_jurisdiction_tasks(state, parameters):
    validate_state(state)
    _fields(parameters, {'screen_result_id', 'task_catalog_pin', 'history', 'task_reviews',
                         'planning_review', 'fixture_mode', 'result_id'}, ('screen_result_id', 'result_id'))
    if type(parameters['fixture_mode']) is not bool or any(r['id'] == parameters['result_id'] for r in state['results']):
        raise ValueError('Explicit fixture mode and unused result ID required.')
    result = {'id': parameters['result_id'], 'skill': 'prepare-jurisdiction-task-register',
              'contract_version': '0.1.0', 'status': 'partial', 'review_states': ['ADVISORY'],
              'review_requirements': copy.deepcopy(state['review_requirements']), 'metrics': [], 'evidence_ids': [],
              'assumptions': list(state['assumptions']), 'data_gaps': copy.deepcopy(state['data_gaps']),
              'diagnostics': [], 'next_actions': []}
    refs = set()
    def gap(message):
        result['data_gaps'].append({'id': result['id'] + '-gap-' + str(len(result['data_gaps'])),
            'field': 'jurisdiction_tasks', 'reason': message, 'impact': 'Task applicability or timing remains conditional.',
            'remedy': 'Obtain qualified source/legal and accountable-owner review before any action.'})
    try:
        review = parameters['planning_review']
        _fields(review, {'boundary_id', 'period', 'as_of_date', 'scope', 'evidence_ids', 'evidence_fit', 'rationale', 'reviewer_role'},
                ('scope', 'rationale', 'reviewer_role'))
        primary = _sources(state, review['evidence_ids'], refs)
        as_of = _date(review['as_of_date'])
        if review['boundary_id'] != state['organizational_boundary']['id'] or review['period'] != state['reporting_period'] or review['evidence_fit'] not in FIT:
            raise ValueError('Matched boundary/period and explicit planning fitness required.')
        planning_fit = bool(primary) and review['evidence_fit'] == 'reviewed_supporting' and all(
            e['source']['version'] is not None and _date(e['source']['accessed']) <= as_of for e in primary)
        owner = next((r for r in state['results'] if r['id'] == parameters['screen_result_id']), None)
        if owner is None or owner['skill'] != 'screen-subject-jurisdiction-applicability' or owner['status'] != 'partial':
            raise ValueError('Current complete subject-screen result required.')
        inputs = _diagnostic(owner, 'JURISDICTION_SUBJECT_INPUTS')
        if inputs['fixture_mode'] and not parameters['fixture_mode']:
            raise ValueError('Fictional upstream screening cannot enter a real task register.')
        reproduction = copy.deepcopy(inputs)
        reproduction['result_id'] = parameters['result_id'] + '-screen-reproduction'
        while any(r['id'] == reproduction['result_id'] for r in state['results']):
            reproduction['result_id'] += '-next'
        checked = screen_subject_jurisdiction(state, reproduction)['result']
        screen = _diagnostic(owner, 'JURISDICTION_SUBJECT_SCREEN')
        if checked['status'] != owner['status'] or checked['metrics'] != owner['metrics'] or set(checked['evidence_ids']) != set(owner['evidence_ids']) or _diagnostic(checked, 'JURISDICTION_SUBJECT_SCREEN') != screen:
            raise ValueError('Complete screening report, metrics and evidence lineage must reproduce.')
        if screen['screening_review']['as_of_date'] != review['as_of_date']:
            raise ValueError('Refresh screening for the task review date; no stale currency inference.')
        refs.update(owner['evidence_ids'])
        catalog = load_task_catalog(parameters['task_catalog_pin'], parameters['fixture_mode'])
        pin = catalog['screen_pack_pin']
        if pin not in screen['pins']:
            raise ValueError('Task catalog must select the exact screened rule pack bytes.')
        pack = screen['packs'][screen['pins'].index(pin)]
        if set(catalog['rule_ids']) != {r['id'] for r in pack['rules']}:
            raise ValueError('All selected pack branches required; a negative branch alone cannot trigger notification.')
        covered_years = set.intersection(*(set(r['reporting_years']) for r in pack['rules']))
        if any(not {int(y) for y in t['deadlines']} <= covered_years for t in catalog['tasks']):
            raise ValueError('Task years must be covered by every selected screening branch in this edition.')
        subjects = screen['subjects']; year = int(review['period']['start'][:4])
        history = {}
        if not isinstance(parameters['history'], list) or not isinstance(parameters['task_reviews'], list):
            raise ValueError('Explicit history and task review lists required.')
        for h in parameters['history']:
            _fields(h, {'subject_id', 'operator_id', 'reporting_year', 'submitted', 'submitted_date', 'observed_date',
                        'evidence_ids', 'evidence_fit', 'rationale'}, ('subject_id', 'operator_id', 'rationale'))
            key = (h['subject_id'], h['reporting_year'])
            if h['subject_id'] not in subjects or type(h['reporting_year']) is not int or h['reporting_year'] not in {year-1, year} or key in history or h['evidence_fit'] not in FIT or h['submitted'] is not None and type(h['submitted']) is not bool:
                raise ValueError('Distinct selected subject/current-or-prior-year history required.')
            observed = _date(h['observed_date']) if h['observed_date'] is not None else None
            submitted = _date(h['submitted_date']) if h['submitted_date'] is not None else None
            if observed and observed > as_of or submitted and (h['submitted'] is not True or not observed or submitted > observed or submitted.year < h['reporting_year']):
                raise ValueError('Supported nonfuture history chronology required; no invented submissions.')
            sources = _sources(state, h['evidence_ids'], refs)
            supported = (planning_fit and bool(sources) and h['evidence_fit'] == 'reviewed_supporting' and observed is not None
                and h['operator_id'] == subjects[h['subject_id']]['record']['candidate_operator_id']
                and all(e['boundary_id'] == review['boundary_id'] and e['source']['version'] is not None
                    and _date(e['source']['accessed']) <= as_of and _date(e['period']['start']) <= observed <= _date(e['period']['end'])
                    and (submitted is None or _date(e['period']['start']) <= submitted <= _date(e['period']['end'])) for e in sources))
            history[key] = {'record': copy.deepcopy(h), 'sources': sources, 'supported': supported}
        task_reviews = {}
        for item in parameters['task_reviews']:
            _fields(item, {'task_id', 'checked_as_of', 'evidence_ids', 'evidence_fit', 'rationale'}, ('task_id', 'rationale'))
            if item['task_id'] in task_reviews or item['task_id'] not in {t['id'] for t in catalog['tasks']} or item['evidence_fit'] not in FIT or _date(item['checked_as_of']) > as_of:
                raise ValueError('Distinct selected task reviews with nonfuture currency required.')
            task_reviews[item['task_id']] = (item, _sources(state, item['evidence_ids'], refs))
        rows = []
        for sid in subjects:
            selected = [r for r in screen['rows'] if r['subject_id'] == sid and r['pack_id'] == pack['id']]
            conditions = [r['preliminary_status'] for r in selected]
            current_condition = True if 'potentially_applicable' in conditions else False if all(x == 'not_applicable' for x in conditions) else None
            for task in catalog['tasks']:
                source = task['source']; item, sources = task_reviews.get(task['id'], (None, []))
                source_fit = (planning_fit and subjects[sid]['supported'] and item is not None and item['evidence_fit'] == 'reviewed_supporting'
                    and item['checked_as_of'] == review['as_of_date'] and source['version'] is not None
                    and _date(source['retrieved']) <= as_of
                    and all(_date(e['source']['accessed']) <= as_of for e in sources)
                    and any(e['source']['locator'] == source['locator'] and e['source']['version'] == source['version'] for e in sources))
                selected_history = history.get((sid, year-1 if task['kind'] == 'notify' else year))
                prior = selected_history['record']['submitted'] if selected_history and selected_history['supported'] else None
                trigger = current_condition
                if task['kind'] == 'notify':
                    trigger = False if prior is False or current_condition is True else True if prior is True and current_condition is False else None
                elif task['kind'] == 'retain':
                    trigger = prior
                covered = str(year) in task['deadlines']
                status = 'potential_task' if source_fit and covered and trigger is True else 'not_triggered' if source_fit and covered and trigger is False else 'undetermined'
                due = task['deadlines'].get(str(year)); anchor = None
                if task['kind'] == 'retain' and selected_history and selected_history['supported'] and prior is True:
                    anchor = selected_history['record']['submitted_date']
                    if anchor is not None:
                        due = _retention_date(anchor, task['retention_years'])
                        if due is None:
                            gap(sid + '/' + task['id'] + ': retention anniversary requires explicit calendar interpretation.')
                if status != 'not_triggered':
                    gap(sid + '/' + task['id'] + ': task, source interpretation and timing require legal/owner review.')
                if status == 'potential_task' and due is None:
                    gap(sid + '/' + task['id'] + ': candidate date is unknown; no deadline or retention anchor inferred.')
                rows.append({'subject_id': sid, 'operator_id': subjects[sid]['record']['candidate_operator_id'],
                    'reporting_year': year, 'task': copy.deepcopy(task), 'screen_rule_statuses': conditions,
                    'current_reporting_condition': current_condition, 'history': copy.deepcopy(selected_history),
                    'source_review': copy.deepcopy(item), 'source_snapshots': sources, 'source_fit': source_fit,
                    'trigger': trigger, 'candidate_status': status, 'candidate_date': due, 'retention_anchor': anchor,
                    'candidate_date_precedes_assessment': due is not None and _date(due) < as_of,
                    'legal_obligation_determined': False, 'completion_verified': False, 'filing_authorized': False})
        report = {'execution_contract': CONTRACT, 'catalog': catalog, 'catalog_pin': copy.deepcopy(parameters['task_catalog_pin']),
                  'screen_result_id': owner['id'], 'screen_snapshot': screen, 'history': list(history.values()),
                  'planning_review': copy.deepcopy(review), 'rows': rows, 'legal_obligation_determined': False,
                  'regulatory_quantity_verified': False, 'whole_organization_coverage_verified': False,
                  'owner_authority_adopted': False, 'external_action_authorized': False}
        if catalog['synthetic']:
            result['assumptions'] = list(dict.fromkeys(result['assumptions'] + ['Fictional conditional jurisdiction tasks only; no actual filing or law implemented.']))
        result['review_requirements'].append({'id': result['id'] + '-legal-review', 'state': 'LEGAL_REVIEW_REQUIRED',
            'reason': 'Review complete trigger branches, subject/operator history, source version, dates, retention anchor and task applicability.',
            'scope': review['scope'], 'reviewer_role': review['reviewer_role'], 'status': 'open', 'resolution': None})
        result['diagnostics'].append({'code': 'JURISDICTION_TASK_REGISTER', 'message': json.dumps(report, sort_keys=True)})
    except (ValueError, TypeError, KeyError, OSError) as error:
        result['status'] = 'blocked'; gap(str(error))
        result['diagnostics'].append({'code': 'JURISDICTION_TASK_DATA_REQUIRED', 'message': str(error)})
    result['evidence_ids'] = sorted(refs)
    result['diagnostics'].append({'code': 'JURISDICTION_TASK_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    result['review_states'] = list(dict.fromkeys(result['review_states'] + [r['state'] for r in result['review_requirements'] if r['status'] == 'open'] + ['EVIDENCE_INCOMPLETE']))
    result['next_actions'] = list(dict.fromkeys(g['remedy'] for g in result['data_gaps']))
    return {'result': result, 'proposal': propose(state, result, 'Record separate conditional task candidates; no filings, certification or review resolution')}
