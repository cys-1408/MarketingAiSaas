"""Vector index backed by the relational store.

Chunks are upserted with tenant/workspace metadata and searched with
tenant-scoped filters applied inside the query — never only after
generation.  Source deletion removes the source's chunks; re-embedding a new
source version replaces prior vectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk
from app.retrieval.embeddings import EmbeddingModel, cosine_similarity, tokenize


@dataclass(slots=True)
class VectorHit:
    chunk_id: str
    score: float
    source_id: str
    source_version: int
    source_name: str
    title: str
    text: str
    locator: dict[str, Any]
    kind: str


class VectorIndex:
    """Tenant-scoped vector store over persisted chunks."""

    def __init__(self, model: EmbeddingModel) -> None:
        self.model = model

    def upsert_index(
        self,
        db: Session,
        *,
        workspace_id: str,
        source_id: str,
        source_version: int,
        source_name: str,
        chunks: list[dict[str, Any]],
        previous_versions: list[int],
    ) -> int:
        """Insert embeddings for new chunks; replaces prior-version vectors."""
        for version in previous_versions:
            db.execute(
                Chunk.__table__.delete().where(
                    Chunk.source_id == source_id,
                    Chunk.source_version == version,
                )
            )
        count = 0
        for i, chunk in enumerate(chunks):
            embedding = self.model.embed_one(chunk["text"])
            fingerprint = chunk["fingerprint"]
            db.add(
                Chunk(
                    workspace_id=workspace_id,
                    source_id=source_id,
                    source_version=source_version,
                    source_name=source_name,
                    kind=chunk.get("kind", "narrative"),
                    title=chunk.get("title", ""),
                    text=chunk["text"],
                    locator=chunk.get("locator", {}),
                    embedding=embedding,
                    embedding_model=self.model.version,
                    tokens=tokenize(chunk["text"]),
                    checksum_fingerprint=fingerprint,
                    version_fingerprint=f"{source_id}:{source_version}:{fingerprint}:{i}",
                )
            )
            count += 1
        return count

    def search(
        self,
        db: Session,
        *,
        workspace_id: str,
        query: str,
        top_k: int,
        allowed_source_ids: set[str] | None = None,
    ) -> list[VectorHit]:
        """Tenant-scoped similarity search; candidates filtered pre-scoring."""
        query_vector = self.model.embed_one(query)
        stmt = select(Chunk).where(Chunk.workspace_id == workspace_id)
        if allowed_source_ids is not None:
            if not allowed_source_ids:
                return []
            stmt = stmt.where(Chunk.source_id.in_(allowed_source_ids))
        scored: list[tuple[float, Chunk]] = []
        for chunk in db.scalars(stmt):
            vector = chunk.embedding or []
            score = cosine_similarity(query_vector, vector)
            if score > 0.01:
                scored.append((score, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            VectorHit(
                chunk_id=chunk.id,
                score=round(float(score), 4),
                source_id=chunk.source_id,
                source_version=chunk.source_version,
                source_name=chunk.source_name,
                title=chunk.title,
                text=chunk.text,
                locator=chunk.locator,
                kind=chunk.kind,
            )
            for score, chunk in scored[:top_k]
        ]

    def delete_for_source(self, db: Session, workspace_id: str, source_id: str) -> int:
        result = db.execute(
            Chunk.__table__.delete().where(
                Chunk.workspace_id == workspace_id,
                Chunk.source_id == source_id,
            )
        )
        return int(result.rowcount or 0)
