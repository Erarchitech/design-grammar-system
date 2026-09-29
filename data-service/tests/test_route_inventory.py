"""D-14 route inventory and denial sweeps (Phase 1205 plan 10, ALGN12-17,
ALGN12-20; D-03, D-04, D-14, D-19, D-20).

Proves, for the whole data-service API:

* every ``APIRoute`` carries ``auth.require_principal`` in its dependency tree
  (D-03);
* the set of ``(method, path template)`` pairs registered on the app equals
  the key set of ``route_policy.ROUTE_POLICIES`` in BOTH directions -- a new
  route without a classification, or a stale classification, fails the suite
  (D-14);
* every denial class holds for every policy row: no credential (401), service
  token on a non-service route (403), user session on a service route (403),
  non-admin on an admin route (403 ADMIN_REQUIRED), a user with no membership
  on a member route (403 PROJECT_FORBIDDEN or the resource's 404), an
  under-privileged member (403), a connector bound to another project (403);
* resource routes answer an unknown and an unauthorised resource with the
  same 404 (ALGN12-20).

No test-only bypass: requests carry real cookies/tokens minted through the
1205-08 fixtures (D-20). ``DG_TEST_PRINCIPAL = "none"`` keeps the conftest
autouse fixture from pre-authorising anything here.
"""

from __future__ import annotations

import os
import re
import sys

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402
import route_policy  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
_BODY_METHODS = {"POST", "PUT", "DELETE"}
_DOCS_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

ROWS = sorted(route_policy.ROUTE_POLICIES.items(), key=lambda kv: kv[0])
ROW_IDS = [f"{m} {p}" for (m, p), _ in ROWS]


def _non_public(policy: route_policy.RoutePolicy) -> bool:
    return route_policy.PRINCIPAL_PUBLIC not in policy.principals


def _rows(pred):
    return [
        pytest.param(key, policy, id=f"{key[0]} {key[1]}")
        for key, policy in ROWS
        if pred(policy)
    ]


# ── request construction ───────────────────────────────────────────────────


def _path_for(template: str) -> str:
    return re.sub(
        r"\{([^}]+)\}", lambda m: "P1" if m.group(1) == "project" else "x", template
    )


def _send(client: TestClient, key, policy, headers=None):
    method, template = key
    kwargs: dict = {"headers": headers or {}}
    if policy.project_source == "query":
        kwargs["params"] = {"project": "P1"}
    if method in _BODY_METHODS:
        body = {"project": "P1"}
        if template == "/designstate/capture":
            body["statePayloadJson"] = "{}"
        kwargs["json"] = body
    return client.request(method, _path_for(template), **kwargs)


def _code(response) -> str | None:
    try:
        detail = response.json().get("detail")
    except Exception:
        return None
    return detail.get("code") if isinstance(detail, dict) else None


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    # The note resolver reads Neo4j; an empty graph keeps every sweep offline.
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)
    monkeypatch.setattr(app_module, "EXECUTION_OWNERS", {})


@pytest.fixture(params=["local", "multi-user"])
def profile(request, monkeypatch):
    """D-19: every sweep passes under both deployment profiles."""
    monkeypatch.setenv("DG_DEPLOYMENT", request.param)
    return request.param


@pytest.fixture
def client(profile):
    return TestClient(app, raise_server_exceptions=False)


