"""Deterministic analytics tools.

Read-only, parameterized queries; the model can never inject SQL.  Every
metric carries its definition, unit, date window, source lineage and
freshness.  Campaign ownership is verified per call.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import CAP_RUN_INVESTIGATIONS
from app.core.tenancy import WorkspaceContext, assert_scoped, authorize_workspace
from app.db.models import Campaign, CampaignMetric, MetricDefinition, Source


class AnalyticsService:
    """Shared domain service used by routes, the agent workflow, and MCP."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- helpers -----------------------------------------------------------
    def _authorize(
        self, *, user_id: str, workspace_id: str
    ) -> WorkspaceContext:
        return authorize_workspace(
            self.db,
            user_id=user_id,
            workspace_id=workspace_id,
            required_capability=CAP_RUN_INVESTIGATIONS,
        )

    def _validate_window(self, start_date: str, end_date: str) -> tuple[date, date]:
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise ValueError("dates must be ISO format YYYY-MM-DD") from exc
        if end < start:
            raise ValueError("end_date precedes start_date")
        if (end - start).days > 366 * 3:
            raise ValueError("date range exceeds 3 years")
        return start, end

    def _campaign_scoped(
        self, workspace_id: str, campaign_id: str
    ) -> Campaign:
        campaign = assert_scoped(self.db.get(Campaign, campaign_id), workspace_id)
        return campaign

    # --- tools --------------------------------------------------------------
    def get_campaign_summary(
        self,
        *,
        workspace_id: str,
        campaign_id: str,
        start_date: str,
        end_date: str,
        user_id: str | None = None,
        context: WorkspaceContext | None = None,
    ) -> dict[str, Any]:
        """Per-metric totals for one campaign in a date window."""
        ctx = context or self._authorize(
            user_id=user_id or "", workspace_id=workspace_id
        )
        # Tenant scope is verified before any request validation so that
        # probing another tenant's ids is indistinguishable from unknown ids.
        campaign = self._campaign_scoped(workspace_id, campaign_id)
        start, end = self._validate_window(start_date, end_date)
        rows = self.db.execute(
            select(
                CampaignMetric.metric_name,
                func.sum(CampaignMetric.value),
                func.max(CampaignMetric.unit),
                func.max(CampaignMetric.definition),
                func.min(CampaignMetric.day),
                func.max(CampaignMetric.day),
                CampaignMetric.source_id,
                CampaignMetric.source_version,
            )
            .where(
                CampaignMetric.workspace_id == workspace_id,
                CampaignMetric.campaign_id == campaign.id,
                CampaignMetric.day >= start,
                CampaignMetric.day <= end,
            )
            .group_by(CampaignMetric.metric_name, CampaignMetric.source_id)
        ).all()
        metrics: list[dict[str, Any]] = []
        for metric_name, value, unit, definition, day_min, day_max, source_id, source_version in rows:
            metrics.append(
                {
                    "metric_name": metric_name,
                    "value": round(float(value or 0), 6),
                    "unit": unit or "count",
                    "definition": definition or "",
                    "source_id": source_id,
                    "source_version": source_version,
                    "date_min": str(day_min) if day_min else None,
                    "date_max": str(day_max) if day_max else None,
                }
            )
        derived = self._derive_rates(metrics)
        source = self.db.get(Source, campaign.source_id)
        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "channel": campaign.channel,
            "date_start": start.isoformat(),
            "date_end": end.isoformat(),
            "metrics": metrics,
            "derived": derived,
            "freshness": {
                "source_id": source.id if source else campaign.source_id,
                "source_name": source.name if source else "",
                "source_version": campaign.source_version,
                "last_synced_at": source.updated_at.isoformat() if source else None,
            },
            "limitations": self._limitations(metrics),
        }

    def _derive_rates(self, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        values = {m["metric_name"]: m["value"] for m in metrics}
        derived: list[dict[str, Any]] = []
        def add(name: str, numerator: float | None, denominator: float | None, definition: str, unit: str) -> None:
            if numerator is None or denominator is None or denominator == 0:
                derived.append(
                    {
                        "metric_name": name,
                        "value": None,
                        "unit": unit,
                        "definition": definition,
                        "note": "undefined: denominator is zero or missing metric",
                    }
                )
                return
            derived.append(
                {
                    "metric_name": name,
                    "value": round(numerator / denominator, 6),
                    "unit": unit,
                    "definition": definition,
                }
            )

        add(
            "click_through_rate",
            values.get("clicks"),
            values.get("impressions"),
            "clicks / impressions",
            "ratio",
        )
        add(
            "conversion_rate",
            values.get("conversions"),
            values.get("clicks"),
            "conversions / clicks",
            "ratio",
        )
        add(
            "purchase_conversion_rate",
            values.get("purchases"),
            values.get("clicks"),
            "purchases / clicks",
            "ratio",
        )
        add(
            "cost_per_click",
            values.get("spend"),
            values.get("clicks"),
            "spend / clicks",
            "currency",
        )
        add(
            "return_on_ad_spend",
            values.get("revenue"),
            values.get("spend"),
            "revenue / spend",
            "ratio",
        )
        return derived

    def _limitations(self, metrics: list[dict[str, Any]]) -> list[str]:
        notes: list[str] = []
        names = {m["metric_name"] for m in metrics}
        if "sessions" not in names:
            notes.append("session-level metrics are not connected for this source")
        if "purchases" not in names and "conversions" in names:
            notes.append(
                "the source reports generic conversions; without a labeled "
                "purchase column, purchase conversion cannot be claimed"
            )
        if "spend" not in names:
            notes.append("spend is missing; cost-based metrics are undefined, not zero")
        return notes

    def list_campaigns(self, *, workspace_id: str, user_id: str) -> list[dict[str, Any]]:
        self._authorize(user_id=user_id, workspace_id=workspace_id)
        campaigns = self.db.execute(
            select(Campaign).where(Campaign.workspace_id == workspace_id)
        ).scalars().all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "channel": c.channel,
                "audience": c.audience,
                "product": c.product,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "external_key": c.external_key,
            }
            for c in campaigns
        ]

    def compare_campaigns(
        self,
        *,
        workspace_id: str,
        campaign_ids: list[str],
        metric_names: list[str],
        start_date: str,
        end_date: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Side-by-side totals for selected campaigns and metric names."""
        self._authorize(user_id=user_id, workspace_id=workspace_id)
        if not campaign_ids:
            raise ValueError("select at least two campaigns to compare")
        if len(campaign_ids) > 5:
            raise ValueError("compare at most 5 campaigns")
        allowed = {
            "spend", "impressions", "clicks", "sessions", "conversions",
            "purchases", "revenue",
        }
        bad = [m for m in metric_names if m not in allowed]
        if bad:
            raise ValueError(f"unsupported metric names: {', '.join(bad)}")
        start, end = self._validate_window(start_date, end_date)
        result: dict[str, Any] = {
            "date_start": start.isoformat(),
            "date_end": end.isoformat(),
            "campaigns": [],
            "limitations": [],
        }
        for campaign_id in campaign_ids:
            # Each call re-authorizes tenant scope internally.
            summary = self.get_campaign_summary(
                workspace_id=workspace_id,
                campaign_id=campaign_id,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
                context=None,
            )
            selected = [
                m for m in summary["metrics"] if m["metric_name"] in metric_names
            ]
            result["campaigns"].append(
                {
                    "campaign_id": summary["campaign_id"],
                    "campaign_name": summary["campaign_name"],
                    "metrics": selected,
                    "derived": summary["derived"],
                }
            )
            result["limitations"].extend(summary["limitations"])
        result["limitations"] = sorted(set(result["limitations"]))
        return result

    def funnel_metrics(
        self,
        *,
        workspace_id: str,
        campaign_id: str,
        start_date: str,
        end_date: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Funnel from impressions → clicks → conversions/purchases."""
        self._authorize(user_id=user_id, workspace_id=workspace_id)
        summary = self.get_campaign_summary(
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            start_date=start_date,
            end_date=end_date,
            context=None,
        )
        values = {m["metric_name"]: m for m in summary["metrics"]}
        funnel: list[dict[str, Any]] = []
        for metric_name in ("impressions", "clicks", "conversions", "purchases"):
            metric = values.get(metric_name)
            funnel.append(
                {
                    "stage": metric_name,
                    "value": metric["value"] if metric else None,
                    "present": metric is not None,
                }
            )
        return {
            "campaign_id": summary["campaign_id"],
            "campaign_name": summary["campaign_name"],
            "date_start": summary["date_start"],
            "date_end": summary["date_end"],
            "funnel": funnel,
            "limitations": summary["limitations"],
        }
