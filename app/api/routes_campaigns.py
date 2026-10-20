"""Campaign routes: list, summary, compare, funnel — thin wrappers over the
shared AnalyticsService (no metric logic in route code)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import request_db
from app.api.routes_auth import _current_user
from app.core.tenancy import new_id
from app.db.models import PendingReviewItem, Recommendation
from app.tools.analytics import AnalyticsService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CompareRequest(BaseModel):
    campaign_ids: list[str] = Field(min_length=2, max_length=5)
    metric_names: list[str]
    start_date: str
    end_date: str


class ExperimentBriefRequest(BaseModel):
    hypothesis: str = Field(min_length=10)
    control: str
    variant: str
    audience: str = ""
    primary_metric: str
    guardrail_metrics: list[str] = []


@router.get("")
def list_campaigns(claims=Depends(_current_user), db: Session = Depends(request_db)):
    return {"campaigns": AnalyticsService(db).list_campaigns(
        workspace_id=claims.workspace_id, user_id=claims.user_id
    )}


@router.get("/{campaign_id}/summary")
def summary(
    campaign_id: str,
    start_date: str = "2000-01-01",
    end_date: str = "2100-12-31",
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    try:
        data = AnalyticsService(db).get_campaign_summary(
            workspace_id=claims.workspace_id,
            campaign_id=campaign_id,
            start_date=start_date,
            end_date=end_date,
            user_id=claims.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return data


@router.post("/compare")
def compare(payload: CompareRequest, claims=Depends(_current_user), db: Session = Depends(request_db)):
    try:
        return AnalyticsService(db).compare_campaigns(
            workspace_id=claims.workspace_id,
            campaign_ids=payload.campaign_ids,
            metric_names=payload.metric_names,
            start_date=payload.start_date,
            end_date=payload.end_date,
            user_id=claims.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{campaign_id}/funnel")
def funnel(
    campaign_id: str,
    start_date: str = "2000-01-01",
    end_date: str = "2100-12-31",
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    try:
        return AnalyticsService(db).funnel_metrics(
            workspace_id=claims.workspace_id,
            campaign_id=campaign_id,
            start_date=start_date,
            end_date=end_date,
            user_id=claims.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class RecommendationCreate(BaseModel):
    campaign_id: str
    action: str = Field(min_length=5)
    observed_facts: list[str] = []
    interpretation: str = ""
    hypothesis: str = ""
    supporting_evidence: list[str] = []
    contradictory_evidence: list[str] = []
    primary_metric: str = ""
    risks: list[str] = []
    missing_data: list[str] = []


@router.post("/{campaign_id}/recommendations", status_code=201)
def create_recommendation(
    campaign_id: str,
    payload: RecommendationCreate,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    from app.core.tenancy import get_scoped
    from app.db.models import Campaign

    authorize_placeholder = None  # tenancy enforced below via get_scoped
    del authorize_placeholder
    campaign = get_scoped(db, Campaign, claims.workspace_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    recommendation = Recommendation(
        workspace_id=claims.workspace_id,
        campaign_id=campaign.id,
        action=payload.action,
        observed_facts=payload.observed_facts,
        interpretation=payload.interpretation,
        hypothesis=payload.hypothesis,
        supporting_evidence=payload.supporting_evidence,
        contradictory_evidence=payload.contradictory_evidence,
        primary_metric=payload.primary_metric,
        risks=payload.risks,
        missing_data=payload.missing_data,
        created_by=claims.user_id,
    )
    db.add(recommendation)
    db.commit()
    return {"id": recommendation.id, "status": recommendation.status}


@router.post("/experiments/brief", status_code=201)
def create_experiment_brief(
    payload: ExperimentBriefRequest,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    """Create an experiment brief; predicted lift is never fabricated."""
    from app.core.security import CAP_GENERATE_REPORTS
    from app.core.tenancy import authorize_workspace
    from app.db.models import Experiment

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_GENERATE_REPORTS,
    )
    experiment = Experiment(
        workspace_id=claims.workspace_id,
        name=payload.hypothesis[:80],
        hypothesis=payload.hypothesis,
        control=payload.control,
        variant=payload.variant,
        audience=payload.audience,
        primary_metric=payload.primary_metric,
        guardrail_metrics=payload.guardrail_metrics,
        stopping_rules="stop on guardrail violation or after the planned duration",
        confounders=[
            "seasonality", "audience overlap", "concurrent campaigns",
        ],
        success_criteria=(
            f"a measureable improvement in {payload.primary_metric} with "
            "guardrails not degrading"
        ),
        sample_size_note=(
            "compute required sample size with a power analysis before "
            "stopping decisions; small samples cannot justify early wins"
        ),
        status="draft",
        created_by=claims.user_id,
    )
    db.add(experiment)
    db.commit()
    return {
        "id": experiment.id,
        "name": experiment.name,
        "hypothesis": experiment.hypothesis,
        "control": experiment.control,
        "variant": experiment.variant,
        "primary_metric": experiment.primary_metric,
        "guardrail_metrics": experiment.guardrail_metrics,
        "stopping_rules": experiment.stopping_rules,
        "confounders": experiment.confounders,
        "success_criteria": experiment.success_criteria,
        "sample_size_note": experiment.sample_size_note,
        "status": experiment.status,
    }


@router.get("/{campaign_id}/evidence-review")
def review_pending(
    campaign_id: str,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    """List pending brand/content review items for a campaign."""
    from app.core.tenancy import authorize_workspace

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=2
    )
    items = db.query(PendingReviewItem).filter(
        PendingReviewItem.workspace_id == claims.workspace_id,
        PendingReviewItem.status == "pending",
    ).all()
    return {
        "pending": [
            {"id": i.id, "type": i.item_type, "payload": i.payload} for i in items
        ]
    }
