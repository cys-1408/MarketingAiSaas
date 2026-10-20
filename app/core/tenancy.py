"""Authoritative workspace/tenant resolution and authorization.

Every protected service call funnels through :func:`authorize_workspace`,
which verifies that the authenticated user is an active member of the
requested workspace and holds sufficient role rank for the attempted action.
Query scoping helpers guarantee tenant filters are applied to relational
lookups from one tested implementation instead of ad-hoc ``where`` clauses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security as sec
from app.db.models import Membership, Workspace


class AuthorizationError(Exception):
    """Raised when a user is not authorized for the requested workspace/action."""

    def __init__(self, detail: str = "not authorized", status_code: int = 403) -> None:
        super().__init__(detail)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Resolved authorization context for one request/job step."""

    user_id: str
    workspace_id: str
    role: str

    def can(self, capability_rank: int) -> bool:
        return sec.role_satisfies(self.role, capability_rank)

    def require(self, capability_rank: int) -> "WorkspaceContext":
        if not self.can(capability_rank):
            raise AuthorizationError("insufficient role for this action")
        return self


def authorize_workspace(
    db: Session,
    *,
    user_id: str,
    workspace_id: str,
    required_capability: int = sec.CAP_VIEW_WORKSPACE,
) -> WorkspaceContext:
    """Verify membership + role and return the authorized context.

    Raises :class:`AuthorizationError` when the user is not an active member
    of ``workspace_id`` with sufficient rank.  Never trust a client-supplied
    role: it is read from the persisted membership.
    """
    workspace = db.get(Workspace, workspace_id)
    if workspace is None or workspace.deleted_at is not None:
        raise AuthorizationError("workspace not found", status_code=404)
    membership = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AuthorizationError("not a member of this workspace", status_code=403)
    if not sec.role_satisfies(membership.role, required_capability):
        raise AuthorizationError("insufficient role for this action", status_code=403)
    return WorkspaceContext(
        user_id=user_id, workspace_id=workspace_id, role=membership.role
    )


def authorize_workspace_or_fail(
    db: Session,
    *,
    user_id: str,
    workspace_id: str,
    required_capability: int = sec.CAP_VIEW_WORKSPACE,
) -> WorkspaceContext:
    """Alias kept for call-site readability; identical to authorize_workspace."""
    return authorize_workspace(
        db,
        user_id=user_id,
        workspace_id=workspace_id,
        required_capability=required_capability,
    )


# --- Scoped query helpers -------------------------------------------------------


def tenant_where(model: Any, workspace_id: str):  # noqa: ANN201 - conditions
    """Return the tenant filter condition for a tenant-scoped model."""
    column = getattr(model, "workspace_id", None)
    if column is None:  # pragma: no cover - programming error
        raise TypeError(f"{model.__name__} is not tenant-scoped")
    return column == workspace_id


def tenant_query(db: Session, model: Any, workspace_id: str):  # noqa: ANN201
    """Pre-filtered selectable for tenant-scoped models."""
    return select(model).where(tenant_where(model, workspace_id))


def get_scoped(db: Session, model: Any, workspace_id: str, record_id: str) -> Any:
    """Fetch by id with tenant scoping; returns None when not found/foreign.

    Used by every per-record endpoint so a cross-tenant identifier behaves
    exactly like a missing one.
    """
    record = db.get(model, record_id)
    if record is None:
        return None
    if getattr(record, "workspace_id", None) != workspace_id:
        return None
    return record


def assert_scoped(record: Any, workspace_id: str) -> Any:
    """Raise AuthorizationError when a loaded record belongs to another tenant."""
    if record is None:
        raise AuthorizationError("record not found", status_code=404)
    if getattr(record, "workspace_id", None) != workspace_id:
        raise AuthorizationError("record not found", status_code=404)
    return record


def new_id(prefix: str) -> str:
    """Stable-format opaque id (prefix + uuid4)."""
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:20]}"


# --- Background job context ---------------------------------------------------------

@dataclass(frozen=True, slots=True)
class JobContext:
    """Explicit tenant context carried through background jobs."""

    workspace_id: str
    user_id: str

    def recheck(self, db: Session, capability: int) -> WorkspaceContext:
        """Re-verify authorization in the worker before touching tenant data."""
        return authorize_workspace(
            db,
            user_id=self.user_id,
            workspace_id=self.workspace_id,
            required_capability=capability,
        )
