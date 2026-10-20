"""Permission-aware semantic cache.

Caches investigation answers only when tenant, permissions, source
versions, metric definitions, and model/prompt versions still match.
Invalidation is wired into source ingestion/deletion and permission changes;
cache hits re-verify authorization — a hit never bypasses tenancy.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import CacheEntry
from app.retrieval.embeddings import EmbeddingModel, cosine_similarity

_SIMILARITY_THRESHOLD = 0.97


def _now():  # noqa: ANN201
    from datetime import datetime, timezone as dt_timezone

    return datetime.now(dt_timezone.utc)


@dataclass(slots=True)
class CacheValidity:
    permission_rank: int
    source_versions: dict[str, int]
    metric_definition_versions: int
    model_id: str
    prompt_version: str

    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(self.__dict__, sort_keys=True).encode()
        ).hexdigest()[:32]


class SemanticCache:
    def __init__(self, db: Session, model: EmbeddingModel | None = None) -> None:
        self.db = db
        self.model = model or EmbeddingModel.configured()

    def _embed_key(self, question: str) -> list[float]:
        return self.model.embed_one(question.lower().strip())

    def lookup(
        self,
        *,
        workspace_id: str,
        question: str,
        validity: CacheValidity,
    ) -> dict[str, Any] | None:
        """Return a cached payload only when ALL validity dimensions match."""
        settings = get_settings()
        query_vector = self._embed_key(question)
        candidates = self.db.execute(
            select(CacheEntry).where(CacheEntry.workspace_id == workspace_id)
        ).scalars().all()
        payload_fingerprint = validity.fingerprint()
        for entry in candidates:
            entry_validity = entry.validity or {}
            if entry_validity.get("fingerprint") != payload_fingerprint:
                continue  # permissions/model/prompt/source versions changed
            stored_vector = entry_validity.get("question_vector") or []
            if cosine_similarity(query_vector, stored_vector) < _SIMILARITY_THRESHOLD:
                continue  # not the same question
            entry.last_hit_at = _now()
            return dict(entry.payload or {})
        return None

    def store(
        self,
        *,
        workspace_id: str,
        question: str,
        payload: dict[str, Any],
        validity: CacheValidity,
    ) -> bool:
        settings = get_settings()
        if len(json.dumps(payload, default=str)) > settings.cache_max_payload_bytes:
            return False
        self.db.add(
            CacheEntry(
                workspace_id=workspace_id,
                key_hash=hashlib.sha256(question.lower().encode()).hexdigest()[:32],
                payload=payload,
                validity={
                    "fingerprint": validity.fingerprint(),
                    "question_vector": self._embed_key(question),
                },
            )
        )
        return True
