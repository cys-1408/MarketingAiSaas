"""Shared API dependencies used by multiple route modules."""

from __future__ import annotations

from typing import Iterator

from sqlalchemy.orm import Session

from app.db.session import get_session_factory


def request_db() -> Iterator[Session]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
