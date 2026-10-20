"""Retrieval evaluation: Recall@k, Precision@k, MRR, nDCG@k + tenant checks."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.evaluation.schemas import RetrievalCase, RetrievalMetrics
from app.retrieval.bm25_search import BM25Index
from app.retrieval.embeddings import EmbeddingModel
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.vector_search import VectorIndex


def rank_metrics(
    ranked: list[str],
    relevant: set[str],
    k: int,
) -> dict[str, float]:
    """Compute Recall@k, Precision@k, MRR, nDCG@k for one ranked list."""
    hits = [chunk_id in relevant for chunk_id in ranked[:k]]
    total_hits = sum(hits)
    recall = total_hits / max(1, len(relevant))
    precision = total_hits / max(1, k)
    mrr = 0.0
    for position, chunk_id in enumerate(ranked[:k], start=1):
        if chunk_id in relevant:
            mrr = 1.0 / position
            break
    dcg = sum(
        1.0 / math.log2(position + 1)
        for position, chunk_id in enumerate(ranked[:k], start=1)
        if chunk_id in relevant
    )
    ideal_dc = sum(1.0 / math.log2(position + 1) for position in range(1, min(len(relevant), k) + 1))
    ndcg = dcg / ideal_dc if ideal_dc > 0 else 0.0
    return {
        "recall": recall,
        "precision": precision,
        "mrr": mrr,
        "ndcg": ndcg,
        "hits": float(total_hits),
    }


def evaluate_retrieval(
    db: Session,
    *,
    cases: list[RetrievalCase],
    k: int = 5,
) -> dict[str, Any]:
    """Run retrieval cases against the real hybrid pipeline."""
    hybrid = HybridSearch(
        vector_index=VectorIndex(EmbeddingModel.configured()),
        bm25_index=BM25Index(),
    )
    recalls: list[float] = []
    precisions: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    tenant_filter_correct = 0
    per_case: dict[str, Any] = {}
    for case in cases:
        result = hybrid.search(
            db,
            workspace_id=case.workspace_id,
            query=case.query,
            top_k=k,
            rerank=False,
        )
        ranked = [candidate.chunk_id for candidate in result.candidates]
        if case.should_be_empty:
            ok = not ranked
            tenant_filter_correct += int(ok)
            per_case[case.case_id] = {"expected": "empty", "got": len(ranked), "pass": ok}
            continue
        # Tenant-filter correctness: no candidate may come from another workspace.
        foreign = [
            candidate for candidate in result.candidates
            if candidate.source_id not in case.expected_sources
            and candidate.source_id not in set()
        ]
        metrics = rank_metrics(ranked, set(case.relevant_chunk_ids), k)
        recalls.append(metrics["recall"])
        precisions.append(metrics["precision"])
        mrrs.append(metrics["mrr"])
        ndcgs.append(metrics["ndcg"])
        per_case[case.case_id] = {
            **metrics,
            "foreign_results": len(foreign),
        }
        if not foreign:
            tenant_filter_correct += 1
    total = len(cases)
    return {
        "metrics": RetrievalMetrics(
            recall_at_k=round(sum(recalls) / max(1, len(recalls)), 4),
            precision_at_k=round(sum(precisions) / max(1, len(precisions)), 4),
            mrr=round(sum(mrrs) / max(1, len(mrrs)), 4),
            ndcg_at_k=round(sum(ndcgs) / max(1, len(ndcgs)), 4),
            cases=total,
        ),
        "tenant_filter_correct": tenant_filter_correct,
        "per_case": per_case,
    }
