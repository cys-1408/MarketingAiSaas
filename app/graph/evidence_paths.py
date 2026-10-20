"""Human-readable evidence paths for the Evidence Graph API and UI.

Every returned hop identifies its nodes, edge provenance, the rule that
produced it, and the evidence readers can open.  The serializer also
identifies missing links (where a connection is absent) and contradictory
edges, and never presents a connected path as proof of causation.
"""

from __future__ import annotations

from typing import Any

from app.db.models import Chunk, GraphNode
from app.graph.retrieval import GraphPath, GraphRetrievalResult

_EXPLANATIONS: dict[str, str] = {
    "USES_CHANNEL": "campaign ran on this channel",
    "TARGETS_SEGMENT": "campaign targeted this audience segment",
    "PROMOTES_PRODUCT": "campaign promoted this product",
    "CONTAINS_MESSAGE": "campaign used this message/offer",
    "LINKS_TO_PAGE": "campaign pointed to this landing page",
    "FEEDBACK_MENTIONS": "customer feedback mentions this product",
    "EXPRESSES_OBJECTION": "customer feedback expresses this objection",
    "OBSERVED_WITH_METRIC": "campaign was measured by this metric value",
    "ASSOCIATED_WITH_CONVERSION": "feedback co-occurs with this conversion observation "
                                  "(association only, not causation)",
    "TESTED_IN_EXPERIMENT": "change was tested in this experiment",
    "SUPPORTED_BY": "recommendation is supported by this evidence",
    "CONTRADICTED_BY": "evidence runs counter to this recommendation",
    "DERIVED_FROM": "derived from this source record",
}


def serialize_path(path: GraphPath, node_by_id: dict[str, GraphNode]) -> dict[str, Any]:
    hops: list[dict[str, Any]] = []
    previous = node_by_id.get(path.start_node_id)
    for step in path.steps:
        destination = node_by_id.get(step.dst_id)
        if previous is None or destination is None:
            continue
        hops.append(
            {
                "from": {
                    "id": previous.id,
                    "type": previous.node_type,
                    "label": previous.label,
                },
                "relation": step.edge_type,
                "explanation": _EXPLANATIONS.get(step.edge_type, step.edge_type),
                "provenance": step.provenance,
                "rule": step.rule,
                "to": {
                    "id": destination.id,
                    "type": destination.node_type,
                    "label": destination.label,
                },
                "connection": "observed data join" if step.provenance == "observed" else step.rule,
                "indicates_causation": False,
            }
        )
        previous = destination
    return {
        "start_node_id": path.start_node_id,
        "hops": hops,
        "path_is_causal_proof": False,
        "notes": ["Graph edges are associations with recorded provenance; they do not prove cause."],
    }


def serialize_graph_result(
    result: GraphRetrievalResult,
    *,
    db,  # noqa: ANN001 - Session
) -> dict[str, Any]:
    """Build the evidence-path payload used by the API and the graph UI."""
    nodes: dict[str, dict[str, Any]] = {}
    evidence_links: dict[str, list[dict[str, Any]]] = {}
    for node_id, node in result.nodes.items():
        props = node.props or {}
        attachments = []
        for chunk in db.execute(
            Chunk.__table__.select().where(
                Chunk.workspace_id == node.workspace_id,
                Chunk.source_id == node.source_id,
            ).limit(3)
        ).fetchall():
            attachments.append(
                {
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "source_version": chunk.source_version,
                    "locator": chunk.locator,
                }
            )
        nodes[node_id] = {
            "id": node_id,
            "node_type": node.node_type,
            "label": node.label,
            "props": {k: v for k, v in props.items() if k in ("metric_name", "value", "unit", "day", "status")},
            "source_id": node.source_id,
            "source_version": node.source_version,
            "evidence": attachments,
            "evidence_available": bool(attachments),
        }

    missing_links: list[dict[str, str]] = []
    if not result.paths:
        missing_links.append(
            {
                "kind": "no_connected_path",
                "detail": "No graph path connects the question's entities; "
                          "check that related sources are ingested.",
            }
        )
    if result.contradicting:
        missing_links.append(
            {
                "kind": "contradictory_evidence_present",
                "detail": f"{len(result.contradicting)} node(s) contained contradicting edges",
            }
        )

    serialized_paths = [
        serialize_path(path, result.nodes) for path in result.paths[:50]
    ]
    return {
        "nodes": nodes,
        "paths": serialized_paths,
        "supporting_node_ids": result.supporting,
        "contradicting_node_ids": result.contradicting,
        "missing_links": missing_links,
        "notes": [
            "Distinguish observed links from inferred ones; inferred links are heuristics.",
        ],
    }
