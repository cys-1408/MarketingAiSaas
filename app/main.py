"""FastAPI application composition root.

Registers routers, middleware, exception handlers and lifespan resource
management.  Importing :mod:`app.main` does not start services; creating the
app through :func:`create_app` does not perform network calls either —
engines/adapters initialize lazily through lifespan and the get_* helpers.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, logging_context, request_id_ctx
from app.db.session import create_schema, get_engine, get_session_factory
from app.ingestion.jobs import get_worker

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    create_schema(get_engine())
    get_worker().start()
    if settings.ingest_worker_enabled:
        logger.info("ingestion worker started", extra={"mode": "thread_pool"})
    app.state.settings = settings
    try:
        yield
    finally:
        worker = get_worker()
        worker.shutdown()
        logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Multi-tenant marketing intelligence and campaign copilot: "
            "ingestion, canonical analytics, hybrid retrieval, evidence graph, "
            "and bounded agentic investigations."
        ),
        lifespan=lifespan,
    )
    _register_middleware(app, settings)
    _register_routers(app)
    _register_exception_handlers(app)
    _register_health(app)
    return app


def _register_middleware(app: FastAPI, settings) -> None:  # noqa: ANN001
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # noqa: ANN202
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            return response
        finally:
            request_id_ctx.reset(token)


def _register_routers(app: FastAPI) -> None:
    from app.api.routes_auth import router as auth_router
    from app.api.routes_campaigns import router as campaigns_router
    from app.api.routes_chat import router as chat_router
    from app.api.routes_evidence import router as evidence_router
    from app.api.routes_evaluations import router as evaluations_router
    from app.api.routes_ingestion import router as ingestion_router
    from app.api.routes_integrations import router as integrations_router
    from app.api.routes_models import router as models_router
    from app.api.routes_reports import router as reports_router
    from app.api.routes_uploads import router as uploads_router
    from app.api.routes_workspaces import router as workspaces_router

    settings = get_settings()
    prefix = settings.api_prefix
    app.include_router(auth_router, prefix=prefix)
    app.include_router(workspaces_router, prefix=prefix)
    app.include_router(uploads_router, prefix=prefix)
    app.include_router(ingestion_router, prefix=prefix)
    app.include_router(integrations_router, prefix=prefix)
    app.include_router(chat_router, prefix=prefix)
    app.include_router(campaigns_router, prefix=prefix)
    app.include_router(evidence_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(models_router, prefix=prefix)
    app.include_router(evaluations_router, prefix=prefix)


def _register_exception_handlers(app: FastAPI) -> None:
    from app.core.tenancy import AuthorizationError

    @app.exception_handler(AuthorizationError)
    async def authorization_handler(request: Request, exc: AuthorizationError):  # noqa: ANN202
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc), "error_code": "not_authorized"},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):  # noqa: ANN202
        logger.error("unhandled error", extra={"path": request.url.path},
                     exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "an internal error occurred", "error_code": "internal_error"},
        )


def _register_health(app: FastAPI) -> None:
    @app.get("/health")
    def health() -> dict:
        """Liveness: process is up; this endpoint never claims dependency health."""
        return {"status": "alive", "note": "liveness only; see /ready for dependencies"}

    @app.get("/ready")
    def ready() -> JSONResponse:
        """Readiness: reports actual dependency state (database required)."""
        settings = get_settings()
        checks: dict[str, str] = {}
        ok = True
        try:
            with get_session_factory()() as session:
                session.execute(sql_text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - truthful readiness
            checks["database"] = f"unavailable: {type(exc).__name__}"
            ok = False
        # Optional integrations: reported as configured/unconfigured, never 'connected'.
        providers = ["google_analytics", "mailchimp"]
        for provider in providers:
            client_id = getattr(settings, f"{provider}_client_id", "")
            checks[f"integration_{provider}"] = "configured" if client_id else "not_configured"
        model_status = (
            "local_connector"
            if settings.model_mode != "mock"
            else "mock_models"
        )
        checks["model_router"] = model_status
        status_code = 200 if ok else 503
        return JSONResponse(
            status_code=status_code,
            content={"status": "ready" if ok else "degraded", "checks": checks},
        )


app = create_app()
