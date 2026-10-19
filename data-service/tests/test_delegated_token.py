"""Phase 1301 plan 05, task 2 (DGCL-05, D-06, D-08, D-20): the delegated
``dgd_`` token principal.

A cookie session, with ``X-DG-CSRF``, mints a short-lived Bearer token bound to
one project, its company and its parent session. The token authenticates only
the routes whose policy lists ``delegated``, never elevates an admin, and dies
with the parent session, the membership, the project's company assignment or
its own expiry. Every request goes through the real ``require_principal``;
credentials come from the 1205-08 fixtures and nothing is overridden.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import company  # noqa: E402
import connectors  # noqa: E402
import delegation  # noqa: E402
import route_policy  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
ALICE = "alice@dg.local"


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setattr(app_module, "read_many", lambda *a, **k: [])
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)
    monkeypatch.setattr(app_module, "EXECUTION_OWNERS", {})


@pytest.fixture(params=["local", "multi-user"])
def profile(request, monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", request.param)
    return request.param


@pytest.fixture
def client(profile):
    return TestClient(app, raise_server_exceptions=False)


# -- helpers ----------------------------------------------------------------


def _session(username=ALICE, *, admin=False, memberships=None):
    """Create the user, mint a real session; return (cookie headers, token)."""
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}, token


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _mint(client, cookie_headers, project="P1"):
    return client.post("/auth/delegated-token", json={"project": project}, headers=cookie_headers)


def _minted(client, cookie_headers, project="P1"):
    response = _mint(client, cookie_headers, project)
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _edit_session(token, **changes):
    digest = hashlib.sha256(token.encode()).hexdigest()
    data = _read(auth.SESSIONS_FILE)
    for row in data["sessions"]:
        if row["token_hash"] == digest:
            row.update(changes)
    auth.SESSIONS_FILE.write_text(json.dumps(data), encoding="utf-8")


def _tokens_file():
    return auth.MEMBERSHIPS_FILE.parent / delegation.TOKENS_FILE_NAME


@pytest.fixture
def world(client):
    cookie, session_token = _session(memberships={"P1": "viewer", "P2": "viewer"})
    token = _minted(client, cookie, "P1")
    return {"cookie": cookie, "session": session_token, "token": token}


# -- explicit mapping confirmation -------------------------------------------


def test_delegated_editor_mapping_commit_is_bound_and_receipts_stay_connector_only(client, monkeypatch):
    cookie, _ = _session(memberships={"P1": "editor", "P2": "editor"})
    token = _minted(client, cookie, "P1")
    calls = []

    def capture(fn, *args):
        calls.append((fn, args))
        return {"batchId": "commit-test", "delivery": {"state": "queued"}}

    monkeypatch.setattr(app_module, "_mapping_call", capture)
    path = "/mapping/sessions/ms-test/apply"
    intent = {"project": "P1", "requestId": "commit-test", "revision": "a" * 24, "answerIds": ["A-1"]}
    response = client.post(path, json=intent, headers=_bearer(token))
    assert response.status_code == 200, response.text
    assert calls[0][0] is app_module.mapping_store.apply_session
    assert calls[0][1][0] == "P1" and calls[0][1][-3:] == ("commit-test", "a" * 24, ["A-1"])
    foreign = client.post(path, json={**intent, "project": "P2"}, headers=_bearer(token))
    assert foreign.status_code == 403 and _code(foreign) == "PROJECT_FORBIDDEN"
    receipt = client.post(path, json={"project": "P1", "batchId": "commit-test",
        "delivery": {"state": "written", "written": 1, "skipped": 0}}, headers=_bearer(token))
    assert receipt.status_code == 403 and _code(receipt) == "PRINCIPAL_NOT_PERMITTED"
    assert len(calls) == 1
    assert client.delete("/auth/delegated-token", headers=_bearer(token)).status_code == 204
    revoked = client.post(path, json=intent, headers={**cookie, **_bearer(token)})
    assert revoked.status_code == 401 and len(calls) == 1, "no cookie fallback after explicit bearer revocation"


def test_delegated_viewer_cannot_commit_mapping(client, monkeypatch):
    cookie, _ = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie)
    calls = []
    monkeypatch.setattr(app_module, "_mapping_call", lambda *args: calls.append(args))
    response = client.post("/mapping/sessions/ms-test/apply", json={"project": "P1",
        "requestId": "commit-test", "revision": "a" * 24, "answerIds": ["A-1"]}, headers=_bearer(token))
    assert response.status_code == 403 and not calls


# -- issue ------------------------------------------------------------------


def test_member_mints_a_dgd_token_bound_to_project_and_company(client):
    company.set_project_company("P1", "Acme")
    cookie, _ = _session(memberships={"P1": "viewer"})
    issued_at = int(time.time())
    response = _mint(client, cookie)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token"].startswith("dgd_")
    assert body["project"] == "P1"
    assert body["company"] == "Acme"
    assert body["expiresInSeconds"] == delegation.DELEGATED_TOKEN_TTL_SECONDS == 900
    assert body["expiresAt"].endswith("Z")
    record = _read(_tokens_file())["tokens"][0]
    assert record["project"] == "P1" and record["company"] == "Acme"
    assert record["username"] == ALICE
    assert 0 <= record["expires_at"] - issued_at - 900 <= 5
    assert response.headers["cache-control"] == "no-store"


def test_project_without_company_mints_with_null_company(client):
    cookie, _ = _session(memberships={"P1": "viewer"})
    assert _mint(client, cookie).json()["company"] is None


def test_store_keeps_only_the_hash_and_the_parent_session_hash(client):
    cookie, session = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie)
    text = _tokens_file().read_text(encoding="utf-8")
    assert token not in text
    record = json.loads(text)["tokens"][0]
    assert record["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert record["session_hash"] == hashlib.sha256(session.encode()).hexdigest()
    assert "token" not in record
    leftovers = [p.name for p in _tokens_file().parent.iterdir() if ".tmp-" in p.name]
    assert leftovers == []


def test_non_member_cannot_mint(client):
    cookie, _ = _session(memberships={"P2": "owner"})
    response = _mint(client, cookie, "P1")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"
    assert not _tokens_file().exists()


def test_admin_without_membership_cannot_mint(client):
    cookie, _ = _session("root@dg.local", admin=True)
    response = _mint(client, cookie, "P1")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_mint_without_cookie_is_401(client):
    response = client.post("/auth/delegated-token", json={"project": "P1"}, headers=CSRF)
    assert response.status_code == 401


def test_mint_without_csrf_is_403(client):
    cookie, _ = _session(memberships={"P1": "viewer"})
    cookie.pop(auth.CSRF_HEADER)
    response = _mint(client, cookie)
    assert response.status_code == 403
    assert _code(response) == "CSRF_HEADER_REQUIRED"


def test_mint_without_project_fails_closed(client):
    cookie, _ = _session(memberships={"P1": "viewer"})
    response = client.post("/auth/delegated-token", json={}, headers=cookie)
    assert response.status_code == 403
    assert _code(response) == "PROJECT_REQUIRED"


def test_bearer_callers_cannot_mint(client, world):
    connector = auth_fixtures.connector_token_for("P1")
    for headers in (_bearer(connector), _bearer(world["token"])):
        response = client.post("/auth/delegated-token", json={"project": "P1"}, headers=headers)
        assert response.status_code == 403, response.text
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


# -- authenticate and route scope -------------------------------------------


def test_delegated_reaches_graph_and_rules_of_its_bound_project(client, world):
    for path in ("/graph/P1", "/rules/P1"):
        response = client.get(path, headers=_bearer(world["token"]))
        assert response.status_code == 200, (path, response.text)


def test_delegated_principal_shape():
    auth_fixtures.make_user(ALICE, memberships={"P1": "viewer"})
    session = auth_fixtures.session_cookie_for(ALICE)
    digest = hashlib.sha256(session.encode()).hexdigest()
    token, _record = delegation.issue_delegated_token(
        session_hash=digest, username=ALICE, project="P1"
    )
    principal = delegation.authenticate_delegated_token(token)
    assert principal.kind == "delegated"
    assert principal.username == ALICE
    assert principal.bound_project == "P1"
    assert principal.session_hash == digest
    assert principal.is_admin is False


def test_delegated_for_another_project_is_project_forbidden(client, world):
    for path in ("/graph/P2", "/rules/P2"):
        response = client.get(path, headers=_bearer(world["token"]))
        assert response.status_code == 403, path
        assert _code(response) == "PROJECT_FORBIDDEN"


def test_delegated_denied_on_session_admin_and_member_only_routes(client, world):
    token = _bearer(world["token"])
    probes = [
        ("PUT", "/projects/P1/company", {"company": "x"}),
        ("POST", "/projects", {"project": "Fresh"}),
        ("GET", "/projects", None),
        ("GET", "/auth/me", None),
        ("POST", "/graph/P1/claim-untagged", {"project": "P1"}),
        ("POST", "/auth/delegated-token", {"project": "P1"}),
        ("GET", "/projects/P1/members", None),
    ]
    for method, path, body in probes:
        kwargs = {"json": body} if body is not None else {}
        response = client.request(method, path, headers=token, **kwargs)
        assert response.status_code == 403, (method, path, response.status_code)
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED", (method, path)


def test_admin_delegated_token_does_not_elevate(client):
    cookie, _ = _session("root@dg.local", admin=True, memberships={"P1": "viewer"})
    token = _minted(client, cookie, "P1")
    headers = _bearer(token)
    assert client.get("/graph/P1", headers=headers).status_code == 200
    other = client.get("/graph/P3", headers=headers)
    assert other.status_code == 403 and _code(other) == "PROJECT_FORBIDDEN"
    denied = client.put("/projects/P1/company", json={"company": "x"}, headers=headers)
    assert denied.status_code == 403 and _code(denied) == "PRINCIPAL_NOT_PERMITTED"


def test_delegated_does_not_inherit_a_role_above_membership(client):
    """The viewer membership is re-read live, so a role the route needs above
    it is not granted by the token."""
    cookie, _ = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie, "P1")
    probe = FastAPI()

    @probe.get("/probe-editor/{project}")
    def _editor(project: str, principal=Depends(auth.require_principal)):
        return {"ok": True}

    route_policy.ROUTE_POLICIES[("GET", "/probe-editor/{project}")] = route_policy.RoutePolicy(
        principals=frozenset({route_policy.PRINCIPAL_MEMBER, route_policy.PRINCIPAL_DELEGATED}),
        project_source="path",
        min_role="editor",
    )
    try:
        response = TestClient(probe, raise_server_exceptions=False).get(
            "/probe-editor/P1", headers=_bearer(token)
        )
    finally:
        del route_policy.ROUTE_POLICIES[("GET", "/probe-editor/{project}")]
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_connector_and_service_tokens_do_not_reach_delegated_only_routes(client):
    connector = auth_fixtures.connector_token_for("P1")
    for headers in (_bearer(connector), auth_fixtures.service_headers()):
        response = client.delete("/auth/delegated-token", headers=headers)
        assert response.status_code == 403
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_cookie_session_cannot_use_the_delegated_only_route(client, world):
    response = client.delete("/auth/delegated-token", headers=world["cookie"])
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


# -- CSRF -------------------------------------------------------------------


def _probe_app(monkeypatch):
    probe = FastAPI()

    @probe.post("/probe/{project}")
    async def _post(project: str, request: Request, principal=Depends(auth.require_principal)):
        return {"kind": principal.kind}

    monkeypatch.setitem(
        route_policy.ROUTE_POLICIES,
        ("POST", "/probe/{project}"),
        route_policy.RoutePolicy(
            principals=frozenset(
                {
                    route_policy.PRINCIPAL_MEMBER,
                    route_policy.PRINCIPAL_DELEGATED,
                    route_policy.PRINCIPAL_SERVICE,
                }
            ),
            project_source="path",
            min_role="viewer",
        ),
    )
    return TestClient(probe, raise_server_exceptions=False)


def test_delegated_post_needs_no_csrf_header_but_cookie_post_does(client, world, monkeypatch):
    probe = _probe_app(monkeypatch)
    delegated = probe.post("/probe/P1", json={}, headers=_bearer(world["token"]))
    assert delegated.status_code == 200, delegated.text
    assert delegated.json() == {"kind": "delegated"}

    cookie_only = {"Cookie": world["cookie"]["Cookie"]}
    refused = probe.post("/probe/P1", json={}, headers=cookie_only)
    assert refused.status_code == 403
    assert _code(refused) == "CSRF_HEADER_REQUIRED"
    assert probe.post("/probe/P1", json={}, headers=world["cookie"]).status_code == 200


def test_service_header_outranks_a_delegated_bearer(client, world, monkeypatch):
    probe = _probe_app(monkeypatch)
    headers = {**auth_fixtures.service_headers(), **_bearer(world["token"])}
    response = probe.post("/probe/P1", json={}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"kind": "service"}


def test_delegated_delete_without_csrf_is_accepted(client, world):
    response = client.delete("/auth/delegated-token", headers=_bearer(world["token"]))
    assert response.status_code == 204


# -- no fallback ------------------------------------------------------------


def test_invalid_dgd_bearer_never_falls_back_to_a_present_cookie(client, world):
    headers = {"Cookie": world["cookie"]["Cookie"], **_bearer("dgd_not-a-real-token")}
    response = client.get("/graph/P1", headers=headers)
    assert response.status_code == 401
    assert _code(response) == "DELEGATED_AUTH_FAILED"


def test_valid_dgd_bearer_is_not_downgraded_by_a_bad_cookie(client, world):
    headers = {"Cookie": f"{auth.SESSION_COOKIE_NAME}=dgs_bogus", **_bearer(world["token"])}
    assert client.get("/graph/P1", headers=headers).status_code == 200


def test_unknown_dgd_token_is_401(client):
    response = client.get("/graph/P1", headers=_bearer("dgd_" + "a" * 40))
    assert response.status_code == 401
    assert _code(response) == "DELEGATED_AUTH_FAILED"


# -- lifecycle: each end-of-access case --------------------------------------


def _expect_dead(client, token, status, code):
    response = client.get("/graph/P1", headers=_bearer(token))
    assert response.status_code == status, response.text
    assert _code(response) == code


def test_logout_of_the_parent_session_kills_the_token(client, world):
    assert client.get("/graph/P1", headers=_bearer(world["token"])).status_code == 200
    assert client.post("/auth/logout", headers=world["cookie"]).status_code == 204
    _expect_dead(client, world["token"], 401, "DELEGATED_SESSION_ENDED")


def test_logout_revokes_every_token_of_that_session_but_not_other_sessions(client):
    cookie_a, _ = _session(memberships={"P1": "viewer"})
    cookie_b, _ = _session(memberships={"P1": "viewer"})
    first, second = _minted(client, cookie_a), _minted(client, cookie_a)
    other = _minted(client, cookie_b)
    assert client.post("/auth/logout", headers=cookie_a).status_code == 204
    for token in (first, second):
        _expect_dead(client, token, 401, "DELEGATED_SESSION_ENDED")
    assert client.get("/graph/P1", headers=_bearer(other)).status_code == 200


def test_password_change_kills_the_token(client):
    password = auth_fixtures.make_user("pw@dg.local", memberships={"P1": "viewer"})["password"]
    pw_cookie, _ = _session("pw@dg.local")
    token = _minted(client, pw_cookie)
    response = client.post(
        "/auth/password",
        json={"currentPassword": password, "newPassword": "a-brand-new-password-1"},
        headers=pw_cookie,
    )
    assert response.status_code == 204, response.text
    _expect_dead(client, token, 401, "DELEGATED_SESSION_ENDED")


def test_password_change_kills_tokens_of_other_sessions_too(client):
    password = auth_fixtures.make_user("pw2@dg.local", memberships={"P1": "viewer"})["password"]
    cookie_a, _ = _session("pw2@dg.local")
    cookie_b, _ = _session("pw2@dg.local")
    other = _minted(client, cookie_b)
    client.post(
        "/auth/password",
        json={"currentPassword": password, "newPassword": "a-brand-new-password-2"},
        headers=cookie_a,
    )
    _expect_dead(client, other, 401, "DELEGATED_SESSION_ENDED")


def test_parent_session_expiry_kills_the_token(client, world):
    _edit_session(world["session"], expires_at=int(time.time()) - 1)
    _expect_dead(client, world["token"], 401, "DELEGATED_SESSION_ENDED")


def test_parent_session_idle_timeout_kills_the_token(client, world):
    _edit_session(world["session"], last_seen_at=int(time.time()) - 10_000)
    _expect_dead(client, world["token"], 401, "DELEGATED_SESSION_ENDED")


def test_delegated_use_does_not_refresh_the_parent_idle_timer(client, world):
    stale = int(time.time()) - 600  # past the 60 s touch interval, inside idle
    _edit_session(world["session"], last_seen_at=stale)
    assert client.get("/graph/P1", headers=_bearer(world["token"])).status_code == 200
    digest = hashlib.sha256(world["session"].encode()).hexdigest()
    rows = [r for r in _read(auth.SESSIONS_FILE)["sessions"] if r["token_hash"] == digest]
    assert rows[0]["last_seen_at"] == stale


def test_membership_removal_through_the_route_kills_the_token(client, world):
    admin, _ = _session("root@dg.local", admin=True)
    removed = client.delete(f"/projects/P1/members/{ALICE}", headers=admin)
    # alice is the only member and a viewer: removal is allowed (not an owner)
    assert removed.status_code == 204, removed.text
    _expect_dead(client, world["token"], 403, "PROJECT_FORBIDDEN")


def test_membership_removed_behind_the_routes_back_is_still_caught_live(client, world):
    auth.remove_membership(ALICE, "P1")
    _expect_dead(client, world["token"], 403, "PROJECT_FORBIDDEN")


def test_company_reassignment_through_the_route_kills_the_token(client):
    company.set_project_company("P1", "Acme")
    cookie, _ = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie, "P1")
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 200
    admin, _ = _session("root@dg.local", admin=True)
    changed = client.put("/projects/P1/company", json={"company": "Globex"}, headers=admin)
    assert changed.status_code == 200
    _expect_dead(client, token, 403, "DELEGATED_SCOPE_CHANGED")


def test_company_change_behind_the_routes_back_is_caught_and_stays_dead(client):
    company.set_project_company("P1", "Acme")
    cookie, _ = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie, "P1")
    company.set_project_company("P1", "Globex")
    _expect_dead(client, token, 403, "DELEGATED_SCOPE_CHANGED")
    company.set_project_company("P1", "Acme")  # putting it back must not resurrect
    _expect_dead(client, token, 403, "DELEGATED_SCOPE_CHANGED")


def test_assigning_a_company_to_a_previously_unassigned_project_changes_scope(client):
    cookie, _ = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie, "P1")
    company.set_project_company("P1", "Acme")
    _expect_dead(client, token, 403, "DELEGATED_SCOPE_CHANGED")


def test_token_expiry_is_401_delegated_expired(client, world):
    data = _read(_tokens_file())
    data["tokens"][0]["expires_at"] = int(time.time()) - 1
    _tokens_file().write_text(json.dumps(data), encoding="utf-8")
    _expect_dead(client, world["token"], 401, "DELEGATED_EXPIRED")


def test_expiry_boundary_is_inclusive():
    auth_fixtures.make_user(ALICE, memberships={"P1": "viewer"})
    session = auth_fixtures.session_cookie_for(ALICE)
    digest = hashlib.sha256(session.encode()).hexdigest()
    now = int(time.time())
    token, record = delegation.issue_delegated_token(
        session_hash=digest, username=ALICE, project="P1", now=now
    )
    assert record["expires_at"] == now + delegation.DELEGATED_TOKEN_TTL_SECONDS
    delegation.authenticate_delegated_token(token, now=now + 899)
    with pytest.raises(Exception) as caught:
        delegation.authenticate_delegated_token(token, now=now + 900)
    assert caught.value.detail["code"] == "DELEGATED_EXPIRED"


def test_explicit_delete_revokes_only_the_callers_token(client):
    cookie, _ = _session(memberships={"P1": "viewer"})
    mine, theirs = _minted(client, cookie), _minted(client, cookie)
    assert client.delete("/auth/delegated-token", headers=_bearer(mine)).status_code == 204
    _expect_dead(client, mine, 401, "DELEGATED_AUTH_FAILED")
    assert client.get("/graph/P1", headers=_bearer(theirs)).status_code == 200


def test_user_removed_from_the_store_ends_the_token(client, world):
    users = _read(auth.USERS_FILE)
    users["users"] = []
    auth.USERS_FILE.write_text(json.dumps(users), encoding="utf-8")
    _expect_dead(client, world["token"], 401, "DELEGATED_SESSION_ENDED")


# -- logging ----------------------------------------------------------------


def test_raw_token_is_never_logged(client, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    cookie, _ = _session(memberships={"P1": "viewer"})
    token = _minted(client, cookie)
    client.get("/graph/P1", headers=_bearer(token))
    client.get("/graph/P2", headers=_bearer(token))
    client.delete("/auth/delegated-token", headers=_bearer(token))
    client.get("/graph/P1", headers=_bearer(token))  # revoked
    client.get("/graph/P1", headers=_bearer("dgd_" + "z" * 43))
    secret = token[len("dgd_"):]
    assert token not in caplog.text
    assert secret not in caplog.text
