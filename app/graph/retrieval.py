"""Tenant-scoped graph retrieval with strict depth/size limits.

Traversal uses typed, parameterized queries (never unrestricted graph query
execution) and enforces workspace scoping at every step.  Results distinguish
observed edges from inferred/derived ones so callers can display the
difference instead of implying causality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import GraphEdge, GraphNode


@dataclass(slots=True)
class PathStep:
    edge_type: str
    provenance: str
    rule: str
    src_id: str
    dst_id: str


@dataclass(slots=True)
class GraphPath:
    start_node_id: str
    steps: list[PathStep] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GraphRetrievalResult:
    paths: list[GraphPath]
    nodes: dict[str, GraphNode]
    evidence_node_ids: list[str]
    supporting: list[str]
    contradicting: list[str]
    truncated_by_depth: bool = False


def resolve_start_nodes(
    db: Session,
    *,
    workspace_id: str,
    query: str,
    limit: int = 5,
) -> list[GraphNode]:
    """Resolve graph entities relevant to a question, workspace-scoped."""
    terms = query.lower()
    candidates = db.execute(
        select(GraphNode).where(GraphNode.workspace_id == workspace_id).limit(500)
    ).scalars().all()
    scored: list[tuple[float, GraphNode]] = []
    for node in candidates:
        label = node.label.lower()
        key = node.entity_key.lower()
        score = 0.0
        for token in terms.replace(",", " ").split():
            token = token.strip("\"'?.!")
            if len(token) < 3:
                continue
            if token in label:
                score += 2.0
            if token in key:
                score += 1.5
        if score > 0:
            scored.append((score, node))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [node for _, node in scored[:limit]]


def traverse(
    db: Session,
    *,
    workspace_id: str,
    start_node_id: str,
    depth: int | None = None,
    edge_types: tuple[str, ...] | None = None,
) -> list[GraphPath]:
    """BFS traversal with strict depth/result limits and scope checks."""
    settings = get_settings()
    max_depth = min(depth or settings.graph_traversal_max_depth, settings.graph_traversal_max_depth)
    max_nodes = settings.graph_traversal_max_nodes
    start = db.get(GraphNode, start_node_id)
    if start is None or start.workspace_id != workspace_id:
        return []
    paths: list[GraphPath] = []
    frontier: list[tuple[GraphNode, GraphPath]] = [(start, GraphPath(start_node_id=start.id))]
    visited = {start.id}
    while frontier and len(visited) < max_nodes:
        node, path = frontier.pop(0)
        if path.steps and len(path.steps) >= max_depth:
            continue
        edges = db.execute(
            select(GraphEdge).where(
                GraphEdge.workspace_id == workspace_id,
                GraphEdge.src_id == node.id,
            )
        ).scalars().all()
        for edge in edges:
            if edge_types and edge.edge_type not in edge_types:
                continue
            dest = db.get(GraphNode, edge.dst_id)
            if dest is None or dest.workspace_id != workspace_id:
                continue
            step = PathStep(
                edge_type=edge.edge_type,
                provenance=edge.provenance,
                rule=edge.rule,
                src_id=edge.src_id,
                dst_id=edge.dst_id,
            )
            new_path = GraphPath(
                start_node_id=path.start_node_id,
                steps=[*path.steps, step],
                node_ids=[*path.node_ids, edge.dst_id],
            )
            paths.append(new_path)
            if dest.id not in visited:
                visited.add(dest.id)
                frontier.append((dest, new_path))
            if len(visited) >= max_nodes:
                break
    return paths


def retrieve_graph_context(
    db: Session,
    *,
    workspace_id: str,
    query: str,
) -> GraphRetrievalResult:
    """Resolve entities for a question and collect supporting/contradicting links."""
    starts = resolve_start_nodes(db, workspace_id=workspace_id, query=query)
    all_paths: list[GraphPath] = []
    node_map: dict[str, GraphNode] = {}
    supporting: list[str] = []
    contradicting: list[str] = []
    for start in starts:
        paths = traverse(db, workspace_id=workspace_id, start_node_id=start.id)
        all_paths.extend(paths)
        node_map[start.id] = start
        for path in paths:
            for step in path.steps:
                if step.edge_type == "SUPPORTED_BY":
                    supporting.append(step.dst_id)
                elif step.edge_type == "CONTRADICTED_BY":
                    contradicting.append(step.dst_id)
            for node_id in path.node_ids:
                if node_id not in node_map:
                    node = db.get(GraphNode, node_id)
                    if node is not None and node.workspace_id == workspace_id:
                        node_map[node_id] = node
    return GraphRetrievalResult(
        paths=all_paths,
        nodes=node_map,
        evidence_node_ids=list(node_map.keys()),
        supporting=supporting,
        contradicting=contradicting,
    )
