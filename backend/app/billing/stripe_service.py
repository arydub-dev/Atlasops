"""Stripe customer, checkout, portal, and subscription sync."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.plans import PLAN_CATALOG, get_plan
from app.core.config import settings
from app.models import BillingAccount, Organization, UsageRecord
from app.models.enums import (
    BillingInterval,
    BillingPlan,
    OrgStatus,
    SubscriptionStatus,
)


class StripeNotConfigured(RuntimeError):
    """Raised when STRIPE_SECRET_KEY is empty and a Stripe API call is required."""

    def __init__(self, action: str = "Stripe API call") -> None:
        super().__init__(
            f"{action} requires STRIPE_SECRET_KEY. Set it in the environment to enable billing."
        )


def _require_stripe(action: str = "Stripe API call") -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise StripeNotConfigured(action)
    stripe.api_key = settings.STRIPE_SECRET_KEY


def validate_frontend_url(url: str) -> str:
    """Allow only URLs under FRONTEND_URL (open-redirect protection).

    Raises ValueError when the URL is absolute and does not share the configured
    frontend origin. Relative paths are resolved against FRONTEND_URL.
    """
    from urllib.parse import urljoin, urlparse

    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required")

    base = settings.FRONTEND_URL.rstrip("/") + "/"
    absolute = urljoin(base, raw)
    base_parts = urlparse(settings.FRONTEND_URL)
    abs_parts = urlparse(absolute)

    if abs_parts.scheme not in {"http", "https"}:
        raise ValueError("URL must be http(s)")
    if abs_parts.netloc.lower() != (base_parts.netloc or "").lower():
        raise ValueError("URL must stay on the configured FRONTEND_URL origin")
    return absolute


def _price_id_for(plan: BillingPlan, interval: BillingInterval) -> str:
    definition = get_plan(plan)
    env_key = (
        definition.stripe_price_env_monthly
        if interval == BillingInterval.MONTHLY
        else definition.stripe_price_env_annual
    )
    if not env_key:
        raise ValueError(f"No Stripe price configured for {plan.value}/{interval.value}")
    price_id = getattr(settings, env_key, "") or ""
    if not price_id:
        raise ValueError(f"Environment variable {env_key} is not set")
    return price_id


def _plan_from_price_id(price_id: str | None) -> BillingPlan | None:
    if not price_id:
        return None
    mapping = {
        settings.STRIPE_PRICE_STARTER_MONTHLY: BillingPlan.STARTER,
        settings.STRIPE_PRICE_STARTER_ANNUAL: BillingPlan.STARTER,
        settings.STRIPE_PRICE_PROFESSIONAL_MONTHLY: BillingPlan.PROFESSIONAL,
        settings.STRIPE_PRICE_PROFESSIONAL_ANNUAL: BillingPlan.PROFESSIONAL,
        settings.STRIPE_PRICE_ENTERPRISE_MONTHLY: BillingPlan.ENTERPRISE,
    }
    return mapping.get(price_id)


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def get_or_create_billing_account(db: Session, organization_id: UUID) -> BillingAccount:
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == organization_id)
    )
    if account:
        return account
    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found")
    plan_def = get_plan(org.plan)
    account = BillingAccount(
        organization_id=organization_id,
        plan=org.plan,
        status=SubscriptionStatus.TRIALING,
        seat_quantity=1,
        ai_credits_included=plan_def.ai_credits_monthly,
    )
    db.add(account)
    db.flush()
    return account


def create_customer(
    db: Session,
    *,
    organization: Organization,
    email: str,
    name: str | None = None,
) -> BillingAccount:
    """Create a Stripe Customer and persist the id on BillingAccount."""
    _require_stripe("create_customer")
    account = get_or_create_billing_account(db, organization.id)
    if account.stripe_customer_id:
        return account

    customer = stripe.Customer.create(
        email=email,
        name=name or organization.name,
        metadata={
            "organization_id": str(organization.id),
            "organization_slug": organization.slug,
        },
    )
    account.stripe_customer_id = customer["id"]
    db.flush()
    return account


def create_checkout_session(
    db: Session,
    *,
    organization: Organization,
    plan: BillingPlan,
    interval: BillingInterval = BillingInterval.MONTHLY,
    customer_email: str,
    success_url: str,
    cancel_url: str,
    seat_quantity: int = 1,
) -> dict[str, Any]:
    """Create a Stripe Checkout Session for a subscription."""
    _require_stripe("create_checkout_session")
    if plan == BillingPlan.TRIAL:
        raise ValueError("Cannot checkout the trial plan")

    success_url = validate_frontend_url(success_url)
    cancel_url = validate_frontend_url(cancel_url)

    account = create_customer(db, organization=organization, email=customer_email)
    price_id = _price_id_for(plan, interval)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=account.stripe_customer_id,
        line_items=[{"price": price_id, "quantity": max(1, seat_quantity)}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(organization.id),
        metadata={
            "organization_id": str(organization.id),
            "plan": plan.value,
            "interval": interval.value,
        },
        subscription_data={
            "metadata": {
                "organization_id": str(organization.id),
                "plan": plan.value,
            }
        },
        allow_promotion_codes=True,
    )
    return {"id": session["id"], "url": session["url"]}


def create_billing_portal_session(
    db: Session,
    *,
    organization_id: UUID,
    return_url: str,
) -> dict[str, Any]:
    _require_stripe("create_billing_portal_session")
    return_url = validate_frontend_url(return_url)
    account = get_or_create_billing_account(db, organization_id)
    if not account.stripe_customer_id:
        raise ValueError("Organization has no Stripe customer yet")
    portal = stripe.billing_portal.Session.create(
        customer=account.stripe_customer_id,
        return_url=return_url,
    )
    return {"url": portal["url"]}


def _map_subscription_status(raw: str | None) -> SubscriptionStatus:
    mapping = {
        "trialing": SubscriptionStatus.TRIALING,
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "unpaid": SubscriptionStatus.UNPAID,
    }
    return mapping.get((raw or "").lower(), SubscriptionStatus.INCOMPLETE)


def sync_subscription_from_stripe(
    db: Session,
    subscription: dict[str, Any] | Any,
    *,
    organization_id: UUID | None = None,
) -> BillingAccount | None:
    """Upsert BillingAccount + Organization.plan from a Stripe Subscription object."""
    data = subscription if isinstance(subscription, dict) else dict(subscription)
    sub_id = data.get("id")
    customer_id = data.get("customer")
    meta = data.get("metadata") or {}

    org_id = organization_id
    if org_id is None and meta.get("organization_id"):
        org_id = UUID(str(meta["organization_id"]))

    account: BillingAccount | None = None
    if org_id:
        account = db.scalar(
            select(BillingAccount).where(BillingAccount.organization_id == org_id)
        )
    if account is None and customer_id:
        account = db.scalar(
            select(BillingAccount).where(BillingAccount.stripe_customer_id == customer_id)
        )
    if account is None and sub_id:
        account = db.scalar(
            select(BillingAccount).where(BillingAccount.stripe_subscription_id == sub_id)
        )
    if account is None:
        return None

    items = (data.get("items") or {}).get("data") or []
    price_id = None
    quantity = account.seat_quantity
    if items:
        first = items[0]
        price = first.get("price") or {}
        price_id = price.get("id") if isinstance(price, dict) else None
        quantity = int(first.get("quantity") or quantity)

    plan = _plan_from_price_id(price_id)
    if plan is None and meta.get("plan"):
        try:
            plan = BillingPlan(meta["plan"])
        except ValueError:
            plan = account.plan
    if plan is None:
        plan = account.plan

    interval = BillingInterval.MONTHLY
    if items:
        price = items[0].get("price") or {}
        recurring = price.get("recurring") or {} if isinstance(price, dict) else {}
        if recurring.get("interval") == "year":
            interval = BillingInterval.ANNUAL

    account.stripe_subscription_id = sub_id
    if customer_id:
        account.stripe_customer_id = customer_id
    account.plan = plan
    account.interval = interval
    account.status = _map_subscription_status(data.get("status"))
    account.seat_quantity = quantity
    account.ai_credits_included = get_plan(plan).ai_credits_monthly
    account.current_period_end = _ts_to_dt(data.get("current_period_end"))
    account.cancel_at_period_end = bool(data.get("cancel_at_period_end"))

    org = db.get(Organization, account.organization_id)
    if org:
        org.plan = plan
        if account.status == SubscriptionStatus.ACTIVE:
            org.status = OrgStatus.ACTIVE
        elif account.status == SubscriptionStatus.PAST_DUE:
            org.status = OrgStatus.PAST_DUE
        elif account.status == SubscriptionStatus.CANCELED:
            org.status = OrgStatus.SUSPENDED
        elif account.status == SubscriptionStatus.TRIALING:
            org.status = OrgStatus.TRIALING

    db.flush()
    return account


def cancel_subscription(
    db: Session,
    *,
    organization_id: UUID,
    at_period_end: bool = True,
) -> BillingAccount:
    _require_stripe("cancel_subscription")
    account = get_or_create_billing_account(db, organization_id)
    if not account.stripe_subscription_id:
        raise ValueError("No active Stripe subscription")
    if at_period_end:
        sub = stripe.Subscription.modify(
            account.stripe_subscription_id, cancel_at_period_end=True
        )
    else:
        sub = stripe.Subscription.cancel(account.stripe_subscription_id)
    synced = sync_subscription_from_stripe(db, sub, organization_id=organization_id)
    return synced or account


def report_ai_credit_usage(
    db: Session,
    *,
    organization_id: UUID,
    quantity: int = 1,
    meta: dict | None = None,
) -> UsageRecord:
    """Record AI credit usage locally and report metered usage to Stripe when configured."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    account = get_or_create_billing_account(db, organization_id)
    account.ai_credits_used = int(account.ai_credits_used or 0) + quantity

    record = UsageRecord(
        organization_id=organization_id,
        metric="ai",
        quantity=float(quantity),
        meta=meta or {},
    )
    db.add(record)

    # Metered billing via Stripe usage records when price + customer exist.
    if settings.STRIPE_SECRET_KEY and settings.STRIPE_PRICE_AI_CREDIT and account.stripe_subscription_id:
        _require_stripe("report_ai_credit_usage")
        try:
            sub = stripe.Subscription.retrieve(account.stripe_subscription_id)
            items = (sub.get("items") or {}).get("data") or []
            meter_item_id = None
            for item in items:
                price = item.get("price") or {}
                if price.get("id") == settings.STRIPE_PRICE_AI_CREDIT:
                    meter_item_id = item.get("id")
                    break
            if meter_item_id:
                stripe.SubscriptionItem.create_usage_record(
                    meter_item_id,
                    quantity=quantity,
                    action="increment",
                )
        except stripe.error.StripeError:
            # Local usage is authoritative; Stripe meter sync is best-effort.
            pass

    db.flush()
    return record


def reset_ai_credits_for_period(db: Session, account: BillingAccount) -> None:
    """Reset used credits at period boundary (called from invoice.paid)."""
    plan_def = PLAN_CATALOG.get(account.plan) or get_plan(BillingPlan.TRIAL)
    account.ai_credits_used = 0
    account.ai_credits_included = plan_def.ai_credits_monthly
    db.flush()
