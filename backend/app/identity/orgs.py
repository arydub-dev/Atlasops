"""Organization lifecycle services."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BillingAccount,
    Invitation,
    Membership,
    Organization,
    User,
)
from app.models.enums import (
    BillingPlan,
    InvitationStatus,
    MembershipStatus,
    OrgStatus,
    SubscriptionStatus,
)
from app.rbac.permissions import SYSTEM_ROLES, permissions_for_role
from app.tenancy.context import TenantContext
from app.tenancy.rls import set_session_org


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] or "org"
    return base


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    n = 1
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        n += 1
        slug = f"{base}-{n}"
    return slug


def create_organization(
    db: Session,
    *,
    name: str,
    owner: User,
    plan: BillingPlan = BillingPlan.TRIAL,
    trial_days: int = 14,
) -> tuple[Organization, Membership]:
    org = Organization(
        name=name,
        slug=unique_slug(db, name),
        status=OrgStatus.TRIALING,
        owner_user_id=owner.id,
        plan=plan,
        trial_ends_at=_utcnow() + timedelta(days=trial_days),
        settings={},
        branding={},
    )
    db.add(org)
    db.flush()
    # FORCE RLS on billing_accounts requires the tenant GUC before insert.
    set_session_org(db, org.id)

    membership = Membership(
        organization_id=org.id,
        user_id=owner.id,
        role_slug="owner",
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)

    billing = BillingAccount(
        organization_id=org.id,
        plan=plan,
        status=SubscriptionStatus.TRIALING,
        seat_quantity=1,
        ai_credits_included=1000,
    )
    db.add(billing)
    db.flush()
    return org, membership


def get_membership(db: Session, org_id: UUID, user_id: UUID) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )


def build_tenant_context(
    *,
    org: Organization,
    user: User,
    membership: Membership,
    request_id: str = "",
) -> TenantContext:
    custom = None
    if membership.custom_permissions is not None:
        custom = frozenset(membership.custom_permissions)
    elif membership.role_slug.startswith("custom:"):
        custom = frozenset()
    perms = permissions_for_role(membership.role_slug, custom)
    if membership.role_slug == "demo_operator" and (org.settings or {}).get("private_demo") is not True:
        perms = frozenset()
    return TenantContext(
        organization_id=org.id,
        user_id=user.id,
        membership_id=membership.id,
        permissions=perms,
        role_slug=membership.role_slug,
        request_id=request_id,
        is_platform_admin=user.is_platform_admin,
    )


def invite_member(
    db: Session,
    *,
    organization_id: UUID,
    email: str,
    role_slug: str,
    invited_by: UUID,
    expires_days: int = 7,
    inviter_role_slug: str | None = None,
) -> Invitation:
    from app.rbac.permissions import can_invite_role

    if role_slug not in SYSTEM_ROLES and not role_slug.startswith("custom:"):
        raise ValueError(f"Unknown role: {role_slug}")
    if inviter_role_slug is not None and not can_invite_role(inviter_role_slug, role_slug):
        raise ValueError(
            f"Cannot invite as '{role_slug}' — role is not assignable by '{inviter_role_slug}'"
        )
    inv = Invitation(
        organization_id=organization_id,
        email=email.lower().strip(),
        role_slug=role_slug,
        token=secrets.token_urlsafe(32),
        status=InvitationStatus.PENDING,
        invited_by_user_id=invited_by,
        expires_at=_utcnow() + timedelta(days=expires_days),
    )
    db.add(inv)
    db.flush()
    return inv


def accept_invitation(db: Session, *, token: str, user: User) -> Membership:
    inv = db.scalar(select(Invitation).where(Invitation.token == token))
    if inv is None or inv.status != InvitationStatus.PENDING:
        raise ValueError("Invitation not found or already used")
    expires = inv.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _utcnow():
        inv.status = InvitationStatus.EXPIRED
        raise ValueError("Invitation expired")
    if inv.email.lower() != user.email.lower():
        raise ValueError("Invitation email does not match signed-in user")

    existing = get_membership(db, inv.organization_id, user.id)
    if existing:
        inv.status = InvitationStatus.ACCEPTED
        inv.accepted_at = _utcnow()
        return existing

    membership = Membership(
        organization_id=inv.organization_id,
        user_id=user.id,
        role_slug=inv.role_slug,
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    inv.status = InvitationStatus.ACCEPTED
    inv.accepted_at = _utcnow()
    db.flush()
    return membership


def transfer_ownership(db: Session, org: Organization, new_owner: User) -> None:
    membership = get_membership(db, org.id, new_owner.id)
    if membership is None:
        raise ValueError("New owner must be an active member")
    # Demote previous owner memberships to admin
    if org.owner_user_id:
        prev = get_membership(db, org.id, org.owner_user_id)
        if prev and prev.role_slug == "owner":
            prev.role_slug = "admin"
    membership.role_slug = "owner"
    org.owner_user_id = new_owner.id


def soft_delete_organization(db: Session, org: Organization) -> None:
    org.status = OrgStatus.DELETED
    org.deleted_at = _utcnow()


def usage_snapshot(db: Session, organization_id: UUID) -> dict:
    from app.models import Connection, ImportJob, AIReport, BillingAccount

    billing = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == organization_id)
    )
    members = db.scalar(
        select(func.count()).select_from(Membership).where(
            Membership.organization_id == organization_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
    ) or 0
    connections = db.scalar(
        select(func.count()).select_from(Connection).where(
            Connection.organization_id == organization_id
        )
    ) or 0
    imports = db.scalar(
        select(func.count()).select_from(ImportJob).where(
            ImportJob.organization_id == organization_id
        )
    ) or 0
    ai_reports = db.scalar(
        select(func.count()).select_from(AIReport).where(
            AIReport.organization_id == organization_id
        )
    ) or 0
    return {
        "seats": members,
        "connections": connections,
        "imports": imports,
        "ai_reports": ai_reports,
        "ai_credits_used": billing.ai_credits_used if billing else 0,
        "ai_credits_included": billing.ai_credits_included if billing else 0,
        "storage_bytes_used": billing.storage_bytes_used if billing else 0,
        "api_requests_month": billing.api_requests_month if billing else 0,
        "plan": billing.plan.value if billing else "trial",
        "subscription_status": billing.status.value if billing else "trialing",
    }
