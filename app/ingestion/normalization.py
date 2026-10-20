"""Convert validated rows into canonical domain entities with provenance.

The same normalization path serves uploaded files and connector data, so
analytics, retrieval and graph construction see one canonical model.  Every
normalized record keeps original values, a source locator, the source id and
the source version.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.tenancy import new_id
from app.ingestion.validation import parse_date, parse_number


def content_fingerprint(*parts: Any) -> str:
    joined = "\x1f".join(str(p).strip().lower() for p in parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:40]


def slugify(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in text.strip().lower())
    return "-".join(part for part in cleaned.split("-") if part)[:80] or "entity"


METRIC_UNITS = {
    "spend": "currency",
    "impressions": "count",
    "clicks": "count",
    "sessions": "count",
    "conversions": "count",
    "purchases": "count",
    "revenue": "currency",
}


@dataclass(slots=True)
class NormalizedMetricRow:
    workspace_id: str
    campaign_key: str
    campaign_name: str
    day: date
    channel: str
    metric_rows: list[dict[str, Any]]  # metric_name, value, unit, conversions event label
    source_id: str
    source_version: int
    locator: dict[str, Any]
    raw_row: dict[str, Any]


@dataclass(slots=True)
class NormalizedFeedback:
    workspace_id: str
    text: str
    summary: str
    product_ref: str
    occurred_on: date | None
    source_type: str
    rating: float | None
    content_fingerprint_value: str
    source_id: str
    source_version: int
    locator: dict[str, Any]
    raw_row: dict[str, Any]


@dataclass(slots=True)
class NormalizedExperiment:
    workspace_id: str
    experiment_name: str
    variant: str
    observations: dict[str, float]
    sample_size: int
    source_id: str
    source_version: int
    locator: dict[str, Any]
    raw_row: dict[str, Any]


def normalize_campaign_metrics(
    workspace_id: str,
    rows: list[dict[str, Any]],
    *,
    source_id: str,
    source_version: int,
    value_columns: dict[str, set[str]],
) -> list[NormalizedMetricRow]:
    """Normalize validated campaign-metric rows into per-day metric records."""
    normalized: list[NormalizedMetricRow] = []
    for row in rows:
        locator = {
            "sheet": row.get("__sheet__", "data"),
            "row": row.get("__row__", 0),
        }
        campaign_name = str(row.get("campaign_name", "")).strip()
        day_value = parse_date(row.get("date"))
        if not campaign_name or day_value is None:
            continue
        metric_rows: list[dict[str, Any]] = []
        for canonical, columns in value_columns.items():
            if column := next(iter(sorted(columns)), None):
                value = parse_number(row.get(column))
                if value is None:
                    continue
                unit = METRIC_UNITS.get(canonical, "count")
                event_label = ""
                if canonical in {"conversions", "purchases"}:
                    # Preserve what the source actually measured; never assume
                    # an unlabeled conversion column means a purchase.
                    event_label = canonical
                metric_rows.append(
                    {
                        "metric_name": canonical,
                        "value": value,
                        "unit": unit,
                        "conversion_event": event_label,
                    }
                )
        raw_row = {k: v for k, v in row.items() if not k.startswith("__")}
        normalized.append(
            NormalizedMetricRow(
                workspace_id=workspace_id,
                campaign_key=slugify(campaign_name),
                campaign_name=campaign_name,
                day=day_value,
                channel=str(row.get("channel", "") or "").strip(),
                metric_rows=metric_rows,
                source_id=source_id,
                source_version=source_version,
                locator=locator,
                raw_row=raw_row,
            )
        )
    return normalized


def normalize_feedback(
    workspace_id: str,
    rows: list[dict[str, Any]],
    *,
    source_id: str,
    source_version: int,
    source_type_fallback: str = "customer_feedback",
) -> list[NormalizedFeedback]:
    normalized: list[NormalizedFeedback] = []
    for row in rows:
        text = str(row.get("feedback_text", "") or "").strip()
        if not text:
            continue
        locator = {"sheet": row.get("__sheet__", "data"), "row": row.get("__row__", 0)}
        occurred = parse_date(row.get("feedback_date"))
        normalized.append(
            NormalizedFeedback(
                workspace_id=workspace_id,
                text=text,
                summary=text[:200],
                product_ref=str(row.get("product_ref", "") or "").strip(),
                occurred_on=occurred,
                source_type=str(row.get("source_type", "") or "").strip() or source_type_fallback,
                rating=parse_number(row.get("rating")),
                content_fingerprint_value=content_fingerprint(text, occurred),
                source_id=source_id,
                source_version=source_version,
                locator=locator,
                raw_row={k: v for k, v in row.items() if not k.startswith("__")},
            )
        )
    return normalized


def normalize_experiments(
    workspace_id: str,
    rows: list[dict[str, Any]],
    *,
    source_id: str,
    source_version: int,
) -> list[NormalizedExperiment]:
    normalized: list[NormalizedExperiment] = []
    for row in rows:
        name = str(row.get("experiment_name", "") or "").strip()
        variant = str(row.get("variant", "") or "").strip()
        if not name or not variant:
            continue
        observations: dict[str, float] = {}
        sample_size = parse_number(row.get("sample_size")) or 0
        value = parse_number(row.get("observations"))
        if value is not None:
            observations["value"] = value
        normalized.append(
            NormalizedExperiment(
                workspace_id=workspace_id,
                experiment_name=name,
                variant=variant,
                observations=observations,
                sample_size=int(sample_size),
                source_id=source_id,
                source_version=source_version,
                locator={"sheet": row.get("__sheet__", "data"), "row": row.get("__row__", 0)},
                raw_row={k: v for k, v in row.items() if not k.startswith("__")},
            )
        )
    return normalized


# Mapping from parsed sections (narrative documents) -> feedback-like rows.
def rows_from_sections(doc, category: str) -> list[dict[str, Any]]:  # noqa: ANN001
    rows: list[dict[str, Any]] = []
    for offset, section in enumerate(doc.sections, start=1):
        rows.append(
            {
                "feedback_text": section.text if len(section.text) > 60 else "",
                "feedback_date": "",
                "rating": "",
                "product_ref": section.heading if category == "product_facts" else "",
                "source_type": "document",
                "__sheet__": section.heading or "document",
                "__row__": offset,
            }
        )
    return rows
