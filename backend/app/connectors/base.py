"""Abstract Connector protocol — authenticate, discover, sync, health."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.enums import ConnectorHealth, ConnectorType


class SyncMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class SyncResult:
    records_processed: int = 0
    records_imported: int = 0
    records_rejected: int = 0
    cursor: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    # True when pagination/safety caps stopped the fetch before the remote done flag.
    incomplete: bool = False
    failure_class: str | None = None

    def finish(self) -> SyncResult:
        self.finished_at = datetime.now(timezone.utc)
        return self


@dataclass
class HealthStatus:
    health: ConnectorHealth
    message: str = ""
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaDiscovery:
    entities: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] | None = None


class ConnectorError(Exception):
    """Base connector failure with a clear, non-random message.

    ``retryable`` distinguishes transient (429/5xx/timeout) from permanent
    (invalid credentials, malformed payloads) failures so the worker can bound
    ARQ retries instead of looping forever.
    """

    def __init__(
        self,
        message: str = "",
        *,
        retryable: bool = True,
        failure_class: str = "unknown_failure",
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.failure_class = failure_class
        self.status_code = status_code


class CredentialsMissingError(ConnectorError):
    def __init__(self, connector: str, missing: list[str] | str) -> None:
        if isinstance(missing, str):
            missing = [missing]
        fields = ", ".join(missing)
        super().__init__(
            f"{connector}: missing required credentials ({fields}). "
            "Configure credentials on the Connection before syncing.",
            retryable=False,
            failure_class="authentication_failure",
        )
        self.missing = missing


class Connector(ABC):
    """Real connector protocol. Implementations must call external APIs — no fake data."""

    connector_type: ConnectorType
    display_name: str = ""

    def __init__(
        self,
        *,
        organization_id: UUID,
        config: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        cursor: dict[str, Any] | None = None,
    ) -> None:
        self.organization_id = organization_id
        self.config = config or {}
        self.credentials = credentials or {}
        self.cursor = cursor or {}
        self._access_token: str | None = None

    def require_credentials(self, *keys: str) -> None:
        missing = [k for k in keys if not self.credentials.get(k)]
        if missing:
            raise CredentialsMissingError(self.display_name or self.connector_type.value, missing)

    @abstractmethod
    async def authenticate(self) -> str:
        """Obtain (and cache) an access token. Returns the token."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Return True if remote API is reachable with current credentials."""

    @abstractmethod
    async def discover_schema(self) -> SchemaDiscovery:
        """Describe available remote entities / fields."""

    @abstractmethod
    async def sync(self, db: Session, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncResult:
        """Pull remote data into tenant tables. Must not invent records."""

    @abstractmethod
    async def health(self) -> HealthStatus:
        """Probe remote health without mutating data."""

    # --- Connector Platform V2 optional surface (defaults preserve V1 connectors) ---

    async def validate(self) -> dict[str, Any]:
        """Validate credentials/config before sync. Override in connectors."""
        ok = await self.test_connection()
        return {"ok": ok, "errors": [] if ok else ["connection_test_failed"]}

    async def field_mappings(self) -> list[dict[str, Any]]:
        """Declare default source→destination field mappings."""
        return list(self.config.get("field_mappings") or [])

    async def incremental_sync(self, db: Session) -> SyncResult:
        """Alias for incremental mode — preferred V2 entrypoint."""
        return await self.sync(db, mode=SyncMode.INCREMENTAL)

    async def retry_last(self, db: Session) -> SyncResult:
        """Re-run incremental sync (retry semantics)."""
        return await self.incremental_sync(db)

    async def disconnect(self) -> None:
        """Revoke remote tokens / clear local access cache when supported."""
        self._access_token = None

    def version(self) -> str:
        return str(self.config.get("connector_version") or "1.0.0")

    def metadata_snapshot(self) -> dict[str, Any]:
        """Self-describing connector metadata for UI / health panels."""
        return {
            "type": self.connector_type.value
            if hasattr(self.connector_type, "value")
            else str(self.connector_type),
            "display_name": self.display_name,
            "version": self.version(),
            "supports": {
                "oauth": True,
                "incremental": True,
                "field_mappings": True,
                "health": True,
                "retry": True,
            },
        }