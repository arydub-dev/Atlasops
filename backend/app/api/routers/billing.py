"""Billing API routes — plans, checkout, portal, Stripe webhooks.

Security model:
- GET /plans — public catalog
- POST /webhooks/stripe — Stripe signature verification only
- All other routes — authenticated session/API token + org membership +
  ``org.billing.manage`` permission. Path ``organization_id`` must match the
  active tenant context (no cross-org ID guessing).
"""
from __future__ import annotations

from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_db_with_tenant, get_request_context, require_permission
from app.billing.enforce import check_plan_limits
from app.billing.plans import list_public_plans
from app.billing.stripe_service import (
    StripeNotConfigured,
    cancel_subscription,
    create_billing_portal_session,
    create_checkout_session,
    get_or_create_billing_account,
    validate_frontend_url,
)
from app.billing.webhooks import construct_event, dispatch_stripe_event
from app.core.config import settings
from app.core.database import get_db
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str
    interval: str = "monthly"
    seat_quantity: int = Field(default=1, ge=1)
    success_url: str | None = None
    cancel_url: str | None = None
    customer_email: str


class PortalRequest(BaseModel):
    return_url: str | None = None


class CancelRequest(BaseModel):
    at_period_end: bool = True


def _require_path_org(organization_id: UUID, ctx: TenantContext) -> None:
    if organization_id != ctx.organization_id:
        raise HTTPException(
            status_code=403,
            detail="organization_id does not match the active organization",
        )


@router.get("/plans")
def get_plans():
    """Public plan catalog (always available; no Stripe key required)."""
    return [
        {
            "slug": p.slug.value,
            "name": p.name,
            "description": p.description,
            "seat_limit": p.seat_limit,
            "connector_limit": p.connector_limit,
            "ai_credits_monthly": p.ai_credits_monthly,
            "features": sorted(p.features),
            "trial_days": p.trial_days,
        }
        for p in list_public_plans()
    ]


@router.get("/usage/{organization_id}")
def get_usage(
    organization_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    _require_path_org(organization_id, ctx)
    return check_plan_limits(db, ctx.organization_id)


@router.get("/usage")
def get_usage_current(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    """Preferred: usage for the active organization (no path ID)."""
    return check_plan_limits(db, ctx.organization_id)


@router.post("/checkout/{organization_id}")
def checkout(
    organization_id: UUID,
    body: CheckoutRequest,
    db: Session = Depends(get_db_with_tenant),
    rcx: RequestContext = Depends(get_request_context),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    from app.models.enums import BillingInterval, BillingPlan

    _require_path_org(organization_id, ctx)
    try:
        plan = BillingPlan(body.plan)
        interval = BillingInterval(body.interval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid plan or interval") from exc

    try:
        success = validate_frontend_url(
            body.success_url
            or f"{settings.FRONTEND_URL}/settings/billing?checkout=success"
        )
        cancel = validate_frontend_url(
            body.cancel_url
            or f"{settings.FRONTEND_URL}/settings/billing?checkout=cancel"
        )
        result = create_checkout_session(
            db,
            organization=rcx.org,
            plan=plan,
            interval=interval,
            customer_email=body.customer_email,
            success_url=success,
            cancel_url=cancel,
            seat_quantity=body.seat_quantity,
        )
        from app.services.audit import write_audit

        write_audit(
            db,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="checkout_started",
            resource="billing",
            detail=f"plan={plan.value}",
        )
        db.commit()
        return result
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/checkout")
def checkout_current(
    body: CheckoutRequest,
    db: Session = Depends(get_db_with_tenant),
    rcx: RequestContext = Depends(get_request_context),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    """Preferred: checkout for the active organization."""
    return checkout(ctx.organization_id, body, db, rcx, ctx)


@router.post("/portal/{organization_id}")
def portal(
    organization_id: UUID,
    body: PortalRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    _require_path_org(organization_id, ctx)
    try:
        return_url = validate_frontend_url(
            body.return_url or f"{settings.FRONTEND_URL}/settings/billing"
        )
        return create_billing_portal_session(
            db,
            organization_id=ctx.organization_id,
            return_url=return_url,
        )
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/portal")
def portal_current(
    body: PortalRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    return portal(ctx.organization_id, body, db, ctx)


@router.post("/cancel/{organization_id}")
def cancel(
    organization_id: UUID,
    body: CancelRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    _require_path_org(organization_id, ctx)
    try:
        account = cancel_subscription(
            db, organization_id=ctx.organization_id, at_period_end=body.at_period_end
        )
        db.commit()
        return {
            "plan": account.plan.value,
            "status": account.status.value,
            "cancel_at_period_end": account.cancel_at_period_end,
        }
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cancel")
def cancel_current(
    body: CancelRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    return cancel(ctx.organization_id, body, db, ctx)


@router.get("/account/{organization_id}")
def billing_account(
    organization_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    _require_path_org(organization_id, ctx)
    account = get_or_create_billing_account(db, ctx.organization_id)
    db.commit()
    return {
        "plan": account.plan.value,
        "interval": account.interval.value,
        "status": account.status.value,
        "seat_quantity": account.seat_quantity,
        "ai_credits_included": account.ai_credits_included,
        "ai_credits_used": account.ai_credits_used,
        "current_period_end": account.current_period_end,
        "cancel_at_period_end": account.cancel_at_period_end,
        "has_stripe_customer": bool(account.stripe_customer_id),
    }


@router.get("/account")
def billing_account_current(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.billing.manage")),
):
    return billing_account(ctx.organization_id, db, ctx)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    payload = await request.body()
    try:
        event = construct_event(payload, stripe_signature)
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    handled = dispatch_stripe_event(db, event)
    return {"received": True, "type": handled}
