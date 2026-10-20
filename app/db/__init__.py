"""Database layer: import-safe; engines are created lazily via session.py."""

from app.db.base import Base, new_id, utcnow  # noqa: F401
