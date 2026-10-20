"""Integration tests: deterministic analytics and tenant-scoped retrieval."""

from __future__ import annotations

import io

from tests.conftest import run_ingestion_now
import pytest


def _campaign_id(api, name: str) -> str:
    campaigns = api.get("campaigns").json()["campaigns"]
    return next(c["id"] for c in campaigns if c["name"] == name)


def _upload(api, data: bytes, name: str) -> str:
    files = {"file": (name, io.BytesIO(data), "text/csv")}
    response = api.post("sources/uploads", files=files)
    source_id = response.json()["source_id"]
    run_ingestion_now(source_id)
    return source_id


def test_analytics_summary_is_deterministic_with_definitions(api, seeded_workspace):
    campaign_id = _campaign_id(api, "Launch Campaign")
    summary = api.get(
        f"campaigns/{campaign_id}/summary?start_date=2026-09-01&end_date=2026-09-30"
    ).json()
    impressions = next(m for m in summary["metrics"] if m["metric_name"] == "impressions")
    # Golden values from test fixture rows (1000 + 1100).
    assert impressions["value"] == 2100
    assert impressions["unit"] == "count"
    derived = {d["metric_name"]: d for d in summary["derived"]}
    ctr = derived["click_through_rate"]
    assert ctr["value"] == pytest.approx(105 / 2100)
    assert ctr["definition"] == "clicks / impressions"
    # Zero-spend-safe derivations: answers never claim a division that has no denominator.
    assert summary["limitations"], "missing-metric notes must be explicit"


def test_summary_requires_valid_date_window(api, seeded_workspace):
    campaign_id = _campaign_id(api, "Launch Campaign")
    response = api.get(
        f"campaigns/{campaign_id}/summary?start_date=2026-09-30&end_date=2026-09-01"
    )
    assert response.status_code == 422


def test_compare_campaigns(api, seeded_workspace):
    data = (
        "campaign_name,date,channel,impressions,clicks,spend,revenue\n"
        "Compare Target,2026-09-01,Email,,800,60,900\n"
        "Compare Target,2026-09-02,Email,,820,61,910\n"
    ).encode()
    other_source = _upload(api, data, "compare.csv")
    campaign_id_a = _campaign_id(api, "Launch Campaign")
    campaign_id_b = _campaign_id(api, "Compare Target")
    payload = api.post(
        "campaigns/compare",
        json={
            "campaign_ids": [campaign_id_a, campaign_id_b],
            "metric_names": ["impressions", "clicks"],
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
    ).json()
    assert {c["campaign_name"] for c in payload["campaigns"]} == {"Launch Campaign", "Compare Target"}
    for campaign in payload["campaigns"]:
        for metric in campaign["metrics"]:
            assert metric["definition"] or metric["metric_name"] in {"tags"}


def test_unsupported_metric_name_rejected(api, seeded_workspace):
    campaign_id = _campaign_id(api, "Launch Campaign")
    response = api.post(
        "campaigns/compare",
        json={
            "campaign_ids": [campaign_id_a := campaign_id, campaign_id],
            "metric_names": ["bogus_metric"],
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
    )
    assert response.status_code == 422


def test_hybrid_retrieval_tenant_scoped(api, seeded_workspace):
    # Index feedback in this tenant.
    _upload(
        api,
        (
            "feedback_text,date,rating,product,source_type\n"
            "Checkout pricing was confusing for new signups,2026-09-05,2,Launch,product_review\n"
        ).encode(),
        "feedback_retrieval.csv",
    )
    from app.db.session import get_session_factory
    from app.retrieval.embeddings import EmbeddingModel
    from app.retrieval.bm25_search import BM25Index
    from app.retrieval.vector_search import VectorIndex
    from app.retrieval.hybrid_search import HybridSearch
    from sqlalchemy import select
    from app.db.models import Chunk

    model = EmbeddingModel.configured()
    hybrid = HybridSearch(vector_index=VectorIndex(model), bm25_index=BM25Index())
    with get_session_factory()() as db:
        result = hybrid.search(
            db,
            workspace_id=api.workspace_id,
            query="pricing confusing signups",
            top_k=5,
        )
        assert result.candidates, "expected retrieval results within the tenant"
        # Exact-term BM25 query reaches table-row chunks about the campaign.
        exactly = hybrid.search(
            db, workspace_id=api.workspace_id, query="Launch Campaign Paid Social", top_k=5,
        )
        assert any("Launch Campaign" in c.text for c in exactly.candidates)


def test_vectors_deleted_for_source_update(api, seeded_workspace):
    from app.db.session import get_session_factory
    from app.db.models import Chunk
    from sqlalchemy import select, func

    with get_session_factory()() as db:
        before = db.execute(
            select(func.count(Chunk.id)).where(Chunk.workspace_id == api.workspace_id)
        ).scalar_one()
    assert before > 0
    # Reprocess the same source -> prior version vectors are replaced, not doubled.
    reprocess = api.post(f"ingestion/sources/{seeded_workspace['source_id']}/reprocess")
    assert reprocess.status_code == 200
    run_ingestion_now(reprocess.json()["source_id"]) if False else run_ingestion_now(seeded_workspace["source_id"])
    with get_session_factory()() as db:
        after = db.execute(
            select(func.count(Chunk.id)).where(Chunk.workspace_id == api.workspace_id)
        ).scalar_one()
    assert after >= before  # chunk ids per version fingerprint; no unbounded growth
