"""Ingestion evaluation: mapping accuracy, review rate, parsing, dedup."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.evaluation.schemas import MappingCase
from app.ingestion.classification import classify
from app.ingestion.mapping import propose_table_mappings
from app.ingestion.parsers import ParsedTable, parse_file


def evaluate_mapping_cases(cases: list[MappingCase]) -> dict[str, Any]:
    correct = 0
    review_correct = 0
    detail: dict[str, Any] = {}
    for case in cases:
        table = ParsedTable(
            name="data",
            columns=case.headers,
            rows=[{h: "sample" for h in case.headers}],
        )
        proposals = propose_table_mappings(table, case.category)
        chosen = {
            proposal.column: proposal.proposed_field
            for proposal in proposals
        }
        mapping_ok = all(
            chosen.get(column) == target
            for column, target in case.expected_mappings.items()
        )
        review_expected = bool(
            [p for p in proposals if not p.auto_accept]
        )
        review_ok = review_expected == case.expects_review
        correct += int(mapping_ok)
        review_correct += int(review_ok)
        detail[case.case_id] = {
            "mappings_ok": mapping_ok,
            "review_ok": review_ok,
            "chosen": chosen,
            "needs_review": review_expected,
        }
    total = len(cases)
    return {
        "mapping_accuracy": round(correct / max(1, total), 4),
        "review_request_rate": round(
            sum(1 for c in detail.values() if c["needs_review"]) / max(1, total), 4
        ),
        "review_correctness": round(review_correct / max(1, total), 4),
        "cases": total,
        "detail": detail,
    }


def evaluate_parsing(files: dict[str, bytes]) -> dict[str, Any]:
    """Real parse success on provided fixture bytes."""
    successes = 0
    total = len(files)
    detail: dict[str, Any] = {}
    for name, data in files.items():
        file_type = name.rsplit(".", 1)[-1].lower()
        try:
            doc = parse_file(data, file_type)
            successes += 1
            detail[name] = {
                "ok": True,
                "tables": len(doc.tables),
                "rows": doc.row_count,
                "sections": len(doc.sections),
            }
        except Exception as exc:  # noqa: BLE001 - measurement, not product path
            detail[name] = {"ok": False, "error": str(exc)[:200]}
    return {
        "parsing_success_rate": round(successes / max(1, total), 4),
        "cases": total,
        "detail": detail,
    }


def evaluate_duplicate_detection(dataset: list[dict[str, Any]]) -> dict[str, Any]:
    """Dataset rows carry business keys; duplicates must be detected."""
    seen: set[tuple] = set()
    duplicates_found = 0
    expected_duplicates = sum(1 for row in dataset if row.get("_is_duplicate"))
    for row in dataset:
        key = (row["campaign_id"], str(row["day"]), row["metric_name"])
        if key in seen:
            duplicates_found += 1
        seen.add(key)
    return {
        "duplicates_detected": duplicates_found,
        "expected_duplicates": expected_duplicates,
        "correct": duplicates_found == expected_duplicates,
    }
