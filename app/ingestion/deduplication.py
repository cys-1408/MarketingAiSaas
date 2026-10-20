"""Idempotent ingestion: repeated uploads/sync retries never duplicate records.

Deduplication relies on stable business keys (verified unique in the
database) rather than text similarity alone — two feedback items that merely
look alike may be distinct events, so near-duplicate merging happens only on
exact content fingerprints.
"""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CampaignMetric, FeedbackItem


def existing_metric_keys(
    db: Session,
    workspace_id: str,
    source_id: str,
    source_version: int,
) -> set[tuple[str, str, str]]:
    """Return (campaign_id, day, metric_name) keys already stored for a source version."""
    rows = db.execute(
        select(CampaignMetric.campaign_id, CampaignMetric.day, CampaignMetric.metric_name)
        .where(
            CampaignMetric.workspace_id == workspace_id,
            CampaignMetric.source_id == source_id,
            CampaignMetric.source_version == source_version,
        )
    ).all()
    return {(campaign_id, str(day), metric_name) for campaign_id, day, metric_name in rows}


def is_duplicate_feedback(
    db: Session,
    workspace_id: str,
    fingerprint: str,
) -> bool:
    """True when an identical feedback record already exists in the workspace."""
    row = db.execute(
        select(FeedbackItem.id)
        .where(
            FeedbackItem.workspace_id == workspace_id,
            FeedbackItem.content_fingerprint == fingerprint,
        )
        .limit(1)
    ).scalar_one_or_none()
    return row is not None


def dedupe_metric_payloads(
    payloads: Iterable[dict],
    seen: set[tuple[str, str, str]],
) -> tuple[list[dict], int]:  # (kept, skipped_count)
    """Filter out payload dicts whose business key was already stored."""
    kept: list[dict] = []
    skipped = 0
    for payload in payloads:
        key = (payload["campaign_id"], str(payload["day"]), payload["metric_name"])
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        kept.append(payload)
    return kept, skipped
