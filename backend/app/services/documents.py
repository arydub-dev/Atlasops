"""Document attachments backed by Cloudflare R2 / S3-compatible storage."""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations import storage
from app.core.config import settings
from app.models import DocumentAttachment
from app.models.enums import DocumentEntityType

class DocumentStorageUnavailable(RuntimeError):
    """Upload could not be durably persisted."""


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._\-]+")


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename((filename or "file").replace("\\", "/"))
    cleaned = _SAFE_FILENAME.sub("_", base).strip("._")
    return (cleaned or "file")[:180]


def list_documents(
    db: Session,
    org_id: UUID,
    *,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
) -> list[dict[str, Any]]:
    q = select(DocumentAttachment).where(
        DocumentAttachment.organization_id == org_id,
        DocumentAttachment.is_deleted.is_(False),
    )
    if entity_type:
        q = q.where(DocumentAttachment.entity_type == DocumentEntityType(entity_type))
    if entity_id:
        q = q.where(DocumentAttachment.entity_id == entity_id)
    rows = db.scalars(q.order_by(DocumentAttachment.created_at.desc()).limit(100)).all()
    return [_out(r) for r in rows]


def upload_document(
    db: Session,
    org_id: UUID,
    *,
    entity_type: str,
    entity_id: UUID,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    uploaded_by_user_id: UUID | None = None,
    meta: dict | None = None,
) -> DocumentAttachment:
    etype = DocumentEntityType(entity_type)
    filename = _sanitize_filename(filename)
    # Version: next for same filename+entity
    prior = db.scalar(
        select(DocumentAttachment)
        .where(
            DocumentAttachment.organization_id == org_id,
            DocumentAttachment.entity_type == etype,
            DocumentAttachment.entity_id == entity_id,
            DocumentAttachment.filename == filename,
            DocumentAttachment.is_deleted.is_(False),
        )
        .order_by(DocumentAttachment.version.desc())
        .limit(1)
    )
    version = (prior.version + 1) if prior else 1
    checksum = hashlib.sha256(content).hexdigest()
    key = f"orgs/{org_id}/{etype.value}/{entity_id}/{uuid4().hex}_{filename}"

    stored = storage.upload_bytes(key=key, data=content, content_type=content_type)
    # Never claim "clean" without a real scanner — pending until scanned.
    scan_status = "pending"
    if not stored and (settings.requires_secure_boot or storage.storage_configured()):
        raise DocumentStorageUnavailable("Document storage is unavailable; upload was not saved")
    if not stored:
        # Persist metadata even when object storage is unset (local/dev) so API works
        key = f"local://{key}"

    doc = DocumentAttachment(
        organization_id=org_id,
        entity_type=etype,
        entity_id=entity_id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        storage_key=key,
        version=version,
        checksum_sha256=checksum,
        meta=meta or {},
        uploaded_by_user_id=uploaded_by_user_id,
        virus_scan_status=scan_status,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def soft_delete(db: Session, org_id: UUID, document_id: UUID) -> bool:
    doc = db.get(DocumentAttachment, document_id)
    if doc is None or doc.organization_id != org_id:
        return False
    doc.is_deleted = True
    db.add(doc)
    db.commit()
    return True


def _out(d: DocumentAttachment) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "entity_type": d.entity_type.value,
        "entity_id": str(d.entity_id),
        "filename": d.filename,
        "content_type": d.content_type,
        "size_bytes": d.size_bytes,
        "version": d.version,
        "checksum_sha256": d.checksum_sha256,
        "meta": d.meta,
        "virus_scan_status": d.virus_scan_status,
        "storage_configured": storage.storage_configured() and not d.storage_key.startswith("local://"),
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
