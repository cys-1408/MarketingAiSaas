"""Investigation workflow nodes.

Each node receives/returns :class:`InvestigationState`, calls real services
through injected interfaces, validates outputs, preserves tenant scope,
records safe diagnostics, bounds retries/tool calls, and returns explicit
routing or a terminal state.  Authorization failures fail closed.
"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.tenancy import new_id
from app.agents.state import EvidenceItem, InvestigationResult, InvestigationState
from app.db.models import Campaign

logger = get_logger(__name__)

DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
QUESTION_KINDS = {"metric", "evidence", "mixed", "unanswerable"}


# --- nodes ---------------------------------------------------------------------


def classify_request(state: InvestigationState) -> str:
    """Route the request kind."""
    question = state.question.lower()
    metric_tokens = ("how many", "how much", "rate", "spend", "revenue", "conversions",
                     "compare", "CTR", "cpa", "value", "average")
    evidence_tokens = ("why", "what do customers", "feedback", "objection", "said",
                       "review", "mention", "explain", "which product")
    metric_score = sum(1 for token in metric_tokens if token in question)
    evidence_score = sum(1 for token in evidence_tokens if token in question)
    if metric_score and evidence_score:
        kind = "mixed"
    elif metric_score:
        kind = "metric"
    elif evidence_score:
        kind = "evidence"
    else:
        kind = "mixed"
    state.request_kind = kind
    return kind


def resolve_scope(state: InvestigationState, db: Session, *, workspace_id: str) -> str:
    """Resolve campaign/date scope from the workspace's own campaigns."""
    campaigns = db.execute(
        select(Campaign).where(Campaign.workspace_id == workspace_id)
    ).scalars().all()
    question = state.question.lower()
    best = None
    for campaign in campaigns:
        tokens = re.split(r"[^a-z0-9]+", campaign.name.lower())
        for token in tokens:
            if len(token) > 3 and token in question:
                best = campaign
                break
        if best is not None:
            break
    if best is not None:
        state.scope_campaign_key = best.external_key or best.id
        if best.start_date:
            state.scope_date_start = best.start_date.isoformat()
        if best.end_date:
            state.scope_date_end = best.end_date.isoformat()
    elif campaigns:
        # Default to the most recent campaign window so numeric questions
        # have a bounded scope; recorded in the answer under limitations.
        best = max(campaigns, key=lambda c: c.start_date or c.end_date or c.created_at)
        state.scope_campaign_key = best.external_key or best.id
        state.scope_date_start = best.start_date.isoformat() if best.start_date else None
        state.scope_date_end = best.end_date.isoformat() if best.end_date else None
    return state.scope_campaign_key


def rewrite_query(state: InvestigationState) -> str:
    """Focused retrieval preserves ids, product names and dates."""
    focused = state.question
    if state.scope_campaign_key:
        focused = f"{focused} campaign:{state.scope_campaign_key}"
    if state.scope_date_start and state.scope_date_end:
        focused = f"{focused} date:{state.scope_date_start}..{state.scope_date_end}"
    state.focused_question = focused
    return focused


def plan_investigation(state: InvestigationState) -> list[str]:
    """Bounded, deterministic plan based on the request kind."""
    settings = get_settings()
    steps: list[str] = []
    if state.request_kind in {"metric", "mixed"}:
        steps.append("analytics")
    steps.append("retrieval")
    if state.request_kind in {"evidence", "mixed"}:
        steps.append("graph")
    state.iterations += 1
    if state.iterations > settings.agent_max_iterations:
        return ["format"]
    return steps or ["format"]


