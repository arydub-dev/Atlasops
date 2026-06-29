"""Administrative bootstrap endpoints.

These exist to make first-run setup reliable on platforms where ASGI lifespan
(``startup``) events do not fire — notably serverless runtimes. The seed
endpoint runs inside a normal request, so it is guaranteed to execute and
returns a real HTTP response with the resulting counts.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.models import User

logger = logging.getLogger("atlasops")

router = APIRouter(prefix="/admin", tags=["Admin"])


def _authorize(db: Session, token: str | None) -> None:
    """Guard the seed endpoint.

    - If ``SEED_TOKEN`` is configured, require a matching ``x-seed-token`` header.
    - Otherwise, allow only a one-time bootstrap on an empty database. Once any
      user exists the open path is rejected, so the endpoint self-disables.
    """
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
    """Create tables, ensure demo accounts, and seed the demo dataset if empty.

    Idempotent: demo accounts and mock connectors are skipped when present, and
    the full dataset is only generated when the database has no domain data.
    Demo accounts are committed first, so login works even if the larger dataset
    seed is interrupted by a function time limit.
    """
    _authorize(db, x_seed_token)

    # Imported lazily so this module stays importable without a live database.
    import app.models  # noqa: F401  registers all tables
    from app.seed import synthetic
    from app.services import ingestion

    Base.metadata.create_all(bind=engine)

    users_ensured = synthetic.seed_users(db)

    seeded_full_dataset = False
    counts: dict = {}
    if not synthetic.is_seeded(db):
        logger.info("Admin seed: empty database — seeding demo dataset...")
        counts = synthetic.seed_all(db, inventory_history_snapshots=12, verbose=False)
        seeded_full_dataset = True

    connectors_created = ingestion.seed_data_sources(db)

    return {
        "ok": True,
        "users_ensured": users_ensured,
        "seeded_full_dataset": seeded_full_dataset,
        "connectors_created": connectors_created,
        "counts": counts,
    }
