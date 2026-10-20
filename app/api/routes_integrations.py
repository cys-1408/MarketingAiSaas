"""Integrations: provider registry, OAuth, sync, status, disconnect."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes_auth import _current_user
from app.connectors.oauth import (
    EncryptedCredentialStore,
    OAuthError,
    exchange_code,
    start_authorization,
    validate_callback_state,
)
from app.connectors.providers import supported_providers
from app.connectors.sync import SyncExecutor
from app.core.config import get_settings
from app.core.security import CAP_MANAGE_INTEGRATIONS
from app.core.tenancy import authorize_workspace, get_scoped
from app.db.models import IntegrationConnection, SyncRun
from app.db.session import get_session_factory

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _db():  # noqa: ANN201
    session_factory = get_session_factory()
    yield session_factory()


@router.get("")
def list_providers(claims=Depends(_current_user), db: Session = Depends(_db)):
    """Capability metadata + per-workspace connection state (real states)."""
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    settings = get_settings()
    connections = db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == claims.workspace_id
        )
    ).scalars().all()
    by_provider = {c.provider: c for c in connections if c.disconnected_at is None}
    providers = []
    for meta in supported_providers():
        cxn = by_provider.get(meta["provider"])
        configured = bool(getattr(settings, f"{meta['provider']}_client_id", ""))
        state = "not_connected"
        last_sync = None
        if cxn is not None:
            if cxn.status == "connected":
                state = "connected"
            elif cxn.status in {"pending"}:
                state = "authorization_pending"
            else:
                state = cxn.status
            last_sync = cxn.last_synced_at.isoformat() if cxn.last_synced_at else None
        providers.append(
            {
                **meta,
                "server_configured": configured,
                "workspace_status": state,
                "last_synced_at": last_sync,
            }
        )
    return {"providers": providers}


class ConnectRequest(BaseModel):
    redirect_uri: str = ""


@router.post("/{provider}/connect")
def connect(
    provider: str,
    payload: ConnectRequest,
    request: Request,
    claims=Depends(_current_user),
    db: Session = Depends(_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_MANAGE_INTEGRATIONS,
    )
    settings = get_settings()
    client_id = getattr(settings, f"{provider}_client_id", "")
    if not client_id:
        raise HTTPException(
            status_code=409,
            detail=f"{provider} is not configured on this server: add its OAuth client "
            "credentials to the environment to enable connection",
        )
    base_url = str(request.base_url).rstrip("/")
    try:
        connection, url = start_authorization(
            db,
            workspace_id=claims.workspace_id,
            provider=provider,
            client_id=client_id,
            redirect_uri=payload.redirect_uri,
            base_url=base_url,
        )
        db.commit()
    except OAuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"authorize_url": url, "connection_id": connection.id}


@router.get("/{provider}/callback")
def callback(provider: str, code: str, state: str, db: Session = Depends(_db)):
    settings = get_settings()
    connections = db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.provider == provider,
            IntegrationConnection.status == "pending",
        )
    ).scalars().all()
    if not connections:
        raise HTTPException(status_code=404, detail="no pending authorization for this provider")
    scopes = getattr(settings, f"{provider}_scopes", "")
    store = EncryptedCredentialStore(settings.session_secret)
    for connection in connections:
        try:
            validate_callback_state(connection, state=state)
        except OAuthError:
            continue  # one pending connection owns this state; others keep trying
        tokens = exchange_code(
            provider=provider,
            authorization_code=code,
            redirect_uri="",  # the configured redirect is implicit
            code_verifier=connection.oauth_code_verifier,
        )
        from app.connectors.oauth import store_credentials

        store_credentials(connection, tokens=tokens, store=store)
        connection.scopes = [s for s in scopes.split() if s]
        db.commit()
        return {"connection_id": connection.id, "status": "connected"}
    raise HTTPException(status_code=400, detail="OAuth state mismatch; restart authorization")


@router.post("/{connection_id}/sync")
def sync(
    connection_id: str,
    claims=Depends(_current_user),
    db: Session = Depends(_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_MANAGE_INTEGRATIONS,
    )
    connection = get_scoped(db, IntegrationConnection, claims.workspace_id, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="connection not found")
    if connection.status != "connected":
        raise HTTPException(
            status_code=409,
            detail=f"connection is '{connection.status}'; it must be connected and validated "
            "before sync can run",
        )
    from app.connectors.providers import _load_registry

    registry = _load_registry()
    adapter_cls = registry.get(connection.provider)
    if adapter_cls is None:
        raise HTTPException(status_code=409, detail=f"provider '{connection.provider}' has no adapter")
    store = EncryptedCredentialStore(get_settings().session_secret)
    credentials = store.decrypt(connection.credentials_encrypted)
    connector = adapter_cls(credentials)
    try:
        connector.connect()
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=f"connection validation failed: {exc}",
        ) from exc
    mode = "incremental" if connection.cursor and connection.last_synced_at else "initial"
    executor = SyncExecutor(db, connector)
    run = executor.run(
        connection,
        mode=mode,
        resource=connector.capabilities.supported_objects[0],
        workspace_id=claims.workspace_id,
        user_id=claims.user_id,
    )
    db.commit()
    return {
        "sync_id": run.id,
        "mode": mode,
        "status": run.status,
        "records_imported": run.records_imported,
        "pages_fetched": run.pages_fetched,
        "warnings": run.warnings,
    }


@router.get("/{connection_id}/status")
def status(connection_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=1
    )
    connection = get_scoped(db, IntegrationConnection, claims.workspace_id, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="connection not found")
    runs = db.execute(
        select(SyncRun)
        .where(SyncRun.connection_id == connection_id)
        .order_by(SyncRun.started_at.desc())
        .limit(10)
    ).scalars().all()
    return {
        "connection_id": connection.id,
        "provider": connection.provider,
        "status": connection.status,
        "last_synced_at": connection.last_synced_at.isoformat() if connection.last_synced_at else None,
        "cursor": connection.cursor,
        "last_error": connection.last_error or None,
        "recent_runs": [
            {
                "id": r.id,
                "mode": r.mode,
                "status": r.status,
                "records": r.records_imported,
                "pages": r.pages_fetched,
                "started_at": r.started_at.isoformat(),
            }
            for r in runs
        ],
    }


@router.delete("/{connection_id}")
def disconnect(connection_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id,
        required_capability=CAP_MANAGE_INTEGRATIONS,
    )
    from app.connectors.oauth import revoke_connection
    from app.connectors.providers import _load_registry
    from app.connectors.base import ProviderNotConfigured

    connection = get_scoped(db, IntegrationConnection, claims.workspace_id, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="connection not found")
    provider_revoke = None
    store = EncryptedCredentialStore(get_settings().session_secret)
    try:
        credentials = store.decrypt(connection.credentials_encrypted)
        registry = _load_registry()
        adapter_cls = registry.get(connection.provider)
        if adapter_cls is not None:
            connector = adapter_cls(credentials)
            connector.disconnect()
            provider_revoke = f"{connection.provider}"  # adapter handles revocation
            del adapter_cls
    except (OAuthError, ProviderNotConfigured):
        # Local disconnect still completes; provider revocation is best-effort.
        pass
    revoked = revoke_connection(connection, provider_token_revoke_url=provider_revoke)
    connection.credentials_encrypted = {}
    connection.status = "disconnected"
    db.add(
        __import__("app.db.models", fromlist=["AuditEvent"]).AuditEvent(
            workspace_id=claims.workspace_id,
            actor_id=claims.user_id,
            action="integration.disconnected",
            detail={"provider": connection.provider, "provider_revoked": bool(revoked)},
        )
    )
    db.commit()
    return {"connection_id": connection.id, "status": "disconnected"}
