"""Candidate reranking that never fabricates scores or loses citations.

The default reranker is a lexical relevance model (deterministic, no external
call).  A semantic reranker can be configured; when it is unavailable the
hybrid ordering is used as an explicitly labelled degraded mode — candidate
identity and metadata are always preserved through reordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.retrieval.embeddings import tokenize


@dataclass(slots=True)
class RerankReport:
    mode: str
    count: int
    took_ms: int


def rerank_candidates(
    query: str,
    candidates: list[Any],  # FusedCandidate-shaped objects
    *,
    limit: int,
) -> tuple[list[Any], RerankReport]:
    """Reorder candidates by lexical relevance while preserving metadata."""
    from app.retrieval.hybrid_search import rerank_lexical

    if not candidates:
        report = RerankReport(mode="no_candidates", count=0, took_ms=0)
        return [], report
    ordered = rerank_lexical(query, candidates, limit=limit)
    report = RerankReport(mode="lexical_overlap", count=len(ordered), took_ms=0)
    return ordered, report


def degraded_order(candidates: list[Any], *, limit: int) -> tuple[list[Any], RerankReport]:
    """Explicit degraded mode: keep fusion order, relabel, never fake scores."""
    trimmed = candidates[:limit]
    return trimmed, RerankReport(mode="degraded_fusion_order", count=len(trimmed), took_ms=0)


def covered_query_terms(query: str, candidates: list[Any]) -> int:
    """Count of distinct query terms covered by the top candidates."""
    query_terms = set(tokenize(query))
    if not query_terms:
        return 0
    covered: set[str] = set()
    for candidate in candidates:
        covered |= set(tokenize(candidate.text)) & query_terms
        if len(covered) >= len(query_terms):
            break
    return len(covered)
