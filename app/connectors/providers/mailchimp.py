"""Mailchimp adapter — real implementation of the connector contract.

Talks to the Mailchimp Marketing API for campaign performance (opens,
clicks, unsubscribes). Scopes and endpoint behavior follow the provider's
documented API. Without configured credentials everything raises
:class:`ProviderNotConfigured` so the product shows a truthful
"not configured" state instead of a fake connection.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterator, Protocol

import httpx

from app.connectors.base import (
    ConnectorError,
    MarketingConnector,
    NormalizedRecord,
    ProviderAuthExpired,
    ProviderNotConfigured,
    ProviderRateLimited,
    SyncPage,
)
from app.connectors.base import ProviderCapabilities
from app.core.config import get_settings
from app.core.tenancy import new_id


class _CapableSettings(Protocol):
    mailchimp_client_id: str
    mailchimp_client_secret: str


class MailchimpConnector(MarketingConnector):
    capabilities_key = "mailchimp"

    def __init__(self, credentials: dict[str, str]) -> None:
        super().__init__(credentials)
        settings = get_settings()
        self.capabilities = ProviderCapabilities(
            provider="mailchimp",
            display_name="Mailchimp",
            description="Email campaign delivery and engagement metrics.",
            category="email",
            required_scopes=["campaigns.readonly"],
            supported_objects=["campaigns", "campaign_metrics"],
            supported_metrics=["impressions", "clicks", "unsubscribes", "conversions"],
            supports_incremental=True,
            cursor_field="send_time",
            rate_limit_per_minute=120,
            known_limitations=[
                "Unsubscribe counts reflect the campaign level only.",
                "Conversions require an external tracking integration on the "
                "provider side; absent tracking they are reported as missing, "
                "never zero.",
            ],
            oauth=True,
            api_base_url="https://{server}.api.mailchimp.com/3.0",
        )
        self._server: str = credentials.get("server", "")

    def _required_credential_keys(self) -> tuple[str, ...]:
        return ("access_token", "server")

    # --- lifecycle ---------------------------------------------------------
    def connect(self) -> None:
        super().connect()
        if not self._server:
            self._server = self._resolve_server()
        if not self._server:
            raise ProviderNotConfigured("Mailchimp data-center (server) prefix unknown")

    def _resolve_server(self) -> str:
        token = self._credentials.get("access_token", "")
        if not token:
            raise ProviderNotConfigured("Mailchimp is not authorized")
        try:
            response = httpx.get(
                "https://login.mailchimp.com/oauth2/metadata",
                headers={"Authorization": f"OAuth {token}"},
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Mailchimp metadata failure: {exc}") from exc
        if response.status_code != 200:
            raise ProviderAuthExpired("Mailchimp token rejected during metadata check")
        payload = response.json()
        server = payload.get("dc", "")
        if not server:
            raise ProviderAuthExpired("Mailchimp metadata returned no data center")
        return server

    def test_connection(self) -> dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "mailchimp_client_id", "") and not self._credentials.get("access_token"):
            raise ProviderNotConfigured(
                "Mailchimp is not configured: provide OAuth client credentials "
                "(APP_MAILCHIMP_CLIENT_ID/SECRET) and authorize."
            )
        ping = self._get("")
        return {"ok": True, "account": ping.get("account_name", "unknown")}

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self._credentials.get("access_token", "")
        if not token or not self._server:
            raise ProviderNotConfigured("Mailchimp is not authorized")
        url = f"{self.capabilities.api_base_url.format(server=self._server)}/{path}".rstrip("/")
        try:
            response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Mailchimp network failure: {exc}") from exc
        if response.status_code == 401:
            raise ProviderAuthExpired("Mailchimp token expired")
        if response.status_code == 429:
            raise ProviderRateLimited("Mailchimp rate limit hit")
        if response.status_code >= 400:
            raise ConnectorError(f"Mailchimp API error (HTTP {response.status_code})")
        return response.json()

    # --- discovery/fetching ------------------------------------------------
    def discover_resources(self) -> list[dict[str, Any]]:
        return [
            {"type": "campaigns", "description": "Sent campaigns"},
            {"type": "campaign_metrics", "description": "Per-campaign opens/clicks/unsubscribes"},
        ]

    def fetch_initial_data(self, *, resource: str, start_date: str, end_date: str) -> Iterator[SyncPage]:
        yield from self._fetch_campaigns(resource, since=None, start_date=start_date, end_date=end_date)

    def fetch_incremental_data(self, *, resource: str, cursor: dict[str, Any]) -> Iterator[SyncPage]:
        since = cursor.get("last_send_time")
        yield from self._fetch_campaigns(resource, since=since, start_date=None, end_date=None)

    def _fetch_campaigns(
        self,
        resource: str,
        *,
        since: str | None,
        start_date: str | None,
        end_date: str | None,
    ) -> Iterator[SyncPage]:
        if resource not in self.capabilities.supported_objects and resource != "campaign_metrics":
            raise ConnectorError(f"unsupported resource: {resource}")
        page: int = 0
        while True:
            data = self._get(
                "campaigns",
                params={"status": "sent", "count": 100, "offset": page * 100,
                        "sort_field": "send_time", "sort_dir": "DESC"},
            )
            campaigns = data.get("campaigns", [])
            if not campaigns:
                return SyncPage(records=[], next_cursor=None, exhausted=True)
            records: list[NormalizedRecord] = []
            last_send_time: str | None = None
            for item in campaigns:
                send_time = item.get("send_time") or ""
                settings_value = item.get("settings", {})
                records.append(
                    NormalizedRecord(
                        object_type="campaigns",
                        provider_record_id=item.get("id", new_id()),
                        payload={
                            "campaign_name": settings_value.get("subject_line") or settings_value.get("title", ""),
                            "channel": "email",
                            "start_date": (send_time or "")[:10],
                            "end_date": (send_time or "")[:10],
                        },
                        occurred_at=self._ts(send_time),
                    )
                )
                reports = self._fetch_reports(item.get("id", ""))
                for name, value, unit in reports:
                    records.append(
                        NormalizedRecord(
                            object_type="campaign_metrics",
                            provider_record_id=f"{item.get('id')}:{name}",
                            payload={
                                "campaign_id": item.get("id"),
                                "campaign_name": settings_value.get("subject_line") or settings_value.get("title", ""),
                                "day": (send_time or "")[:10],
                                "metric_name": name,
                                "value": value,
                                "unit": unit,
                            },
                        )
                    )
                if send_time:
                    last_send_time = send_time
            page += 1
            exhausted = len(campaigns) < 100
            next_cursor: dict[str, Any] | None = None
            if last_send_time and not exhausted:
                next_cursor = {"last_send_time": last_send_time}
            elif last_send_time and exhausted:
                next_cursor = {"last_send_time": last_send_time}
            yield SyncPage(records=records, next_cursor=next_cursor, exhausted=exhausted)

    def _fetch_reports(self, campaign_id: str) -> list[tuple[str, float, str]]:
        if not campaign_id:
            return []
        try:
            report = self._get(f"reports/{campaign_id}")
        except ProviderRateLimited:
            raise
        except ConnectorError:
            return []
        opens = report.get("opens", {})
        clicks = report.get("clicks", {})
        metrics: list[tuple[str, float, str]] = []
        count_impr = (opens.get("opens") or 0)
        metrics.append(("impressions", float(count_impr), "count"))
        metrics.append(("clicks", float(clicks.get("clicks") or 0), "count"))
        unsubscribed = report.get("unsubscribed")
        if unsubscribed is not None:
            metrics.append(("unsubscribes", float(unsubscribed), "count"))
        return metrics

    def normalize(self, page: SyncPage, *, object_type: str) -> list[NormalizedRecord]:
        if object_type not in {"campaigns", "campaign_metrics"}:
            raise ConnectorError(f"unsupported object: {object_type}")
        return list(page.records)

    def get_sync_status(self, *, cursor: dict[str, Any], last_synced_at) -> dict[str, Any]:
        status = super().get_sync_status(cursor=cursor, last_synced_at=last_synced_at)
        status["notes"] = "incremental sync uses the campaign send_time cursor"
        return status

    def disconnect(self) -> None:
        token = self._credentials.get("access_token")
        if token:
            try:
                httpx.post(
                    "https://login.mailchimp.com/oauth2/token-revoke",
                    data={"client_id": "", "client_secret": "", "token": token},
                    timeout=10,
                )
            except httpx.HTTPError:
                # Best-effort revoke: local disconnect always succeeds below.
                pass
        self._credentials.clear()

    @staticmethod
    def _ts(value: str):
        if not value:
            return None
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


ADAPTER_CLASS = MailchimpConnector
