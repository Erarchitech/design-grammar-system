"""D-15 cross-project matrix (Phase 1205 plan 17, ALGN12-20, GATE12-05;
D-15, D-18, D-19, D-20).

A two-project, several-principal fixture drives every ``ROUTE_POLICIES`` row
whose project comes from the path, the body or the query, and proves the
tenancy boundary fails closed:

* an editor of P1 asking for P2 -> 403 ``PROJECT_FORBIDDEN``;
* a connector token bound to P1 asking for P2 -> 403 (``PROJECT_FORBIDDEN``
  on connector-permitted rows, ``PRINCIPAL_NOT_PERMITTED`` elsewhere);
* a viewer (or an editor on an owner row) on a P1 row above their role -> 403;
* a body/query project that disagrees with the path project -> 403
  ``PROJECT_MISMATCH``;
* positive controls (the right principal passes the real dependency) keep the
  matrix from passing vacuously;
* id-only resources (credential, note) and owner-bound executions answer the
  same 404 for another project's resource, and never side-effect;
* the two listing routes (``GET /projects``, ``GET /connectors``) only ever
  show the caller's own projects.

The matrix is generated from ``route_policy.ROUTE_POLICIES`` at collection
time, so a new project-scoped row is covered without touching this file. Every
case runs under ``DG_DEPLOYMENT=local`` and ``=multi-user`` (D-18/D-19) and
must produce identical outcomes.

No bypass (D-20): principals are minted through the real auth store and the
connectors API; requests carry real cookies / Bearer tokens; the dependency
under test is never overridden. Positive controls call
``auth.require_principal`` directly on a constructed ASGI request, so no
handler and no Neo4j is involved.

Flagged assumption (ALGN12-20, unclassified edge): a route whose project
cannot be expressed as path/body/query/resource is covered only by the
dedicated resource, execution, ``GET /projects`` and ``GET /connectors`` cases
here plus the 1205-10 sweeps. A future route of a *new shape* is caught by the
route-inventory completeness test, not by this matrix.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from types import SimpleNamespace
from urllib.parse import urlencode

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

P1 = "P1"
P2 = "P2"
CSRF = {auth.CSRF_HEADER: "1"}
_BODY_METHODS = {"POST", "PUT", "DELETE"}
_SCOPED_SOURCES = ("path", "body", "query")


# ── generated matrix ────────────────────────────────────────────────────────


def _scoped_rows() -> list[tuple[tuple[str, str], route_policy.RoutePolicy]]:
    return sorted(
        (
            (key, policy)
            for key, policy in route_policy.ROUTE_POLICIES.items()
            if policy.project_source in _SCOPED_SOURCES
        ),
        key=lambda kv: kv[0],
    )


def _url(template: str, project: str) -> str:
    return re.sub(
        r"\{([^}]+)\}", lambda m: project if m.group(1) == "project" else "x", template
    )


def _path_params(template: str, project: str) -> dict[str, str]:
    return {
        name: (project if name == "project" else "x")
        for name in re.findall(r"\{([^}]+)\}", template)
    }


def _placement(key, policy, *, project: str | None = None, **extra):
    """Return ``(url, params, body)`` placing ``project`` in the row's declared
    source only. ``extra`` may set ``query`` / ``body`` (a project value put in
    that *additional* location) and ``path`` (path project override)."""
    method, template = key
    source = policy.project_source
    path_project = extra.get("path", project if source == "path" else P1)
    url = _url(template, path_project)
    params: dict[str, str] = {}
    body: dict | None = {} if method in _BODY_METHODS else None
    if source == "query" and project is not None:
        params["project"] = project
    if source == "body" and project is not None:
        body = {"project": project}
    if "query" in extra:
        params["project"] = extra["query"]
    if "body" in extra and body is not None:
        body = {**body, "project": extra["body"]}
    return url, params, body


def _mismatch_variants(key, policy) -> list[str]:
    """Which second location can carry a disagreeing project for this row."""
    method, _template = key
    has_body = method in _BODY_METHODS
    source = policy.project_source
    if source == "path":
        return ["query"] + (["body"] if has_body else [])
    if source == "query":
        return ["body"] if has_body else []
    return ["query"]  # body-sourced (always a body method)


def _mismatch_placement(key, policy, variant: str):
    """P1 in the declared source, P2 in the ``variant`` location."""
    source = policy.project_source
    if source == "path":
        return _placement(key, policy, project=P1, **{variant: P2})
    if source == "query":
        return _placement(key, policy, project=P1, body=P2)
    return _placement(key, policy, project=P1, query=P2)


def _matrix_cases() -> list[tuple]:
    """(category, key, policy, actor, extra) for every scoped row."""
    cases: list[tuple] = []
    for key, policy in _scoped_rows():
        cases.append(("forbidden", key, policy, "A", P2))
        cases.append(("connector", key, policy, "T1", P2))
        if policy.min_role in ("editor", "owner"):
            cases.append(("downgrade", key, policy, "V", P1))
        if policy.min_role == "owner":
            cases.append(("downgrade", key, policy, "A", P1))
        for variant in _mismatch_variants(key, policy):
            cases.append(("mismatch", key, policy, "A", variant))
        # positive controls
        if policy.min_role in ("viewer", "editor"):
            cases.append(("positive", key, policy, "A", P1))
            cases.append(("positive", key, policy, "B2", P2))
        if policy.min_role == "viewer":
            cases.append(("positive", key, policy, "V", P1))
        cases.append(("positive", key, policy, "B", P2))
        if route_policy.PRINCIPAL_CONNECTOR in policy.principals:
            cases.append(("positive", key, policy, "T1", P1))
    return cases


MATRIX_CASES = _matrix_cases()


def _case_id(case) -> str:
    category, key, _policy, actor, extra = case
    return f"{category}: {key[0]} {key[1]} -> {actor}/{extra}"


def _cases(category: str):
    return [
        pytest.param(*case, id=_case_id(case))
        for case in MATRIX_CASES
        if case[0] == category
    ]


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """Real stores in a temp dir (scrypt hashing is slow, so built once per
    module): A editor of P1, V viewer of P1, B owner of P2, B2 editor of P2, an
    admin, and a connector credential bound to P1 (T1)."""
    mp = pytest.MonkeyPatch()
    store = tmp_path_factory.mktemp("matrix-auth")
    mp.setattr(auth, "USERS_FILE", store / "auth-users.json")
    mp.setattr(auth, "SESSIONS_FILE", store / "auth-sessions.json")
    mp.setattr(auth, "MEMBERSHIPS_FILE", store / "auth-memberships.json")
    mp.setattr(auth, "INVITES_FILE", store / "auth-invites.json")
    mp.setattr(connectors, "CREDENTIALS_FILE", store / "connector-credentials.json")

    names = {
        "A": "matrix-a@dg.local",
        "V": "matrix-v@dg.local",
        "B": "matrix-b@dg.local",
        "B2": "matrix-b2@dg.local",
        "ADMIN": "matrix-admin@dg.local",
    }
    auth_fixtures.make_user(names["A"], memberships={P1: "editor"})
    auth_fixtures.make_user(names["V"], memberships={P1: "viewer"})
    auth_fixtures.make_user(names["B"], memberships={P2: "owner"})
    auth_fixtures.make_user(names["B2"], memberships={P2: "editor"})
    auth_fixtures.make_user(names["ADMIN"], is_admin=True)

    headers: dict[str, dict[str, str]] = {}
    for actor, username in names.items():
        token = auth_fixtures.session_cookie_for(username)
        headers[actor] = {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}

    t1_record, t1_token = connectors.create_credential("grasshopper", project=P1)
    headers["T1"] = {"Authorization": f"Bearer {t1_token}"}
    headers["SERVICE"] = auth_fixtures.service_headers()

    yield SimpleNamespace(
        names=names, headers=headers, t1_credential_id=t1_record["credential_id"]
    )
    mp.undo()


@pytest.fixture(autouse=True)
def _offline_graph(monkeypatch):
    """No test here may reach Neo4j: denials stop in the dependency, resolvers
    read an empty graph unless a test patches them, executions start empty."""
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)
    monkeypatch.setattr(app_module, "EXECUTION_OWNERS", {})


@pytest.fixture(params=["local", "multi-user"])
def profile(request, monkeypatch):
    """D-18/D-19: every case passes, identically, under both profiles."""
    monkeypatch.setenv("DG_DEPLOYMENT", request.param)
    return request.param


@pytest.fixture
def client(profile):
    return TestClient(app, raise_server_exceptions=False)


def _code(response) -> str | None:
    try:
        detail = response.json().get("detail")
    except Exception:
        return None
    return detail.get("code") if isinstance(detail, dict) else None


def _send(client, world, key, actor, url, params, body):
    kwargs: dict = {"headers": world.headers[actor]}
    if params:
        kwargs["params"] = params
    if body is not None:
        kwargs["json"] = body
    return client.request(key[0], url, **kwargs)


# ── the dependency called directly (positive controls) ──────────────────────


def _route_for(method: str, template: str):
    """The registered route object for ``(method, template)``. Falls back to a
    path-only stand-in (``require_principal`` reads only ``route.path``) when a
    FastAPI release exposes included routes with a router-relative path."""
    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path == template and method in route.methods:
                return route
        elif hasattr(route, "effective_route_contexts"):
            for ctx in route.effective_route_contexts():
                if ctx.path == template and method in ctx.methods:
                    for candidate in (ctx.starlette_route, ctx.original_route):
                        if getattr(candidate, "path", None) == template:
                            return candidate
                    return SimpleNamespace(path=template)
    raise AssertionError(f"no registered route for {method} {template}")


def _call_dependency(route, headers, path_params, query, body):
    """Await ``auth.require_principal`` on a constructed ASGI request. Returns
    ``(principal, request)``; raises whatever the dependency raises."""
    from starlette.requests import Request

    method, template = route
    payload = json.dumps(body).encode() if body is not None else b""

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "scheme": "http",
        "server": ("testserver", 80),
        "path": template,
        "raw_path": template.encode(),
        "root_path": "",
        "path_params": path_params,
        "query_string": urlencode(query).encode(),
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "route": _route_for(method, template),
    }
    request = Request(scope, receive)
    principal = asyncio.run(auth.require_principal(request))
    return principal, request


# ── Task 1: path/body/query matrix ──────────────────────────────────────────


def test_matrix_is_not_vacuous():
    """T-1205-17-03: the generated matrix really covers every scoped row."""
    scoped = _scoped_rows()
    assert len(scoped) >= 40, len(scoped)
    assert len(MATRIX_CASES) >= len(scoped)
    by_category: dict[str, set] = {}
    for category, key, _policy, _actor, _extra in MATRIX_CASES:
        by_category.setdefault(category, set()).add(key)
    scoped_keys = {key for key, _ in scoped}
    for category in ("forbidden", "connector", "positive"):
        assert by_category.get(category) == scoped_keys, category
    assert by_category.get("mismatch"), "no mismatch cases generated"
    assert by_category.get("downgrade"), "no role-downgrade cases generated"
    # 2 denials + at least 1 positive control per row
    assert len(MATRIX_CASES) >= 3 * len(scoped)
    # every row is one the member dependency can authorise
    for _key, policy in scoped:
        assert route_policy.PRINCIPAL_MEMBER in policy.principals
        assert policy.min_role in ("viewer", "editor", "owner")


@pytest.mark.parametrize("category,key,policy,actor,other", _cases("forbidden"))
def test_editor_of_p1_asking_for_p2_is_project_forbidden(
    client, world, category, key, policy, actor, other
):
    url, params, body = _placement(key, policy, project=other)
    response = _send(client, world, key, actor, url, params, body)
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize("category,key,policy,actor,other", _cases("connector"))
def test_p1_connector_asking_for_p2_is_denied(
    client, world, category, key, policy, actor, other
):
    url, params, body = _placement(key, policy, project=other)
    response = _send(client, world, key, actor, url, params, body)
    assert response.status_code == 403, (key, response.status_code, response.text)
    expected = (
        "PROJECT_FORBIDDEN"
        if route_policy.PRINCIPAL_CONNECTOR in policy.principals
        else "PRINCIPAL_NOT_PERMITTED"
    )
    assert _code(response) == expected


@pytest.mark.parametrize("category,key,policy,actor,other", _cases("downgrade"))
def test_role_below_the_route_minimum_is_project_forbidden(
    client, world, category, key, policy, actor, other
):
    url, params, body = _placement(key, policy, project=other)
    response = _send(client, world, key, actor, url, params, body)
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize("category,key,policy,actor,variant", _cases("mismatch"))
def test_disagreeing_project_locations_are_project_mismatch(
    client, world, category, key, policy, actor, variant
):
    url, params, body = _mismatch_placement(key, policy, variant)
    response = _send(client, world, key, actor, url, params, body)
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PROJECT_MISMATCH"


@pytest.mark.parametrize("category,key,policy,actor,project", _cases("positive"))
def test_positive_control_the_right_principal_passes_the_dependency(
    profile, world, category, key, policy, actor, project
):
    """Without these the denial cases could all pass because *everything* is
    denied. Each control calls the real dependency directly."""
    method, template = key
    _url_unused, params, body = _placement(key, policy, project=project)
    path_project = project if policy.project_source == "path" else P1
    principal, request = _call_dependency(
        key,
        world.headers[actor],
        _path_params(template, path_project),
        params,
        body,
    )
    assert request.state.project == project
    assert request.state.principal is principal
    if actor == "T1":
        assert principal.kind == "connector"
        assert principal.bound_project == project
    else:
        assert principal.kind == "user"
        assert principal.username == world.names[actor]


# ── Task 2: id-only resources ───────────────────────────────────────────────


class TestResourceBola:
    """Credential and note ids carry no project; another project's resource
    answers the same 404 as an unknown one, and nothing is changed."""

    def test_p2_credential_is_404_to_a_p1_editor_and_stays_unrevoked(self, client, world):
        record, _token = connectors.create_credential("grasshopper", project=P2)
        cred_id = record["credential_id"]
        route = f"/connectors/grasshopper/credentials/{cred_id}"
        known = client.delete(route, headers=world.headers["A"])
        unknown = client.delete(
            "/connectors/grasshopper/credentials/does-not-exist",
            headers=world.headers["A"],
        )
        assert known.status_code == unknown.status_code == 404
        assert _code(known) == _code(unknown) == "CREDENTIAL_NOT_FOUND"
        assert known.json() == unknown.json()
        stored = {r["credential_id"]: r for r in connectors.load_credentials()}
        assert not stored[cred_id].get("revoked")
        # V (viewer of P1) and T1 fare no better
        assert client.delete(route, headers=world.headers["V"]).status_code == 404
        assert not {
            r["credential_id"]: r for r in connectors.load_credentials()
        }[cred_id].get("revoked")

    def test_p2_owner_can_revoke_the_p2_credential(self, client, world):
        record, _token = connectors.create_credential("grasshopper", project=P2)
        cred_id = record["credential_id"]
        response = client.delete(
            f"/connectors/grasshopper/credentials/{cred_id}",
            headers=world.headers["B"],
        )
        assert response.status_code == 204
        stored = {r["credential_id"]: r for r in connectors.load_credentials()}
        assert stored[cred_id].get("revoked")

    def test_p1_connector_token_cannot_revoke_any_credential(self, client, world):
        record, _token = connectors.create_credential("grasshopper", project=P2)
        response = client.delete(
            f"/connectors/grasshopper/credentials/{record['credential_id']}",
            headers=world.headers["T1"],
        )
        assert response.status_code == 403
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"

    def test_p2_note_is_404_to_a_p1_editor_identical_to_unknown(
        self, client, world, monkeypatch
    ):
        reads: list[str] = []
        writes: list[str] = []

        def fake_read(query, params=None):
            reads.append(query)
            if params and params.get("noteId") == "note-p2":
                return {"project": P2}
            return None

        monkeypatch.setattr(app_module, "read_single", fake_read)
        monkeypatch.setattr(
            app_module, "write_query", lambda q, p=None, *a, **k: writes.append(q)
        )
        for actor in ("A", "V"):
            for method in ("GET", "PUT", "DELETE"):
                kwargs = {"json": {"title": "x"}} if method == "PUT" else {}
                known = client.request(
                    method, "/knowledge/note/note-p2", headers=world.headers[actor], **kwargs
                )
                unknown = client.request(
                    method, "/knowledge/note/note-none", headers=world.headers[actor], **kwargs
                )
                assert known.status_code == unknown.status_code == 404, (actor, method)
                assert known.json() == unknown.json(), (actor, method)
        # only the resolver ever read; no handler ran and nothing was written
        assert reads and all("n.project AS project" in q for q in reads)
        assert writes == []

    @pytest.mark.parametrize(
        "method,actor",
        [("GET", "B"), ("GET", "B2"), ("PUT", "B"), ("PUT", "B2"), ("DELETE", "B")],
    )
    def test_p2_members_pass_the_note_dependency(self, world, monkeypatch, method, actor):
        monkeypatch.setattr(
            app_module,
            "read_single",
            lambda query, params=None: {"project": P2} if params.get("noteId") == "note-p2" else None,
        )
        principal, request = _call_dependency(
            (method, "/knowledge/note/{note_id}"),
            world.headers[actor],
            {"note_id": "note-p2"},
            {},
            {"title": "x"} if method == "PUT" else None,
        )
        assert request.state.project == P2
        assert principal.username == world.names[actor]

    def test_viewer_of_the_notes_project_cannot_write_it(self, client, world, monkeypatch):
        """Same project, role below the route minimum -> the resource's 404."""
        monkeypatch.setattr(
            app_module,
            "read_single",
            lambda query, params=None: {"project": P1} if params.get("noteId") == "note-p1" else None,
        )
        response = client.request(
            "DELETE", "/knowledge/note/note-p1", headers=world.headers["V"]
        )
        assert response.status_code == 404


