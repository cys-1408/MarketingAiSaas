"""Complete relational schema.

Scope-of-truth rules baked into the design:

* every record carries ``workspace_id`` — the authoritative tenant key that
  :mod:`app.core.tenancy` verifies server-side on every access,
* source-derived records carry ``source_id`` + ``source_version`` lineage so
  reprocessing and deletion can recompute/remove contributions,
* providers never leak: credentials are stored encrypted, provider payloads
  are normalized into canonical tables before persistence.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin, new_id, utcnow

LongText = Text
JSONType = JSON


# --- Identity, tenancy, audit ---------------------------------------------------


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SessionToken(Base, IdMixin):
    __tablename__ = "sessions"
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Workspace(Base, IdMixin, TimestampMixin):
    __tablename__ = "workspaces"
    name: Mapped[str] = mapped_column(String(160))
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    plan: Mapped[str] = mapped_column(String(32), default="team")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Membership(Base, IdMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_member"),)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    invited_by: Mapped[str | None] = mapped_column(String(32), default=None)


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    actor_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# --- Sources and ingestion --------------------------------------------------------


class Source(Base, IdMixin, TimestampMixin):
    __tablename__ = "sources"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    file_type: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64), default="unknown")
    storage_key: Mapped[str] = mapped_column(String(512))
    checksum: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    latest_version: Mapped[int] = mapped_column(Integer, default=1)
    uploader_id: Mapped[str] = mapped_column(String(32), index=True)
    origin: Mapped[str] = mapped_column(String(32), default="upload")  # upload|integration
    origin_connector_id: Mapped[str | None] = mapped_column(String(32), default=None)
    record_count: Mapped[int | None] = mapped_column(Integer, default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class SourceVersion(Base, IdMixin):
    __tablename__ = "source_versions"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class IngestionJob(Base, IdMixin, TimestampMixin):
    __tablename__ = "ingestion_jobs"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(32), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    ready_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    review_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONType, default=None)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(32), index=True)


class StageRun(Base, IdMixin):
    __tablename__ = "ingestion_stage_runs"
    job_id: Mapped[str] = mapped_column(String(32), index=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class MappingCandidate(Base, IdMixin, TimestampMixin):
    __tablename__ = "mapping_candidates"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    job_id: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    sheet: Mapped[str] = mapped_column(String(256), default="")
    column_name: Mapped[str] = mapped_column(String(256))
    sample_values: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    proposed_field: Mapped[str | None] = mapped_column(String(128), default=None)
    alternatives: Mapped[list[str]] = mapped_column(JSONType, default=list)
    confidence: Mapped[str] = mapped_column(String(16))  # high|medium|low
    reason: Mapped[str] = mapped_column(String(512), default="")
    impact: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(24), default="proposed")  # proposed|accepted|edited|skipped|unmapped
    chosen_field: Mapped[str | None] = mapped_column(String(128), default=None)

    __table_args__ = (
        UniqueConstraint("job_id", "sheet", "column_name", name="uq_mapping_unique_col"),
    )


class MappingRule(Base, IdMixin, TimestampMixin):
    """Versioned customer mapping decisions reused across compatible sources."""

    __tablename__ = "mapping_rules"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    source_category: Mapped[str] = mapped_column(String(64))
    schema_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    column_name: Mapped[str] = mapped_column(String(256))
    target_field: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(24), default="accepted")
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# --- Canonical domain entities ------------------------------------------------------


class MetricDefinition(Base, IdMixin, TimestampMixin):
    __tablename__ = "metric_definitions"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(32))
    numerator: Mapped[str] = mapped_column(String(128))
    denominator: Mapped[str | None] = mapped_column(String(128), default=None)
    aggregation: Mapped[str] = mapped_column(String(32), default="sum")
    attribution_window_days: Mapped[int] = mapped_column(Integer, default=0)
    definition: Mapped[str] = mapped_column(String(512))
    limitations: Mapped[str] = mapped_column(String(512), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_precedence: Mapped[list[str]] = mapped_column(JSONType, default=list)

    __table_args__ = (UniqueConstraint("workspace_id", "name", "version", name="uq_metric_def"),)


class Campaign(Base, IdMixin, TimestampMixin):
    __tablename__ = "campaigns"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="active")
    channel: Mapped[str] = mapped_column(String(128), default="")
    audience: Mapped[str] = mapped_column(String(256), default="")
    product: Mapped[str] = mapped_column(String(256), default="")
    offer: Mapped[str] = mapped_column(String(256), default="")
    message: Mapped[str] = mapped_column(String(256), default="")
    landing_page: Mapped[str] = mapped_column(String(512), default="")
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    external_key: Mapped[str] = mapped_column(String(256), default="")
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (
        Index("ix_campaign_ws_key", "workspace_id", "external_key"),
    )


class CampaignMetric(Base, IdMixin):
    __tablename__ = "campaign_metrics"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    campaign_id: Mapped[str] = mapped_column(String(32), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(String(128))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="count")
    definition: Mapped[str] = mapped_column(String(512), default="")
    conversion_event: Mapped[str] = mapped_column(String(128), default="")
    # Original row values + locator for every metric record (lineage rule).
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        Index("ix_metric_unique_row", "campaign_id", "day", "metric_name", "source_id", "source_version"),
    )


class Product(Base, IdMixin, TimestampMixin):
    __tablename__ = "products"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    normalized_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(String(2048), default="")
    features: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    limitations: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    approved_claims: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    faqs: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)


class FeedbackItem(Base, IdMixin):
    __tablename__ = "feedback_items"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    text: Mapped[str] = mapped_column(LongText)
    summary: Mapped[str] = mapped_column(String(512), default="")
    product_ref: Mapped[str] = mapped_column(String(256), default="")
    campaign_ref: Mapped[str] = mapped_column(String(256), default="")
    occurred_on: Mapped[date | None] = mapped_column(Date, default=None)
    source_type: Mapped[str] = mapped_column(String(64), default="unknown")
    rating: Mapped[float | None] = mapped_column(Float, default=None)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    content_fingerprint: Mapped[str] = mapped_column(String(64), index=True)


class Experiment(Base, IdMixin, TimestampMixin):
    __tablename__ = "experiments"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    hypothesis: Mapped[str] = mapped_column(String(1024))
    control: Mapped[str] = mapped_column(String(512), default="")
    variant: Mapped[str] = mapped_column(String(512), default="")
    audience: Mapped[str] = mapped_column(String(256), default="")
    primary_metric: Mapped[str] = mapped_column(String(128), default="")
    guardrail_metrics: Mapped[list[str]] = mapped_column(JSONType, default=list)
    duration_days: Mapped[int | None] = mapped_column(Integer, default=None)
    stopping_rules: Mapped[str] = mapped_column(String(512), default="")
    confounders: Mapped[list[str]] = mapped_column(JSONType, default=list)
    success_criteria: Mapped[str] = mapped_column(String(512), default="")
    sample_size_note: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(24), default="draft")
    recommendation_id: Mapped[str | None] = mapped_column(String(32), default=None)
    created_by: Mapped[str] = mapped_column(String(32))


class ExperimentResult(Base, IdMixin):
    __tablename__ = "experiment_results"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    experiment_id: Mapped[str] = mapped_column(String(32), index=True)
    variant: Mapped[str] = mapped_column(String(128))
    observations: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    started_on: Mapped[date | None] = mapped_column(Date, default=None)
    ended_on: Mapped[date | None] = mapped_column(Date, default=None)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer)


class Recommendation(Base, IdMixin, TimestampMixin):
    __tablename__ = "recommendations"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    campaign_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(512))
    observed_facts: Mapped[list[str]] = mapped_column(JSONType, default=list)
    interpretation: Mapped[str] = mapped_column(String(1024), default="")
    hypothesis: Mapped[str] = mapped_column(String(1024), default="")
    supporting_evidence: Mapped[list[str]] = mapped_column(JSONType, default=list)
    contradictory_evidence: Mapped[list[str]] = mapped_column(JSONType, default=list)
    primary_metric: Mapped[str] = mapped_column(String(128), default="")
    risks: Mapped[list[str]] = mapped_column(JSONType, default=list)
    missing_data: Mapped[list[str]] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(24), default="new")
    created_by: Mapped[str] = mapped_column(String(32))


# --- Integrations --------------------------------------------------------------------


class IntegrationConnection(Base, IdMixin, TimestampMixin):
    __tablename__ = "integration_connections"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|connected|error|disconnected
    credentials_encrypted: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    scopes: Mapped[list[str]] = mapped_column(JSONType, default=list)
    oauth_state: Mapped[str] = mapped_column(String(128), default="")
    oauth_state_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    oauth_code_verifier: Mapped[str] = mapped_column(String(256), default="")
    cursor: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_error: Mapped[str] = mapped_column(String(512), default="")
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    __table_args__ = (UniqueConstraint("workspace_id", "provider", name="uq_connection_per_provider"),)


class SyncRun(Base, IdMixin):
    __tablename__ = "sync_runs"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    connection_id: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(16))  # initial|incremental
    status: Mapped[str] = mapped_column(String(16))  # running|complete|partial|failed|cancelled
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_imported: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSONType, default=list)
    error: Mapped[str | None] = mapped_column(String(512), default=None)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


# --- Retrieval -------------------------------------------------------------------------


class Chunk(Base, IdMixin, TimestampMixin):
    __tablename__ = "chunks"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer, index=True)
    source_name: Mapped[str] = mapped_column(String(256), default="")
    kind: Mapped[str] = mapped_column(String(16), default="narrative")  # narrative|table_row|meta
    title: Mapped[str] = mapped_column(String(256), default="")
    text: Mapped[str] = mapped_column(LongText)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(JSONType, default=None)
    embedding_model: Mapped[str] = mapped_column(String(128), default="")
    tokens: Mapped[list[str] | None] = mapped_column(JSONType, default=None)
    checksum_fingerprint: Mapped[str] = mapped_column(String(64))
    # Per-source-version identity so reprocessing is idempotent.
    version_fingerprint: Mapped[str] = mapped_column(String(72), default="")

    __table_args__ = ()


# --- Campaign Evidence Graph --------------------------------------------------------------


class GraphNode(Base, IdMixin, TimestampMixin):
    __tablename__ = "graph_nodes"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    node_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_key: Mapped[str] = mapped_column(String(256), index=True)
    label: Mapped[str] = mapped_column(String(256))
    props: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (UniqueConstraint("workspace_id", "node_type", "entity_key", name="uq_node"),)


class GraphEdge(Base, IdMixin, TimestampMixin):
    __tablename__ = "graph_edges"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    edge_type: Mapped[str] = mapped_column(String(48), index=True)
    src_id: Mapped[str] = mapped_column(String(32), index=True)
    dst_id: Mapped[str] = mapped_column(String(32), index=True)
    provenance: Mapped[str] = mapped_column(String(16), default="observed")  # observed|inferred|derived
    rule: Mapped[str] = mapped_column(String(256), default="")
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    time_start: Mapped[date | None] = mapped_column(Date, default=None)
    time_end: Mapped[date | None] = mapped_column(Date, default=None)

    __table_args__ = (
        Index("ix_edge_triple", "workspace_id", "src_id", "dst_id", "edge_type"),
    )


# --- Evidence, conversations, reports --------------------------------------------------------


class EvidenceRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "evidence_records"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[int] = mapped_column(Integer)
    source_name: Mapped[str] = mapped_column(String(256), default="")
    evidence_type: Mapped[str] = mapped_column(String(32))  # measured_fact|feedback|product_fact|derived
    campaign_id: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    metric_name: Mapped[str | None] = mapped_column(String(128), default=None)
    metric_value: Mapped[float | None] = mapped_column(Float, default=None)
    metric_unit: Mapped[str | None] = mapped_column(String(32), default=None)
    metric_definition: Mapped[str] = mapped_column(String(512), default="")
    date_start: Mapped[date | None] = mapped_column(Date, default=None)
    date_end: Mapped[date | None] = mapped_column(Date, default=None)
    excerpt: Mapped[str] = mapped_column(LongText, default="")
    locator: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class Conversation(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversations"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    created_by: Mapped[str] = mapped_column(String(32), index=True)


class ConversationMessage(Base, IdMixin):
    __tablename__ = "conversation_messages"
    conversation_id: Mapped[str] = mapped_column(String(32), index=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(LongText)
    structured: Mapped[dict[str, Any] | None] = mapped_column(JSONType, default=None)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONType, default=list)
    model: Mapped[str] = mapped_column(String(128), default="")
    prompt_version: Mapped[str] = mapped_column(String(32), default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    abstention_reason: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Report(Base, IdMixin, TimestampMixin):
    __tablename__ = "reports"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    campaign_id: Mapped[str] = mapped_column(String(32), index=True)
    date_start: Mapped[date | None] = mapped_column(Date, default=None)
    date_end: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(String(16), default="ready")
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_by: Mapped[str] = mapped_column(String(32))


class PendingReviewItem(Base, IdMixin, TimestampMixin):
    """Brand/content approval queue — nothing publishes without review."""

    __tablename__ = "pending_reviews"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    item_type: Mapped[str] = mapped_column(String(32))  # content|report_publish|mapping
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    requested_by: Mapped[str] = mapped_column(String(32))
    decided_by: Mapped[str | None] = mapped_column(String(32), default=None)


# --- Semantic cache ---------------------------------------------------------------------------


class CacheEntry(Base, IdMixin, TimestampMixin):
    __tablename__ = "cache_entries"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    validity: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    __table_args__ = (Index("ix_cache_best", "workspace_id", "key_hash"),)


# --- Evaluation --------------------------------------------------------------------------------


class EvaluationRun(Base, IdMixin):
    __tablename__ = "evaluation_runs"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    dataset_version: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(64))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# --- Local model connector (Ollama companion) ---------------------------------------------------


class LocalConnector(Base, IdMixin, TimestampMixin):
    __tablename__ = "local_connectors"
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    pairing_code_hash: Mapped[str] = mapped_column(String(128), default="")
    pairing_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    status: Mapped[str] = mapped_column(String(24), default="pending")  # pending|paired|disconnected|revoked
    selected_model: Mapped[str] = mapped_column(String(128), default="")
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    access_token_hash: Mapped[str] = mapped_column(String(128), default="")
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class ModelRequest(Base, IdMixin):
    """Queued inference work drained by the customer's local connector.

    The connector polls an authenticated outbound endpoint; there is no
    inbound listener on customer machines.
    """

    __tablename__ = "model_requests"
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    connector_id: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)  # queued|claimed|completed|failed|cancelled
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONType, default=None)
    error: Mapped[str] = mapped_column(String(512), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


def utcnow_alias() -> datetime:  # re-exported for migrations/scripts
    return utcnow()
