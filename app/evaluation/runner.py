"""Versioned evaluation runner.

Loads dataset cases from ``evals/``, executes the real services against
them, and persists one EvaluationRun with measured metrics.  Nothing is
fabricated: if a dataset is missing or empty the run reports that honestly.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.tenancy import new_id
from app.db.models import EvaluationRun
from app.evaluation import agents as agent_eval
from app.evaluation import answers as answer_eval
from app.evaluation import ingestion as ingestion_eval
from app.evaluation import retrieval as retrieval_eval
from app.evaluation.schemas import (
    DATASET_VERSION,
    AnswerCase,
    RetrievalCase,
    ToolCase,
)
from app.retrieval.bm25_search import BM25Index
from app.retrieval.embeddings import EmbeddingModel
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.vector_search import VectorIndex

logger = get_logger(__name__)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def run_retrieval_evaluation(db: Session, *, workspace_id: str) -> dict[str, Any]:
    cases = [
        RetrievalCase(
            case_id=row["case_id"],
            workspace_id=workspace_id,
            query=row["query"],
            relevant_chunk_ids=row.get("relevant_chunk_ids", []),
            expected_sources=row.get("expected_sources", []),
            should_be_empty=row.get("should_be_empty", False),
        )
        for row in _load_jsonl(_evals_path("retrieval_cases.jsonl"))
    ]
    result = retrieval_eval.evaluate_retrieval(db, cases=cases)
    result["note"] = (
        "scores are measured only for fixtures indexed into this workspace; "
        "missing fixtures report as uncovered rather than as zero quality"
    )
    return result


def run_answer_evaluation(
    db: Session,
    *,
    workspace_id: str,
    router,  # noqa: ANN001
) -> dict[str, Any]:
    cases = [
        AnswerCase(
            case_id=row["case_id"],
            question=row["question"],
            expected_behavior=row["expected_behavior"],
            expected_evidence_sources=row.get("expected_evidence_sources", []),
            expected_numbers=row.get("expected_numbers", []),
        )
        for row in _load_jsonl(_evals_path("investigation_cases.jsonl"))
    ]
    results: list[dict[str, Any]] = []
    latency_sum = 0.0
    for case in cases:
        started = time.perf_counter()
        outcome = _run_one_case(db, router, workspace_id, case.question)
        case_result = answer_eval.evaluate_answer(
            result=outcome["result"], case=case
        )
        case_result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results.append(case_result)
    latency_sum = sum(r["latency_ms"] for r in results)
    return {
        "cases": len(cases),
        "pass_rate": round(sum(1 for r in results if r["passed"]) / max(1, len(cases)), 4),
        "avg_latency_ms": round(latency_sum / max(1, len(results)), 1),
        "detail": results,
    }


def _evals_path(name: str) -> Path:
    from app.core.config import get_settings as _gs

    return Path(_gs().evals_dir) / name


def _run_one_case(db: Session, router, workspace_id: str, question: str):  # noqa: ANN001
    from app.agents.workflow import InvestigationWorkflow

    workflow = InvestigationWorkflow(router=router)
    result = workflow.run(
        db=db, workspace_id=workspace_id, user_id="evaluation", question=question
    )
    return {"result": result}


def run_ingestion_evaluation() -> dict[str, Any]:
    cases = [
        case
        for case in (
            _mapping_case_from_row(row)
            for row in _load_jsonl(_evals_path("mapping_cases.jsonl"))
            if row.get("type") != "invalid"
        )
        if case is not None
    ]
    metrics = ingestion_eval.evaluate_mapping_cases(cases)
    fixture_dir = _evals_path("fixtures")
    files = {
        path.name: path.read_bytes()
        for path in sorted(fixture_dir.glob("*"))
        if path.is_file()
    } if fixture_dir.exists() else {}
    parsing = ingestion_eval.evaluate_parsing(files)
    return {**metrics, **parsing}


def _mapping_case_from_row(row: dict[str, Any]):
    try:
        from app.evaluation.schemas import MappingCase

        return MappingCase(
            case_id=row["case_id"],
            headers=row["headers"],
            category=row["category"],
            expected_mappings=row["expected_mappings"],
            expects_review=row.get("expects_review", False),
        )
    except (KeyError, TypeError):
        return None


def persist_run(
    db: Session,
    *,
    workspace_id: str,
    mode: str,
    metrics: dict[str, Any],
    detail: dict[str, Any],
) -> EvaluationRun:
    run = EvaluationRun(
        workspace_id=workspace_id,
        dataset_version=DATASET_VERSION,
        mode=mode,
        metrics=dict(metrics),
        detail=dict(detail),
    )
    db.add(run)
    db.flush()
    return run
