"""Real parsers for every advertised file format.

Supported: CSV, TSV, XLSX, PDF, DOCX, Markdown, plain text, HTML, JSON.
All parsers normalize into :class:`ParsedDocument` so downstream inspection,
mapping, validation and normalization stages are format-agnostic, and every
parsed item carries source locators (sheet/row/page/heading).
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

SUPPORTED_FILE_TYPES = ("csv", "tsv", "xlsx", "pdf", "docx", "md", "txt", "html", "json")


class ParserError(Exception):
    """Raised when a file cannot be parsed safely."""


@dataclass(slots=True)
class ParsedTable:
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass(slots=True)
class ParsedSection:
    heading: str
    text: str
    locator: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    file_type: str
    tables: list[ParsedTable] = field(default_factory=list)
    sections: list[ParsedSection] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return sum(t.row_count for t in self.tables)

    @property
    def text_length(self) -> int:
        return sum(len(s.text) for s in self.sections)


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ParserError("file is not decodable text or a supported binary format")


def _rows_from_grid(grid: list[list[str]], table_name: str = "data") -> ParsedTable | None:
    """Build a header->row table from a grid of strings."""
    grid = [[(cell if cell is not None else "") for cell in row] for row in grid]
    grid = [row for row in grid if any(str(cell).strip() for cell in row)]
    if len(grid) < 2:
        return None
    header = grid[0]
    columns = [str(h).strip() or f"column_{i}" for i, h in enumerate(header)]
    rows: list[dict[str, Any]] = []
    for offset, row in enumerate(grid[1:], start=2):
        record: dict[str, Any] = {}
        for i, column in enumerate(columns):
            record[column] = str(row[i]).strip() if i < len(row) else ""
        record["__row__"] = offset  # 1-based sheet row locator including header
        rows.append(record)
    return ParsedTable(name=table_name, columns=columns, rows=rows)


def _grid_from_text(text: str, delimiter: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [list(row) for row in reader]


def parse_delimited(data: bytes, file_type: str, delimiter: str) -> ParsedDocument:
    if not data.strip():
        return ParsedDocument(file_type=file_type, warnings=["file is empty"])
    text = _decode(data)
    table = _rows_from_grid(_grid_from_text(text, delimiter), file_type)
    if table is None:
        return ParsedDocument(file_type=file_type, warnings=["no data rows found"])
    if any(len(r) != len(table.columns) for r in _grid_from_text(text, delimiter)):
        pass  # csv module already pads short rows; ragged rows are a warning below
    warnings: list[str] = []
    grid_lengths = {len(r) for r in _grid_from_text(text, delimiter)}
    if len(grid_lengths) > 1:
        warnings.append("rows have inconsistent column counts; missing cells were left empty")
    return ParsedDocument(file_type=file_type, tables=[table], warnings=warnings)


def parse_xlsx(data: bytes) -> ParsedDocument:
    if not data[:2] == b"PK":
        raise ParserError("file is not a valid XLSX workbook")
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - dependency always present
        raise ParserError("XLSX support is not installed") from exc
    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(data), read_only=True, data_only=True
        )
    except Exception as exc:
        raise ParserError(f"workbook could not be opened: {exc}") from exc
    doc = ParsedDocument(file_type="xlsx", meta={"sheet_names": workbook.sheetnames})
    empty_sheets: list[str] = []
    for sheetname in workbook.sheetnames:
        sheet = workbook[sheetname]
        grid: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            grid.append(["" if v is None else str(v) for v in row])
        if len(grid) < 2:
            empty_sheets.append(sheetname)
            continue
        table = _rows_from_grid(grid, sheetname)
        if table is not None:
            doc.tables.append(table)
    if len(doc.tables) < len(workbook.sheetnames) and not empty_sheets:
        doc.warnings.append("some sheets contained no parsable table rows")
    if empty_sheets and doc.tables:
        doc.warnings.append(
            "sheets with no data rows skipped: " + ", ".join(empty_sheets)
        )
    return doc


def parse_docx(data: bytes) -> ParsedDocument:
    if not data[:2] == b"PK":
        raise ParserError("file is not a valid DOCX document")
    try:
        import docx as docx_module
    except ImportError as exc:  # pragma: no cover
        raise ParserError("DOCX support is not installed") from exc
    try:
        document = docx_module.Document(io.BytesIO(data))
    except Exception as exc:
        raise ParserError(f"document could not be opened: {exc}") from exc
    doc = ParsedDocument(file_type="docx")
    heading = ""
    buffer: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.style.name.startswith("Heading"):
            if buffer:
                doc.sections.append(_section(heading, buffer))
            heading = text
            buffer = []
        else:
            buffer.append(text)
    if buffer:
        doc.sections.append(_section(heading, buffer))
    for t_index, table in enumerate(document.tables):
        grid = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        parsed = _rows_from_grid(grid, f"table_{t_index + 1}")
        if parsed is not None:
            doc.tables.append(parsed)
    if not doc.sections and not doc.tables:
        raise ParserError("document contains no readable text")
    return doc


def _section(heading: str, lines: list[str]) -> ParsedSection:
    return ParsedSection(
        heading=heading or "document",
        text="\n".join(lines),
        locator={"heading": heading or "document"},
    )


def parse_pdf(data: bytes) -> ParsedDocument:
    if not data[:5] == b"%PDF-":
        raise ParserError("file is not a valid PDF document")
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ParserError("PDF support is not installed") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ParserError(f"PDF could not be opened: {exc}") from exc
    doc = ParsedDocument(file_type="pdf", meta={"page_count": len(reader.pages)})
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            doc.warnings.append(f"page {page_number} could not be extracted")
            continue
        text = text.strip()
        if text:
            heading = text.splitlines()[0][:120] if text else ""
            doc.sections.append(
                ParsedSection(heading=heading or "page", text=text, locator={"page": page_number})
            )
    if not doc.sections:
        raise ParserError("PDF contains no extractable text (possibly scanned images)")
    return doc


class _HTMLTextExtractor(HTMLParser):
    _SKIPPED = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._skip_depth = 0
        self._in_table = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._SKIPPED:
            self._skip_depth += 1
        elif tag == "table":
            self._in_table = True
            self._current_table = []
        elif tag == "tr" and self._in_table:
            self._current_row = []
        elif tag in {"td", "th"} and self._in_table:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIPPED and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"td", "th"} and self._in_table:
            self._current_row.append(" ".join("".join(self._current_cell).split()))
        elif tag == "tr" and self._in_table:
            self._current_table.append(self._current_row)
        elif tag == "table" and self._in_table:
            self.tables.append(self._current_table)
            self._in_table = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text or self._skip_depth:
            return
        if self._in_table and self._current_cell is not None and data:
            self._current_cell.append(data)
        else:
            self.parts.append(text)


def parse_html(data: bytes) -> ParsedDocument:
    text = _decode(data)
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(text)
    except Exception as exc:
        raise ParserError(f"HTML could not be parsed: {exc}") from exc
    doc = ParsedDocument(file_type="html", meta={"title": ""})
    body = "\n".join(extractor.parts)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if title_match:
        doc.meta["title"] = " ".join(title_match.group(1).split())
    if extractor.tables:
        for index, grid in enumerate(extractor.tables):
            table = _rows_from_grid(grid, f"table_{index + 1}")
            if table is not None:
                doc.tables.append(table)
    if body.strip():
        doc.sections.append(_section(doc.meta["title"] or "page", [body.strip()]))
    if not doc.tables and not doc.sections:
        raise ParserError("HTML contains no readable content")
    return doc


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_markdown(data: bytes) -> ParsedDocument:
    text = _decode(data)
    if not text.strip():
        return ParsedDocument(file_type="md", warnings=["file is empty"])
    doc = ParsedDocument(file_type="md")
    heading = "document"
    buffer: list[str] = []
    paragraphs = text.split("\n")
    fenced = False
    import linecache  # noqa: F401 (intentional no-op to keep import list stable)
    del linecache
    for line in paragraphs:
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            buffer.append(stripped)
            continue
        match = _HEADING_RE.match(stripped)
        if match:
            if buffer:
                doc.sections.append(_section(heading, buffer))
                buffer = []
            heading = match.group(2).strip()
        elif stripped:
            buffer.append(stripped)
    if buffer:
        doc.sections.append(_section(heading, buffer))
    if not doc.sections:
        doc.sections.append(_section("document", [text.strip()]))
    return doc


def parse_text(data: bytes) -> ParsedDocument:
    text = _decode(data)
    if not text.strip():
        return ParsedDocument(file_type="txt", warnings=["file is empty"])
    doc = ParsedDocument(file_type="txt")
    doc.sections.append(_section("text", [text.strip()]))
    return doc


def parse_json(data: bytes) -> ParsedDocument:
    if not data.strip():
        return ParsedDocument(file_type="json", warnings=["file is empty"])
    try:
        payload = json.loads(_decode(data))
    except json.JSONDecodeError as exc:
        raise ParserError(f"invalid JSON: {exc}") from exc
    doc = ParsedDocument(file_type="json")
    _flatten_json(payload, "", doc, locator={})
    if not doc.tables and not doc.sections:
        raise ParserError("JSON contains no records or textual content")
    return doc


def _flatten_json(payload: Any, prefix: str, doc: ParsedDocument, locator: dict[str, Any]) -> None:
    if isinstance(payload, list) and payload and all(isinstance(item, dict) for item in payload):
        keys = sorted({k for item in payload for k in item.keys()})
        head = [k if k else f"column_{i}" for i, k in enumerate(keys)]
        rows: list[dict[str, Any]] = []
        for offset, item in enumerate(payload, start=1):
            record = {"__row__": offset}
            for column in head:
                value = item.get(column, "")
                record[column] = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            rows.append(record)
        doc.tables.append(ParsedTable(name=prefix or "records", columns=head, rows=rows))
        return
    if isinstance(payload, list) and all(isinstance(item, str) for item in payload):
        doc.sections.append(_section(prefix or "items", payload))
        return
    if isinstance(payload, dict):
        strings = {k: v for k, v in payload.items() if isinstance(v, str)}
        if strings:
            lines = [f"{k}: {v}" for k, v in sorted(strings.items())]
            heading = prefix or "object"
            doc.sections.append(_section(heading, lines, locator={**locator, "path": heading}))
            nested = {k: v for k, v in payload.items() if k not in strings}
            for key, value in nested.items():
                _flatten_json(value, f"{prefix}.{key}" if prefix else key, doc, locator)
        else:
            for key, value in payload.items():
                _flatten_json(
                    value, f"{prefix}.{key}" if prefix else key, doc, locator
                )
        return
    if isinstance(payload, list):
        for offset, item in enumerate(payload, start=1):
            _flatten_json(item, f"{prefix}[{offset}]" if prefix else f"item[{offset}]", doc, locator)
        return
    doc.sections.append(_section(prefix or "value", [str(payload)], locator=dict(locator)))


_FILE_TYPE_TO_PARSER = {
    "csv": lambda d: parse_delimited(d, "csv", ","),
    "tsv": lambda d: parse_delimited(d, "tsv", "\t"),
    "xlsx": parse_xlsx,
    "docx": parse_docx,
    "pdf": parse_pdf,
    "html": parse_html,
    "md": parse_markdown,
    "txt": parse_text,
    "json": parse_json,
}


def parse_file(data: bytes, file_type: str) -> ParsedDocument:
    """Parse raw bytes with the parser registered for ``file_type``."""
    parser = _FILE_TYPE_TO_PARSER.get(file_type)
    if parser is None:
        raise ParserError(f"unsupported file type: {file_type}")
    return parser(data)
