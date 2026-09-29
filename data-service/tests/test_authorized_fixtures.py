"""Self-test of the 1205-08 authorised-fixture mechanics (D-20).

Covers the conftest store redirect / test-only secrets, the autouse
``_dg_authorize_module_client`` fixture (module default + marker override +
restoration), and the ``auth_fixtures`` helpers. Every credential asserted on
here is resolved through the real ``auth`` / ``connectors`` functions -- no
dependence on the 1205-07 routes, and no dependency override of any kind.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import auth  # noqa: E402
import auth_fixtures  # noqa: E402
import connectors  # noqa: E402
import secrets_policy  # noqa: E402

# A private echo app: proves the cookie jar / headers actually reach the
# server side, without touching data-service's own routes.
_echo = FastAPI()


@_echo.get("/echo")
def _echo_route(request: Request) -> dict:
    return {
        "cookie": request.cookies.get(auth.SESSION_COOKIE_NAME),
        "csrf": request.headers.get(auth.CSRF_HEADER),
        "service": request.headers.get(auth.SERVICE_TOKEN_HEADER),
    }


client = TestClient(_echo, raise_server_exceptions=False)


def _cookie(c: TestClient) -> str | None:
    return c.cookies.get(auth.SESSION_COOKIE_NAME)


# ── conftest: store redirect and test-only secrets ──


def test_auth_store_is_redirected_out_of_the_live_data_dir():
    for path in (
        auth.USERS_FILE,
        auth.SESSIONS_FILE,
        auth.MEMBERSHIPS_FILE,
        auth.INVITES_FILE,
    ):
        assert "dg-auth-test-" in str(path)
        assert not str(path).replace("\\", "/").startswith("/app/data")


def test_test_only_secrets_are_policy_compliant_and_deployment_untouched():
    token = os.environ["DG_SERVICE_TOKEN"]
    assert len(token) == 48
    assert secrets_policy.classify_secret("DG_SERVICE_TOKEN", token) == []
    password = os.environ["DG_BOOTSTRAP_ADMIN_PASSWORD"]
    assert len(password) >= 12
    assert secrets_policy.classify_secret("DG_BOOTSTRAP_ADMIN_PASSWORD", password) == []
    assert os.environ.get("DG_BOOTSTRAP_ADMIN_USER")
    conftest_text = (Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    assert "DG_DEPLOYMENT" not in conftest_text
    assert "dependency_overrides" not in conftest_text
    fixtures_text = (Path(__file__).parent / "auth_fixtures.py").read_text(encoding="utf-8")
    assert "dependency_overrides" not in fixtures_text


# ── autouse module-client authoriser ──


def test_default_principal_is_a_real_admin_session():
    token = _cookie(client)
    assert token
    assert client.headers.get(auth.CSRF_HEADER) == "1"
    principal = auth.resolve_session_principal(token)
    assert principal is not None
    assert principal.kind == "user"
    assert principal.is_admin is True


def test_cookie_and_headers_reach_the_server_side():
    body = client.get("/echo").json()
    assert body["cookie"] == _cookie(client)
    assert body["csrf"] == "1"
    assert body["service"] is None


@pytest.mark.dg_principal("service")
def test_marker_service_puts_service_header_and_no_cookie():
    assert _cookie(client) is None
    header = client.headers.get(auth.SERVICE_TOKEN_HEADER)
    assert header
    principal = auth.resolve_service_principal(header)
    assert principal is not None and principal.kind == "service"
    assert client.get("/echo").json()["service"] == header


@pytest.mark.dg_principal("none")
def test_marker_none_leaves_client_untouched():
    assert _cookie(client) is None
    assert client.headers.get(auth.CSRF_HEADER) is None
    assert client.headers.get(auth.SERVICE_TOKEN_HEADER) is None


@pytest.mark.dg_principal("admin")
def test_marker_admin_is_explicit_default():
    principal = auth.resolve_session_principal(_cookie(client))
    assert principal is not None and principal.is_admin


def test_default_is_restored_for_the_next_test_after_an_override():
    # The two preceding markers changed the principal; this one has none.
    principal = auth.resolve_session_principal(_cookie(client))
    assert principal is not None and principal.is_admin
    assert client.headers.get(auth.SERVICE_TOKEN_HEADER) is None


def test_undo_removes_exactly_what_authorize_client_added():
    fresh = TestClient(_echo, raise_server_exceptions=False)
    undo = auth_fixtures.authorize_client(fresh, "admin")
    assert _cookie(fresh) and fresh.headers.get(auth.CSRF_HEADER) == "1"
    undo()
    assert _cookie(fresh) is None
    assert fresh.headers.get(auth.CSRF_HEADER) is None

    undo = auth_fixtures.authorize_client(fresh, "service")
    assert fresh.headers.get(auth.SERVICE_TOKEN_HEADER)
    undo()
    assert fresh.headers.get(auth.SERVICE_TOKEN_HEADER) is None


def test_undo_tolerates_a_cookie_the_test_already_cleared():
    fresh = TestClient(_echo, raise_server_exceptions=False)
    undo = auth_fixtures.authorize_client(fresh, "admin")
    fresh.cookies.clear()
    undo()  # must not raise
    assert _cookie(fresh) is None


def test_principal_resolution_order_marker_then_module_then_admin():
    class _Mod:
        DG_TEST_PRINCIPAL = "service"

    class _Bare:
        pass

    assert auth_fixtures.resolve_principal_name(None, _Bare) == "admin"
    assert auth_fixtures.resolve_principal_name(None, _Mod) == "service"
    assert auth_fixtures.resolve_principal_name("none", _Mod) == "none"


# ── auth_fixtures helpers ──


def test_admin_session_is_reminted_after_revocation():
    first = auth_fixtures.admin_session_token()
    assert auth.revoke_session(first)
    second = auth_fixtures.admin_session_token()
    assert second != first
    assert auth.resolve_session_principal(second) is not None


def test_make_user_with_memberships_and_user_principal():
    record = auth_fixtures.make_user(
        "member-08@dg.local", memberships={"P1": "viewer", "P2": "editor"}
    )
    assert record["username"] == "member-08@dg.local"
    assert auth.get_role("member-08@dg.local", "P1") == "viewer"
    assert auth.get_role("member-08@dg.local", "P2") == "editor"

    fresh = TestClient(_echo, raise_server_exceptions=False)
    auth_fixtures.authorize_client(fresh, ("user", "member-08@dg.local"))
    principal = auth.resolve_session_principal(_cookie(fresh))
    assert principal is not None
    assert principal.username == "member-08@dg.local"
    assert principal.is_admin is False
    # make_user is idempotent for an existing username.
    again = auth_fixtures.make_user("member-08@dg.local", memberships={"P3": "owner"})
    assert again["username"] == "member-08@dg.local"
    assert auth.get_role("member-08@dg.local", "P3") == "owner"


def test_make_user_admin_flag():
    auth_fixtures.make_user("second-admin-08@dg.local", is_admin=True)
    token = auth_fixtures.session_cookie_for("second-admin-08@dg.local")
    principal = auth.resolve_session_principal(token)
    assert principal is not None and principal.is_admin


def test_service_headers_carry_the_configured_token():
    headers = auth_fixtures.service_headers()
    assert headers == {auth.SERVICE_TOKEN_HEADER: os.environ["DG_SERVICE_TOKEN"]}


def test_connector_token_for_binds_the_project(tmp_path, monkeypatch):
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "creds.json")
    token = auth_fixtures.connector_token_for("P1")
    assert token.startswith(connectors.TOKEN_PREFIX)
    principal = auth.resolve_connector_principal(token)
    assert principal is not None
    assert principal.kind == "connector"
    assert principal.bound_project == "P1"


def test_unknown_principal_is_rejected():
    fresh = TestClient(_echo, raise_server_exceptions=False)
    with pytest.raises(ValueError):
        auth_fixtures.authorize_client(fresh, "root")
