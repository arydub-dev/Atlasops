"""Connector dead-letter queue helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import ConnectorDeadLetter


def enqueue_dead_letter(
    db: Session,
    *,
    organization_id: UUID,
    connection_id: UUID | None,
    connector_type: str,
    error: str,
    payload: dict[str, Any] | None = None,
) -> ConnectorDeadLetter:
    row = ConnectorDeadLetter(
        organization_id=organization_id,
        connection_id=connection_id,
        connector_type=connector_type,
        error=error[:4000],
        payload=payload,
        attempts=1,
    )
    db.add(row)
    db.flush()
    return row


def mark_resolved(db: Session, row: ConnectorDeadLetter) -> None:
    row.resolved_at = datetime.now(timezone.utc)
