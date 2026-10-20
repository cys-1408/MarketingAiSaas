"""Lexical BM25 retrieval for exact campaign ids, product names and phrases.

Tokens are stored with each chunk so the workspace index can be
incrementally maintained; queries preserve exact identifiers (no stemming
that would break "campaign_c7" matching) while normalizing case.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk
from app.retrieval.embeddings import tokenize


@dataclass(slots=True)
class BM25Hit:
    chunk_id: str
    score: float
    source_id: str
    source_version: int
    source_name: str
    title: str
    text: str
    locator: dict[str, Any]
    kind: str


_K1 = 1.4
_B = 0.72


class BM25Index:
    """Inverted index over stored chunks, scoped per workspace at query time."""

    def search(
        self,
        db: Session,
        *,
        workspace_id: str,
        query: str,
        top_k: int,
        allowed_source_ids: set[str] | None = None,
    ) -> list[BM25Hit]:
        query_terms = tokenize(query)
        if not query_terms:
            return []
        stmt = select(Chunk).where(Chunk.workspace_id == workspace_id)
        if allowed_source_ids is not None:
            if not allowed_source_ids:
                return []
            stmt = stmt.where(Chunk.source_id.in_(allowed_source_ids))
        chunks = db.scalars(stmt).all()

        doc_tokens: list[list[str]] = []
        for chunk in chunks:
            tokens = chunk.tokens or tokenize(f"{chunk.title} {chunk.text}")
            doc_tokens.append(tokens)
        doc_count = len(doc_tokens)
        if doc_count == 0:
            return []
        avg_len = sum(len(t) for t in doc_tokens) / doc_count
        df = Counter()
        for tokens_i in doc_tokens:
            df.update(set(tokens_i))

        scores: list[tuple[float, int]] = []
        for index, tokens_i in enumerate(doc_tokens):
            tf = Counter(tokens_i)
            length = len(tokens_i) or 1
            score = 0.0
            for term in query_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (doc_count - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * (
                    tf[term] * (_K1 + 1)
                    / (tf[term] + _K1 * (1 - _B + _B * length / (avg_len or 1)))
                )
            if score > 0:
                scores.append((score, index))
        scores.sort(key=lambda pair: pair[0], reverse=True)
        hits: list[BM25Hit] = []
        for score, index in scores[:top_k]:
            chunk = chunks[index]
            hits.append(
                BM25Hit(
                    chunk_id=chunk.id,
                    score=round(score, 4),
                    source_id=chunk.source_id,
                    source_version=chunk.source_version,
                    source_name=chunk.source_name,
                    title=chunk.title,
                    text=chunk.text,
                    locator=chunk.locator,
                    kind=chunk.kind,
                )
            )
        return hits
