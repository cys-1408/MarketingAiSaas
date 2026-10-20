"""Builds the Campaign Evidence Graph from canonical persisted records.

Construction is idempotent (stable (type,key) node identity), tenant-aware,
source-version-aware, and supports removing one source's contributions on
deletion/reprocessing without touching evidence from other sources.  Edges
carry provenance and a derivation rule; observed data creates observed edges,
heuristic/derived links are labelled inferred and never treated as causal.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenancy import new_id
from app.db.models import (
    Campaign,
    CampaignMetric,
    FeedbackItem,
    GraphEdge,
    GraphNode,
    Product,
)
from app.graph.schema import EdgeSpec, NodeSpec, validate_edge, validate_node

# entity keys are (node_type, key) composables; id resolution is deferred
# until after all nodes of a build are upserted.
_Built = tuple[str, str]  # (node_type, entity_key)


def _ensure_node(
    db: Session,
    workspace_id: str,
    spec: NodeSpec,
    *,
    source_id: str,
    source_version: int,
) -> GraphNode:
    spec = validate_node(spec)
    existing = db.execute(
        select(GraphNode).where(
            GraphNode.workspace_id == workspace_id,
            GraphNode.node_type == spec.node_type,
            GraphNode.entity_key == spec.entity_key,
        )
    ).scalar_one_or_none()
    if existing:
        existing.label = spec.label
        existing.props = {**existing.props, **spec.props} if existing.props else dict(spec.props)
        return existing
    node = GraphNode(
        workspace_id=workspace_id,
        node_type=spec.node_type,
        entity_key=spec.entity_key,
        label=spec.label,
        props=spec.props,
        source_id=source_id,
        source_version=source_version,
    )
    db.add(node)
    db.flush()
    return node


def _ensure_edge(
    db: Session,
    workspace_id: str,
    spec: EdgeSpec,
    node_ids: dict[_Built, str],
    *,
    source_id: str,
    source_version: int,
) -> None:
    spec = validate_edge(spec)
    src_key = (spec.src_type, spec.src_key)
    dst_key = (spec.dst_type, spec.dst_key)
    src_id = node_ids.get(src_key)
    dst_id = node_ids.get(dst_key)
    if src_id is None or dst_id is None:
        raise ValueError(
            f"edge references unknown node: {src_key!r} or {dst_key!r} not in this build"
        )
    existing = db.execute(
        select(GraphEdge).where(
            GraphEdge.workspace_id == workspace_id,
            GraphEdge.edge_type == spec.edge_type,
            GraphEdge.src_id == src_id,
            GraphEdge.dst_id == dst_id,
        )
    ).scalar_one_or_none()
    if existing:
        existing.provenance = spec.provenance
        existing.rule = spec.rule
        existing.source_id = source_id
        existing.source_version = source_version
        return
    db.add(
        GraphEdge(
            workspace_id=workspace_id,
            edge_type=spec.edge_type,
            src_id=src_id,
            dst_id=dst_id,
            provenance=spec.provenance,
            rule=spec.rule,
            source_id=source_id,
            source_version=source_version,
            time_start=spec.time_start,
            time_end=spec.time_end,
        )
    )


def build_for_campaign_metrics(
    db: Session,
    *,
    workspace_id: str,
    source_id: str,
    source_version: int,
) -> dict[str, int]:
    """Create/update campaign, channel-observation and metric nodes+edges."""
    node_ids: dict[_Built, str] = {}
    campaigns = db.execute(
        select(Campaign).where(Campaign.workspace_id == workspace_id, Campaign.source_id == source_id)
    ).scalars().all()
    node_count = edge_count = 0
    for campaign in campaigns:
        campaign_node = _ensure_node(
            db, workspace_id,
            NodeSpec(
                node_type="Campaign",
                entity_key=campaign.external_key or campaign.id,
                label=campaign.name,
                props={"status": campaign.status, "channel": campaign.channel},
            ),
            source_id=source_id, source_version=source_version,
        )
        node_ids[("Campaign", campaign_node.entity_key)] = campaign_node.id
        node_count += 1
        if campaign.channel:
            channel_node = _ensure_node(
                db, workspace_id,
                NodeSpec(node_type="Channel", entity_key=campaign.channel.lower(), label=campaign.channel),
                source_id=source_id, source_version=source_version,
            )
            node_ids[("Channel", channel_node.entity_key)] = channel_node.id
            node_count += 1
            _ensure_edge(
                db, workspace_id,
                EdgeSpec(
                    edge_type="USES_CHANNEL",
                    src_key=campaign_node.entity_key, dst_key=channel_node.entity_key,
                    src_type="Campaign", dst_type="Channel",
                    provenance="observed", rule="campaign record declares this channel",
                    time_start=campaign.start_date, time_end=campaign.end_date,
                ),
                node_ids, source_id=source_id, source_version=source_version,
            )
            edge_count += 1
        metrics = db.execute(
            select(CampaignMetric).where(
                CampaignMetric.workspace_id == workspace_id,
                CampaignMetric.campaign_id == campaign.id,
                CampaignMetric.source_id == source_id,
            )
        ).scalars().all()
        for metric in metrics:
            obs_key = f"{campaign.id}:{metric.metric_name}"
            obs_node = _ensure_node(
                db, workspace_id,
                NodeSpec(
                    node_type="MetricObservation",
                    entity_key=obs_key,
                    label=f"{metric.metric_name}={metric.value}",
                    props={
                        "metric_name": metric.metric_name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "day": str(metric.day),
                    },
                ),
                source_id=source_id, source_version=source_version,
            )
            node_ids[("MetricObservation", obs_key)] = obs_node.id
            node_count += 1
            _ensure_edge(
                db, workspace_id,
                EdgeSpec(
                    edge_type="OBSERVED_WITH_METRIC",
                    src_key=campaign_node.entity_key, dst_key=obs_key,
                    src_type="Campaign", dst_type="MetricObservation",
                    provenance="observed",
                    rule=f"metric row {metric.day} from source {source_id} v{source_version}",
                    time_start=metric.day, time_end=metric.day,
                ),
                node_ids, source_id=source_id, source_version=source_version,
            )
            edge_count += 1
    return {"nodes": node_count, "edges": edge_count}


def build_for_feedback(
    db: Session,
    *,
    workspace_id: str,
    source_id: str,
    source_version: int,
) -> dict[str, int]:
    """Create FeedbackItem nodes with mention/objection links where derivable."""
    node_ids: dict[_Built, str] = {}
    items = db.execute(
        select(FeedbackItem).where(
            FeedbackItem.workspace_id == workspace_id,
            FeedbackItem.source_id == source_id,
        )
    ).scalars().all()
    products = {
        p.normalized_name: p
        for p in db.execute(
            select(Product).where(Product.workspace_id == workspace_id)
        ).scalars().all()
    }
    node_count = edge_count = 0
    for item in items:
        key = f"fb:{item.content_fingerprint}"
        node = _ensure_node(
            db, workspace_id,
            NodeSpec(
                node_type="FeedbackItem", entity_key=key,
                label=item.summary or item.text[:80],
                props={"source_type": item.source_type},
            ),
            source_id=source_id, source_version=source_version,
        )
        node_ids[("FeedbackItem", key)] = node.id
        node_count += 1
        ref = item.product_ref.strip().lower()
        if ref and ref in products:
            product = products[ref]
            product_node = _ensure_node(
                db, workspace_id,
                NodeSpec(
                    node_type="Product", entity_key=product.normalized_name,
                    label=product.name,
                ),
                source_id=source_id, source_version=source_version,
            )
            node_ids[("Product", product_node.entity_key)] = product_node.id
            node_count += 1
            _ensure_edge(
                db, workspace_id,
                EdgeSpec(
                    edge_type="FEEDBACK_MENTIONS",
                    src_key=key, dst_key=product.normalized_name,
                    src_type="FeedbackItem", dst_type="Product",
                    provenance="observed",
                    rule=f"feedback row references product '{product.name}'",
                ),
                node_ids, source_id=source_id, source_version=source_version,
            )
            edge_count += 1
    return {"nodes": node_count, "edges": edge_count}


def link_objections_to_conversion(
    db: Session,
    *,
    workspace_id: str,
) -> dict[str, int]:
    """Inferred association edges: feedback mentioning products with conversion metrics.

    This is an *inferred* relationship (heuristic: the feedback text mentions a
    product that also has a conversion metric in the workspace) and the rule
    is recorded; co-occurrence is never causal proof. Runs at workspace level
    after feedback + metric nodes exist.
    """
    node_count = edge_count = 0
    feedback_nodes = db.execute(
        select(GraphNode).where(
            GraphNode.workspace_id == workspace_id,
            GraphNode.node_type == "FeedbackItem",
        )
    ).scalars().all()
    node_ids: dict[_Built, str] = {}
    for node in feedback_nodes:
        node_ids[("FeedbackItem", node.entity_key)] = node.id
        node_count += 1
        linked_metric = _metric_for_product(db, workspace_id, node.label)
        if linked_metric is None:
            continue
        metric, campaign = linked_metric
        obs_key = f"{campaign.id}:conversions"
        obs = db.execute(
            select(GraphNode).where(
                GraphNode.workspace_id == workspace_id,
                GraphNode.node_type == "MetricObservation",
                GraphNode.entity_key == obs_key,
            )
        ).scalar_one_or_none()
        if obs is None:
            continue
        node_ids[("MetricObservation", obs_key)] = obs.id
        _ensure_edge(
            db, workspace_id,
            EdgeSpec(
                edge_type="ASSOCIATED_WITH_CONVERSION",
                src_key=node.entity_key, dst_key=obs_key,
                src_type="FeedbackItem", dst_type="MetricObservation",
                provenance="inferred",
                rule="feedback mentions a product whose conversion metric exists in "
                     "the same workspace; co-occurrence only, not causation",
            ),
            node_ids, source_id=metric.source_id, source_version=metric.source_version,
        )
        edge_count += 1
    return {"nodes": node_count, "edges": edge_count}


def _metric_for_product(db: Session, workspace: str, label: str) -> tuple[CampaignMetric, Campaign] | None:
    """Find a conversion metric for a product whose name appears in ``label``."""
    products = db.execute(
        select(Product).where(Product.workspace_id == workspace)
    ).scalars().all()
    for product in products:
        if product.name.lower()[:18] in label.lower():
            campaigns = db.execute(
                select(CampaignMetric, Campaign)
                .join(Campaign, Campaign.id == CampaignMetric.campaign_id)
                .where(
                    CampaignMetric.workspace_id == workspace,
                    CampaignMetric.metric_name == "conversions",
                    Campaign.source_id == product.source_id,
                )
                .limit(1)
            ).first()
            if campaigns is not None:
                return campaigns[0], campaigns[1]
    return None


def delete_source_contributions(
    db: Session,
    *,
    workspace_id: str,
    source_id: str,
) -> dict[str, int]:
    """Remove one source's node/edge contribution; other sources unaffected."""
    # Edges sourced by this source; nodes whose only source is this source.
    edges = db.execute(
        select(GraphEdge).where(
            GraphEdge.workspace_id == workspace_id, GraphEdge.source_id == source_id
        )
    ).scalars().all()
    edge_count = len(edges)
    for edge in edges:
        db.delete(edge)
    nodes = db.execute(
        select(GraphNode).where(
            GraphNode.workspace_id == workspace_id, GraphNode.source_id == source_id
        )
    ).scalars().all()
    node_count = 0
    for node in nodes:
        remaining = db.execute(
            select(GraphNode.id).where(
                GraphNode.workspace_id == workspace_id,
                GraphNode.node_type == node.node_type,
                GraphNode.entity_key == node.entity_key,
                GraphNode.source_id != source_id,
            )
        ).scalar_one_or_none()
        if remaining is None:
            db.delete(node)
            node_count += 1
    return {"nodes": node_count, "edges": edge_count}
