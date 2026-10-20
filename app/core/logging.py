"""Structured logging with secret/sensitive-content redaction.

Logs are emitted as single-line JSON so they can be parsed by any structured
log pipeline.  Correlation fields (request id, workspace, user, job, stage)
are attached through :class:`logging_context` context variables.

Redaction policy (defaults, enforced by the filter):

* authorization headers, API keys, tokens and configured secret sources are
  removed,
* prompt/completion bodies, retrieved excerpts and generated copy are dropped
  from records by default so customer source text never reaches telemetry,
* error tracebacks are preserved for actionable diagnosis.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from typing import Any

# Context variables carrying correlation info across the request/job span.
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
workspace_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "workspace_id", default=None
)
user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)
job_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "job_id", default=None
)
stage_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "stage", default=None
)

_REDACTED = "[REDACTED]"

_SECRET_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "apikey",
    "credential",
    "pairing_code",
)

# Field names whose *content* is customer-sensitive and therefore excluded
# from telemetry by default (prompt text, retrieved excerpts, generated copy).
_SENSITIVE_CONTENT_FIELDS = (
    "prompt",
    "completion",
    "excerpt",
    "generated_text",
    "chunk_text",
    "message_body",
)

_SECRET_PATTERN = re.compile(
    r"(?:Bearer\s+|sk[-_][A-Za-z0-9]{8,}|ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
)


def redact_text(text: str) -> str:
    """Replace token-like patterns inside free text with a placeholder."""
    return _SECRET_PATTERN.sub(_REDACTED, text)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _REDACTED if _SECRET_PATTERN.search(value) else value
    return value


def _redact_record(record: logging.LogRecord) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ts": record.created,
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }
    for ctx_name, ctx_var in (
        ("request_id", request_id_ctx),
        ("workspace_id", workspace_id_ctx),
        ("user_id", user_id_ctx),
        ("job_id", job_id_ctx),
        ("stage", stage_ctx),
    ):
        value = ctx_var.get()
        if value is not None:
            payload[ctx_name] = value

    extras: dict[str, Any] = {}
    for key, value in record.__dict__.items():
        if key in {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "taskName",
            "message", "asctime",
        }:
            continue
        lowered = key.lower()
        if any(part in lowered for part in _SECRET_KEY_PARTS):
            extras[key] = _REDACTED
        elif lowered in _SENSITIVE_CONTENT_FIELDS:
            continue  # sensitive content is never logged by default
        else:
            extras[key] = _redact_value(value)
    if extras:
        payload["data"] = extras
    if record.exc_info:
        payload["exception"] = _format_exception(record.exc_info)
    return payload


def _format_exception(exc_info: Any) -> str:
    import traceback

    return "".join(traceback.format_exception(*exc_info))


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = _redact_record(record)
        try:
            return json.dumps(payload, default=str, ensure_ascii=False)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return json.dumps({"message": "unserializable log record"})


class RedactionFilter(logging.Filter):
    """Defense-in-depth scrub of redactable substrings in rendered messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and _SECRET_PATTERN.search(record.msg):
            record.msg = _SECRET_PATTERN.sub(_REDACTED, record.msg)
            record.args = ()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger exactly once."""
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)
    root.setLevel(level)
    # Route uvicorn/fastapi loggers through the same pipeline.
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy).handlers = []
        logging.getLogger(noisy).propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class logging_context:  # noqa: N801 - context-manager naming
    """Attach correlation fields to every log record inside the block."""

    def __init__(
        self,
        *,
        request_id: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        job_id: str | None = None,
        stage: str | None = None,
    ) -> None:
        self._tokens: list[tuple[contextvars.ContextVar, Any]] = []
        self._values = {
            request_id_ctx: request_id,
            workspace_id_ctx: workspace_id,
            user_id_ctx: user_id,
            job_id_ctx: job_id,
            stage_ctx: stage,
        }

    def __enter__(self) -> "logging_context":
        for var, value in self._values.items():
            if value is not None:
                self._tokens.append((var, var.set(value)))
        return self

    def __exit__(self, *exc: Any) -> None:
        for var, token in self._tokens:
            var.reset(token)
