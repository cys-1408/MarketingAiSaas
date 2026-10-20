"""Content inspection: verify what a source actually is before trusting it.

Inspection combines file-signature sniffing with real parsing, so mislabeled
files are detected and unsafe/corrupt content is rejected with actionable
errors before any pipeline stage consumes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.ingestion.parsers import (
    SUPPORTED_FILE_TYPES,
    ParsedDocument,
    ParsedTable,
    ParserError,
    parse_file,
)


class InspectionError(Exception):
    """Raised when a file fails inspection and cannot enter the pipeline."""


_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "xlsx": (b"PK\x03\x04",),
    "docx": (b"PK\x03\x04",),
    "pdf": (b"%PDF-",),
}


@dataclass(slots=True)
class InspectionResult:
    """Typed inspection outcome with safe diagnostics (no raw content)."""

    declared_type: str
    detected_type: str
    type_mismatch: bool
    table_summaries: list[dict[str, Any]] = field(default_factory=list)
    section_count: int = 0
    meta: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    parsed: ParsedDocument | None = None

    @property
    def row_count(self) -> int:
        return sum(int(t["row_count"]) for t in self.table_summaries)


def _sniff_signature(data: bytes, declared: str) -> str:
    """Determine the likely real format from magic bytes/text shape."""
    for file_type, signatures in _MAGIC_SIGNATURES.items():
        if any(data.startswith(sig) for sig in signatures):
            # Office formats share a zip container; openpyxl/docx parse errors
            # distinguish them later.
            return file_type
    head = data[:4096]
    stripped = head.strip()
    if not stripped:
        return declared
    if stripped[:1] in {b"{", b"["}:
        return "json"
    first_line = stripped.split(b"\n", 1)[0].lstrip(b"\xef\xbb\xbf")
    if b"\t" in first_line and b"," not in first_line:
        return "tsv"
    if b"," in first_line:
        return "csv"
    head_text = stripped[:2048].decode("latin-1", errors="replace").lower()
    if "<html" in head_text or "<!doctype html" in head_text:
        return "html"
    if head_text.lstrip().startswith("%%"):
        return "pdf"
    return declared


def _limit_and_preview_tables(doc: ParsedDocument) -> list[dict[str, Any]]:
    settings = get_settings()
    truncated: list[dict[str, Any]] = []
    total_cells = 0
    for table in doc.tables:
        row_count = table.row_count
        if row_count > settings.upload_max_rows:
            raise InspectionError(
                f"table '{table.name}' has {row_count} rows, exceeding the "
                f"{settings.upload_max_rows}-row limit"
            )
        total_cells += row_count * max(1, len(table.columns))
        if total_cells > settings.upload_max_cells:
            raise InspectionError(
                f"source exceeds the {settings.upload_max_cells}-cell limit; "
                "split the export before uploading"
            )
        samples: dict[str, list[str]] = {}
        for column in table.columns[:50]:
            values: list[str] = []
            for row in table.rows[:5]:
                value = str(row.get(column, "")).strip()
                if value:
                    values.append(value[:60])
                if len(values) >= 3:
                    break
            samples[column] = values
        truncated.append(
            {
                "name": table.name,
                "columns": table.columns[:100],
                "row_count": row_count,
                "sample_values": samples,
            }
        )
    return truncated


def inspect_bytes(data: bytes, declared_type: str, *, parse: bool = True) -> InspectionResult:
    """Inspect a source: signature check, limits, parse, and safe diagnostics.

    Raises :class:`InspectionError` for unsupported/unsafe files; returns the
    typed result otherwise. With ``parse=False`` only cheap signature/limit
    checks run (used during upload validation).
    """
    settings = get_settings()
    if declared_type not in SUPPORTED_FILE_TYPES:
        raise InspectionError(f"unsupported file type: {declared_type}")
    if not data:
        raise InspectionError("file is empty")
    if len(data) > settings.upload_max_bytes:
        raise InspectionError(
            f"file exceeds the {settings.upload_max_bytes // (1024 * 1024)} MB upload limit"
        )

    detected = _sniff_signature(data, declared_type)
    type_mismatch = detected != declared_type and not _compat_extension(detected, declared_type)

    if not parse:
        return InspectionResult(
            declared_type=declared_type,
            detected_type=detected,
            type_mismatch=type_mismatch,
        )

    effective_type = detected if _compat_extension(detected, declared_type) else declared_type
    try:
        doc = parse_file(data, effective_type)
    except ParserError as exc:
        if type_mismatch:
            raise InspectionError(
                f"declared as {declared_type} but content is not a valid "
                f"{declared_type} file: {exc}"
            ) from exc
        raise InspectionError(str(exc)) from exc

    if effective_type == "pdf":
        pages = int(doc.meta.get("page_count", 0) or 0)
        if pages > settings.upload_max_pages:
            raise InspectionError(
                f"PDF has {pages} pages, exceeding the {settings.upload_max_pages}-page limit"
            )

    warnings = list(doc.warnings)
    if type_mismatch:
        warnings.append(
            f"extension suggested '{declared_type}' but content signature/parsing "
            f"identified '{detected}'"
        )
    table_summaries = _limit_and_preview_tables(doc)
    return InspectionResult(
        declared_type=declared_type,
        detected_type=effective_type,
        type_mismatch=type_mismatch,
        table_summaries=table_summaries,
        section_count=len(doc.sections),
        meta=dict(doc.meta),
        warnings=warnings,
        parsed=doc,
    )


def _compat_extension(detected: str, declared: str) -> bool:
    """Signature/declared pairs that are consistent interpretations."""
    compat = {
        ("csv", "tsv"), ("tsv", "csv"),
        ("txt", "md"), ("md", "txt"),
        ("xlsx", "docx"), ("docx", "xlsx"),  # both zip containers; parsing decides
        ("csv", "json"), ("json", "csv"),
    }
    return (detected, declared) in compat or detected == declared
