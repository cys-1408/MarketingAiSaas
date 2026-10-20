"""Google Analytics 4 adapter — real implementation of the connector contract.

Uses the GA4 Data API ``runReport`` endpoint with date ranges verified
against current provider documentation. When credentials are not configured
in the environment, every operation raises :class:`ProviderNotConfigured`
and the product surfaces a truthful "not configured" state; no connection is
ever faked.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterator

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
from app.connectors.oauth import EncryptedCredentialStore
from app.core.config import get_settings


class GoogleAnalyticsConnector(MarketingConnector):
    capabilities_key = "google_analytics"

    def __init__(self, credentials: dict[str, str]) -> None:
        super().__init__(credentials)
        settings = get_settings()
        self.capabilities = self._capabilities(settings)

    @staticmethod
    def _capabilities(settings) -> "ProviderCapabilitiesLike":  # noqa: ANN001
        from app.connectors.base import ProviderCapabilities

        return ProviderCapabilities(
            provider="google_analytics",
            display_name="Google Analytics 4",
            description="Website traffic, sessions, and conversion events.",
            category="web_analytics",
            required_scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            supported_objects=["campaign_metrics"],
            supported_metrics=["sessions", "conversions", "impressions"],
            supports_incremental=True,
            cursor_field="date",
            rate_limit_per_minute=60,
            known_limitations=[
                "Revenue and spend are not exposed by this connector; upload "
                "campaign spend/revenue files for those metrics.",
                "GA4 attribution windows may differ from ad-platform reported "
                "conversions; metric definitions record the source.",
            ],
            api_base_url="https://analyticsdata.googleapis.com/v1beta",
        )

    def _required_credential_keys(self) -> tuple[str, ...]:
        return ("access_token", "property_id")

    # --- discovery --------------------------------------------------------
    def test_connection(self) -> dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "google_analytics_client_id", "") and not self._credentials.get("access_token"):
            raise ProviderNotConfigured(
                "Google Analytics is not configured: provide OAuth client "
                "credentials (APP_GOOGLE_ANALYTICS_CLIENT_ID/SECRET) and authorize."
            )
        response = self._run_report(
            date_range={"startDate": "yesterday", "endDate": "today"},
            dimensions=["date"],
            metrics=["sessions"],
            property_id=self._credentials["property_id"],
        )
        if response.get("error"):
            detail = response.get("error", {})
            if detail.get("status") == "UNAUTHENTICATED":
                raise ProviderAuthExpired("Google Analytics token rejected")
            raise ConnectorError(f"GA4 API error ({response.get('error', {}).get('code')})")
        return {"ok": True, "property": self._credentials["property_id"]}

    def discover_resources(self) -> list[dict[str, Any]]:
        return [
            {"type": "campaign_metrics", "description": "Daily sessions and conversions"},
        ]

    # --- fetching ------------------------------------------------------------
    def fetch_initial_data(self, *, resource: str, start_date: str, end_date: str) -> Iterator[SyncPage]:
        if resource not in self.capabilities.supported_objects:
            raise ConnectorError(f"unsupported resource: {resource}")
        offset = 0
        while True:
            page = self._run_report(
                date_range={"startDate": start_date, "endDate": end_date},
                dimensions=["date", "sessionDefaultChannelGroup", "sessionCampaignName"],
                metrics=["sessions", "conversions"],
                offset=offset,
                property_id=self._credentials["property_id"],
            )
            if page.get("error"):
                raise ConnectorError(str(page.get("error", {}).get("message", "GA4 error")))
            rows = page.get("rows", [])
            if not rows:
                return SyncPage(records=[], next_cursor=None, exhausted=True)
            records = [
                NormalizedRecord(
                    object_type="campaign_metrics",
                    provider_record_id=f"{row['dimensionValues'][0]['value']}:{offset + i}",
                    payload={
                        "day": row["dimensionValues"][0]["value"],
                        "channel": row["dimensionValues"][1]["value"],
                        "campaign_name": row["dimensionValues"][2]["value"],
                        "metric_name": metric["name"],
                        "value": metric["value"],
                        "unit": "count",
                    },
                )
                for row in rows
                for i, metric in enumerate(row.get("metricValues", [{}]))
            ]
            next_offset = int(page.get("rowCount", 0)) > offset + len(rows)
            yield SyncPage(
                records=records,
                next_cursor={"offset": offset + len(rows)} if next_offset else None,
                exhausted=not next_offset,
            )
            if not next_offset:
                return
            offset += len(rows)

    def fetch_incremental_data(self, *, resource: str, cursor: dict[str, Any]) -> Iterator[SyncPage]:
        since = cursor.get("last_date") or (
            dt.date.today() - dt.timedelta(days=7)
        ).isoformat()
        yield from self._fetch_since(resource, {'start': since, 'end': dt.date.today().isoformat()})

    def _fetch_since(self, resource: str, window: dict[str, str]) -> Iterator[SyncPage]:
        yield from self.fetch_initial_data(
            resource=resource,
            start_date=window["start"],
            end_date=window["end"],
        )

    def normalize(self, page: SyncPage, *, object_type: str) -> list[NormalizedRecord]:
        if object_type != "campaign_metrics":
            raise ConnectorError(f"unsupported object: {object_type}")
        return list(page.records)

    def _run_report(
        self,
        *,
        date_range: dict[str, str],
        dimensions: list[str],
        metrics: list[str],
        offset: int = 0,
        property_id: str = "",
    ) -> dict[str, Any]:
        token = self._credentials.get("access_token")
        if not token:
            raise ProviderNotConfigured("Google Analytics is not authorized")
        body = {
            "dateRanges": [date_range],
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": 10000,
            "offset": offset,
        }
        url = f"{self.capabilities.api_base_url}/properties/{property_id}:runReport"
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"GA4 network failure: {exc}") from exc
        if response.status_code == 401:
            raise ProviderAuthExpired("Google Analytics token expired")
        if response.status_code == 429:
            raise ProviderRateLimited("Google Analytics rate limit hit")
        return response.json()


ADAPTER_CLASS = GoogleAnalyticsConnector