def _user_headers(username, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


# ── comparator (D-14) ──────────────────────────────────────────────────────


def compare_routes(route_keys: set, policy_keys: set) -> tuple[set, set]:
    """Return ``(unclassified, stale)``: routes lacking a policy row, and
    policy rows naming no registered route."""
    return route_keys - policy_keys, policy_keys - route_keys


def _flat_routes() -> list[tuple[str, str | None, set, object]]:
    """Every registered route as ``(kind, path, methods, dependant)``,
    ``kind`` being ``"api"`` or ``"other"``.

    Older FastAPI releases put each included ``APIRoute`` straight into
    ``app.routes`` (with the router-level dependencies already merged into its
    dependant); newer ones wrap an included router in a lazy
    ``_IncludedRouter`` whose ``effective_route_contexts()`` carry the full
    path and merged dependant. Both shapes are flattened here so the inventory
    holds in the dev host and in the container image.
    """
    flat: list[tuple[str, str | None, set, object]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            flat.append(("api", route.path, set(route.methods), route.dependant))
        elif hasattr(route, "effective_route_contexts"):
            for ctx in route.effective_route_contexts():
                if isinstance(ctx.original_route, APIRoute):
                    flat.append(("api", ctx.path, set(ctx.methods), ctx.dependant))
                else:
                    flat.append(("other", getattr(ctx.starlette_route, "path", None), set(), None))
        else:
            flat.append(("other", getattr(route, "path", None), set(), None))
    return flat


def _registered_keys() -> set:
    keys = set()
    for kind, path, methods, _dependant in _flat_routes():
        if kind == "api":
            for method in methods - {"HEAD", "OPTIONS"}:
                keys.add((method, path))
    return keys


def _dependency_calls(dependant) -> set:
    calls = set()
    for sub in dependant.dependencies:
        calls.add(sub.call)
        calls |= _dependency_calls(sub)
    return calls


class TestInventory:
    def test_every_api_route_has_require_principal(self):
        api_routes = [r for r in _flat_routes() if r[0] == "api"]
        assert len(api_routes) >= 60  # the flattening really found the routes
        missing = [
            path
            for _kind, path, _methods, dependant in api_routes
            if auth.require_principal not in _dependency_calls(dependant)
        ]
        assert missing == []

    def test_registered_routes_equal_policy_keys_in_both_directions(self):
        unclassified, stale = compare_routes(
            _registered_keys(), set(route_policy.ROUTE_POLICIES)
        )
        assert unclassified == set(), f"routes without a policy row: {sorted(unclassified)}"
        assert stale == set(), f"policy rows without a route: {sorted(stale)}"

    def test_only_docs_routes_are_not_api_routes_and_only_in_local(self):
        extras = {path for kind, path, _m, _d in _flat_routes() if kind == "other"}
        assert extras <= _DOCS_PATHS
        if not app_module._DOCS_ENABLED:
            assert extras == set()

    def test_policy_table_size(self):
        assert len(route_policy.ROUTE_POLICIES) == 73

    def test_removed_routes_are_gone(self):
        paths = {k[1] for k in _registered_keys()}
        assert "/create_node/" not in paths
        assert "/execution-result/latest/{workflow}" not in paths
        assert not hasattr(app_module, "WORKFLOW_STATUS")

    def test_comparator_reports_an_induced_mismatch(self):
        policy_keys = set(route_policy.ROUTE_POLICIES)
        unclassified, stale = compare_routes(
            _registered_keys() | {("GET", "/throwaway")}, policy_keys
        )
        assert unclassified == {("GET", "/throwaway")}
        assert stale == set()
        unclassified, stale = compare_routes(
            _registered_keys(), policy_keys | {("GET", "/stale-row")}
        )
        assert unclassified == set()
        assert stale == {("GET", "/stale-row")}

    def test_policy_rows_are_well_formed(self):
        for key, policy in ROWS:
            assert policy.principals, key
            assert policy.principals <= {
                route_policy.PRINCIPAL_PUBLIC,
                route_policy.PRINCIPAL_SESSION,
                route_policy.PRINCIPAL_ADMIN,
                route_policy.PRINCIPAL_MEMBER,
                route_policy.PRINCIPAL_CONNECTOR,
                route_policy.PRINCIPAL_SERVICE,
                route_policy.PRINCIPAL_CONNECTOR_SELF,
            }, key
            if route_policy.PRINCIPAL_MEMBER in policy.principals:
                assert policy.project_source and policy.min_role, key


# ── denial sweeps (one case per policy row per profile) ────────────────────


def test_health_is_public(client):
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("key,policy", _rows(_non_public))
def test_no_credential_answers_401(client, key, policy):
    response = _send(client, key, policy)
    assert response.status_code == 401, (key, response.status_code, response.text)


@pytest.mark.parametrize(
    "key,policy",
    _rows(
        lambda p: _non_public(p)
        and route_policy.PRINCIPAL_SERVICE not in p.principals
        and route_policy.PRINCIPAL_CONNECTOR_SELF not in p.principals
    ),
)
def test_service_token_on_non_service_route_is_403(client, key, policy):
    response = _send(client, key, policy, headers=auth_fixtures.service_headers())
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


@pytest.mark.parametrize(
    "key,policy", _rows(lambda p: route_policy.PRINCIPAL_SERVICE in p.principals)
)
def test_user_session_on_service_route_is_403(client, key, policy):
    plain = _user_headers("plain@dg.local")
    admin = _user_headers("root@dg.local", admin=True)
    for headers in (plain, admin):
        response = _send(client, key, policy, headers=headers)
        assert response.status_code == 403, (key, response.status_code)
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


@pytest.mark.parametrize(
    "key,policy", _rows(lambda p: p.principals == {route_policy.PRINCIPAL_ADMIN})
)
def test_non_admin_on_admin_route_is_403_admin_required(client, key, policy):
    headers = _user_headers(
        "owner-not-admin@dg.local", memberships={"P1": "owner"}
    )
    response = _send(client, key, policy, headers=headers)
    assert response.status_code == 403, (key, response.status_code)
    assert _code(response) == "ADMIN_REQUIRED"


def _member_rows():
    return _rows(
        lambda p: route_policy.PRINCIPAL_MEMBER in p.principals
        and not (p.project_source or "").startswith("resource:")
    )


def _resource_rows():
    return _rows(lambda p: (p.project_source or "").startswith("resource:"))


@pytest.mark.parametrize("key,policy", _member_rows())
def test_user_without_membership_is_403_project_forbidden(client, key, policy):
    headers = _user_headers("nobody@dg.local")
    response = _send(client, key, policy, headers=headers)
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize("key,policy", _resource_rows())
def test_user_without_membership_gets_the_resource_404(client, key, policy):
    headers = _user_headers("nobody@dg.local")
    response = _send(client, key, policy, headers=headers)
    assert response.status_code == 404, (key, response.status_code, response.text)


@pytest.mark.parametrize(
    "key,policy",
    _rows(
        lambda p: route_policy.PRINCIPAL_MEMBER in p.principals
        and p.min_role in ("editor", "owner")
        and not (p.project_source or "").startswith("resource:")
    ),
)
def test_viewer_on_editor_or_owner_route_is_403(client, key, policy):
    headers = _user_headers("viewer@dg.local", memberships={"P1": "viewer"})
    if policy.min_role == "owner":
        headers = _user_headers("editor@dg.local", memberships={"P1": "editor"})
    response = _send(client, key, policy, headers=headers)
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize(
    "key,policy",
    _rows(
        lambda p: route_policy.PRINCIPAL_CONNECTOR in p.principals
        and p.project_source == "path"
        or (
            route_policy.PRINCIPAL_CONNECTOR in p.principals
            and p.project_source == "body"
        )
    ),
)
def test_connector_bound_to_another_project_is_403(client, key, policy):
    token = auth_fixtures.connector_token_for("P2")
    response = _send(
        client, key, policy, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize(
    "key,policy",
    _rows(
        lambda p: _non_public(p)
        and route_policy.PRINCIPAL_CONNECTOR not in p.principals
        and route_policy.PRINCIPAL_CONNECTOR_SELF not in p.principals
    ),
)
def test_connector_token_on_non_connector_route_is_403(client, key, policy):
    token = auth_fixtures.connector_token_for("P1")
    response = _send(
        client, key, policy, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


@pytest.mark.parametrize(
    "key,policy",
    _rows(lambda p: p.project_source == "body" and route_policy.PRINCIPAL_MEMBER in p.principals),
)
def test_body_route_without_project_fails_closed(client, key, policy):
    """Research gap 3: a body-sourced route with no project in the body is
    403 PROJECT_REQUIRED (never an unscoped default)."""
    headers = _user_headers("owner@dg.local", memberships={"P1": "owner"})
    response = client.request(key[0], _path_for(key[1]), headers=headers, json={})
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_REQUIRED"


# ── resource routes: no-leak 404 and owner binding (ALGN12-20) ─────────────


class TestResourceNotFoundSemantics:
    def test_credential_of_another_project_is_the_same_404_as_unknown(self, client):
        record, _token = connectors.create_credential("grasshopper", project="P2")
        headers = _user_headers("p1editor@dg.local", memberships={"P1": "editor"})
        known = client.delete(
            f"/connectors/grasshopper/credentials/{record['credential_id']}",
            headers=headers,
        )
        unknown = client.delete(
            "/connectors/grasshopper/credentials/does-not-exist", headers=headers
        )
        assert known.status_code == unknown.status_code == 404
        assert _code(known) == _code(unknown) == "CREDENTIAL_NOT_FOUND"
        assert known.json() == unknown.json()
        # and the credential is still live
        stored = connectors.load_credentials()
        assert stored and not stored[0].get("revoked")

    def test_credential_of_own_project_is_revocable_by_an_editor(self, client):
        record, _token = connectors.create_credential("grasshopper", project="P1")
        headers = _user_headers("p1editor@dg.local", memberships={"P1": "editor"})
        response = client.delete(
            f"/connectors/grasshopper/credentials/{record['credential_id']}",
            headers=headers,
        )
        assert response.status_code == 204

    def test_note_of_another_project_is_the_same_404_as_unknown(self, client, monkeypatch):
        def fake_read(query, params=None):
            if params and params.get("noteId") == "note-p2":
                return {"project": "P2"}
            return None

        monkeypatch.setattr(app_module, "read_single", fake_read)
        headers = _user_headers("p1owner@dg.local", memberships={"P1": "owner"})
        for method in ("GET", "PUT", "DELETE"):
            kwargs = {"json": {"title": "x"}} if method == "PUT" else {}
            known = client.request(method, "/knowledge/note/note-p2", headers=headers, **kwargs)
            unknown = client.request(method, "/knowledge/note/note-none", headers=headers, **kwargs)
            assert known.status_code == unknown.status_code == 404, method
            assert known.json() == unknown.json(), method

    def test_execution_result_is_bound_to_the_user_who_started_it(self, client):
        app_module.record_execution_owner("exec-1", "alice@dg.local", "P1", "rules-ingest")
        app_module.EXECUTION_RESULTS["exec-1"] = {"status": "completed", "payload": {}}
        try:
            alice = _user_headers("alice@dg.local", memberships={"P1": "editor"})
            bob = _user_headers("bob@dg.local", memberships={"P1": "editor"})
            admin = _user_headers("root@dg.local", admin=True)
            mine = client.get("/execution-result/exec-1", headers=alice)
            assert mine.status_code == 200
            assert mine.json()["status"] == "completed"
            for headers in (bob, admin):
                other = client.get("/execution-result/exec-1", headers=headers)
                unknown = client.get("/execution-result/never-started", headers=headers)
                assert other.status_code == unknown.status_code == 404
                assert _code(other) == _code(unknown) == "EXECUTION_NOT_FOUND"
        finally:
            app_module.EXECUTION_RESULTS.pop("exec-1", None)

    def test_owned_execution_without_result_reports_running(self, client):
        app_module.record_execution_owner("exec-2", "alice@dg.local", "P1", None)
        alice = _user_headers("alice@dg.local", memberships={"P1": "viewer"})
        response = client.get("/execution-result/exec-2", headers=alice)
        assert response.status_code == 200
        assert response.json() == {"status": "running"}

    def test_owner_who_lost_membership_gets_404(self, client):
        app_module.record_execution_owner("exec-3", "alice@dg.local", "P1", None)
        headers = _user_headers("alice@dg.local")  # no membership in P1
        assert client.get("/execution-result/exec-3", headers=headers).status_code == 404

    def test_execution_owner_map_is_capped_and_evicts_oldest(self):
        for i in range(app_module.EXECUTION_OWNERS_CAP + 5):
            app_module.record_execution_owner(f"e{i}", "u@dg.local", "P1", None)
        assert len(app_module.EXECUTION_OWNERS) == app_module.EXECUTION_OWNERS_CAP
        assert "e0" not in app_module.EXECUTION_OWNERS
        assert f"e{app_module.EXECUTION_OWNERS_CAP + 4}" in app_module.EXECUTION_OWNERS

    def test_service_token_can_store_an_execution_result(self, client):
        response = client.post(
            "/execution-result",
            headers=auth_fixtures.service_headers(),
            json={"executionId": "exec-9", "status": "running"},
        )
        assert response.status_code == 200
        app_module.EXECUTION_RESULTS.pop("exec-9", None)
