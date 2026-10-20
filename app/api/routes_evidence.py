"""Evidence and graph routes: every citation resolves to a permitted record."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import request_db
from app.api.routes_auth import _current_user
from app.core.tenancy import authorize_workspace, get_scoped
from app.db.models import Chunk, EvidenceRecord, GraphNode
from app.graph.evidence_paths import serialize_graph_result
from app.graph.retrieval import retrieve_graph_context

router = APIRouter(tags=["evidence"])


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: str, claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    record = get_scoped(db, EvidenceRecord, claims.workspace_id, evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return {
        "id": record.id,
        "evidence_type": record.evidence_type,
        "source": {
            "source_id": record.source_id,
            "source_version": record.source_version,
            "source_name": record.source_name,
        },
        "campaign_id": record.campaign_id,
        "metric": {
            "name": record.metric_name,
            "value": record.metric_value,
            "unit": record.metric_unit,
            "definition": record.metric_definition,
        } if record.metric_name else None,
        "date_range": {
            "start": record.date_start.isoformat() if record.date_start else None,
            "end": record.date_end.isoformat() if record.date_end else None,
        },
        "excerpt": record.excerpt,
        "locator": record.locator,
        "distinguishes": {
            "direct_observation": record.evidence_type in {"measured_fact", "feedback", "product_fact"},
            "inferred_or_derived": record.evidence_type in {"derived", "hypothesis"},
        },
    }


@router.get("/graphs/entities/{entity_id}")
def get_graph_entity(
    entity_id: str,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    node = get_scoped(db, GraphNode, claims.workspace_id, entity_id)
    if node is None:
        raise HTTPException(status_code=404, detail="graph entity not found")
    return {
        "id": node.id,
        "node_type": node.node_type,
        "label": node.label,
        "props": node.props,
        "source": {"source_id": node.source_id, "source_version": node.source_version},
    }


class GraphQueryRequest(BaseModel):
    query: str


@router.post("/graphs/paths")
def graph_paths(payload: GraphQueryRequest, claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    depth = None
    result = retrieve_graph_context(
        db, workspace_id=claims.workspace_id, query=payload.query
    )
    payload_out = serialize_graph_result(result, db=db)
    # Attach per-path serialization (depth-limited traversal happens inside).
    return payload_out


@router.get("/sources/{source_id}/chunks")
def source_chunks(
    source_id: str,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    from app.db.models import Source

    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    source = get_scoped(db, Source, claims.workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    chunks = db.execute(
        select_chunk(claims.workspace_id, source_id)
    ).scalars().all()
    return {
        "source_id": source_id,
        "source_version": source.latest_version,
        "chunks": [
            {
                "chunk_id": c.id,
                "kind": c.kind,
                "title": c.title,
                "locator": c.locator,
                "embedding_model": c.embedding_model,
            }
            for c in chunks
        ],
    }


def select_chunk(workspace_id: str, source_id: str):  # noqa: ANN201
    from sqlalchemy import select

    return select(Chunk).where(
        Chunk.workspace_id == workspace_id,
        Chunk.source_id == source_id,
    )
