"""Model router: local inference first; hosted only when explicitly allowed.

Never silently switches from a failed local model to a hosted one.  When the
local connector is offline/timeout/incompatible, the failure is surfaced so
the user can retry or explicitly enable the fallback.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LocalConnector
from app.models.adapters import (
    HostedAdapter,
    HostedFallbackNotAuthorized,
    ModelAdapter,
    ModelFailure,
    ModelReply,
    MockAdapter,
    OllamaAdapter,
    safe_json_payload,
)
from app.models.channel import ChannelError, ConnectorChannel


class RouterError(Exception):
    pass


class LocalModelUnavailable(RouterError):
    pass


class ModelRouter:
    """Chooses the adapter for an inference request according to policy."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def adapter_for(
        self,
        *,
        workspace_id: str,
        allow_hosted_fallback: bool | None = None,
    ) -> ModelAdapter:
        settings = get_settings()
        if settings.model_mode == "mock":
            return MockAdapter()
        connector = self.db.execute(
            LocalConnector.__table__.select().where(
                LocalConnector.workspace_id == workspace_id,
                LocalConnector.status == "paired",
                LocalConnector.selected_model != "",
            )
        ).first()
        if connector is not None:
            return OllamaAdapter(ConnectorChannel(self.db))
        if settings.allow_hosted_fallback and (
            allow_hosted_fallback is None or allow_hosted_fallback
        ):
            if not (settings.hosted_api_key and settings.hosted_model and settings.hosted_provider):
                raise HostedFallbackNotAuthorized(
                    "hosted fallback is enabled but the provider is not configured"
                )
            return HostedAdapter(
                provider=settings.hosted_provider,
                model=settings.hosted_model,
                api_key=settings.hosted_api_key,
                poll_channel=ConnectorChannel(self.db),
            )
        raise LocalModelUnavailable(
            "no local model connector is paired for this workspace; pair a "
            "computer with the local connector, or explicitly enable hosted "
            "fallback in settings (off by default)"
        )

    def complete(
        self,
        *,
        workspace_id: str,
        system_prompt: str,
        user_prompt: str,
        structured: dict[str, Any] | None = None,
        allow_hosted_fallback: bool | None = None,
        timeout_seconds: int | None = None,
    ) -> ModelReply:
        settings = get_settings()
        adapter = self.adapter_for(
            workspace_id=workspace_id, allow_hosted_fallback=allow_hosted_fallback
        )
        return adapter.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            structured=structured,
            timeout_seconds=timeout_seconds or settings.agent_model_timeout_seconds,
        )
