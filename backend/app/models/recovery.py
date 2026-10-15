"""Additive, tenant-owned recovery inputs and human decision snapshots."""
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.models import TimestampMixin
from app.tenancy.mixin import TenantOwned

class RecoveryRecord(Base, TimestampMixin, TenantOwned):
    __tablename__ = 'recovery_records'
    __table_args__ = (UniqueConstraint('organization_id','kind','source_key'),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    kind: Mapped[str] = mapped_column(String(32),nullable=False)
    source_key: Mapped[str] = mapped_column(String(160),nullable=False)
    data: Mapped[dict] = mapped_column(JSON,nullable=False)

class RecoveryCase(Base, TimestampMixin, TenantOwned):
    __tablename__ = 'recovery_cases'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('incidents.id'),nullable=False)
    work_order: Mapped[str] = mapped_column(String(160),nullable=False)
    status: Mapped[str] = mapped_column(String(32),nullable=False,default='proposed')
    data: Mapped[dict] = mapped_column(JSON,nullable=False)
