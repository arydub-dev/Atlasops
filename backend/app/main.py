"""FastAPI application entrypoint for the SupplyChain Command Center."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scc")

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description=(
        "Enterprise Supply Chain Control Tower API — dashboards, shipments, "
        "inventory, suppliers, risk, scenario simulation, alerts, analytics and an AI advisor."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def _ensure_ingestion_tables() -> None:
    """Additively create new tables and seed mock connectors (idempotent).

    Never touches existing seeded domain data — create_all only creates missing
    tables, and connector seeding is a no-op when connectors already exist.
    """
    try:
        import app.models  # noqa: F401  registers all tables
        from app.core.database import Base, SessionLocal, engine
        from app.services import ingestion

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            created = ingestion.seed_data_sources(db)
            if created:
                logger.info("Seeded %d mock data-source connectors", created)
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - startup must not crash the app
        logger.warning("Ingestion bootstrap skipped: %s", exc)


@app.get("/", tags=["Health"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": __version__,
        "status": "ok",
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "healthy", "environment": settings.ENVIRONMENT}
