"""Isolated test configuration.

Uses a fresh SQLite database per test session, a test session secret, and
disables the background worker so pipeline stages run synchronously and
deterministically.  Client helpers provide a pre-authenticated test tenant.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

import pytest

TEST_DB_PATH = Path("data/test_marketingai.db")
TEST_SECRET = "test-secret-0123456789abcdef"


@pytest.fixture(scope="session", autouse=True)
def _test_environment() -> Iterator[None]:
    """Force test settings before any app import touches configuration."""
    os.environ["APP_ENVIRONMENT"] = "test"
    os.environ["APP_SESSION_SECRET"] = TEST_SECRET
    os.environ["APP_INGEST_WORKER_ENABLED"] = "false"
    os.environ["APP_MODEL_MODE"] = "mock"
    os.environ["APP_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
    os.environ["APP_OBJECT_STORAGE_DIR"] = "data/test_object_storage"

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    import app.db.models  # noqa: F401 - register models on the metadata
    from app.db.base import Base
    from app.db.session import make_engine

    engine = make_engine(os.environ["APP_DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield

    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _reset_lru_caches() -> None:
    """Settings are environment-dependent; refresh between tests."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- authenticated client helpers -------------------------------------------------


@pytest.fixture(scope="session")
def api():
    """TestClient factory bound to the composition root with overridden DB."""
    from fastapi.testclient import TestClient

    from app.db.session import get_session_factory, session_scope
    from app.main import create_app

    app = create_app()
    client = TestClient(app)

    class BoundClient:
        def __init__(self) -> None:
            self._client = client
            self.token: str | None = None
            self.workspace_id: str | None = None
            self.user_id: str | None = None

        @staticmethod
        def _prefix(path: str) -> str:
            from app.core.config import get_settings

            prefix = get_settings().api_prefix
            return path if path.startswith(f"{prefix}/") else f"{prefix}/{path}"

        def request(self, method: str, path: str, **kwargs: Any):
            headers = kwargs.pop("headers", {}) or {}
            if self.token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {self.token}"
            request_id = kwargs.pop("request_id", None)
            if request_id:
                headers.setdefault("X-Request-ID", request_id)
            response = self._client.request(method, self._prefix(path), headers=headers, **kwargs)
            # Auto-track authenticated sessions returned by auth endpoints.
            try:
                body = response.json()
            except Exception:
                body = {}
            if isinstance(body, dict):
                if body.get("token") and "workspace" in body:
                    self.token = body["token"]
                    self.workspace_id = body["workspace"]["id"]
                    self.user_id = body.get("user", {}).get("id", self.user_id)
            # Self-heal: if the first requests of a session hit auth without a
            # signup having happened yet, sign up lazily and retry once.
            if (
                response.status_code == 401
                and self.token is None
                and not path.endswith("auth/signup")
                and not path.endswith("auth/login")
                and getattr(self, "_retrying_auth", False) is False
            ):
                self._retrying_auth = True
                try:
                    self.signup()
                    retry_headers = dict(headers)
                    retry_headers["Authorization"] = f"Bearer {self.token}"
                    response = self._client.request(
                        method, self._prefix(path), headers=retry_headers, **kwargs
                    )
                finally:
                    self._retrying_auth = False
            return response

        def get(self, path: str, **kwargs: Any):
            return self.request("GET", path, **kwargs)

        def post(self, path: str, **kwargs: Any):
            return self.request("POST", path, **kwargs)

        def delete(self, path: str, **kwargs: Any):
            return self.request("DELETE", path, **kwargs)

        def patch(self, path: str, **kwargs: Any):
            return self.request("PATCH", path, **kwargs)

        def signup(self, email: str = "demo@example.com", workspace: str = "Demo WS"):
            response = self.request(
                "POST",
                "auth/signup",
                json={"email": email, "password": "correct-horse-42", "name": "Demo User", "workspace_name": workspace},
            )
            assert response.status_code == 201, response.text
            payload = response.json()
            self.token = payload["token"]
            self.workspace_id = payload["workspace"]["id"]
            self.user_id = payload["user"]["id"]
            return payload

    return BoundClient()


@pytest.fixture(scope="session")
def tenant_two(api):
    """A second, unrelated tenant for isolation tests.

    Signup would normally hijack the shared client's session; the primary
    tenant's token/workspace is saved and restored so tests that use both
    tenants keep pointing at the primary workspace unless they opt in.
    """
    import time

    email = f"second-{int(time.time() * 1000)}@example.com"
    saved = (api.token, api.workspace_id, api.user_id)
    payload = api.signup(email=email, workspace="Other Tenant")
    api.token, api.workspace_id, api.user_id = saved
    return payload


@pytest.fixture()
def seeded_workspace(api):
    """A workspace with one ingested campaign-metrics source (deterministic)."""
    import io

    csv_bytes = (
        "campaign_name,date,channel,impressions,clicks,spend,purchases,revenue\n"
        "Launch Campaign,2026-09-01,Paid Social,1000,50,100,4,200\n"
        "Launch Campaign,2026-09-02,Paid Social,1100,55,105,5,220\n"
    ).encode()
    files = {"file": ("metrics.csv", io.BytesIO(csv_bytes), "text/csv")}
    response = api.request(
        "POST",
        "sources/uploads",
        files=files,
    )
    assert response.status_code == 202, response.text
    body = response.json()
    source_id = body["source_id"]
    job_id = run_ingestion_now(source_id)
    return {"source_id": source_id, "job_id": job_id}


def run_ingestion_now(source_id: str) -> str:
    """Drive the synchronous ingestion pipeline for a source; idempotent for duplicates."""
    from app.db.session import get_session_factory
    from app.db.models import IngestionJob
    from sqlalchemy import select

    factory = get_session_factory()
    with factory() as db:
        job = db.execute(
            select(IngestionJob).where(
                IngestionJob.source_id == source_id,
                IngestionJob.status == "queued",
            )
        ).scalars().first()
        if job is None:
            # Duplicate upload reused the source with no new job; the most
            # recent job already ingested these bytes.
            job = db.execute(
                select(IngestionJob)
                .where(IngestionJob.source_id == source_id)
                .order_by(IngestionJob.created_at.desc())
            ).scalars().first()
            assert job is not None, "no ingestion job for source"
            if job.status == "ready":
                return job.id  # already ingested; re-running would duplicate rows
        else:
            assert job.status == "queued", job.status
        job_id = job.id

    _execute_job(job_id)
    return job_id


def _execute_job(job_id: str) -> None:
    """Execute the workflow against the exact file bytes."""
    from pathlib import Path

    from app.core.config import get_settings
    from app.db.models import IngestionJob, Source
    from app.db.session import get_session_factory
    from app.ingestion.jobs import run_job

    factory = get_session_factory()
    with factory() as db:
        job = db.get(IngestionJob, job_id)
        source = db.get(Source, job.source_id)
        path = Path(get_settings().object_storage_dir) / source.storage_key
        data = path.read_bytes()
        run_job(db, job_id=job.id, file_bytes=data)
        db.commit()
