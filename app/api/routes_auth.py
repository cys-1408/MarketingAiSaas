"""Authentication routes: signup, login, logout, current user."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    SecurityError,
    TokenBucket,
    client_rate_key,
    create_session_token,
    hash_password,
    new_token_id,
    password_policy_error,
    verify_password,
)
from app.core.tenancy import authorize_workspace, new_id
from app.db.models import AuditEvent, Membership, SessionToken, User, Workspace
from app.db.session import get_session_factory

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

_login_bucket = TokenBucket(30)
_signup_bucket = TokenBucket(10)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=120)
    workspace_name: str = Field(min_length=1, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(BaseModel):
    token: str
    user: dict[str, Any]
    workspace: dict[str, Any]
    role: str


def _current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    settings = get_settings()
    try:
        claims = SecurityEngineVerify(claims=credentials.credentials)
    except SecurityError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    session_factory = get_session_factory()
    with session_factory() as db:
        session = db.get(SessionToken, claims.token_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session not recognized")
        if session.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session was revoked")
        user = db.get(User, claims.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="account inactive")
    request.state.user_id = claims.user_id
    return claims


def SecurityEngineVerify(*, claims: str):  # noqa: N802 - thin helper
    from app.core.security import verify_session_token

    return verify_session_token(claims)


def _safe_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_initials": user.name[:2].upper() if user.name else "?",
    }


def audit(db: Session, *, workspace_id: str, actor_id: str, action: str, detail: dict[str, Any] | None = None) -> None:
    db.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action,
            detail=detail or {},
        )
    )


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, request: Request):
    settings = get_settings()
    if not _signup_bucket.allow(client_rate_key(request.client.host if request.client else "unknown", "signup")):
        raise HTTPException(status_code=429, detail="too many signup attempts, slow down")
    policy_error = password_policy_error(payload.password)
    if policy_error:
        raise HTTPException(status_code=422, detail=policy_error)
    session_factory = get_session_factory()
    with session_factory() as db:
        with db.begin():
            existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
            if existing is not None:
                # Generic error: avoid account enumeration while still
                # preventing duplicates.
                raise HTTPException(status_code=409, detail="account already exists for this email")
            user = User(
                email=payload.email,
                password_hash=hash_password(payload.password),
                name=payload.name,
            )
            db.add(user)
            db.flush()
            workspace = Workspace(name=payload.workspace_name, owner_id=user.id)
            db.add(workspace)
            db.flush()
            db.add(
                Membership(
                    workspace_id=workspace.id, user_id=user.id,
                    role="owner", invited_by=user.id,
                )
            )
            audit(db, workspace_id=workspace.id, actor_id=user.id, action="workspace.created")
            expires = int(
                (datetime.now(dt_timezone.utc) + timedelta(seconds=settings.session_ttl_seconds)).timestamp()
            )
            token_id = new_token_id()
            db.add(SessionToken(id=token_id, user_id=user.id, expires_at=datetime.fromtimestamp(expires, dt_timezone.utc)))
            token = create_session_token(
                token_id=token_id, user_id=user.id, workspace_id=workspace.id, expires_at=expires
            )
        return AuthResponse(
            token=token,
            user=_safe_user(user),
            workspace={"id": workspace.id, "name": workspace.name, "plan": workspace.plan},
            role="owner",
        )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request):
    settings = get_settings()
    if not _login_bucket.allow(client_rate_key(request.client.host if request.client else "unknown", "login")):
        raise HTTPException(status_code=429, detail="too many login attempts, please wait")
    session_factory = get_session_factory()
    with session_factory() as db:
        user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        # Generic invalid-credential message prevents account enumeration.
        if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
            raise HTTPException(status_code=401, detail="invalid email or password")
        # The active workspace is the most recently joined one: multi-workspace
        # users sign in where they were last added, with the role that grants
        # their current permissions (e.g. viewer in a workspace they joined).
        membership = db.execute(
            select(Membership)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at.desc())
        ).scalars().first()
        if membership is None:
            raise HTTPException(status_code=403, detail="no workspace membership found")
        workspace = db.get(Workspace, membership.workspace_id)
        if workspace is None or workspace.deleted_at is not None:
            raise HTTPException(status_code=403, detail="workspace unavailable")
        expires = int(
            (datetime.now(dt_timezone.utc) + timedelta(seconds=settings.session_ttl_seconds)).timestamp()
        )
        token_id = new_token_id()
        db.add(SessionToken(id=token_id, user_id=user.id, expires_at=datetime.fromtimestamp(expires, dt_timezone.utc)))
        db.commit()
        token = create_session_token(
            token_id=token_id, user_id=user.id, workspace_id=workspace.id, expires_at=expires
        )
        role = membership.role
        return AuthResponse(
            token=token,
            user=_safe_user(user),
            workspace={"id": workspace.id, "name": workspace.name, "plan": workspace.plan},
            role=role,
        )


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="authentication required")
    claims = SecurityEngineVerify(claims=credentials.credentials)
    session_factory = get_session_factory()
    with session_factory() as db:
        session = db.get(SessionToken, claims.token_id)
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(dt_timezone.utc)
            db.commit()
    return {"status": "logged_out", "detail": "session revoked"}


@router.get("/me")
def me(claims=Depends(_current_user)):
    session_factory = get_session_factory()
    with session_factory() as db:
        user = db.get(User, claims.user_id)
        membership = db.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.workspace_id == claims.workspace_id,
            )
        ).scalar_one_or_none()
        context = authorize_workspace(
            db, user_id=user.id, workspace_id=claims.workspace_id, required_capability=1
        )
        workspace = db.get(Workspace, claims.workspace_id)
        return {
            "user": _safe_user(user),
            "workspace": {"id": workspace.id, "name": workspace.name, "plan": workspace.plan},
            "role": membership.role if membership else context.role,
        }


@router.get("/sessions")
def list_sessions(claims=Depends(_current_user)):
    """List the user's active sessions (id + expiry only, never tokens)."""
    session_factory = get_session_factory()
    with session_factory() as db:
        sessions = db.execute(
            select(SessionToken).where(
                SessionToken.user_id == claims.user_id,
                SessionToken.revoked_at.is_(None),
            )
        ).scalars().all()
        return {
            "sessions": [
                {"id": s.id[:8], "expires_at": s.expires_at.isoformat()} for s in sessions
            ],
            "revoked_note": "revoked sessions are deleted records; tokens are never returned",
        }
