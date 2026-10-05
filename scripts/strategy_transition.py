"""Sourced transition pathways and dated decision proposals, without adoption."""
import copy

from .data_tools import period
from .operations_tools import _action_sequence
from .strategy_stakeholders import _date, evidence
from .strategy_tools import _text, _reviewed, _reproduce


def build(state, parameters, refs, result, gap):
    _, strategy = _reproduce(state, parameters['strategy_result_id'], 'build-sustainability-strategy', refs)
    review = parameters['transition_review']
    _reviewed(state, review, refs, ('scope', 'planning_basis', 'uncertainty_basis', 'coverage_limitations', 'trade_off_review'))
    as_of = _date(review.get('as_of_date'))
    if (review['scope'] != strategy['strategy_review']['scope'] or review.get('period') != state['reporting_period']
            or type(review.get('coverage_complete')) is not bool or as_of < _date(strategy['strategy_review']['as_of_date'])):
        raise ValueError('Transition review needs matched strategy scope/period, explicit coverage and nonhistorical review date.')
    plan = parameters['plan']
    if (not isinstance(plan, dict) or set(plan) != {'id', 'name', 'purpose', 'horizon', 'owner', 'review_date'}
            or any(not _text(plan[f]) for f in ('id', 'name', 'purpose', 'owner'))):
        raise ValueError('Named proposed transition with purpose, owner, horizon and review date required.')
    horizon = period(plan['horizon']); revisit = _date(plan['review_date'])
    outer = strategy['strategy']['horizon']
    if horizon['start'] < outer['start'] or horizon['end'] > outer['end'] or not as_of < revisit <= _date(horizon['end']):
        raise ValueError('Live transition horizon within strategy horizon and future review date required.')
    pillars = {p['id']: p for p in strategy['pillars']}
    objectives = {o['id']: o for o in strategy['objectives']}
    initiatives = {i['proposal']['id']: i for i in strategy['initiatives']}
    known = {e['id']: e for e in state['evidence']}
    snapshots = {}; uses = {}; rows = []; indexed = {}; used_objectives = set(); used_initiatives = set()

    def ids(values, valid=None):
        if (not isinstance(values, list) or any(not _text(v) for v in values) or len(set(values)) != len(values)
                or (valid is not None and not set(values) <= set(valid))):
            raise ValueError('Distinct current selected transition reference IDs required.')
        return set(values)

    def sourced(item, label):
        if item['evidence_fit'] not in {'reviewed_supporting', 'unverified'}:
            raise ValueError('Explicit supporting/unverified source fitness required.')
        evidence(item['evidence_ids'], known, refs)
        if not item['evidence_ids'] or item['evidence_fit'] != 'reviewed_supporting': gap(label + ': source fitness remains unverified.')
        return [copy.deepcopy(known[e]) for e in item['evidence_ids']]

    def source(ident, skill, scope):
        owner, report = _reproduce(state, ident, skill, refs)
        context = report['target_review' if skill == 'develop-target' else 'feasibility_review']
        if context['scope'] != scope: raise ValueError('Checkpoint sources must match the selected pillar scope.')
        if skill == 'evaluate-target-feasibility' and _date(context['review_date']) > as_of:
            raise ValueError('Transition review cannot predate selected feasibility review.')
        snapshots[ident] = {'skill': skill, 'result_id': ident, 'report': copy.deepcopy(report), 'metrics': copy.deepcopy(owner['metrics'])}
        return owner, report

    pathways = parameters['pathways']
    if not isinstance(pathways, list) or not pathways: raise ValueError('Nonempty explicit transition pathways required.')
    fields = {'id', 'pillar_id', 'objective_ids', 'initiative_ids', 'target_result_id', 'checkpoints', 'mechanism',
        'evidence_ids', 'evidence_fit', 'interaction_review', 'external_dependency_review', 'external_dependencies'}
    for pathway in pathways:
        if (not isinstance(pathway, dict) or set(pathway) != fields or pathway['pillar_id'] not in pillars
                or any(not _text(pathway[f]) for f in ('id', 'mechanism', 'interaction_review', 'external_dependency_review'))
                or pathway['id'] in indexed):
            raise ValueError('Distinct scoped transition pathways with mechanism, interactions and external-dependency review required.')
        pid = pathway['pillar_id']; scope = pillars[pid]['scope']; ident = pathway['id']; indexed[ident] = pathway
        selected_objectives = ids(pathway['objective_ids'], objectives)
        selected_initiatives = ids(pathway['initiative_ids'], initiatives)
        if not selected_objectives or any(objectives[o]['pillar_id'] != pid for o in selected_objectives):
            raise ValueError('Each pathway needs objectives from its selected strategy pillar.')
        if any(initiatives[i]['proposal']['pillar_id'] != pid or not set(initiatives[i]['proposal']['objective_ids']) & selected_objectives for i in selected_initiatives):
            raise ValueError('Pathway initiatives must address selected objectives in the same pillar.')
        used_objectives |= selected_objectives; used_initiatives |= selected_initiatives
        if not selected_initiatives: gap(ident + ': no initiative response linked; delivery remains open.')
        context = sourced(pathway, ident + ' mechanism')
        final_id = pathway['target_result_id']; final = None
        objective_targets = {t for o in selected_objectives for t in objectives[o]['target_result_ids']}
        if final_id is not None:
            if final_id not in objective_targets: raise ValueError('Final pathway target must belong to a selected strategy objective.')
            _, final = source(final_id, 'develop-target', scope)
        else: gap(ident + ': qualitative pathway has no quantified target; no numeric trajectory inferred.')
        checkpoints = pathway['checkpoints']; checkpoint_rows = []; previous_end = None; previous_value = None
        if not isinstance(checkpoints, list) or (final_id is None and checkpoints) or (final_id is not None and not checkpoints):
            raise ValueError('Quantitative pathways need sourced checkpoints; qualitative pathways use an empty checkpoint list.')
        checkpoint_ids = set()
        for checkpoint in checkpoints:
            if not isinstance(checkpoint, dict) or set(checkpoint) != {'target_result_id', 'feasibility_result_id', 'scenario_id'}:
                raise ValueError('Checkpoint requires exact target, feasibility and modeled scenario references.')
            target_id = checkpoint['target_result_id']
            if target_id in checkpoint_ids: raise ValueError('Checkpoint target must occur once per pathway.')
            checkpoint_ids.add(target_id)
            target_owner, target = source(target_id, 'develop-target', scope)
            definition = target['definition']['definition']; final_definition = final['definition']['definition']
            if (definition['id'] != final_definition['id'] or definition['baseline_result_id'] != final_definition['baseline_result_id']
                    or target['baseline_unit'] != final['baseline_unit'] or target['target']['kind'] != final['target']['kind']
                    or target['target_review']['recalculation_policy'] != final['target_review']['recalculation_policy']
                    or target['definition'] != final['definition']):
                raise ValueError('Interim targets must preserve the final target KPI, baseline, physical service and accounting definition.')
            window = period(target['target']['period'])
            if window['start'] < horizon['start'] or window['end'] > horizon['end'] or (previous_end and window['start'] <= previous_end):
                raise ValueError('Checkpoint periods must be ordered, disjoint and within the transition horizon.')
            previous_end = window['end']
            endpoint = next(m for m in target_owner['metrics'] if m['id'] == target['endpoint_metric_id'])
            if previous_value is not None and endpoint['value'] > previous_value:
                gap(ident + ': proposed checkpoint endpoint increases; retain the changed ambition rather than infer a monotonic trajectory.')
            previous_value = endpoint['value']
            if _date(window['end']) < as_of: gap(target_id + ': checkpoint period elapsed; progress remains unverified.')
            feasibility_id = checkpoint['feasibility_result_id']; modeled_case = None
            if feasibility_id is None:
                if checkpoint['scenario_id'] is not None: raise ValueError('Scenario ID requires a reproduced feasibility source.')
                gap(target_id + ': no checkpoint feasibility source; delivery and investment remain unassessed.')
            else:
                _, feasibility = source(feasibility_id, 'evaluate-target-feasibility', scope)
                if feasibility['target_result_id'] != target_id: raise ValueError('Checkpoint feasibility must address its own target.')
                modeled_case = next((s for s in feasibility['scenarios'] if s['scenario']['id'] == checkpoint['scenario_id']), None)
                if modeled_case is None: raise ValueError('Explicit known scenario required for analytical pathway comparison, not investment selection.')
                if modeled_case['delivery_screen'] != 'reviewed_assumptions_only':
                    gap(target_id + ': selected modeled case retains ' + modeled_case['delivery_screen'] + '; numerical objective coverage does not resolve delivery.')
            for dependency in (target_id, feasibility_id):
                if dependency is not None: uses.setdefault(dependency, []).append(ident)
            checkpoint_rows.append({'references': copy.deepcopy(checkpoint), 'target_snapshot': copy.deepcopy(target),
                'endpoint_metric': copy.deepcopy(endpoint), 'modeled_case': copy.deepcopy(modeled_case), 'performance_verified': False,
                'scenario_selected_for_implementation': False})
        if final_id is not None and checkpoints[-1]['target_result_id'] != final_id:
            raise ValueError('Last checkpoint must be the selected final objective target.')
        external = pathway['external_dependencies']; external_rows = []
        if external is None: gap(ident + ': external technology, policy, market, workforce and value-chain dependencies remain unassessed.')
        else:
            if not isinstance(external, list): raise ValueError('External dependencies require a reviewed list or null when unassessed.')
            external_ids = set()
            for item in external:
                if (not isinstance(item, dict) or set(item) != {'id', 'domain', 'description', 'owner', 'status', 'evidence_ids', 'evidence_fit'}
                        or any(not _text(item[f]) for f in ('id', 'description', 'owner')) or item['id'] in external_ids
                        or item['domain'] not in {'technology', 'policy', 'market', 'value_chain', 'workforce'}
                        or item['status'] not in {'sourced_assumption', 'known_unmet', 'unresolved'}):
                    raise ValueError('Owned distinct external conditions with domain, status and sources required.')
                external_ids.add(item['id']); external_context = sourced(item, item['id'])
                if item['status'] != 'unresolved' and (not item['evidence_ids'] or item['evidence_fit'] != 'reviewed_supporting'):
                    raise ValueError('Known unmet or sourced external assumptions require reviewed supporting evidence.')
                if item['status'] != 'sourced_assumption': gap(item['id'] + ': external condition remains ' + item['status'] + '.')
                external_rows.append({'condition': copy.deepcopy(item), 'source_context': external_context, 'fulfilment_verified': False})
        rows.append({'pathway': copy.deepcopy(pathway), 'source_context': context, 'checkpoints': checkpoint_rows,
            'external_dependencies': external_rows, 'trajectory_interpolated': False, 'delivery_feasible': False})
    for ident in set(objectives) - used_objectives: gap(ident + ': strategy objective omitted from selected transition pathways.')
    for ident in set(initiatives) - used_initiatives: gap(ident + ': strategy initiative omitted from selected transition pathways.')
    milestones = parameters['milestones']; milestone_rows = []; actions = []; covered = set(); milestone_initiatives = set(); monitoring_paths = set(); timing_conditions = []
    if not isinstance(milestones, list): raise ValueError('Explicit dated milestone proposals required.')
    for milestone in milestones:
        if (not isinstance(milestone, dict) or set(milestone) != {'id', 'pathway_id', 'initiative_ids', 'kind', 'description', 'acceptance_criterion',
                'owner', 'due_date', 'depends_on', 'evidence_ids', 'evidence_fit'} or milestone['pathway_id'] not in indexed
                or any(not _text(milestone[f]) for f in ('id', 'description', 'acceptance_criterion', 'owner'))
                or milestone['kind'] not in {'investigation', 'decision', 'engagement', 'commissioning', 'monitoring'}):
            raise ValueError('Owned milestones need a pathway, kind, dated prerequisite links and observable acceptance criterion.')
        path = indexed[milestone['pathway_id']]; links = ids(milestone['initiative_ids'], path['initiative_ids'])
        if not links: raise ValueError('Milestone must address a selected pathway initiative.')
        due = _date(milestone['due_date'])
        if not _date(horizon['start']) <= due <= _date(horizon['end']): raise ValueError('Milestone date must lie within transition horizon.')
        covered.add(path['id']); milestone_initiatives |= links; context = sourced(milestone, milestone['id'])
        if milestone['kind'] == 'monitoring': monitoring_paths.add(path['id'])
        if due < as_of: gap(milestone['id'] + ': milestone is overdue and unverified, not completed.')
        for initiative_id in links:
            if milestone['kind'] == 'commissioning' and milestone['due_date'] != initiatives[initiative_id]['proposal']['target_date']:
                gap(milestone['id'] + ': proposed commissioning differs from source strategy initiative date; upstream timing reconciliation remains open.')
        if milestone['kind'] == 'commissioning':
            path_row = next(r for r in rows if r['pathway']['id'] == path['id'])
            for checkpoint in path_row['checkpoints']:
                start = _date(checkpoint['target_snapshot']['target']['period']['start'])
                model = checkpoint['modeled_case']
                if due > start and (model is None or model['scenario']['scenario_review']['timing_basis'] == 'full_period_from_start'):
                    timing_conditions.append({'milestone_id': milestone['id'], 'target_result_id': checkpoint['references']['target_result_id'],
                        'status': 'known_unmet_timing_assumption' if model else 'timing_unassessed', 'completion_verified': False})
                    gap(milestone['id'] + ': commissioning follows checkpoint-period start; full-period contribution is not supported by this schedule.')
                elif model and due > start:
                    gap(milestone['id'] + ': late commissioning requires profile-specific reconciliation; a dated model does not prove this revised schedule.')
        actions.append({'id': milestone['id'], 'target_date': milestone['due_date'], 'depends_on': milestone['depends_on']})
        milestone_rows.append({'proposal': copy.deepcopy(milestone), 'source_context': context,
            'status': 'overdue_unverified' if due < as_of else 'proposed_unsent', 'completion_verified': False, 'owner_acceptance_verified': False})
    sequence = _action_sequence(actions)
    for missing in set(indexed) - covered: gap(missing + ': no dated decision, engagement, delivery or monitoring milestone proposed.')
    for missing in used_initiatives - milestone_initiatives: gap(missing + ': selected initiative has no milestone response.')
    for missing in set(indexed) - monitoring_paths: gap(missing + ': no monitoring milestone proposed; checkpoint performance remains unverified.')
    governance = parameters['governance']; governance_context = []
    if governance is None: gap('Transition governance owner, cadence and reassessment triggers remain unassessed.')
    else:
        if (not isinstance(governance, dict) or set(governance) != {'owner', 'cadence', 'reassessment_triggers', 'evidence_ids', 'evidence_fit'}
                or any(not _text(governance[f]) for f in ('owner', 'cadence')) or not isinstance(governance['reassessment_triggers'], list)
                or not governance['reassessment_triggers'] or any(not _text(t) for t in governance['reassessment_triggers'])):
            raise ValueError('Proposed governance needs owner, cadence, explicit reassessment triggers and sources.')
        governance_context = sourced(governance, 'Governance proposal')
    shared = {ident: sorted(set(paths)) for ident, paths in uses.items() if len(set(paths)) > 1}
    for ident in shared: gap(ident + ': checkpoint source reused across alternative pathways; outcomes are not additive.')
    if not review['coverage_complete']: gap('Selected transition coverage is incomplete; no whole-organization transition claim.')
    result['review_requirements'].append({'id': result['id'] + '-transition-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
        'reason': 'Review pathway/source fitness, interim ambition, interactions, external dependencies, timing, funding and governance before adoption.',
        'scope': review['scope'], 'reviewer_role': 'Accountable transition owner and technical, financial and affected-interest specialists',
        'status': 'open', 'resolution': None})
    return {'strategy_result_id': parameters['strategy_result_id'], 'strategy_snapshot': copy.deepcopy(strategy), 'plan': copy.deepcopy(plan),
        'transition_review': copy.deepcopy(review), 'pathways': rows, 'dependency_snapshots': snapshots, 'shared_dependency_ids': shared,
        'milestones': milestone_rows, 'proposed_sequence': sequence, 'timing_conditions': timing_conditions, 'governance': copy.deepcopy(governance),
        'governance_source_context': governance_context, 'trajectory': None, 'portfolio_total': None, 'funding_plan_approved': False,
        'plan_adopted': False, 'implementation_authorized': False, 'monitoring_started': False, 'public_claim_authorized': False,
        'science_based_validated': False, 'net_zero_validated': False}
