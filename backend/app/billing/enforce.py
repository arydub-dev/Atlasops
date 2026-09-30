"""Plan limit enforcement — seats, connectors, AI credits, features."""
from __future__ import annotations

from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.plans import get_plan, plan_has_feature
from app.core.config import settings
from app.models import BillingAccount, Connection, Membership, Organization
from app.models.enums import MembershipStatus, SubscriptionStatus


class PlanLimitExceeded(HTTPException):
    """HTTP 402 Payment Required when a hard plan quota is exceeded."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class FeatureNotAvailable(HTTPException):
    """HTTP 403 when the current plan lacks a feature."""

    def __init__(self, feature: str, plan: str) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{feature}' is not available on the {plan} plan",
        )


def _billing(db: Session, organization_id: UUID) -> BillingAccount | None:
    return db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == organization_id)
    )


def _org_plan(db: Session, organization_id: UUID):
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    billing = _billing(db, organization_id)
    plan = billing.plan if billing else org.plan
    return org, billing, get_plan(plan)


def enforce_feature(db: Session, organization_id: UUID, feature: str) -> None:
    if not settings.FEATURE_BILLING_ENFORCE:
        return
    _, _, plan_def = _org_plan(db, organization_id)
    if not plan_has_feature(plan_def.slug, feature):
        raise FeatureNotAvailable(feature, plan_def.slug.value)


def enforce_seat_limit(db: Session, organization_id: UUID, additional: int = 1) -> None:
    if not settings.FEATURE_BILLING_ENFORCE:
        return
    _, _, plan_def = _org_plan(db, organization_id)
    if plan_def.seat_limit < 0:
        return
    current = (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        or 0
    )
    if current + additional > plan_def.seat_limit:
        raise PlanLimitExceeded(
            f"Seat limit reached ({plan_def.seat_limit}). Upgrade your plan to invite more members."
        )


def enforce_connector_limit(db: Session, organization_id: UUID, additional: int = 1) -> None:
    if not settings.FEATURE_BILLING_ENFORCE:
        return
    _, _, plan_def = _org_plan(db, organization_id)
    if plan_def.connector_limit < 0:
        return
    current = (
        db.scalar(
            select(func.count())
            .select_from(Connection)
            .where(Connection.organization_id == organization_id)
        )
        or 0
    )
    if current + additional > plan_def.connector_limit:
        raise PlanLimitExceeded(
            f"Connector limit reached ({plan_def.connector_limit}). Upgrade your plan to add more connections."
        )


def enforce_ai_credits(db: Session, organization_id: UUID, credits: int = 1) -> None:
    if not settings.FEATURE_BILLING_ENFORCE:
        return
    if credits <= 0:
        raise ValueError("credits must be positive")
    # Serialize the check and the caller's subsequent increment/commit.
    # populate_existing refreshes an account previously loaded during auth.
    billing = db.scalar(select(BillingAccount)
        .where(BillingAccount.organization_id == organization_id)
        .with_for_update().execution_options(populate_existing=True))
    if billing is None:
        raise PlanLimitExceeded("Billing account is required for AI usage")
    included = billing.ai_credits_included
    used = billing.ai_credits_used if billing else 0
    if used + credits > included:
        raise PlanLimitExceeded(
            f"AI credit quota exhausted ({included}/month). Upgrade or purchase additional credits."
        )


def check_plan_limits(db: Session, organization_id: UUID) -> dict:
    """Return current usage vs plan limits (does not raise)."""
    _, billing, plan_def = _org_plan(db, organization_id)
    seats = (
        db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        or 0
    )
    connectors = (
        db.scalar(
            select(func.count())
            .select_from(Connection)
            .where(Connection.organization_id == organization_id)
        )
        or 0
    )
    return {
        "plan": plan_def.slug.value,
        "seats": {"used": seats, "limit": plan_def.seat_limit},
        "connectors": {"used": connectors, "limit": plan_def.connector_limit},
        "ai_credits": {
            "used": billing.ai_credits_used if billing else 0,
            "included": billing.ai_credits_included if billing else plan_def.ai_credits_monthly,
        },
        "features": sorted(plan_def.features),
    }


def enforce_subscription_access(db: Session, organization_id: UUID) -> None:
    """Expired trials and unpaid subscriptions cannot use operational features.

    Billing/settings remain accessible for recovery through their own RBAC gates.
    Initial policy: no automatic payment grace period. Change only with an
    explicit persisted grace deadline and lifecycle tests.
    """
    if not settings.FEATURE_BILLING_ENFORCE:
        return
    org, billing, _ = _org_plan(db, organization_id)
    if billing and billing.status == SubscriptionStatus.ACTIVE:
        return
    if billing and billing.status == SubscriptionStatus.TRIALING and org.trial_ends_at:
        deadline = org.trial_ends_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline > datetime.now(timezone.utc):
            return
    raise PlanLimitExceeded("An active subscription or unexpired trial is required. Manage billing to continue.")
