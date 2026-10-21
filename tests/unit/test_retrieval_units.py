"""Unit tests: chunking, embeddings, hybrid fusion, graph schema."""

from __future__ import annotations

import math

import pytest

from app.graph.schema import EdgeSpec, GraphSchemaError, NodeSpec, validate_edge, validate_node
from app.ingestion.parsers import ParsedSection, ParsedTable
from app.retrieval.chunking import chunk_parsed_document, chunk_table_rows, chunk_sections
from app.retrieval.embeddings import EmbeddingModel, cosine_similarity, tokenize
from app.retrieval.hybrid_search import fuse
from app.retrieval.vector_search import VectorHit
from app.retrieval.bm25_search import BM25Hit


def test_tokens_preserve_domain_terms():
    tokens = tokenize("Campaign promo_2026 had 4.5% CTR")
    assert "promo" in tokens and "2026" in tokens


def test_embedding_deterministic_and_normalized():
    model = EmbeddingModel.configured()
    a = model.embed_one("pricing page confusing")
    b = model.embed_one("pricing page confusing")
    assert a == b
    norm = math.sqrt(sum(v * v for v in a))
    assert abs(norm - 1.0) < 1e-6  # unit length
    assert all(len(v) == model.dim for v in [a])
    assert model.dim >= 8


def test_cosine_similarity_bounds():
    model = EmbeddingModel.configured()
    v1 = model.embed_one("launch campaign")
    zero = [0.0] * len(v1)
    assert cosine_similarity(v1, v1) == pytest.approx(1.0, abs=1e-6)
    assert cosine_similarity(v1, zero) == 0.0


def test_table_chunking_keeps_row_context_with_labels():
    table = ParsedTable(
        name="metrics",
        columns=["campaign_name", "date", "clicks", "spend"],
        rows=[{"campaign_name": "A", "date": "2026-09-01", "clicks": "50", "spend": "100", "__row__": 2}],
    )
    chunks = chunk_table_rows(table)
    assert len(chunks) == 1
    text = chunks[0].text
    assert "clicks: 50" in text and "spend: 100" in text
    assert "metrics" in text  # table name retained as context
    assert chunks[0].locator["row"] == 2


def test_narrative_chunking_preserves_sections_and_locators():
    sections = [
        ParsedSection(heading="Pricing objections", text="Sentence one. " * 50, locator={"heading": "Pricing objections"}),
    ]
    chunks = chunk_sections(sections)
    assert chunks
    for chunk in chunks:
        assert chunk.locator["heading"] == "Pricing objections"


def test_chunk_fingerprint_dedupes_identical_content():
    doc = ParsedTable(name="t", columns=["a"], rows=[{"a": "same", "__row__": 2}])
    chunks = chunk_parsed_document(type("D", (), {"tables": [doc], "sections": []})())
    text = chunks[0].text
    from app.retrieval.chunking import chunk_fingerprint

    assert chunk_fingerprint(text) == chunk_fingerprint(text)


def _hit(chunk_id: str, kind_ret: str = "vector"):
    template = VectorHit if kind_ret == "vector" else BM25Hit
    return template(
        chunk_id=chunk_id, score=1.0, source_id="s1", source_version=1,
        source_name="src", title="t", text="text", locator={}, kind="narrative",
    )


def test_rrf_fusion_dedupes_and_combines_contributions():
    fused, diagnostics = fuse([_hit("a"), _hit("b")], [_hit("b"), _hit("c")])
    assert set(fused.keys()) == {"a", "b", "c"}
    # 'b' ranked by both retrievers so its fused score must exceed 'a's.
    assert fused["b"].fused_score > fused["a"].fused_score
    assert fused["b"].contributions["vector"] and fused["b"].contributions["bm25"]
    assert diagnostics["vector"] == 2 and diagnostics["bm25"] == 2


# --- graph schema -------------------------------------------------------------


def test_node_and_edge_schema_validation():
    node = validate_node(NodeSpec(node_type="Campaign", entity_key="c1", label="C"))
    assert node.entity_key == "c1"
    with pytest.raises(GraphSchemaError):
        validate_node(NodeSpec(node_type="Zzz", entity_key="c", label="x"))
    edge = validate_edge(
        EdgeSpec(
            edge_type="USES_CHANNEL", src_key="c1", dst_key="paid social",
            src_type="Campaign", dst_type="Channel", rule="declared",
        )
    )
    assert edge.provenance == "observed"
    with pytest.raises(GraphSchemaError):
        validate_edge(
            EdgeSpec(
                edge_type="CAUSES", src_key="a", dst_key="b",
                src_type="Campaign", dst_type="Campaign", rule="hopefully",
            )
        )
    # Inferred edges require a recorded derivation rule.
    with pytest.raises(GraphSchemaError):
        validate_edge(
            EdgeSpec(
                edge_type="SUPPORTED_BY", src_key="r", dst_key="m",
                src_type="Recommendation", dst_type="MetricObservation",
                provenance="inferred", rule="",
            )
        )        # Causal edge types are not part of the schema at all.
        assert "CAUSED_BY" not in EDGE_TYPES


def test_invalid_edge_triple_rejected():
    with pytest.raises(GraphSchemaError):
        validate_edge(
            EdgeSpec(
                edge_type="USES_CHANNEL", src_key="a", dst_key="b",
                src_type="FeedabackItem", dst_type="Channel", rule="bad",
            )
        )
