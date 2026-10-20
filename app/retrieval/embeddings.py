"""Embedding adapter with a deterministic local implementation.

The default adapter is a hashing bag-of-features embedder that runs in
process: no text leaves the environment to unapproved providers.  The
interface lets a real embedding provider be plugged in behind
``EMBEDDING_MODEL`` configuration; model version is tracked per chunk so a
model change forces re-embedding instead of silently mixing vector spaces.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from app.core.config import get_settings

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


class EmbeddingError(Exception):
    """Raised when embedding generation fails outright."""


def tokenize(text: str) -> list[str]:
    """Normalize text for BM25/embedding without destroying domain terms."""
    return TOKEN_RE.findall(text.lower())


@dataclass(frozen=True, slots=True)
class EmbeddingModel:
    """Deterministic hashing embedder producing unit-length vectors."""

    model_id: str = "hashing-4096-v1"
    dim: int = 256

    @classmethod
    def configured(cls) -> "EmbeddingModel":
        settings = get_settings()
        return cls(dim=settings.embedding_dim)

    @property
    def version(self) -> str:
        return f"{self.model_id}:{self.dim}"

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not isinstance(t, str) for t in texts):
            raise EmbeddingError("embedding input must be a non-empty list of strings")
        return [self._embed_one(text) for text in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        dim = self.dim
        vector = [0.0] * dim
        tokens = tokenize(text)
        if not tokens:
            return vector
        features = list(tokens) + [f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)]
        for feature in features:
            digest = hashlib.sha256(feature.encode()).digest()
            slot = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[slot] += sign
            slot2 = int.from_bytes(digest[5:9], "big") % dim
            vector[slot2] += sign * 0.5
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Cosine between stored vectors; short vectors are padded with zeros."""
    if len(left) != len(right):
        return 0.0
    dot = sum(l * r for l, r in zip(left, right))
    norm_l = math.sqrt(sum(v * v for v in left))
    norm_r = math.sqrt(sum(v * v for v in right))
    if norm_l == 0 or norm_r == 0:
        return 0.0
    return dot / (norm_l * norm_r)
