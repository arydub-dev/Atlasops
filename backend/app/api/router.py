"""Aggregate all API v1 routers under a single router."""
from fastapi import APIRouter

from app.api.routers import (
    admin,
    ai,
    alerts,
    analytics,
    auth,
    dashboard,
    data,
    inventory,
    mission,
    network,
    risks,
    shipments,
    simulations,
    suppliers,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(mission.router)
api_router.include_router(dashboard.router)
api_router.include_router(shipments.router)
api_router.include_router(inventory.router)
api_router.include_router(suppliers.router)
api_router.include_router(risks.router)
api_router.include_router(simulations.router)
api_router.include_router(alerts.router)
api_router.include_router(analytics.router)
api_router.include_router(network.router)
api_router.include_router(data.router)
api_router.include_router(ai.router)
