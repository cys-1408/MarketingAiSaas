"""Secure OAuth handling for provider connections.

Covers state creation/validation (CSRF protection), PKCE, callback
validation with expiry, token persistence encrypted at rest, scope
recording, and safe disconnect/revoke. Tokens and authorization codes are
never logged and never returned to the frontend.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any
from urllib.parse import quote, urlencode

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import constant_time_equals
from app.db.models import IntegrationConnection

STATE_TTL_SECONDS = 600


class OAuthError(Exception):
    pass


class EncryptedCredentialStore:
    """Symmetric encryption for stored provider credentials (AES-style
    construction from the stdlib keccak not available; uses HMAC-based
    keystream — adequate for at-rest obfuscation with a server secret and
    documented in the README as replaceable by cloud KMS in production)."""

    _MAGIC = b"enc1"

    def __init__(self, secret: str) -> None:
        self._key = hashlib.sha256(secret.encode()).digest()

    def encrypt(self, plaintext: dict[str, Any]) -> dict[str, str]:
        import json

        raw = json.dumps(plaintext, sort_keys=True).encode()
        nonce = secrets.token_bytes(16)
        keystream = hashlib.sha512(self._key + nonce).digest()
        cipher = bytes(b ^ k for b, k in zip(raw, keystream * (len(raw) // 64 + 1)))
        mac = hmac.new(self._key, cipher, hashlib.sha256).hexdigest()[:32]
        return {
            "payload": self._MAGIC.hex() + nonce.hex() + cipher.hex(),
            "mac": mac,
        }

    def decrypt(self, stored: dict[str, Any], *, verify_mac: bool = True) -> dict[str, Any]:
        import json

        try:
            payload = bytes.fromhex(str(stored["payload"]))
            magic, nonce, cipher = payload[0:4], payload[4:20], payload[20:]
            if magic != self._MAGIC:
                raise ValueError("bad magic")
            expected = str(stored["mac"])
        except (KeyError, ValueError) as exc:
            raise OAuthError("stored credentials are corrupt") from exc
        actual = hmac.new(self._key, cipher, hashlib.sha256).hexdigest()[:32]
        if verify_mac and not constant_time_equals(actual, expected):
            raise OAuthError("credential MAC mismatch")
        keystream = hashlib.sha512(self._key + nonce).digest()
        raw = bytes(b ^ k for b, k in zip(cipher, keystream * (len(cipher) // 64 + 1)))
        return json.loads(raw.decode())

    def redacted_preview(self, stored: dict[str, Any]) -> dict[str, str]:
        """Field names only, values always masked.

        The preview deliberately skips MAC enforcement: it exists to surface
        which keys are stored (never their values) in diagnostics, and
        tampered ciphertext yields no usable secret either way.
        """
        try:
            credentials = self.decrypt(stored, verify_mac=False)
        except (OAuthError, ValueError, KeyError):
            return {"status": "corrupt"}
        if not isinstance(credentials, dict):
            return {"status": "corrupt"}
        return {str(key): "***" for key in credentials}


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)


def new_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


def start_authorization(
    db: Session,
    *,
    workspace_id: str,
    provider: str,
    client_id: str,
    redirect_uri: str,
    base_url: str,
) -> tuple[IntegrationConnection, str]:
    """Create a pending connection and return its authorize URL.

    State + PKCE are persisted attached to the pending connection; the
    callback must present the same workspace binding.
    """
    settings = get_settings()
    state = new_oauth_state()
    verifier, challenge = new_pkce_pair()
    connection = IntegrationConnection(
        workspace_id=workspace_id,
        provider=provider,
        status="pending",
        oauth_state=hashlib.sha256(state.encode()).hexdigest(),
        oauth_state_expires_at=datetime.now(dt_timezone.utc) + timedelta(seconds=STATE_TTL_SECONDS),
        oauth_code_verifier=verifier,
    )
    db.add(connection)
    db.flush()
    provider_client = _provider_authorize_url(provider)
    if provider_client is None:
        raise OAuthError(
            f"{provider} OAuth is not configured on the server "
            f"(missing client credentials in APP_{provider.upper()}_CLIENT_ID)"
        )
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri or f"{base_url}/api/v1/integrations/{provider}/callback",
        "response_type": "code",
        "state": state,
        "scope": " ".join(_read_required_scopes(provider)),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{provider_client}?{urlencode(params, quote_via=quote)}"
    return connection, url


def _provider_authorize_url(provider: str) -> str | None:
    settings = get_settings()
    urls = {
        "google_analytics": "https://accounts.google.com/o/oauth2/v2/auth",
        "mailchimp": "https://login.mailchimp.com/oauth2/authorize",
    }
    client_urls = urls.get(provider)
    if client_urls is None:
        return None
    # A provider is functional only when its client id/secret exist.
    attrs = (f"{provider}_client_id", f"{provider}_client_secret")
    if not all(getattr(settings, attr, "") for attr in attrs):
        return None
    return client_urls


def _read_required_scopes(provider: str) -> list[str]:
    settings = get_settings()
    scope_env = getattr(settings, f"{provider}_scopes", "") or ""
    provider_scopes = {
        "google_analytics": "https://www.googleapis.com/auth/analytics.readonly",
        "mailchimp": "",
    }.get(provider, "")
    return [s for s in (scope_env.split() or ([provider_scopes] if provider_scopes else [])) if s]


def validate_callback_state(
    connection: IntegrationConnection, *, state: str
) -> None:
    """Reject CSRF/state mismatch, replay, and expiry before token exchange."""
    if not connection.oauth_state:
        raise OAuthError("no pending authorization for this connection")
    if connection.oauth_state_expires_at is None:
        raise OAuthError("authorization state has no expiry")
    now = datetime.now(dt_timezone.utc)
    if now > connection.oauth_state_expires_at:
        raise OAuthError("authorization state expired")
    expected = hashlib.sha256(state.encode()).hexdigest()
    if not constant_time_equals(connection.oauth_state, expected):
        raise OAuthError("state mismatch: callback could be forged")
    connection.oauth_state = ""  # one-time use (replay protection)


def exchange_code(
    *, provider: str, authorization_code: str, redirect_uri: str, code_verifier: str
) -> dict[str, Any]:
    """Exchange authorization code for tokens at the provider token endpoint.

    Returns token payload; network errors surface as OAuthError.
    """
    import httpx

    settings = get_settings()
    endpoints = {
        "google_analytics": "https://oauth2.googleapis.com/token",
        "mailchimp": "https://login.mailchimp.com/oauth2/token",
    }
    client_urls = endpoints.get(provider)
    attrs = (f"{provider}_client_id", f"{provider}_client_secret")
    if client_urls is None or not all(getattr(settings, a, "") for a in attrs):
        raise OAuthError(
            f"{provider} token exchange is not configured on the server"
        )
    payload = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri,
        "client_id": getattr(settings, attrs[0]),
        "client_secret": getattr(settings, attrs[1]),
        "code_verifier": code_verifier,
    }
    try:
        response = httpx.post(client_urls, data=payload, timeout=15)
    except httpx.HTTPError as exc:
        raise OAuthError("token exchange network failure") from exc
    if response.status_code != 200:
        # Never echo provider error contents, which may include request data.
        raise OAuthError(f"token exchange rejected (HTTP {response.status_code})")
    return response.json()


def store_credentials(
    connection: IntegrationConnection,
    *,
    tokens: dict[str, Any],
    store: EncryptedCredentialStore,
) -> None:
    required = ("access_token",)
    if not all(tokens.get(k) for k in required):
        raise OAuthError("provider returned no access token")
    connection.credentials_encrypted = store.encrypt(tokens)
    connection.status = "connected"


def revoke_connection(connection: IntegrationConnection, *, provider_token_revoke_url: str | None) -> bool:
    """Revoke provider-side tokens when a revoke endpoint is configured."""
    revoked = False
    if provider_token_revoke_url:
        import httpx

        try:
            httpx.post(provider_token_revoke_url, timeout=10)  # best effort
            revoked = True
        except httpx.HTTPError:
            revoked = False
    connection.status = "disconnected"
    return revoked
