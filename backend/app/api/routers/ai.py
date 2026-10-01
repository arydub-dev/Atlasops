"""AI Operations Advisor endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.core.config import settings
from app.core.rate_limit import rate_limit_ai
from app.models import AIReport
from app.schemas.entities import AIChatRequest, AIReportOut
from app.services import ai_advisor, insights
from app.tenancy.context import TenantContext

router = APIRouter(prefix="/ai", tags=["AI Advisor"])


@router.get("/status", response_model=dict)
def ai_status(
    ctx: TenantContext = Depends(require_permission("ai.chat")),
) -> dict:
    _ = ctx
    return {
        "provider": "openai" if settings.ai_enabled else "local-engine",
        "model": settings.OPENAI_MODEL if settings.ai_enabled else "local-engine",
        "ai_enabled": settings.ai_enabled,
    }


@router.get("/suggestions", response_model=list[str])
def suggestions(
    ctx: TenantContext = Depends(require_permission("ai.chat")),
) -> list[str]:
    _ = ctx
    return [
        "Why are delays increasing this week?",
        "Which warehouse is most at risk?",
        "What actions should leadership take?",
        "What data sources are connected?",
        "Which systems have ingestion failures?",
        "Which suppliers are underperforming and why?",
        "How many records were imported today?",
    ]


@router.post("/chat", response_model=AIReportOut)
def chat(
    payload: AIChatRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("ai.chat")),
    _: None = Depends(rate_limit_ai),
) -> AIReport:
    from app.billing.enforce import enforce_ai_credits
    from app.models import BillingAccount

    enforce_ai_credits(db, ctx.organization_id, credits=1)
    text, model, context = ai_advisor.answer(db, payload.prompt)
    report = AIReport(
        organization_id=ctx.organization_id,
        prompt=payload.prompt,
        response=text,
        report_type=payload.report_type,
        model=model,
        context_snapshot=context,
        user_id=ctx.user_id,
    )
    db.add(report)
    billing = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == ctx.organization_id)
    )
    if billing is not None:
        billing.ai_credits_used = int(billing.ai_credits_used or 0) + 1
    db.commit()
    db.refresh(report)
    return report


@router.post("/orchestrate", response_model=dict)
def orchestrate(
    payload: AIChatRequest,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("ai.chat")),
    _: None = Depends(rate_limit_ai),
) -> dict:
    """Graph-grounded AI orchestration pipeline (Mission Summary, RCA, Impact, …)."""
    from app.billing.enforce import enforce_ai_credits
    from app.models import BillingAccount
    from app.services import ai_orchestration

    enforce_ai_credits(db, ctx.organization_id, credits=1)
    result = ai_orchestration.orchestrate(
        db, payload.prompt, user_id=str(ctx.user_id)
    )
    report = AIReport(
        organization_id=ctx.organization_id,
        prompt=payload.prompt,
        response=result["response"],
        report_type=payload.report_type or "orchestrate",
        model=result["model"],
        context_snapshot={
            "intent": result["intent"],
            "tool": result["tool"],
            "confidence": result["confidence"],
            "citations": result["citations"],
            "context": result["context"],
        },
        user_id=ctx.user_id,
    )
    db.add(report)
    billing = db.scalar(
        select(BillingAccount).where(BillingAccount.organization_id == ctx.organization_id)
    )
    if billing is not None:
        billing.ai_credits_used = int(billing.ai_credits_used or 0) + 1
    db.commit()
    return {
        **result,
        "report_id": str(report.id),
    }


@router.get("/brief", response_model=dict)
def executive_brief(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("ai.reports")),
) -> dict:
    brief = insights.executive_brief(db)
    db.add(
        AIReport(
            organization_id=ctx.organization_id,
            prompt="[Executive Brief]",
            response=brief["executive_summary"],
            report_type="executive_brief",
            model="local-engine",
            user_id=ctx.user_id,
        )
    )
    db.commit()
    return brief


@router.get("/reports", response_model=list[AIReportOut])
def list_reports(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("ai.reports")),
    limit: int = Query(25, ge=1, le=100),
) -> list[AIReport]:
    return list(
        db.scalars(
            select(AIReport)
            .where(
                AIReport.organization_id == ctx.organization_id,
                AIReport.user_id == ctx.user_id,
            )
            .order_by(AIReport.created_at.desc())
            .limit(limit)
        ).all()
    )
