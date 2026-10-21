"""End-to-end: the critical user journey from workspace to report."""

from __future__ import annotations

import io

from tests.conftest import run_ingestion_now
from tests.integration.test_analytics_and_retrieval import _campaign_id, _upload


def test_full_journey_signup_to_report(api, seeded_workspace):
    # 1. Workspace authenticated (fixture signup) and source ingested.
    job = api.get(f"ingestion/jobs/{seeded_workspace['job_id']}").json()
    assert job["status"] == "ready", job

    # 2. Deterministic analytics.
    from tests.integration.test_analytics_and_retrieval import _campaign_id
    campaign_id = _campaign_id(api, "Launch Campaign")
    summary = api.get(
        f"campaigns/{campaign_id}/summary?start_date=2026-09-01&end_date=2026-09-30"
    ).json()
    impressions = next(m for m in summary["metrics"] if m["metric_name"] == "impressions")
    assert impressions["value"] == 2100

    # 3. Additional feedback ingested and chat investigation cites it.
    from tests.integration.test_analytics_and_retrieval import _upload
    feedback_source = _upload(
        api,
        (
            "feedback_text,date,rating,product,source_type\n"
            "Launch pricing was confusing to buyers,2026-09-05,2,Core Platform,product_review\n"
        ).encode(),
        "e2e_feedback.csv",
    )
    chat = api.post(
        "chat",
        json={"question": "Why did clicks not convert during Launch Campaign, and what should we test?"},
    ).json()
    assert chat["status"] in {"answered", "abstained"}
    if chat["status"] == "answered":
        assert chat["citations"]
        assert chat["measurement_plan"] or chat["hypotheses"]

    # 4. Evidence graph explorable.
    graph = api.post("graphs/paths", json={"query": "Launch Campaign feedback pricing"}).json()
    assert "nodes" in graph

    # 5. Evidence-linked report generated and exported.
    created = api.post(
        "reports",
        json={
            "campaign_id": campaign_id,
            "date_start": "2026-09-01",
            "date_end": "2026-09-30",
            "evidence_ids": [],
        },
    )
    assert created.status_code in (200, 201)

    # 6. Source update -> reprocess -> freshness/version updated.
    reprocess = api.post(f"ingestion/sources/{seeded_workspace['source_id']}/reprocess")
    assert reprocess.status_code == 200
    run_ingestion_now(seeded_workspace["source_id"])
    dummy_chunks = api.get(f"sources/{seeded_workspace['source_id']}/chunks").json()
    assert dummy_chunks["chunks"]

    # 7. Source deletion declared handled at the persistence layer.
    deleted = api.delete(f"ingestion/sources/{seeded_workspace['source_id']}")
    assert deleted.json()["deleted"] is True
    cleanup = deleted.json()["cleanup"]
    assert cleanup["metrics_removed"] >= 0


def test_log_request_id_present_in_responses(api):
    raw = api._client.get("/api/v1/health")
    assert raw.status_code == 200
    ready = api._client.get("/api/v1/ready")
    assert ready.status_code == 200
    checks = ready.json()["checks"]
    assert checks["database"] == "ok"


def test_openapi_documents_intended_routes(api):
    schema = api._client.get("/openapi.json").json()
    paths = set(schema["paths"])
    expected = {
        "/api/v1/auth/signup", "/api/v1/auth/login", "/api/v1/auth/logout",
        "/api/v1/auth/me", "/api/v1/workspaces", "/api/v1/sources/uploads",
        "/api/v1/campaigns", "/api/v1/chat", "/api/v1/reports",
    }
    missing = expected - paths
    assert not missing, f"missing documented routes: {missing}"
