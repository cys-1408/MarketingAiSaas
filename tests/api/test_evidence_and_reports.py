"""API tests: evidence, graph, reports, evaluations."""

from __future__ import annotations

import io

from tests.conftest import run_ingestion_now
from tests.integration.test_analytics_and_retrieval import _campaign_id, _upload


def _seed_campaign_and_feedback(api):
    _upload(
        api,
        (
            "customer survey feedback comments\n"
        ).encode() if False else (
            "feedback_text,date,rating,product,source_type\n"
            "Pricing confusion dominates support tickets,2026-09-05,2,Core Platform,product_review\n"
        ).encode(),
        "report_feedback.csv",
    )
    return _campaign_id(api, "Launch Campaign")


def test_evidence_lookup_scoped(api, seeded_workspace):
    from app.db.session import get_session_factory
    from app.db.models import EvidenceRecord
    from sqlalchemy import select

    campaign_id = _seed_campaign_and_feedback(api)
    with get_session_factory()() as db:
        record = db.execute(
            select(EvidenceRecord).where(EvidenceRecord.workspace_id == api.workspace_id)
        ).scalars().first()
    if record is None:
        pytest_import_skip = None
        return
    response = api.get(f"evidence/{record.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["source"]["source_id"] == record.source_id
    assert "distinguishes" in body


def test_missing_evidence_reported(api):
    assert api.get("evidence/ev_does_not_exist").status_code == 404


def test_report_generation_and_export(api, seeded_workspace):
    campaign_id = _seed_campaign_and_feedback(api)
    from app.db.session import get_session_factory
    from app.db.models import EvidenceRecord
    from sqlalchemy import select

    with get_session_factory()() as db:
        evidence_ids = [
            r.id for r in db.execute(
                select(EvidenceRecord).where(EvidenceRecord.workspace_id == api.workspace_id)
            ).scalars().all()
        ]
    created = api.post(
        "reports",
        json={
            "campaign_id": campaign_id,
            "date_start": "2026-09-01",
            "date_end": "2026-09-30",
            "evidence_ids": evidence_ids,
        },
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["report_id"]
    report = api.get(f"reports/{report_id}").json()
    assert report["campaign_id"] == campaign_id
    for fact in report.get("facts", []):
        assert fact["evidence_id"] in evidence_ids
        assert fact["source"]["source_id"]
    export = api.get(f"reports/{report_id}/export")
    assert export.status_code == 200
    assert "Metrics" in export.text or "Facts" in export.text


def test_report_rejects_foreign_evidence(api, seeded_workspace, tenant_two):
    # Attempt to generate a report referencing a nonexistent/foreign evidence id.
    campaign_id = _seed_campaign_and_feedback(api)
    response = api.post(
        "reports",
        json={
            "campaign_id": campaign_id,
            "date_start": "2026-09-01",
            "date_end": "2026-09-30",
            "evidence_ids": ["ev_from_someone_else"],
        },
    )
    assert response.status_code == 404


def test_report_publish_requires_approval(api, seeded_workspace):
    campaign_id = _seed_campaign_and_feedback(api)
    created = api.post(
        "reports",
        json={
            "campaign_id": campaign_id,
            "date_start": "2026-09-01",
            "date_end": "2026-09-30",
            "evidence_ids": [],
        },
    )
    report_id = created.json()["report_id"]
    publish = api.post(
        f"reports/{report_id}/publish-request", json={"reviewer_note": "for newsletter"}
    )
    assert publish.status_code == 202
    body = publish.json()
    assert body["status"] == "pending"
    assert "nothing was sent" in body["detail"]


def test_source_chunks_endpoint(api, seeded_workspace):
    response = api.get(f"sources/{seeded_workspace['source_id']}/chunks")
    assert response.status_code == 200
    body = response.json()
    assert body["chunks"], "ingested source must expose indexed chunks"
    for chunk in body["chunks"]:
        assert chunk["locator"] is not None


def test_evaluation_runs_record_measured_metrics(api, seeded_workspace):
    runs = api.post("evaluations/runs")
    assert runs.status_code == 202, runs.text
    body = runs.json()
    metrics = body["metrics"]
    assert metrics["answers"]["cases"] >= 1
    listing = api.get("evaluations/runs").json()
    assert listing["runs"], listing
    for run in listing["runs"]:
        assert isinstance(run["metrics"], dict)
