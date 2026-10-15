"""Narrow, deterministic evidence retrieval for specific delivery-event questions.

No model interprets database access or decides whether a delivery is supported.
Unsupported phrasing asks for clarification instead of treating a partial match
as evidence. Dates without a timezone are explicitly interpreted in UTC.
"""
from datetime import date, datetime, time, timedelta, timezone
import re

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import Shipment, Supplier
from app.models.enums import ShipmentStatus
from app.tenancy.context import get_tenant

_NUMBER = r'(?:\d{1,3}(?:,\d{3})+|\d+)'
_DELIVERY = re.compile(
    rf'\s*(?:(?:which|what)\s+(?:supplier|vendor)s?|who)\s+'
    rf'(?:(?:has|have)\s+)?delivered\s+(?:exactly\s+)?(?P<units>{_NUMBER})\s+units?\s+'
    r'(?P<day>yesterday|today|(?:on\s+)?\d{4}-\d{2}-\d{2})(?:\s*\(?UTC\)?)?\s*[?!.]*\s*', re.I,
)


def is_delivery_question(prompt: str) -> bool:
    """Leave general supplier/delivery performance summaries on their old path."""
    return bool(re.search(r'\b(delivered|deliver)\b', prompt, re.I) or (
        re.search(r'\b(delivery|deliveries|received)\b', prompt, re.I)
        and re.search(r'\b(yesterday|today|units?)\b|\d{4}-\d{2}-\d{2}', prompt, re.I)))


def delivery_evidence(db: Session, prompt: str) -> dict | None:
    if not is_delivery_question(prompt):
        return None
    tenant = get_tenant()
    if not {'shipments.read', 'suppliers.read'}.issubset(tenant.permissions):
        return {'status': 'restricted'}
    match = _DELIVERY.fullmatch(prompt)
    if not match:
        return {'status': 'clarify'}
    try:
        units = int(match['units'].replace(',', ''))
        if units > 10**12:
            return {'status': 'clarify'}
        day_text = match['day'].lower().removeprefix('on ')
        today = datetime.now(timezone.utc).date()
        day = today-timedelta(days=1) if day_text == 'yesterday' else today if day_text == 'today' else date.fromisoformat(day_text)
    except ValueError:
        return {'status': 'clarify'}
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start+timedelta(days=1)
    org_id = tenant.organization_id
    rows = db.execute(select(Shipment, Supplier)
        .outerjoin(Supplier, and_(Supplier.id == Shipment.supplier_id, Supplier.organization_id == org_id))
        .where(Shipment.organization_id == org_id, Shipment.status == ShipmentStatus.DELIVERED,
               Shipment.units == units, Shipment.delivered_at >= start, Shipment.delivered_at < end)
        .order_by(Shipment.delivered_at, Shipment.id).limit(51)).all()
    return {'status': 'found' if rows else 'missing', 'units': units, 'day': day.isoformat(),
        'timezone': 'UTC', 'truncated': len(rows) > 50,
        'records': [{'reference': shipment.reference, 'supplier': supplier.name if supplier else None,
                     'units': shipment.units, 'delivered_at': (
                         shipment.delivered_at.replace(tzinfo=timezone.utc) if shipment.delivered_at.tzinfo is None
                         else shipment.delivered_at.astimezone(timezone.utc)).isoformat()}
                    for shipment, supplier in rows[:50]]}


def delivery_answer(evidence: dict) -> str:
    if evidence['status'] == 'restricted':
        return 'I cannot verify that delivery from the records authorized for this account. Shipment and supplier read permissions are required.'
    if evidence['status'] == 'clarify':
        return ('I cannot verify that delivery claim without an unambiguous unit count and date. '
                'I can check recorded completed shipments for an exact number of units on one UTC day. '
                'Ask which supplier delivered that number of units yesterday, today, or on YYYY-MM-DD (UTC). '
                'Supplier performance metrics are not evidence of a delivery.')
    description = f"exactly {evidence['units']:,} units on {evidence['day']} (UTC)"
    if evidence['status'] == 'missing':
        return (f'I cannot verify which supplier delivered {description} from the available authorized records. '
                'No recorded completed shipment with a delivery timestamp matches both conditions. '
                'This does not prove that no delivery occurred; the records may be incomplete. '
                'Supplier performance metrics are not evidence of this delivery.')
    lines = [f'Recorded completed shipments matching {description}:']
    for row in evidence['records']:
        name = row['supplier'] or 'supplier identity not available in authorized records'
        lines.append(f"- Shipment {row['reference']} — {name}; {row['units']:,} units; recorded delivery {row['delivered_at']}.")
    if evidence['truncated']:
        lines.append('More than 50 shipments match; showing the first 50. Narrow the question before treating this as an exhaustive list.')
    lines.append('These are recorded shipment facts, not independent confirmation of physical delivery.')
    return '\n'.join(lines)
