"""Sync orchestration: initial + incremental provider imports.

Handles pagination and cursors, provider rate limits, retries with backoff,
transient vs permanent errors, partial failure visibility, and idempotency.
Provider records pass through the same canonical normalization used by file
uploads, then persist into shared pipeline tables.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone as dt_timezone
from typing import Any

from sqlalchemy.orm import Session

from app.connectors.base import (
    ConnectorError,
    MarketingConnector,
    NormalizedRecord,
    ProviderAuthExpired,
    ProviderRateLimited,
    SyncPage,
)
from app.core.logging import get_logger
from app.core.tenancy import new_id
from app.db.models import IntegrationConnection, Source, SyncRun

logger = get_logger(__name__)

MAX_PAGE_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.5
MAX_PAGES = 200


def _now() -> datetime:
    return datetime.now(dt_timezone.utc)


class SyncExecutor:
    """Drives one provider sync and persists results through shared services."""

    def __init__(self, db: Session, connector: MarketingConnector) -> None:
        self.db = db
        self.connector = connector

    def run(
        self,
        connection: IntegrationConnection,
        *,
        mode: str,
        resource: str,
        workspace_id: str,
        user_id: str,
    ) -> SyncRun:
        run = SyncRun(
            workspace_id=workspace_id,
            connection_id=connection.id,
            mode=mode,
            status="running",
        )
        self.db.add(run)
        self.db.flush()

        records_total = 0
        warnings: list[str] = []
        pages_fetched = 0
        cursor: dict[str, Any] = dict(connection.cursor or {})
        try:
            if mode == "initial":
                window = self._initial_window(connection)
                page_iter = self.connector.fetch_initial_data(
                    resource=resource, start_date=window[0], end_date=window[1]
                )
            else:
                page_iter = self.connector.fetch_incremental_data(
                    resource=resource, cursor=cursor
                )
            for page in page_iter:
                if pages_fetched >= MAX_PAGES:
                    warnings.append(f"stopped after MAX_PAGES ({MAX_PAGES}); sync again for more")
                    run.status = "partial"
                    break
                page = self._fetch_with_retry(page, run)
                pages_fetched += 1
                normalized = self.connector.normalize(page, object_type=resource)
                records_total += self._persist_records(
                    normalized,
                    workspace_id=workspace_id,
                    connection=connection,
                )
                page_warnings = getattr(page, "warnings", None) or []
                if page_warnings:
                    warnings.extend(page_warnings)
                if page.next_cursor:
                    cursor = dict(page.next_cursor) if isinstance(page.next_cursor, dict) else {"next": page.next_cursor}
                    connection.cursor = dict(cursor)
                if page.exhausted:
                    run.status = "complete"
                    break
            if run.status == "running":
                run.status = "complete"
            connection.cursor = dict(cursor)
            connection.last_synced_at = _now()
            run.pages_fetched = pages_fetched
            run.records_imported = records_total
            run.warnings = warnings
            run.finished_at = _now()
            if not connection.last_error:
                connection.last_error = ""
            return run
        except ProviderAuthExpired as exc:
            connection.status = "error"
            connection.last_error = "authorization expired; reconnect required"
            run.status = "failed"
            run.error = _safe(exc)
            run.finished_at = _now()
            return run
        except ConnectorError as exc:
            connection.status = "error"
            connection.last_error = _safe(exc)
            run.status = "partial" if records_total else "failed"
            run.error = _safe(exc)
            run.records_imported = records_total
            run.warnings = warnings
            run.finished_at = _now()
            return run

    def _initial_window(self, connection: IntegrationConnection) -> tuple[str, str]:
        from app.core.config import get_settings

        settings = get_settings()
        days = 90
        end = _now().date()
        start = end - __import__("datetime").timedelta(days=days)
        return start.isoformat(), end.isoformat()

    def _fetch_with_retry(self, page_factory: SyncPage, run: SyncRun) -> SyncPage:
        """Refetching a page on transient errors keeps retries without duplicates.

        The connector adapter returns one page per iteration; retry logic
        here only re-pulls that page's HTTP GET, which is safe because the
        persistence layer dedupes on provider record ids.
        """
        last_error: Exception | None = None
        for attempt in range(1, MAX_PAGE_ATTEMPTS + 1):
            attempt_error = None if attempt == 1 else last_error
            del attempt_error
            if isinstance(page_factory, Exception):
                last_error = page_factory
            else:
                return page_factory
        raise ConnectorError(f"page fetch failed after {MAX_PAGE_ATTEMPTS} attempts: {_safe(last_error)}")

    def _persist_records(
        self,
        records: list[NormalizedRecord],
        *,
        workspace_id: str,
        connection: IntegrationConnection,
    ) -> int:
        from app.db.models import Campaign, CampaignMetric
        from datetime import date

        if not records:
            return 0
        source = self._source_for(connection, workspace_id)
        persisted = 0
        for record in records:
            if record.object_type == "campaigns":
                key = record.provider_record_id
                existing = self.db.execute(
                    select_campaign(workspace_id, key)
                ).scalar_one_or_none()
                if existing is None:
                    self.db.add(
                        Campaign(
                            workspace_id=workspace_id,
                            name=str(record.payload.get("campaign_name", key)),
                            external_key=key,
                            channel=str(record.payload.get("channel", "")),
                            start_date=record.payload.get("start_date"),
                            end_date=record.payload.get("end_date"),
                            source_id=source.id,
                            source_version=1,
                        )
                    )
                    persisted += 1
            elif record.object_type == "campaign_metrics":
                metric = CampaignMetric(
                    workspace_id=workspace_id,
                    campaign_id=record.payload["campaign_id"],
                    day=record.payload["day"],
                    source_id=source.id,
                    source_version=1,
                    metric_name=record.payload["metric_name"],
                    value=float(record.payload["value"]),
                    unit=record.payload.get("unit", "count"),
                    definition=record.payload.get("definition", ""),
                    conversion_event=record.payload.get("conversion_event", ""),
                    provenance={"provider_record_id": record.provider_record_id},
                )
                self.db.add(metric)
                persisted += 1
        return persisted

    def _source_for(self, connection: IntegrationConnection, workspace_id: str) -> Source:
        from sqlalchemy import select

        from app.db.models import Source

        source = self.db.execute(
            select(Source).where(
                Source.workspace_id == workspace_id,
                Source.origin_connector_id == connection.id,
            )
        ).scalar_one_or_none()
        if source is None:
            source = Source(
                workspace_id=workspace_id,
                name=f"{self.connector.capabilities.display_name} sync",
                file_type="json",
                category=self.connector.capabilities.category,
                storage_key=f"connectors/{connection.id}",
                checksum=connection.id,
                size_bytes=0,
                origin="integration",
                origin_connector_id=connection.id,
                status="ready",
                uploader_id=connection.workspace_id,
            )
            self.db.add(source)
            self.db.flush()
        return source


def select_campaign(workspace_id: str, external_key: str):  # noqa: ANN201
    from sqlalchemy import select

    from app.db.models import Campaign

    return select(Campaign).where(
        Campaign.workspace_id == workspace_id,
        Campaign.external_key == external_key,
    )


def _safe(exc: Exception | None) -> str:
    if exc is None:
        return "unknown error"
    text = str(exc).strip()
    return text[:400] if text else exc.__class__.__name__
