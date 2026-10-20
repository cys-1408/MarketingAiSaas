"""Customer feedback search over authorized indexed records.

Returns exact excerpts with locators so every reported objection/theme can be
checked.  Measured counts come from real records; theme *labels* (objection
grouping) are derived heuristically and always distinguished from measured
counts.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenancy import WorkspaceContext, authorize_workspace
from app.db.models import FeedbackItem
from app.retrieval.bm25_search import BM25Index

_OBJECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing": ("price", "pricing", "cost", "expensive", "too much"),
    "delivery": ("delivery", "shipping", "shipping cost", "slow"),
    "setup": ("setup", "install", "onboarding", "integration"),
    "trust": ("trust", "privacy", "security", "scratch"),
}


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        *,
        workspace_id: str,
        user_id: str,
        query: str = "",
        date_start: str | None = None,
        date_end: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        ctx = authorize_workspace(
            self.db, user_id=user_id, workspace_id=workspace_id,
            required_capability=1,
        )
        start = date.fromisoformat(date_start) if date_start else None
        end = date.fromisoformat(date_end) if date_end else None
        stmt = select(FeedbackItem).where(FeedbackItem.workspace_id == workspace_id)
        if start is not None:
            stmt = stmt.where(FeedbackItem.occurred_on >= start)
        if end is not None:
            stmt = stmt.where(FeedbackItem.occurred_on <= end)
        items = self.db.scalars(stmt.limit(2000)).all()
        results: list[dict[str, Any]] = []
        for item in items:
            if query:
                tokens = set(query.lower().split())
                text = item.text.lower()
                if not (tokens & set(text.split())):
                    continue
            results.append(
                {
                    "feedback_id": item.id,
                    "text": item.text,
                    "summary": item.summary,
                    "product_ref": item.product_ref,
                    "occurred_on": item.occurred_on.isoformat() if item.occurred_on else None,
                    "source_type": item.source_type,
                    "source_id": item.source_id,
                    "source_version": item.source_version,
                    "locator": item.locator,
                    "rating": item.rating,
                }
            )
            if len(results) >= limit:
                break
        return {
            "results": results,
            "returned": len(results),
            "measured_from_records": True,
            "theme_labels": self._themes(items, query),
        }

    def _themes(self, items, query: str) -> list[dict[str, Any]]:  # noqa: ANN001
        """Heuristic theme buckets; counts are measured, labels are heuristic."""
        themes: list[dict[str, Any]] = []
        for label, tokens in _OBJECTION_KEYWORDS.items():
            matching = [
                item for item in items
                if any(token in item.text.lower() for token in tokens)
            ]
            if matching:
                themes.append(
                    {
                        "label": label,
                        "measured_count": len(matching),
                        "interpretation": (
                            f"records mentioning {label}-related terms; keyword heuristic, "
                            "verify against the quoted feedback"
                        ),
                        "example_feedback_ids": [i.id for i in matching[:3]],
                    }
                )
        return themes
