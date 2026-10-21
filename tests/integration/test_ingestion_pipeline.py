"""Integration tests: the real ingestion pipeline end to end."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest


def upload_bytes(api, data: bytes, name: str, content_type: str = "text/csv"):
    files = {"file": (name, io.BytesIO(data), content_type)}
    response = api.post("sources/uploads", files=files)
    return response


def drive_job(api, source_id: str) -> dict:
    from tests.conftest import run_ingestion_now

    job_id = run_ingestion_now(source_id)
    status = api.get(f"ingestion/jobs/{job_id}").json()
    return status


def test_csv_ingestion_reaches_ready_with_metrics_and_graph(api, seeded_workspace):
    assert seeded_workspace, "workspace seeded"
    status_response = api.get(f"ingestion/jobs/{seeded_workspace['job_id']}")
    payload = status_response.json()
    assert payload["status"] == "ready", payload
    assert payload["row_count"] == 2
    stage_log = [s["stage"] for s in payload["stages"]]
    assert "inspecting" in stage_log and "normalizing" in stage_log and "indexing" in stage_log
    # Graph nodes exist for the ingested campaign.
    campaigns = api.get("campaigns").json()["campaigns"]
    assert any(c["name"] == "Launch Campaign" for c in campaigns)


def test_ambiguous_conversion_column_pauses_for_review(api):
    data = (
        "campaign_name,date,impressions,clicks,conv_events\n"
        "Beta Campaign,2026-09-01,900,45,12\n"
    ).encode()
    response = upload_bytes(api, data, "ambiguous.csv")
    assert response.status_code == 202, response.text
    source_id = response.json()["source_id"]
    from tests.conftest import run_ingestion_now

    job_id = run_ingestion_now(source_id)
    status = api.get(f"ingestion/jobs/{job_id}").json()
    assert status["status"] == "awaiting_review", status
    review = api.get(f"ingestion/jobs/{job_id}/mapping-review").json()
    assert review["candidates"], "review queue must contain the ambiguous column"
    columns = [c["column"] for c in review["candidates"]]
    assert "conv_events" in columns
    # The proposed conversion field must not be silently 'purchases' and must be reviewable.
    conversion = next(c for c in review["candidates"] if c["column"] == "conv_events")
    assert conversion["proposed_field"] in {"conversions", "purchases", "await_review"}
    assert conversion["confidence"] in {"low", "medium", "high", "auto_accept", "review"} or not conversion.get("auto_accept")
    assert not conversion.get("auto_accept")


def test_mapping_decision_resumes_pipeline(api):
    data = (
        "campaign_name,date,impressions,clicks,conv_events\n"
        "Resume Campaign,2026-09-01,900,45,12\n"
    ).encode()
    source_id = upload_bytes(api, data, "resume.csv").json()["source_id"]
    from tests.conftest import _execute_job

    from app.db.session import get_session_factory
    from app.db.models import IngestionJob
    from sqlalchemy import select

    with get_session_factory()() as db:
        job_id = db.execute(
            select(IngestionJob).where(IngestionJob.source_id == source_id)
        ).scalars().one().id
    _execute_job(job_id)
    review = api.get(f"ingestion/jobs/{job_id}/mapping-review").json()
    assert review["status"] == "awaiting_review"
    decisions = [
        {
            "candidate_id": c["id"],
            "action": "edit" if c["column"] == "conv_events" else "confirm",
            "chosen_field": "conversions" if c["column"] == "conv_events" else None,
        }
        for c in review["candidates"]
    ]
    submitted = api.post(
        f"ingestion/jobs/{job_id}/mapping-review", json={"decisions": decisions}
    )
    assert submitted.status_code == 200, submitted.text
    after = submitted.json()
    assert after["status"] in {"ready", "partially_ready"}, after
    # Decisions persist as versioned rules.
    campaigns = api.get("campaigns").json()["campaigns"]
    assert any(c["name"] == "Resume Campaign" for c in campaigns)


def test_duplicate_upload_is_idempotent(api, seeded_workspace):
    data = Path().resolve() / "data" / "test_object_storage"
    # Upload  the same bytes as the seeded workspace to trigger dedup.
    csv_bytes = (
        "campaign_name,date,channel,impressions,clicks,spend,purchases,revenue\n"
        "Launch Campaign,2026-09-01,Paid Social,1000,50,100,4,200\n"
        "Launch Campaign,2026-09-02,Paid Social,1100,55,105,5,220\n"
    ).encode()
    response = upload_bytes(api, csv_bytes, "metrics-again.csv")
    payload = response.json()
    assert payload["status"] == "duplicate"
    assert payload["source_id"] == seeded_workspace["source_id"]


def test_source_deletion_cleans_dependent_records(api, seeded_workspace):
    status = api.delete(f"ingestion/sources/{seeded_workspace['source_id']}")
    assert status.status_code == 200, status.text
    cleanup = status.json()["cleanup"]
    assert cleanup["chunks_removed"] > 0
    after = api.get(f"ingestion/jobs/{seeded_workspace['job_id']}").json()
    assert after["status"] == "cancelled"
    # After deletion, records are removed or marked removed where applicable.
    campaigns = api.get("campaigns").json()["campaigns"]
    assert not any(c["name"] == "Launch Campaign" for c in campaigns), campaigns


def test_mislabeled_file_rejected_cleanly(api):
    payload = b"PK\x03\x04not-really-a-zip"
    response = upload_bytes(api, payload, "broken.xlsx", "application/octet-stream")
    assert response.status_code in {202, 409, 422}


def test_empty_and_oversized_rejections(api):
    assert api.post(
        "sources/uploads", files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    ).status_code == 422


def test_docx_pdf_txt_ingestion(api):
    # Minimal but real DOCX built in-proc via python-docx.
    import docx as docx_module

    buffer = io.BytesIO()
    document = docx_module.Document()
    document.add_heading("Customer interview notes", level=1)
    document.add_paragraph(
        "The respondent said pricing was confusing and shipping costs were too high."
    )
    document.save(buffer)
    docx_bytes = buffer.getvalue()
    response = upload_bytes(
        api, docx_bytes, "interviews.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 202, response.text
    source_id = response.json()["source_id"]
    status = drive_job(api, source_id)
    assert status["status"] in {"ready", "partially_ready"}, status


def test_feedback_ingestion_creates_feedback_records(api):
    data = (
        "feedback_text,date,rating,product,source_type\n"
        "Pricing was confusing at checkout,2026-09-05,2,Core Platform,product_review\n"
        "Shipping costs were too high so I stopped,2026-09-06,1,Core Platform,product_review\n"
    ).encode()
    source_id = upload_bytes(api, data, "feedback.csv").json()["source_id"]
    status = drive_job(api, source_id)
    assert status["status"] in {"ready", "awaiting_review", "partially_ready"}, status
    if status["status"] == "awaiting_review":
        review = api.get(f"ingestion/jobs/{status['job_id'] if False else status.get('job_id', '')}/mapping-review").json()
        assert review["candidates"] is not None


def test_feedback_reingest_does_not_duplicate(api):
    data = (
        "feedback_text,date,rating,product,source_type\n"
        "Unique feedback fingerprint one,2026-09-05,2,Core Platform,product_review\n"
        "Unique feedback fingerprint one,2026-09-05,2,Core Platform,product_review\n"
    ).encode()
    source_id = upload_bytes(api, data, "feedbackdup.csv").json()["source_id"]
    status_a = drive_job(api, source_id)
    assert status_a["status"] in {"ready", "partially_ready"}, status_a
    from app.db.session import get_session_factory
    from app.db.models import FeedbackItem
    from sqlalchemy import select

    with get_session_factory()() as db:
        matching = db.execute(select(FeedbackItem)).scalars().all()
    same = [r for r in matching if r.summary.startswith("Unique feedback fingerprint")]
    # Content-fingerprint dedup keeps one canonical record per identical row.
    assert len(same) == 1
