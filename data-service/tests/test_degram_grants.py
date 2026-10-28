"""Phase 1301 plan 30 (D-39, D-40, DGCL-01, DGCL-05): DeGram access grants.

A DeGram grant is issued by a DG admin or the owner of the project, for one
member of that project, with a name and a purpose. The grant holds no secret:
it is the authorization that ``POST /auth/degram/session-exchange`` checks
before it trades the caller's cookie session for a ``dgd_`` token. Every
request goes through the real ``require_principal``; credentials come from the
1205-08 fixtures.
"""

from __future__ import annotations

import json
import logging
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import company  # noqa: E402
import connectors  # noqa: E402
import degram_grants  # noqa: E402
import delegation  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
ALICE = "alice@dg.local"
BOB = "bob@dg.local"
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


# -- helpers ----------------------------------------------------------------


def _session(username, *, admin=False, memberships=None):
    user = auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}, user


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


@pytest.fixture
def world(client):
    alice, alice_user = _session(ALICE, memberships={"P1": "viewer", "P2": "viewer"})
    return {
        "alice": alice,
        "alice_user": alice_user,
        "olga": _session(OLGA, memberships={"P1": "owner"})[0],
        "zed": _session(ZED, memberships={"P2": "owner"})[0],
        "eric": _session(ERIC, memberships={"P1": "editor"})[0],
        "bob": _session(BOB)[0],
        "root": _session(ROOT, admin=True)[0],
    }


def _issue(client, cookie, project="P1", username=ALICE, label="Office PC", purpose="Daily review"):
    return client.post(
        f"/projects/{project}/degram-grants",
        json={"username": username, "label": label, "purpose": purpose},
        headers=cookie,
    )


def _exchange(client, cookie, project="P1"):
    return client.post("/auth/degram/session-exchange", json={"project": project}, headers=cookie)


def _grants_file():
    return auth.MEMBERSHIPS_FILE.parent / degram_grants.GRANTS_FILE_NAME


def _stored_grants():
    return json.loads(_grants_file().read_text(encoding="utf-8"))["grants"]


def _tokens_file():
    return auth.MEMBERSHIPS_FILE.parent / delegation.TOKENS_FILE_NAME


def _all_keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _all_keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _all_keys(inner)


# -- issue ------------------------------------------------------------------


