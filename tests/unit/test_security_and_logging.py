"""Unit tests: security, auth, tenant isolation, and logging redaction."""
from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, RedactionFilter, logging_context


class _CollectionHandler(logging.Handler):
    def __init__(self, records: list[dict[str, str]]):
        super().__init__()
        self.records = records

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(
            {
                "message": record.getMessage(),
                "json": self.format(record),
            }
        )


def test_json_log_redacts_tokens_and_excludes_content():
    records: list[dict[str, str]] = []
    handler = _CollectionHandler(records)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    logger = logging.getLogger("test.redaction")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        with logging_context(request_id="req-1", workspace_id="w-1", job_id="job-9"):
            logger.warning(
                "auth header Bearer abcdefghijklmno leaked",
                extra={"api_key": "sk-proj-12345678", "excerpt": "secret customer text"},
            )
    finally:
        logger.removeHandler(handler)

    assert len(records) == 1
    payload = json.loads(records[0]["json"])
    assert payload["request_id"] == "req-1"
    assert payload["workspace_id"] == "w-1"
    assert payload["job_id"] == "job-9"
    rendered = records[0]["json"]
    assert "secret customer text" not in rendered  # excerpt excluded by default
    assert "sk-proj-12345678" not in rendered  # secret key redacted via data map
    assert "abcdefghij" not in rendered  # free-text bearer token scrubbed in message
