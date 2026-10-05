"""Phase 1301 plan 09 (DGCL-03, DGCL-05, D-21): project-authorised Speckle geometry
proxy and a token-free ``/validation/view`` payload.

The Speckle server is an ``httpx.MockTransport`` injected through the module-level
``speckle_proxy._transport_factory``: no test opens a network connection or contacts a
real Speckle server. Credentials come from the 1205-08 fixtures (real sessions, a real
``dgd_`` delegated token); nothing is overridden. The Speckle read token used here is a
synthetic value that must never appear in any response, header, payload or log.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import company  # noqa: E402
import connectors  # noqa: E402
import speckle_proxy  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
ALICE = "alice@dg.local"
BOB = "bob@dg.local"
READ_TOKEN = "speckle-READ-token-SYNTHETIC-0123456789"
SPECKLE_URL = "http://speckle.internal:3000"
BOUND = "abcdef0123"          # Speckle project bound to DG project P1
OTHER = "0123456789"          # a Speckle project bound to nobody we can see
OBJ_BASE = "a" * 32
OBJ_VALID = "b" * 32
OBJ_CHILD = "c" * 32
PREFIX = "/data-service/speckle-proxy"

RUN = {
    "runId": "run-1",
    "speckleProjectId": BOUND,
    "baseModelId": "bm",
    "baseVersionId": "bv",
    "validationModelId": "vm",
    "validationVersionId": "vv",
    "baseResourceUrl": f"http://localhost:8090/projects/{BOUND}/models/bm@bv",
    "validationResourceUrl": f"http://localhost:8090/projects/{BOUND}/models/vm@vv",
    "modelViewerUrl": "http://localhost:8080/model-viewer/?project=P1&runId=run-1",
}


# -- upstream double ------------------------------------------------------------


class FakeSpeckle:
    """A network-free Speckle server. Counts every request."""

    def __init__(self, *, graphql_status=200, object_status=200, raises=None,
                 version_objects=None):
        self.graphql_status = graphql_status
        self.object_status = object_status
        self.raises = raises
        self.version_objects = version_objects or {"bv": OBJ_BASE, "vv": OBJ_VALID}
        self.requests: list[httpx.Request] = []

    def transport(self):
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.raises is not None:
            raise self.raises
        path = request.url.path
        if path == "/graphql":
            if self.graphql_status != 200:
                return httpx.Response(self.graphql_status, text="boom")
            variables = json.loads(request.content)["variables"]
            referenced = self.version_objects.get(variables["versionId"])
            if referenced is None:
                return httpx.Response(200, json={"data": {"project": {"model": {"version": None}}}})
            return httpx.Response(
                200, json={"data": {"project": {"model": {"version": {"referencedObject": referenced}}}}}
            )
        if self.object_status != 200:
            return httpx.Response(self.object_status, text="upstream says no")
        if request.method == "GET":
            return httpx.Response(200, headers={"content-type": "application/json"},
                                  content=b'{"id":"root","totalChildrenCount":1}')
        return httpx.Response(200, headers={"content-type": "text/plain"},
                              content=(OBJ_CHILD + '\t{"id":"' + OBJ_CHILD + '"}\n').encode())

    def object_requests(self):
        return [r for r in self.requests if r.url.path != "/graphql"]


# -- fixtures -------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setattr(app_module, "read_many", lambda *a, **k: [])
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)
    monkeypatch.setattr(app_module, "load_persisted_speckle_settings", lambda: {})
    monkeypatch.setenv("DG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SPECKLE_READ_TOKEN", READ_TOKEN)
    monkeypatch.setenv("SPECKLE_WRITE_TOKEN", "speckle-WRITE-token-SYNTHETIC")
    monkeypatch.setenv("SPECKLE_BASE_URL", "http://localhost:8090")
    monkeypatch.setenv("SPECKLE_INTERNAL_URL", SPECKLE_URL)
    monkeypatch.setattr(speckle_proxy, "_transport_factory", lambda: None)
    bindings = {"P1": BOUND}

    def fake_config(project):
        spid = bindings.get(project)
        return None if spid is None else app_module.SpeckleProjectConfigPayload(
            speckleProjectId=spid, baseModelId="bm"
        )

    monkeypatch.setattr(app_module, "get_integration_config", fake_config)
    company.set_project_company("P1", "Acme")
    company.set_project_company("P2", "Acme")


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def speckle(monkeypatch):
    fake = FakeSpeckle()
    monkeypatch.setattr(speckle_proxy, "_transport_factory", fake.transport)
    return fake


def _cookie(username=ALICE, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _delegated(client, project="P1", username=ALICE, role="viewer"):
    cookie = _cookie(username, memberships={project: role})
    response = client.post("/auth/delegated-token", json={"project": project}, headers=cookie)
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


def _member(project="P1", role="viewer"):
    return _cookie(ALICE, memberships={project: role})


def _get_url(spid=BOUND, oid=OBJ_VALID, project="P1", single=False):
    return f"/speckle-proxy/{project}/objects/{spid}/{oid}" + ("/single" if single else "")


def _stream_url(spid=BOUND, project="P1"):
    return f"/speckle-proxy/{project}/api/v2/projects/{spid}/object-stream/"


def _getobjects_url(spid=BOUND, project="P1"):
    return f"/speckle-proxy/{project}/api/getobjects/{spid}"


# -- the view payload carries no Speckle credential (D-21) --------------------------


def test_view_payload_has_no_token_key_and_no_speckle_host(speckle):
    user = auth.Principal(kind="user", username=ALICE)
    payload = app_module.build_view_payload("P1", RUN, {}, principal=user)
    assert not [k for k in _keys(payload) if "token" in k.lower()]
    assert "speckleBaseUrl" not in payload
    text = json.dumps(payload)
    assert READ_TOKEN not in text and "speckle-WRITE-token" not in text
    assert SPECKLE_URL not in text


def test_view_payload_resource_urls_point_at_the_dg_proxy(speckle):
    user = auth.Principal(kind="user", username=ALICE)
    payload = app_module.build_view_payload("P1", RUN, {}, principal=user)
    assert payload["viewerResources"] == [
        f"{PREFIX}/P1/objects/{BOUND}/{OBJ_BASE}",
        f"{PREFIX}/P1/objects/{BOUND}/{OBJ_VALID}",
    ]
    assert "viewerResourcesError" not in payload
    # Every resolution call carried the server-held token, never the write token.
    assert speckle.requests
    for request in speckle.requests:
        assert request.headers["authorization"] == f"Bearer {READ_TOKEN}"
        assert request.url.path == "/graphql"
        assert request.url.host == "speckle.internal"


def test_view_payload_source_never_names_a_read_token_key():
    source = inspect.getsource(app_module.build_view_payload)
    assert "readToken" not in source and "speckleBaseUrl" not in source
    # The setting may gate whether resolution is attempted; it is never placed in the dict.
    assert '"readToken"' not in source and "read_token," not in source


def test_view_payload_without_a_configured_read_token_has_no_resources_and_no_calls(speckle, monkeypatch):
    monkeypatch.delenv("SPECKLE_READ_TOKEN")
    user = auth.Principal(kind="user", username=ALICE)
    payload = app_module.build_view_payload("P1", RUN, {}, principal=user)
    assert payload["viewerResources"] == []
    assert payload["viewerResourcesError"] == "SPECKLE_NOT_CONFIGURED"
    assert speckle.requests == []


def test_view_payload_does_not_resolve_for_a_connector_or_unknown_caller(speckle):
    connector = auth.Principal(kind="connector", bound_project="P1", credential_id="c1")
    assert app_module.build_view_payload("P1", RUN, {}, principal=connector)["viewerResources"] == []
    assert app_module.build_view_payload("P1", RUN, {})["viewerResources"] == []
    assert speckle.requests == []


def test_view_payload_unbound_project_resolves_nothing(speckle):
    user = auth.Principal(kind="user", username=ALICE)
    payload = app_module.build_view_payload("P-none", RUN, {}, principal=user)
    assert payload["viewerResources"] == []
    assert payload["viewerResourcesError"] == "SPECKLE_PROJECT_UNBOUND"
    assert speckle.requests == []


def test_view_payload_run_in_a_foreign_speckle_project_resolves_nothing(speckle):
    user = auth.Principal(kind="user", username=ALICE)
    foreign = {**RUN, "speckleProjectId": OTHER}
    payload = app_module.build_view_payload("P1", foreign, {}, principal=user)
    assert payload["viewerResources"] == []
    assert payload["viewerResourcesError"] == "SPECKLE_PROJECT_FORBIDDEN"
    assert speckle.requests == []


@pytest.mark.parametrize("kwargs", [{"graphql_status": 500}, {"raises": httpx.ConnectError("down")}])
def test_view_payload_upstream_failure_is_named_and_leaks_nothing(monkeypatch, kwargs):
    fake = FakeSpeckle(**kwargs)
    monkeypatch.setattr(speckle_proxy, "_transport_factory", fake.transport)
    user = auth.Principal(kind="user", username=ALICE)
    payload = app_module.build_view_payload("P1", RUN, {}, principal=user)
    assert payload["viewerResources"] == []
    assert payload["viewerResourcesError"] == "SPECKLE_UPSTREAM_ERROR"
    assert READ_TOKEN not in json.dumps(payload)


def test_view_payload_rejects_a_referenced_object_that_is_not_a_hash(monkeypatch):
    fake = FakeSpeckle(version_objects={"bv": "../../graphql", "vv": OBJ_VALID})
    monkeypatch.setattr(speckle_proxy, "_transport_factory", fake.transport)
    user = auth.Principal(kind="user", username=ALICE)
    payload = app_module.build_view_payload("P1", RUN, {}, principal=user)
    assert payload["viewerResources"] == []
    assert payload["viewerResourcesError"] == "SPECKLE_UPSTREAM_ERROR"


def test_view_payload_skips_a_model_without_a_version(speckle):
    user = auth.Principal(kind="user", username=ALICE)
    run = {**RUN, "validationModelId": None, "validationVersionId": None}
    payload = app_module.build_view_payload("P1", run, {}, principal=user)
    assert payload["viewerResources"] == [f"{PREFIX}/P1/objects/{BOUND}/{OBJ_BASE}"]


def test_view_route_answers_without_any_token_field(client, speckle, monkeypatch):
    monkeypatch.setattr(app_module, "get_validation_run", lambda *a, **k: dict(RUN))
    monkeypatch.setattr(app_module, "get_validation_entity_sets", lambda *a, **k: {"failed": [], "passed": []})
    for url in ("/validation/view/P1", "/validation/view/P1/run-1", "/validation/view/P1/run-1/R_X"):
        response = client.get(url, headers=_member())
        assert response.status_code == 200, response.text
        body = response.json()
        assert not [k for k in _keys(body) if "token" in k.lower()]
        assert len(body["viewerResources"]) == 2
        assert READ_TOKEN not in response.text


# -- the object proxy -----------------------------------------------------------


def test_get_object_forwards_with_the_server_token_to_the_bound_project(client, speckle):
    response = client.get(_get_url(), headers=_member())
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["id"] == "root"
    (request,) = speckle.object_requests()
    assert request.method == "GET"
    assert request.url.path == f"/objects/{BOUND}/{OBJ_VALID}"
    assert request.url.host == "speckle.internal"
    assert request.headers["authorization"] == f"Bearer {READ_TOKEN}"


def test_get_object_single_variant_used_by_the_viewer_loader(client, speckle):
    response = client.get(_get_url(single=True), headers=_member())
    assert response.status_code == 200
    (request,) = speckle.object_requests()
    assert request.url.path == f"/objects/{BOUND}/{OBJ_VALID}/single"


def test_object_stream_post_forwards_ids_and_mask(client, speckle):
    mask = {"include": ["id", "speckle_type"]}
    response = client.post(_stream_url(), json={"objectIds": [OBJ_VALID, OBJ_CHILD], "attributeMask": mask},
                           headers=_member())
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.startswith(OBJ_CHILD + "\t")
    (request,) = speckle.object_requests()
    assert request.method == "POST"
    assert request.url.path == f"/api/v2/projects/{BOUND}/object-stream/"
    assert request.headers["authorization"] == f"Bearer {READ_TOKEN}"
    assert json.loads(request.content) == {"objectIds": [OBJ_VALID, OBJ_CHILD], "attributeMask": mask}


def test_getobjects_post_uses_the_legacy_wire_shape(client, speckle):
    response = client.post(_getobjects_url(), json={"objects": json.dumps([OBJ_VALID])}, headers=_member())
    assert response.status_code == 200, response.text
    (request,) = speckle.object_requests()
    assert request.url.path == f"/api/getobjects/{BOUND}"
    assert json.loads(json.loads(request.content)["objects"]) == [OBJ_VALID]


def test_client_credentials_are_never_forwarded_upstream(client, speckle):
    headers = {**_member(), "X-Forwarded-Token": "should-not-pass"}
    client.get(_get_url(), headers=headers)
    (request,) = speckle.object_requests()
    forwarded = {k.lower() for k in request.headers.keys()}
    assert "cookie" not in forwarded and "x-dg-csrf" not in forwarded
    assert "x-forwarded-token" not in forwarded
    assert request.headers["authorization"] == f"Bearer {READ_TOKEN}"


@pytest.mark.parametrize("call", ["get", "single", "stream", "getobjects"])
def test_mismatched_speckle_project_is_403_with_zero_upstream_calls(client, speckle, call):
    headers = _member()
    if call == "get":
        response = client.get(_get_url(spid=OTHER), headers=headers)
    elif call == "single":
        response = client.get(_get_url(spid=OTHER, single=True), headers=headers)
    elif call == "stream":
        response = client.post(_stream_url(OTHER), json={"objectIds": [OBJ_VALID]}, headers=headers)
    else:
        response = client.post(_getobjects_url(OTHER), json={"objects": json.dumps([OBJ_VALID])}, headers=headers)
    assert response.status_code == 403, response.text
    assert _code(response) == "SPECKLE_PROJECT_FORBIDDEN"
    assert speckle.requests == []


def test_a_project_bound_elsewhere_cannot_be_read_through_a_project_the_caller_belongs_to(client, speckle):
    # P2 has no binding at all: its member gets UNBOUND, never P1's geometry.
    headers = _member("P2")
    response = client.get(_get_url(project="P2"), headers=headers)
    assert response.status_code == 404 and _code(response) == "SPECKLE_PROJECT_UNBOUND"
    response = client.get(_get_url(spid=BOUND, project="P2"), headers=headers)
    assert response.status_code == 404
    assert speckle.requests == []


def test_non_member_is_403_and_nothing_is_contacted(client, speckle):
    headers = _cookie(BOB, memberships={"P2": "owner"})
    response = client.get(_get_url(), headers=headers)
    assert response.status_code == 403 and _code(response) == "PROJECT_FORBIDDEN"
    assert speckle.requests == []


def test_anonymous_is_401(client, speckle):
    assert client.get(_get_url()).status_code == 401
    assert client.post(_stream_url(), json={"objectIds": [OBJ_VALID]}, headers=CSRF).status_code == 401
    assert speckle.requests == []


def test_connector_and_service_principals_are_refused(client, speckle):
    connector = _bearer(auth_fixtures.connector_token_for("P1"))
    for headers in (connector, auth_fixtures.service_headers()):
        response = client.get(_get_url(), headers=headers)
        assert response.status_code == 403 and _code(response) == "PRINCIPAL_NOT_PERMITTED"
    assert speckle.requests == []


def test_post_with_a_cookie_session_requires_the_csrf_header(client, speckle):
    headers = {k: v for k, v in _member().items() if k != auth.CSRF_HEADER}
    response = client.post(_stream_url(), json={"objectIds": [OBJ_VALID]}, headers=headers)
    assert response.status_code == 403 and _code(response) == "CSRF_HEADER_REQUIRED"
    assert speckle.requests == []


def test_delegated_token_reads_its_own_project(client, speckle):
    token = _delegated(client, "P1")
    assert client.get(_get_url(), headers=_bearer(token)).status_code == 200
    posted = client.post(_stream_url(), json={"objectIds": [OBJ_VALID]}, headers=_bearer(token))
    assert posted.status_code == 200
    assert len(speckle.object_requests()) == 2


def test_delegated_token_for_another_project_is_403(client, speckle):
    token = _delegated(client, "P2")
    response = client.get(_get_url(project="P1"), headers=_bearer(token))
    assert response.status_code == 403 and _code(response) == "PROJECT_FORBIDDEN"
    assert speckle.requests == []


def test_delegated_token_cannot_reach_a_foreign_speckle_project(client, speckle):
    token = _delegated(client, "P1")
    response = client.get(_get_url(spid=OTHER), headers=_bearer(token))
    assert response.status_code == 403 and _code(response) == "SPECKLE_PROJECT_FORBIDDEN"
    assert speckle.requests == []


def test_logout_and_revoke_stop_further_object_reads(client, speckle):
    token = _delegated(client, "P1")
    assert client.get(_get_url(), headers=_bearer(token)).status_code == 200
    revoked = client.delete("/auth/delegated-token", headers=_bearer(token))
    assert revoked.status_code in (200, 204)
    calls_before = len(speckle.requests)
    response = client.get(_get_url(), headers=_bearer(token))
    assert response.status_code == 401
    assert len(speckle.requests) == calls_before


def test_session_logout_stops_a_delegated_token(client, speckle):
    cookie = _cookie(ALICE, memberships={"P1": "viewer"})
    token = client.post("/auth/delegated-token", json={"project": "P1"}, headers=cookie).json()["token"]
    assert client.get(_get_url(), headers=_bearer(token)).status_code == 200
    assert client.post("/auth/logout", headers=cookie).status_code in (200, 204)
    calls_before = len(speckle.requests)
    assert client.get(_get_url(), headers=_bearer(token)).status_code == 401
    assert len(speckle.requests) == calls_before


@pytest.mark.parametrize("bad", ["../graphql", "A" * 32, "b" * 31, "b" * 33, "zz" + "b" * 30, "b" * 32 + "x", "%2e%2e"])
def test_object_ids_must_be_speckle_hashes(client, speckle, bad):
    response = client.get(f"/speckle-proxy/P1/objects/{BOUND}/{bad}", headers=_member())
    assert response.status_code in (404, 422), response.text
    if response.status_code == 422:
        assert _code(response) == "SPECKLE_OBJECT_ID_INVALID"
    assert speckle.requests == []


@pytest.mark.parametrize(
    "body",
    [
        {"objectIds": [OBJ_VALID, "not-a-hash"]},
        {"objectIds": "nope"},
        {"objectIds": [123]},
        {"objectIds": []},
        {"other": 1},
        ["list"],
    ],
)
def test_object_stream_body_ids_are_validated(client, speckle, body):
    response = client.post(_stream_url(), json=body, headers=_member())
    assert response.status_code == 422, response.text
    assert _code(response) == "SPECKLE_OBJECT_ID_INVALID"
    assert speckle.requests == []


def test_object_stream_rejects_a_non_object_attribute_mask(client, speckle):
    response = client.post(_stream_url(), json={"objectIds": [OBJ_VALID], "attributeMask": "x"}, headers=_member())
    assert response.status_code == 422
    assert speckle.requests == []


def test_object_stream_body_that_is_not_json_is_422(client, speckle):
    response = client.post(_stream_url(), content=b"{not json", headers={**_member(), "Content-Type": "application/json"})
    assert response.status_code == 422
    assert speckle.requests == []


def test_oversized_object_stream_body_is_413(client, speckle, monkeypatch):
    monkeypatch.setattr(speckle_proxy, "MAX_BODY_BYTES", 64)
    response = client.post(_stream_url(), json={"objectIds": [OBJ_VALID] * 10}, headers=_member())
    assert response.status_code == 413 and _code(response) == "SPECKLE_BODY_TOO_LARGE"
    assert speckle.requests == []


def test_too_many_ids_in_one_request_is_422(client, speckle, monkeypatch):
    monkeypatch.setattr(speckle_proxy, "MAX_OBJECT_IDS", 2)
    response = client.post(_stream_url(), json={"objectIds": [OBJ_VALID, OBJ_CHILD, OBJ_BASE]}, headers=_member())
    assert response.status_code == 422
    assert speckle.requests == []


@pytest.mark.parametrize("kwargs", [{"object_status": 404}, {"object_status": 500}, {"object_status": 401},
                                    {"raises": httpx.ConnectError("down")},
                                    {"raises": httpx.ReadTimeout("slow")}])
def test_upstream_errors_map_to_502_and_leak_nothing(client, monkeypatch, kwargs):
    fake = FakeSpeckle(**kwargs)
    monkeypatch.setattr(speckle_proxy, "_transport_factory", fake.transport)
    response = client.get(_get_url(), headers=_member())
    assert response.status_code == 502, response.text
    assert _code(response) == "SPECKLE_UPSTREAM_ERROR"
    assert READ_TOKEN not in response.text and "upstream says no" not in response.text
    assert READ_TOKEN not in json.dumps(dict(response.headers))


def test_upstream_redirect_is_not_followed(client, monkeypatch):
    class Redirecting(FakeSpeckle):
        def _handle(self, request):
            self.requests.append(request)
            return httpx.Response(302, headers={"location": "http://evil.example/steal"})

    fake = Redirecting()
    monkeypatch.setattr(speckle_proxy, "_transport_factory", fake.transport)
    response = client.get(_get_url(), headers=_member())
    assert response.status_code == 502
    assert len(fake.requests) == 1


def test_unconfigured_read_token_is_503_before_any_upstream_call(client, speckle, monkeypatch):
    monkeypatch.delenv("SPECKLE_READ_TOKEN")
    response = client.get(_get_url(), headers=_member())
    assert response.status_code == 503 and _code(response) == "SPECKLE_NOT_CONFIGURED"
    assert speckle.requests == []


def test_the_read_token_is_never_logged(client, speckle, caplog, monkeypatch):
    with caplog.at_level(logging.DEBUG):
        client.get(_get_url(), headers=_member())
        client.get(_get_url(spid=OTHER), headers=_member())
        bad = FakeSpeckle(object_status=500)
        monkeypatch.setattr(speckle_proxy, "_transport_factory", bad.transport)
        client.get(_get_url(), headers=_member())
    assert READ_TOKEN not in caplog.text


def test_the_stream_is_closed_after_the_response(client, speckle):
    # TestClient reads the whole body; a second request must still work, proving the
    # per-request upstream client does not leak state between calls.
    assert client.get(_get_url(), headers=_member()).status_code == 200
    assert client.get(_get_url(single=True), headers=_member()).status_code == 200


def test_module_exports_the_planned_entry_points():
    assert callable(speckle_proxy.resolve_view_resources)
    assert callable(speckle_proxy.proxy_objects)
    assert speckle_proxy.OBJECT_ID_PATTERN.pattern == r"^[0-9a-f]{32}$"
