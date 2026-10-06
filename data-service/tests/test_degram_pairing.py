"""Phase 1301 plan 17, task 2 (D-25, D-26, D-27, DGCL-01, DGCL-05): the DeGram
pairing token.

A signed-in user creates a ``dgp_`` pairing token on the Connectors tab. The
token is bound to that user and to no project, never expires (D-27) and is
accepted by exactly one route, ``POST /auth/degram/exchange``, which trades it
for the same short-lived ``dgd_`` token ``POST /auth/delegated-token`` mints
from a cookie session. Every request goes through the real
``require_principal``; credentials come from the 1205-08 fixtures.
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
import degram_pairing  # noqa: E402
import delegation  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
ALICE = "alice@dg.local"
BOB = "bob@dg.local"
ROOT = "root@dg.local"


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


def _session(username=ALICE, *, admin=False, memberships=None):
    user = auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}, user


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _create(client, cookie, label="Office PC"):
    response = client.post("/connectors/degram/pairings", json={"label": label}, headers=cookie)
    assert response.status_code == 201, response.text
    return response.json()


def _exchange(client, pairing_token, project="P1"):
    return client.post(
        "/auth/degram/exchange", json={"project": project}, headers=_bearer(pairing_token)
    )


def _pairings_file():
    return auth.MEMBERSHIPS_FILE.parent / degram_pairing.PAIRINGS_FILE_NAME


def _degram_card(body):
    return next(c for c in body["connectors"] if c["id"] == "degram")


@pytest.fixture
def world(client):
    cookie, user = _session(memberships={"P1": "viewer", "P2": "viewer"})
    created = _create(client, cookie)
    return {"cookie": cookie, "user": user, "pairing": created["token"], "id": created["pairing_id"]}


# -- create -----------------------------------------------------------------


def test_create_returns_dgp_token_once_and_stores_only_its_hash(client):
    cookie, _ = _session(memberships={"P1": "viewer"})
    response = client.post("/connectors/degram/pairings", json={"label": "Office PC"}, headers=cookie)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"pairing_id", "token"}
    assert body["token"].startswith("dgp_") and len(body["token"]) > 40
    assert response.headers["cache-control"] == "no-store"
    stored = json.loads(_pairings_file().read_text(encoding="utf-8"))["pairings"]
    assert len(stored) == 1
    record = stored[0]
    assert record["pairing_id"] == body["pairing_id"]
    assert record["username"] == ALICE
    assert record["label"] == "Office PC"
    assert record["token_hash"] == degram_pairing._hash(body["token"])
    assert record["revoked"] is False
    assert record["expires_at"] is None  # D-27: no expiry, revoke only
    assert record["last_exchange"] is None
    assert "project" not in record  # D-26: user-bound, not project-bound
    assert body["token"] not in _pairings_file().read_text(encoding="utf-8")


def test_create_needs_a_session_and_csrf(client):
    cookie, _ = _session()
    no_csrf = {"Cookie": cookie["Cookie"]}
    assert client.post("/connectors/degram/pairings", json={}, headers=no_csrf).status_code == 403
    assert client.post("/connectors/degram/pairings", json={}).status_code == 401


def test_a_user_without_memberships_can_pair(client):
    cookie, _ = _session(username="new@dg.local")
    response = client.post("/connectors/degram/pairings", json={}, headers=cookie)
    assert response.status_code == 201


def test_a_bearer_cannot_create_a_pairing(client, world):
    response = client.post(
        "/connectors/degram/pairings",
        json={},
        headers=_bearer(auth_fixtures.connector_token_for("P1")),
    )
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_degram_is_not_a_connector_id(client, world):
    response = client.post(
        "/connectors/degram/credentials", json={"project": "P1"}, headers=world["cookie"]
    )
    assert response.status_code in (403, 404)
    assert "degram" not in connectors.CONNECTOR_IDS


# -- list -------------------------------------------------------------------


def test_connectors_lists_a_degram_card_in_the_agents_category(client, world):
    response = client.get("/connectors", headers=world["cookie"])
    assert response.status_code == 200
    body = response.json()
    assert body["categories"][-1] == "Agents"
    card = _degram_card(body)
    assert card["name"] == "DeGram" and card["category"] == "Agents"
    assert card["status"] == "never_connected"
    assert [c["credential_id"] for c in card["credentials"]] == [world["id"]]
    entry = card["credentials"][0]
    assert entry["label"] == "Office PC" and entry["revoked"] is False
    assert entry["last_exchange"] is None and entry["created_at"]
    assert "token_hash" not in json.dumps(body) and world["pairing"] not in json.dumps(body)


def test_a_user_sees_only_their_own_pairings_and_an_admin_sees_all(client, world):
    bob_cookie, _ = _session(BOB)
    _create(client, bob_cookie, label="Bob laptop")
    bob_card = _degram_card(client.get("/connectors", headers=bob_cookie).json())
    assert [c["label"] for c in bob_card["credentials"]] == ["Bob laptop"]
    assert "username" not in bob_card["credentials"][0]

    root_cookie, _ = _session(ROOT, admin=True)
    root_card = _degram_card(client.get("/connectors", headers=root_cookie).json())
    assert sorted((c["username"], c["label"]) for c in root_card["credentials"]) == [
        (ALICE, "Office PC"),
        (BOB, "Bob laptop"),
    ]


# -- exchange ---------------------------------------------------------------


def test_exchange_returns_the_delegated_token_shape(client, world):
    company.set_project_company("P1", "Acme")
    response = _exchange(client, world["pairing"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"token", "project", "company", "expiresAt", "expiresInSeconds", "username"}
    assert body["username"] == ALICE
    assert body["token"].startswith("dgd_")
    assert body["project"] == "P1" and body["company"] == "Acme"
    assert body["expiresInSeconds"] == delegation.DELEGATED_TOKEN_TTL_SECONDS
    assert response.headers["cache-control"] == "no-store"
    record = json.loads((auth.MEMBERSHIPS_FILE.parent / delegation.TOKENS_FILE_NAME).read_text())[
        "tokens"
    ][0]
    assert record["parent_kind"] == "pairing"
    assert record["pairing_id"] == world["id"]
    assert record.get("session_hash") is None


def test_the_exchanged_token_reads_the_bound_project_only(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    assert client.get("/graph/P1", headers=_bearer(token)).status_code == 200
    assert client.get("/graph/P2", headers=_bearer(token)).status_code == 403


def test_exchange_records_last_exchange(client, world):
    assert _exchange(client, world["pairing"]).status_code == 201
    card = _degram_card(client.get("/connectors", headers=world["cookie"]).json())
    assert card["credentials"][0]["last_exchange"]
    assert card["status"] == "active"


def test_exchange_refuses_a_non_member_project(client, world):
    response = _exchange(client, world["pairing"], project="P9")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_exchange_refuses_disagreeing_project_locations(client, world):
    response = client.post(
        "/auth/degram/exchange",
        params={"project": "P2"},
        json={"project": "P1"},
        headers=_bearer(world["pairing"]),
    )
    assert response.status_code == 403
    assert _code(response) == "PROJECT_MISMATCH"


def test_exchange_refuses_an_admin_who_is_not_a_member(client):
    cookie, _ = _session(ROOT, admin=True)
    pairing = _create(client, cookie)["token"]
    response = _exchange(client, pairing, project="P1")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_exchange_refuses_an_unknown_pairing(client, world):
    response = _exchange(client, "dgp_" + "x" * 43)
    assert response.status_code == 401
    assert _code(response) == "PAIRING_AUTH_FAILED"


@pytest.mark.parametrize(
    "headers_for",
    [
        lambda w: w["cookie"],
        lambda w: _bearer(auth_fixtures.connector_token_for("P1")),
        lambda w: auth_fixtures.service_headers(),
    ],
    ids=["cookie", "connector", "service"],
)
def test_exchange_refuses_every_other_principal(client, world, headers_for):
    response = client.post("/auth/degram/exchange", json={"project": "P1"}, headers=headers_for(world))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_exchange_refuses_a_delegated_token(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    response = client.post("/auth/degram/exchange", json={"project": "P1"}, headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


# -- the pairing token is not a principal anywhere else ----------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/"),
        ("GET", "/auth/me"),
        ("GET", "/graph/P1"),
        ("GET", "/connectors"),
        ("POST", "/auth/delegated-token"),
        ("POST", "/degram/v1/chat/completions"),
        ("POST", "/connectors/heartbeat"),
        ("POST", "/computgraph/publish"),
    ],
)
def test_a_pairing_token_is_refused_on_every_other_route(client, world, method, path):
    response = client.request(method, path, json={"project": "P1"}, headers=_bearer(world["pairing"]))
    assert response.status_code == 401, (path, response.text)
    assert _code(response) == "PAIRING_NOT_A_PRINCIPAL"


# -- revocation -------------------------------------------------------------


def test_owner_revokes_and_every_minted_token_ends(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    response = client.delete(f"/connectors/degram/pairings/{world['id']}", headers=world["cookie"])
    assert response.status_code == 204
    assert _code(_exchange(client, world["pairing"])) == "PAIRING_AUTH_FAILED"
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401
    assert _code(late) == "DELEGATED_SESSION_ENDED"
    card = _degram_card(client.get("/connectors", headers=world["cookie"]).json())
    assert card["credentials"][0]["revoked"] is True


def test_admin_revokes_another_users_pairing(client, world):
    root_cookie, _ = _session(ROOT, admin=True)
    response = client.delete(f"/connectors/degram/pairings/{world['id']}", headers=root_cookie)
    assert response.status_code == 204
    assert _code(_exchange(client, world["pairing"])) == "PAIRING_AUTH_FAILED"


def test_another_user_cannot_revoke_and_cannot_tell_it_exists(client, world):
    bob_cookie, _ = _session(BOB)
    foreign = client.delete(f"/connectors/degram/pairings/{world['id']}", headers=bob_cookie)
    unknown = client.delete("/connectors/degram/pairings/nope", headers=bob_cookie)
    assert foreign.status_code == unknown.status_code == 404
    assert _code(foreign) == _code(unknown) == "PAIRING_NOT_FOUND"
    assert _exchange(client, world["pairing"]).status_code == 201


def test_a_pairing_revoked_in_the_store_ends_its_tokens_even_without_the_cascade(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    data = json.loads(_pairings_file().read_text(encoding="utf-8"))
    data["pairings"][0]["revoked"] = True
    _pairings_file().write_text(json.dumps(data), encoding="utf-8")
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401
    assert _code(late) == "DELEGATED_SESSION_ENDED"


def test_password_change_revokes_pairings_and_their_tokens(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    response = client.post(
        "/auth/password",
        json={"currentPassword": world["user"]["password"], "newPassword": "a-new-long-password-42"},
        headers=world["cookie"],
    )
    assert response.status_code == 204, response.text
    assert _code(_exchange(client, world["pairing"])) == "PAIRING_AUTH_FAILED"
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "DELEGATED_SESSION_ENDED"


def test_a_deleted_user_ends_the_pairing_and_its_tokens(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    users = json.loads(auth.USERS_FILE.read_text(encoding="utf-8"))
    users["users"] = [u for u in users["users"] if u["username"] != ALICE]
    auth.USERS_FILE.write_text(json.dumps(users), encoding="utf-8")
    assert _code(_exchange(client, world["pairing"])) == "PAIRING_AUTH_FAILED"
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "DELEGATED_SESSION_ENDED"


def test_logout_of_the_creating_session_keeps_the_pairing(client, world):
    assert client.post("/auth/logout", headers=world["cookie"]).status_code == 204
    assert _exchange(client, world["pairing"]).status_code == 201


def test_membership_removal_refuses_the_exchange_for_that_project(client, world):
    token = _exchange(client, world["pairing"]).json()["token"]
    auth.remove_membership(ALICE, "P1")
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "PROJECT_FORBIDDEN"
    assert _code(_exchange(client, world["pairing"])) == "PROJECT_FORBIDDEN"
    assert _exchange(client, world["pairing"], project="P2").status_code == 201


# -- no token in logs -------------------------------------------------------


def test_no_pairing_or_delegated_token_reaches_a_log_line(client, caplog):
    caplog.set_level(logging.DEBUG)
    cookie, _ = _session(memberships={"P1": "viewer"})
    created = _create(client, cookie)
    minted = _exchange(client, created["token"]).json()["token"]
    client.get("/graph/P1", headers=_bearer(created["token"]))
    client.delete(f"/connectors/degram/pairings/{created['pairing_id']}", headers=cookie)
    _exchange(client, created["token"])
    text = caplog.text
    assert created["token"] not in text and minted not in text
    assert "dgp_" not in text
