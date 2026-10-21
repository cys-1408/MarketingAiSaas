"""Reports: evidence-linked generation, retrieval, export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import request_db
from app.api.routes_auth import _current_user
from app.db.models import PendingReviewItem, Report
from app.tools.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    campaign_id: str
    date_start: str
    date_end: str
    evidence_ids: list[str] = Field(default_factory=list)


class PublishRequest(BaseModel):
    reviewer_note: str = ""


@router.get("")
def list_reports(claims=Depends(_current_user), db: Session = Depends(request_db)):
    """List saved reports for this workspace with real persisted data only."""
    from sqlalchemy import select, desc
    from app.core.tenancy import authorize_workspace

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    reports = db.execute(
        select(Report)
        .where(Report.workspace_id == claims.workspace_id)
        .order_by(desc(Report.created_at))
        .limit(50)
    ).scalars().all()
    return {
        "reports": [
            {
                "id": r.id,
                "campaign_id": r.campaign_id,
                "date_start": r.date_start.isoformat() if r.date_start else None,
                "date_end": r.date_end.isoformat() if r.date_end else None,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "payload": r.payload if isinstance(r.payload, dict) else {},
            }
            for r in reports
        ]
    }


@router.post("", status_code=201)
def create_report(payload: ReportRequest, claims=Depends(_current_user), db: Session = Depends(request_db)):
    try:
        result = ReportService(db).generate_report(
            workspace_id=claims.workspace_id,
            campaign_id=payload.campaign_id,
            date_start=payload.date_start,
            date_end=payload.date_end,
            evidence_ids=payload.evidence_ids,
            user_id=claims.user_id,
        )
        db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.get("/{report_id}")
def get_report(report_id: str, claims=Depends(_current_user), db: Session = Depends(request_db)):
    from app.core.tenancy import authorize_workspace

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    report = ReportService(db).get_report(
        workspace_id=claims.workspace_id, report_id=report_id
    )
    return {"report_id": report.id, "status": report.status, **report.payload}


@router.get("/{report_id}/export")
def export_report(
    report_id: str,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    from app.core.tenancy import authorize_workspace

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    report = ReportService(db).get_report(
        workspace_id=claims.workspace_id, report_id=report_id
    )
    markdown = ReportService(db).export_markdown(report)
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.md"'},
    )


@router.post("/{report_id}/publish-request", status_code=202)
def request_publish(
    report_id: str,
    payload: PublishRequest,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    """Queue an external publish/email/share for approval — never auto-publish."""
    from app.core.tenancy import authorize_workspace

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=2
    )
    report = ReportService(db).get_report(
        workspace_id=claims.workspace_id, report_id=report_id
    )
    item = PendingReviewItem(
        workspace_id=claims.workspace_id,
        item_type="report_publish",
        payload={
            "report_id": report.id,
            "note": payload.reviewer_note,
            "external_channels": "email|share|publish require reviewer approval",
        },
        requested_by=claims.user_id,
    )
    db.add(item)
    db.commit()
    return {
        "review_id": item.id,
        "status": item.status,
        "detail": "report publish/share requires explicit reviewer approval; nothing was sent",
    }
