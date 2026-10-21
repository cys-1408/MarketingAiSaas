"""Ingestion routes: job status, mapping review, reprocess, deletion, retry."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes_auth import _current_user
from app.core.security import CAP_DELETE_SOURCES, CAP_EDIT_MAPPINGS, CAP_INGEST
from app.core.tenancy import authorize_workspace, get_scoped
from app.db.models import (
    IngestionJob,
    MappingCandidate,
    Source,
    StageRun,
)
from app.db.session import get_session_factory
from app.ingestion.jobs import (
    IngestionError,
    apply_review_decisions,
    continue_after_review,
    get_worker,
    run_job,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _db():  # noqa: ANN201
    session_factory = get_session_factory()
    yield session_factory()


class MappingDecision(BaseModel):
    candidate_id: str
    action: str = Field(pattern="^(confirm|edit|skip|leave_unmapped)$")
    chosen_field: str | None = None


class ReviewRequest(BaseModel):
    decisions: list[MappingDecision]


@router.get("/sources")
def list_sources(claims=Depends(_current_user), db: Session = Depends(_db)):
    """List workspace sources with their latest job state (real records only)."""
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    sources = db.execute(
        select(Source)
        .where(Source.workspace_id == claims.workspace_id, Source.deleted_at.is_(None))
        .order_by(Source.updated_at.desc())
    ).scalars().all()
    out = []
    for source in sources:
        job = db.execute(
            select(IngestionJob)
            .where(
                IngestionJob.source_id == source.id,
                IngestionJob.source_version == source.latest_version,
            )
            .order_by(IngestionJob.created_at.desc())
        ).scalars().first()
        safe_error = None
        if job is not None and job.error:
            # Serialize only a short, human-readable message; never expose
            # storage paths, stack traces, or source content.
            raw = job.error.get("detail") or job.error.get("message")
            if isinstance(raw, str):
                safe_error = raw[:300]
        out.append(
            {
                "source_id": source.id,
                "name": source.name,
                "file_type": source.file_type,
                "category": source.category,
                "status": source.status,
                "version": source.latest_version,
                "size_bytes": source.size_bytes,
                "record_count": source.record_count,
                "origin": source.origin,
                "updated_at": source.updated_at.isoformat() if source.updated_at else None,
                "job_id": job.id if job else None,
                "job_status": job.status if job else None,
                "review_pending": bool(job.review_pending) if job else False,
                "row_count": job.row_count if job else None,
                "ready_count": job.ready_count if job else None,
                "error_count": job.error_count if job else None,
                "warning_count": job.warning_count if job else None,
                "safe_error": safe_error,
            }
        )
    return {"sources": out}


@router.get("/jobs/{job_id}")
def job_status(job_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    job = get_scoped(db, IngestionJob, claims.workspace_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    stages = db.execute(
        select(StageRun).where(StageRun.job_id == job_id).order_by(StageRun.started_at)
    ).scalars().all()
    return {
        "job_id": job.id,
        "source_id": job.source_id,
        "status": job.status,
        "stage": job.stage,
        "row_count": job.row_count,
        "ready_count": job.ready_count,
        "error_count": job.error_count,
        "warning_count": job.warning_count,
        "review_pending": job.review_pending,
        "stages": [
            {
                "stage": s.stage,
                "status": s.status,
                "detail": s.detail,
                "started_at": s.started_at.isoformat(),
            }
            for s in stages
        ],
    }


@router.get("/jobs/{job_id}/mapping-review")
def get_review(job_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    job = get_scoped(db, IngestionJob, claims.workspace_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    candidates = db.execute(
        select(MappingCandidate).where(
            MappingCandidate.job_id == job_id,
            MappingCandidate.status == "proposed",
        )
    ).scalars().all()
    return {
        "job_id": job_id,
        "status": job.status,
        "candidates": [
            {
                "id": c.id,
                "sheet": c.sheet,
                "column": c.column_name,
                "sample_values": c.sample_values,
                "proposed_field": c.proposed_field,
                "alternatives": c.alternatives,
                "confidence": c.confidence,
                "reason": c.reason,
                "impact": c.impact,
            }
            for c in candidates
        ],
        "actions_available": ["confirm", "edit", "skip", "leave_unmapped"],
    }


@router.post("/jobs/{job_id}/mapping-review")
def submit_review(
    job_id: str,
    payload: ReviewRequest,
    claims=Depends(_current_user),
    db: Session = Depends(_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_EDIT_MAPPINGS,
    )
    job = get_scoped(db, IngestionJob, claims.workspace_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    try:
        job = apply_review_decisions(
            db,
            job_id=job_id,
            decisions=[d.model_dump() for d in payload.decisions],
            reviewer_id=claims.user_id,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # Resume the pipeline synchronously so the response reflects real state.
    source = db.get(Source, job.source_id)
    data = None
    path = __import__("pathlib").Path(
        __import__("app.core.config", fromlist=["get_settings"]).get_settings().object_storage_dir
    ) / source.storage_key
    if path.exists():
        data = path.read_bytes()
    if data is None:
        raise HTTPException(status_code=409, detail="uploaded file content is missing; re-upload the source")
    candidates = db.execute(
        select(MappingCandidate).where(MappingCandidate.job_id == job_id)
    ).scalars().all()
    from app.ingestion.inspection import inspect_bytes
    from app.ingestion.classification import classify

    doc = None
    try:
        inspection = inspect_bytes(data, source.file_type)
        doc = inspection.parsed
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"re-parse failed: {exc}") from exc
    classification = classify(doc)
    from app.ingestion.jobs import _mapping_from_candidates, validation_stage  # local import ok
    from app.ingestion import classification as cls_mod

    accepted = [c for c in candidates if c.status in {"accepted", "edited"}]
    value_columns = _mapping_from_candidates(accepted)
    try:
        job = continue_after_review(
            db,
            job_id=job_id,
            file_bytes=data,
            category=classification.category,
            classification=classification,
            candidates=accepted,
            value_columns=value_columns,
        )
        db.commit()
    except IngestionError as exc:
        db.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job_id": job_id, "status": job.status, "stage": job.stage}


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_INGEST,
    )
    job = get_scoped(db, IngestionJob, claims.workspace_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status not in {"retryable_failure", "failed", "cancelled", "partially_ready"}:
        raise HTTPException(status_code=409, detail=f"job in status '{job.status}' is not retryable")
    source = db.get(Source, job.source_id)
    path = __import__("pathlib").Path(
        __import__("app.core.config", fromlist=["get_settings"]).get_settings().object_storage_dir
    ) / source.storage_key
    if not path.exists():
        raise HTTPException(status_code=409, detail="uploaded file content is missing; re-upload required")
    job.attempts += 1
    job.stage = "queued"
    job.status = "queued"
    db.commit()
    from app.core.config import get_settings as gs

    if gs().ingest_worker_enabled:
        get_worker().submit(job.id)
    return {"job_id": job_id, "status": "queued", "attempts": job.attempts}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_INGEST,
    )
    job = get_scoped(db, IngestionJob, claims.workspace_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.cancel_requested = True
    if job.status in {"queued", "awaiting_review", "inspecting"}:
        job.status = "cancelled"
        job.stage = "cancelled"
    db.commit()
    return {"job_id": job_id, "status": job.status}


@router.post("/sources/{source_id}/reprocess")
def reprocess(source_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_INGEST,
    )
    source = get_scoped(db, Source, claims.workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    source.latest_version += 1
    version = source.latest_version
    db.add(
        __import__("app.db.models", fromlist=["SourceVersion"]).SourceVersion(
            workspace_id=claims.workspace_id,
            source_id=source.id,
            version=version,
            checksum=source.checksum,
        )
    )
    job = IngestionJob(
        workspace_id=claims.workspace_id,
        source_id=source.id,
        source_version=version,
        status="queued",
        created_by=claims.user_id,
    )
    db.add(job)
    db.commit()
    from app.core.config import get_settings as gs

    if gs().ingest_worker_enabled:
        get_worker().submit(job.id)
    return {"source_id": source_id, "version": version, "job_id": job.id, "status": "queued"}


@router.delete("/sources/{source_id}")
def delete_source(source_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_DELETE_SOURCES,
    )
    try:
        from app.ingestion.jobs import delete_source as delete_source_service

        stats = delete_source_service(db, workspace_id=claims.workspace_id, source_id=source_id)
        db.commit()
    except IngestionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"source_id": source_id, "deleted": True, "cleanup": stats}
