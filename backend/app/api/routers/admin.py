"""Administrative bootstrap endpoints (demo sandbox only)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.models import User
from app.seed.synthetic import seed_sandbox

logger = logging.getLogger("supply")

router = APIRouter(prefix="/admin", tags=["Admin"])


def _authorize(db: Session, token: str | None) -> None:
    if not settings.FEATURE_DEMO_SANDBOX:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo sandbox is disabled",
        )
    if settings.SEED_TOKEN:
        if not token or token != settings.SEED_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid seed token"
            )
        return
    existing_users = db.scalar(select(func.count(User.id))) or 0
    if existing_users > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Already initialized. Set SEED_TOKEN to reseed.",
        )


@router.post("/seed")
def seed(
    db: Session = Depends(get_db),
    x_seed_token: str | None = Header(default=None, alias="x-seed-token"),
) -> dict:
    """Create tables and seed one multi-tenant demo org (FEATURE_DEMO_SANDBOX only)."""
    _authorize(db, x_seed_token)

    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    result = seed_sandbox(db)
    return {"ok": True, "demo_sandbox": True, **result}
