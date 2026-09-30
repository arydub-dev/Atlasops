"""Stripe webhook processing with tenant context + event idempotency.

System path (signature-verified only):
1. Short-circuit if ``event.id`` already recorded.
2. Resolve ``organization_id`` from metadata / ``client_reference_id``, or via
   ``app_lookup_org_by_stripe_customer`` (reads ``stripe_customer_index`` only —
   no RLS bypass on the application role).
3. ``set_session_org`` so FORCE RLS allows tenant-scoped mutations.
4. Dispatch handler; record processed event id uniquely.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import stripe
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.billing.stripe_service import (
    StripeNotConfigured,
    reset_ai_credits_for_period,
    sync_subscription_from_stripe,
)
from app.core.config import settings
from app.models import BillingAccount, Organization, StripeEvent
from app.models.enums import SubscriptionStatus
from app.tenancy.rls import set_session_org

logger = logging.getLogger(__name__)


def construct_event(payload: bytes, sig_header: str | None) -> stripe.Event:
    """Verify and construct a Stripe Event. Raises StripeNotConfigured if unset."""
    if not settings.STRIPE_SECRET_KEY:
        raise StripeNotConfigured("webhook verification")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise StripeNotConfigured("webhook signature verification (STRIPE_WEBHOOK_SECRET)")
    if not sig_header:
        raise ValueError("Missing Stripe-Signature header")
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )


def _event_id(event: dict[str, Any] | Any) -> str | None:
    data = event if isinstance(event, dict) else dict(event)
    eid = data.get("id")
    return str(eid) if eid else None


def _already_processed(db: Session, event_id: str) -> bool:
    return (
        db.scalar(select(StripeEvent.id).where(StripeEvent.stripe_event_id == event_id))
        is not None
    )


def _mark_processed(db: Session, event_id: str, event_type: str, organization_id: UUID | None) -> None:
    db.add(
        StripeEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            organization_id=organization_id,
            processed_at=datetime.now(timezone.utc),
        )
    )
    db.flush()


def _lookup_org_id_by_customer(db: Session, customer_id: str) -> UUID | None:
    """Resolve org for invoice/subscription events that only carry customer id.

    PostgreSQL: call ``app_lookup_org_by_stripe_customer`` which reads the
    non-RLS ``stripe_customer_index`` mapping (migration 0013). Never uses
    ``SET LOCAL row_security = off`` and never requires app-role BYPASSRLS.

    SQLite / other dialects: direct ``BillingAccount`` query (no FORCE RLS).
    """
    cid = (customer_id or "").strip()
    if not cid:
        return None

    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        row = db.execute(
            text("SELECT app_lookup_org_by_stripe_customer(:cid)"),
            {"cid": cid},
        ).scalar()
        return UUID(str(row)) if row else None

    account = db.scalar(
        select(BillingAccount).where(BillingAccount.stripe_customer_id == cid)
    )
    return account.organization_id if account else None


def resolve_organization_id(db: Session, event_type: str, obj: dict[str, Any]) -> UUID | None:
    """Resolve tenant for a Stripe object.

    Prefer ``stripe_customer_index`` (authoritative customer→org map). Metadata
    ``organization_id`` / ``client_reference_id`` is only used when no customer
    mapping exists (e.g. first checkout). If both are present and disagree,
    the customer index wins — metadata must never remap billing across tenants.
    """
    _ = event_type
    customer_id = obj.get("customer")
    from_customer: UUID | None = None
    if isinstance(customer_id, str) and customer_id:
        from_customer = _lookup_org_id_by_customer(db, customer_id)

    meta = obj.get("metadata") or {}
    raw = meta.get("organization_id") or obj.get("client_reference_id")
    from_meta: UUID | None = None
    if raw:
        try:
            from_meta = UUID(str(raw))
        except ValueError:
            logger.warning("Invalid organization_id in Stripe event metadata: %s", raw)

    if from_customer and from_meta and from_customer != from_meta:
        logger.warning(
            "stripe_org_mismatch event=%s customer_org=%s metadata_org=%s — using customer index",
            event_type,
            from_customer,
            from_meta,
        )
        return from_customer
    if from_customer:
        return from_customer
    return from_meta


def handle_checkout_session_completed(db: Session, session_obj: dict[str, Any]) -> UUID | None:
    """Link subscription after successful Checkout. Returns organization_id."""
    org_id = resolve_organization_id(db, "checkout.session.completed", session_obj)
    if org_id is None:
        logger.warning("checkout.session.completed missing organization_id")
        return None
    set_session_org(db, org_id)
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if account is None:
        account = BillingAccount(organization_id=org_id)
        db.add(account)
        db.flush()
    if customer_id:
        account.stripe_customer_id = customer_id
    if subscription_id:
        # Checkout metadata and payment status cannot grant subscription access.
        # Retrieve the authoritative subscription; failure rolls back the event
        # claim so Stripe can retry instead of acknowledging an unpaid upgrade.
        if not settings.STRIPE_SECRET_KEY:
            raise StripeNotConfigured("checkout subscription verification")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        sub = stripe.Subscription.retrieve(subscription_id)
        if sub.get("customer") != customer_id:
            raise ValueError("Checkout subscription customer mismatch")
        sync_subscription_from_stripe(db, sub, organization_id=org_id)

    db.flush()
    return org_id


def _current_subscription(account: BillingAccount, subscription_id: str) -> Any:
    if not settings.STRIPE_SECRET_KEY:
        raise StripeNotConfigured("subscription reconciliation")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = stripe.Subscription.retrieve(subscription_id)
    if subscription.get("customer") != account.stripe_customer_id:
        raise ValueError("Subscription customer mismatch")
    return subscription


def _locked_account(db: Session, org_id: UUID) -> BillingAccount | None:
    set_session_org(db, org_id)
    return db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org_id)
        .with_for_update().execution_options(populate_existing=True)
    )


def handle_subscription_event(db: Session, subscription: dict[str, Any]) -> UUID | None:
    org_id = resolve_organization_id(db, "subscription", subscription)
    if org_id is None:
        return None
    account = _locked_account(db, org_id)
    if account is None:
        return org_id
    sub_id = subscription.get("id")
    if not sub_id or (account.stripe_subscription_id and account.stripe_subscription_id != sub_id):
        return org_id  # an event for an old/replaced subscription
    current = _current_subscription(account, sub_id)
    sync_subscription_from_stripe(db, current, organization_id=org_id)
    return org_id


def _reconcile_invoice(db: Session, invoice: dict[str, Any], *, paid: bool) -> UUID | None:
    org_id = resolve_organization_id(db, "invoice", invoice)
    if org_id is None:
        return None
    account = _locked_account(db, org_id)
    if account is None:
        return org_id
    sub_id = invoice.get("subscription") or (
        ((invoice.get("parent") or {}).get("subscription_details") or {}).get("subscription")
    )
    if isinstance(sub_id, dict):
        sub_id = sub_id.get("id")
    if not sub_id or sub_id != account.stripe_subscription_id:
        return org_id  # manual invoices cannot grant subscription access
    current = _current_subscription(account, sub_id)
    sync_subscription_from_stripe(db, current, organization_id=org_id)
    latest_invoice = current.get("latest_invoice")
    if isinstance(latest_invoice, dict):
        latest_invoice = latest_invoice.get("id")
    invoice_id = invoice.get("id")
    # A delayed invoice must not replenish credits in a newer billing period.
    # Separate event IDs for the same invoice also cannot reset usage twice.
    if (paid and invoice_id and latest_invoice == invoice_id
            and invoice.get("billing_reason") in ("subscription_cycle", "subscription_create")
            and account.status == SubscriptionStatus.ACTIVE):
        claim = f"invoice-credit-reset:{invoice_id}"
        if not _already_processed(db, claim):
            _mark_processed(db, claim, "internal.invoice_credit_reset", org_id)
            reset_ai_credits_for_period(db, account)
    db.flush()
    return org_id


def handle_invoice_payment_failed(db: Session, invoice: dict[str, Any]) -> UUID | None:
    return _reconcile_invoice(db, invoice, paid=False)


def handle_invoice_paid(db: Session, invoice: dict[str, Any]) -> UUID | None:
    return _reconcile_invoice(db, invoice, paid=True)


def dispatch_stripe_event(db: Session, event: dict[str, Any] | Any) -> str:
    """Route a Stripe event; idempotent on ``event.id``; sets tenant RLS context.

    Claims ``event.id`` before side effects so concurrent retries cannot double-apply
    credit resets or subscription mutations. Failed handlers roll back the claim.
    """
    from sqlalchemy.exc import IntegrityError

    data = event if isinstance(event, dict) else dict(event)
    event_type = data.get("type") or ""
    event_id = _event_id(data)
    obj = (data.get("data") or {}).get("object") or {}

    if event_id and _already_processed(db, event_id):
        logger.info("Skipping duplicate Stripe event %s (%s)", event_id, event_type)
        _stripe_metric("duplicate")
        return f"duplicate:{event_type}"

    # Claim first (unique stripe_event_id). Organization filled after resolve.
    if event_id:
        try:
            _mark_processed(db, event_id, event_type, None)
            db.flush()
        except IntegrityError:
            db.rollback()
            logger.info("Race duplicate Stripe event %s (%s)", event_id, event_type)
            _stripe_metric("duplicate")
            return f"duplicate:{event_type}"

    org_id: UUID | None = None
    try:
        if event_type == "checkout.session.completed":
            org_id = handle_checkout_session_completed(db, obj)
        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            org_id = handle_subscription_event(db, obj)
        elif event_type == "invoice.payment_failed":
            org_id = handle_invoice_payment_failed(db, obj)
        elif event_type == "invoice.paid":
            org_id = handle_invoice_paid(db, obj)
        else:
            logger.debug("Ignoring unhandled Stripe event type: %s", event_type)
            db.commit()
            _stripe_metric("ignored")
            return f"ignored:{event_type}"

        if event_id and org_id is not None:
            row = db.scalar(
                select(StripeEvent).where(StripeEvent.stripe_event_id == event_id)
            )
            if row is not None:
                row.organization_id = org_id
        db.commit()
        _stripe_metric("ok")
    except Exception:
        db.rollback()
        _stripe_metric("error")
        raise

    return event_type


def _stripe_metric(result: str) -> None:
    try:
        from app.core.telemetry import STRIPE_WEBHOOK_TOTAL

        if STRIPE_WEBHOOK_TOTAL is not None:
            STRIPE_WEBHOOK_TOTAL.labels(result).inc()
    except Exception:  # noqa: BLE001
        pass
