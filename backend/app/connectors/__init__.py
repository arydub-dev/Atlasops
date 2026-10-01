"""Connector SDK — real integrations (Dynamics BC, Salesforce, UPS)."""
from app.connectors.base import Connector, SyncMode, SyncResult
from app.connectors.registry import get_connector, list_connectors, register_connector

__all__ = [
    "Connector",
    "SyncMode",
    "SyncResult",
    "get_connector",
    "list_connectors",
    "register_connector",
]


def _autoload() -> None:
    # Register built-in connectors on import.
    from app.connectors import dynamics_bc, salesforce, ups  # noqa: F401


_autoload()
