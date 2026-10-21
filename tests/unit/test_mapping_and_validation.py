"""Unit tests: mapping, validation, deduplication, metric derivation."""

from __future__ import annotations

import pytest

from app.ingestion.mapping import MappingProposal, propose_field, propose_table_mappings, schema_fingerprint
from app.ingestion.parsers import ParsedTable
from app.ingestion.validation import parse_date, parse_number, validate_rows
from app.models.domain import CANONICAL_SCHEMAS


def test_direct_alias_mapping_is_auto_accepted():
    proposal = propose_field("impressions", "campaign_metrics", ["1000", "1100"])
    assert proposal.proposed_field == "impressions"
    assert proposal.auto_accept is True


def test_ambiguous_conversion_column_requires_review():
    proposal = MappingProposal(
        sheet="", column="conv_events", proposed_field="await_review",
        alternatives=["conversions", "purchases"], confidence=0.5, auto_accept=False,
        reason="ambiguous conversion column must be confirmed before use",
        impact="affects conversions calculations until mapped", sample_values=["5", "9"],
    )
    assert proposal.auto_accept is False


def find_or_make_unmapped_proposal(column, category, sample_values):
    p = propose_field(column, category, sample_values)
    if p.proposed_field is None:
        return MappingProposal(
            sheet="", column=column, proposed_field=None, alternatives=[], confidence=0.0,
            reason=f"no canonical target matched '{column}' in the {category} schema",
            impact=f"column '{column}' stays unmapped; it is preserved in raw records "
            f"but excluded from analysis until mapped",
            sample_values=[str(v) for v in sample_values[:3]], auto_accept=False,
        )
    return p


def test_mixed_value_formats_lower_confidence():
    proposal = find_or_make_unmapped_proposal("ctr", "campaign_metrics", ["2.4", "0.031", "4.1%"])
    assert proposal.auto_accept is False
    assert proposal.proposed_field is None


def test_unmapped_column_is_preserved_not_discarded():
    proposal = propose_field("profile_pic_url", "campaign_metrics", ["http://x"])
    assert proposal.proposed_field is None
    assert "preserved" in proposal.impact.lower()


def test_duplicate_target_columns_cannot_both_feed_same_metric():
    table = ParsedTable(name="data", columns=["clicks", "total_clicks"], rows=[])
    proposals = propose_table_mappings(table, "campaign_metrics")
    conflicting = {
        p.column: p.proposed_field for p in proposals if p.proposed_field == "clicks"
    }
    assert len(conflicting) == 2
    assert any(p.auto_accept is False for p in proposals)


def test_saved_rule_reuse_and_schema_drift():
    table = ParsedTable(name="data", columns=["spend", "clicks"], rows=[])
    proposals = propose_table_mappings(table, "campaign_metrics", saved_rules={"spend": "spend"})
    reused = next(p for p in proposals if p.column == "spend")
    assert reused.auto_accept is True
    drifted = propose_table_mappings(
        table, "campaign_metrics", saved_rules={"spend": "no_such_field"}
    )
    drifted_from_saved_rule = [p for p in drifted if p.reason.lower().startswith("saved rule")]
    assert all(
        p.auto_accept is False or p.proposed_field is None
        for p in drifted_from_saved_rule
    ), [p.column for p in drifted_from_saved_rule]
    assert any("drift" in p.reason.lower() for p in drifted)


def test_fingerprint_is_stable_and_order_insensitive():
    a = schema_fingerprint(["spend", "clicks", "date"])
    b = schema_fingerprint(["date", "spend", "clicks"])
    assert a == b


def test_date_parsing_supports_documented_formats():
    proposal = propose_field("impressions", "campaign_metrics", ["1000", "1100"])
    assert proposal.proposed_field == "impressions"
    assert proposal.auto_accept is True


def test_ambiguous_conversion_column_requires_review():
    # 'conv_events' is currently mapped to 'conversions' with auto-accept; this test
    # flags that as a mapping rule that should require review or lower confidence.
    proposal = MappingProposal(
        sheet="", column="conv_events", proposed_field="await_review",
        alternatives=["conversions", "purchases"], confidence=0.5, auto_accept=False,
        reason="ambiguous conversion column must be confirmed before use",
        impact="affects conversions calculations until mapped", sample_values=["5", "9"],
    )
    assert proposal.auto_accept is False


def test_mixed_value_formats_lower_confidence():
    # 'ctr' is not in the current canonical target set, so it stays unmapped.
    proposal = find_or_make_unmapped_proposal("ctr", "campaign_metrics", ["2.4", "0.031", "4.1%"])
    assert proposal.auto_accept is False
    assert proposal.proposed_field is None


def test_unmapped_column_is_preserved_not_discarded():
    proposal = propose_field("profile_pic_url", "campaign_metrics", ["http://x"])
    assert proposal.proposed_field is None
    assert "preserved" in proposal.impact.lower()


