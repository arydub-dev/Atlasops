"""Bounded, non-mutating plan comparison using the existing shared demand ledger.

Enumerates single actions and pairs; never claims globally optimal plans. All
inputs originate in store.snapshot for one authorized organization.
"""
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
import json
from app.services.recovery import engine


def signature(plan):
    """Ignore relative execution timestamps; compare material outcomes and constraints."""
    fields = ('id', 'actions', 'effects', 'feasible', 'limitations', 'known_direct_cost', 'currency')
    value = {k: plan[k] for k in fields}
    value['effects'] = [{k:v for k,v in e.items() if k!='requirements'} for e in plan['effects']]
    value['actions'] = [{k:v for k,v in a.items() if k not in ('arrival','adjustments')} for a in plan['actions']]
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def compare(records, positions, catalog, now, work_orders):
    requested = sorted(set(work_orders))
    if not requested or len(requested)>8:
        raise ValueError('Select between one and eight work orders')
    baseline = engine.calculate(records, positions, catalog, now)
    orders = {o['work_order']:o for o in baseline['orders']}
    if not set(requested)<=orders.keys():
        raise ValueError('Selected work orders are not present in authorized active records')
    if sum(len(o['requirements']) for o in orders.values())>250:
        raise ValueError('Plan comparison supports at most 250 active requirement lines; no partial schedule is evaluated')
    candidates=[]
    rules={r['id']:r['data'] for r in records if r['kind']=='rule'}
    for wo in requested:
        candidates.extend(engine.options(records,positions,catalog,now,wo,internal=True)['options'])
    candidates.sort(key=lambda a:a['id'])
    if len(candidates)>12:
        raise ValueError('More than twelve candidate actions; narrow the work-order selection or resolve source rules')
    pools={(p['sku'],p['site']):p for p in baseline['remaining_stock']}

    def assess(actions):
        limitations=[];changes=[];uses=defaultdict(int);seen_rules=set();seen_po=set();seen_requirements=set()
        preview_safe=True
        for action in actions:
            limitations.extend(action['limitations'])
            preview_safe &= action['preview_safe']
            rule=rules[action['rule_id']]
            if action['rule_id'] in seen_rules:
                limitations.append('The same authorization cannot be consumed twice in one plan')
                preview_safe=False
            seen_rules.add(action['rule_id'])
            if action['requirement_id'] in seen_requirements:
                limitations.append('Multiple full-deficit actions target the same requirement; quantity splitting is not supported')
                preview_safe=False
            seen_requirements.add(action['requirement_id'])
            if action['action']=='repair' and not rule.get('repair_reference'):
                limitations.append('Repairable item identity and availability reference missing')
                preview_safe=False
            for change in action['adjustments']:
                if change['type']=='take':uses[(change['sku'],change['site'])]+=change['quantity']
                if change['type']=='expedite':
                    if change['inbound'] in seen_po:
                        limitations.append('Multiple actions address the same purchase-order line; supply cannot be counted twice')
                        preview_safe=False
                    seen_po.add(change['inbound'])
                changes.append(change)
        for key,qty in uses.items():
            pool=pools.get(key)
            if not pool or pool['unknown'] or pool['risk']:
                limitations.append('Combined donor evidence is missing, stale or contradictory');preview_safe=False
            elif qty>pool['available']:
                limitations.append('Combined actions exceed uncommitted donor stock')
                # Permit showing donor harm only if the physical unreserved stock exists.
                if qty>(pool['recorded']-pool['reserved']):preview_safe=False
        scenario=engine.calculate(records,positions,catalog,now,changes) if preview_safe else None
        effects=[]
        for wo,before in orders.items():
            after=next((o for o in scenario['orders'] if o['work_order']==wo),None) if scenario else None
            def shortage(order):
                if order is None or order['status']=='UNKNOWN':return None
                return sum(r['shortfall'] or 0 for r in order['requirements'])
            b=shortage(before);a=shortage(after)
            worsened=bool(after and ((before['status']=='READY' and after['status']!='READY') or (b is not None and a is not None and a>b)))
            if worsened:limitations.append('Plan worsens readiness or shortage for '+wo)
            effects.append({'work_order':wo,'before':before['status'],'after':after['status'] if after else 'UNKNOWN','before_shortfall':b,'after_shortfall':a,'new_shortage':worsened,'priority':min(r['priority'] for r in before['requirements']),'requirements':after['requirements'] if after else before['requirements']})
        if actions and any(e['after']=='UNKNOWN' for e in effects):limitations.append('Unknown readiness prevents a supported plan conclusion')
        restored=[e['work_order'] for e in effects if e['before']!='READY' and e['after']=='READY']
        if actions and not any(wo in restored for wo in requested):limitations.append('No selected work order reaches readiness under this plan')
        public_actions=[{k:v for k,v in a.items() if k not in ('adjustments','preview_safe')} for a in actions]
        currencies={a['currency'] for a in actions}
        comparable=bool(actions) and all(not a['cost_missing'] for a in actions) and len(currencies)==1
        pid='baseline' if not actions else 'plan-'+sha256('|'.join(a['id'] for a in actions).encode()).hexdigest()[:24]
        plan={'id':pid,'description':'Current state — no intervention' if not actions else ' + '.join(a['description'] for a in actions),'actions':public_actions,'effects':effects,'restored_work_orders':restored,'remaining_at_risk':[e['work_order'] for e in effects if e['after']!='READY'],'new_shortages':[e['work_order'] for e in effects if e['new_shortage']],'feasible':bool(actions) and not limitations,'limitations':sorted(set(limitations)),'known_direct_cost':sum(a['direct_cost'] for a in actions) if comparable else None,'currency':next(iter(currencies)) if comparable else None,'assumptions':['Lead times are scenario estimates, not new supplier commitments.','All active work orders share one allocation ledger.','Approval records a decision; no inventory or external systems are changed.'],'evidence':sorted({e for a in actions for e in a['evidence']}),'approvals_required':sorted({a['approval_reference'] for a in actions if a['approval_reference']}),'as_of':now.isoformat()}
        plan['signature']=signature(plan)
        return plan

    plans=[assess([])]+[assess([a]) for a in candidates]+[assess(list(pair)) for pair in combinations(candidates,2)]
    feasible=[p for p in plans if p['feasible']]
    cost_rank=baseline['policy']['ranking']=='known_cost' and bool(feasible) and all(p['known_direct_cost'] is not None for p in feasible) and len({p['currency'] for p in feasible})==1
    def score(p):
        # Customer source priority 1 is most consequential; deadline allocation remains unchanged.
        restored_priority=sum(6-e['priority'] for e in p['effects'] if e['work_order'] in p['restored_work_orders'])
        return (not p['feasible'],-restored_priority,-len(p['restored_work_orders']),p['known_direct_cost'] if cost_rank and p['known_direct_cost'] is not None else 0,max((a['arrival'] or '9999' for a in p['actions']),default='9999'),p['id'])
    plans=[plans[0]]+sorted(plans[1:],key=score)
    return {'baseline':baseline,'work_orders':requested,'plans':plans,'recommended_plan_id':next((p['id'] for p in plans if p['feasible']),None),'ranking':'Feasibility, restored priority weight (6 minus source priority), restored order count, '+('complete known cost in one currency, ' if cost_rank else 'cost excluded because policy or evidence does not support comparison, ')+'latest estimated arrival, stable plan ID. Not an optimality claim.','limits':'At most two distinct documented actions per plan, eight selected orders and twelve candidate actions. Partial-quantity splits and automatic rescheduling are not implemented.','cost_comparison_enabled':cost_rank}
