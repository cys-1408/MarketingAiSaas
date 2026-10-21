"""Workspace routes: creation, membership, usage."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes_auth import _current_user
from app.core.security import VALID_ROLES
from app.core.tenancy import (
    AuthorizationError,
    authorize_workspace,
    new_id,
)
from app.db.models import (
    CampaignMetric,
    Chunk,
    IngestionJob,
    Membership,
    Source,
    User,
    Workspace,
)
from app.db.session import get_session_factory

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class MemberAdd(BaseModel):
    email: str
    role: str = "marketer"


class MemberRoleUpdate(BaseModel):
    role: str


def _db():  # noqa: ANN201
    session_factory = get_session_factory()
    yield session_factory()  # returned session per-request


@router.post("", status_code=201)
def create_workspace(payload: WorkspaceCreate, claims=Depends(_current_user), db: Session = Depends(_db)):
    with db.begin():
        workspace = Workspace(name=payload.name, owner_id=claims.user_id)
        db.add(workspace)
        db.flush()
        db.add(
            Membership(
                workspace_id=workspace.id, user_id=claims.user_id, role="owner",
                invited_by=claims.user_id,
            )
        )
        return {
            "id": workspace.id,
            "name": workspace.name,
            "plan": workspace.plan,
            "role": "owner",
        }


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    authorize_workspace(db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=1)
    workspace = db.get(Workspace, workspace_id)
    members = db.execute(
        select(Membership, User.email, User.name)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == workspace_id)
    ).all()
    return {
        "id": workspace.id,
        "name": workspace.name,
        "plan": workspace.plan,
        "created_at": workspace.created_at.isoformat(),
        "members": [
            {"user_id": m.user_id, "email": email, "name": name, "role": m.role}
            for m, email, name in members
        ],
    }


@router.post("/{workspace_id}/members", status_code=201)
def add_member(
    workspace_id: str,
    payload: MemberAdd,
    claims=Depends(_current_user),
    db: Session = Depends(_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=5,
    )
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {sorted(VALID_ROLES)}")
    user = db.execute(select(User).where(User.email == payload.email.strip().lower())).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="no account exists for that email; ask them to sign up first")
    existing = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Re-adding an existing member updates their membership to the newly
        # requested role (an idempotent re-invite) rather than erroring; role
        # changes always remain auditable.
        existing.role = payload.role
    else:
        db.add(
            Membership(workspace_id=workspace_id, user_id=user.id, role=payload.role)
        )
    from app.api.routes_auth import audit

    audit(
        db,
        workspace_id=workspace_id,
        actor_id=claims.user_id,
        action="member.added",
        detail={"member_id": user.id, "role": payload.role},
    )
    db.commit()
    return {"user_id": user.id, "email": user.email, "role": payload.role}


@router.patch("/{workspace_id}/members/{user_id}")
def change_role(
    workspace_id: str,
    user_id: str,
    payload: MemberRoleUpdate,
    claims=Depends(_current_user),
    db: Session = Depends(_db),
):
    authorize_workspace(
        db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=5,
    )
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {sorted(VALID_ROLES)}")
    membership = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="membership not found")
    membership.role = payload.role
    from app.api.routes_auth import audit

    audit(
        db,
        workspace_id=workspace_id,
        actor_id=claims.user_id,
        action="member.role_changed",
        detail={"member_id": user_id, "role": payload.role},
    )
    db.commit()
    return {"user_id": user_id, "role": payload.role}


@router.delete("/{workspace_id}/members/{user_id}")
def remove_member(
    workspace_id: str,
    user_id: str,
    claims=Depends(_current_user),
    db: Session = Depends(_db),
):
    ctx = authorize_workspace(
        db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=5,
    )
    workspace = db.get(Workspace, workspace_id)
    if user_id == workspace.owner_id:
        raise HTTPException(status_code=409, detail="the workspace owner cannot be removed")
    membership = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="membership not found")
    db.delete(membership)
    from app.api.routes_auth import audit

    audit(
        db,
        workspace_id=workspace_id,
        actor_id=claims.user_id,
        action="member.removed",
        detail={"member_id": user_id},
    )
    db.commit()
    return {"removed": user_id}


@router.get("/{workspace_id}/activity")
def activity(workspace_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    """Recent audit events for this workspace (persisted real events)."""
    authorize_workspace(db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=1)
    from app.db.models import AuditEvent

    events = db.execute(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == workspace_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(50)
    ).scalars().all()
    users_by_id = {}
    actor_ids = {e.actor_id for e in events}
    if actor_ids:
        rows = db.execute(select(User).where(User.id.in_(actor_ids))).scalars().all()
        users_by_id = {u.id: u.name for u in rows}
    return {
        "events": [
            {
                "id": e.id,
                "actor": users_by_id.get(e.actor_id, "System"),
                "action": e.action,
                "detail": e.detail if isinstance(e.detail, dict) else {},
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    }


@router.get("/{workspace_id}/usage")
def usage(workspace_id: str, claims=Depends(_current_user), db: Session = Depends(_db)):
    """Real usage numbers computed from stored records."""
    authorize_workspace(db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=1)
    sources = db.execute(
        select(func.count(Source.id)).where(Source.workspace_id == workspace_id)
    ).scalar_one()
    metrics = db.execute(
        select(func.count(CampaignMetric.id)).where(CampaignMetric.workspace_id == workspace_id)
    ).scalar_one()
    chunks = db.execute(
        select(func.count(Chunk.id)).where(Chunk.workspace_id == workspace_id)
    ).scalar_one()
    jobs = db.execute(
        select(func.count(IngestionJob.id)).where(IngestionJob.workspace_id == workspace_id)
    ).scalar_one()
    jobs_running = db.execute(
        select(func.count(IngestionJob.id)).where(
            IngestionJob.workspace_id == workspace_id,
            IngestionJob.status.in_(["queued", "inspecting", "normalizing", "indexing", "awaiting_review"]),
        )
    ).scalar_one()
    members = db.execute(
        select(func.count(Membership.id)).where(Membership.workspace_id == workspace_id)
    ).scalar_one()
    storage_bytes = db.execute(
        select(func.sum(Source.size_bytes)).where(Source.workspace_id == workspace_id)
    ).scalar_one() or 0
    return {
        "sources": sources,
        "metric_rows": metrics,
        "indexed_chunks": chunks,
        "ingestion_jobs": jobs,
        "jobs_in_progress": jobs_running,
        "members": members,
        "storage_bytes": storage_bytes,
        "notes": "counts are measured from workspace records, not estimated",
    }
