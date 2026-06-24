"""Operational Risk Center endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import RiskAssessment, User
from app.models.enums import RiskCategory, RiskLevel, UserRole
from app.schemas.entities import RiskAssessmentOut, RiskSummary
from app.services import alert_engine, risk_engine

router = APIRouter(prefix="/risks", tags=["Risk Center"])


@router.get("/summary", response_model=RiskSummary)
def risk_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> RiskSummary:
    summary = risk_engine.summarize(db)
    return RiskSummary(
        overall_score=summary["overall_score"],
        overall_level=summary["overall_level"],
        by_category=summary["by_category"],
        counts=summary["counts"],
        top_risks=summary["top_risks"],
    )


@router.get("", response_model=list[RiskAssessmentOut])
def list_risks(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    category: RiskCategory | None = None,
    level: RiskLevel | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[RiskAssessment]:
    stmt = select(RiskAssessment)
    if category:
        stmt = stmt.where(RiskAssessment.category == category)
    if level:
        stmt = stmt.where(RiskAssessment.level == level)
    stmt = stmt.order_by(RiskAssessment.score.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("/recompute", response_model=dict)
def recompute(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.OPERATIONS_MANAGER, UserRole.ANALYST)),
) -> dict:
    """Re-run the risk scoring engine and regenerate alerts."""
    risk_count = risk_engine.recompute_all(db)
    alert_count = alert_engine.generate_alerts(db)
    return {"risk_assessments": risk_count, "alerts_created": alert_count}
