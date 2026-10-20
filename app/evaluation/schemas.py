"""Typed evaluation schemas (versioned)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DATASET_VERSION = "v1"


@dataclass(slots=True)
class RetrievalCase:
    case_id: str
    workspace_id: str
    query: str
    relevant_chunk_ids: list[str]
    expected_sources: list[str]
    should_be_empty: bool = False


@dataclass(slots=True)
class AnswerCase:
    case_id: str
    question: str
    expected_behavior: str  # answered|abstained
    expected_evidence_sources: list[str] = field(default_factory=list)
    expected_numbers: list[str] = field(default_factory=list)
    forbid_causal_claim: bool = True


@dataclass(slots=True)
class ToolCase:
    case_id: str
    question: str
    expected_tools: list[str]
    forbidden_tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MappingCase:
    case_id: str
    headers: list[str]
    category: str
    expected_mappings: dict[str, str]
    expects_review: bool = False


@dataclass(slots=True)
class RetrievalMetrics:
    recall_at_k: float
    precision_at_k: float
    mrr: float
    ndcg_at_k: float
    cases: int


@dataclass(slots=True)
class AnswerMetrics:
    citation_correctness: float
    numeric_accuracy: float
    abstention_correctness: float
    causal_language_violations: int
    cases: int


@dataclass(slots=True)
class AgentMetrics:
    tool_choice_correctness: float
    forbidden_tool_calls: int
    completion_rate: float
    avg_latency_ms: float
    cases: int


@dataclass(slots=True)
class IngestionMetrics:
    mapping_accuracy: float
    review_request_rate: float
    parsing_success_rate: float
    duplicate_detection: float
    cases: int


@dataclass(slots=True)
class EvaluationRunResult:
    dataset_version: str = DATASET_VERSION
    metrics: dict[str, Any] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)
