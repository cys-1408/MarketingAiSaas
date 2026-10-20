"""Authentication primitives: password hashing, session tokens, permissions.

Passwords are hashed with memory-hard ``scrypt`` via :mod:`hashlib` (actively
maintained, part of the Python standard library).  Sessions are opaque,
HMAC-signed bearer tokens; only IDs are persisted so a database leak never
exposes usable credentials, and sessions can be revoked server-side.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from app.core.config import get_settings


class SecurityError(Exception):
    """Raised when credential material fails verification."""


# --- Password hashing --------------------------------------------------------

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    """Return a salted scrypt hash in PHC-style ``scrypt$n$r$p$salt$hash`` form."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return "$".join(
        [
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            salt.hex(),
            digest.hex(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    try:
        algo, n, r, p, salt_hex, digest_hex = stored.split("$")
        if algo != "scrypt" or len(salt_hex) != 32:
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, bytes.fromhex(digest_hex))


def password_policy_error(password: str) -> str | None:
    """Return a human-readable policy violation, or None when acceptable."""
    settings = get_settings()
    if len(password) < settings.password_min_length:
        return f"Password must be at least {settings.password_min_length} characters"
    if password.lower() in {"password", "password1", "qwertyuiop1", "passw0rd12345"}:
        return "Password must not be a well-known value"
    return None


# --- Session tokens -----------------------------------------------------------


def _sign(payload: bytes) -> str:
    settings = get_settings()
    return hmac.new(
        settings.session_secret.encode(), payload, hashlib.sha256
    ).hexdigest()


_TOKEN_SEPARATOR = "........"


@dataclass(frozen=True, slots=True)
class SessionClaims:
    token_id: str
    user_id: str
    workspace_id: str
    expires_at: int


def create_session_token(
    *,
    token_id: str,
    user_id: str,
    workspace_id: str,
    expires_at: int,
) -> str:
    """Create a signed, expiring session token string.

    Format: ``<token_id>.<user_id>.<workspace_id>.<expires_at>........<sig>``.
    The signature is HMAC-SHA256 of the body with the server secret.
    """
    body = f"{token_id}.{user_id}.{workspace_id}.{expires_at}"
    return f"{body}{_TOKEN_SEPARATOR}{_sign(body.encode())}"


def verify_session_token(token: str) -> SessionClaims:
    """Validate signature and expiry, raising :class:`SecurityError` on failure."""
    try:
        body, signature = token.rsplit(_TOKEN_SEPARATOR, 1)
        token_id, user_id, workspace_id, expires_raw = body.split(".")
    except ValueError as exc:
        raise SecurityError("malformed session token") from exc
    expected = _sign(body.encode())
    if not hmac.compare_digest(signature, expected):
        raise SecurityError("invalid session signature")
    expires_at = int(expires_raw)
    if time.time() > expires_at:
        raise SecurityError("session expired")
    return SessionClaims(
        token_id=token_id,
        user_id=user_id,
        workspace_id=workspace_id,
        expires_at=expires_at,
    )


def new_token_id() -> str:
    return secrets.token_urlsafe(16)


# --- Roles and capabilities ------------------------------------------------------

ROLE_OWNER = "owner"
ROLE_ADMIN = "administrator"
ROLE_ANALYST = "analyst"
ROLE_MARKETER = "marketer"
ROLE_REVIEWER = "reviewer"
ROLE_VIEWER = "viewer"

ROLE_RANK: dict[str, int] = {
    ROLE_OWNER: 6,
    ROLE_ADMIN: 5,
    ROLE_ANALYST: 4,
    ROLE_MARKETER: 3,
    ROLE_REVIEWER: 2,
    ROLE_VIEWER: 1,
}
VALID_ROLES = frozenset(ROLE_RANK)

# Capabilities a member may exercise, expressed as a minimum role rank.
CAP_VIEW_WORKSPACE = 1
CAP_RUN_INVESTIGATIONS = 2
CAP_INGEST = 2
CAP_EDIT_MAPPINGS = 2
CAP_GENERATE_REPORTS = 2
CAP_DELETE_SOURCES = 4
CAP_MANAGE_INTEGRATIONS = 5
CAP_MANAGE_MEMBERS = 5


def role_satisfies(role: str, capability_rank: int) -> bool:
    """Return whether ``role`` grants a capability of the given minimal rank."""
    rank = ROLE_RANK.get(role)
    if rank is None:
        raise ValueError(f"unknown role: {role}")
    return rank >= capability_rank


# --- Rate limiting ---------------------------------------------------------------


class TokenBucket:
    """In-process token bucket keyed by client identity.

    Used for login, upload and chat rate limits.  In a multi-process
    deployment this is fronted by Redis (documented in README); the
    interface stays identical.
    """

    def __init__(self, per_minute: int, burst: int | None = None) -> None:
        self.rate = per_minute / 60.0
        self.burst = burst or per_minute
        self._buckets: dict[str, tuple[float, float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        tokens, last = self._buckets.get(key, (float(self.burst), now))
        elapsed = max(0.0, now - last)
        tokens = min(float(self.burst), tokens + elapsed * self.rate)
        if tokens < 1.0:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - 1.0, now)
        return True


def client_rate_key(remote_addr: str, principal: str) -> str:
    """Composite rate-limit key: principal scope plus client address."""
    return f"{principal}:{remote_addr}"


# --- Safe errors -----------------------------------------------------------------


def safe_error_detail(exc: Exception) -> str:
    """Produce an error string that cannot leak secrets or raw internals."""
    text = str(exc)
    lowered = text.lower()
    if any(word in lowered for word in ("password", "secret", "token", "api_key")):
        return "an internal error occurred"
    return text if 0 < len(text) < 300 else "an internal error occurred"


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())
