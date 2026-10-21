"""Application settings.

All configuration is loaded from environment variables (optionally a ``.env``
file) so that no secrets are ever hardcoded.  Setting names match the entries
documented in ``.env.example``; the optional ``APP_`` prefix keeps the
application namespaced in shared environments.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Typed application settings.

    Accessing secret-typed values intentionally does not log them; validation
    errors produced by pydantic never include the raw values.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---------------------------------------------------------
    environment: Environment = "development"
    api_prefix: str = "/api/v1"
    app_name: str = "Marketing Intelligence and Campaign Copilot"
    app_version: str = "0.1.0"

    # --- Persistence -----------------------------------------------------
    # SQLite keeps local development and tests dependency-free; production
    # should point this at PostgreSQL.
    database_url: str = "sqlite:///./data/marketingai.db"
    db_echo: bool = False
    object_storage_dir: str = "./data/object_storage"

    # --- Background work -------------------------------------------------
    # In the modular-monolith deployment a worker thread inside the API
    # process drains the job queue. Tests disable the worker and drive the
    # pipeline synchronously for determinism.
    ingest_worker_enabled: bool = True

    # --- Security --------------------------------------------------------
    session_secret: str = "change-me-in-nondev-environments"
    session_ttl_seconds: int = 8 * 60 * 60
    password_min_length: int = 10

    # --- CORS -------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Upload limits -----------------------------------------------------
    upload_max_bytes: int = 25 * 1024 * 1024
    upload_max_rows: int = 200_000
    upload_max_pages: int = 2_000
    upload_max_cells: int = 4_000_000

    # --- Attribution window for conversions (days) -------------------------
    conversion_attribution_window_days: int = 7

    # --- Model routing ------------------------------------------------------
    # ``mock`` deterministically summarizes provided evidence (tests/CI).
    # ``ollama`` routes inference through the customer's paired local
    # connector with an explicit opt-in fallback. Hosted models are only
    # used when ``allow_hosted_fallback`` is true, never silently.
    model_mode: Literal["mock", "ollama"] = "mock"
    hosted_provider: str = ""  # e.g. "openai"; requires allow_hosted_fallback
    hosted_api_key: str = ""
    hosted_model: str = ""
    # Hosted-model fallback must be explicitly opted in; default is fail-closed
    # to the customer's own local model (or an explicit unavailable error).
    allow_hosted_fallback: bool = False

    # --- Provider OAuth (each provider functional only when both set) ------
    google_analytics_client_id: str = ""
    google_analytics_client_secret: str = ""
    google_analytics_scopes: str = "https://www.googleapis.com/auth/analytics.readonly"
    mailchimp_client_id: str = ""
    mailchimp_client_secret: str = ""
    mailchimp_scopes: str = "campaigns.readonly"

    # --- Rate limits ---------------------------------------------------------
    rate_limit_per_minute: int = 120
    chat_rate_limit_per_minute: int = 20

    # --- Agent bounds ---------------------------------------------------------
    agent_max_tool_calls: int = 6
    agent_max_iterations: int = 8
    agent_model_timeout_seconds: int = 60
    graph_traversal_max_depth: int = 3
    graph_traversal_max_nodes: int = 200

    # --- Retrieval -------------------------------------------------------------
    embedding_dim: int = 256
    retrieval_top_k: int = 12
    bm25_candidates: int = 12
    vector_candidates: int = 12
    rerank_candidates: int = 8

    # --- Cache -----------------------------------------------------------------
    cache_max_payload_bytes: int = 8_000

    # --- Data -------------------------------------------------------------------
    synthetic_demo_dir: str = "./data/synthetic_demo"
    evals_dir: str = "./evals"

    @field_validator("session_secret")
    @classmethod
    def _reject_default_secret_outside_dev(cls, value: str, info) -> str:  # noqa: ANN001
        if len(value) < 16:
            raise ValueError("APP_SESSION_SECRET must be at least 16 characters")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
