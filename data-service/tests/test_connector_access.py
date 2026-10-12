"""Phase 1301 plan 40 (D-46, DGCL-05, DGCL-06): per-connector access requests.

A project viewer asks for access to a connector (Grasshopper, Revit, ...); the
owner or an admin approves it under the connector's «Pending requests»; the
approved member can then sign in with that connector. Owner and admin need no
grant (Phase 1308, D-29); editor and viewer do. Connector-token creation is
retired (D-31): the credentials POST answers 410 for everyone, and the grant is
exercised through ``POST /auth/connector-session``. Every request goes through
the real ``require_principal``; credentials come from the 1205-08 fixtures.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connector_access  # noqa: E402
import connectors  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
ALICE = "alice@dg.local"  # viewer of P1 and P2
BOB = "bob@dg.local"  # member of nothing
OLGA = "olga@dg.local"  # owner of P1
ZED = "zed@dg.local"  # owner of P2
ERIC = "eric@dg.local"  # editor of P1
ROOT = "root@dg.local"  # admin, member of nothing


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
def client(request, monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", request.param)
    return TestClient(app, raise_server_exceptions=False)


def _session(username, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


@pytest.fixture
def world(client):
    return {
        "alice": _session(ALICE, memberships={"P1": "viewer", "P2": "viewer"}),
        "olga": _session(OLGA, memberships={"P1": "owner"}),
        "zed": _session(ZED, memberships={"P2": "owner"}),
        "eric": _session(ERIC, memberships={"P1": "editor"}),
        "bob": _session(BOB),
        "root": _session(ROOT, admin=True),
    }


def _request(client, cookie, project="P1", connector="grasshopper", note=None):
    body = {"project": project, "connector_id": connector}
    if note is not None:
        body["note"] = note
    return client.post("/connector-access-requests", json=body, headers=cookie)


def _issue(client, cookie, project="P1", username=ALICE, connector="grasshopper"):
    return client.post(
        f"/projects/{project}/connector-access",
        json={"username": username, "connector_id": connector},
        headers=cookie,
    )


def _credential(client, cookie, project="P1", connector="grasshopper"):
    return client.post(
        f"/connectors/{connector}/credentials",
        json={"project": project, "label": "seat"},
        headers=cookie,
    )


def _connector_session_for(client, cookie, project="P1", connector="grasshopper"):
    response = client.post(
        "/auth/connector-session",
        json={"project": project, "connector_id": connector},
        headers=cookie,
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _access_file():
    return auth.MEMBERSHIPS_FILE.parent / connector_access.FILE_NAME


def _stored():
    return json.loads(_access_file().read_text(encoding="utf-8"))


# -- the D-46 flow ----------------------------------------------------------


def test_viewer_requests_owner_approves_viewer_signs_in(client, world):
    sent = _request(client, world["alice"], note="need it for the model")
    assert sent.status_code == 201, sent.text
    assert sent.json()["connector_id"] == "grasshopper"
    assert sent.json()["username"] == ALICE

    listed = client.get("/projects/P1/connector-access", headers=world["olga"])
    assert listed.status_code == 200
    body = listed.json()
    assert body["grants"] == []
    assert [r["username"] for r in body["requests"]] == [ALICE]
    assert body["requests"][0]["connector_id"] == "grasshopper"
    assert body["requests"][0]["note"] == "need it for the model"

    issued = _issue(client, world["olga"])
    assert issued.status_code == 201, issued.text
    assert issued.json()["issued_by"] == OLGA

    after = client.get("/projects/P1/connector-access", headers=world["olga"]).json()
    assert after["requests"] == []
    assert [g["username"] for g in after["grants"]] == [ALICE]

    # D-31: the credentials POST is a tombstone for everyone, grant or not.
    created = _credential(client, world["alice"])
    assert created.status_code == 410, created.text
    assert _code(created) == "CONNECTOR_TOKENS_RETIRED"
    assert "token" not in created.json()

    # the grant opens the connector sign-in instead
    assert _connector_session_for(client, world["alice"]).startswith("dgk_")

    again = _request(client, world["alice"])
    assert again.status_code == 409
    assert _code(again) == "ACCESS_EXISTS"


def test_a_viewer_without_access_gets_410_and_no_credential(client, world):
    response = _credential(client, world["alice"])
    assert response.status_code == 410
    assert _code(response) == "CONNECTOR_TOKENS_RETIRED"
    assert connectors.load_credentials() == []


def test_access_is_per_connector(client, world):
    assert _issue(client, world["olga"], connector="grasshopper").status_code == 201
    other = client.post(
        "/auth/connector-session",
        json={"project": "P1", "connector_id": "revit"},
        headers=world["alice"],
    )
    assert other.status_code == 403
    assert _code(other) == "CONNECTOR_ACCESS_REQUIRED"


def test_the_credentials_post_is_410_for_every_role(client, world):
    for who in ("olga", "eric", "alice", "root"):
        response = _credential(client, world[who])
        assert response.status_code == 410, who
        assert _code(response) == "CONNECTOR_TOKENS_RETIRED", who
    assert connectors.load_credentials() == []


def test_owner_and_admin_sign_in_without_a_request_editor_needs_a_grant(client, world):
    assert _connector_session_for(client, world["olga"]).startswith("dgk_")
    assert _connector_session_for(client, world["root"]).startswith("dgk_")
    denied = client.post(
        "/auth/connector-session",
        json={"project": "P1", "connector_id": "grasshopper"},
        headers=world["eric"],
    )
    assert denied.status_code == 403
    assert _code(denied) == "CONNECTOR_ACCESS_REQUIRED"
    assert _issue(client, world["olga"], username=ERIC).status_code == 201
    assert _connector_session_for(client, world["eric"]).startswith("dgk_")


def test_editor_without_a_grant_can_request_access(client, world):
    """Phase 1308 D-29: an editor is no longer exempt; it asks like a viewer."""
    response = _request(client, world["eric"], note="need the add-in")
    assert response.status_code == 201, response.text
    assert response.json()["username"] == ERIC
    assert response.json()["connector_id"] == "grasshopper"
    pending = client.get("/projects/P1/connector-access", headers=world["olga"]).json()["requests"]
    assert [r["username"] for r in pending] == [ERIC]


def test_owner_and_admin_request_is_access_exists(client, world):
    for who in ("olga", "root"):
        response = _request(client, world[who])
        assert response.status_code == 409, who
        assert _code(response) == "ACCESS_EXISTS", who
    assert not _access_file().exists()


def test_editor_with_an_active_grant_request_is_access_exists(client, world):
    assert _issue(client, world["olga"], username=ERIC).status_code == 201
    response = _request(client, world["eric"])
    assert response.status_code == 409
    assert _code(response) == "ACCESS_EXISTS"


def test_admin_request_for_an_unknown_connector_is_404_not_exists(client, world):
    response = _request(client, world["root"], connector="sketchup")
    assert response.status_code == 404
    assert _code(response) == "CONNECTOR_NOT_FOUND"


def test_owner_revoke_ends_the_access(client, world):
    access_id = _issue(client, world["olga"]).json()["access_id"]
    assert _connector_session_for(client, world["alice"]).startswith("dgk_")
    revoked = client.delete(f"/projects/P1/connector-access/{access_id}", headers=world["olga"])
    assert revoked.status_code == 204
    denied = client.post(
        "/auth/connector-session",
        json={"project": "P1", "connector_id": "grasshopper"},
        headers=world["alice"],
    )
    assert denied.status_code == 403
    assert _code(denied) == "CONNECTOR_ACCESS_REQUIRED"
    listed = client.get("/projects/P1/connector-access", headers=world["olga"]).json()
    assert [g for g in listed["grants"] if not g["revoked"]] == []


def test_revoking_an_unknown_or_foreign_access_is_404(client, world):
    foreign = _issue(client, world["zed"], project="P2").json()["access_id"]
    for access_id in ("nope", foreign):
        response = client.delete(f"/projects/P1/connector-access/{access_id}", headers=world["olga"])
        assert response.status_code == 404
        assert _code(response) == "ACCESS_NOT_FOUND"
    assert connector_access.can_create(ALICE, "P2", "grasshopper")


def test_member_removal_revokes_the_access(client, world):
    _issue(client, world["olga"])
    assert connector_access.can_create(ALICE, "P1", "grasshopper")
    removed = client.delete(f"/projects/P1/members/{ALICE}", headers=world["olga"])
    assert removed.status_code == 204
    assert not connector_access.can_create(ALICE, "P1", "grasshopper")
    # P2 access is untouched by a P1 removal
    assert _issue(client, world["zed"], project="P2").status_code == 201
    assert connector_access.can_create(ALICE, "P2", "grasshopper")


def test_a_removed_and_readded_member_does_not_regain_access(client, world):
    _issue(client, world["olga"])
    client.delete(f"/projects/P1/members/{ALICE}", headers=world["olga"])
    auth.set_membership(ALICE, "P1", "viewer")
    assert not connector_access.can_create(ALICE, "P1", "grasshopper")


# -- owner-only project routes ----------------------------------------------


def test_non_owner_cannot_use_the_project_routes(client, world):
    for who in ("alice", "eric"):
        assert client.get("/projects/P1/connector-access", headers=world[who]).status_code == 403
        assert _issue(client, world[who]).status_code == 403
        assert client.delete("/projects/P1/connector-access/x", headers=world[who]).status_code == 403
    # a viewer cannot grant themselves access
    assert not connector_access.can_create(ALICE, "P1", "grasshopper")


def test_admin_uses_the_project_routes(client, world):
    _request(client, world["alice"])
    assert len(client.get("/projects/P1/connector-access", headers=world["root"]).json()["requests"]) == 1
    assert _issue(client, world["root"]).status_code == 201


def test_issuing_to_a_non_member_is_409_not_a_member(client, world):
    response = _issue(client, world["olga"], username=BOB)
    assert response.status_code == 409
    assert _code(response) == "NOT_A_MEMBER"


def test_issuing_for_an_unknown_connector_is_404(client, world):
    for connector in ("sketchup", "degram"):
        response = _issue(client, world["olga"], connector=connector)
        assert response.status_code == 404
        assert _code(response) == "CONNECTOR_NOT_FOUND"


def test_request_for_unknown_connector_and_degram_is_404(client, world):
    for connector in ("sketchup", "degram"):
        response = _request(client, world["alice"], connector=connector)
        assert response.status_code == 404
        assert _code(response) == "CONNECTOR_NOT_FOUND"


def test_request_note_is_bounded(client, world):
    assert _request(client, world["alice"], note="x" * 201).status_code == 422


def test_second_request_replaces_the_note_instead_of_adding_a_row(client, world):
    _request(client, world["alice"], note="one")
    _request(client, world["alice"], note="two")
    pending = client.get("/projects/P1/connector-access", headers=world["olga"]).json()["requests"]
    assert [r["note"] for r in pending] == ["two"]


# -- project isolation ------------------------------------------------------


def test_request_for_a_project_the_caller_is_not_a_member_of_is_forbidden(client, world):
    response = _request(client, world["alice"], project="P3")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"
    assert not _access_file().exists()


def test_a_p1_owner_cannot_issue_or_list_for_p2(client, world):
    assert _issue(client, world["olga"], project="P2").status_code == 403
    assert client.get("/projects/P2/connector-access", headers=world["olga"]).status_code == 403


def test_access_never_crosses_projects(client, world):
    _issue(client, world["olga"], project="P1")
    assert connector_access.can_create(ALICE, "P1", "grasshopper")
    assert not connector_access.can_create(ALICE, "P2", "grasshopper")
    denied = client.post(
        "/auth/connector-session",
        json={"project": "P2", "connector_id": "grasshopper"},
        headers=world["alice"],
    )
    assert _code(denied) == "CONNECTOR_ACCESS_REQUIRED"


def test_body_project_mismatch_is_rejected(client, world):
    response = client.post(
        "/projects/P1/connector-access",
        json={"username": ALICE, "connector_id": "grasshopper", "project": "P2"},
        headers=world["olga"],
    )
    assert response.status_code == 403
    assert _code(response) == "PROJECT_MISMATCH"


# -- mine / lists / no secret -------------------------------------------------


def test_mine_lists_only_the_callers_rows(client, world):
    _request(client, world["alice"], connector="revit")
    _issue(client, world["olga"], connector="grasshopper")
    mine = client.get("/connector-access/mine", headers=world["alice"]).json()
    assert [g["connector_id"] for g in mine["grants"]] == ["grasshopper"]
    assert [r["connector_id"] for r in mine["requests"]] == ["revit"]
    assert set(mine["grants"][0]) == {"project", "connector_id", "created_at", "active"}
    other = client.get("/connector-access/mine", headers=world["eric"]).json()
    assert other == {"grants": [], "requests": []}


def test_list_payloads_carry_no_token_or_hash(client, world):
    _request(client, world["alice"])
    _issue(client, world["olga"])
    session_token = _connector_session_for(client, world["alice"])
    dumps = [
        client.get("/projects/P1/connector-access", headers=world["olga"]).text,
        client.get("/connector-access/mine", headers=world["alice"]).text,
        client.get("/connectors", params={"project": "P1"}, headers=world["alice"]).text,
    ]
    for text in dumps:
        assert session_token not in text
        assert "token_hash" not in text
        assert '"token"' not in text
    assert "token" not in json.dumps(_stored())


# -- GET /connectors?project= -------------------------------------------------


def _access_by_id(response):
    return {c["id"]: c.get("access") for c in response.json()["connectors"]}


def test_connectors_without_project_has_no_access_field(client, world):
    body = client.get("/connectors", headers=world["alice"]).json()
    assert all("access" not in c for c in body["connectors"])


def test_connectors_access_field_per_role_and_state(client, world):
    viewer = _access_by_id(client.get("/connectors", params={"project": "P1"}, headers=world["alice"]))
    assert viewer["grasshopper"] == "requestable"
    assert viewer["degram"] is None
    _request(client, world["alice"], connector="grasshopper")
    _issue(client, world["olga"], connector="revit")
    viewer = _access_by_id(client.get("/connectors", params={"project": "P1"}, headers=world["alice"]))
    assert viewer["grasshopper"] == "pending"
    assert viewer["revit"] == "available"
    assert viewer["dynamo"] == "requestable"
    for who in ("olga", "root"):
        row = _access_by_id(client.get("/connectors", params={"project": "P1"}, headers=world[who]))
        assert all(row[c["id"]] == "available" for c in connectors.CONNECTOR_REGISTRY), who


def test_connectors_access_field_for_an_editor_follows_the_grant(client, world):
    """D-29: owner/admin are exempt, an editor is requestable, pending, then available."""

    def state():
        body = client.get("/connectors", params={"project": "P1"}, headers=world["eric"])
        return _access_by_id(body)

    assert state()["grasshopper"] == "requestable"
    assert _request(client, world["eric"], connector="grasshopper").status_code == 201
    assert state()["grasshopper"] == "pending"
    assert _issue(client, world["olga"], username=ERIC, connector="grasshopper").status_code == 201
    row = state()
    assert row["grasshopper"] == "available"
    assert row["revit"] == "requestable"


def test_connectors_access_field_absent_for_a_non_member(client, world):
    body = client.get("/connectors", params={"project": "P1"}, headers=world["bob"]).json()
    assert all("access" not in c for c in body["connectors"])


# -- store unit ---------------------------------------------------------------


def test_access_state_values(client, world):
    assert connector_access.access_state(ALICE, "P1", "viewer", "grasshopper") == "requestable"
    assert connector_access.access_state(ERIC, "P1", "editor", "grasshopper") == "requestable"
    assert connector_access.access_state(OLGA, "P1", "owner", "grasshopper") == "available"
    assert connector_access.access_state(ROOT, "P1", "owner", "grasshopper") == "available"
    connector_access.create_request(ALICE, "P1", "grasshopper", None)
    assert connector_access.access_state(ALICE, "P1", "viewer", "grasshopper") == "pending"
    connector_access.issue_access("P1", ALICE, "grasshopper", OLGA)
    assert connector_access.access_state(ALICE, "P1", "viewer", "grasshopper") == "available"


def test_reissue_is_idempotent_one_active_row(client, world):
    first = _issue(client, world["olga"]).json()["access_id"]
    second = _issue(client, world["olga"]).json()["access_id"]
    active = [g for g in _stored()["grants"] if not g.get("revoked")]
    assert [g["access_id"] for g in active] == [second]
    assert first != second


# -- D-30: a viewer with a grant has the connector's full route scope -----------


def test_viewer_with_a_grant_publishes_for_its_bound_project(client, world, monkeypatch):
    """D-30: the route policy admits POST /validation/publish for a dgk_ session
    bound to P1 whatever the project role (it answers the Speckle config 404,
    not a 401/403); another project in the body is still refused."""
    monkeypatch.setattr(app_module, "_auto_configure_integration", lambda *a, **k: None)
    monkeypatch.setattr(app_module, "get_integration_config", lambda *a, **k: None)
    assert _issue(client, world["olga"]).status_code == 201
    token = _connector_session_for(client, world["alice"])
    assert token.startswith("dgk_")
    bearer = {"Authorization": f"Bearer {token}"}

    own = client.post("/validation/publish", json={"project": "P1", "rules": [], "entities": []}, headers=bearer)
    assert own.status_code == 404, own.text
    assert _code(own) == "SPECKLE_CONFIG_MISSING"

    other = client.post("/validation/publish", json={"project": "P2", "rules": [], "entities": []}, headers=bearer)
    assert other.status_code == 403, other.text


def test_editor_without_a_grant_gets_no_connector_session(client, world):
    response = client.post(
        "/auth/connector-session",
        json={"project": "P1", "connector_id": "grasshopper"},
        headers=world["eric"],
    )
    assert response.status_code == 403
    assert _code(response) == "CONNECTOR_ACCESS_REQUIRED"
