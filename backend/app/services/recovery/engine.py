"""Pure, deterministic readiness allocation; no database writes or model calls."""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone


def date(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc) if value else None


def calculate(records, positions, catalog, now, adjustments=None):
    """All active demand shares one ledger, ordered by deadline, priority and source ID.

    Reservations are unavailable global commitments (never added back to a work order).
    Confirmed inbound is consumed once across the entire schedule. Unknown demand
    poisons later same-site/SKU allocations rather than inventing an available balance.
    """
    now=now.astimezone(timezone.utc)
    grouped=defaultdict(list)
    for r in records: grouped[r['kind']].append(r)
    policies=grouped['policy']
    policy=policies[0]['data'] if len(policies)==1 else {'max_age_days':7,'ranking':'arrival'}
    max_age=timedelta(days=policy['max_age_days'])
    quality=[]
    def stale(d):
        stamp=date(d.get('source_updated_at'))
        return stamp is None or stamp>now or now-stamp>max_age
    def issue(code,ids,message):
        quality.append({'code':code,'records':ids,'message':message})
    if len(policies)>1: issue('policy_conflict',[r['id'] for r in policies],'Multiple policies: no readiness result is reliable until corrected')
    aliases=defaultdict(set)
    for r in grouped['rule']:
        d=r['data']
        if d['action']=='alias' and d['permitted'] and d.get('approval_reference') and not stale(d):
            aliases[d['sku']].add(d.get('substitute_sku'))
    def sku(raw):
        if raw in catalog: return raw
        targets=aliases.get(raw,set())
        return next(iter(targets)) if len(targets)==1 and next(iter(targets)) in catalog else None
    pos=defaultdict(list)
    for p in positions: pos[(p['sku'],p['site'])].append(p)
    stock=defaultdict(list)
    for r in grouped['stock']:
        d=r['data'];stock[(sku(d['sku']) or d['sku'],d['site'])].append(r)
    pools={}
    for key in set(pos)|set(stock):
        p=pos[key]; evidence=stock[key]; reasons=[]; unknown=False; risk=False
        if len(p)!=1:
            unknown=True;reasons.append('Missing or conflicting current inventory position')
        if len(evidence)!=1:
            unknown=True;reasons.append('Missing or conflicting stock evidence')
        d=evidence[0]['data'] if len(evidence)==1 else {}
        quantity=p[0]['quantity'] if len(p)==1 else None
        if d.get('observed_quantity') is None or d.get('observed_quantity')!=quantity:
            unknown=True;reasons.append('Source quantity is missing or disagrees with recorded inventory')
        reserved=d.get('reserved_quantity')
        if reserved is None or (quantity is not None and reserved>quantity):
            unknown=True;reasons.append('Reservations missing or exceed recorded stock')
        if d.get('usability','unknown')=='unknown':
            unknown=True;reasons.append('Usability not established')
        if stale(d):
            risk=True;reasons.append('Stock source update missing, future-dated or stale')
        available=max((quantity or 0)-(reserved or 0),0) if not unknown and d.get('usability')=='usable' else 0
        ids=[r['id'] for r in evidence]+[p1['id'] for p1 in p]
        if reasons: issue('stock_trust',ids,'; '.join(reasons))
        pools[key]={'available':available,'recorded':quantity,'reserved':reserved,'unknown':unknown,'risk':risk,'reasons':reasons,'evidence':ids}
    inbound=[]; duplicates=defaultdict(list)
    for r in grouped['inbound']: duplicates[(r['data']['po'],r['data']['line'])].append(r)
    for values in duplicates.values():
        if len(values)>1: issue('duplicate_inbound',[r['id'] for r in values],'PO line appears more than once; excluded from supported supply')
        for r in values:
            d=r['data'];when=date(d.get('promised_at') or d.get('expected_at'))
            trusted=(len(values)==1 and d.get('confirmed') is True and d.get('date_source') and d.get('supplier') and when and when>=now and not stale(d) and d.get('open_quantity') is not None)
            if not trusted: issue('inbound_uncertain',[r['id']],'Missing, stale, duplicated or unconfirmed delivery commitment')
            inbound.append({'key':(sku(d['sku']) or d['sku'],d['site']),'left':d.get('open_quantity') or 0,'at':when,'trusted':bool(trusted),'id':r['id'],'source':d.get('date_source'),'confirmed':d.get('confirmed')})
    # Scenario adjustments are created server-side from validated rules only.
    for a in adjustments or []:
        if a['type']=='take':
            key=(a['sku'],a['site'])
            if key in pools: pools[key]['available']=max(0,pools[key]['available']-a['quantity'])
        elif a['type']=='arrival':
            inbound.append({'key':(a['sku'],a['site']),'left':a['quantity'],'at':a['at'],'trusted':True,'id':a['evidence'],'source':'documented scenario assumption','confirmed':False})
        elif a['type']=='expedite':
            for item in inbound:
                if item['id']==a['inbound']: item['at']=a['at']
    demand=sorted([r for r in grouped['requirement'] if r['data']['status'] not in ('completed','cancelled')],key=lambda r:(date(r['data'].get('required_by')) or datetime.min.replace(tzinfo=timezone.utc),r['data']['priority'],r['data']['work_order'],r['data']['record_id']))
    lines=[];poisoned=set()
    for r in demand:
        d=r['data'];part=sku(d['sku']);key=(part or d['sku'],d['site']);pool=pools.get(key)
        qty=d['quantity'];deadline=date(d['required_by']);reasons=[];evidence=[r['id']]
        unknown=(part is None or qty is None or deadline is None or pool is None or key in poisoned or len(policies)>1)
        if unknown: reasons.append('Essential part, quantity, date, stock, policy or prior demand is unresolved')
        if qty is None or deadline is None: poisoned.add(key)
        if pool:
            evidence+=pool['evidence'];reasons+=pool['reasons'];unknown |= pool['unknown']
        available=pool['available'] if pool else 0
        allocated=min(qty or 0,available)
        if pool: pool['available']-=allocated
        left=max((qty or 0)-allocated,0);incoming=0;uncertain=0;allocations=[]
        for item in sorted(inbound,key=lambda x:(x['at'] or datetime.max.replace(tzinfo=timezone.utc),x['id'])):
            if item['key']!=key: continue
            if item['at'] is None or not item['trusted']:
                uncertain+=item['left'];continue
            if deadline is not None and item['at']<=deadline:
                take=min(left,item['left']);left-=take;item['left']-=take;incoming+=take
                if take: allocations.append({'record':item['id'],'quantity':take,'arrival':item['at'].isoformat(),'date_source':item['source']});evidence.append(item['id'])
        risk=stale(d) or bool(pool and pool['risk']) or bool(deadline and deadline<now)
        if deadline and deadline<now: reasons.append('Required date has passed; current records do not establish historical readiness')
        if stale(d): reasons.append('Requirement source update missing, future-dated or stale')
        status='UNKNOWN' if unknown else 'AT RISK' if risk else 'AT RISK' if left and uncertain>=left else 'SHORTAGE' if left else 'READY'
        if left: reasons.append('Supported supply by the required date does not cover demand')
        if uncertain: reasons.append('Unconfirmed or undated inbound is not allocated as guaranteed supply')
        if not reasons: reasons.append('Covered by recorded usable stock and supported dated inbound under the allocation policy')
        if status!='READY': issue('requirement_'+status.lower().replace(' ','_'),[r['id']],'; '.join(reasons))
        lines.append({'record_id':r['id'],'work_order':d['work_order'],'sku':d['sku'],'canonical_sku':part,'site':d['site'],'asset':d.get('asset'),'priority':d['priority'],'required_by':d['required_by'],'required_quantity':qty,'recorded_on_hand':pool['recorded'] if pool else None,'reserved_quantity':pool['reserved'] if pool else None,'allocated_on_hand':allocated,'allocated_inbound':incoming,'shortfall':None if qty is None else left,'uncertain_inbound':uncertain,'inbound_allocations':allocations,'status':status,'reasons':reasons,'evidence':sorted(set(evidence))})
    orders=[]
    for wo in sorted({r['work_order'] for r in lines}):
        selected=[r for r in lines if r['work_order']==wo]
        status=next(s for s in ['UNKNOWN','SHORTAGE','AT RISK','READY'] if any(r['status']==s for r in selected))
        orders.append({'work_order':wo,'status':status,'requirements':selected})
    return {'as_of':now.isoformat(),'policy':policy,'allocation_rule':'Earliest required date, then priority (1 highest), work-order ID and source record ID. Reservations remain unavailable. Each unit allocated once.','orders':orders,'quality':quality,'remaining_stock':[{'sku':key[0],'site':key[1],**p} for key,p in sorted(pools.items())],'notice':'Recorded quantities only; physical inventory is not verified. Scenario arrivals are estimates, not operational changes.'}