# ── Task 2: owner-bound executions ──────────────────────────────────────────


class TestExecutionOwnerBinding:
    def test_only_the_initiator_reads_the_execution(self, client, world):
        app_module.record_execution_owner(
            "exec-b", world.names["B"], P2, "rules-ingest"
        )
        unknown = client.get("/execution-result/never-started", headers=world.headers["A"])
        assert unknown.status_code == 404
        for actor in ("A", "V", "B2", "ADMIN"):
            other = client.get("/execution-result/exec-b", headers=world.headers[actor])
            assert other.status_code == 404, actor
            assert _code(other) == "EXECUTION_NOT_FOUND", actor
            assert other.json() == unknown.json(), actor
        mine = client.get("/execution-result/exec-b", headers=world.headers["B"])
        assert mine.status_code == 200
        assert mine.json() == {"status": "running"}

    def test_a_result_is_never_served_to_a_same_project_member(self, client, world):
        app_module.record_execution_owner(
            "exec-b2", world.names["B"], P2, "graph-query"
        )
        app_module.EXECUTION_RESULTS["exec-b2"] = {"status": "completed", "payload": {"k": 1}}
        try:
            denied = client.get("/execution-result/exec-b2", headers=world.headers["B2"])
            assert denied.status_code == 404
            assert "payload" not in denied.text
            served = client.get("/execution-result/exec-b2", headers=world.headers["B"])
            assert served.status_code == 200
            assert served.json()["status"] == "completed"
        finally:
            app_module.EXECUTION_RESULTS.pop("exec-b2", None)

    def test_the_initiator_passes_the_dependency_directly(self, world):
        app_module.record_execution_owner(
            "exec-b3", world.names["B"], P2, "rules-ingest"
        )
        principal, request = _call_dependency(
            ("GET", "/execution-result/{execution_id}"),
            world.headers["B"],
            {"execution_id": "exec-b3"},
            {},
            None,
        )
        assert request.state.project == P2
        assert principal.username == world.names["B"]