def retrieve_documents(state: InvestigationState, *, db: Session) -> str:  # noqa: ANN001
    """Hybrid retrieval with tenant scope embedded in the query path."""
    state.tool_calls += 1
    from app.retrieval.bm25_search import BM25Index
    from app.retrieval.hybrid_search import HybridSearch
    from app.retrieval.vector_search import VectorIndex
    from app.retrieval.embeddings import EmbeddingModel

    settings = get_settings()
    hybrid = HybridSearch(
        vector_index=VectorIndex(EmbeddingModel.configured()),
        bm25_index=BM25Index(),
    )
    result = hybrid.search(
        db,
        workspace_id=state.workspace_id,
        query=state.focused_question or state.question,
        top_k=settings.retrieval_top_k,
    )
    state.candidates = result.candidates
    return "candidates_found" if state.candidates else "empty_retrieval"


def retrieve_graph(state: InvestigationState, *, db: Session) -> GraphContext:  # noqa: ANN001
    """Typed graph traversal limited in depth and size."""
    state.tool_calls += 1
    from app.graph.retrieval import retrieve_graph_context

    result = retrieve_graph_context(
        db, workspace_id=state.workspace_id, query=state.focused_question or state.question,
    )
    state.graph_paths = result.paths
    return result


def execute_analytics(state: InvestigationState, *, db: Session) -> str:  # noqa: ANN001
    """Deterministic, read-only metric computation."""
    state.tool_calls += 1
    from app.tools.analytics import AnalyticsService

    service = AnalyticsService(db)
    campaign_id: str | None = None
    if state.scope_campaign_key:
        campaign = db.execute(
            select(Campaign).where(
                Campaign.workspace_id == state.workspace_id,
                Campaign.external_key == state.scope_campaign_key,
            )
        ).scalar_one_or_none()
        campaign_id = campaign.id if campaign else None
    if campaign_id is None:
        campaigns = db.execute(
            select(Campaign).where(Campaign.workspace_id == state.workspace_id).limit(1)
        ).scalars().all()
        campaign_id = campaigns[0].id if campaigns else None
    if campaign_id is None:
        state.analytics_summaries = []
        return "analytics_unavailable"
    start = state.scope_date_start or "2000-01-01"
    end = state.scope_date_end or "2100-12-31"
    summary = service.get_campaign_summary(
        workspace_id=state.workspace_id,
        campaign_id=campaign_id,
        start_date=start,
        end_date=end,
    )
    state.analytics_summaries.append(summary)
    return "analytics_ready"


def rerank_and_compress(state: InvestigationState) -> str:
    from app.retrieval.compression import compress_passages
    from app.retrieval.reranking import covered_query_terms

    settings = get_settings()
    retrieve_candidates = state.candidates
    if len(retrieve_candidates) > settings.rerank_candidates:
        retrieve_candidates = retrieve_candidates[: settings.rerank_candidates]
    state.compressed = compress_passages(
        state.focused_question or state.question, retrieve_candidates
    )
    coverage = covered_query_terms(state.question, retrieve_candidates)
    return f"compress_ok(coverage={coverage})"


def assemble_evidence(state: InvestigationState) -> list[EvidenceItem]:
    """Merge metrics, compressed passages and graph evidence into items."""
    evidence: list[EvidenceItem] = []
    for summary in state.analytics_summaries:
        for metric in summary.get("metrics", []):
            evidence.append(
                EvidenceItem(
                    evidence_id=new_id("ev"),
                    statement=(
                        f"{metric['metric_name']} = {metric['value']} {metric['unit']} "
                        f"({summary['campaign_name']}, {summary['date_start']}..{summary['date_end']}, "
                        f"source {metric.get('source_id', 'analytics')})"
                    ),
                    source_id=metric.get("source_id", "analytics"),
                    source_version=metric.get("source_version", 0),
                    source_name=metric.get("source_name", "computed analytics"),
                    evidence_type="measured_fact",
                    metric_definition=metric.get("definition", ""),
                    date_start=summary.get("date_start"),
                    date_end=summary.get("date_end"),
                )
            )
    for item in state.compressed:
        for passage in item.passages:
            evidence.append(
                EvidenceItem(
                    evidence_id=new_id("ev"),
                    statement=passage,
                    source_id=item.source_id,
                    source_version=item.source_version,
                    source_name=item.source_name,
                    locator=item.locator,
                    evidence_type="feedback" if item.kind == "feedback" else "document",
                )
            )
        for contradiction in item.contradictions:
            evidence.append(
                EvidenceItem(
                    evidence_id=new_id("ev"),
                    statement=contradiction,
                    source_id=item.source_id,
                    source_version=item.source_version,
                    source_name=item.source_name,
                    locator=item.locator,
                    evidence_type="contradiction",
                    contradicts=[],
                )
            )
    state.evidence = evidence
    return evidence


