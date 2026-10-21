"""Uploads: validation, safe storage, source registration, job creation."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes_auth import _current_user
from app.core.config import get_settings
from app.core.tenancy import authorize_workspace, new_id
from app.db.models import IngestionJob, Source, SourceVersion
from app.db.session import get_session_factory

router = APIRouter(prefix="/sources", tags=["uploads"])

ALLOWED_TYPES = {"csv", "tsv", "xlsx", "pdf", "docx", "md", "txt", "html", "json"}


def _safe_storage_key(workspace_id: str, filename: str) -> str:
    """Never trust client paths: names go through sanitization + uuid."""
    settings = get_settings()
    base_name = Path(filename or "upload.bin").name
    ext = base_name.rsplit(".", 1)[-1].lower() if "." in base_name else "bin"
    ext = ext[:8]
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in base_name[:80])
    key = f"{workspace_id[:8]}/{uuid.uuid4().hex}/{stem}.{ext}"
    root = Path(settings.object_storage_dir)
    target = (root / key).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise HTTPException(status_code=400, detail="invalid storage path")
    return key


def _read_upload(file: UploadFile, declared_type: str) -> bytes:
    settings = get_settings()
    declared = (declared_type or "").lower()
    if declared not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported file type '{declared}'; supported: {', '.join(sorted(ALLOWED_TYPES))}",
        )
    data = file.file.read(settings.upload_max_bytes + 1)
    if len(data) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"file exceeds the {settings.upload_max_bytes // (1024 * 1024)} MB upload limit",
        )
    if not data:
        raise HTTPException(status_code=422, detail="uploaded file is empty")
    return data


class UploadResult(BaseModel):
    source_id: str
    job_id: str
    status: str
    detail: str


@router.post("/uploads", response_model=UploadResult, status_code=202)
def upload(
    file: UploadFile,
    claims=Depends(_current_user),
):
    """Validate, store, and register an upload; enqueue the ingestion job.

    The upload endpoint verifies tenancy, size and declared type, then
    registers a source record with checksum/version and queues a real
    ingestion job (idempotent for duplicate identical uploads).
    """
    session_factory = get_session_factory()
    settings = get_settings()
    declared = (file.filename or "upload.bin").rsplit(".", 1)[-1].lower()
    data = _read_upload(file, declared)
    checksum = hashlib.sha256(data).hexdigest()
    from app.ingestion.inspection import InspectionError, inspect_bytes

    try:
        inspect_bytes(data, declared, parse=False)
    except InspectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    with session_factory() as db:
        from app.core.security import CAP_INGEST

        ctx = authorize_workspace(
            db,
            user_id=claims.user_id,
            workspace_id=claims.workspace_id,
            required_capability=CAP_INGEST,
        )
        # Duplicate upload -> reuse the existing source, no duplicate job.
        from sqlalchemy import select

        existing = db.execute(
            select(Source).where(
                Source.workspace_id == claims.workspace_id,
                Source.checksum == checksum,
                Source.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing is not None:
            return UploadResult(
                source_id=existing.id,
                job_id="",
                status="duplicate",
                detail="identical file was already uploaded; the existing source is reused",
            )
        storage_key = _safe_storage_key(claims.workspace_id, file.filename or "upload.bin")
        root = Path(settings.object_storage_dir)
        target = root / storage_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        version = 1
        source = Source(
            workspace_id=claims.workspace_id,
            name=file.filename or "upload.bin",
            file_type=declared,
            storage_key=storage_key,
            checksum=checksum,
            size_bytes=len(data),
            status="queued",
            uploader_id=claims.user_id,
        )
        db.add(source)
        db.flush()
        db.add(
            SourceVersion(
                workspace_id=claims.workspace_id,
                source_id=source.id,
                version=version,
                checksum=checksum,
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
        from app.ingestion.jobs import get_worker
        from app.core.config import get_settings as gs

        if gs().ingest_worker_enabled:
            get_worker().submit(job.id)
        return UploadResult(
            source_id=source.id,
            job_id=job.id,
            status="queued",
            detail="ingestion job queued",
        )
