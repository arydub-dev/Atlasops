"""Stripe webhook: tenant RLS context + event idempotency."""
from __future__ import annotations

from uuid import uuid4

import pytest
import stripe
from app.core.config import settings

from sqlalchemy import select

from app.billing.webhooks import dispatch_stripe_event
from app.models import BillingAccount, StripeEvent
from app.models.enums import BillingPlan, OrgStatus, SubscriptionStatus
from app.tenancy.rls import set_session_org


@pytest.fixture(autouse=True)
def stripe_subscription_api(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_contract")
    def retrieve(sub_id):
        customer = sub_id.removeprefix("sub_")
        return {"id": sub_id, "customer": customer, "status": "active",
                "latest_invoice": f"in_{customer}", "items": {"data": []}}
    monkeypatch.setattr(stripe.Subscription, "retrieve", retrieve)


def _checkout_event(org_id, event_id: str = "evt_test_checkout_1"):
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "customer": "cus_test_1",
                "subscription": None,
                "client_reference_id": str(org_id),
                "metadata": {"organization_id": str(org_id), "plan": "starter"},
            }
        },
    }


def _invoice_paid_event(customer_id: str, event_id: str, *, reset: bool = True):
    return {
        "id": event_id,
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": f"in_{customer_id}",
                "subscription": f"sub_{customer_id}",
                "customer": customer_id,
                "billing_reason": "subscription_cycle" if reset else "manual",
            }
        },
    }


def test_checkout_webhook_sets_billing_and_is_idempotent(db, org_a):
    org, _ = org_a
    event = _checkout_event(org.id, "evt_checkout_once")

    first = dispatch_stripe_event(db, event)
    assert first == "checkout.session.completed"

    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    assert account is not None
    assert account.stripe_customer_id == "cus_test_1"
    assert account.plan == BillingPlan.TRIAL  # metadata alone cannot grant a paid plan

    rows = db.scalars(select(StripeEvent)).all()
    assert len(rows) == 1
    assert rows[0].stripe_event_id == "evt_checkout_once"
    assert rows[0].organization_id == org.id

    # Replay must not create a second stripe_events row or mutate plan unexpectedly
    account.plan = BillingPlan.PROFESSIONAL
    db.commit()

    second = dispatch_stripe_event(db, event)
    assert second.startswith("duplicate:")
    assert db.scalar(select(StripeEvent).where(StripeEvent.stripe_event_id == "evt_checkout_once"))
    set_session_org(db, org.id)
    account2 = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    assert account2.plan == BillingPlan.PROFESSIONAL  # unchanged by duplicate