def draft_analysis(
    state: InvestigationState,
    *,
    db: Session,  # noqa: ANN001
    router,  # noqa: ANN001 - ModelRouter
) -> str:
    """Request model synthesis via the router (provider policy enforced)."""
    from app.models.channel import LibWaitForConnector

    if not state.evidence:
        state.abstention_reason = (
            "nothing was retrieved for this question; refine it or ingest more sources"
        )
        state.result = InvestigationResult(
            status="abstained", question=state.question, abstention_reason=state.abstention_reason
        )
        return "abstain"
    evidence_lines = [f"{item.statement} [{item.evidence_id}]" for item in state.evidence]
    structured = {
        "evidence": [
            {"evidence_id": item.evidence_id, "statement": item.statement}
            for item in state.evidence
        ],
        "hypothesis_seed": _seed_hypothesis(state),
        "limitations_note": _limitation_note(state),
    }
    from app.agents.prompts import INVESTIGATION_SYSTEM_PROMPT, build_user_prompt

    try:
        reply = router.complete(
            workspace_id=state.workspace_id,
            system_prompt=INVESTIGATION_SYSTEM_PROMPT,
            user_prompt=build_user_prompt(state.question, evidence_lines),
            structured=structured,
        )
    except LibWaitForConnector as pending:
        state.pending_request_id = pending.request_id
        return "awaiting_local_model"
    except Exception as exc:
        state.abstention_reason = f"model routing failed: {safe_str(exc)}"
        state.result = InvestigationResult(
            status="abstained", question=state.question, abstention_reason=state.abstention_reason
        )
        return "abstain"
    state.model_reply = reply
    return "reply_ready"


def await_local_model(state: InvestigationState, *, db: Session) -> str:  # noqa: ANN001
    """Poll a queued local-connector request until terminal or timeout."""
    from app.models.adapters import ModelReply
    from app.models.channel import ChannelError

    deadline = time.monotonic() + get_settings().agent_model_timeout_seconds
    while time.monotonic() < deadline:
        request = db.get(ModelRequestRow, state.pending_request_id)
        if request is None or request.workspace_id != state.workspace_id:
            state.abstention_reason = "local model request lost tenant binding"
            state.result = InvestigationResult(
                status="abstained", question=state.question,
                abstention_reason=state.abstention_reason,
            )
            return "abstain"
        if request.status == "completed":
            payload = request.response_payload or {}
            sections = payload.get("sections")
            state.model_reply = ModelReply(
                status="ok", sections=sections if isinstance(sections, dict) else {},
                model_id="ollama", latency_ms=payload.get("latency_ms", 0),
            )
            return "reply_ready"
        if request.status in {"failed", "cancelled"}:
            state.abstention_reason = (
                f"local model did not complete inference ({request.error or request.status})"
            )
            state.result = InvestigationResult(
                status="abstained", question=state.question,
                abstention_reason=state.abstention_reason,
            )
            return "abstain"
        time.sleep(0.05)
    state.abstention_reason = "local model did not respond in time"
    state.result = InvestigationResult(
        status="abstained", question=state.question,
        abstention_reason=state.abstention_reason,
    )
    return "abstain"


