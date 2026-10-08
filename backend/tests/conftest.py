"""Pytest fixtures: SQLite DB, org+user+membership, session cookies, tenant context."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Must set before app imports settings / engine.
# CI Postgres job sets SUPPLY_CI_POSTGRES=1 and DATABASE_URL to Postgres.
if os.environ.get("SUPPLY_CI_POSTGRES") != "1":
    os.environ["DATABASE_URL"] = "sqlite:///./_test_supply_v2.db"
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:1/0")
os.environ.setdefault("SEED_ON_STARTUP", "false")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-min-32-characters!!")
os.environ.setdefault("CREDENTIALS_ENCRYPTION_KEY", "")
os.environ.setdefault("WORKOS_API_KEY", "")
os.environ.setdefault("WORKOS_CLIENT_ID", "")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("FEATURE_BILLING_ENFORCE", "false")
os.environ.setdefault("CONNECTOR_SYNC_INLINE", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.identity.orgs import create_organization
from app.identity.sessions import create_session
from app.main import app
from app.models import Membership, Organization, Shipment, User
from app.models.enums import MembershipStatus, ShipmentStatus
from app.rbac.permissions import permissions_for_role
from app.tenancy.context import TenantContext, reset_tenant, set_tenant
from app.tenancy.rls import set_session_org

get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _db_schema():
    if os.environ.get("SUPPLY_CI_POSTGRES") == "1":
        # Schema + RLS come from `alembic upgrade head` in CI.
        yield
        return
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("_test_supply_v2.db"):
        os.remove("_test_supply_v2.db")


@pytest.fixture(autouse=True)
def _clean_tables(monkeypatch):
    """Wipe rows between tests so unique emails/slugs do not collide."""
    from app.core.rate_limit import reset_rate_limiter

    # Shared TestClient IP would otherwise trip in-memory rate limits mid-suite.
    reset_rate_limiter()
    # Each test has its own clients. Isolate their Redis counters just as the
    # in-memory counters are reset; preserve limits and expiry enforcement.
    from app.core import rate_limit
    original_check = rate_limit._check
    namespace = uuid4().hex
    def isolated_check(key, *args, **kwargs):
        return original_check(f"test:{namespace}:{key}", *args, **kwargs)
    monkeypatch.setattr(rate_limit, "_check", isolated_check)
    yield
    session = SessionLocal()
    try:
        if engine.dialect.name == "postgresql":
            # Table owners under FORCE RLS cannot SET row_security=off.
            # Truncate is permitted for owners and is not filtered by RLS policies.
            tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            if tables:
                session.execute(
                    __import__("sqlalchemy").text(
                        f"TRUNCATE {tables} RESTART IDENTITY CASCADE"
                    )
                )
        else:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _make_user(db: Session, email: str, full_name: str = "Test User") -> User:
    user = User(email=email.lower(), full_name=full_name, is_active=True)
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def owner_user(db: Session) -> User:
    return _make_user(db, f"owner-{uuid4().hex[:8]}@example.com", "Owner User")


@pytest.fixture()
def org_a(db: Session, owner_user: User) -> tuple[Organization, Membership]:
    org, membership = create_organization(
        db, name=f"Org Alpha {uuid4().hex[:6]}", owner=owner_user
    )
    db.commit()
    return org, membership


@pytest.fixture()
def org_b(db: Session) -> tuple[Organization, Membership, User]:
    user = _make_user(db, f"owner-b-{uuid4().hex[:8]}@example.com", "Owner B")
    org, membership = create_organization(
        db, name=f"Org Beta {uuid4().hex[:6]}", owner=user
    )
    db.commit()
    return org, membership, user


@pytest.fixture()
def viewer_user(db: Session, org_a: tuple[Organization, Membership]) -> User:
    org, _ = org_a
    user = _make_user(db, f"viewer-{uuid4().hex[:8]}@example.com", "Viewer User")
    db.add(
        Membership(
            organization_id=org.id,
            user_id=user.id,
            role_slug="viewer",
            status=MembershipStatus.ACTIVE,
        )
    )
    db.commit()
    return user


def _session_client(client: TestClient, db: Session, user: User, org: Organization) -> TestClient:
    """Attach a real session cookie for the user/org."""
    _session, raw = create_session(db, user=user, organization_id=org.id)
    db.commit()
    client.cookies.set(get_settings().SESSION_COOKIE_NAME, raw)
    return client


@pytest.fixture()
def owner_client(client: TestClient, db: Session, owner_user: User, org_a):
    org, _ = org_a
    return _session_client(client, db, owner_user, org)


@pytest.fixture()
def viewer_client(client: TestClient, db: Session, viewer_user: User, org_a):
    org, _ = org_a
    return _session_client(client, db, viewer_user, org)


@pytest.fixture()
def org_b_client(client: TestClient, db: Session, org_b):
    org, _membership, user = org_b
    return _session_client(client, db, user, org)


@pytest.fixture()
def shipment_a(db: Session, org_a) -> Shipment:
    org, _ = org_a
    now = datetime.now(timezone.utc)
    set_session_org(db, org.id)
    s = Shipment(
        id=uuid4(),
        organization_id=org.id,
        reference=f"ORG-A-{uuid4().hex[:6]}",
        origin="Shanghai",
        destination="Los Angeles",
        carrier="Maersk",
        current_location="Pacific",
        status=ShipmentStatus.IN_TRANSIT,
        delay_risk_score=10.0,
        units=100,
        value_usd=5000.0,
        shipped_at=now - timedelta(days=3),
        eta=now + timedelta(days=7),
    )
    db.add(s)
    db.commit()
    # Re-bind tenant GUC after commit (SET LOCAL ends) so refresh can see the row.
    set_session_org(db, org.id)
    db.refresh(s)
    return s


@pytest.fixture()
def shipment_b(db: Session, org_b) -> Shipment:
    org, _membership, _user = org_b
    now = datetime.now(timezone.utc)
    set_session_org(db, org.id)
    s = Shipment(
        id=uuid4(),
        organization_id=org.id,
        reference=f"ORG-B-{uuid4().hex[:6]}",
        origin="Rotterdam",
        destination="New York",
        carrier="MSC",
        current_location="Atlantic",
        status=ShipmentStatus.IN_TRANSIT,
        delay_risk_score=20.0,
        units=50,
        value_usd=2500.0,
        shipped_at=now - timedelta(days=2),
        eta=now + timedelta(days=5),
    )
    db.add(s)
    db.commit()
    set_session_org(db, org.id)
    db.refresh(s)
    return s


@pytest.fixture()
def tenant_ctx(org_a, owner_user):
    org, membership = org_a
    ctx = TenantContext(
        organization_id=org.id,
        user_id=owner_user.id,
        membership_id=membership.id,
        permissions=permissions_for_role("owner"),
        role_slug="owner",
    )
    token = set_tenant(ctx)
    yield ctx
    reset_tenant(token)