# ── Task 2: principal cross-checks (every row) ──────────────────────────────


def _all_rows():
    return sorted(route_policy.ROUTE_POLICIES.items(), key=lambda kv: kv[0])


def _rows(pred):
    return [
        pytest.param(key, policy, id=f"{key[0]} {key[1]}")
        for key, policy in _all_rows()
        if pred(policy)
    ]


def _plain_request(key, policy):
    method, template = key
    params = {"project": P1} if policy.project_source == "query" else {}
    body = None
    if method in _BODY_METHODS:
        body = {"project": P1}
    return _url(template, P1), params, body


@pytest.mark.parametrize(
    "key,policy",
    _rows(
        lambda p: route_policy.PRINCIPAL_PUBLIC not in p.principals
        and route_policy.PRINCIPAL_SERVICE not in p.principals
        and route_policy.PRINCIPAL_CONNECTOR_SELF not in p.principals
    ),
)
def test_service_token_on_a_user_route_is_403(client, world, key, policy):
    url, params, body = _plain_request(key, policy)
    response = _send(client, world, key, "SERVICE", url, params, body)
    assert response.status_code == 403, (key, response.status_code, response.text)
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


@pytest.mark.parametrize(
    "key,policy", _rows(lambda p: route_policy.PRINCIPAL_SERVICE in p.principals)
)
def test_user_session_on_a_service_route_is_403(client, world, key, policy):
    url, params, body = _plain_request(key, policy)
    for actor in ("A", "ADMIN"):
        response = _send(client, world, key, actor, url, params, body)
        assert response.status_code == 403, (key, actor, response.status_code)
        assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


