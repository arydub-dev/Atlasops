"""Internal ATLASOPS operator console APIs.

Mounted at ``/api/v1/admin/*`` alongside the demo ``POST /admin/seed`` route.
All console routes require a session cookie and ``User.is_platform_admin``.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.core.database import get_db
from app.models import User
from app.services import platform_console as console

router = APIRouter(prefix="/admin", tags=["Platform Admin"])


@router.get("/health")
def admin_health(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    _ = request, admin
    return console.collect_system_health(db)


@router.get("/tenants")
def admin_tenants(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    _ = admin
    return console.list_tenants(db)


@router.get("/tenants/{tenant_id}")
def admin_tenant_detail(
    tenant_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    data = console.get_tenant(db, tenant_id, admin_user=admin, request=request)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return data


@router.get("/connectors")
def admin_connectors(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    _ = admin
    return console.list_connectors(db)


@router.get("/jobs")
def admin_jobs(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    _ = admin
    return console.list_jobs(db, status=status_filter)


@router.get("/jobs/{job_id}")
def admin_job_detail(
    job_id: UUID,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    _ = admin
    row = console.get_job(db, organization_id, job_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return row


@router.post("/connectors/{connection_id}/retry")
async def admin_retry_connector(
    connection_id: UUID,
    request: Request,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    try:
        return await console.retry_connector_sync(
            db,
            organization_id=organization_id,
            connection_id=connection_id,
            admin_user=admin,
            request=request,
        )
    except ValueError as exc:
        code = str(exc)
        if code in {"tenant_not_found", "connection_not_found"}:
            raise HTTPException(status_code=404, detail="Not found") from exc
        if code == "connection_disabled":
            raise HTTPException(status_code=400, detail="Connector is disabled") from exc
        if code == "credentials_missing":
            raise HTTPException(status_code=400, detail="Connector credentials are not configured") from exc
        raise HTTPException(status_code=400, detail="Unable to retry sync") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to enqueue retry",
        ) from exc


@router.get("/errors")
def admin_errors(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> dict:
    _ = admin
    return console.list_errors(db)
