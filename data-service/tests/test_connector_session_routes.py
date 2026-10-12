"""Phase 1308 plan 06 (WEBUI-07, WEBUI-10, D-25, D-26, D-29, D-34, D-36): the
``dgk_`` connector sign-in session as a principal and the mint/revoke routes.

Every request goes through the real ``require_principal``; credentials come
from the 1205-08 fixtures and from ``connector_session`` itself.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connector_access  # noqa: E402
import connector_session  # noqa: E402
import connectors  # noqa: E402
import delegation  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
P1 = "P1"
P2 = "P2"
OWNER = "owner@dg.local"
EDITOR = "editor@dg.local"
VIEWER = "viewer@dg.local"
OUTSIDER = "outsider@dg.local"
ROOT = "root@dg.local"
GH = "grasshopper"


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.setattr(app_module, "read_many", lambda *a, **k: [])
    monkeypatch.setattr(app_module, "read_single", lambda *a, **k: None)
    monkeypatch.delenv(connector_session.TTL_ENV, raising=False)
    auth_fixtures.make_user(OWNER, memberships={P1: "owner"})
    auth_fixtures.make_user(EDITOR, memberships={P1: "editor"})
    auth_fixtures.make_user(VIEWER, memberships={P1: "viewer"})
    auth_fixtures.make_user(OUTSIDER)
    auth_fixtures.make_user(ROOT, is_admin=True)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", "local")
    return TestClient(app, raise_server_exceptions=False)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _grant(username, project=P1, connector_id=GH):
    return connector_access.issue_access(project, username, connector_id, OWNER)


def _session_headers(username):
    token = auth_fixtures.session_cookie_for(username)
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


# -- the dgk_ resolver (D-26) -----------------------------------------------


def test_resolver_maps_a_dgk_session_to_a_connector_principal():
    token, record = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    principal = auth.resolve_connector_principal(token)
    assert principal is not None
    assert principal.kind == "connector"
    assert principal.username == OWNER
    assert principal.bound_project == P1
    assert principal.connector_id == GH
    assert principal.credential_id == record["session_id"]
    assert principal.is_admin is False


def test_resolver_returns_none_for_a_foreign_prefix():
    assert auth.resolve_connector_principal("dgx_whatever") is None
    assert auth.resolve_connector_principal("") is None


def test_resolver_still_accepts_a_legacy_dgc_token_until_retirement():
    _record, token = connectors.create_credential(GH, project=P1)
    principal = auth.resolve_connector_principal(token)
    assert principal is not None and principal.bound_project == P1
    assert principal.connector_id is None


def test_resolver_raises_the_named_error_for_an_unknown_dgk_token():
    with pytest.raises(HTTPException) as exc:
        auth.resolve_connector_principal("dgk_" + "x" * 40)
    assert exc.value.detail["code"] == "CONNECTOR_AUTH_FAILED"


def test_fixture_seam_issues_a_session_of_the_shared_admin_without_membership():
    token = auth_fixtures.connector_token_for("P7")
    assert token.startswith(connector_session.SESSION_TOKEN_PREFIX)
    principal = auth.resolve_connector_principal(token)
    assert principal.username == auth_fixtures.TEST_ADMIN_USERNAME
    assert principal.bound_project == "P7"
    assert auth.get_role(auth_fixtures.TEST_ADMIN_USERNAME, "P7") is None


def test_fixture_seam_accepts_a_username_and_connector_id():
    token = auth_fixtures.connector_token_for(P1, username=OWNER, connector_id="revit")
    principal = auth.resolve_connector_principal(token)
    assert principal.username == OWNER and principal.connector_id == "revit"


# -- dgk_ on connector routes ------------------------------------------------


def test_session_passes_a_connector_route_of_its_own_project(client):
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code not in (401, 403), response.text


def test_session_on_another_projects_path_is_refused(client):
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    response = client.get(f"/validation/view/{P2}", headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


def test_expired_session_answers_401_expired(client, monkeypatch):
    monkeypatch.setenv(connector_session.TTL_ENV, "1")
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH, now=1_000)
    monkeypatch.setattr(auth, "_now", lambda now=None: now if now is not None else 5_000)
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code == 401
    assert _code(response) == "CONNECTOR_SESSION_EXPIRED"


def test_revoked_session_answers_401_ended(client):
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    assert connector_session.revoke_token(token) is True
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code == 401
    assert _code(response) == "CONNECTOR_SESSION_ENDED"


def test_editor_without_a_grant_answers_403_access_required(client):
    token, _ = connector_session.issue(username=EDITOR, project=P1, connector_id=GH)
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "CONNECTOR_ACCESS_REQUIRED"


def test_editor_with_a_grant_passes(client):
    _grant(EDITOR)
    token, _ = connector_session.issue(username=EDITOR, project=P1, connector_id=GH)
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code not in (401, 403), response.text


def test_session_is_refused_on_a_delegated_only_route(client):
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    response = client.delete("/auth/delegated-token", headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_session_is_refused_on_a_member_or_delegated_only_route(client):
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    response = client.get(f"/graph/{P1}", headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"
