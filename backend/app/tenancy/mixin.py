"""SQLAlchemy mixins for multi-tenant entities."""
from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TenantOwned:
    """Mixin: every row belongs to exactly one organization."""

    @declared_attr
    def organization_id(cls) -> Mapped[UUID]:
        return mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class UUIDPrimaryKey:
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )


def tenant_index(*columns: str, name: str) -> Index:
    return Index(name, "organization_id", *columns)
