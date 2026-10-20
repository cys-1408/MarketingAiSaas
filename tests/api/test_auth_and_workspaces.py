"""API tests: authentication and workspace membership."""

from __future__ import annotations

import time


def test_signup_creates_workspace_and_login(api):
    email = f"a-{int(time.time() * 1000)}@example.com"
    signup = api.post(
        "auth/signup",
        json={
            "email": email, "password": "correct-horse-42",
            "name": "A", "workspace_name": "A WS",
        },
    )
    assert signup.status_code == 201
    payload = signup.json()
    assert payload["token"] and payload["workspace"]["id"]

    login = api.post("auth/login", json={"email": email, "password": "correct-horse-42"})
    assert login.status_code == 200
    me = api.get("auth/me")
    print("ME-DETAIL:", me.text)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email
    assert "password_hash" not in me.text


def test_duplicate_signup_counts_as_conflict_without_enumeration(api):
    email = f"d-{int(time.time() * 1000)}@example.com"
    body = {
        "email": email, "password": "correct-horse-42",
        "name": "D", "workspace_name": "D WS",
    }
    assert api.post("auth/signup", json=body).status_code == 201
    duplicate = api.post("auth/signup", json=body)
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"].lower()


def test_weak_password_rejected(api):
    response = api.post(
        "auth/signup",
        json={"email": f"w-{time.time()}@example.com", "password": "short",
              "name": "W", "workspace_name": "W"},
    )
    assert response.status_code == 422


def test_invalid_login_generic_error(api, tenant_two):
    login = api._client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "nope-nope-nope"},
    )
    assert login.status_code == 401
    assert "invalid" in login.json()["detail"].lower()
    # Nonexistent email and wrong password produce the same message.
    wrong_password = api._client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "nope-nope-nope"},
    )
    assert wrong_password.json()["detail"] == login.json()["detail"]


def test_logout_revokes_token(api):
    assert api.post("auth/logout").status_code == 200
    after = api.get("auth/me")
    assert after.status_code == 401
    # Restore session for remaining tests in this module ordering safety.
    api.signup()


def test_requires_authorization_header(api):
    bare = api._client.get("/api/v1/auth/me")
    assert bare.status_code == 401


def test_member_management_and_roles(api, tenant_two):
    payload = api.post(
        f"workspaces/{api.workspace_id}/members",
        json={"email": tenant_two["user"]["email"], "role": "viewer"},
    )
    assert payload.status_code == 201
    member_id = payload.json()["user_id"]
    promote = api.patch(
        f"workspaces/{api.workspace_id}/members/{member_id}",
        json={"role": "analyst"},
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "analyst"
    usage = api.get(f"workspaces/{api.workspace_id}/usage").json()
    assert usage["members"] >= 2
    assert usage["notes"].startswith("counts are measured")
    owner = api.get(f"workspaces/{api.workspace_id}").json()
    assert any(m["role"] == "owner" for m in owner["members"])


def test_nonexistent_member_email_rejected(api):
    response = api.post(
        f"workspaces/{api.workspace_id}/members",
        json={"email": "missing-user-999@example.com", "role": "viewer"},
    )
    assert response.status_code == 404


def test_invalid_role_rejected(api, tenant_two):
    response = api.post(
        f"workspaces/{api.workspace_id}/members",
        json={"email": tenant_two["user"]["email"], "role": "supreme"},
    )
    assert response.status_code == 422
