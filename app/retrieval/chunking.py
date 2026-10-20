"""Document chunking that preserves source locators and table relationships.

Narrative documents are split into semantically coherent sections; tabular
data is chunked per row so numbers stay attached to their labels/units and
campaign context, never flattened into prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ingestion.parsers import ParsedDocument, ParsedSection, ParsedTable
from app.models.domain import CANONICAL_SCHEMAS

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP_CHARS = 120


@dataclass(slots=True)
class RawChunk:
    kind: str  # narrative|table_row|meta
    title: str
    text: str
    locator: dict[str, Any]


def chunk_sections(
    sections: list[ParsedSection],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP_CHARS,
) -> list[RawChunk]:
    """Split narrative sections on sentence boundaries with bounded size."""
    chunks: list[RawChunk] = []
    for section_index, section in enumerate(sections, start=1):
        text = section.text.strip()
        if not text:
            continue
        heading = section.heading or "document"
        pieces = _split_sentences(text)
        buffer: list[str] = []

        def flush(buf: list[str], extra_context: list[str] | None = None) -> RawChunk:
            body = " ".join(buf)
            context = heading
            return RawChunk(
                kind="narrative",
                title=heading,
                text=f"{context}: {body}" if context and context.lower() not in body.lower()[:32] else body,
                locator={
                    "section": section_index,
                    "heading": heading,
                    **section.locator,
                },
            )

        for piece in pieces:
            if sum(len(p) for p in buffer) + len(piece) > max_chars and buffer:
                chunks.append(flush(buffer))
                tail = " ".join(buffer[-1])[-overlap:] if overlap else ""
                buffer = [tail + piece] if tail else [piece]
            else:
                buffer.append(piece)
        if buffer:
            chunks.append(flush(buffer))
    return chunks


def _split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    for index, char in enumerate(text):
        if char in ".!?\n" and (index + 1 >= len(text) or text[index + 1] == " "):
            sentence = text[start:index + 1].strip()
            if sentence:
                sentences.append(sentence)
            start = index + 1
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def chunk_table_rows(
    table: ParsedTable,
    *,
    category: str = "campaign_metrics",
) -> list[RawChunk]:
    """One chunk per row with explicit column: value pairs.

    Numbers are never separated from the labels/definitions that give them
    meaning, and column headings are repeated per row so retrieval can match
    on exact terms.
    """
    chunks: list[RawChunk] = []
    for row in table.rows:
        locator_row = row.get("__row__", 0)
        pairs = [
            f"{column}: {row[column]}"
            for column in table.columns
            if str(row.get(column, "")).strip() and column != "__row__"
        ]
        if not pairs:
            continue
        title = table.name
        text = f"{title} | " + " | ".join(pairs)
        chunks.append(
            RawChunk(
                kind="table_row",
                title=title,
                text=text[:4000],
                locator={"sheet": table.name, "row": locator_row},
            )
        )
    return chunks


def chunk_parsed_document(doc: ParsedDocument) -> list[RawChunk]:
    """Chunk a parsed document using the appropriate strategy per content kind."""
    chunks: list[RawChunk] = []
    for table in doc.tables:
        chunks.extend(chunk_table_rows(table))
    chunks.extend(chunk_sections(doc.sections))
    return chunks


def chunk_fingerprint(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.strip().encode()).hexdigest()[:40]
