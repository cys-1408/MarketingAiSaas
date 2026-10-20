"""Typed Campaign Evidence Graph schema.

Node and edge types are fixed; validation rejects unknown types, missing
provenance and edges missing a derivation rule when labelled inferred.  The
schema explicitly encodes that graph relationships are associations — never
causal proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date

NODE_TYPES = (
    "Campaign", "Channel", "Message", "Product", "CustomerSegment",
    "FeedbackItem", "Objection", "MetricObservation", "LandingPage",
    "Experiment", "Recommendation", "EvidenceSource",
)

EDGE_TYPES = (
    "USES_CHANNEL", "TARGETS_SEGMENT", "PROMOTES_PRODUCT", "CONTAINS_MESSAGE",
    "LINKS_TO_PAGE", "FEEDBACK_MENTIONS", "EXPRESSES_OBJECTION",
    "OBSERVED_WITH_METRIC", "ASSOCIATED_WITH_CONVERSION", "TESTED_IN_EXPERIMENT",
    "SUPPORTED_BY", "CONTRADICTED_BY", "DERIVED_FROM",
)

# Legal (src type, edge type, dst type) triples.
_VALID_TRIPLES: set[tuple[str, str, str]] = {
    ("Campaign", "USES_CHANNEL", "Channel"),
    ("Campaign", "TARGETS_SEGMENT", "CustomerSegment"),
    ("Campaign", "PROMOTES_PRODUCT", "Product"),
    ("Campaign", "CONTAINS_MESSAGE", "Message"),
    ("Campaign", "LINKS_TO_PAGE", "LandingPage"),
    ("Campaign", "OBSERVED_WITH_METRIC", "MetricObservation"),
    ("Campaign", "TESTED_IN_EXPERIMENT", "Experiment"),
    ("FeedbackItem", "FEEDBACK_MENTIONS", "Product"),
    ("FeedbackItem", "EXPRESSES_OBJECTION", "Objection"),
    ("Objection", "ASSOCIATED_WITH_CONVERSION", "MetricObservation"),
    ("Recommendation", "SUPPORTED_BY", "MetricObservation"),
    ("Recommendation", "SUPPORTED_BY", "FeedbackItem"),
    ("Recommendation", "SUPPORTED_BY", "Objection"),
    ("Recommendation", "CONTRADICTED_BY", "MetricObservation"),
    ("Recommendation", "SUPPORTED_BY", "EvidenceSource"),
    ("Recommendation", "TESTED_IN_EXPERIMENT", "Experiment"),
    ("Experiment", "DERIVED_FROM", "Recommendation"),
    ("MetricObservation", "DERIVED_FROM", "EvidenceSource"),
    ("Objection", "DERIVED_FROM", "FeedbackItem"),
}

PROVENANCE_MODES = ("observed", "inferred", "derived")


class GraphSchemaError(ValueError):
    """Raised for invalid node/edge definitions."""


@dataclass(slots=True)
class NodeSpec:
    node_type: str
    entity_key: str
    label: str
    props: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EdgeSpec:
    edge_type: str
    src_key: str   # (node_type, entity_key) composite
    dst_key: str
    src_type: str = ""
    dst_type: str = ""
    provenance: str = "observed"
    rule: str = ""
    time_start: date | None = None
    time_end: date | None = None


def validate_node(spec: NodeSpec) -> NodeSpec:
    if spec.node_type not in NODE_TYPES:
        raise GraphSchemaError(f"unknown node type: {spec.node_type}")
    if not spec.entity_key.strip():
        raise GraphSchemaError("node entity_key is required")
    if not spec.label.strip():
        raise GraphSchemaError("node label is required")
    return spec


def validate_edge(spec: EdgeSpec) -> EdgeSpec:
    if spec.edge_type not in EDGE_TYPES:
        raise GraphSchemaError(f"unknown edge type: {spec.edge_type}")
    if not spec.src_type or not spec.dst_type:
        raise GraphSchemaError("edge src/dst node types are required")
    triple = (spec.src_type, spec.edge_type, spec.dst_type)
    if triple not in _VALID_TRIPLES:
        raise GraphSchemaError(
            f"edge {spec.src_type} --{spec.edge_type}--> {spec.dst_type} is not a "
            "valid schema triple"
        )
    if spec.provenance not in PROVENANCE_MODES:
        raise GraphSchemaError(
            f"edge provenance must be one of {PROVENANCE_MODES}, got {spec.provenance}"
        )
    if not spec.rule.strip():
        raise GraphSchemaError(
            "edge rule is required: describe the derivation so users can audit "
            "the relationship; a graph edge is never causal proof"
        )
    if spec.time_start and spec.time_end and spec.time_end < spec.time_start:
        raise GraphSchemaError("edge time_end precedes time_start")
    return spec
