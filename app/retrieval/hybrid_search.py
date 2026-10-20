"""Hybrid retrieval: vector + BM25Candidates fused via reciprocal rank fusion.

Tenant/permission/date/source filters are applied to both candidate lists
before fusion, and each candidate keeps a record of which retriever produced
it plus its rank contribution — so fusion is auditable and debuggable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.retrieval.bm25_search import BM25Index, BM25Hit
from app.retrieval.vector_search import VectorHit, VectorIndex


@dataclass(slots=True)
class FusedCandidate:
    chunk_id: str
    fused_score: float
    text: str
    title: str
    source_id: str
    source_version: int
    source_name: str
    locator: dict[str, Any]
    kind: str
    contributions: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class HybridResult:
    candidates: list[FusedCandidate]
    diagnostics: dict[str, Any]


_RRF_K = 60


def _hit_key(hit: object) -> str:  # noqa: ANN201 - shared key shape
    return str(hit.chunk_id)


def fuse(
    vector_hits: list[VectorHit],
    bm25_hits: list[BM25Hit],
) -> tuple[dict[str, FusedCandidate], dict[str, Any]]:
    """Reciprocal-rank-fusion of both ranked lists."""
    fused: dict[str, FusedCandidate] = {}
    diagnostics: dict[str, int] = {"vector": 0, "bm25": 0}

    def add(hit: object, retriever: str) -> None:  # noqa: ANN001
        index = (vector_hits if retriever == "vector" else bm25_hits).index(hit)
        contribution = 1.0 / (_RRF_K + index + 1)
        key = _hit_key(hit)
        candidate = fused.get(key)
        if candidate is None:
            candidate = FusedCandidate(
                chunk_id=str(hit.chunk_id),
                fused_score=0.0,
                text=hit.text,
                title=hit.title,
                source_id=hit.source_id,
                source_version=hit.source_version,
                source_name=hit.source_name,
                locator=hit.locator,
                kind=hit.kind,
            )
            fused[key] = candidate
        candidate.fused_score += contribution
        candidate.contributions[retriever] = round(contribution, 6)
        diagnostics[retriever] += 1

    for hit in vector_hits:
        add(hit, "vector")
    for hit in bm25_hits:
        add(hit, "bm25")
    return fused, diagnostics


class HybridSearch:
    """Tenant-scoped hybrid retrieval used by investigations and chat."""

    def __init__(self, vector_index: VectorIndex, bm25_index: BM25Index) -> None:
        self.vector_index = vector_index
        self.bm25_index = bm25_index

    def search(
        self,
        db: Session,
        *,
        workspace_id: str,
        query: str,
        top_k: int,
        allowed_source_ids: set[str] | None = None,
        rerank: bool = True,
    ) -> HybridResult:
        vector_hits = self.vector_index.search(
            db,
            workspace_id=workspace_id,
            query=query,
            top_k=top_k,
            allowed_source_ids=allowed_source_ids,
        )
        bm25_hits = self.bm25_index.search(
            db,
            workspace_id=workspace_id,
            query=query,
            top_k=top_k,
            allowed_source_ids=allowed_source_ids,
        )
        fused, diagnostics = fuse(vector_hits, bm25_hits)
        candidates = sorted(fused.values(), key=lambda c: c.fused_score, reverse=True)
        if rerank:
            candidates = rerank_lexical(query, candidates, limit=top_k)
        else:
            candidates = candidates[:top_k]
        return HybridResult(
            candidates=candidates,
            diagnostics={
                **diagnostics,
                "fused_results": len(candidates),
                "fusion": "reciprocal_rank_fusion(k=$RRF_K)".replace("$RRF_K", str(_RRF_K)),
            },
        )


def rerank_lexical(
    query: str, candidates: list[FusedCandidate], *, limit: int
) -> list[FusedCandidate]:
    """Lexical-overlap re-scoring that preserves candidate identity."""
    from app.retrieval.embeddings import tokenize

    query_terms = set(tokenize(query))
    if not query_terms:
        return candidates[:limit]

    def relevance(candidate: FusedCandidate) -> float:
        terms = set(tokenize(candidate.text))
        return candidate.fused_score * (len(terms & query_terms) + 1) / (len(query_terms) + 1)

    scored = sorted(
        ((relevance(candidate), candidate) for candidate in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [candidate for _, candidate in scored[:limit]]
