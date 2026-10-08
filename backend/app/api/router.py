"""Aggregate all API v1 routers under a single router."""
from fastapi import APIRouter, Depends

from app.api.routers import (
    admin,
    ai,
    alerts,
    analytics,
    auth,
    billing,
    connector_studio,
    dashboard,
    data,
    enterprise,
    graph,
    incidents,
    intelligence,
    inventory,
    leads,
    mission,
    network,
    orders,
    orgs,
    platform_console,
    risks,
    shipments,
    simulations,
    suppliers,
    workflows,
)
from app.core.rate_limit import rate_limit_general

api_router = APIRouter(dependencies=[Depends(rate_limit_general)])
api_router.include_router(auth.router)
api_router.include_router(leads.router)
api_router.include_router(billing.router)
api_router.include_router(orgs.router)
api_router.include_router(admin.router)
api_router.include_router(platform_console.router)
api_router.include_router(mission.router)
api_router.include_router(dashboard.router)
api_router.include_router(shipments.router)
api_router.include_router(inventory.router)
api_router.include_router(suppliers.router)
api_router.include_router(orders.router)
api_router.include_router(graph.router)
api_router.include_router(incidents.router)
api_router.include_router(intelligence.router)
api_router.include_router(connector_studio.router)
api_router.include_router(workflows.router)
api_router.include_router(enterprise.router)
api_router.include_router(risks.router)
api_router.include_router(simulations.router)
api_router.include_router(alerts.router)
api_router.include_router(analytics.router)
api_router.include_router(network.router)
api_router.include_router(data.router)
api_router.include_router(ai.router)
from app.api.routers import priorities
api_router.include_router(priorities.router)
