"""Phase C enterprise APIs: data quality, dashboards, predictions, documents, CS, security, ops."""
from __future__ import annotations

import base64
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db_with_tenant, require_permission
from app.core.rate_limit import rate_limit_upload
from app.core.uploads import (
    ALLOWED_DOCUMENT_CONTENT_TYPES,
    ALLOWED_DOCUMENT_EXTENSIONS,
    assert_safe_upload,
)
from app.services import (
    customer_success,
    data_quality,
    documents,
    executive_dashboards,
    platform_ops,
    predictions,
    security_center,
)
from app.tenancy.context import TenantContext

router = APIRouter(tags=["Enterprise"])


# ---- Data quality ----
@router.get("/data-quality")
def get_data_quality(
    refresh: bool = Query(False),
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    if refresh:
        return data_quality.assess(db, ctx.organization_id, persist=True)
    latest = data_quality.latest(db, ctx.organization_id)
    if latest is None:
        return data_quality.assess(db, ctx.organization_id, persist=True)
    return latest


@router.post("/data-quality/assess")
def assess_data_quality(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    return data_quality.assess(db, ctx.organization_id, persist=True)


# ---- Dashboards ----
@router.get("/dashboards/roles")
def dashboard_roles(
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    _ = ctx
    return {"roles": executive_dashboards.role_catalogue()}


@router.get("/dashboards/{role_key}")
def get_dashboard(
    role_key: str,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    return executive_dashboards.build_dashboard(
        db, ctx.organization_id, role_key, user_id=ctx.user_id
    )


class LayoutSave(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    widgets: list[str] = Field(min_length=1)
    is_default: bool = False


@router.put("/dashboards/{role_key}/layout")
def save_dashboard_layout(
    role_key: str,
    payload: LayoutSave,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("mission.read")),
) -> dict:
    row = executive_dashboards.save_layout(
        db,
        ctx.organization_id,
        user_id=ctx.user_id,
        role_key=role_key,
        name=payload.name,
        widgets=payload.widgets,
        is_default=payload.is_default,
    )
    return {
        "id": str(row.id),
        "role_key": row.role_key,
        "name": row.name,
        "widgets": row.widgets,
    }


# ---- Predictions ----
@router.get("/predictions")
def list_predictions(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("risk.read")),
) -> dict:
    return {"items": predictions.list_active(db, ctx.organization_id)}


@router.post("/predictions/generate")
def generate_predictions(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("risk.recompute")),
) -> dict:
    items = predictions.generate(db, ctx.organization_id)
    return {"items": items, "count": len(items)}


# ---- Documents ----
class DocumentUpload(BaseModel):
    entity_type: str
    entity_id: UUID
    filename: str = Field(min_length=1, max_length=512)
    content_base64: str
    content_type: str = "application/octet-stream"
    meta: dict = Field(default_factory=dict)


@router.get("/documents")
def list_documents(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("documents.read")),
) -> dict:
    return {
        "items": documents.list_documents(
            db, ctx.organization_id, entity_type=entity_type, entity_id=entity_id
        )
    }


@router.post("/documents", status_code=201)
def upload_document(
    payload: DocumentUpload,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("documents.manage")),
    _: None = Depends(rate_limit_upload),
) -> dict:
    # Reject oversized base64 payloads before allocating a decoded buffer.
    # base64 expands ~4/3; 20MB encoded ≈ 15MB raw.
    if len(payload.content_base64) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 15MB limit")
    try:
        raw = base64.b64decode(payload.content_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid base64 content") from exc
    safe_name = assert_safe_upload(
        filename=payload.filename,
        content_type=payload.content_type,
        size=len(raw),
        max_bytes=15 * 1024 * 1024,
        allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS,
        allowed_content_types=ALLOWED_DOCUMENT_CONTENT_TYPES,
    )
    try:
        doc = documents.upload_document(
            db,
            ctx.organization_id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            filename=safe_name,
            content=raw,
            content_type=payload.content_type,
            uploaded_by_user_id=ctx.user_id,
            meta=payload.meta,
        )
    except documents.DocumentStorageUnavailable:
        raise HTTPException(status_code=503, detail="Document storage is unavailable; please retry later") from None

    return documents.list_documents(
        db, ctx.organization_id, entity_type=payload.entity_type, entity_id=payload.entity_id
    )[0] | {"id": str(doc.id)}


@router.delete("/documents/{document_id}", status_code=204, response_class=Response)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("documents.manage")),
) -> Response:
    if not documents.soft_delete(db, ctx.organization_id, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=204)


# ---- Customer success ----
@router.get("/customer-success/onboarding")
def cs_onboarding(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.read")),
) -> dict:
    return customer_success.onboarding_checklist(db, ctx.organization_id)


@router.get("/customer-success/health-report")
def cs_health(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.usage.read")),
) -> dict:
    return customer_success.health_report(db, ctx.organization_id)


@router.get("/customer-success/adoption")
def cs_adoption(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.usage.read")),
) -> dict:
    return customer_success.adoption_score(db, ctx.organization_id)


# ---- Security center ----
@router.get("/security-center")
def security_center_overview(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.audit.read")),
) -> dict:
    return security_center.security_overview(db, ctx.organization_id)


@router.post("/security-center/revoke-sessions")
def security_revoke_sessions(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.manage")),
) -> dict:
    n = security_center.revoke_all_sessions(db, ctx.organization_id, actor_user_id=ctx.user_id)
    return {"revoked": n}


@router.post("/security-center/tokens/{token_id}/rotate")
def security_rotate_token(
    token_id: UUID,
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.tokens.manage")),
) -> dict:
    token = security_center.rotate_api_token(
        db, ctx.organization_id, token_id, actor_user_id=ctx.user_id
    )
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"id": str(token.id), "revoked": True}


@router.post("/security-center/emergency-lockout")
def security_lockout(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("org.members.manage")),
) -> dict:
    return security_center.emergency_lockout(db, ctx.organization_id, actor_user_id=ctx.user_id)


# ---- Platform ops ----
@router.get("/platform-ops")
def get_platform_ops(
    db: Session = Depends(get_db_with_tenant),
    ctx: TenantContext = Depends(require_permission("connectors.read")),
) -> dict:
    return platform_ops.platform_ops(db, ctx.organization_id)
