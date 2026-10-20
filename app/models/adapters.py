"""Model adapters: the provider-neutral interface and its implementations.

* :class:`MockAdapter` — deterministic evidence summarizer used in tests and
  CI so investigations always run without external services.
* :class:`OllamaAdapter` — routes inference through the customer's paired
  local connector (never directly to a public Ollama endpoint).
* :class:`HostedAdapter` — only constructed when the user explicitly opted
  in; unauthorized use raises :class:`HostedFallbackNotAuthorized`.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ModelFailure(Exception):
    pass


class HostedFallbackNotAuthorized(ModelFailure):
    pass


@dataclass(slots=True)
class ModelReply:
    status: str  # ok|abstain|error
    sections: dict[str, Any]
    model_id: str
    latency_ms: int = 0
    usage: dict[str, int] = field(default_factory=dict)


class ModelAdapter(ABC):
    name: str

    @abstractmethod
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        structured: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> ModelReply: ...

    @abstractmethod
    def health_check(self, timeout_seconds: int = 10) -> dict[str, Any]: ...


class MockAdapter(ModelAdapter):
    """Deterministic, citation-safe summarizer.

    Only restates supplied evidence, qualifies every interpretation as a
    hypothesis, and abstains when no evidence was provided — proving the
    anti-fabrication behaviors are enforced upstream of the model.
    """

    name = "mock"

    def complete(
        self,
        *, system_prompt: str, user_prompt: str,
        structured: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> ModelReply:
        evidence = (structured or {}).get("evidence", [])
        if not evidence:
            return ModelReply(
                status="abstain",
                sections={
                    "abstention_reason": "no evidence was retrieved for this question",
                },
                model_id=self.name,
            )
        observed: list[str] = []
        evidence_ids: list[str] = []
        for item in evidence:
            observed.append(item["statement"])
            evidence_ids.append(item["evidence_id"])
        hypothesis = "A causal explanation is a hypothesis until tested"
        if (structured or {}).get("hypothesis_seed"):
            hypothesis = f"{(structured or {})['hypothesis_seed']} (hypothesis, untested)"
        return ModelReply(
            status="ok",
            sections={
                "observed_facts": observed,
                "supporting_evidence": evidence_ids,
                "hypotheses": [hypothesis],
                "measurement": (
                    "Run a controlled experiment on a primary metric with "
                    "guardrails before treating a change as causal."
                ),
                "limitations": [
                    (structured or {}).get("limitations_note", "No additional limitation noted."),
                ],
            },
            model_id=self.name,
        )

    def health_check(self, timeout_seconds: int = 10) -> dict[str, Any]:
        return {"ok": True, "model": self.name}


class OllamaAdapter(ModelAdapter):
    """Customer-side local inference through the paired connector channel."""

    name = "ollama"

    def __init__(self, connector_channel) -> None:  # noqa: ANN001
        self._channel = connector_channel

    def complete(
        self,
        *, system_prompt: str, user_prompt: str,
        structured: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> ModelReply:
        return self._channel.request_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )

    def health_check(self, timeout_seconds: int = 10) -> dict[str, Any]:
        return self._channel.health_check(timeout_seconds=timeout_seconds)


class HostedAdapter(ModelAdapter):
    """Explicitly opted-in hosted inference."""

    name = "hosted"

    def __init__(self, *, provider: str, model: str, api_key: str, poll_channel) -> None:  # noqa: ANN001
        if not api_key:
            raise HostedFallbackNotAuthorized("hosted model is not configured")
        self.provider = provider
        self.model = model
        self._api_key = api_key
        self._channel = poll_channel

    def complete(
        self,
        *, system_prompt: str, user_prompt: str,
        structured: dict[str, Any] | None = None,
        timeout_seconds: int = 60,
    ) -> ModelReply:
        return self._channel.request_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )

    def health_check(self, timeout_seconds: int = 10) -> dict[str, Any]:
        return {"ok": bool(self._api_key), "model": self.name, "provider": self.provider}


def safe_json_payload(raw: str) -> dict[str, Any] | None:
    """Parse a connector/model reply into a dict or return None (never trust)."""
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None
