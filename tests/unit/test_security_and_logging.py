"""Unit tests: security primitives and log redaction."""

from __future__ import annotations

import logging

import pytest

from app.core import security as sec
from app.core.logging import JsonFormatter, RedactionFilter, logging_context


def test_password_hash_roundtrip_and_wrong_password():
    stored = sec.hash_password("correct-horse-42")
    assert sec.verify_password("correct-horse-42", stored)
    assert not sec.verify_password("wrong", stored)
    assert "correct-horse-42" not in stored


def test_session_token_signatures_and_expiry():
    token = sec.create_session_token(
        token_id="tok123", user_id="u1", workspace_id="w1", expires_at=2_000_000_000
    )
    claims = sec.verify_session_token(token)
    assert claims.token_id == "tok123" and claims.user_id == "u1"
    expired = sec.create_session_token(
        token_id="tok4", user_id="u1", workspace_id="w1", expires_at=1
    )
    with pytest.raises(sec.SecurityError):
        sec.verify_session_token(expired)
    with pytest.raises(sec.SecurityError):
        sec.verify_session_token(token + "tampered")


def test_role_capability_ranking():
    assert sec.role_satisfies("viewer", sec.CAP_VIEW_WORKSPACE)
    assert not sec.role_satisfies("viewer", sec.CAP_INGEST)
    assert sec.role_satisfies("marketer", sec.CAP_INGEST)
    assert not sec.role_satisfies("marketer", sec.CAP_MANAGE_MEMBERS)
    assert sec.role_satisfies("administrator", sec.CAP_MANAGE_MEMBERS)
    with pytest.raises(ValueError):
        sec.role_satisfies("superuser", 1)


def test_password_policy():
    assert sec.password_policy_error("short") is not None
    assert sec.password_policy_error("correct-horse-42") is None


def test_rate_limit_blocks_after_burst():
    bucket = sec.TokenBucket(per_minute=60, burst=2)
    assert bucket.allow("k")
    assert bucket.allow("k")
    assert not bucket.allow("k")


def test_token_buckets_are_independent_per_key():
    bucket = sec.TokenBucket(per_minute=60, burst=1)
    assert bucket.allow("a")
    assert not bucket.allow("a")
    assert bucket.allow("b")


def test_json_log_redacts_tokens_and_excludes_content():
    logger = logging.getLogger("test.redaction")
    logger.setLevel(logging.DEBUG)
    records = []
    handler = _CollectionHandler(records)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    logger.addHandler(handler)
    with logging_context(request_id="req-1", workspace_id="w-1", job_id="job-9"):
        logger.warning(
            "auth header Bearer abcdefghijklmno leaked",
            extra={"api_key": "sk-proj-12345678", "excerpt": "secret customer text"},
        )
    payload = __import__("json").loads(records[0]["json"])
    assert "sk-proj-12345678" not in payload["data"]["api_key"]
    assert payload["data"]["api_key"] == "[REDACTED]"
    assert payload["request_id"] == "req-1"
    assert payload["workspace_id"] == "w-1"
    assert payload["job_id"] == "job-9"
    rendered = __import__("json").dumps(payload)
    assert "secret customer text" not in rendered  # excerpt excluded by default
    assert "abcdefghij" not in rendered  # free-text token scrubbed


class _CollectionHandler(logging.Handler):
    def __init__(self, sink: list) -> None:
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.append({"record": record, "json": self.format(record)})
