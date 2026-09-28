"""End-to-end tracer tests for Phase 1205 "Security and Tenancy Release Gate"
plan 07 (ALGN12-17, ALGN12-19, D-01..D-05, D-07, D-11, D-19).

Proves D-01/D-02/D-03/D-04 end to end on one real route
(`GET /validation/runs/{project}`) with real sessions: server-side login, the
deny-by-default policy-driven `require_principal` dependency, and the
project-scoped 403/401 rules -- before 1205-10 expands enforcement to every
route.

Follows the test_auth_store.py / test_connectors.py header pattern: sys.path
insert so `app`/`auth`/`auth_routes`/`connectors`/`route_policy` import as
top-level modules, LLM_MASTER_SECRET set before any data-service import, and
persistence redirected to a per-test tmp_path.

Every test is parametrized over both deployment profiles (D-19): the tracer's
own auth/authz behavior must be identical in `local` and `multi-user` --
1205-07's Task 2 is what actually makes the *startup* and *heartbeat* paths
profile-sensitive; this file only proves the request-time behavior does not
regress under either profile.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402
import route_policy  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402

CSRF_HEADERS = {"X-DG-CSRF": "1"}

PASSWORD_A = "correct-horse-battery-a"
PASSWORD_ADMIN = "correct-horse-battery-admin"


@pytest.fixture(autouse=True)
def _redirect_stores(tmp_path, monkeypatch):
    """Self-contained: every store this plan touches is redirected to a
    per-test tmp_path, and no real connector store or service token is ever
    read (test_auth_store.py / test_connectors.py convention)."""
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setenv("DG_SERVICE_TOKEN", "test-service-token-0123456789abcdef")
    monkeypatch.setattr(app_module, "list_validation_runs", lambda project: [])
    yield


@pytest.fixture(params=["local", "multi-user"])
def deployment_profile(request, monkeypatch):
    """D-19: every behavior in this file passes under both profiles."""
    monkeypatch.setenv("DG_DEPLOYMENT", request.param)
    return request.param


@pytest.fixture
def client(deployment_profile):
    return TestClient(app, raise_server_exceptions=False)


def _connector_token(project: str) -> str:
    _record, token = connectors.create_credential("grasshopper", project=project)
    return token


# ── Login / logout / me / password (D-01) ──────────────────────────────────


def test_login_success_sets_httponly_samesite_cookie_and_no_token_in_body(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)

    resp = client.post(
        "/auth/login",
        json={"username": "user-a", "password": PASSWORD_A},
        headers=CSRF_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"username": "user-a", "isAdmin": False}
    assert "password" not in resp.text and "token" not in body

    set_cookie = resp.headers.get("set-cookie", "")
    assert auth.SESSION_COOKIE_NAME in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=strict" in set_cookie.lower()


def test_login_wrong_password_and_unknown_user_both_401_auth_failed_identical_message(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)

    wrong_password = client.post(
        "/auth/login",
        json={"username": "user-a", "password": "totally-wrong-password"},
        headers=CSRF_HEADERS,
    )
    unknown_user = client.post(
        "/auth/login",
        json={"username": "nobody-here", "password": "whatever-password"},
        headers=CSRF_HEADERS,
    )

    for resp in (wrong_password, unknown_user):
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_FAILED"

    assert wrong_password.json()["detail"]["error"] == unknown_user.json()["detail"]["error"]


def test_login_without_csrf_header_403(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)

    resp = client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A})

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_HEADER_REQUIRED"


def test_auth_me_returns_username_isadmin_and_memberships(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    auth.set_membership("user-a", "P1", "editor")
    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    resp = client.get("/auth/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "user-a"
    assert body["isAdmin"] is False
    assert body["memberships"] == [{"project": "P1", "role": "editor"}]


def test_logout_revokes_session_then_401(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    logout_resp = client.post("/auth/logout", headers=CSRF_HEADERS)
    assert logout_resp.status_code == 204

    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 401
    assert me_resp.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_password_change_wrong_current_403(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    resp = client.post(
        "/auth/password",
        json={"currentPassword": "not-the-real-password", "newPassword": "brand-new-password-1"},
        headers=CSRF_HEADERS,
    )

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PASSWORD_INCORRECT"


def test_password_change_weak_new_password_422(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    resp = client.post(
        "/auth/password",
        json={"currentPassword": PASSWORD_A, "newPassword": "11-char-pw!"},
        headers=CSRF_HEADERS,
    )

    assert len("11-char-pw!") == 11
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PASSWORD_POLICY"


def test_password_change_success_revokes_other_sessions_keeps_current(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    other_token = auth.create_session("user-a")

    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    new_password = "brand-new-password-1"
    change_resp = client.post(
        "/auth/password",
        json={"currentPassword": PASSWORD_A, "newPassword": new_password},
        headers=CSRF_HEADERS,
    )
    assert change_resp.status_code == 204

    # The other session is revoked.
    other_client = TestClient(app, raise_server_exceptions=False)
    other_client.cookies.set(auth.SESSION_COOKIE_NAME, other_token)
    other_resp = other_client.get("/auth/me")
    assert other_resp.status_code == 401
    assert other_resp.json()["detail"]["code"] == "AUTH_REQUIRED"

    # The current session (the one that just changed the password) still works.
    current_resp = client.get("/auth/me")
    assert current_resp.status_code == 200


# ── The tracer's one enforced project route (D-03/D-04) ────────────────────


def test_member_access_cross_project_403_and_no_cookie_401(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    auth.set_membership("user-a", "P1", "editor")
    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    own_project = client.get("/validation/runs/P1")
    assert own_project.status_code == 200
    assert own_project.json() == {"project": "P1", "runs": []}

    other_project = client.get("/validation/runs/P2")
    assert other_project.status_code == 403
    assert other_project.json()["detail"]["code"] == "PROJECT_FORBIDDEN"

    anonymous_client = TestClient(app, raise_server_exceptions=False)
    no_cookie = anonymous_client.get("/validation/runs/P1")
    assert no_cookie.status_code == 401
    assert no_cookie.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_admin_user_can_access_any_project(client, deployment_profile):
    auth.create_user("admin-user", PASSWORD_ADMIN, is_admin=True)
    client.post("/auth/login", json={"username": "admin-user", "password": PASSWORD_ADMIN}, headers=CSRF_HEADERS)

    resp = client.get("/validation/runs/P2")

    assert resp.status_code == 200
    assert resp.json() == {"project": "P2", "runs": []}


def test_connector_token_bound_to_p1_on_p1_route_is_principal_not_permitted(client, deployment_profile):
    token = _connector_token("P1")

    resp = client.get("/validation/runs/P1", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PRINCIPAL_NOT_PERMITTED"


def test_invalid_bearer_plus_valid_cookie_401_connector_auth_failed_no_fallback(client, deployment_profile):
    auth.create_user("user-a", PASSWORD_A)
    auth.set_membership("user-a", "P1", "editor")
    client.post("/auth/login", json={"username": "user-a", "password": PASSWORD_A}, headers=CSRF_HEADERS)

    resp = client.get(
        "/validation/runs/P1",
        headers={"Authorization": "Bearer dgc_not-a-real-token"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "CONNECTOR_AUTH_FAILED"


def test_valid_service_header_on_route_is_principal_not_permitted(client, deployment_profile):
    resp = client.get(
        "/validation/runs/P1",
        headers={auth.SERVICE_TOKEN_HEADER: "test-service-token-0123456789abcdef"},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PRINCIPAL_NOT_PERMITTED"


def test_wrong_service_header_401_service_auth_failed(client, deployment_profile):
    resp = client.get(
        "/validation/runs/P1",
        headers={auth.SERVICE_TOKEN_HEADER: "definitely-the-wrong-token"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "SERVICE_AUTH_FAILED"


# ── Policy-driven fail-closed behavior, exercised on throwaway routes ───────
# (RESEARCH.md/1205-CONTEXT.md pattern: a route with no ROUTE_POLICIES entry,
# or one with a body-and-path project source, is proven with a private
# FastAPI app rather than mutating the real app.py's route table.)


def test_unclassified_route_answers_403_route_unclassified(deployment_profile):
    throwaway = FastAPI()

    @throwaway.get("/no-policy")
    def _no_policy(principal=Depends(auth.require_principal)):
        return {"ok": True}

    tc = TestClient(throwaway, raise_server_exceptions=False)
    resp = tc.get("/no-policy")

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ROUTE_UNCLASSIFIED"


def test_body_and_path_project_mismatch_403(deployment_profile, monkeypatch):
    auth.create_user("user-b", PASSWORD_A)
    auth.set_membership("user-b", "P1", "editor")
    token = auth.create_session("user-b")

    throwaway = FastAPI()

    @throwaway.post("/throwaway/{project}")
    async def _throwaway(project: str, request: Request, principal=Depends(auth.require_principal)):
        return {"ok": True}

    monkeypatch.setitem(
        route_policy.ROUTE_POLICIES,
        ("POST", "/throwaway/{project}"),
        route_policy.RoutePolicy(
            principals=frozenset({route_policy.PRINCIPAL_SESSION}),
            project_source="path",
        ),
    )

    tc = TestClient(throwaway, raise_server_exceptions=False)
    resp = tc.post(
        "/throwaway/P1",
        json={"project": "P2"},
        cookies={auth.SESSION_COOKIE_NAME: token},
        headers=CSRF_HEADERS,
    )

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PROJECT_MISMATCH"


def test_declared_project_source_absent_403_project_required(deployment_profile, monkeypatch):
    auth.create_user("user-c", PASSWORD_A)
    token = auth.create_session("user-c")

    throwaway = FastAPI()

    @throwaway.post("/throwaway-body-only")
    async def _throwaway(request: Request, principal=Depends(auth.require_principal)):
        return {"ok": True}

    monkeypatch.setitem(
        route_policy.ROUTE_POLICIES,
        ("POST", "/throwaway-body-only"),
        route_policy.RoutePolicy(
            principals=frozenset({route_policy.PRINCIPAL_SESSION}),
            project_source="body",
        ),
    )

    tc = TestClient(throwaway, raise_server_exceptions=False)
    resp = tc.post(
        "/throwaway-body-only",
        json={"note": "no project key here"},
        cookies={auth.SESSION_COOKIE_NAME: token},
        headers=CSRF_HEADERS,
    )

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PROJECT_REQUIRED"
