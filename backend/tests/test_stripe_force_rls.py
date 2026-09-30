"""Postgres FORCE RLS Stripe webhook integration — app role, no BYPASSRLS.

Requires SUPPLY_CI_POSTGRES=1 and alembic >= 0013_stripe_customer_index.
Simulates production webhooks: empty tenant GUC on the request session.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
import stripe
from sqlalchemy import select, text

from app.billing.webhooks import (
    _lookup_org_id_by_customer,
    construct_event,
    dispatch_stripe_event,
)
from app.core.config import settings
from app.core.database import engine
from app.models import BillingAccount, Organization, StripeEvent
from app.models.enums import BillingPlan, OrgStatus, SubscriptionStatus
from app.tenancy.rls import ORG_GUC, set_session_org


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


pytestmark = [
    pytest.mark.skipif(
        os.environ.get("SUPPLY_CI_POSTGRES") != "1" or not _is_postgres(),
        reason="Stripe FORCE RLS tests require SUPPLY_CI_POSTGRES=1",
    ),
]


def _clear_tenant_context(db) -> None:
    """Match production webhook sessions: no org GUC, no session.info binding."""
    db.info.pop("rls_organization_id", None)
    db.execute(text("SELECT set_config(:k, '', true)"), {"k": ORG_GUC})
    db.expire_all()


def _assert_app_role_has_no_bypassrls(db) -> None:
    row = db.execute(
        text("SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user")
    ).one()
    assert row[0] is False, "application role must not have BYPASSRLS"
    assert row[1] is False, "application role must not be superuser"


@pytest.fixture(autouse=True)
def stripe_subscription_api(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_contract")
    def retrieve(sub_id):
        customer = sub_id.removeprefix("sub_")
        return {"id": sub_id, "customer": customer, "status": "active",
                "latest_invoice": f"in_{customer}", "items": {"data": []}}
    monkeypatch.setattr(stripe.Subscription, "retrieve", retrieve)


def _checkout_event(org_id, *, event_id: str, customer: str, plan: str = "starter"):
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{event_id}",
                "customer": customer,
                "subscription": None,
                "client_reference_id": str(org_id),
                "metadata": {"organization_id": str(org_id), "plan": plan},
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


def _subscription_updated_event(customer_id: str, event_id: str, *, status: str = "active"):
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": f"sub_{event_id}",
                "customer": customer_id,
                "status": status,
                "cancel_at_period_end": False,
                "current_period_end": None,
                "items": {"data": []},
                "metadata": {},
            }
        },
    }


def test_app_role_cannot_disable_row_security(db):
    _assert_app_role_has_no_bypassrls(db)
    with pytest.raises(Exception):
        db.execute(text("SET LOCAL row_security = off"))
        db.execute(text("SELECT count(*) FROM billing_accounts")).scalar()
    db.rollback()


def test_lookup_function_works_without_tenant_guc(db, org_a):
    """Index + SECURITY DEFINER must resolve customer with empty GUC."""
    org, _ = org_a
    _assert_app_role_has_no_bypassrls(db)
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    assert account is not None
    cust = f"cus_idx_{uuid4().hex[:10]}"
    account.stripe_customer_id = cust
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    db.commit()

    _clear_tenant_context(db)
    assert (
        db.execute(text("SELECT current_setting(:k, true)"), {"k": ORG_GUC}).scalar()
        in ("", None)
    )
    direct = db.execute(
        text("SELECT count(*) FROM billing_accounts WHERE stripe_customer_id = :c"),
        {"c": cust},
    ).scalar()
    assert direct == 0  # FORCE RLS hides tenant rows

    found = _lookup_org_id_by_customer(db, cust)
    assert found == org.id

    assert _lookup_org_id_by_customer(db, "cus_does_not_exist") is None
    assert _lookup_org_id_by_customer(db, "") is None


def test_invoice_paid_entitlement_update_without_guc(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    cust = f"cus_paid_{uuid4().hex[:10]}"
    account.stripe_customer_id = cust
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    account.status = SubscriptionStatus.PAST_DUE
    account.ai_credits_used = 55
    org.status = OrgStatus.PAST_DUE
    db.commit()

    _clear_tenant_context(db)
    event = _invoice_paid_event(cust, f"evt_paid_{uuid4().hex[:8]}", reset=True)
    assert dispatch_stripe_event(db, event) == "invoice.paid"

    set_session_org(db, org.id)
    db.refresh(account)
    db.refresh(org)
    assert account.status == SubscriptionStatus.ACTIVE
    assert org.status == OrgStatus.ACTIVE
    assert account.ai_credits_used == 0


def test_invoice_paid_duplicate_is_idempotent(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    cust = f"cus_dup_{uuid4().hex[:10]}"
    account.stripe_customer_id = cust
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    account.ai_credits_used = 9
    account.status = SubscriptionStatus.ACTIVE
    db.commit()

    event_id = f"evt_dup_{uuid4().hex[:8]}"
    event = _invoice_paid_event(cust, event_id, reset=True)

    _clear_tenant_context(db)
    assert dispatch_stripe_event(db, event) == "invoice.paid"
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 0

    account.ai_credits_used = 3
    db.commit()
    _clear_tenant_context(db)
    assert dispatch_stripe_event(db, event).startswith("duplicate:")
    set_session_org(db, org.id)
    db.refresh(account)
    assert account.ai_credits_used == 3
    assert (
        db.scalar(select(StripeEvent).where(StripeEvent.stripe_event_id == event_id))
        is not None
    )


def test_invoice_paid_unknown_customer_no_tenant_mutation(db, org_a):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    account.status = SubscriptionStatus.PAST_DUE
    account.ai_credits_used = 12
    org.status = OrgStatus.PAST_DUE
    db.commit()

    _clear_tenant_context(db)
    event = _invoice_paid_event(
        "cus_unknown_zzzz", f"evt_unknown_{uuid4().hex[:8]}", reset=True
    )
    # Handler returns event type even when org cannot be resolved; no entitlement change.
    assert dispatch_stripe_event(db, event) == "invoice.paid"

    set_session_org(db, org.id)
    db.refresh(account)
    db.refresh(org)
    assert account.status == SubscriptionStatus.PAST_DUE
    assert org.status == OrgStatus.PAST_DUE
    assert account.ai_credits_used == 12


def test_checkout_then_invoice_paid_full_path(db, org_a):
    org, _ = org_a
    cust = f"cus_flow_{uuid4().hex[:10]}"
    _clear_tenant_context(db)
    checkout = _checkout_event(
        org.id, event_id=f"evt_cs_{uuid4().hex[:8]}", customer=cust, plan="professional"
    )
    assert dispatch_stripe_event(db, checkout) == "checkout.session.completed"

    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    assert account.stripe_customer_id == cust
    assert account.plan == BillingPlan.TRIAL  # no verified subscription yet

    account.status = SubscriptionStatus.PAST_DUE
    org.status = OrgStatus.PAST_DUE
    account.stripe_subscription_id = f"sub_{cust}"
    account.ai_credits_used = 4
    db.commit()

    _clear_tenant_context(db)
    paid = _invoice_paid_event(cust, f"evt_flow_paid_{uuid4().hex[:8]}", reset=True)
    assert dispatch_stripe_event(db, paid) == "invoice.paid"
    set_session_org(db, org.id)
    db.refresh(account)
    db.refresh(org)
    assert account.status == SubscriptionStatus.ACTIVE
    assert org.status == OrgStatus.ACTIVE
    assert account.ai_credits_used == 0


def test_subscription_update_via_customer_lookup(db, org_a, monkeypatch):
    org, _ = org_a
    set_session_org(db, org.id)
    account = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == org.id)
    )
    cust = f"cus_sub_{uuid4().hex[:10]}"
    account.stripe_customer_id = cust
    account.stripe_subscription_id = f"sub_{account.stripe_customer_id}"
    account.stripe_subscription_id = "sub_existing"
    account.status = SubscriptionStatus.ACTIVE
    db.commit()

    # Avoid live Stripe API; sync path uses metadata/status from event object.
    def _fake_sync(db_sess, subscription, organization_id=None):
        set_session_org(db_sess, organization_id)
        acct = db_sess.scalar(
            select(BillingAccount).where(BillingAccount.organization_id == organization_id)
        )
        assert acct is not None
        status = (subscription.get("status") or "").lower()
        if status == "canceled":
            acct.status = SubscriptionStatus.CANCELED
            o = db_sess.get(Organization, organization_id)
            if o:
                o.status = OrgStatus.SUSPENDED
        db_sess.flush()
        return acct

    monkeypatch.setattr(
        "app.billing.webhooks.sync_subscription_from_stripe", _fake_sync
    )

    _clear_tenant_context(db)
    event = _subscription_updated_event(
        cust, f"evt_sub_{uuid4().hex[:8]}", status="canceled"
    )
    event["data"]["object"]["id"] = "sub_existing"
    monkeypatch.setattr(stripe.Subscription, "retrieve", lambda _: event["data"]["object"])
    assert dispatch_stripe_event(db, event) == "customer.subscription.updated"

    set_session_org(db, org.id)
    db.refresh(account)
    db.refresh(org)
    assert account.status == SubscriptionStatus.CANCELED
    assert org.status == OrgStatus.SUSPENDED


def test_webhook_signature_verification(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_rc3")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_rc3")

    payload = b'{"id":"evt_sig","type":"invoice.paid","data":{"object":{}}}'
    with pytest.raises(ValueError, match="Missing Stripe-Signature"):
        construct_event(payload, None)

    with pytest.raises(stripe.error.SignatureVerificationError):
        construct_event(payload, "t=1,v1=deadbeef")

    # Valid signature for the configured secret
    sig = stripe.WebhookSignature._compute_signature(
        f"{int(__import__('time').time())}.{payload.decode('utf-8')}",
        settings.STRIPE_WEBHOOK_SECRET,
    )
    # stripe.Webhook.construct_event expects Stripe-Signature header format
    import time

    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    digest = stripe.WebhookSignature._compute_signature(
        signed_payload, settings.STRIPE_WEBHOOK_SECRET
    )
    header = f"t={timestamp},v1={digest}"
    event = construct_event(payload, header)
    assert event["id"] == "evt_sig"
