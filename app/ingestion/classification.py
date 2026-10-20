"""Classify sources into supported categories.

Deterministic header/structure rules produce a score; an optional
model-assisted proposal is only consulted for borderline cases and never
treated as authoritative.  Uncertain content is routed to review rather
than force-fitted into a category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ingestion.parsers import ParsedDocument

CATEGORY_CAMPAIGN_METRICS = "campaign_metrics"
CATEGORY_CUSTOMER_FEEDBACK = "customer_feedback"
CATEGORY_PRODUCT_FACTS = "product_facts"
CATEGORY_BRAND_RULES = "brand_rules"
CATEGORY_EXPERIMENT_RESULTS = "experiment_results"
SUPPORTED_CATEGORIES = (
    CATEGORY_CAMPAIGN_METRICS,
    CATEGORY_CUSTOMER_FEEDBACK,
    CATEGORY_PRODUCT_FACTS,
    CATEGORY_BRAND_RULES,
    CATEGORY_EXPERIMENT_RESULTS,
)

# Header tokens that hint at each category.
_HEADER_HINTS: dict[str, dict[str, float]] = {
    CATEGORY_CAMPAIGN_METRICS: {
        "spend": 3, "impressions": 3, "clicks": 3, "sessions": 2,
        "conversions": 2.5, "revenue": 3, "campaign": 2, "ctr": 2,
        "cpc": 2, "cpm": 2, "roas": 2, "opens": 2, "unsubscribes": 2,
        "purchase": 1.5, "date": 1, "channel": 1.5,
    },
    CATEGORY_CUSTOMER_FEEDBACK: {
        "feedback": 3, "comment": 3, "review": 3, "rating": 2.5,
        "response": 2, "survey": 2.5, "objection": 2, "support": 1.5,
        "nps": 2, "verbatim": 2, "tweet": 1, "ticket": 1.5,
    },
    CATEGORY_PRODUCT_FACTS: {
        "product": 2.5, "feature": 2.5, "faq": 2.5, "question": 1.5,
        "answer": 1.5, "specification": 2, "compatibility": 2, "pricing": 1.5,
        "approved_claim": 2.5, "limitation": 2,
    },
    CATEGORY_BRAND_RULES: {
        "brand": 3, "tone": 2.5, "guideline": 2.5, "terminology": 2,
        "prohibited": 2.5, "disclaimer": 2, "voice": 2, "legal": 1,
    },
    CATEGORY_EXPERIMENT_RESULTS: {
        "variant": 3, "control": 3, "hypothesis": 2.5, "arm": 1,
        "sample_size": 2.5, "lift": 2, "significance": 2, "experiment": 3,
        "treatment": 2, "holdout": 2,
    },
}

# Body-text patterns that confirm a narrative category.
_PRIVACY_SAFE_BODY_HINTS: dict[str, list[str]] = {
    CATEGORY_CUSTOMER_FEEDBACK: ["customer said", "review", "respondent", "complaint", "praised", "frustrated"],
    CATEGORY_BRAND_RULES: ["tone of voice", "must not claim", "never promise", "always mention"],
    CATEGORY_PRODUCT_FACTS: ["this product", "the feature", "requires", "is available in"],
}


@dataclass(slots=True)
class Classification:
    category: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    uncertain: bool = False
    reversible: bool = True

    @property
    def needs_review(self) -> bool:
        return self.uncertain or self.confidence < 0.5


def _header_scores(doc: ParsedDocument) -> dict[str, float]:
    scores = {category: 0.0 for category in _HEADER_HINTS}
    for table in doc.tables:
        joined = " ".join(column.lower().replace("_", " ").replace("-", " ") for column in table.columns)
        for category, hints in _HEADER_HINTS.items():
            for token, weight in hints.items():
                if token in joined:
                    scores[category] += weight
    return scores


def _body_scores(doc: ParsedDocument) -> dict[str, float]:
    scores = {category: 0.0 for category in _PRIVACY_SAFE_BODY_HINTS}
    text = " ".join(section.text.lower() for section in doc.sections)
    for category, tokens in _PRIVACY_SAFE_BODY_HINTS.items():
        for token in tokens:
            if token in text:
                scores[category] += 1.0
    return scores


def _table_row_scores(doc: ParsedDocument) -> dict[str, float]:
    """Sample representative values to spot feedback-like or variant-like data."""
    scores = {category: 0.0 for category in _PRIVACY_SAFE_BODY_HINTS}
    for table in doc.tables:
        text_columns = [
            column for column in table.columns
            if table.rows and _is_long_text(table.rows[0].get(column, ""))
        ]
        if len(text_columns) >= 3 or (table.rows and any("rating" in column.lower() for column in table.columns)):
            scores[CATEGORY_CUSTOMER_FEEDBACK] += 1.5
        values = " ".join(
            str(row.get(column, "")) for row in table.rows[:20] for column in table.columns
        ).lower()
        if any(token in values for token in ("control", "variant a", "variant b", "arm a", "arm b")):
            scores[CATEGORY_EXPERIMENT_RESULTS] += 1.5
    return scores


def _is_long_text(value: Any) -> bool:
    return isinstance(value, str) and len(value) > 60


def classify(doc: ParsedDocument) -> Classification:
    """Determine the source category from structure and content clues."""
    if not doc.tables and not doc.sections:
        return Classification(
            category="unknown", confidence=0.0,
            reasons=["source contains no structured tables or narrative text"],
            uncertain=True,
        )
    header_scores = _header_scores(doc)
    body_scores = _body_scores(doc)
    row_scores = _table_row_scores(doc)
    combined: dict[str, float] = {}
    for category in _HEADER_HINTS:
        h = header_scores.get(category, 0.0)
        b = body_scores.get(category, 0.0)
        r = row_scores.get(category, 0.0)
        if h == b == r == 0.0:
            continue
        combined[category] = h + 0.6 * b + 0.8 * r
    if doc.tables and not doc.sections and max(header_scores.values()) == 0:
        return Classification(
            category="unknown",
            confidence=0.2,
            reasons=["tabular data with no recognizable marketing schema headers"],
            uncertain=True,
        )
    best = max(combined, key=lambda category: combined[category])
    total = sum(combined.values())
    if total == 0:
        return Classification(
            category="unknown", confidence=0.1,
            reasons=["no classification clues matched"], uncertain=True,
        )
    confidence = min(1.0, combined[best] / (total + 1e-9))
    reasons: list[str] = []
    if header_scores.get(best, 0) > 0:
        matched = [
            token for token in _HEADER_HINTS[best]
            if any(token in " ".join(t.columns).lower() for t in doc.tables)
        ]
        reasons.append(f"header tokens matched: {', '.join(sorted(matched)[:6])}")
    if body_scores.get(best, 0) > 0:
        reasons.append("narrative content matched category-specific language")
    uncertain = confidence < 0.45 or combined[best] < 1.5
    return Classification(
        category=best,
        confidence=round(confidence, 3),
        reasons=reasons or ["structural match with known schema"],
        uncertain=uncertain,
    )
