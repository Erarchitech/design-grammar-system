"""Member role change route (Phase 1308 plan 02, WEBUI-03; D-01, D-14, D-15).

PUT /projects/{project}/members/{username} with body {role}: owner or admin
only (route policy), CSRF-protected, 404 for an unknown member, 422 for a role
outside auth.ROLES, a no-op for the same role, and 409 LAST_OWNER when the
change would leave the project without an owner (self-demotion included).

Every credential is a real session minted through the 1205-08 fixtures; nothing
patches ``require_principal``.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _headers(username, *, admin=False, memberships=None, csrf=True):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    headers = {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}"}
    if csrf:
        headers.update(CSRF)
    return headers


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def _put(client, headers, username, role, project="P1"):
    return client.put(
        f"/projects/{project}/members/{username}", json={"role": role}, headers=headers
    )


class TestChangeMemberRole:
    def test_owner_changes_viewer_to_editor(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, owner, "vw@dg.local", "editor")

        assert response.status_code == 200
        assert response.json() == {"project": "P1", "username": "vw@dg.local", "role": "editor"}
        assert auth.get_role("vw@dg.local", "P1") == "editor"

    def test_admin_without_membership_changes_a_role(self, client):
        admin = _headers("root@dg.local", admin=True)
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, admin, "vw@dg.local", "owner")

        assert response.status_code == 200
        assert auth.get_role("vw@dg.local", "P1") == "owner"

    @pytest.mark.parametrize("caller_role", ["editor", "viewer"])
    def test_editor_and_viewer_callers_are_forbidden(self, client, caller_role):
        caller = _headers("caller@dg.local", memberships={"P1": caller_role})
        auth_fixtures.make_user("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, caller, "vw@dg.local", "owner")

        assert response.status_code == 403
        assert auth.get_role("vw@dg.local", "P1") == "viewer"

    def test_owner_of_another_project_is_forbidden(self, client):
        stranger = _headers("stranger@dg.local", memberships={"P2": "owner"})
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, stranger, "vw@dg.local", "owner")

        assert response.status_code == 403
        assert auth.get_role("vw@dg.local", "P1") == "viewer"

    def test_sole_owner_cannot_demote_self(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = _put(client, owner, "owner@dg.local", "editor")

        assert response.status_code == 409
        assert _code(response) == "LAST_OWNER"
        assert auth.get_role("owner@dg.local", "P1") == "owner"

    def test_sole_owner_cannot_be_demoted_by_an_admin(self, client):
        admin = _headers("root@dg.local", admin=True)
        auth_fixtures.make_user("owner@dg.local", memberships={"P1": "owner"})

        response = _put(client, admin, "owner@dg.local", "viewer")

        assert response.status_code == 409
        assert _code(response) == "LAST_OWNER"
        assert auth.get_role("owner@dg.local", "P1") == "owner"

    def test_with_two_owners_one_can_be_demoted(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("second@dg.local", memberships={"P1": "owner"})

        response = _put(client, owner, "second@dg.local", "viewer")

        assert response.status_code == 200
        assert auth.get_role("second@dg.local", "P1") == "viewer"
        assert auth.count_owners("P1") == 1

    def test_unknown_member_is_404(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("elsewhere@dg.local", memberships={"P2": "viewer"})

        for name in ("ghost@dg.local", "elsewhere@dg.local"):
            response = _put(client, owner, name, "editor")
            assert response.status_code == 404
            assert _code(response) == "MEMBER_NOT_FOUND"
        assert auth.get_role("elsewhere@dg.local", "P1") is None

    def test_role_outside_the_vocabulary_is_422(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, owner, "vw@dg.local", "admin")

        assert response.status_code == 422
        assert _code(response) == "ROLE_INVALID"
        assert auth.get_role("vw@dg.local", "P1") == "viewer"

    def test_same_role_is_a_noop_without_a_store_write(self, client, monkeypatch):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("ed@dg.local", memberships={"P1": "editor"})
        writes = []
        monkeypatch.setattr(
            auth, "set_membership", lambda *a, **k: writes.append(a) or None
        )

        response = _put(client, owner, "ed@dg.local", "editor")

        assert response.status_code == 200
        assert response.json() == {"project": "P1", "username": "ed@dg.local", "role": "editor"}
        assert writes == []

    def test_sole_owner_same_role_stays_a_noop(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = _put(client, owner, "owner@dg.local", "owner")

        assert response.status_code == 200
        assert auth.get_role("owner@dg.local", "P1") == "owner"

    def test_missing_csrf_header_is_rejected(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"}, csrf=False)
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, owner, "vw@dg.local", "editor")

        assert response.status_code == 403
        assert _code(response) == "CSRF_HEADER_REQUIRED"
        assert auth.get_role("vw@dg.local", "P1") == "viewer"

    def test_invalid_project_name_is_422(self, client):
        admin = _headers("root@dg.local", admin=True)

        response = client.put(
            "/projects/-bad/members/x@dg.local", json={"role": "viewer"}, headers=admin
        )

        assert response.status_code == 422
        assert _code(response) == "PROJECT_NAME_INVALID"

    def test_the_username_in_the_path_is_normalized(self, client):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("vw@dg.local", memberships={"P1": "viewer"})

        response = _put(client, owner, "VW@DG.LOCAL", "editor")

        assert response.status_code == 200
        assert response.json()["username"] == "vw@dg.local"
        assert auth.get_role("vw@dg.local", "P1") == "editor"
