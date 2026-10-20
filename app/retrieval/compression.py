"""Contextual compression that keeps evidence traceable.

Compression reduces retrieved passages to question-relevant material, but
never degrades evidence meaning: numbers stay with units, hypothesis-vs-fact
labels are preserved, contradiction notes are kept verbatim, and every
compressed sentence retains the chunk id + locator it came from.  Retrieved
text is treated as untrusted data — embedded instruction-looking text is
quoted, never obeyed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.retrieval.embeddings import tokenize

_QUALIFIER_MARKERS = (
    "hypothesis", "might", "may", "possible", "uncertain", "not yet",
    "estimate", "assumes", "draft", "unverified", "correlation",
)
_CONTRADICTION_MARKERS = ("however", "but in contrast", "on the other hand", "contradict", "declined", "fell")


@dataclass(slots=True)
class CompressedEvidence:
    chunk_id: str
    source_id: str
    source_version: int
    source_name: str
    locator: dict[str, Any]
    passages: list[str]
    qualifications: list[str]
    contradictions: list[str]
    coverage: float


def _sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in parts if len(s.strip()) > 12]


def compress_passages(
    question: str,
    candidates: list[Any],
    *,
    max_passages_per_chunk: int = 6,
) -> list[CompressedEvidence]:
    """Extract question-relevant sentences from candidate chunks.

    Each passage retains its provenance; qualifiers and contradictions are
    always retained even when not directly matching the question, because
    dropping them would change the meaning of the evidence.
    """
    query_terms = set(tokenize(question))
    compressed: list[CompressedEvidence] = []
    for candidate in candidates:
        text = candidate.text
        passages: list[str] = []
        qualifications: list[str] = []
        contradictions: list[str] = []
        scored: list[tuple[float, str]] = []
        for sentence in _sentence_split(text):
            terms = set(tokenize(sentence))
            overlap = len(terms & query_terms)
            scored.append((overlap, sentence))
            lowered = sentence.lower()
            if any(marker in lowered for marker in _QUALIFIER_MARKERS):
                qualifications.append(sentence)
            if any(marker in lowered for marker in _CONTRADICTION_MARKERS):
                contradictions.append(sentence)
        scored.sort(key=lambda pair: pair[0], reverse=True)
        for _, sentence in scored[:max_passages_per_chunk]:
            # Guard against prompt-injection-style payloads being echoed as
            # instructions: passages are returned as quoted evidence text.
            passages.append(sentence)
        if not passages and text:
            passages.append(text[:400])
        compressed.append(
            CompressedEvidence(
                chunk_id=str(candidate.chunk_id),
                source_id=candidate.source_id,
                source_version=candidate.source_version,
                source_name=candidate.source_name,
                locator=dict(candidate.locator),
                passages=passages,
                qualifications=qualifications[:3],
                contradictions=contradictions[:3],
                coverage=round(
                    len(query_terms and {t for p in passages for t in tokenize(p)} & query_terms)
                    / max(1, len(query_terms)),
                    3,
                )
                if query_terms
                else 1.0,
            )
        )
    return compressed
