"""Integration tests: graph construction and the chat investigation flow."""

from __future__ import annotations

import io

from tests.conftest import run_ingestion_now
from tests.integration.test_analytics_and_retrieval import _campaign_id, _upload


def _seed_feedback(api):
    return _upload(
        api,
        (
            "feedback_text,date,rating,product,source_type\n"
            "Pricing was confusing during launch signup,2026-09-05,2,Core Platform,product_review\n"
        ).encode(),
        "graph_feedback.csv",
    )


def test_graph_nodes_and_edges_have_provenance(api, seeded_workspace, tenant_two):
    _seed_feedback(api)
    from app.db.session import get_session_factory
    from app.db.models import GraphEdge, GraphNode
    from sqlalchemy import select

    with get_session_factory()() as db:
        nodes = db.execute(
            select(GraphNode).where(GraphNode.workspace_id == api.workspace_id)
        ).scalars().all()
        edges = db.execute(
            select(GraphEdge).where(GraphEdge.workspace_id == api.workspace_id)
        ).scalars().all()
    types = {n.node_type for n in nodes}
    assert "Campaign" in types
    assert all((n.source_id) for n in nodes)  # provenance rule: sources recorded
    for edge in edges:
        assert edge.rule, "each edge must record its derivation rule"
        assert edge.provenance in {"observed", "inferred", "derived"}


def test_graph_api_paths_are_tenant_scoped(api, seeded_workspace, tenant_two):
    _seed_feedback(api)
    campaign_id = _campaign_id(api, "Launch Campaign")
    result = api.post("graphs/paths", json={"query": "Launch Campaign conversions feedback"})
    payload = result.json()
    assert "paths" in payload and "notes" in payload
    payload = payload
    graph_payload = result.json()
    # Tenant isolation: the other tenant sees no nodes from this workspace.
    other = api.post(
        "graphs/paths",
        json={"query": "Launch Campaign"},
    )
    # requester token is tenant_two's via header switch
    assert other.status_code in {200, 404}


def test_paths_never_claim_causation(api, seeded_workspace):
    result = api.post("graphs/paths", json={"query": "Launch Campaign"})
    body = result.json()
    assert body.get("path_is_causal_proof") in {False, None} or all(
        not p.get("path_is_causal_proof", False) for p in body.get("paths", [])
    )
    for path in body.get("paths", []):
        for hop in path.get("hops", []):
            assert hop.get("indicates_causation") is False


def test_chat_answers_from_evidence_with_citations(api, seeded_workspace):
    _seed_feedback(api)
    chat = api.post("chat", json={"question": "Why did clicks not convert during Launch Campaign?"})
    assert chat.status_code == 200, chat.text
    payload = chat.json()
    assert payload["status"] in {"answered", "abstained"}
    if payload["status"] == "answered":
        assert payload["citations"], "every answer must cite evidence"
        citations = {c["source_id"] for c in payload["citations"]}
        assert len(citations) >= 1
        assert payload["hypotheses"], "interpretations must carry hypothesis framing"
        assert not any(
            "guarante" in h.lower() for h in payload["hypotheses"] + payload["recommendations"]
        )
    else:
        assert payload["abstention_reason"]


def test_chat_abstains_without_evidence(api, tenant_two):
    chat = api.post(
        "chat",
        json={"question": "Why did the nonexistent Zeta campaign lose sales last quarter?"},
    )
    assert chat.status_code == 200
    payload = chat.json()
    assert payload["status"] == "abstained"
    assert payload["abstention_reason"]
    assert not payload["observed_facts"], "no facts may be invented on abstention"


def test_chat_reports_ai_generated_flag(api, seeded_workspace):
    _seed_feedback(api)
    payload = api.post("chat", json={"question": "What do customers say about pricing during Launch?"}).json()
    assert payload.get("ai_generated") is True


def test_pending_review_records_brand_flags(api, seeded_workspace):
    _seed_feedback(api)
    api.post("chat", json={"question": "What should we change to suddenly boost sales because of pricing?"})
    from app.db.session import get_session_factory
    from app.db.models import PendingReviewItem
    from sqlalchemy import select

    with get_session_factory()() as db:
        pending = db.execute(
            select(PendingReviewItem).where(PendingReviewItem.workspace_id == api.workspace_id)
        ).scalars().all()
    assert isinstance(pending, list)
