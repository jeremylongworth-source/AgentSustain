"""Dated work-package proposals and sourced constant-daily resource screening."""
import copy
from datetime import date

from .data_tools import number, period, serialize
from .operations_tools import _action_sequence
from .strategy_stakeholders import _date, evidence
from .strategy_tools import _text, _reviewed, _reproduce, _selected


def build(state, parameters, refs, result, gap):
    _, transition = _reproduce(state, parameters['transition_result_id'], 'build-transition-plan', refs)
    review = parameters['implementation_review']
    _reviewed(state, review, refs, ('scope', 'planning_basis', 'calendar_basis', 'resource_basis', 'coverage_limitations'))
    as_of = _date(review.get('as_of_date'))
    if (review['scope'] != transition['transition_review']['scope'] or review.get('period') != state['reporting_period']
            or type(review.get('coverage_complete')) is not bool or as_of < _date(transition['transition_review']['as_of_date'])
            or review['calendar_basis'] != 'inclusive_calendar_days_constant_daily_rates'):
        raise ValueError('Matched current transition context and explicit constant daily calendar basis required.')
    roadmap = parameters['roadmap']
    if (not isinstance(roadmap, dict) or set(roadmap) != {'id', 'name', 'owner', 'horizon', 'review_date', 'phases'}
            or any(not _text(roadmap[f]) for f in ('id', 'name', 'owner'))):
        raise ValueError('Named owned proposed roadmap with horizon, phases and review date required.')
    horizon = period(roadmap['horizon']); outer = transition['plan']['horizon']
    if horizon['start'] < outer['start'] or horizon['end'] > outer['end'] or not as_of < _date(roadmap['review_date']) <= _date(horizon['end']):
        raise ValueError('Roadmap must lie within transition horizon with a future review date.')
    phases = {}; known = {e['id']: e for e in state['evidence']}
    if not isinstance(roadmap['phases'], list) or not roadmap['phases']: raise ValueError('Nonempty proposed phases required.')
    for phase in roadmap['phases']:
        if (not isinstance(phase, dict) or set(phase) != {'id', 'name', 'period', 'owner', 'exit_criterion'}
                or any(not _text(phase[f]) for f in ('id', 'name', 'owner', 'exit_criterion')) or phase['id'] in phases):
            raise ValueError('Distinct phases need explicit owner, dates and observable exit criterion.')
        window = period(phase['period'])
        if window['start'] < horizon['start'] or window['end'] > horizon['end']: raise ValueError('Phase dates must lie within roadmap horizon.')
        phases[phase['id']] = phase
    pathways = {p['pathway']['id']: p for p in transition['pathways']}
    milestones = {m['proposal']['id']: m['proposal'] for m in transition['milestones']}
    packages = {}; rows = []; resource_rows = {}; allocations = {}; covered = {}; known_unmet = []; unresolved = []

    def issue(message, unmet=False):
        (known_unmet if unmet else unresolved).append(message); gap(message)

    def ids(values, valid=None):
        if (not isinstance(values, list) or any(not _text(v) for v in values) or len(set(values)) != len(values)
                or (valid is not None and not set(values) <= set(valid))):
            raise ValueError('Distinct current roadmap reference IDs required.')
        return set(values)

    def sourced(item, label):
        if item['evidence_fit'] not in {'reviewed_supporting', 'unverified'}: raise ValueError('Explicit source fitness required.')
        evidence(item['evidence_ids'], known, refs)
        if not item['evidence_ids'] or item['evidence_fit'] != 'reviewed_supporting': issue(label + ': source fitness remains unverified.')
        return [copy.deepcopy(known[e]) for e in item['evidence_ids']]

    resources = parameters['resources']; selected_capacity_ids = set()
    if not isinstance(resources, list): raise ValueError('Explicit selected resource calendars list required.')
    for resource in resources:
        if (not isinstance(resource, dict) or set(resource) != {'id', 'name', 'unit', 'capacity_metric_ids', 'capacity_review'}
                or any(not _text(resource[f]) for f in ('id', 'name')) or resource['id'] in resource_rows or resource['unit'] not in {'h/day', 'count/day'}):
            raise ValueError('Distinct resource IDs with explicit h/day or count/day units required; no unit/calendar conversion inferred.')
        capacity_ids = ids(resource['capacity_metric_ids'])
        if capacity_ids & selected_capacity_ids:
            raise ValueError('One capacity metric cannot supply multiple renamed resource pools; source allocation must be reconciled upstream.')
        selected_capacity_ids |= capacity_ids; fit = resource['capacity_review']
        _reviewed(state, fit, refs, ('scope', 'capacity_definition', 'calendar_basis'))
        if (fit['scope'] != review['scope'] or fit['capacity_definition'] != 'constant_daily_capacity'
                or fit['calendar_basis'] != review['calendar_basis'] or not isinstance(fit.get('metric_contexts'), dict)
                or set(fit['metric_contexts']) != set(resource['capacity_metric_ids'])):
            raise ValueError('Resource capacity requires matched scope/calendar and exact per-metric source review.')
        capacities = []
        for metric_id in resource['capacity_metric_ids']:
            metric = _selected(state, metric_id, refs); context = fit['metric_contexts'][metric_id]
            if (not isinstance(context, dict) or context.get('confirmed') is not True or context.get('evidence_ids') != metric['evidence_ids']
                    or context.get('scope') != review['scope'] or not _text(context.get('rationale'))
                    or metric['boundary_id'] != review['boundary_id'] or metric['unit'] != resource['unit'] or number(metric['value']) < 0):
                raise ValueError('Nonnegative exact-unit capacity with substantive scoped source-fit review required.')
            window = period(metric['period'])
            if window['start'] < horizon['start'] or window['end'] > horizon['end']: raise ValueError('Capacity windows must lie within roadmap horizon.')
            capacities.append(copy.deepcopy(metric))
        capacities.sort(key=lambda m:m['period']['start'])
        if any(b['period']['start'] <= a['period']['end'] for a,b in zip(capacities, capacities[1:])):
            raise ValueError('One resource calendar cannot contain overlapping capacity windows or double-counted availability.')
        if not capacities: issue(resource['id'] + ': resource capacity is unknown, not zero or unlimited.')
        resource_rows[resource['id']] = {'resource': copy.deepcopy(resource), 'capacity_metrics': capacities, 'reservation_verified': False}
        allocations[resource['id']] = []
    work = parameters['work_packages']
    if not isinstance(work, list): raise ValueError('Explicit work-package proposals required.')
    fields = {'id', 'pathway_id', 'initiative_ids', 'milestone_ids', 'phase_id', 'name', 'deliverable', 'acceptance_criterion', 'owner',
        'period', 'depends_on', 'resource_demands', 'preconditions', 'evidence_ids', 'evidence_fit'}
    for task in work:
        if (not isinstance(task, dict) or set(task) != fields or task['id'] in packages or task['pathway_id'] not in pathways
                or task['phase_id'] not in phases or any(not _text(task[f]) for f in ('id', 'name', 'deliverable', 'acceptance_criterion', 'owner'))):
            raise ValueError('Distinct owned work packages with pathway, phase, deliverable and acceptance criterion required.')
        packages[task['id']] = task; path = pathways[task['pathway_id']]['pathway']
        selected_initiatives = ids(task['initiative_ids'], path['initiative_ids']); selected_milestones = ids(task['milestone_ids'], milestones)
        if not selected_initiatives or not selected_milestones or any(milestones[m]['pathway_id'] != path['id'] or not set(milestones[m]['initiative_ids']) & selected_initiatives for m in selected_milestones):
            raise ValueError('Work package must support selected milestones and initiatives from its own pathway.')
        window = period(task['period']); phase = phases[task['phase_id']]['period']
        if window['start'] < phase['start'] or window['end'] > phase['end']: raise ValueError('Work-package dates must lie within its phase.')
        context = sourced(task, task['id'])
        if _date(window['end']) < as_of: issue(task['id'] + ': planned finish has passed; task is overdue and unverified, not complete.')
        elif _date(window['start']) < as_of: issue(task['id'] + ': planned start has passed; actual commencement and progress remain unverified.')
        for milestone_id in selected_milestones:
            covered.setdefault(milestone_id, []).append(task['id'])
            if window['end'] > milestones[milestone_id]['due_date']: issue(task['id'] + ': proposed finish follows source milestone ' + milestone_id + '; timing reconciliation required.', True)
        demands = task['resource_demands']; demand_rows = []
        if demands is None: issue(task['id'] + ': resource demands are unassessed; no resource-free task inferred.')
        else:
            if not isinstance(demands, list): raise ValueError('Resource demands must be a sourced list or null when unassessed.')
            seen = set()
            if not demands: issue(task['id'] + ': empty resource demand list requires resource assessment; no zero demand inferred.')
            for demand in demands:
                if (not isinstance(demand, dict) or set(demand) != {'resource_id', 'demand_metric_id', 'evidence_fit', 'rationale'}
                        or demand['resource_id'] not in resource_rows or demand['resource_id'] in seen
                        or demand['evidence_fit'] not in {'reviewed_supporting', 'unverified'} or not _text(demand['rationale'])):
                    raise ValueError('Distinct selected resource demands require a metric and substantive source fitness rationale.')
                rid = demand['resource_id']; seen.add(rid); metric = _selected(state, demand['demand_metric_id'], refs)
                if metric['unit'] != resource_rows[rid]['resource']['unit'] or metric['period'] != window or metric['boundary_id'] != review['boundary_id'] or number(metric['value']) < 0:
                    raise ValueError('Demand must be nonnegative with exact resource daily unit, task period and boundary.')
                if demand['evidence_fit'] != 'reviewed_supporting': issue(task['id'] + ': resource demand source fitness remains unverified.')
                allocations[rid].append({'task_id': task['id'], 'metric': copy.deepcopy(metric)})
                demand_rows.append({'request': copy.deepcopy(demand), 'metric': copy.deepcopy(metric)})
        conditions = task['preconditions']; condition_rows = []
        if conditions is None: issue(task['id'] + ': technical, funding, staffing, service, evidence and approval prerequisites remain unassessed.')
        else:
            if not isinstance(conditions, list): raise ValueError('Preconditions must be a reviewed list or null.')
            seen = set()
            for condition in conditions:
                if (not isinstance(condition, dict) or set(condition) != {'id', 'domain', 'description', 'owner', 'status', 'evidence_ids', 'evidence_fit'}
                        or any(not _text(condition[f]) for f in ('id', 'description', 'owner')) or condition['id'] in seen
                        or condition['domain'] not in {'technical', 'financial', 'organizational', 'service', 'evidence', 'approval'}
                        or condition['status'] not in {'sourced_assumption', 'known_unmet', 'unresolved'}):
                    raise ValueError('Owned distinct sourced preconditions with explicit domain/status required.')
                seen.add(condition['id']); condition_context = sourced(condition, task['id'] + '/' + condition['id'])
                if condition['status'] != 'unresolved' and (not condition['evidence_ids'] or condition['evidence_fit'] != 'reviewed_supporting'):
                    raise ValueError('Known unmet or sourced preconditions require reviewed supporting evidence.')
                if condition['status'] != 'sourced_assumption': issue(task['id'] + '/' + condition['id'] + ': prerequisite remains ' + condition['status'] + '.', condition['status'] == 'known_unmet')
                condition_rows.append({'condition': copy.deepcopy(condition), 'source_context': condition_context, 'fulfilled_verified': False})
        rows.append({'proposal': copy.deepcopy(task), 'source_context': context, 'resource_demands': demand_rows, 'preconditions': condition_rows,
            'status': 'overdue_unverified' if _date(window['end']) < as_of else 'proposed_unsent', 'work_started': False, 'completion_verified': False,
            'owner_acceptance_verified': False, 'implementation_authorized': False})
    actions = [{'id':t['id'], 'target_date':t['period']['end'], 'depends_on':t['depends_on']} for t in work]
    sequence = _action_sequence(actions)
    for task in work:
        for dependency in task['depends_on']:
            if packages[dependency]['period']['end'] >= task['period']['start']:
                raise ValueError('Inclusive finish-to-start work dependencies require prerequisite finish before dependent start.')
    def ancestors(ident):
        found = set(); pending = list(packages[ident]['depends_on'])
        while pending:
            current = pending.pop()
            if current not in found: found.add(current); pending.extend(packages[current]['depends_on'])
        return found
    for milestone_id, linked in covered.items():
        for source_dependency in milestones[milestone_id]['depends_on']:
            required = covered.get(source_dependency, [])
            if not required: issue(milestone_id + ': source prerequisite milestone ' + source_dependency + ' has no work-package response.')
            elif any(not set(required) <= ancestors(task_id) for task_id in linked):
                issue(milestone_id + ': source prerequisite work is not retained in the proposed task dependency graph.', True)
    for omitted in set(milestones) - set(covered): issue(omitted + ': transition milestone omitted from selected roadmap.')
    for phase_id in set(phases) - {t['phase_id'] for t in work}: issue(phase_id + ': phase has no work packages; exit remains unverified.')
    resource_screens = []
    for rid, entries in allocations.items():
        capacities = resource_rows[rid]['capacity_metrics']; endpoints = set()
        for metric in [e['metric'] for e in entries] + capacities:
            endpoints.update((_date(metric['period']['start']).toordinal(), _date(metric['period']['end']).toordinal()+1))
        points = sorted(endpoints)
        for start, stop in zip(points, points[1:]):
            active = [e for e in entries if _date(e['metric']['period']['start']).toordinal() <= start <= _date(e['metric']['period']['end']).toordinal()]
            if not active: continue
            capacity = next((m for m in capacities if _date(m['period']['start']).toordinal() <= start <= _date(m['period']['end']).toordinal()), None)
            demand = sum((number(e['metric']['value']) for e in active), number(0)); available = None if capacity is None else number(capacity['value'])
            status = 'unresolved_capacity' if available is None else 'overallocated' if demand > available else 'within_supplied_capacity'
            window = {'start':date.fromordinal(start).isoformat(), 'end':date.fromordinal(stop-1).isoformat()}
            if status != 'within_supplied_capacity': issue(rid + ': ' + status + ' for ' + window['start'] + ' through ' + window['end'] + '.', status == 'overallocated')
            resource_screens.append({'resource_id':rid, 'period':window, 'task_ids':sorted(e['task_id'] for e in active), 'unit':resource_rows[rid]['resource']['unit'],
                'daily_demand':serialize(demand), 'daily_capacity':None if available is None else serialize(available),
                'daily_capacity_minus_demand':None if available is None else serialize(available-demand), 'status':status,
                'demand_metric_ids':[e['metric']['id'] for e in active], 'capacity_metric_id':None if capacity is None else capacity['id'], 'reservation_verified':False})
    for path in transition['pathways']:
        for checkpoint in path['checkpoints']:
            model = checkpoint['modeled_case']
            if model is None: issue(path['pathway']['id'] + ': upstream checkpoint delivery/investment remains unassessed.')
            elif model['delivery_screen'] != 'reviewed_assumptions_only': issue(path['pathway']['id'] + ': upstream modeled delivery remains ' + model['delivery_screen'] + '.', model['delivery_screen'] == 'known_conditions_not_met')
    for condition in transition['timing_conditions']: issue(condition['milestone_id'] + ': upstream transition timing remains ' + condition['status'] + '.', condition['status'] == 'known_unmet_timing_assumption')
    if not review['coverage_complete']: issue('Roadmap coverage is incomplete; no organization-wide implementation readiness.')
    result['review_requirements'].append({'id':result['id']+'-implementation-review', 'state':'PROFESSIONAL_REVIEW_REQUIRED',
        'reason':'Review task/source fitness, calendar capacity, source prerequisite mapping, funding, owner acceptance and acceptance evidence before implementation.',
        'scope':review['scope'], 'reviewer_role':'Accountable implementation owner and technical, financial and workforce specialists', 'status':'open', 'resolution':None})
    return {'transition_result_id':parameters['transition_result_id'], 'transition_snapshot':copy.deepcopy(transition), 'roadmap':copy.deepcopy(roadmap),
        'implementation_review':copy.deepcopy(review), 'work_packages':rows, 'resources':resource_rows, 'resource_screens':resource_screens,
        'proposed_sequence':sequence, 'known_unmet_conditions':known_unmet, 'unresolved_conditions':unresolved,
        'delivery_screen':'known_conditions_not_met' if known_unmet else 'unresolved_conditions' if unresolved or state['data_gaps'] else 'reviewed_assumptions_only',
        'resource_optimized':False, 'roadmap_adopted':False, 'funding_authorized':False, 'resources_reserved':False,
        'implementation_authorized':False, 'performance_verified':False, 'public_claim_authorized':False}
