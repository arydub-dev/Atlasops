"""Deterministic recovery answers; no recovery data is sent to external AI."""
import re
from datetime import datetime,timezone
from sqlalchemy import select
from app.models import RecoveryCase
from app.services.recovery import store,engine,simulator
from app.tenancy.context import get_tenant

def matches(prompt):
    return bool(re.search(r'\b(work[- ]?orders?|recovery|spares readiness)\b',prompt,re.I))

def context(db,prompt):
    ctx=get_tenant()
    if not store.READ_PERMISSIONS.issubset(ctx.permissions):
        return {'recovery_answer':'I cannot verify recovery readiness with the records authorized for this account.'}
    records,positions,catalog,fingerprint=store.snapshot(db,ctx.organization_id)
    now=datetime.now(timezone.utc);result=engine.calculate(records,positions,catalog,now)
    orders=result['orders']
    if not orders:return {'recovery_answer':'I cannot verify work-order readiness: no active validated work-order requirements are available.'}
    requested=[o for o in orders if re.search(r'(?<!\w)'+re.escape(o['work_order'])+r'(?!\w)',prompt,re.I)]
    lines=['Readiness derived from recorded quantities; physical stock is not independently verified.',result['allocation_rule']]
    for order in (requested or orders)[:20]:
        lines.append(f"{order['work_order']}: {order['status']}.")
        for row in order['requirements']:
            lines.append(f"- {row['sku']} at {row['site']}: required {row['required_quantity']}; allocated stock {row['allocated_on_hand']}, supported inbound {row['allocated_inbound']}, shortfall {row['shortfall']}. {'; '.join(row['reasons'])}. Evidence: {', '.join(row['evidence'])}.")
        if requested and any(word in prompt.lower() for word in ['option','transfer','cost','another site','recover']):
            plan=engine.options(records,positions,catalog,now,order['work_order'])
            lines.append(plan['ranking'])
            for o in plan['options']:
                lines.append(f"{o['description']}: feasible={o['feasible']}, estimated arrival={o['arrival']}, recorded direct cost={o['direct_cost']} {o['currency'] or '(currency missing)'}. {'; '.join(o['limitations'])}. Evidence: {', '.join(o['evidence'])}.")
            if not plan['options']:lines.append('I cannot verify a feasible recovery action: supporting timing, quantity or authorization records are missing.')
    if len(requested)>1 and any(word in prompt.lower() for word in ['plan','simulat','compare']):
        try:
            comparison=simulator.compare(records,positions,catalog,now,[o['work_order'] for o in requested])
            recommended=next((p for p in comparison['plans'] if p['id']==comparison['recommended_plan_id']),None)
            lines.append(comparison['ranking'])
            if recommended:
                lines.append('First supported plan for human review: '+recommended['description'])
                lines.append('Restored work orders: '+', '.join(recommended['restored_work_orders']))
                lines.append('Known direct cost: '+str(recommended['known_direct_cost'])+' '+str(recommended['currency'])+'. Unknown values are not zero.')
                lines.append('Evidence: '+', '.join(recommended['evidence']))
                lines.extend(recommended['assumptions'])
            else:lines.append('I cannot verify a feasible combined recovery plan from available authorized records.')
        except ValueError as exc:lines.append('I cannot conclude a combined plan: '+str(exc))
    if 'past' in prompt.lower() or 'resolved' in prompt.lower():
        cases=db.scalars(select(RecoveryCase).where(RecoveryCase.organization_id==ctx.organization_id,RecoveryCase.status=='outcome_recorded').order_by(RecoveryCase.created_at.desc()).limit(10)).all()
        lines.append('Recorded past outcomes (not inferred savings):')
        for case in cases:lines.append(f"Case {case.id}: {case.work_order}; recorded outcome {case.data.get('outcome')}; final readiness {case.data.get('final_readiness',{}).get('status') if case.data.get('final_readiness') else 'unknown'}.")
        if not cases:lines.append('No recorded recovery outcomes are available.')
    if len(orders)>20 and not requested:lines.append('Showing first 20 work orders; ask for a specific work-order ID for details.')
    return {'recovery_answer':'\n'.join(lines),'recovery_fingerprint':fingerprint}