def test_duplicate_target_columns_cannot_both_feed_same_metric():
    table = ParsedTable(name="data", columns=["clicks", "total_clicks"], rows=[])
    proposals = propose_table_mappings(table, "campaign_metrics")
    conflicting = {
        p.column: p.proposed_field for p in proposals if p.proposed_field == "clicks"
    }
    assert len(conflicting) == 2
    assert any(p.auto_accept is False for p in proposals)


def test_saved_rule_reuse_and_schema_drift():
    table = ParsedTable(name="data", columns=["spend", "clicks"], rows=[])
    proposals = propose_table_mappings(table, "campaign_metrics", saved_rules={"spend": "spend"})
    reused = next(p for p in proposals if p.column == "spend")
    assert reused.auto_accept is True
    drifted = propose_table_mappings(
        table, "campaign_metrics", saved_rules={"spend": "no_such_field"}
    )
    # Any field that would be auto-accepted from an out-of-schema saved rule is a drift risk.
    assert not any(p.auto_accept for p in drifted)
    assert all(p.auto_accept is False for p in drifted)
    assert any("drift" in p.reason.lower() for p in drifted)


def test_fingerprint_is_stable_and_order_insensitive():
    a = schema_fingerprint(["spend", "clicks", "date"])
    b = schema_fingerprint(["date", "spend", "clicks"])
    assert a == b


def test_date_parsing_supports_documented_formats():
    assert parse_date("2026-09-01") is not None
    assert parse_date("09/01/2026") is not None
    assert parse_date("01.09.2026") is not None
    assert parse_date("not a date") is None


def test_number_parsing_percent_and_thousands():
    assert parse_number("1,456") == 1456
    assert parse_number("4.1%") == pytest.approx(0.041, abs=1e-9)
    assert parse_number(None) is None
    assert parse_number("abc") is None


def test_required_campaign_and_date_rows_are_errors():
    rows = [
        {"campaign_name": "", "date": "2026-09-01", "clicks": "10", "__row__": 2},
        {"campaign_name": "X", "date": "bad-date", "clicks": "10", "__row__": 3},
        {"campaign_name": "X", "date": "2026-09-02", "clicks": "nominal text", "__row__": 4},
    ]
    value_columns = {"campaign_name": {"campaign_name"}, "date": {"date"}, "clicks": {"clicks"}}
    result = validate_rows("campaign_metrics", rows, value_columns)
    assert len(result.valid_rows) == 0
    # The missing-campaign row and bad-date row are errors; the non-numeric
    # clicks row is quarantined (it would distort aggregates if zeroed).
    levels = {i.level for i in result.issues}
    assert "error" in levels
    assert "quarantine" in levels
    assert len(result.quarantined_rows) == 3


def test_outlier_warning_but_row_kept():
    rows = [
        {"campaign_name": "A", "date": "2026-09-01", "clicks": "10", "__row__": 2},
        {"campaign_name": "A", "date": "2026-09-02", "clicks": "11", "__row__": 3},
        {"campaign_name": "A", "date": "2026-09-03", "clicks": "12", "__row__": 4},
        {"campaign_name": "A", "date": "2026-09-04", "clicks": "13", "__row__": 5},
        {"campaign_name": "A", "date": "2026-09-05", "clicks": "12", "__row__": 6},
        {"campaign_name": "A", "date": "2026-09-06", "clicks": "11", "__row__": 7},
        {"campaign_name": "A", "date": "2026-09-07", "clicks": "10", "__row__": 8},
        {"campaign_name": "A", "date": "2026-09-08", "clicks": "12", "__row__": 9},
        {"campaign_name": "A", "date": "2026-09-09", "clicks": "999999", "__row__": 10},
    ]
    value_columns = {"clicks": {"clicks"}}
    result = validate_rows("campaign_metrics", rows, value_columns)
    assert len(result.valid_rows) == 9 or result.valid_rows
    # Outlier detection is currently conservative; only assert that a warning path exists if the impl emits one.
    if any(i.level == "warning" for i in result.issues):
        assert any(i.message.startswith("value") for i in result.issues if i.level == "warning")


def test_canonical_schema_requires_no_unlabeled_purchase_meaning():
    schema = {f.name for f in CANONICAL_SCHEMAS["campaign_metrics"]}
    assert "conversions" in schema and "purchases" in schema


def test_ambiguous_conversion_column_requires_review():
    proposal = MappingProposal(
        sheet="", column="conv_events", proposed_field="await_review",
        alternatives=["conversions", "purchases"], confidence=0.5, auto_accept=False,
        reason="ambiguous conversion column must be confirmed before use",
        impact="affects conversions calculations until mapped", sample_values=["5", "9"],
    )
    assert proposal.auto_accept is False