def options(records,positions,catalog,now,work_order):
    baseline=calculate(records,positions,catalog,now)
    target=next((o for o in baseline['orders'] if o['work_order']==work_order),None)
    if not target: return {'baseline':None,'options':[]}
    result=[]
    for line in target['requirements']:
        deficit=line['shortfall']
        if not deficit: continue
        for r in records:
            if r['kind']!='rule':continue
            d=r['data']
            if d['sku']!=line['sku'] or d['site']!=line['site'] or d['action']=='alias':continue
            action=d['action'];missing=[];changes=[]
            if not d['permitted'] or not d.get('approval_reference'):missing.append('Documented permission/authorization missing')
            if d.get('lead_days') is None:missing.append('Completion timing missing')
            if d.get('quantity') is None or d['quantity']<deficit:missing.append('Supported action quantity insufficient or missing')
            stamp=date(d.get('source_updated_at'))
            if not stamp or stamp>now or now-stamp>timedelta(days=baseline['policy']['max_age_days']):missing.append('Action source evidence stale or missing')
            at=now+timedelta(days=d.get('lead_days') or 0)
            part=line['canonical_sku'] or line['sku']
            if action in ('transfer','substitute'):
                donor=d.get('donor_site') if action=='transfer' else line['site']
                donor_sku=part if action=='transfer' else d.get('substitute_sku')
                pool=next((p for p in baseline['remaining_stock'] if p['site']==donor and p['sku']==donor_sku),None)
                if not pool or pool['unknown'] or pool['risk']:missing.append('Donor stock not trustworthy')
                # Include all planned donor demand before treating remaining stock as free.
                if not pool or pool['available']<deficit:missing.append('Transfer/substitution would consume committed demand or exceed donor surplus')
                changes=[{'type':'take','sku':donor_sku,'site':donor,'quantity':deficit},{'type':'arrival','sku':part,'site':line['site'],'quantity':deficit,'at':at,'evidence':r['id']}]
            elif action=='expedite':
                inbound=next((v for v in records if v['kind']=='inbound' and v['data']['record_id']==d.get('inbound_record_id') and v['data']['sku']==line['sku'] and v['data']['site']==line['site']),None)
                if not inbound or inbound['data'].get('confirmed') is not True:missing.append('Confirmed matching PO line missing')
                changes=[{'type':'expedite','inbound':inbound['id'] if inbound else '', 'at':at}]
            elif action=='repair':
                changes=[{'type':'arrival','sku':part,'site':line['site'],'quantity':deficit,'at':at,'evidence':r['id']}]
            elif action=='reschedule':
                missing.append('Maintenance rescheduling requires a separate human-reviewed plan; no readiness change assumed')
            preview_safe=not missing or all(m=='Transfer/substitution would consume committed demand or exceed donor surplus' for m in missing)
            scenario=calculate(records,positions,catalog,now,changes) if preview_safe else None
            affected=[]
            if scenario:
                for order in scenario['orders']:
                    previous=next(o for o in baseline['orders'] if o['work_order']==order['work_order'])
                    if previous['status']!=order['status']:affected.append({'work_order':order['work_order'],'before':previous['status'],'after':order['status']})
            target_after=next((o['status'] for o in scenario['orders'] if o['work_order']==work_order),None) if scenario else None
            result.append({'id':r['id']+':'+line['record_id'],'action':action,'quantity':deficit,'description':f'{action.title()} {deficit} recorded units for {line["sku"]}', 'arrival':at.isoformat() if d.get('lead_days') is not None else None,'direct_cost':d.get('direct_cost'),'currency':d.get('currency'),'cost_missing':d.get('direct_cost') is None or not d.get('currency'),'owner':d.get('owner'),'approval_reference':d.get('approval_reference'),'feasible':not missing,'limitations':missing,'target_after':target_after,'affected_work':affected,'evidence':[r['id'],line['record_id']],'assumptions':['Documented lead time is an estimate; human approval and execution required.','Donor surplus is calculated after all imported active demand.']})
    # Currency differences preclude comparable price ranking.
    currencies={o['currency'] for o in result if o['feasible'] and not o['cost_missing']}
    cost_rank=baseline['policy']['ranking']=='known_cost' and len(currencies)==1 and all(not o['cost_missing'] for o in result if o['feasible'])
    result.sort(key=lambda o:(not o['feasible'],o['direct_cost'] if cost_rank and o['direct_cost'] is not None else 0,o['arrival'] or '9999',o['id']))
    return {'baseline':target,'options':result,'ranking':'Known direct cost in a common currency, then arrival' if cost_rank else 'Feasible first, then documented arrival, stable source ID; no cheapest claim'}
