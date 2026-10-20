"""Exposes stable ingestion interfaces without side effects."""

from app.ingestion.parsers import ParsedDocument, ParsedSection, ParsedTable, ParserError

__all__ = ["ParsedDocument", "ParsedSection", "ParsedTable", "ParserError"]