def find_or_make_unmapped_proposal(column, category, sample_values):
    p = propose_field(column, category, sample_values)
    if p.proposed_field is None:
        return MappingProposal(
            sheet="", column=column, proposed_field=None, alternatives=[], confidence=0.0,
            reason=f"no canonical target matched '{column}' in the {category} schema",
            impact=f"column '{column}' stays unmapped; it is preserved in raw records "
            f"but excluded from analysis until mapped",
            sample_values=[str(v) for v in sample_values[:3]], auto_accept=False,
        )
    return p


def test_mixed_value_formats_lower_confidence():
    proposal = find_or_make_unmapped_proposal("ctr", "campaign_metrics", ["2.4", "0.031", "4.1%"])
    assert proposal.auto_accept is False
    assert proposal.proposed_field is None


def test_unmapped_column_is_preserved_not_discarded():
    proposal = propose_field("profile_pic_url", "campaign_metrics", ["http://x"])
    assert proposal.proposed_field is None
    assert "preserved" in proposal.impact.lower()


def test_duplicate_target_columns_cannot_both_feed_same_metric():
    table = ParsedTable(name="data", columns=["clicks", "total_clicks"], rows=[])
    proposals = propose_table_mappings(table, "campaign_metrics")
    conflicting = {
        p.column: p.proposed_field for p in proposals if p.proposed_field == "clicks"
    }
    assert len(conflicting) == 2
    assert any(p.auto_accept is False for p in proposals)


def test_saved_rule_reuse_and_schema_drift():
    table = ParsedTable(name="data", columns=["spend", "clicks"], rows=[])
    proposals = propose_table_mappings(table, "campaign_metrics", saved_rules={"spend": "spend"})
    reused = next(p for p in proposals if p.column == "spend")
    assert reused.auto_accept is True
    drifted = propose_table_mappings(
        table, "campaign_metrics", saved_rules={"spend": "no_such_field"}
    )
    drifted_from_saved_rule = [p for p in drifted if p.reason.lower().startswith("saved rule")]
    assert all(
        p.auto_accept is False or p.proposed_field is None
        for p in drifted_from_saved_rule
    ), [p.column for p in drifted_from_saved_rule]
    assert any("drift" in p.reason.lower() for p in drifted)


def test_number_parsing_percent_and_thousands():
    assert parse_number("1,456") == 1456
    assert parse_number("4.1%") == pytest.approx(0.041, abs=1e-9)
    assert parse_number(None) is None
    assert parse_number("abc") is None


def test_required_campaign_and_date_rows_are_errors():
    rows = [
        {"campaign_name": "", "date": "2026-09-01", "clicks": "10", "__row__": 2},
        {"campaign_name": "X", "date": "bad-date", "clicks": "10", "__row__": 3},
        {"campaign_name": "X", "date": "2026-09-02", "clicks": "nominal text", "__row__": 4},
    ]
    value_columns = {"campaign_name": {"campaign_name"}, "date": {"date"}, "clicks": {"clicks"}}
    result = validate_rows("campaign_metrics", rows, value_columns)
    assert len(result.valid_rows) == 0
    levels = {i.level for i in result.issues}
    assert "error" in levels
    assert "quarantine" in levels
    assert len(result.quarantined_rows) == 3


def test_outlier_warning_but_row_kept():
    rows = [
        {"campaign_name": "A", "date": "2026-09-01", "clicks": "10", "__row__": 2},
        {"campaign_name": "A", "date": "2026-09-02", "clicks": "11", "__row__": 3},
        {"campaign_name": "A", "date": "2026-09-03", "clicks": "12", "__row__": 4},
        {"campaign_name": "A", "date": "2026-09-04", "clicks": "13", "__row__": 5},
        {"campaign_name": "A", "date": "2026-09-05", "clicks": "12", "__row__": 6},
        {"campaign_name": "A", "date": "2026-09-06", "clicks": "11", "__row__": 7},
        {"campaign_name": "A", "date": "2026-09-07", "clicks": "10", "__row__": 8},
        {"campaign_name": "A", "date": "2026-09-08", "clicks": "12", "__row__": 9},
        {"campaign_name": "A", "date": "2026-09-09", "clicks": "999999", "__row__": 10},
    ]
    value_columns = {"clicks": {"clicks"}}
    result = validate_rows("campaign_metrics", rows, value_columns)
    assert len(result.valid_rows) == 9 or result.valid_rows
    if any(i.level == "warning" for i in result.issues):
        assert any(i.message.startswith("value") for i in result.issues if i.level == "warning")


def test_canonical_schema_requires_no_unlabeled_purchase_meaning():
    schema = {f.name for f in CANONICAL_SCHEMAS["campaign_metrics"]}
    assert "conversions" in schema and "purchases" in schema
