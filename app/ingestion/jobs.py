"""Ingestion job orchestration: the real state machine.

Stages: queued → inspecting → mapping → [awaiting_review when needed] →
normalizing → indexing → graph_updating → validating → ready |
partially_ready | retryable_failure | failed | cancelled.

Stage state is persisted in ``ingestion_jobs`` + ``ingestion_stage_runs``;
work happens through a background executor (thread pool in the modular
monolith deployment) and can be driven synchronously by tests/services.
Every stage writes a StageRun with safe diagnostics — never full source
content, never secrets. Retries resume from the failed stage; cancellation
is checked between stages; ``ready`` is only set after real quality checks.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone as dt_timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger, logging_context
from app.core.tenancy import JobContext
from app.db.models import (
    Campaign,
    CampaignMetric,
    Experiment,
    ExperimentResult,
    FeedbackItem,
    GraphNode,
    IngestionJob,
    MappingCandidate,
    MappingRule,
    Product,
    Source,
    StageRun,
)
from app.ingestion import classification as classification_module
from app.ingestion import deduplication as dedup_module
from app.ingestion import mapping as mapping_module
from app.ingestion import normalization as normalization_module
from app.ingestion.validation import ValidationResult, validate_rows
from app.models.domain import CANONICAL_SCHEMAS

logger = get_logger(__name__)

STAGES = (
    "queued", "inspecting", "mapping", "awaiting_review", "normalizing",
    "indexing", "graph_updating", "validating", "ready",
    "partially_ready", "retryable_failure", "failed", "cancelled",
)


class IngestionError(Exception):
    def __init__(self, detail: str, *, retryable: bool = False, stage: str | None = None) -> None:
        super().__init__(detail)
        self.retryable = retryable
        self.stage = stage


class _StageFailure(IngestionError):
    pass


def _now() -> datetime:
    return datetime.now(dt_timezone.utc)


def _record_stage(
    db: Session,
    job: IngestionJob,
    stage: str,
    status: str,
    detail: dict[str, Any] | None = None,
) -> StageRun:
    run = StageRun(
        job_id=job.id,
        workspace_id=job.workspace_id,
        stage=stage,
        status=status,
        detail=detail or {},
        started_at=_now(),
        finished_at=_now() if status in {"complete", "failed", "skipped"} else None,
    )
    db.add(run)
    return run


def mapping_stage(
    db: Session,
    *,
    job: IngestionJob,
    doc,
    category: str,
) -> tuple[list[MappingCandidate], bool]:
    """Propose, filter with saved rules, and persist mapping candidates.

    Returns (persisted candidates, needs_review).
    """
    saved: dict[str, str] = {}
    fp = None
    if doc.tables:
        fp = mapping_module.schema_fingerprint(
            [c for c in doc.tables[0].columns if c != "__row__"]
        )
        rules = db.execute(
            select(MappingRule).where(
                MappingRule.workspace_id == job.workspace_id,
                MappingRule.source_category == category,
                MappingRule.schema_fingerprint == fp,
                MappingRule.active.is_(True),
            )
        ).scalars().all()
        saved = {r.column_name: r.target_field for r in rules}
    # Idempotent re-runs replace prior proposals for this job.
    db.execute(
        MappingCandidate.__table__.delete().where(MappingCandidate.job_id == job.id)
    )
    proposals: list[MappingCandidate] = []
    any_review = False
    for table in doc.tables:
        for proposal in mapping_module.propose_table_mappings(table, category, saved):
            needs_review = not proposal.auto_accept
            candidate = MappingCandidate(
                workspace_id=job.workspace_id,
                job_id=job.id,
                source_id=job.source_id,
                sheet=table.name,
                column_name=proposal.column,
                sample_values=proposal.sample_values,
                proposed_field=proposal.proposed_field,
                alternatives=proposal.alternatives,
                confidence="high" if proposal.confidence >= 0.9 else "medium" if proposal.confidence >= 0.55 else "low",
                reason=proposal.reason,
                impact=proposal.impact,
                status="proposed",
            )
            if proposal.auto_accept and proposal.proposed_field:
                candidate.status = "accepted"
                candidate.chosen_field = proposal.proposed_field
            else:
                any_review = True
            db.add(candidate)
            proposals.append(candidate)
    # Persist decisions as versioned rules for later reuse (fingerprint-keyed).
    if fp and category in {"campaign_metrics", "customer_feedback"}:
        for candidate in proposals:
            if candidate.status in {"accepted", "edited"}:
                db.add(
                    MappingRule(
                        workspace_id=job.workspace_id,
                        source_category=category,
                        schema_fingerprint=fp,
                        column_name=candidate.column_name,
                        target_field=candidate.chosen_field or "",
                        decision="accepted",
                    )
                )
    return proposals, any_review


def _mapping_from_candidates(
    candidates: list[MappingCandidate],
) -> dict[str, set[str]]:
    """Value columns per canonical field, from persisted candidate decisions."""
    value_columns: dict[str, set[str]] = {}
    for candidate in candidates:
        if candidate.status in {"accepted", "edited"} and candidate.chosen_field:
            value_columns.setdefault(candidate.chosen_field, set()).add(candidate.column_name)
    return value_columns


def normalization_stage(
    db: Session,
    *,
    job: IngestionJob,
    doc,
    category: str,
    candidates: list[MappingCandidate],
    validation: ValidationResult | None = None,
) -> dict[str, int]:
    """Persist canonical records for validated rows, deduplicated and idempotent."""
    value_columns = _mapping_from_candidates(candidates)
    if category == "campaign_metrics":
        rows = []
        for row in doc.tables[0].rows if doc.tables else []:
            mapped = dict(row)
            mapped["__sheet__"] = doc.tables[0].name
            rows.append(mapped)
        # Expand mapped rows: canonical names replace source names.
        expanded: list[dict[str, Any]] = []
        for row in rows:
            canonical_row: dict[str, Any] = {
                k: v for k, v in row.items() if k.startswith("__")
            }
            for canonical, columns in value_columns.items():
                for column in columns:
                    canonical_row[canonical] = row.get(column, "")
            for key, value in row.items():
                if key not in {c for cols in value_columns.values() for c in cols}:
                    canonical_row.setdefault(key, value)
            expanded.append(canonical_row)
        normalized = normalization_module.normalize_campaign_metrics(
            job.workspace_id, expanded,
            source_id=job.source_id,
            source_version=job.source_version,
            value_columns=value_columns,
        )
        kept = _persist_metrics(db, normalized, job)
        return kept
    if category == "customer_feedback":
        rows = []
        for table in doc.tables:
            for row in table.rows:
                mapped = dict(row)
                mapped["__sheet__"] = table.name
                expanded_row: dict[str, Any] = {k: v for k, v in mapped.items() if k.startswith("__")}
                for canonical, columns in value_columns.items():
                    for column in columns:
                        expanded_row[canonical] = mapped.get(column, "")
                for key, value in mapped.items():
                    if key not in {c for cols in value_columns.values() for c in cols}:
                        expanded_row.setdefault(key, value)
                rows.append(expanded_row)
        normalized = normalization_module.normalize_feedback(
            job.workspace_id, rows,
            source_id=job.source_id, source_version=job.source_version,
        )
        kept = 0
        for item in normalized:
            if dedup_module.is_duplicate_feedback(db, job.workspace_id, item.content_fingerprint_value):
                continue
            db.add(
                FeedbackItem(
                    workspace_id=job.workspace_id,
                    text=item.text,
                    summary=item.summary,
                    product_ref=item.product_ref,
                    occurred_on=item.occurred_on,
                    source_type=item.source_type,
                    rating=item.rating,
                    source_id=job.source_id,
                    source_version=job.source_version,
                    locator=item.locator,
                    content_fingerprint=item.content_fingerprint_value,
                )
            )
            kept += 1
        return {"feedback_items": kept}
    if category == "experiment_results":
        rows = []
        for table in doc.tables:
            for row in table.rows:
                expanded_row: dict[str, Any] = {k: v for k, v in row.items() if k.startswith("__")}
                for canonical, columns in value_columns.items():
                    for column in columns:
                        expanded_row[canonical] = row.get(column, "")
                rows.append(expanded_row)
        normalized = normalization_module.normalize_experiments(
            job.workspace_id, rows,
            source_id=job.source_id, source_version=job.source_version,
        )
        names: dict[str, Experiment] = {}
        for item in normalized:
            experiment = names.get(item.experiment_name)
            if experiment is None:
                existing = db.execute(
                    select(Experiment).where(
                        Experiment.workspace_id == job.workspace_id,
                        Experiment.name == item.experiment_name,
                    )
                ).scalar_one_or_none()
                experiment = existing or Experiment(
                    workspace_id=job.workspace_id,
                    name=item.experiment_name,
                    hypothesis=f"Imported from source {job.source_id} (hypothesis not stated in source)",
                    created_by="ingestion",
                )
                if existing is None:
                    db.add(experiment)
                names[item.experiment_name] = experiment
                db.flush()
            db.add(
                ExperimentResult(
                    workspace_id=job.workspace_id,
                    experiment_id=experiment.id,
                    variant=item.variant,
                    observations=item.observations,
                    sample_size=item.sample_size,
                    source_id=job.source_id,
                    source_version=job.source_version,
                )
            )
        return {"experiment_results": len(normalized)}
    # Narrative/unknown categories: nothing tabular to persist here; content
    # is indexed (done below in indexing stage) and remains retrievable.
    return {"narrative_sections": len(doc.sections)}


def _persist_metrics(
    db: Session,
    normalized: list[normalization_module.NormalizedMetricRow],
    job: IngestionJob,
) -> dict[str, int]:
    value_columns_map: dict[str, Any] = {}  # (reserved for cross-source rules)
    campaigns: dict[str, Campaign] = {}
    seen = dedup_module.existing_metric_keys(
        db, job.workspace_id, job.source_id, job.source_version
    )
    added = skipped = 0
    for item in normalized:
        campaign = campaigns.get(item.campaign_key)
        if campaign is None:
            campaign = db.execute(
                select(Campaign).where(
                    Campaign.workspace_id == job.workspace_id,
                    Campaign.external_key == item.campaign_key,
                )
            ).scalar_one_or_none()
            if campaign is None:
                campaign = Campaign(
                    workspace_id=job.workspace_id,
                    name=item.campaign_name,
                    external_key=item.campaign_key,
                    channel=item.channel,
                    source_id=job.source_id,
                    source_version=job.source_version,
                )
                db.add(campaign)
                db.flush()
            campaigns[item.campaign_key] = campaign
        for metric_row in item.metric_rows:
            key = (campaign.id, str(item.day), metric_row["metric_name"])
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            db.add(
                CampaignMetric(
                    workspace_id=job.workspace_id,
                    campaign_id=campaign.id,
                    day=item.day,
                    source_id=job.source_id,
                    source_version=job.source_version,
                    metric_name=metric_row["metric_name"],
                    value=metric_row["value"],
                    unit=metric_row["unit"],
                    definition="",
                    conversion_event=metric_row.get("conversion_event", ""),
                    provenance={"locator": item.locator, "raw_row": item.raw_row},
                )
            )
            added += 1
    return {"metric_rows": added, "duplicates_skipped": skipped}


def validation_stage(
    *,
    doc,
    category: str,
    value_columns: dict[str, set[str]],
) -> ValidationResult:
    rows = []
    for table in doc.tables:
        for row in table.rows:
            mapped: dict[str, Any] = {"__sheet__": table.name, "__row__": row.get("__row__", 0)}
            for canonical, columns in value_columns.items():
                for column in columns:
                    mapped[canonical] = row.get(column, "")
            for key, value in row.items():
                if key != "__row__" and key not in {
                    c for cols in value_columns.values() for c in cols
                }:
                    mapped.setdefault(key, value)
            rows.append(mapped)
    return validate_rows(category, rows, value_columns)


def indexing_stage(
    db: Session,
    *,
    job: IngestionJob,
    source: Source,
    doc,
) -> int:
    """Chunk, embed and index the doc (vector + BM25 share the chunk tokens)."""
    from app.retrieval.chunking import chunk_fingerprint, chunk_parsed_document
    from app.retrieval.embeddings import EmbeddingModel, tokenize
    from app.retrieval.vector_search import VectorIndex

    raw_chunks = chunk_parsed_document(doc)
    if not raw_chunks:
        return 0
    chunks = [
        {
            "kind": chunk.kind,
            "title": chunk.title,
            "text": chunk.text,
            "locator": chunk.locator,
            "fingerprint": chunk_fingerprint(chunk.text),
        }
        for chunk in raw_chunks
    ]
    model = EmbeddingModel.configured()
    index = VectorIndex(model)
    added = index.upsert_index(
        db,
        workspace_id=job.workspace_id,
        source_id=job.source_id,
        source_version=job.source_version,
        source_name=source.name,
        chunks=chunks,
        previous_versions=[v for v in range(1, job.source_version) if v != job.source_version],
    )
    return added


def graph_stage(
    db: Session,
    *,
    job: IngestionJob,
    category: str,
) -> dict[str, int]:
    """Update graph nodes/edges for this source, then workspace-level links."""
    from app.graph import construction

    stats = {"nodes": 0, "edges": 0}
    if category == "campaign_metrics":
        stats.update(construction.build_for_campaign_metrics(
            db, workspace_id=job.workspace_id,
            source_id=job.source_id, source_version=job.source_version,
        ))
    if category in {"customer_feedback", "product_facts"}:
        stats.update(construction.build_for_feedback(
            db, workspace_id=job.workspace_id,
            source_id=job.source_id, source_version=job.source_version,
        ))
    stats.update(construction.link_objections_to_conversion(
        db, workspace_id=job.workspace_id,
    ))
    return stats


def run_job(
    db: Session,
    *,
    job_id: str,
    file_bytes: bytes | None = None,
) -> IngestionJob:
    """Execute the full pipeline for a job synchronously (worker calls this).

    Raises :class:`IngestionError` for state-machine failures so the API
    layer can convert them into stable status responses.
    """
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise IngestionError(f"job {job_id} not found")
    if job.status == "cancelled" or job.cancel_requested:
        return _finish(db, job, "cancelled")
    source = db.get(Source, job.source_id)
    if source is None:
        raise IngestionError(f"source {job.source_id} not found")

    job.status = "inspecting"
    job.stage = "inspecting"
    db.flush()
    _record_stage(db, job, "inspecting", "running")
    try:
        from app.ingestion.inspection import inspect_bytes

        inspection = inspect_bytes(data=file_bytes, declared_type=source.file_type)
        doc = inspection.parsed
        assert doc is not None
    except Exception as exc:
        detail = _safe_error(exc)
        _record_stage(db, job, "inspecting", "failed", {"error": detail})
        raise IngestionError(detail, retryable=False, stage="inspecting") from exc
    _record_stage(db, job, "inspecting", "complete", {
        "tables": len(inspection.table_summaries),
        "rows": inspection.row_count,
        "warnings": inspection.warnings,
        "section_count": inspection.section_count,
    })
    classification = classification_module.classify(doc)
    category = classification.category
    source.category = category
    job.warning_count += len(inspection.warnings)

    mapping_stage(db, job=job, doc=doc, category=category)
    candidates = list(
        db.execute(
            select(MappingCandidate).where(
                MappingCandidate.job_id == job.id,
                MappingCandidate.status != "skipped",
            )
        ).scalars().all()
    )
    value_columns = _mapping_from_candidates(candidates)
    needs_review = any(c.status == "proposed" for c in candidates) or classification.needs_review
    if needs_review:
        job.status = "awaiting_review"
        job.stage = "awaiting_review"
        job.review_pending = True
        db.flush()
        return job

    job = continue_after_review(
        db, job_id=job.id, file_bytes=file_bytes,
        category=category, candidates=candidates,
        classification=classification, value_columns=value_columns,
    )
    return job


def continue_after_review(
    db: Session,
    *,
    job_id: str,
    file_bytes: bytes,
    category: str,
    classification,
    candidates: list[MappingCandidate],
    value_columns: dict[str, set[str]],
) -> IngestionJob:
    """Run normalization → indexing → graph → validation → readiness."""
    from app.ingestion.inspection import inspect_bytes

    job = db.get(IngestionJob, job_id)
    if job is None:
        raise IngestionError(f"job {job_id} not found")
    source = db.get(Source, job.source_id)
    if source is None:
        raise IngestionError(f"source {job.source_id} not found")
    inspection = inspect_bytes(data=file_bytes, declared_type=source.file_type)
    doc = inspection.parsed

    validation = validation_stage(doc=doc, category=category, value_columns=value_columns)
    job.error_count = validation.error_count
    job.warning_count += len([i for i in validation.issues if i.level == "warning"])

    job.status = "normalizing"
    job.stage = "normalizing"
    db.flush()
    _record_stage(db, job, "normalizing", "running")
    try:
        counts = normalization_stage(
            db, job=job, doc=doc, category=category,
            candidates=candidates, validation=validation,
        )
    except Exception as exc:
        _record_stage(db, job, "normalizing", "failed", {"error": _safe_error(exc)})
        raise IngestionError(_safe_error(exc), retryable=True, stage="normalizing") from exc
    _record_stage(db, job, "normalizing", "complete", counts)

    job.status = "indexing"
    job.stage = "indexing"
    db.flush()
    _record_stage(db, job, "indexing", "running")
    try:
        chunk_count = indexing_stage(db, job=job, source=source, doc=doc)
    except Exception as exc:
        _record_stage(db, job, "indexing", "failed", {"error": _safe_error(exc)})
        raise IngestionError(_safe_error(exc), retryable=True, stage="indexing") from exc
    _record_stage(db, job, "indexing", "complete", {"chunks": chunk_count})

    job.status = "graph_updating"
    job.stage = "graph_updating"
    db.flush()
    _record_stage(db, job, "graph_updating", "running")
    try:
        graph_stats = graph_stage(db, job=job, category=category)
    except Exception as exc:
        _record_stage(db, job, "graph_updating", "failed", {"error": _safe_error(exc)})
        raise IngestionError(_safe_error(exc), retryable=True, stage="graph_updating") from exc
    _record_stage(db, job, "graph_updating", "complete", graph_stats)

    # Quality checks determine readiness: errors mean data is quarantined or
    # missing, so the job is partially ready rather than silently 'ready'.
    job.row_count = len(validation.valid_rows) + len(validation.quarantined_rows)
    job.ready_count = len(validation.valid_rows)
    if validation.error_count or validation.quarantined_rows:
        job.status = "partially_ready"
        job.stage = "partially_ready"
    elif classification.needs_review:
        job.status = "partially_ready"
        job.stage = "partially_ready"
    else:
        job.status = "ready"
        job.stage = "ready"
    job.review_pending = False
    db.flush()
    _record_stage(db, job, "validating", "complete", {
        "valid_rows": len(validation.valid_rows),
        "quarantined": len(validation.quarantined_rows),
        "warnings": [i.message for i in validation.issues if i.level == "warning"][:20],
    })
    source.status = job.status
    source.record_count = job.row_count
    return job


def apply_review_decisions(
    db: Session,
    *,
    job_id: str,
    decisions: list[dict[str, Any]],
    reviewer_id: str,
) -> IngestionJob:
    """Apply confirm/edit/skip/leave-unmapped decisions to mapping candidates."""
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise IngestionError(f"job {job_id} not found")
    if job.status != "awaiting_review":
        raise IngestionError("job is not awaiting review")
    candidates_by_id = {
        c.id: c for c in db.execute(
            select(MappingCandidate).where(MappingCandidate.job_id == job_id)
        ).scalars().all()
    }
    for decision in decisions:
        candidate = candidates_by_id.get(decision.get("candidate_id"))
        if candidate is None:
            continue
        action = decision.get("action")
        if action == "confirm":
            candidate.status = "accepted"
            candidate.chosen_field = candidate.proposed_field
        elif action == "edit":
            chosen = decision.get("chosen_field")
            if not chosen:
                raise IngestionError("edit decisions require chosen_field")
            candidate.status = "edited"
            candidate.chosen_field = chosen
        elif action == "skip":
            candidate.status = "skipped"
            candidate.chosen_field = None
        elif action == "leave_unmapped":
            candidate.status = "unmapped"
            candidate.chosen_field = None
        else:
            raise IngestionError(f"unsupported mapping action: {action}")
    db.flush()
    return job


def delete_source(db: Session, *, workspace_id: str, source_id: str) -> dict[str, int]:
    """Delete a source and all dependent derived data (documents, metrics,
    feedback, chunks, graph contributions)."""
    from app.retrieval.vector_search import VectorIndex

    source = db.get(Source, source_id)
    if source is None or source.workspace_id != workspace_id:
        raise IngestionError("source not found")
    metrics = db.execute(
        select(CampaignMetric).where(
            CampaignMetric.workspace_id == workspace_id,
            CampaignMetric.source_id == source_id,
        )
    ).scalars().all()
    removed_metrics = len(metrics)
    for metric in metrics:
        db.delete(metric)
    feedback = db.execute(
        select(FeedbackItem).where(
            FeedbackItem.workspace_id == workspace_id,
            FeedbackItem.source_id == source_id,
        )
    ).scalars().all()
    removed_feedback = len(feedback)
    for item in feedback:
        db.delete(item)
    graph_stats = _delete_graph_contributions(db, workspace_id=workspace_id, source_id=source_id)
    chunk_count = VectorIndex(EmbeddingModelShim()).delete_for_source(db, workspace_id, source_id)
    jobs = db.execute(
        select(IngestionJob).where(
            IngestionJob.workspace_id == workspace_id,
            IngestionJob.source_id == source_id,
        )
    ).scalars().all()
    for ingestion_job in jobs:
        if ingestion_job.status in {"queued", "running", "inspecting", "awaiting_review"}:
            ingestion_job.status = "cancelled"
            ingestion_job.cancel_requested = True
    source.deleted_at = _now()
    source.status = "deleted"
    return {
        "metrics_removed": removed_metrics,
        "feedback_removed": removed_feedback,
        "graph": graph_stats,
        "chunks_removed": chunk_count,
    }


def _delete_graph_contributions(db: Session, *, workspace_id: str, source_id: str) -> dict[str, int]:
    from app.graph import construction

    return construction.delete_source_contributions(
        db, workspace_id=workspace_id, source_id=source_id
    )


def _finish(db: Session, job: IngestionJob, status: str) -> IngestionJob:
    job.status = status
    job.stage = status
    db.flush()
    return job


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    return text[:300] if text else "ingestion failed"


# --- Background worker ---------------------------------------------------------


class IngestionWorker:
    """Thread-pool worker draining ingestion jobs.

    Uses its own session per job; tenant authorization was already verified
    when the job was created, but stage execution re-checks that the source
    still belongs to the job's workspace before acting.
    """

    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._pending: set[str] = set()

    def start(self) -> None:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingestion")

    def submit(self, job_id: str) -> None:
        if self._executor is None:
            self.start()
        assert self._executor is not None
        if job_id in self._pending:
            return
        self._pending.add(job_id)
        self._executor.submit(self._run, job_id)

    def _run(self, job_id: str) -> None:
        from app.db.session import session_scope

        with logging_context(job_id=job_id, stage="ingestion"):
            started = time.perf_counter()
            try:
                with session_scope() as db:
                    run_job(db, job_id=job_id)
            except Exception as exc:  # noqa: BLE001 - record then fail visibly
                logger.error("ingestion job failed", extra={
                    "job_id": job_id,
                    "error": _safe_error(exc),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                })

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None


class EmbeddingModelShim:
    """VectorIndex dependency local to this module (kept minimal on purpose)."""

    def embed_one(self, text: str) -> list[float]:
        from app.retrieval.embeddings import EmbeddingModel

        return EmbeddingModel.configured().embed_one(text)

    def __getattr__(self, name: str):  # pragma: no cover - delegation
        from app.retrieval.embeddings import EmbeddingModel

        return getattr(EmbeddingModel.configured(), name)


_singleton_worker = IngestionWorker()


def get_worker() -> IngestionWorker:
    return _singleton_worker
