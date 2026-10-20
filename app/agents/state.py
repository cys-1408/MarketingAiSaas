"""Typed LangGraph investigation state.

State carries tenant scope explicitly (losing it is a programming error the
workflow guards against), retrieval/graph candidates, assembled evidence,
claim verification and guardrail results, plus bounded retry counters.
Sensitive content is minimized: no raw dumps, only what each node needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EvidenceItem:
    evidence_id: str
    statement: str
    source_id: str
    source_version: int
    source_name: str
    locator: dict[str, Any] = field(default_factory=dict)
    evidence_type: str = "measured_fact"
    metric_definition: str = ""
    date_start: str | None = None
    date_end: str | None = None
    contradicts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InvestigationResult:
    status: str  # answered|abstained|needs_clarification|failed_guardrails
    question: str
    observed_facts: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    contradictory_evidence: list[str] = field(default_factory=list)
    interpretations: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    measurement_plan: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    abstention_reason: str = ""
    clarification_question: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    model_id: str = ""
    ai_generated: bool = True


@dataclass(slots=True)
class InvestigationState:
    """LangGraph state; nodes receive and return this object."""

    request_id: str
    workspace_id: str
    user_id: str
    question: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    # resolved scope / routing
    request_kind: str = ""  # metric|evidence|mixed|unanswerable
    focused_question: str = ""
    scope_campaign_key: str = ""
    scope_date_start: str | None = None
    scope_date_end: str | None = None

    # retrieval
    candidates: list[Any] = field(default_factory=list)
    compressed: list[Any] = field(default_factory=list)
    graph_paths: list[Any] = field(default_factory=list)
    analytics_summaries: list[dict[str, Any]] = field(default_factory=list)

    # assembled + verified
    evidence: list[EvidenceItem] = field(default_factory=list)
    verification: list[dict[str, Any]] = field(default_factory=list)
    guardrail_findings: list[str] = field(default_factory=list)

    # model interaction
    model_reply: ModelReply | None = None
    pending_request_id: str = ""
    abstention_reason: str = ""

    # bounds and diagnostics
    tool_calls: int = 0
    iterations: int = 0
    started_at_ms: int = 0
    result: InvestigationResult | None = None

    def tenant_scope(self) -> tuple[str, str]:
        """Never allow a node to operate without explicit tenant context."""
        if not self.workspace_id or not self.user_id:
            raise RuntimeError("investigation state lost tenant scope")
        return self.workspace_id, self.user_id
