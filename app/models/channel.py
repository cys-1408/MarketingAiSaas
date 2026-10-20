"""Local model connector channel: pairing and queued inference.

The customer's connector polls an authenticated outbound endpoint (outbound
TLS from their machine; no inbound ports, no public Ollama API).  Pairing
uses short-lived, one-time codes; access tokens are revocable.  The SaaS
queues inference requests scoped to one workspace; the connector claims and
completes them. Tenant isolation tests prove one workspace cannot receive
another workspace's requests.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.models import LocalConnector, ModelRequest
from app.models.adapters import ModelFailure, ModelReply, safe_json_payload

PAIRING_TTL_MINUTES = 15


class ChannelError(Exception):
    pass


class PairingError(ChannelError):
    pass


def _now() -> datetime:
    return datetime.now(dt_timezone.utc)


def begin_pairing(
    db: Session,
    *,
    user_id: str,
    workspace_id: str,
) -> dict[str, Any]:
    """Issue a one-time pairing code (shown once, hashed at rest)."""
    code = "".join(secrets.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(8))
    expires = _now() + timedelta(minutes=PAIRING_TTL_MINUTES)
    connector = LocalConnector(
        user_id=user_id,
        workspace_id=workspace_id,
        pairing_code_hash=hash_password(code),
        pairing_expires_at=expires,
        status="pending",
    )
    db.add(connector)
    db.flush()
    return {"connector_id": connector.id, "pairing_code": code, "expires_at": expires.isoformat()}


def complete_pairing(
    db: Session,
    *,
    workspace_id: str,
    pairing_code: str,
    selected_model: str,
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    """Connector-side pairing: one-time code -> revocable access token."""
    now = _now()
    candidates = db.execute(
        select(LocalConnector).where(
            LocalConnector.workspace_id == workspace_id,
            LocalConnector.status == "pending",
        )
    ).scalars().all()
    matched: LocalConnector | None = None
    for candidate in candidates:
        if candidate.pairing_expires_at is None or now > candidate.pairing_expires_at:
            continue
        if candidate.pairing_code_hash and verify_password(pairing_code, candidate.pairing_code_hash):
            matched = candidate
            break
    if matched is None:
        raise PairingError("invalid or expired pairing code")
    token = secrets.token_urlsafe(32)
    matched.access_token_hash = hash_password(token)
    matched.status = "paired"
    matched.selected_model = selected_model
    matched.capabilities = capabilities
    matched.pairing_code_hash = ""  # code is single-use
    matched.paired_at = now
    matched.last_seen_at = now
    db.flush()
    return {"connector_id": matched.id, "access_token": token}


def authenticate_connector(
    db: Session, *, workspace_id: str, access_token: str
) -> LocalConnector:
    connector = db.execute(
        select(LocalConnector).where(
            LocalConnector.workspace_id == workspace_id,
            LocalConnector.status == "paired",
        )
    ).scalars().all()
    for candidate in connector:
        if candidate.access_token_hash and verify_voice_factor(access_token, candidate.access_token_hash):
            candidate.last_seen_at = _now()
            return candidate
    raise PairingError("invalid connector credentials or not paired")


def verify_voice_factor(token: str, stored_hash: str) -> bool:
    """Password-style constant-time verification for connector tokens."""
    from app.core.security import verify_password

    return verify_password(token, stored_hash)


def disconnect_connector(db: Session, *, connector_id: str, workspace_id: str) -> None:
    connector = db.get(LocalConnector, connector_id)
    if connector is None or connector.workspace_id != workspace_id:
        raise ChannelError("connector not found")
    connector.status = "disconnected"
    connector.access_token_hash = ""
    connector.selected_model = ""
    connector.last_seen_at = _now()


def revoke_connector(db: Session, *, connector_id: str, workspace_id: str) -> None:
    connector = db.get(LocalConnector, connector_id)
    if connector is None or connector.workspace_id != workspace_id:
        raise ChannelError("connector not found")
    connector.status = "revoked"
    connector.access_token_hash = ""


class ConnectorChannel:
    """SaaS-side half of the outbound channel."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @property
    def adapter_name(self) -> str:
        return "ollama"

    def request_completion(
        self,
        *,
        workspace_id: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
    ) -> ModelReply:
        settings = get_settings()
        request = ModelRequest(
            workspace_id=workspace_id,
            status="queued",
            request_payload={
                "system": system_prompt,
                "prompt": user_prompt,
                "timeout_seconds": min(timeout_seconds, settings.agent_model_timeout_seconds),
            },
        )
        self.db.add(request)
        self.db.flush()
        raise LibWaitForConnector(request_id=request.id)

    def status_of(self, request_id: str, *, workspace_id: str) -> ModelRequest:
        request = self.db.get(ModelRequest, request_id)
        if request is None or request.workspace_id != workspace_id:
            raise ChannelError("inference request not found")
        return request


class LibWaitForConnector(Exception):
    """Raised to signal the caller that inference moved to the queue."""

    def __init__(self, request_id: str) -> None:
        super().__init__(request_id)
        self.request_id = request_id
