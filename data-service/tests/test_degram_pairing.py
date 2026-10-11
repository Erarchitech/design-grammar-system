"""Phase 1301 plan 30 (D-39): the retired DeGram pairing token.

Plan 17 let a signed-in user create a ``dgp_`` pairing token and paste it into
DeGram. D-39 retires it: DeGram access is granted by a project owner or a DG
admin (``test_degram_grants.py``). Creating a pairing answers 410
``PAIRING_RETIRED``, the exchange answers 401 ``PAIRING_RETIRED`` to any
``dgp_`` Bearer (DeGram 0.1.9 maps any exchange 401 to "pairing revoked"),
every stored pairing is treated as revoked and the ``dgd_`` tokens minted from
one before the retirement have ended. The pairing token is still not a
principal anywhere else.
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
LEGACY_TOKEN = "dgp_" + "x" * 43
LEGACY_ID = "legacypairing0001"


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


def _pairings_file():
    return auth.MEMBERSHIPS_FILE.parent / degram_pairing.PAIRINGS_FILE_NAME


def _seed_legacy_pairing(username=ALICE):
    """A pairing as plan 17 stored it, plus a dgd_ token minted from it."""
    _pairings_file().write_text(
        json.dumps(
            {
                "pairings": [
                    {
                        "pairing_id": LEGACY_ID,
                        "username": username,
                        "label": "Old PC",
                        "token_hash": "0" * 64,
                        "created_at": 1,
                        "last_exchange": None,
                        "revoked": False,
                        "expires_at": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    token, _ = delegation.issue_delegated_token(
        pairing_id=LEGACY_ID, username=username, project="P1"
    )
    return token


@pytest.fixture
def world(client):
    cookie, user = _session(memberships={"P1": "viewer", "P2": "viewer"})
    return {"cookie": cookie, "user": user}


# -- creation is retired ----------------------------------------------------


def test_creating_a_pairing_answers_410(client, world):
    response = client.post("/connectors/degram/pairings", json={"label": "Office PC"}, headers=world["cookie"])
    assert response.status_code == 410
    assert _code(response) == "PAIRING_RETIRED"
    assert not _pairings_file().exists()
    assert "dgp_" not in response.text


def test_creating_still_needs_a_session_and_csrf(client, world):
    no_csrf = {"Cookie": world["cookie"]["Cookie"]}
    assert client.post("/connectors/degram/pairings", json={}, headers=no_csrf).status_code == 403
    assert client.post("/connectors/degram/pairings", json={}).status_code == 401


def test_a_bearer_cannot_reach_the_creation_route(client, world):
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


def test_the_module_no_longer_issues_a_pairing():
    assert not hasattr(degram_pairing, "issue_pairing")
    assert not hasattr(degram_pairing, "record_exchange")
    assert not hasattr(degram_pairing, "connector_card")


# -- the exchange is retired ------------------------------------------------


def test_the_exchange_answers_401_pairing_retired_to_any_dgp_bearer(client, world):
    response = client.post(
        "/auth/degram/exchange", json={"project": "P1"}, headers=_bearer(LEGACY_TOKEN)
    )
    assert response.status_code == 401
    assert _code(response) == "PAIRING_RETIRED"


def test_a_stored_pairing_does_not_resolve(client, world):
    _seed_legacy_pairing()
    response = client.post(
        "/auth/degram/exchange", json={"project": "P1"}, headers=_bearer(LEGACY_TOKEN)
    )
    assert response.status_code == 401 and _code(response) == "PAIRING_RETIRED"
    with pytest.raises(Exception) as caught:
        degram_pairing.authenticate_pairing(LEGACY_TOKEN)
    assert getattr(caught.value, "status_code", None) == 401


@pytest.mark.parametrize(
    "headers_for",
    [
        lambda w: w["cookie"],
        lambda w: _bearer(auth_fixtures.connector_token_for("P1")),
        lambda w: auth_fixtures.service_headers(),
    ],
    ids=["cookie", "connector", "service"],
)
def test_the_exchange_refuses_every_other_principal(client, world, headers_for):
    response = client.post("/auth/degram/exchange", json={"project": "P1"}, headers=headers_for(world))
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
        ("POST", "/auth/degram/session-exchange"),
        ("POST", "/degram/v1/chat/completions"),
        ("POST", "/connectors/heartbeat"),
        ("POST", "/computgraph/publish"),
    ],
)
def test_a_pairing_token_is_refused_on_every_other_route(client, world, method, path):
    response = client.request(method, path, json={"project": "P1"}, headers=_bearer(LEGACY_TOKEN))
    assert response.status_code == 401, (path, response.text)
    assert _code(response) == "PAIRING_NOT_A_PRINCIPAL"


# -- tokens minted before the retirement have ended --------------------------


def test_a_delegated_token_minted_from_a_pairing_has_ended(client, world):
    token = _seed_legacy_pairing()
    late = client.get("/graph/P1", headers=_bearer(token))
    assert late.status_code == 401
    assert _code(late) == "DELEGATED_SESSION_ENDED"
    assert degram_pairing.is_live(LEGACY_ID, ALICE) is False


# -- cleanup of stored rows -------------------------------------------------


def test_the_owner_of_a_stored_pairing_can_still_delete_it(client, world):
    token = _seed_legacy_pairing()
    response = client.delete(f"/connectors/degram/pairings/{LEGACY_ID}", headers=world["cookie"])
    assert response.status_code == 204
    stored = json.loads(_pairings_file().read_text(encoding="utf-8"))["pairings"]
    assert stored[0]["revoked"] is True
    assert _code(client.get("/graph/P1", headers=_bearer(token))) == "DELEGATED_SESSION_ENDED"


def test_an_admin_can_delete_another_users_stored_pairing(client, world):
    _seed_legacy_pairing()
    root_cookie, _ = _session(ROOT, admin=True)
    response = client.delete(f"/connectors/degram/pairings/{LEGACY_ID}", headers=root_cookie)
    assert response.status_code == 204


def test_another_user_cannot_delete_and_cannot_tell_it_exists(client, world):
    _seed_legacy_pairing()
    bob_cookie, _ = _session(BOB)
    foreign = client.delete(f"/connectors/degram/pairings/{LEGACY_ID}", headers=bob_cookie)
    unknown = client.delete("/connectors/degram/pairings/nope", headers=bob_cookie)
    assert foreign.status_code == unknown.status_code == 404
    assert _code(foreign) == _code(unknown) == "PAIRING_NOT_FOUND"


# -- the card describes grants ----------------------------------------------


def test_the_degram_card_lists_no_pairing(client, world):
    _seed_legacy_pairing()
    body = client.get("/connectors", headers=world["cookie"]).json()
    assert body["categories"][-1] == "Agents"
    card = next(c for c in body["connectors"] if c["id"] == "degram")
    assert card["category"] == "Agents" and card["credentials"] == []
    assert LEGACY_ID not in json.dumps(body)
    assert "pairing" not in json.dumps(card).lower()


# -- no token in logs -------------------------------------------------------


def test_no_pairing_token_reaches_a_log_line(client, world, caplog):
    caplog.set_level(logging.DEBUG)
    client.post("/auth/degram/exchange", json={"project": "P1"}, headers=_bearer(LEGACY_TOKEN))
    client.get("/graph/P1", headers=_bearer(LEGACY_TOKEN))
    assert LEGACY_TOKEN not in caplog.text
