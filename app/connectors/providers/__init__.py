"""Provider registry.

A provider appears as supported only when its adapter exists; a provider is
*functional* only when its server-side OAuth credentials are configured.
The UI provider list is derived from this registry's capability metadata —
never hardcoded.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from app.connectors.base import MarketingConnector

_PROVIDER_MODULES: dict[str, str] = {
    "google_analytics": "app.connectors.providers.google_analytics",
    "mailchimp": "app.connectors.providers.mailchimp",
}

_registry: dict[str, type] | None = None


def _load_registry() -> dict[str, type]:
    global _registry
    if _registry is not None:
        return _registry
    registry: dict[str, type] = {}
    for provider, module_name in _PROVIDER_MODULES.items():
        module = importlib.import_module(module_name)
        adapter_cls = getattr(module, "ADAPTER_CLASS", None)
        if adapter_cls is None:
            raise RuntimeError(f"provider module {module_name} defines no ADAPTER_CLASS")
        registry[provider] = adapter_cls
    _registry = registry
    return registry


def supported_providers() -> list[dict[str, Any]]:
    """Capability metadata for every implemented adapter."""
    registry = _load_registry()
    return [cls.capabilities.__dict__ for cls in registry.values()]
