from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.config import settings
from app.models import BillingAccount
from app.models.enums import SubscriptionStatus, OrgStatus


def test_expired_trial_blocks_operations_but_allows_billing(owner_client, db, org_a, monkeypatch):
    org, _ = org_a
    org.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    monkeypatch.setattr(settings, 'FEATURE_BILLING_ENFORCE', True)
    assert owner_client.get('/api/v1/shipments').status_code == 402
    assert owner_client.get('/api/v1/billing/usage').status_code == 200


def test_active_subscription_and_failed_payment(owner_client, db, org_a, monkeypatch):
    org, _ = org_a
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.status = SubscriptionStatus.ACTIVE; db.commit()
    monkeypatch.setattr(settings, 'FEATURE_BILLING_ENFORCE', True)
    assert owner_client.get('/api/v1/shipments').status_code == 200
    account.status = SubscriptionStatus.PAST_DUE; db.commit()
    assert owner_client.get('/api/v1/shipments').status_code == 402
    org.status = OrgStatus.SUSPENDED; db.commit()
    assert owner_client.get('/api/v1/shipments').status_code == 403
    assert owner_client.get('/api/v1/billing/usage').status_code == 200


def test_concurrent_ai_quota_is_serialized(db, org_a, monkeypatch):
    import pytest
    from concurrent.futures import ThreadPoolExecutor
    from app.core.database import engine, SessionLocal
    from app.tenancy.rls import set_session_org
    from app.billing.enforce import enforce_ai_credits, PlanLimitExceeded
    if engine.dialect.name != 'postgresql':
        pytest.skip('Row-lock concurrency requires PostgreSQL')
    org, _ = org_a
    account = db.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
    account.ai_credits_included = 1; account.ai_credits_used = 0; db.commit()
    monkeypatch.setattr(settings, 'FEATURE_BILLING_ENFORCE', True)
    def consume():
        with SessionLocal() as session:
            set_session_org(session, org.id)
            try:
                enforce_ai_credits(session, org.id)
                row = session.scalar(select(BillingAccount).where(BillingAccount.organization_id == org.id))
                row.ai_credits_used += 1
                session.commit()
                return True
            except PlanLimitExceeded:
                session.rollback()
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert sorted(results) == [False, True]


def test_trial_cannot_create_paid_api_tokens(owner_client, monkeypatch):
    monkeypatch.setattr(settings, 'FEATURE_BILLING_ENFORCE', True)
    response = owner_client.post('/api/v1/orgs/current/tokens', json={'name':'not-in-trial'})
    assert response.status_code == 403