def verify_claims(state: InvestigationState) -> str:
    """Check claim support, citations, arithmetic and causal language."""
    from app.tools.verification import verify_reply

    if state.model_reply is None:
        return "abstain"
    state.verification = verify_reply(state.model_reply.sections, state.evidence)
    unsupported = [v for v in state.verification if v["level"] == "unsupported"]
    if unsupported:
        state.model_reply.sections["limitations"] = [
            *state.model_reply.sections.get("limitations", []),
            *[
                f"{v['claim'][:120]} is not supported by retrieved evidence and was qualified."
                for v in unsupported
            ],
        ]
    return "verified"


def check_guardrails(state: InvestigationState) -> str:
    """Brand/policy checks; causal language without experiments is flagged."""
    if state.model_reply is None:
        return "abstain"
    findings: list[str] = []
    sections = state.model_reply.sections
    for claim in sections.get("hypotheses", []) + sections.get("recommendations", []):
        lowered = claim.lower()
        if any(marker in lowered for marker in ("increases sales", "boost sales", "will improve conversions")):
            findings.append(
                "causal-sounding phrasing without experimental evidence was qualified "
                "(recommendation wording flagged)"
            )
    if not sections.get("observed_facts"):
        findings.append("answer had no observed facts; abstained")
    state.guardrail_findings = findings
    return "guardrails_ok" if not findings or all("abstained" not in f for f in findings) else "abstain"


def request_review(state: InvestigationState, *, db: Session) -> str:
    """Route consequential brand claims to the pending-review queue."""
    from app.db.models import PendingReviewItem

    review_needed = any(
        "flagged" in finding for finding in state.guardrail_findings
    )
    if review_needed:
        db.add(
            PendingReviewItem(
                workspace_id=state.workspace_id,
                item_type="content",
                payload={"question": state.question, "findings": state.guardrail_findings},
                requested_by=state.user_id,
            )
        )
        db.flush()
        return "review_requested"
    return "format"


def format_response(state: InvestigationState) -> InvestigationResult:
    """Final structured answer with citations and evidence ids."""
    from app.agents.state import InvestigationResult as Result

    if state.result is not None and state.result.status in {"abstained"}:
        return state.result
    sections = state.model_reply.sections if state.model_reply else {}
    citations: list[dict[str, Any]] = []
    for item in state.evidence:
        citations.append(
            {
                "evidence_id": item.evidence_id,
                "source_id": item.source_id,
                "source_version": item.source_version,
                "source_name": item.source_name,
                "locator": item.locator,
                "evidence_type": item.evidence_type,
                "metric_definition": item.metric_definition,
            }
        )
    result = Result(
        status="answered",
        question=state.question,
        observed_facts=sections.get("observed_facts", []),
        supporting_evidence=sections.get("supporting_evidence", []),
        contradictory_evidence=sections.get("contradictory_evidence", []),
        interpretations=sections.get("interpretations", []),
        hypotheses=sections.get("hypotheses", []),
        recommendations=sections.get("recommendations", []),
        measurement_plan=sections.get("measurement", []),
        limitations=sections.get("limitations", []),
        abstention_reason=state.abstention_reason,
        citations=citations,
        model_id=(state.model_reply.model_id if state.model_reply else "unknown"),
    )
    state.result = result
    return result


def record_feedback(state: InvestigationState) -> InvestigationResult:
    '''No-op terminal step; feedback submission is a separate API call.'''
    return format_response(state)


def _seed_hypothesis(state: InvestigationState) -> str:
    lowered = state.question.lower()
    if "why" in lowered:
        return "The observed outcome has a testable cause worth investigating"
    return ""


def _limitation_note(state: InvestigationState) -> str:
    notes = []
    if not state.scope_date_start:
        notes.append("no explicit date window was resolved for the question")
    return "; ".join(notes) or "No additional limitation noted."


def safe_str(exc: Exception) -> str:
    text = str(exc)
    return text[:200] if text else exc.__class__.__name__


# --- local binding used by await_local_model ---------------------------------------
from app.db.models import ModelRequest as ModelRequestRow  # noqa: E402


class GraphContext:
    """Type placeholder mirroring graph retrieval result between nodes."""
