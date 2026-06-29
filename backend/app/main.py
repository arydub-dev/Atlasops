"""FastAPI application entrypoint for ATLASOPS."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("atlasops")

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
def _bootstrap() -> None:
    """Create tables, optionally seed the demo dataset, and seed mock connectors.

    Idempotent and safe to run on every boot:
    - ``create_all`` only creates missing tables (never drops or overwrites).
    - Domain seeding runs only when ``SEED_ON_STARTUP`` is enabled AND the
      database is empty, so existing data is never touched.
    - Connector seeding is a no-op when connectors already exist.

    Enabling ``SEED_ON_STARTUP`` lets a freshly provisioned deployment (e.g. on
    Render) come up fully populated with demo data and demo login accounts.
    """
    try:
        import app.models  # noqa: F401  registers all tables
        from app.core.database import Base, SessionLocal, engine
        from app.seed import synthetic
        from app.services import ingestion

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            if settings.SEED_ON_STARTUP and not synthetic.is_seeded(db):
                logger.info("Empty database detected — seeding demo dataset...")
                # Keep history light so the seed completes within serverless
                # execution limits on the first cold start.
                counts = synthetic.seed_all(
                    db, inventory_history_snapshots=12, verbose=False
                )
                logger.info("Seed complete: %s", counts)
            created = ingestion.seed_data_sources(db)
            if created:
                logger.info("Seeded %d mock data-source connectors", created)
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - startup must not crash the app
        logger.warning("Startup bootstrap skipped: %s", exc)


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