def test_owner_issues_a_grant_for_a_member(client, world):
    response = _issue(client, world["olga"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {
        "grant_id",
        "username",
        "project",
        "label",
        "purpose",
        "issued_by",
        "created_at",
        "last_used",
        "revoked",
        "active",
    }
    assert body["username"] == ALICE and body["project"] == "P1"
    assert body["label"] == "Office PC" and body["purpose"] == "Daily review"
    assert body["issued_by"] == OLGA
    assert body["last_used"] is None and body["revoked"] is False and body["active"] is True
    stored = _stored_grants()
    assert len(stored) == 1
    assert stored[0]["grant_id"] == body["grant_id"]
    assert stored[0]["revoked"] is False and stored[0]["last_used"] is None
    assert not [k for k in stored[0] if "token" in k or "secret" in k or "hash" in k]


@pytest.mark.parametrize("who", ["eric", "alice", "bob"])
def test_a_non_owner_cannot_issue(client, world, who):
    response = _issue(client, world[who])
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"
    assert not _grants_file().exists()


def test_the_owner_of_another_project_cannot_issue(client, world):
    response = _issue(client, world["zed"], project="P1")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_an_admin_who_is_not_a_member_can_issue(client, world):
    response = _issue(client, world["root"])
    assert response.status_code == 201, response.text
    assert response.json()["issued_by"] == ROOT


def test_a_grant_needs_a_member_target(client, world):
    for username in (BOB, "nobody@dg.local"):
        response = _issue(client, world["olga"], username=username)
        assert response.status_code == 409
        assert _code(response) == "NOT_A_MEMBER"
    assert not _grants_file().exists()


@pytest.mark.parametrize(
    "label,purpose",
    [("", "ok"), ("   ", "ok"), ("x" * 121, "ok"), ("ok", ""), ("ok", "y" * 201)],
)
def test_label_and_purpose_are_bounded(client, world, label, purpose):
    response = _issue(client, world["olga"], label=label, purpose=purpose)
    assert response.status_code == 422
    assert _code(response) == "GRANT_INVALID"


def test_the_limits_are_inclusive(client, world):
    response = _issue(client, world["olga"], label="x" * 120, purpose="y" * 200)
    assert response.status_code == 201


def test_issue_needs_a_session_and_csrf(client, world):
    no_csrf = {"Cookie": world["olga"]["Cookie"]}
    body = {"username": ALICE, "label": "a", "purpose": "b"}
    assert client.post("/projects/P1/degram-grants", json=body, headers=no_csrf).status_code == 403
    assert client.post("/projects/P1/degram-grants", json=body).status_code == 401


def test_a_bearer_cannot_issue(client, world):
    response = client.post(
        "/projects/P1/degram-grants",
        json={"username": ALICE, "label": "a", "purpose": "b"},
        headers=_bearer(auth_fixtures.connector_token_for("P1")),
    )
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_reissuing_replaces_the_old_grant_and_ends_its_tokens(client, world):
    first = _issue(client, world["olga"], label="Old PC").json()
    token = _exchange(client, world["alice"]).json()["token"]
    second = _issue(client, world["olga"], label="New PC").json()
    assert second["grant_id"] != first["grant_id"]
    stored = {g["grant_id"]: g for g in _stored_grants()}
    assert stored[first["grant_id"]]["revoked"] is True
    assert stored[second["grant_id"]]["revoked"] is False
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "DELEGATED_SESSION_ENDED"
    assert _exchange(client, world["alice"]).status_code == 201


# -- list (owner / admin) ---------------------------------------------------


def test_owner_lists_the_project_grants_and_requests(client, world):
    _issue(client, world["olga"])
    client.post("/degram/grant-requests", json={"project": "P1", "note": "please"}, headers=world["eric"])
    response = client.get("/projects/P1/degram-grants", headers=world["olga"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["project"] == "P1"
    assert [g["username"] for g in body["grants"]] == [ALICE]
    assert [r["username"] for r in body["requests"]] == [ERIC]
    assert body["requests"][0]["note"] == "please"


def test_the_listing_is_project_scoped_and_owner_only(client, world):
    _issue(client, world["olga"])
    _issue(client, world["zed"], project="P2")
    p1 = client.get("/projects/P1/degram-grants", headers=world["olga"]).json()
    assert {g["project"] for g in p1["grants"]} == {"P1"}
    for who in ("alice", "eric"):
        denied = client.get("/projects/P1/degram-grants", headers=world[who])
        assert denied.status_code == 403 and _code(denied) == "PROJECT_FORBIDDEN"
    foreign = client.get("/projects/P1/degram-grants", headers=world["zed"])
    assert foreign.status_code == 403
    assert client.get("/projects/P1/degram-grants", headers=world["root"]).status_code == 200


# -- mine -------------------------------------------------------------------


def test_mine_returns_only_the_callers_grants(client, world):
    _issue(client, world["olga"], label="Alice PC", purpose="reviews")
    _issue(client, world["olga"], username=OLGA, label="Olga PC", purpose="own")
    response = client.get("/degram/grants/mine", headers=world["alice"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert [g["label"] for g in body["grants"]] == ["Alice PC"]
    entry = body["grants"][0]
    assert set(entry) == {"project", "label", "purpose", "created_at", "last_used", "active"}
    assert entry["project"] == "P1" and entry["purpose"] == "reviews" and entry["active"] is True
    assert "Olga PC" not in json.dumps(body) and OLGA not in json.dumps(body)
    assert client.get("/degram/grants/mine", headers=world["bob"]).json()["grants"] == []


def test_mine_needs_a_session(client, world):
    assert client.get("/degram/grants/mine").status_code == 401
    response = client.get("/degram/grants/mine", headers=_bearer(auth_fixtures.connector_token_for("P1")))
    assert response.status_code == 403


def test_mine_shows_a_revoked_grant_as_inactive(client, world):
    grant = _issue(client, world["olga"]).json()
    client.delete(f"/projects/P1/degram-grants/{grant['grant_id']}", headers=world["olga"])
    entry = client.get("/degram/grants/mine", headers=world["alice"]).json()["grants"][0]
    assert entry["active"] is False


# -- requests (D-40) --------------------------------------------------------


def test_a_member_requests_a_grant_and_the_issue_closes_it(client, world):
    response = client.post(
        "/degram/grant-requests", json={"project": "P1", "note": "need DeGram"}, headers=world["alice"]
    )
    assert response.status_code == 201, response.text
    assert set(response.json()) == {"request_id", "username", "project", "note", "created_at", "status"}
    assert response.json()["status"] == "pending"
    mine = client.get("/degram/grants/mine", headers=world["alice"]).json()
    assert [r["project"] for r in mine["requests"]] == ["P1"]
    listed = client.get("/projects/P1/degram-grants", headers=world["olga"]).json()
    assert [r["username"] for r in listed["requests"]] == [ALICE]
    assert _issue(client, world["olga"]).status_code == 201
    listed = client.get("/projects/P1/degram-grants", headers=world["olga"]).json()
    assert listed["requests"] == []
    assert client.get("/degram/grants/mine", headers=world["alice"]).json()["requests"] == []


def test_a_repeated_request_keeps_one_pending_row(client, world):
    for note in ("first", "second"):
        assert (
            client.post("/degram/grant-requests", json={"project": "P1", "note": note}, headers=world["alice"]).status_code
            == 201
        )
    listed = client.get("/projects/P1/degram-grants", headers=world["olga"]).json()
    assert [r["note"] for r in listed["requests"]] == ["second"]


def test_a_request_with_an_active_grant_conflicts(client, world):
    _issue(client, world["olga"])
    response = client.post("/degram/grant-requests", json={"project": "P1"}, headers=world["alice"])
    assert response.status_code == 409
    assert _code(response) == "GRANT_EXISTS"


def test_a_non_member_cannot_request(client, world):
    response = client.post("/degram/grant-requests", json={"project": "P1"}, headers=world["bob"])
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_a_request_needs_csrf(client, world):
    no_csrf = {"Cookie": world["alice"]["Cookie"]}
    assert client.post("/degram/grant-requests", json={"project": "P1"}, headers=no_csrf).status_code == 403


def test_the_note_is_optional_and_bounded(client, world):
    assert client.post("/degram/grant-requests", json={"project": "P1"}, headers=world["alice"]).status_code == 201
    response = client.post(
        "/degram/grant-requests", json={"project": "P1", "note": "n" * 201}, headers=world["alice"]
    )
    assert response.status_code == 422 and _code(response) == "GRANT_INVALID"


# -- revoke -----------------------------------------------------------------


def test_owner_revokes_a_grant_and_its_tokens_end(client, world):
    grant = _issue(client, world["olga"]).json()
    token = _exchange(client, world["alice"]).json()["token"]
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 200
    response = client.delete(f"/projects/P1/degram-grants/{grant['grant_id']}", headers=world["olga"])
    assert response.status_code == 204
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401 and _code(late) == "DELEGATED_SESSION_ENDED"
    again = _exchange(client, world["alice"])
    assert again.status_code == 403 and _code(again) == "GRANT_REQUIRED"


def test_an_admin_revokes_a_grant(client, world):
    grant = _issue(client, world["olga"]).json()
    response = client.delete(f"/projects/P1/degram-grants/{grant['grant_id']}", headers=world["root"])
    assert response.status_code == 204


def test_revoke_is_owner_only_and_project_scoped(client, world):
    grant = _issue(client, world["olga"]).json()
    path = f"/projects/P1/degram-grants/{grant['grant_id']}"
    assert client.delete(path, headers=world["eric"]).status_code == 403
    assert client.delete(path, headers=world["alice"]).status_code == 403
    assert client.delete(path, headers=world["zed"]).status_code == 403
    # the id of a P1 grant under P2's path answers like an unknown id
    wrong = client.delete(f"/projects/P2/degram-grants/{grant['grant_id']}", headers=world["zed"])
    unknown = client.delete("/projects/P2/degram-grants/nope", headers=world["zed"])
    assert wrong.status_code == unknown.status_code == 404
    assert _code(wrong) == _code(unknown) == "GRANT_NOT_FOUND"
    assert _exchange(client, world["alice"]).status_code == 201


def test_removing_the_member_revokes_the_grant_and_its_tokens(client, world):
    grant = _issue(client, world["olga"]).json()
    token = _exchange(client, world["alice"]).json()["token"]
    response = client.delete(f"/projects/P1/members/{ALICE}", headers=world["olga"])
    assert response.status_code == 204
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401 and _code(late) == "DELEGATED_SESSION_ENDED"
    stored = {g["grant_id"]: g for g in _stored_grants()}
    assert stored[grant["grant_id"]]["revoked"] is True


def test_the_grant_of_another_project_survives_a_member_removal(client, world):
    _issue(client, world["olga"])
    zed_grant = _issue(client, world["zed"], project="P2").json()
    client.delete(f"/projects/P1/members/{ALICE}", headers=world["olga"])
    stored = {g["grant_id"]: g for g in _stored_grants()}
    assert stored[zed_grant["grant_id"]]["revoked"] is False
    assert _exchange(client, world["alice"], project="P2").status_code == 201


# -- no secret anywhere -----------------------------------------------------


def test_no_response_or_stored_grant_carries_a_secret(client, world):
    grant = _issue(client, world["olga"]).json()
    client.post("/degram/grant-requests", json={"project": "P2", "note": "n"}, headers=world["alice"])
    responses = [
        _issue(client, world["olga"], label="Again"),
        client.get("/projects/P1/degram-grants", headers=world["olga"]),
        client.get("/degram/grants/mine", headers=world["alice"]),
        client.get("/connectors", headers=world["alice"]),
        client.get("/connectors", headers=world["root"]),
    ]
    for response in responses:
        assert response.status_code in (200, 201), response.text
        keys = {k.lower() for k in _all_keys(response.json())}
        assert not [k for k in keys if "token" in k or "secret" in k or "hash" in k or "password" in k]
        assert "dgp_" not in response.text and "dgd_" not in response.text
    assert grant["grant_id"]


def test_the_grant_module_has_no_secret_serializer_field():
    import inspect

    source = inspect.getsource(degram_grants)
    assert "GRANT_REQUIRED" in source
    assert "secrets.token" not in source


# -- session exchange (Task 2) ----------------------------------------------


def test_session_exchange_returns_the_delegated_token_shape(client, world):
    company.set_project_company("P1", "Acme")
    grant = _issue(client, world["olga"]).json()
    response = _exchange(client, world["alice"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"token", "project", "company", "expiresAt", "expiresInSeconds", "username"}
    assert body["username"] == ALICE and body["project"] == "P1" and body["company"] == "Acme"
    assert body["token"].startswith("dgd_")
    assert body["expiresInSeconds"] == delegation.DELEGATED_TOKEN_TTL_SECONDS
    assert response.headers["cache-control"] == "no-store"
    record = json.loads(_tokens_file().read_text(encoding="utf-8"))["tokens"][0]
    assert record["parent_kind"] == "session"
    assert record["grant_id"] == grant["grant_id"]
    assert record["session_hash"]
    stored = _stored_grants()[0]
    assert stored["last_used"]
    mine = client.get("/degram/grants/mine", headers=world["alice"]).json()["grants"][0]
    assert mine["last_used"]


def test_a_member_without_a_grant_gets_grant_required(client, world):
    response = _exchange(client, world["alice"])
    assert response.status_code == 403
    assert _code(response) == "GRANT_REQUIRED"
    assert not _tokens_file().exists()


def test_a_non_member_gets_project_forbidden(client, world):
    response = _exchange(client, world["bob"])
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_an_admin_who_is_not_a_member_gets_project_forbidden(client, world):
    response = _exchange(client, world["root"])
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_a_grant_covers_only_its_own_project(client, world):
    _issue(client, world["olga"])
    response = _exchange(client, world["alice"], project="P2")
    assert response.status_code == 403
    assert _code(response) == "GRANT_REQUIRED"


def _token_records():
    return json.loads(_tokens_file().read_text(encoding="utf-8"))["tokens"]


def test_the_owner_needs_no_grant(client, world):
    response = _exchange(client, world["olga"])
    assert response.status_code == 201, response.text
    assert response.json()["username"] == OLGA
    record = _token_records()[0]
    assert record["grant_id"] is None and record["exempt"] is True
    assert not _grants_file().exists()
    token = response.json()["token"]
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 200


def test_an_admin_member_needs_no_grant(client, world):
    ada = _session("ada@dg.local", admin=True, memberships={"P1": "viewer"})[0]
    response = _exchange(client, ada)
    assert response.status_code == 201, response.text
    assert _token_records()[0]["exempt"] is True


def test_an_editor_still_needs_a_grant(client, world):
    response = _exchange(client, world["eric"])
    assert response.status_code == 403
    assert _code(response) == "GRANT_REQUIRED"


def test_an_owner_with_a_grant_exchanges_under_the_grant(client, world):
    grant = _issue(client, world["olga"], username=OLGA).json()
    assert _exchange(client, world["olga"]).status_code == 201
    record = _token_records()[0]
    assert record["grant_id"] == grant["grant_id"] and not record.get("exempt")


def test_losing_ownership_ends_the_exempt_token(client, world):
    token = _exchange(client, world["olga"]).json()["token"]
    auth.set_membership(OLGA, "P1", "editor")
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 401


def test_the_owner_cannot_request_a_grant(client, world):
    response = client.post("/degram/grant-requests", json={"project": "P1"}, headers=world["olga"])
    assert response.status_code == 409
    assert _code(response) == "GRANT_EXISTS"


def test_the_exchanged_token_reads_the_bound_project_only(client, world):
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 200
    assert client.get("/graph/P2", headers=_bearer(token)).status_code == 403


def test_session_exchange_needs_a_session_and_csrf(client, world):
    _issue(client, world["olga"])
    no_csrf = {"Cookie": world["alice"]["Cookie"]}
    assert client.post("/auth/degram/session-exchange", json={"project": "P1"}, headers=no_csrf).status_code == 403
    assert client.post("/auth/degram/session-exchange", json={"project": "P1"}).status_code == 401


@pytest.mark.parametrize(
    "headers_for",
    [
        lambda w: _bearer(auth_fixtures.connector_token_for("P1")),
        lambda w: auth_fixtures.service_headers(),
    ],
    ids=["connector", "service"],
)
def test_session_exchange_refuses_every_bearer_principal(client, world, headers_for):
    response = client.post(
        "/auth/degram/session-exchange", json={"project": "P1"}, headers=headers_for(world)
    )
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_a_delegated_token_cannot_mint_another(client, world):
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    response = client.post("/auth/degram/session-exchange", json={"project": "P1"}, headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_logout_ends_the_exchanged_token(client, world):
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    assert client.post("/auth/logout", headers=world["alice"]).status_code == 204
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401 and _code(late) == "DELEGATED_SESSION_ENDED"


def test_password_change_ends_the_exchanged_token(client, world):
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    response = client.post(
        "/auth/password",
        json={"currentPassword": world["alice_user"]["password"], "newPassword": "a-new-long-password-42"},
        headers=world["alice"],
    )
    assert response.status_code == 204, response.text
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "DELEGATED_SESSION_ENDED"
    # the grant itself is the admin's decision: it survives a password change
    assert degram_grants.active_grant(ALICE, "P1") is not None


def test_a_deleted_user_ends_the_grant_and_its_tokens(client, world):
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    users = json.loads(auth.USERS_FILE.read_text(encoding="utf-8"))
    users["users"] = [u for u in users["users"] if u["username"] != ALICE]
    auth.USERS_FILE.write_text(json.dumps(users), encoding="utf-8")
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "DELEGATED_SESSION_ENDED"
    assert degram_grants.active_grant(ALICE, "P1") is None
    assert degram_grants.revoke_for_user(ALICE) == 1
    assert _stored_grants()[0]["revoked"] is True


def test_a_grant_revoked_in_the_store_ends_its_tokens_without_the_cascade(client, world):
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    data = json.loads(_grants_file().read_text(encoding="utf-8"))
    data["grants"][0]["revoked"] = True
    _grants_file().write_text(json.dumps(data), encoding="utf-8")
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401 and _code(late) == "DELEGATED_SESSION_ENDED"


def test_a_session_minted_token_without_a_grant_is_unaffected(client, world):
    response = client.post("/auth/delegated-token", json={"project": "P1"}, headers=world["alice"])
    assert response.status_code == 201
    token = response.json()["token"]
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 200


def test_the_connector_card_describes_grants(client, world):
    _issue(client, world["olga"], label="Office PC", purpose="Daily review")
    body = client.get("/connectors", headers=world["alice"]).json()
    card = next(c for c in body["connectors"] if c["id"] == "degram")
    assert card["category"] == "Agents" and card["name"] == "DeGram"
    assert "pairing" not in json.dumps(card).lower()
    assert [c["label"] for c in card["credentials"]] == ["Office PC"]
    assert card["credentials"][0]["purpose"] == "Daily review"
    assert card["credentials"][0]["project"] == "P1"
    assert "owner" in card["description"].lower()
    root_card = next(
        c for c in client.get("/connectors", headers=world["root"]).json()["connectors"] if c["id"] == "degram"
    )
    assert [c["username"] for c in root_card["credentials"]] == [ALICE]


def test_no_delegated_token_reaches_a_log_line(client, world, caplog):
    caplog.set_level(logging.DEBUG)
    _issue(client, world["olga"])
    token = _exchange(client, world["alice"]).json()["token"]
    client.get("/graph/P1", headers=_bearer(token))
    assert token not in caplog.text and "dgd_" not in caplog.text
