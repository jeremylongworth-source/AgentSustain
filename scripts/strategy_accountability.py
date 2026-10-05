"""Source-attributed responsibility, acceptance candidates and unsent escalation."""
import copy

from .strategy_stakeholders import _date, evidence
from .strategy_tools import _text, _reviewed, _reproduce


def assign(state, parameters, refs, result, gap):
    _, roadmap = _reproduce(state, parameters['roadmap_result_id'], 'build-implementation-roadmap', refs)
    review = parameters['accountability_review']
    _reviewed(state, review, refs, ('scope', 'responsibility_basis', 'authority_basis', 'acceptance_basis', 'conflict_policy', 'coverage_limitations'))
    as_of = _date(review.get('as_of_date'))
    if (review['scope'] != roadmap['implementation_review']['scope'] or review.get('period') != state['reporting_period']
            or type(review.get('coverage_complete')) is not bool or as_of < _date(roadmap['implementation_review']['as_of_date'])
            or review.get('method') != 'raci_proposal'):
        raise ValueError('Matched current roadmap context, explicit coverage and sourced RACI proposal review required.')
    if as_of>_date(roadmap['roadmap']['review_date']) or as_of>_date(roadmap['roadmap']['horizon']['end']):
        gap('Source roadmap review/horizon has elapsed; current assignment and delivery applicability need review, not historical rewriting.')
    known = {e['id']:e for e in state['evidence']}; items = {}; actors = {}; actor_rows = []; assignment_rows = []; assignments = {}; rights = []; routes = []
    def item(kind, ident, owner, source):
        items[(kind,ident)] = {'item_type':kind,'item_id':ident,'source_owner':owner,'source':copy.deepcopy(source)}
    for task in roadmap['work_packages']: item('work_package',task['proposal']['id'],task['proposal']['owner'],task)
    for phase in roadmap['roadmap']['phases']: item('phase',phase['id'],phase['owner'],phase)
    for milestone in roadmap['transition_snapshot']['milestones']: item('milestone',milestone['proposal']['id'],milestone['proposal']['owner'],milestone)
    for ident, resource in roadmap['resources'].items(): item('resource',ident,None,resource)
    item('governance',roadmap['roadmap']['id'],roadmap['roadmap']['owner'],roadmap['roadmap'])
    for requirement in state['review_requirements']:
        if requirement['status']=='open': item('review_requirement',requirement['id'],requirement['reviewer_role'],requirement)
    def ids(values, valid=None):
        if (not isinstance(values,list) or any(not _text(v) for v in values) or len(set(values))!=len(values)
                or (valid is not None and not set(values)<=set(valid))):
            raise ValueError('Distinct current accountability reference IDs required.')
        return set(values)
    def sourced(record,label):
        if record['evidence_fit'] not in {'reviewed_supporting','unverified'}: raise ValueError('Explicit accountability source fitness required.')
        evidence(record['evidence_ids'],known,refs)
        if not record['evidence_ids'] or record['evidence_fit']!='reviewed_supporting': gap(label+': source fitness remains unverified.')
        return [copy.deepcopy(known[e]) for e in record['evidence_ids']]
    def observed(record,label):
        value = record['observed_date']
        if value is None: gap(label+': observation date unknown; receipt/access/planning dates do not supply acceptance or authority.'); return False
        when = _date(value)
        if when>as_of: raise ValueError('Acceptance/mandate observations cannot follow accountability as-of date.')
        if not record['evidence_ids'] or any(not _date(known[e]['period']['start'])<=when<=_date(known[e]['period']['end']) for e in record['evidence_ids']):
            gap(label+': observation/source-period fit needs upstream reconciliation.'); return False
        return True
    roster = parameters['actors']
    if not isinstance(roster,list): raise ValueError('Explicit proposed actor roster required.')
    for actor in roster:
        if (not isinstance(actor,dict) or set(actor)!={'id','name','role','role_scope','evidence_ids','evidence_fit','mandate','availability'}
                or any(not _text(actor[f]) for f in ('id','name','role','role_scope')) or actor['id'] in actors):
            raise ValueError('Distinct named actors with explicit role scope, mandate and availability context required.')
        actors[actor['id']]=actor; context=sourced(actor,actor['id']); mandate=actor['mandate']; mandate_row=None
        if mandate is None: gap(actor['id']+': role title does not establish a mandate or decision authority.')
        else:
            if (not isinstance(mandate,dict) or set(mandate)!={'description','limitations','observed_date','valid_until','evidence_ids','evidence_fit'}
                    or any(not _text(mandate[f]) for f in ('description','limitations'))):
                raise ValueError('Mandate needs source description, limits, observation and explicit expiry or unknown.')
            mandate_context=sourced(mandate,actor['id']+' mandate'); dated=observed(mandate,actor['id']+' mandate')
            until=None if mandate['valid_until'] is None else _date(mandate['valid_until'])
            if until and mandate['observed_date'] and until<_date(mandate['observed_date']): raise ValueError('Mandate expiry cannot precede its observation.')
            if until is None: gap(actor['id']+': mandate expiry/current applicability unknown, not indefinite authority.')
            expired=until is not None and until<as_of
            if expired: gap(actor['id']+': sourced mandate has expired; renewed authority remains unverified.')
            mandate_row={'record':copy.deepcopy(mandate),'source_context':mandate_context,'status':'expired_source' if expired else 'sourced_mandate_candidate' if dated and mandate['evidence_fit']=='reviewed_supporting' and until is not None else 'unverified', 'authority_verified':False}
        availability=actor['availability']; availability_row=None
        if availability is None: gap(actor['id']+': availability and workload acceptance remain unassessed.')
        else:
            if not isinstance(availability,dict) or set(availability)!={'description','resource_ids','evidence_ids','evidence_fit'} or not _text(availability['description']):
                raise ValueError('Availability context needs a source description and selected resource references.')
            ids(availability['resource_ids'],roadmap['resources']); availability_context=sourced(availability,actor['id']+' availability')
            if not availability['resource_ids']: gap(actor['id']+': availability does not link a sourced resource calendar.')
            availability_row={'record':copy.deepcopy(availability),'source_context':availability_context,'availability_verified':False,'resources_reserved':False}
        actor_rows.append({'proposal':copy.deepcopy(actor),'source_context':context,'mandate':mandate_row,'availability':availability_row,'identity_verified':False,'qualified_reviewer_verified':False})
    matrix=parameters['assignments']; roles=('responsible','accountable','consulted','informed')
    if not isinstance(matrix,list): raise ValueError('Explicit responsibility assignments list required.')
    assignment_ids=set()
    for assignment in matrix:
        if (not isinstance(assignment,dict) or set(assignment)!={'id','item_type','item_id',*roles,'acceptance_records','reviewer_actor_id','evidence_ids','evidence_fit'}
                or not _text(assignment['id']) or assignment['id'] in assignment_ids or (assignment['item_type'],assignment['item_id']) not in items):
            raise ValueError('Distinct exact responsibility assignments must reference current roadmap items or open reviews.')
        key=(assignment['item_type'],assignment['item_id'])
        if key in assignments: raise ValueError('One explicit responsibility record per selected item required; reconcile competing records upstream.')
        assignment_ids.add(assignment['id']); assignments[key]=assignment
        selected={role:ids(assignment[role],actors) for role in roles}; context=sourced(assignment,assignment['id'])
        if not selected['responsible']: gap(assignment['id']+': no responsible actor proposed.')
        if len(selected['accountable'])!=1: gap(assignment['id']+': accountable owner missing or ambiguous; multiple proposals are not joint approval.')
        reviewer=assignment['reviewer_actor_id']
        if reviewer is not None and reviewer not in actors: raise ValueError('Reviewer must be a selected actor or null when unassigned.')
        if reviewer is None: gap(assignment['id']+': independent acceptance/source review remains unassigned.')
        elif reviewer in selected['responsible']|selected['accountable']: gap(assignment['id']+': proposed reviewer is also a delivery/decision owner; independence needs review.')
        source_owner=items[key]['source_owner']
        if source_owner and not any(source_owner in {actors[a]['name'],actors[a]['role']} for a in selected['responsible']|selected['accountable']):
            gap(assignment['id']+': proposed actors do not map to source owner '+source_owner+'; delegation/source-owner reconciliation remains open.')
        acceptance=assignment['acceptance_records']; accepted=set(); acceptance_rows=[]
        if not isinstance(acceptance,list): raise ValueError('Explicit scoped acceptance records list required.')
        for record in acceptance:
            if (not isinstance(record,dict) or set(record)!={'actor_id','role','item_type','item_id','statement','observed_date','evidence_ids','evidence_fit'}
                    or record['role'] not in roles or record['actor_id'] not in selected[record['role']] or not _text(record['statement'])
                    or (record['item_type'],record['item_id'])!=key or (record['actor_id'],record['role']) in accepted):
                raise ValueError('Acceptance must match one selected actor, role and exact assignment item; generic role acceptance cannot transfer.')
            accepted.add((record['actor_id'],record['role'])); acceptance_context=sourced(record,assignment['id']+' acceptance'); dated=observed(record,assignment['id']+' acceptance')
            supported=dated and bool(record['evidence_ids']) and record['evidence_fit']=='reviewed_supporting'
            acceptance_rows.append({'record':copy.deepcopy(record),'source_context':acceptance_context,'status':'sourced_acceptance_candidate' if supported else 'unverified','acceptance_verified':False})
        for role in ('responsible','accountable'):
            for actor_id in sorted(selected[role]):
                if not any(r['record']['actor_id']==actor_id and r['record']['role']==role and r['status']=='sourced_acceptance_candidate' for r in acceptance_rows):
                    gap(assignment['id']+': '+role+' '+actor_id+' lacks a sourced scoped acceptance candidate.')
        assignment_rows.append({'proposal':copy.deepcopy(assignment),'item_snapshot':copy.deepcopy(items[key]),'source_context':context,'acceptance_records':acceptance_rows,
            'status':'ambiguous_accountability' if len(selected['accountable'])>1 else 'unassigned_accountability' if not selected['accountable'] else 'proposed_pending_review',
            'assignment_approved':False,'owner_acceptance_verified':False,'implementation_authorized':False})
    for key in sorted(set(items)-set(assignments)): gap(key[0]+':'+key[1]+': accountability item omitted; source ownership/review remains open.')
    decisions=parameters['decision_rights']; right_ids=set()
    if not isinstance(decisions,list): raise ValueError('Explicit proposed decision rights list required.')
    open_reviews={r['id'] for r in state['review_requirements'] if r['status']=='open'}
    for right in decisions:
        if (not isinstance(right,dict) or set(right)!={'id','item_type','item_id','decision','actor_id','mandate_description','required_review_ids','evidence_ids','evidence_fit'}
                or not _text(right['id']) or right['id'] in right_ids or (right['item_type'],right['item_id']) not in items or right['actor_id'] not in actors
                or not _text(right['mandate_description']) or right['decision'] not in {'task_acceptance','phase_exit','technical_review','funding_decision','work_start','monitoring_review','public_claim_review'}):
            raise ValueError('Distinct proposed decision roles need a current item, actor, decision kind and scoped mandate description.')
        right_ids.add(right['id']); ids(right['required_review_ids'],open_reviews); context=sourced(right,right['id'])
        actor_row=next(a for a in actor_rows if a['proposal']['id']==right['actor_id'])
        if not actor_row['mandate'] or actor_row['mandate']['status']!='sourced_mandate_candidate': gap(right['id']+': current scoped mandate remains unverified.')
        linked=assignments.get((right['item_type'],right['item_id']))
        if linked is None or right['actor_id'] not in linked['accountable']: gap(right['id']+': decision role does not match a single proposed accountable owner.')
        if linked is not None and len(linked['accountable'])!=1: gap(right['id']+': competing accountable proposals leave decision ownership unresolved.')
        if not set(right['required_review_ids'])>=open_reviews: gap(right['id']+': omitted open review references do not waive historical review obligations.')
        gap(right['id']+': decision authority and qualified approval remain pending; a proposed right is not an actual decision.')
        rights.append({'proposal':copy.deepcopy(right),'source_context':context,'status':'proposed_pending_authority_review','decision_record':None,'authority_verified':False,'approval_granted':False})
    if not decisions: gap('Decision roles remain unassigned; responsibility names do not supply approval authority.')
    escalations=parameters['escalation_routes']; edges={}; route_ids=set()
    if not isinstance(escalations,list): raise ValueError('Explicit proposed escalation routes list required.')
    for route in escalations:
        if (not isinstance(route,dict) or set(route)!={'id','item_type','item_id','from_actor_id','to_actor_id','trigger','response_days','evidence_ids','evidence_fit'}
                or not _text(route['id']) or route['id'] in route_ids or (route['item_type'],route['item_id']) not in items
                or route['from_actor_id'] not in actors or route['to_actor_id'] not in actors or route['from_actor_id']==route['to_actor_id']
                or not _text(route['trigger']) or type(route['response_days']) is not int or route['response_days']<=0):
            raise ValueError('Distinct nonself escalation routes need a current item, known actors, trigger and positive supplied calendar response days.')
        route_ids.add(route['id']); key=(route['item_type'],route['item_id']); graph=edges.setdefault(key,{})
        if route['to_actor_id'] in graph.get(route['from_actor_id'],set()): raise ValueError('Duplicate escalation edge for one item requires reconciliation.')
        graph.setdefault(route['from_actor_id'],set()).add(route['to_actor_id']); context=sourced(route,route['id'])
        routes.append({'proposal':copy.deepcopy(route),'source_context':context,'status':'proposed_unsent','contacted':False,'response_observed':False})
    for graph in edges.values():
        nodes=set(graph)|{target for targets in graph.values() for target in targets}
        indegree={node:0 for node in nodes}
        for targets in graph.values():
            for target in targets: indegree[target]+=1
        ready=[node for node in nodes if indegree[node]==0]; count=0
        while ready:
            node=ready.pop(); count+=1
            for target in graph.get(node,set()):
                indegree[target]-=1
                if indegree[target]==0: ready.append(target)
        if count!=len(nodes): raise ValueError('Escalation routes for one item contain a cycle.')
    for key in assignments:
        if key not in edges: gap(key[0]+':'+key[1]+': no escalation path proposed for unresolved ownership, acceptance or decisions.')
    shared={}
    for actor in roster:
        if actor['availability']:
            for rid in actor['availability']['resource_ids']: shared.setdefault(rid,[]).append(actor['id'])
    shared={rid:actors for rid,actors in shared.items() if len(actors)>1}
    for rid in shared: gap(rid+': multiple actors link the same resource pool; availability is not independent or newly reserved.')
    if not review['coverage_complete']: gap('Accountability coverage is incomplete; no whole-organization ownership or accepted governance.')
    result['review_requirements'].append({'id':result['id']+'-accountability-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
        'reason':'Review role/source identity, scoped acceptance, mandates, independence, workload, decision rights and escalation before adopting assignments.',
        'scope':review['scope'],'reviewer_role':'Accountable governance owner and relevant professional/workforce reviewers','status':'open','resolution':None})
    return {'roadmap_result_id':parameters['roadmap_result_id'],'roadmap_snapshot':copy.deepcopy(roadmap),'accountability_review':copy.deepcopy(review),
        'actors':actor_rows,'items':list(items.values()),'assignments':assignment_rows,'decision_rights':rights,'escalation_routes':routes,'shared_resource_actor_ids':shared,
        'delivery_screen':roadmap['delivery_screen'],'roadmap_applicability_verified':False,'assignments_adopted':False,'authority_verified':False,'funding_authorized':False,'resources_reserved':False,
        'implementation_authorized':False,'public_claim_authorized':False,'review_requirements_resolved':False}
