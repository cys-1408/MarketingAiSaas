"""Evaluation runs: measured metrics against versioned datasets, never invented."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import request_db
from app.api.routes_auth import _current_user
from app.core.security import CAP_RUN_INVESTIGATIONS
from app.core.tenancy import authorize_workspace
from app.db.models import EvaluationRun
from app.models.router import ModelRouter
from app.evaluation.runner import (
    persist_run,
    run_answer_evaluation,
    run_ingestion_evaluation,
    run_retrieval_evaluation,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/runs", status_code=202)
def create_run(
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_RUN_INVESTIGATIONS,
    )
    router = ModelRouter(db)
    retrieval = run_retrieval_evaluation(db, workspace_id=claims.workspace_id)
    answers = run_answer_evaluation(db, workspace_id=claims.workspace_id, router=router)
    ingestion = run_ingestion_evaluation()
    metrics = {
        "retrieval": _public_metrics(retrieval),
        "answers": answers,
        "ingestion": _public_metrics(ingestion),
    }
    run = persist_run(
        db,
        workspace_id=claims.workspace_id,
        mode="full",
        metrics=metrics,
        detail={
            "retrieval_detail": retrieval.get("per_case", {}),
            "answers_detail": answers.get("detail", {}),
            "ingestion_detail": ingestion.get("detail", {}),
        },
    )
    db.commit()
    return {"run_id": run.id, "dataset_version": run.dataset_version, "metrics": metrics}


@router.get("/runs")
def list_runs(claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    runs = db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.workspace_id == claims.workspace_id)
        .order_by(EvaluationRun.created_at.desc())
        .limit(20)
    ).scalars().all()
    return {
        "runs": [
            {
                "id": r.id,
                "dataset_version": r.dataset_version,
                "mode": r.mode,
                "created_at": r.created_at.isoformat(),
                "metrics": r.metrics,
            }
            for r in runs
        ],
        "note": (
            "no fabricated scores: when a dataset has not been evaluated "
            "the list is empty rather than filled with invented numbers"
        ),
    }


def _public_metrics(payload: dict) -> dict:
    metrics = payload.get("metrics")
    if metrics is None:
        return {k: v for k, v in payload.items() if isinstance(v, (int, float, str))}
    return {
        "recall_at_k": metrics.recall_at_k,
        "precision_at_k": metrics.precision_at_k,
        "mrr": metrics.mrr,
        "ndcg_at_k": metrics.ndcg_at_k,
        "cases": metrics.cases,
        "tenant_filter_correct": payload.get("tenant_filter_correct", 0),
    }
