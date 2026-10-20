"""Canonical domain schemas used across ingestion, analytics and retrieval.

Single source of truth for canonical field names, units and aliases.  The
frontend never independently decides metric semantics; it consumes what the
backend computes from these definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CanonicalField:
    name: str
    kind: str  # text|number|date|percent|currency
    aliases: tuple[str, ...] = field(default=())
    required: bool = False


CANONICAL_CAMPAIGN_FIELDS = (
    CanonicalField("campaign_name", "text", ("campaign", "campaign id", "name"), required=True),
    CanonicalField("date", "date", ("day", "date_day", "reporting_date", "calendar_date"), required=True),
    CanonicalField("channel", "text", ("platform", "media", "traffic_source")),
    CanonicalField("audience", "text", ("segment", "target_audience", "audience_segment")),
    CanonicalField("product_name", "text", ("product", "sku", "offering")),
    CanonicalField("impressions", "number", ("impressions", "impr", "views")),
    CanonicalField("spend", "currency", ("cost", "ad_spend", "amount_spent")),
    CanonicalField("clicks", "number", ("click", "ad_clicks", "total_clicks")),
    CanonicalField("sessions", "number", ("site_sessions", "visits", "visitors")),
    CanonicalField("conversions", "number", ("conv", "total_conversions", "leads", "signups")),
    CanonicalField("purchases", "number", ("orders", "buy", "sold")),
    CanonicalField("revenue", "currency", ("sales", "income", "total_revenue")),
)
CANONICAL_FEEDBACK_FIELDS = (
    CanonicalField("feedback_text", "text", ("feedback", "comment", "review", "response", "verbatim"), required=True),
    CanonicalField("feedback_date", "date", ("date", "submitted_at", "created_at")),
    CanonicalField("rating", "number", ("score", "stars", "nps")),
    CanonicalField("product_ref", "text", ("product", "sku")),
    CanonicalField("source_type", "text", ("channel", "survey", "review_site", "origin")),
)
CANONICAL_EXPERIMENT_FIELDS = (
    CanonicalField("experiment_name", "text", ("experiment", "test", "test_name"), required=True),
    CanonicalField("variant", "text", ("arm", "treatment", "group"), required=True),
    CanonicalField("observations", "number", ("value", "result", "metric_value")),
    CanonicalField("sample_size", "number", ("n", "users", "sessions_count")),
)

CANONICAL_SCHEMAS: dict[str, tuple[CanonicalField, ...]] = {
    "campaign_metrics": CANONICAL_CAMPAIGN_FIELDS,
    "customer_feedback": CANONICAL_FEEDBACK_FIELDS,
    "experiment_results": CANONICAL_EXPERIMENT_FIELDS,
    "product_facts": (),
    "brand_rules": (),
}
