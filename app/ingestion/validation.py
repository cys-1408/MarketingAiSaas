"""Validate normalized-candidate rows before they enter canonical storage.

Validation distinguishes:

* ``error``    — record cannot enter published analytics without an explicit
                 resolution path (missing required field, invalid date...),
* ``warning``  — suspicious but usable (outlier values, missing optional),
* ``quarantine`` — record is excluded from analytics until reviewed because
                 it could distort results (mixed units, unknown content).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.models.domain import CANONICAL_SCHEMAS, CanonicalField


@dataclass(slots=True)
class ValidationIssue:
    level: str  # error|warning|quarantine
    locator: dict[str, Any]
    field: str
    message: str


@dataclass(slots=True)
class ValidationResult:
    valid_rows: list[dict[str, Any]] = field(default_factory=list)
    quarantined_rows: list[dict[str, Any]] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "warning")


_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d")


def parse_date(value: Any) -> date | None:
    """Parse a date in supported formats; returns None when unparseable."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_number(value: Any) -> float | None:
    """Parse numerics including percent-suffixed values (kept as ratio)."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _schema(category: str) -> tuple[CanonicalField, ...]:
    return CANONICAL_SCHEMAS.get(category, ())


def validate_rows(
    category: str,
    rows: list[dict[str, Any]],
    value_columns: dict[str, set[str]],
) -> ValidationResult:
    """Validate parsed rows mapped onto canonical fields.

    ``value_columns`` maps canonical target -> set of source column names that
    feed it; values so far live under the source column keys.
    """
    schema = {f.name: f for f in _schema(category)}
    result = ValidationResult()
    numeric_columns = {
        name for name, spec in schema.items() if spec.kind in {"number", "percent", "currency"}
    }
    # Pass 1: collect numeric magnitudes per feedback column for outlier flags.
    magnitudes: dict[str, list[float]] = {}
    for row in rows:
        for column in value_columns.keys():
            if column in numeric_columns:
                number = parse_number(row.get(column))
                if number is not None:
                    magnitudes.setdefault(column, []).append(number)

    for row in rows:
        locator = {"row": row.get("__row__", 0), "sheet": row.get("__sheet__", "data")}
        row_issues: list[ValidationIssue] = []
        fatal = False
        for field_name, spec in schema.items():
            value = row.get(field_name, "")
            if (value is None or str(value).strip() == "") and spec.required:
                row_issues.append(
                    ValidationIssue(
                        level="error", locator=locator, field=field_name,
                        message=f"required field '{field_name}' is empty",
                    )
                )
                fatal = True
                continue
            if spec.kind == "date" and str(value).strip():
                if parse_date(value) is None:
                    row_issues.append(
                        ValidationIssue(
                            level="error", locator=locator, field=field_name,
                            message=f"value '{value}' is not a supported date format "
                            "(%Y-%m-%d, %m/%d/%Y, %d.%m.%Y)",
                        )
                    )
                    fatal = True
            if spec.kind in {"number", "percent", "currency"} and str(value).strip():
                if parse_number(value) is None:
                    row_issues.append(
                        ValidationIssue(
                            level="quarantine", locator=locator, field=field_name,
                            message=f"value '{value}' is not numeric; the row is quarantined "
                            "because a silently zeroed value would distort aggregates",
                        )
                    )
                    fatal = True
        # Statistical outlier warnings for numeric value columns.
        for column, numbers in magnitudes.items():
            if len(numbers) >= 8:
                mean = statistics.fmean(numbers)
                stdev = statistics.pstdev(numbers)
                value = parse_number(row.get(column))
                if value is not None and stdev > 0 and abs(value - mean) > 5 * stdev:
                    row_issues.append(
                        ValidationIssue(
                            level="warning", locator=locator, field=column,
                            message=f"value {value} is more than 5 standard deviations "
                            "from the column mean; verify the unit",
                        )
                    )
        if fatal:
            result.quarantined_rows.append(row)
        else:
            result.valid_rows.append(row)
        result.issues.extend(row_issues)
    return result
