"""Campaign report generation from stored evidence.

Every reported fact maps to an authorized evidence record; supplied evidence
ids are validated against the workspace, so reports never contain
unsupported metrics or citations.  Reports are versioned, persisted, and
kept separate from any external publishing/email action (which requires the
explicit approval queue).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenancy import new_id
from app.db.models import Campaign, EvidenceRecord, Report
from app.tools.analytics import AnalyticsService


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_report(
        self,
        *,
        workspace_id: str,
        campaign_id: str,
        date_start: str,
        date_end: str,
        evidence_ids: list[str],
        user_id: str,
    ) -> dict[str, Any]:
        from app.core.tenancy import authorize_workspace

        authorize_workspace(
            self.db, user_id=user_id, workspace_id=workspace_id, required_capability=2
        )
        try:
            start = date.fromisoformat(date_start)
            end = date.fromisoformat(date_end)
        except ValueError as exc:
            raise ValueError("dates must be ISO format YYYY-MM-DD") from exc
        campaign = self.db.get(Campaign, campaign_id)
        if campaign is None or campaign.workspace_id != workspace_id:
            raise LookupError("campaign not found in this workspace")

        # Validate every evidence id belongs to this workspace and campaign
        # scope (reject foreign evidence rather than filtering silently).
        validated: list[EvidenceRecord] = []
        for evidence_id in evidence_ids:
            record = self.db.get(EvidenceRecord, evidence_id)
            if record is None or record.workspace_id != workspace_id:
                raise LookupError(f"evidence {evidence_id} not found in this workspace")
            if record.campaign_id and record.campaign_id != campaign.id:
                raise LookupError(
                    f"evidence {evidence_id} belongs to another campaign and cannot "
                    "support this report"
                )
            validated.append(record)

        summary = AnalyticsService(self.db).get_campaign_summary(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
            start_date=date_start,
            end_date=date_end,
            user_id=user_id,
        )
        payload = {
            "title": f"Campaign report: {campaign.name}",
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "channel": campaign.channel,
            "date_start": start.isoformat(),
            "date_end": end.isoformat(),
            "methodology": (
                "Metrics computed from stored campaign records with recorded "
                "definitions; narrative findings cite individual evidence records."
            ),
            "metrics": summary["metrics"],
            "derived": summary["derived"],
            "limitations": summary["limitations"],
            "facts": [
                {
                    "evidence_id": record.id,
                    "statement": record.excerpt or (
                        f"{record.metric_name} = {record.metric_value} "
                        f"{record.metric_unit or ''}"
                    ).strip(),
                    "evidence_type": record.evidence_type,
                    "source": {
                        "source_id": record.source_id,
                        "source_version": record.source_version,
                        "source_name": record.source_name,
                        "locator": record.locator,
                    },
                    "metric_definition": record.metric_definition,
                }
                for record in validated
            ],
            "hypotheses_note": (
                "Interpretations and any proposed explanation are hypotheses "
                "unless supported by a controlled experiment."
            ),
            "generated_by": user_id,
        }
        report = Report(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
            date_start=start,
            date_end=end,
            status="ready",
            payload=payload,
            created_by=user_id,
        )
        self.db.add(report)
        self.db.flush()
        db_session = self.db
        return {"report_id": report.id, "status": report.status, "report": payload}

    def get_report(self, *, workspace_id: str, report_id: str) -> Report:
        report = self.db.get(Report, report_id)
        if report is None or report.workspace_id != workspace_id:
            raise LookupError("report not found")
        return report

    def export_markdown(self, report: Report) -> str:
        """Real export derived from actual report data, not placeholders."""
        payload = report.payload
        lines = [
            f"# {payload['title']}",
            "",
            f"Period: {payload['date_start']} to {payload['date_end']}",
            f"Campaign: {payload['campaign_name']} ({payload['channel']})",
            "",
            "## Methodology",
            payload["methodology"],
            "",
            "## Metrics",
        ]
        for metric in payload.get("metrics", []):
            lines.append(f"- {metric['metric_name']}: {metric['value']} {metric['unit']}")
        for derived in payload.get("derived", []):
            value = derived.get("value")
            rendered = f"{value} {derived['unit']}" if value is not None else "undefined"
            lines.append(f"- {derived['metric_name']} (derived): {rendered} — {derived['definition']}")
        lines += ["", "## Facts (evidence-linked)"]
        for fact in payload.get("facts", []):
            source = fact["source"]
            lines.append(
                f"- {fact['statement']} (evidence {fact['evidence_id']}, "
                f"from {source['source_name']} v{source['source_version']} "
                f"locator {source.get('locator')})"
            )
        lines += ["", "## Limitations", *[*payload.get("limitations", []), payload.get("hypotheses_note", "")]]
        return "\n".join(lines) + "\n"