# ── Task 2: listing filters ─────────────────────────────────────────────────


class TestListingFilters:
    def test_projects_lists_only_the_callers_projects(self, client, world, monkeypatch):
        seen: list = []

        def fake_read_many(query, params=None):
            seen.append(params)
            return [
                {"project": name, "nodes": 3}
                for name in (params or {}).get("projects") or [P1, P2]
            ]

        monkeypatch.setattr(app_module, "read_many", fake_read_many)
        for actor, expected in (("A", P1), ("V", P1), ("B", P2), ("B2", P2)):
            body = client.get("/projects", headers=world.headers[actor]).json()
            assert [p["project"] for p in body["projects"]] == [expected], actor
        # the graph query itself was restricted to the caller's projects
        assert [p["projects"] for p in seen] == [[P1], [P1], [P2], [P2]]

    def test_connectors_lists_no_credential_of_another_project(self, client, world):
        record, _token = connectors.create_credential("grasshopper", project=P2)
        p2_ids = {
            r["credential_id"]
            for r in connectors.load_credentials()
            if r.get("project") == P2
        }
        assert record["credential_id"] in p2_ids

        def listed(actor):
            body = client.get("/connectors", headers=world.headers[actor]).json()
            return {
                c["credential_id"]
                for connector in body["connectors"]
                for c in connector["credentials"]
            }

        a_listed = listed("A")
        assert world.t1_credential_id in a_listed  # positive control
        assert a_listed.isdisjoint(p2_ids)
        b_listed = listed("B")
        assert p2_ids <= b_listed
        assert world.t1_credential_id not in b_listed
