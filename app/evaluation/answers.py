"""Answer evaluation: citations, numbers, abstention, causal language.

Deterministic checks for citation ids and numeric presence; no fabricated
scores — anything unmeasurable is omitted from results.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.state import InvestigationResult
from app.tools.verification import verify_reply

NAMES_RE = re.compile(r"\d+(?:\.\d+)?")


def evaluate_answer(
    *,
    result: InvestigationResult,
    case,  # AnswerCase-shaped
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    checks["expected_behavior"] = (
        result.status == case.expected_behavior
    )
    if case.expected_behavior == "answered":
        citations = result.citations or []
        citation_sources = {c["source_id"] for c in citations}
        expected_sources = set(case.expected_evidence_sources)
        checks["citations_rendered"] = bool(citations)
        if expected_sources:
            checks["citation_sources_match"] = bool(
                citation_sources & expected_sources
            )
            expected = len(expected_sources & citation_sources)
            checks["citation_correctness"] = expected / max(1, len(expected_sources))
        else:
            checks["citation_correctness"] = 1.0 if citations else 0.0
        numbers_in_facts = set(
            NAMES_RE.findall(" ".join(result.observed_facts))
        )
        if case.expected_numbers:
            checks["numeric_accuracy"] = (
                all(number in " ".join(result.observed_facts) for number in case.expected_numbers)
            )
            checks["numbers_found"] = sorted(numbers_in_facts)
        # Causal language checks: unqualified causal markers in facts or
        # recommendations must not appear without hypothesis framing.
        text = " ".join(result.observed_facts + result.recommendations).lower()
        causal_markers = ("caused", "because of", "due to", "proves that")
        flagged = [m for m in causal_markers if m in text]
        checks["causal_language_violations"] = len(flagged)
        checks["no_guarded_causal_claims"] = not flagged or bool(
            result.hypotheses or result.measurement_plan
        )
    else:  # abstained
        checks["abstention_correctness"] = result.status == "abstained"
        checks["gave_reason"] = bool(result.abstention_reason)

    return {"case_id": case.case_id, "checks": checks, "passed": all(checks.values())}


def evaluate_case_manifest(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-case evaluation into dataset-level metrics."""
    total = len(cases)
    if total == 0:
        return {"cases": 0, "pass_rate": 0.0}
    passed = sum(1 for r in results if r.get("passed"))
    return {"cases": total, "pass_rate": round(passed / total, 4)}
