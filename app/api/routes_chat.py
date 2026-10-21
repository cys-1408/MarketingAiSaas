"""Investigation chat: bounded LangGraph workflow behind authentication."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.workflow import InvestigationWorkflow
from app.api.deps import request_db
from app.api.routes_auth import _current_user
from app.cache import CacheValidity, SemanticCache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import TokenBucket
from app.core.tenancy import authorize_workspace, new_id
from app.db.models import (
    Conversation,
    ConversationMessage,
    Chunk,
)
from app.db.session import get_session_factory

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

_chat_bucket = TokenBucket(20)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = None


def _validity_for(workspace_id: str, role_rank: int, model_id: str) -> CacheValidity:
    session_factory = get_session_factory()
    with session_factory() as db:
        from sqlalchemy import select

        max_version = max(
            [
                (chunk.source_version or 0)
                for chunk in db.execute(
                    select(Chunk).where(Chunk.workspace_id == workspace_id)
                ).scalars().all()
            ]
            or [0]
        )
    from app.agents.prompts import PROMPT_VERSION

    return CacheValidity(
        permission_rank=role_rank,
        source_versions={"*": max_version},
        metric_definition_versions=1,
        model_id=model_id,
        prompt_version=PROMPT_VERSION,
    )


@router.post("/chat")
def chat(
    payload: ChatRequest,
    claims=Depends(_current_user),
    db: Session = Depends(request_db),
):
    settings = get_settings()
    import time as _time

    if not _chat_bucket.allow(
        f"chat:{claims.user_id}:{claims.workspace_id}", now=_time.monotonic()
    ):
        raise HTTPException(status_code=429, detail="chat rate limit reached; wait a moment")
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=claims.workspace_id, required_capability=2
    )
    # Resolve the model the same way the workflow router will, so cache
    # invalidation tracks the right model id.
    from app.models.router import ModelRouter, LocalModelUnavailable

    router = ModelRouter(db)
    try:
        adapter = router.adapter_for(workspace_id=claims.workspace_id, allow_hosted_fallback=False)
        model_id = adapter.name
    except (LocalModelUnavailable, Exception) as exc:
        del exc
        model_id = settings.model_mode

    cache = SemanticCache(db)
    validity = _validity_for(claims.workspace_id, role_rank=2, model_id=model_id)
    cached = None
    if settings.environment != "test":
        cached = cache.lookup(
            workspace_id=claims.workspace_id, question=payload.question, validity=validity
        )
    if cached is not None:
        return {"conversation_id": payload.conversation_id, "cached": True, **cached}

    started = time.perf_counter()
    workflow = InvestigationWorkflow(router=router)
    history = []
    if payload.conversation_id:
        conversation = db.get(Conversation, payload.conversation_id)
        if conversation is not None and conversation.workspace_id == claims.workspace_id:
            messages = db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == payload.conversation_id)
                .order_by(ConversationMessage.created_at)
                .limit(10)
            ).scalars().all()
            history = [{"role": m.role, "content": m.content} for m in messages]
    latency_ms = None
    try:
        result = workflow.run(
            db=db,
            workspace_id=claims.workspace_id,
            user_id=claims.user_id,
            question=payload.question,
            conversation_history=history,
        )
    except Exception as exc:
        db.rollback()
        logger.error("chat workflow failed", extra={"error": str(exc)[:200]})
        raise HTTPException(status_code=503, detail="investigation failed; please retry") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)

    if conversation_id_ref := payload.conversation_id:
        conversation = db.get(Conversation, conversation_id_ref)
    else:
        conversation_ref = Conversation(
            workspace_id=claims.workspace_id, created_by=claims.user_id
        )
        db.add(conversation_ref)
        db.flush()  # populate the server-default id before writing child rows
        conversation = conversation_ref
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            workspace_id=claims.workspace_id,
            role="user",
            content=payload.question,
        )
    )
    answer_payload = {
        "status": result.status,
        "observed_facts": result.observed_facts,
        "supporting_evidence": result.supporting_evidence,
        "contradictory_evidence": result.contradictory_evidence,
        "interpretations": result.interpretations,
        "hypotheses": result.hypotheses,
        "recommendations": result.recommendations,
        "measurement_plan": result.measurement_plan,
        "limitations": result.limitations,
        "abstention_reason": result.abstention_reason,
        "citations": result.citations,
        "model_id": result.model_id,
        "latency_ms": latency_ms,
        "ai_generated": True,
    }
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            workspace_id=claims.workspace_id,
            role="assistant",
            content=(
                " ".join(result.observed_facts)
                if result.observed_facts
                else result.abstention_reason
            ),
            structured=answer_payload,
            evidence_ids=result.supporting_evidence,
            model=result.model_id,
            latency_ms=latency_ms,
            abstention_reason=result.abstention_reason,
        )
    )
    db.commit()
    if result.status == "answered" and settings.environment != "test":
        cache.store(
            workspace_id=claims.workspace_id,
            question=payload.question,
            payload={k: v for k, v in answer_payload.items() if k != "latency_ms"},
            validity=validity,
        )
        db.commit()
    return {"conversation_id": conversation.id, "cached": False, **answer_payload}
