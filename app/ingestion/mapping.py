"""Propose canonical field mappings; auto-accept only unambiguous cases.

Canonical target fields are defined per category with aliases and sample-value
checks.  High-confidence deterministic matches are auto-accepted; ambiguous
matches (multiple interpretations, metric-definition conflicts, mixed value
formats) enter the review queue for the workspace owner.  Accepted decisions
are stored as versioned mapping rules keyed by a schema fingerprint, and
schema drift is detected when a saved rule's fingerprint no longer matches a
new source.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from app.ingestion.classification import (
    CATEGORY_CAMPAIGN_METRICS,
    CATEGORY_CUSTOMER_FEEDBACK,
    CATEGORY_EXPERIMENT_RESULTS,
)
from app.ingestion.parsers import ParsedDocument, ParsedTable
from app.models.domain import CANONICAL_SCHEMAS, CanonicalField

_AUTO_ACCEPT_CONFIDENCE = 0.90


@dataclass(slots=True)
class MappingProposal:
    sheet: str
    column: str
    proposed_field: str | None
    alternatives: list[str]
    confidence: float
    reason: str
    impact: str
    sample_values: list[str] = field(default_factory=list)
    auto_accept: bool = False


def schema_fingerprint(columns: list[str]) -> str:
    joined = "::".join(sorted(column.strip().lower() for column in columns))
    return hashlib.sha256(joined.encode()).hexdigest()[:32]


def _norm(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]", " ", name.strip().lower())
    return re.sub(r"\s+", "_", cleaned.strip())


def _column_alias_targets(column: str, category: str) -> list[str]:
    normalized = _norm(column)
    schema = CANONICAL_SCHEMAS.get(category, ())
    for field in schema:
        aliases = {_norm(field.name), *(_norm(alias) for alias in field.aliases)}
        if normalized in aliases:
            return [field.name]
    # Prefix/substring matching for columns like "total_clicks" -> clicks
    matches: list[str] = []
    for field in schema:
        for alias in {_norm(field.name), *(_norm(alias) for alias in field.aliases)}:
            if normalized and (normalized.endswith(alias) or normalized.startswith(alias)):
                matches.append(field.name)
    return matches


def _value_pattern_conflicts(values: list[str]) -> bool:
    """Detect mixed representation (e.g. 2.4 vs 4.1% vs 0.031)."""
    shapes: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text.endswith("%"):
            shapes.add("percent")
        elif re.fullmatch(r"-?\d+(\.\d+)?", text):
            shapes.add("decimal" if "." in text else "integer")
        else:
            shapes.add("text")
    return len(shapes) > 1


def propose_field(column: str, category: str, sample_values: list[str]) -> MappingProposal:
    """Propose the canonical target for a single column."""
    schema = CANONICAL_SCHEMAS.get(category, ())
    direct = _column_alias_targets(column, category)
    unique = list(dict.fromkeys(direct))
    if not unique:
        return MappingProposal(
            sheet="", column=column, proposed_field=None, alternatives=[],
            confidence=0.0,
            reason=f"no canonical target matched '{column}' in the {category} schema",
            impact=(f"column '{column}' stays unmapped; it is preserved in raw records "
                    f"but excluded from analysis until mapped"),
            sample_values=[str(v) for v in sample_values[:3]],
        )
    if len(unique) == 1:
        target = unique[0]
        # Conversion-like columns must not silently mean "purchase".
        ambiguous_conversion = (
            target in {"conversions", "purchases"} and "convert" in _norm(column)
        )
        mixed = _value_pattern_conflicts(sample_values)
        confidence = 0.95
        reason = f"'{column}' directly matches canonical field '{target}'"
        if ambiguous_conversion:
            confidence = 0.55
            reason = (
                f"'{column}' maps to '{target}' but the source conversion event is "
                "unlabeled; treat as its own conversion event unless confirmed"
            )
        if mixed:
            confidence = min(confidence, 0.5)
            reason = (
                f"'{column}' contains mixed value formats (e.g. decimal and percent); "
                "the intended unit is ambiguous"
            )
        auto = confidence >= _AUTO_ACCEPT_CONFIDENCE
        return MappingProposal(
            sheet="", column=column, proposed_field=target,
            alternatives=[c for c in unique if c != target] or [f.name for f in schema[:2]],
            confidence=round(confidence, 3), reason=reason,
            impact=f"affects {target} calculations for every row using this column",
            sample_values=[str(v) for v in sample_values[:3]], auto_accept=auto,
        )
    # Multiple candidate targets -> consequential ambiguity, needs review.
    return MappingProposal(
        sheet="", column=column, proposed_field=unique[0],
        alternatives=unique[1:],
        confidence=round(0.4 + 0.1 * max(0, 3 - len(unique)), 2),
        reason=(
            f"'{column}' plausibly maps to several canonical fields "
            f"({', '.join(unique)}); the intended meaning must be confirmed"
        ),
        impact="a wrong automatic choice would distort the affected metrics",
        sample_values=[str(v) for v in sample_values[:3]],
        auto_accept=False,
    )


def propose_table_mappings(
    table: ParsedTable,
    category: str,
    saved_rules: dict[str, str] | None = None,
) -> list[MappingProposal]:
    """Propose mappings for every column of one parsed table.

    ``saved_rules`` maps column name -> previously approved canonical field and
    is applied first when the fingerprint matches (see functions above).
    """
    saved_rules = saved_rules or {}
    proposals: list[MappingProposal] = []
    targets_used: dict[str, list[str]] = {}
    for column in table.columns:
        if column == "__row__":
            continue
        normalized = _norm(column)
        proposal: MappingProposal | None = None
        if normalized in saved_rules:
            target = saved_rules[normalized]
            schema = CANONICAL_SCHEMAS.get(category, ())
            drift = target not in {f.name for f in schema}
            proposal = MappingProposal(
                sheet=table.name, column=column, proposed_field=target,
                alternatives=[], confidence=0.99 if not drift else 0.3,
                reason=
                    "reused previously approved mapping rule"
                    if not drift
                    else "saved rule targets a no-longer-valid canonical field (schema drift)",
                impact="drift means the reused rule may silently misclassify data",
                auto_accept=not drift,
            )
        if proposal is None:
            samples = [
                str(row.get(column, "")).strip()
                for row in table.rows[:12]
                if str(row.get(column, "")).strip()
            ]
            base = propose_field(column, category, samples)
            base.sheet = table.name
            proposal = base
        targets_used.setdefault(proposal.proposed_field or "$unmapped", []).append(proposal.column)
        proposals.append(proposal)
    # A canonical field may only be fed by one source column; otherwise the
    # computation would double count.  Require review.
    for target, columns in targets_used.items():
        if target != "$unmapped" and len(columns) > 1:
            secondary = columns[1:]
            for proposal in proposals:
                if proposal.proposed_field == target and proposal.column in secondary:
                    proposal.confidence = min(proposal.confidence, 0.45)
                    proposal.reason += (
                        f"; another column already maps to '{target}' "
                        f"({columns[0]}) so both cannot feed the same metric"
                    )
                    proposal.auto_accept = False
    for proposal in proposals:
        if proposal.proposed_field is None:
            proposal.status = "leave_unmapped"  # explicit, never silent
    return proposals


def propose_document_mappings(doc: ParsedDocument, category: str) -> dict[str, list[MappingProposal]]:
    return {
        table.name: propose_table_mappings(table, category)
        for table in doc.tables
    }


def fingerprint_matches(doc: ParsedDocument, category: str, saved_rules: dict[str, str]) -> bool:
    columns = doc.tables[0].columns if doc.tables else []
    return schema_fingerprint([c for c in columns if c != "__row__"]) == schema_fingerprint(list(saved_rules.keys()))


def columns_needing_review(proposals: list[MappingProposal]) -> list[MappingProposal]:
    return [p for p in proposals if not p.auto_accept]
