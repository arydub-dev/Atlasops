"""FastAPI application entrypoint for Supply."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.security_headers import install_security_headers
from app.core.startup_checks import assert_safe_to_boot
from app.core.telemetry import (
    configure_logging,
    install_request_id_middleware,
    setup_opentelemetry,
)

configure_logging()
logger = logging.getLogger("supply")


def _api_prefixes() -> list[str]:
    """Return every prefix the API router should be mounted at."""
    prefix = settings.API_V1_PREFIX
    prefixes = [prefix]
    if prefix.startswith("/api"):
        stripped = prefix[len("/api") :] or "/"
        if stripped != prefix:
            prefixes.append(stripped)
    return prefixes


API_PREFIXES = _api_prefixes()
API_PREFIX = API_PREFIXES[0]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_safe_to_boot(settings)
    if settings.requires_secure_boot:
        from app.core.database import engine
        from app.core.startup_checks import assert_safe_database_role
        assert_safe_database_role(engine)
    try:
        from app.integrations.sentry_setup import init_sentry

        init_sentry()
    except Exception:  # noqa: BLE001
        logger.debug("sentry_init_skipped", exc_info=True)
    # Schema: production must use Alembic. create_all is for local/dev only and
    # does NOT install RLS policies — never rely on it for tenant isolation.
    if settings.ALLOW_CREATE_ALL_ON_STARTUP and not settings.requires_secure_boot:
        try:
            import app.models  # noqa: F401

            from app.core.database import Base, engine

            Base.metadata.create_all(bind=engine)
            logger.info("Database schema ensured via create_all (non-production)")
        except Exception as exc:  # pragma: no cover
            logger.warning("Startup create_all skipped: %s", exc)
    elif settings.requires_secure_boot:
        logger.info(
            "%s boot: expecting schema from alembic upgrade head",
            settings.ENVIRONMENT,
        )
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description=(
        "Enterprise Supply Chain Control Tower API — multi-tenant dashboards, "
        "shipments, inventory, suppliers, risk, scenario simulation, alerts, "
        "analytics and an AI advisor."
    ),
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_security_headers(app)
install_request_id_middleware(app)
setup_opentelemetry(app)

# CSRF Origin/Referer check for cookie-authenticated mutations (enabled in production).
from app.core.csrf import CsrfOriginMiddleware

app.add_middleware(CsrfOriginMiddleware)

# Metrics: public in development; token-gated on staging/production.
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request) -> Response:
        if settings.requires_secure_boot or settings.METRICS_TOKEN:
            auth = request.headers.get("Authorization") or ""
            token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
            if not settings.METRICS_TOKEN or token != settings.METRICS_TOKEN:
                raise HTTPException(status_code=404, detail="Not found")
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
except ImportError:  # pragma: no cover
    pass

app.include_router(api_router, prefix=API_PREFIXES[0])
for _alias in API_PREFIXES[1:]:
    app.include_router(api_router, prefix=_alias, include_in_schema=False)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected errors; never leak stack traces outside development."""
    from fastapi.exception_handlers import http_exception_handler

    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled_exception path=%s method=%s request_id=%s",
        request.url.path,
        request.method,
        request_id,
    )
    detail = "Internal server error"
    if settings.ENVIRONMENT.lower() in {"development", "test"}:
        detail = f"Internal server error ({type(exc).__name__})"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": request_id},
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.get("/", tags=["Health"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": __version__,
        "status": "ok",
        "docs": "/docs" if settings.api_docs_enabled else None,
        "api": API_PREFIX,
    }


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


@app.get("/health/live", tags=["Health"])
def health_live() -> dict:
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def health_ready() -> dict:
    """Readiness: DB required; Redis required only when queue-backed sync is enabled.

    When ``CONNECTOR_SYNC_INLINE=true`` (local/dev), Redis is reported as
    ``skipped:inline_sync`` and readiness succeeds without Redis.
    """
    try:
        from sqlalchemy import text

        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        logger.exception("health_ready_db_failed")
        raise HTTPException(status_code=503, detail="not_ready:database") from None

    checks: dict[str, str] = {"database": "ok"}

    if settings.CONNECTOR_SYNC_INLINE:
        checks["redis"] = "skipped:inline_sync"
        checks["workers"] = "degraded:inline_sync"
        return {
            "status": "ready",
            "mode": "inline_sync",
            "checks": checks,
            "message": "Connector jobs run inline; Redis/worker not required.",
        }

    try:
        from app.core.startup_checks import ping_redis

        ping_redis(settings.REDIS_URL)
        checks["redis"] = "ok"
        checks["workers"] = "required"
    except Exception:
        logger.exception("health_ready_redis_failed")
        raise HTTPException(status_code=503, detail="not_ready:redis") from None

    return {"status": "ready", "mode": "queued", "checks": checks}
