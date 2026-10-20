"""Provider-neutral connector contract.

Real provider adapters implement every method or explicitly report the
capability as unsupported; provider response shapes never leak into
analytics — everything is normalized before persistence.  All operations
carry explicit tenant/context and must be idempotent (a retried sync must
not duplicate records).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator


class ConnectorError(Exception):
    """Normalized provider error."""


class ProviderRateLimited(ConnectorError):
    pass


class ProviderAuthExpired(ConnectorError):
    pass


class ProviderNotConfigured(ConnectorError):
    pass


@dataclass(slots=True)
class ProviderCapabilities:
    provider: str
    display_name: str
    description: str
    category: str  # web_analytics|advertising|crm|email
    required_scopes: list[str] = field(default_factory=list)
    supported_objects: list[str] = field(default_factory=list)
    supported_metrics: list[str] = field(default_factory=list)
    supports_incremental: bool = False
    cursor_field: str | None = None
    rate_limit_per_minute: int | None = None
    known_limitations: list[str] = field(default_factory=list)
    oauth: bool = True
    api_base_url: str = ""


@dataclass(slots=True)
class NormalizedRecord:
    """Provider record already translated into a canonical ingest shape."""

    object_type: str  # campaign_metrics|campaigns
    payload: dict[str, Any]
    provider_record_id: str
    occurred_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SyncPage:
    records: list[NormalizedRecord]
    next_cursor: str | None = None
    exhausted: bool = False


class MarketingConnector:
    """Abstract provider adapter; subclasses implement the real API calls."""

    capabilities: ProviderCapabilities

    def __init__(self, credentials: dict[str, str]) -> None:
        self._credentials = credentials

    # --- lifecycle ------------------------------------------------------
    def connect(self) -> None:
        """Validate credentials are present enough to attempt calls."""
        missing = [k for k in self._required_credential_keys() if not self._credentials.get(k)]
        if missing:
            raise ProviderNotConfigured(
                f"{self.capabilities.provider}: missing credentials: {', '.join(missing)}"
            )

    def _required_credential_keys(self) -> tuple[str, ...]:
        return ("access_token",)

    def test_connection(self) -> dict[str, Any]:
        """Verify access and scopes; returns safe diagnostic info."""
        raise NotImplementedError

    # --- discovery and fetching ------------------------------------------
    def discover_resources(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_initial_data(
        self, *, resource: str, start_date: str, end_date: str
    ) -> Iterator[SyncPage]:
        raise NotImplementedError

    def fetch_incremental_data(
        self, *, resource: str, cursor: dict[str, Any]
    ) -> Iterator[SyncPage]:
        raise NotImplementedError

    # --- normalization ----------------------------------------------------
    def normalize(self, page: SyncPage, *, object_type: str) -> list[NormalizedRecord]:
        """Convert raw fetched payloads to canonical records."""
        raise NotImplementedError

    # --- status ------------------------------------------------------------
    def get_sync_status(self, *, cursor: dict[str, Any], last_synced_at: datetime | None) -> dict[str, Any]:
        fresh = self.capabilities.supports_incremental and bool(cursor)
        return {
            "provider": self.capabilities.provider,
            "incremental_ready": fresh,
            "cursor": cursor,
            "last_synced_at": last_synced_at.isoformat() if last_synced_at else None,
        }

    def disconnect(self) -> None:
        """Revoke provider-side access when the provider APIs allow it."""
        return None
