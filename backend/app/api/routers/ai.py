"""AI Operations Advisor endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import AIReport, User
from app.schemas.entities import AIChatRequest, AIReportOut
from app.services import ai_advisor, insights

router = APIRouter(prefix="/ai", tags=["AI Advisor"])


@router.get("/status", response_model=dict)
def ai_status(_: User = Depends(get_current_user)) -> dict:
    return {
        "provider": "openai" if settings.ai_enabled else "local-engine",
        "model": settings.OPENAI_MODEL if settings.ai_enabled else "local-engine",
        "ai_enabled": settings.ai_enabled,
    }


@router.get("/suggestions", response_model=list[str])
def suggestions(_: User = Depends(get_current_user)) -> list[str]:
    return [
        "Why are delays increasing this week?",
        "Which warehouse is most at risk?",
        "What actions should leadership take?",
        "What data sources are connected?",
        "When was SAP last synced?",
        "Which systems have ingestion failures?",
        "Which suppliers are underperforming and why?",
        "How many records were imported today?",
    ]


@router.post("/chat", response_model=AIReportOut)
def chat(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIReport:
    text, model, context = ai_advisor.answer(db, payload.prompt)
    report = AIReport(
        prompt=payload.prompt,
        response=text,
        report_type=payload.report_type,
        model=model,
        context_snapshot=context,
        user_id=user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/brief", response_model=dict)
def executive_brief(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Generate a management-consulting style executive brief from live data."""
    brief = insights.executive_brief(db)
    db.add(
        AIReport(
            prompt="[Executive Brief]",
            response=brief["executive_summary"],
            report_type="executive_brief",
            model="local-engine",
            user_id=user.id,
        )
    )
    db.commit()
    return brief


@router.get("/reports", response_model=list[AIReportOut])
def list_reports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(25, ge=1, le=100),
) -> list[AIReport]:
    return list(
        db.scalars(
            select(AIReport)
            .where(AIReport.user_id == user.id)
            .order_by(AIReport.created_at.desc())
            .limit(limit)
        ).all()
    )
