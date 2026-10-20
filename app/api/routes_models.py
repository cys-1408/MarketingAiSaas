"""Local model connector channel routes (Ollama companion).

The connector polls outbound — no inbound ports are required and the
customer's Ollama API is never exposed publicly.  Pairing uses one-time
short-lived codes; access tokens revocable; requests are queued per workspace
so tenant isolation is enforced server-side.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes_auth import _current_user
from app.api.deps import request_db
from app.core.security import CAP_RUN_INVESTIGATIONS
from app.core.tenancy import authorize_workspace
from app.db.models import LocalConnector, ModelRequest
from app.models.adapters import safe_json_payload
from app.models.channel import (
    ChannelError,
    ConnectorChannel,
    PairingError,
    authenticate_connector,
    begin_pairing,
    complete_pairing,
    disconnect_connector,
    revoke_connector,
)

router = APIRouter(prefix="/model-connector", tags=["model-connector"])


class PairingStart(BaseModel):
    pass


class PairingComplete(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=64)
    pairing_code: str = Field(min_length=6, max_length=16)
    selected_model: str = Field(min_length=1, max_length=128)
    capabilities: dict = Field(default_factory=dict)


@router.post("/pair/start")
def start_pairing(claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_RUN_INVESTIGATIONS,
    )
    info = begin_pairing(db, user_id=claims.user_id, workspace_id=claims.workspace_id)
    db.commit()
    # The pairing code is shown exactly once and stored hashed at rest.
    return {**info, "note": "copy this code into the connector app within 15 minutes"}


@router.post("/pair/complete")
def complete_pair_call(payload: PairingComplete, db: Session = Depends(request_db)):
    try:
        result = complete_pairing(
            db,
            workspace_id=payload.workspace_id,
            pairing_code=payload.pairing_code,
            selected_model=payload.selected_model,
            capabilities=payload.capabilities,
        )
        db.commit()
    except (PairingError, ChannelError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {**result, "note": "store the access token; it is revocable at any time"}


@router.post("/requests/{request_id}/claim")
def claim_request(request_id: str, db: Session = Depends(request_db)):
    """Connector-side claim: one queued request for a paired connector."""
    raise HTTPException(status_code=501, detail="use /pair/complete first to bind this route to a tenant")


class RequestClaimBody(BaseModel):
    workspace_id: str
    access_token: str


@router.post("/heartbeat")
def heartbeat(payload: RequestClaimBody, db: Session = Depends(request_db)):
    try:
        connector = authenticate_connector(
            db, workspace_id=payload.workspace_id, access_token=payload.access_token
        )
    except (PairingError, ChannelError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    pending = db.execute(
        select(ModelRequest)
        .where(
            ModelRequest.workspace_id == payload.workspace_id,
            ModelRequest.status == "queued",
        )
        .limit(1)
    ).scalars().first()
    if pending is None:
        return {"status": "no_pending_requests"}
    pending.status = "claimed"
    pending.connector_id = connector.id
    pending.claimed_at = datetime.now(dt_timezone.utc)
    pending.attempts += 1
    db.commit()
    return {
        "request_id": pending.id,
        "model": connector.selected_model,
        "request_payload": pending.request_payload,
        "note": "responses go back through /requests/complete with the same token",
    }


class RequestCompleteBody(BaseModel):
    workspace_id: str
    access_token: str
    request_id: str
    response: dict = Field(default_factory=dict)
    error: str = ""


@router.post("/requests/complete")
def complete_request(payload: RequestCompleteBody, db: Session = Depends(request_db)):
    try:
        connector = authenticate_connector(
            db, workspace_id=payload.workspace_id, access_token=payload.access_token
        )
    except (PairingError, ChannelError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    request = db.get(ModelRequest, payload.request_id)
    if request is None or request.workspace_id != payload.workspace_id:
        raise HTTPException(status_code=404, detail="request not found for this workspace")
    if request.connector_id != connector.id:
        raise HTTPException(status_code=403, detail="request was claimed by another connector")
    if payload.error:
        request.status = "failed"
        request.error = payload.error[:400]
    else:
        prompt_content_present = bool(payload.response)
        del prompt_content_present
        request.status = "completed"
        request.response_payload = {
            "sections": payload.response,
            "latency_ms": payload.response.get("latency_ms", 0),
        }
    request.completed_at = datetime.now(dt_timezone.utc)
    db.commit()
    # Prompt/output content is never logged by default (verified by tests).
    return {"request_id": request.id, "status": request.status}


@router.get("/status")
def status(claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=2
    )
    connectors = db.execute(
        select(LocalConnector).where(
            LocalConnector.workspace_id == claims.workspace_id,
            LocalConnector.status.in_(["pending", "paired", "disconnected", "revoked"]),
        )
    ).scalars().all()
    return {
        "connectors": [
            {
                "id": c.id,
                "status": c.status,
                "selected_model": c.selected_model,
                "capabilities": c.capabilities,
                "paired_at": c.paired_at.isoformat() if c.paired_at else None,
                "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
            }
            for c in connectors
        ],
        "privacy": (
            "Local inference sends only the required prompt/context to your "
            "computer through the paired connector. Files, retrieval indexes, "
            "and analytics remain cloud-hosted in this SaaS mode; hosted "
            "fallback stays disabled unless explicitly enabled."
        ),
    }


@router.delete("/connectors/{connector_id}")
def disconnect_route(connector_id: str, claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_RUN_INVESTIGATIONS,
    )
    try:
        disconnect_connector(db, connector_id=connector_id, workspace_id=claims.workspace_id)
        db.commit()
    except ChannelError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"connector_id": connector_id, "status": "disconnected"}


@router.delete("/connectors/{connector_id}/revoke")
def revoke_route(connector_id: str, claims=Depends(_current_user), db: Session = Depends(request_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_RUN_INVESTIGATIONS,
    )
    try:
        revoke_connector(db, connector_id=connector_id, workspace_id=claims.workspace_id)
        db.commit()
    except ChannelError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"connector_id": connector_id, "status": "revoked"}