def test_invoice_paid_credit_reset_idempotent(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    assert account is not None
    account.stripe_customer_id = f"cus_{uuid4().hex[:10]}"
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    account.ai_credits_used = 42
    account.status = SubscriptionStatus.ACTIVE
    org.status = OrgStatus.ACTIVE
    db.commit()

    # Production webhook sessions have no tenant GUC.
    db.info.pop("rls_organization_id", None)

    event = _invoice_paid_event(account.stripe_customer_id, "evt_invoice_paid_1")
    assert dispatch_stripe_event(db, event) == "invoice.paid"
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 0

    account.ai_credits_used = 7
    db.commit()
    db.info.pop("rls_organization_id", None)

    assert dispatch_stripe_event(db, event).startswith("duplicate:")
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 7  # not reset again


def test_invoice_paid_resolves_org_via_customer_id(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    account.stripe_customer_id = "cus_lookup_me"
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    account.status = SubscriptionStatus.PAST_DUE
    org.status = OrgStatus.PAST_DUE
    db.commit()
    db.info.pop("rls_organization_id", None)

    event = _invoice_paid_event("cus_lookup_me", "evt_invoice_paid_lookup", reset=True)
    assert dispatch_stripe_event(db, event) == "invoice.paid"
    set_session_org(db, org.id)
    db.refresh(account)
    db.refresh(org)
    assert account.status == SubscriptionStatus.ACTIVE
    assert org.status == OrgStatus.ACTIVE


def test_checkout_metadata_does_not_activate_unpaid_subscription(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.status = SubscriptionStatus.PAST_DUE
    org.status = OrgStatus.PAST_DUE
    db.commit()
    event = _checkout_event(org.id, "evt_unpaid_checkout")
    event["data"]["object"]["metadata"]["plan"] = "enterprise"
    dispatch_stripe_event(db, event)
    set_session_org(db, org.id)
    db.refresh(account)
    db.refresh(org)
    assert account.status == SubscriptionStatus.PAST_DUE
    assert org.status == OrgStatus.PAST_DUE
    assert account.plan != BillingPlan.ENTERPRISE


def test_checkout_customer_mapping_overrides_conflicting_metadata(db, org_a, org_b):
    org, _ = org_a
    other, _, _ = org_b
    set_session_org(db, org.id)
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.stripe_customer_id = "cus_test_1"
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    db.commit()
    event = _checkout_event(other.id, "evt_conflicting_checkout")
    dispatch_stripe_event(db, event)
    row = db.scalar(select(StripeEvent).where(StripeEvent.stripe_event_id == "evt_conflicting_checkout"))
    assert row.organization_id == org.id
    set_session_org(db, other.id)
    other_account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == other.id))
    assert other_account.stripe_customer_id != "cus_test_1"


def test_manual_invoice_cannot_reactivate_subscription(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.stripe_customer_id = "cus_manual"
    account.status = SubscriptionStatus.PAST_DUE
    org.status = OrgStatus.PAST_DUE
    db.commit()
    event = _invoice_paid_event("cus_manual", "evt_manual", reset=False)
    event["data"]["object"].pop("subscription")
    dispatch_stripe_event(db, event)
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.status == SubscriptionStatus.PAST_DUE


def test_delayed_and_duplicate_invoice_cannot_reset_current_usage(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.stripe_customer_id = "cus_period"
    account.stripe_subscription_id = "sub_cus_period"
    account.ai_credits_used = 23
    db.commit()
    old = _invoice_paid_event("cus_period", "evt_old")
    old["data"]["object"]["id"] = "in_old_period"
    dispatch_stripe_event(db, old)
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 23
    dispatch_stripe_event(db, _invoice_paid_event("cus_period", "evt_current"))
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 0
    account.ai_credits_used = 5
    db.commit()
    dispatch_stripe_event(db, _invoice_paid_event("cus_period", "evt_same_invoice_different_id"))
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 5


def test_checkout_verification_failure_is_retryable(db, org_a, monkeypatch):
    org, _ = org_a
    event = _checkout_event(org.id, "evt_retryable")
    event["data"]["object"]["subscription"] = "sub_cus_test_1"
    def unavailable(_):
        raise RuntimeError("Provider unavailable")
    monkeypatch.setattr(stripe.Subscription, "retrieve", unavailable)
    with pytest.raises(RuntimeError):
        dispatch_stripe_event(db, event)
    assert db.scalar(select(StripeEvent).where(StripeEvent.stripe_event_id == "evt_retryable")) is None


def test_stale_subscription_event_uses_current_provider_status(db, org_a, monkeypatch):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.stripe_customer_id = "cus_stale"
    account.stripe_subscription_id = "sub_cus_stale"
    db.commit()
    monkeypatch.setattr(stripe.Subscription, "retrieve", lambda _: {
        "id": "sub_cus_stale", "customer": "cus_stale", "status": "canceled", "items": {"data": []}})
    dispatch_stripe_event(db, {"id": "evt_stale", "type": "customer.subscription.updated",
                              "data": {"object": {"id": "sub_cus_stale", "customer": "cus_stale", "status": "active"}}})
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.status == SubscriptionStatus.CANCELED


def test_verified_checkout_activates_paid_plan(db, org_a, monkeypatch):
    org, _ = org_a
    monkeypatch.setattr(settings, 'STRIPE_PRICE_STARTER_MONTHLY', 'price_starter')
    monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda _: {
        'id': 'sub_verified', 'customer': 'cus_test_1', 'status': 'active',
        'items': {'data': [{'price': {'id': 'price_starter', 'recurring': {'interval': 'month'}}, 'quantity': 1}]}})
    event = _checkout_event(org.id, 'evt_verified_checkout')
    event['data']['object']['subscription'] = 'sub_verified'
    dispatch_stripe_event(db, event)
    set_session_org(db, org.id)
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    assert account.status == SubscriptionStatus.ACTIVE
    assert account.plan == BillingPlan.STARTER
    assert account.stripe_subscription_id == 'sub_verified'


def test_checkout_rejects_subscription_from_another_customer(db, org_a, monkeypatch):
    org, _ = org_a
    monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda _: {
        'id': 'sub_wrong', 'customer': 'cus_other', 'status': 'active'})
    event = _checkout_event(org.id, 'evt_wrong_customer')
    event['data']['object']['subscription'] = 'sub_wrong'
    with pytest.raises(ValueError, match='customer mismatch'):
        dispatch_stripe_event(db, event)
    assert db.scalar(select(StripeEvent).where(StripeEvent.stripe_event_id == 'evt_wrong_customer')) is None
