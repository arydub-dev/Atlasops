"""Connector registry — register/get by ConnectorType."""
from __future__ import annotations

from typing import Type

from app.connectors.base import Connector
from app.models.enums import ConnectorType

_REGISTRY: dict[ConnectorType, Type[Connector]] = {}


def register_connector(connector_cls: Type[Connector]) -> Type[Connector]:
    """Decorator or direct call to register a connector class."""
    ctype = getattr(connector_cls, "connector_type", None)
    if ctype is None:
        raise ValueError(f"{connector_cls.__name__} missing connector_type")
    _REGISTRY[ctype] = connector_cls
    return connector_cls


def get_connector(connector_type: ConnectorType | str) -> Type[Connector]:
    if isinstance(connector_type, str):
        connector_type = ConnectorType(connector_type)
    try:
        return _REGISTRY[connector_type]
    except KeyError as exc:
        raise KeyError(f"No connector registered for {connector_type}") from exc


def list_connectors() -> list[dict]:
    return [
        {
            "type": ctype.value,
            "display_name": cls.display_name or ctype.value,
            "class": cls.__name__,
        }
        for ctype, cls in sorted(_REGISTRY.items(), key=lambda x: x[0].value)
    ]


def create_connector(
    connector_type: ConnectorType | str,
    *,
    organization_id,
    config: dict | None = None,
    credentials: dict | None = None,
    cursor: dict | None = None,
) -> Connector:
    cls = get_connector(connector_type)
    return cls(
        organization_id=organization_id,
        config=config,
        credentials=credentials,
        cursor=cursor,
    )
