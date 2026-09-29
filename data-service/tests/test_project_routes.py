"""Project tenancy routes (Phase 1205 plan 12, ALGN12-17/ALGN12-18; D-02, D-05).

Covers GET/POST /projects, GET/DELETE /projects/{project}/members[...],
POST /auth/invites and POST /auth/accept-invite: membership-scoped listing,
first-come project registration with a 409 on any reuse, owner-only member
administration with the last-owner guard, and invitation-only onboarding
(an invite can never take over an existing account).

Every credential is a real session minted through the 1205-08 fixtures
(D-20); nothing patches ``require_principal``. The Neo4j reads that back the
listing and the name-availability check are monkeypatched, and the tests
assert those queries carry the project only as a bound parameter.
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
import route_policy  # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

CSRF = {auth.CSRF_HEADER: "1"}
GOOD_PASSWORD = "twelve-chars-ok-1"  # 17 characters, not a real secret


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")


@pytest.fixture
def graph(monkeypatch):
    """Capture every graph read; ``rows``/``single`` are what the fakes return."""
    state = {"rows": [], "single": None, "read_many": [], "read_single": []}

    def fake_many(query, parameters=None):
        state["read_many"].append((query, parameters))
        return list(state["rows"])

    def fake_single(query, parameters=None):
        state["read_single"].append((query, parameters))
        return state["single"]

    monkeypatch.setattr(app_module, "read_many", fake_many)
    monkeypatch.setattr(app_module, "read_single", fake_single)
    return state


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _headers(username, *, admin=False, memberships=None):
    auth_fixtures.make_user(username, is_admin=admin, memberships=memberships)
    token = auth_fixtures.session_cookie_for(auth.normalize_username(username))
    return {"Cookie": f"{auth.SESSION_COOKIE_NAME}={token}", **CSRF}


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


class TestListProjects:
    def test_member_sees_only_memberships_with_roles_and_counts(self, client, graph):
        headers = _headers("mem@dg.local", memberships={"P1": "editor", "P3": "viewer"})
        auth_fixtures.make_user("other@dg.local", memberships={"P2": "owner"})
        graph["rows"] = [{"project": "P1", "nodes": 7}, {"project": "P3", "nodes": 2}]

        response = client.get("/projects", headers=headers)

        assert response.status_code == 200
        assert response.json() == {
            "projects": [
                {"project": "P1", "nodes": 7, "role": "editor"},
                {"project": "P3", "nodes": 2, "role": "viewer"},
            ]
        }
        query, params = graph["read_many"][0]
        assert "$projects" in query
        assert params == {"projects": ["P1", "P3"]}
        assert "P1" not in query and "P3" not in query

    def test_membership_without_graph_nodes_lists_zero(self, client, graph):
        headers = _headers("mem@dg.local", memberships={"Fresh": "owner"})

        response = client.get("/projects", headers=headers)

        assert response.json()["projects"] == [{"project": "Fresh", "nodes": 0, "role": "owner"}]

    def test_user_without_membership_gets_empty_list_and_no_query(self, client, graph):
        headers = _headers("nobody@dg.local")

        response = client.get("/projects", headers=headers)

        assert response.json() == {"projects": []}
        assert graph["read_many"] == []

    def test_admin_sees_graph_and_membership_projects_as_owner(self, client, graph):
        headers = _headers("boss@dg.local", admin=True)
        auth_fixtures.make_user("mem@dg.local", memberships={"P1": "viewer"})
        graph["rows"] = [{"project": "P9", "nodes": 4}, {"project": "P1", "nodes": 1}]

        response = client.get("/projects", headers=headers)

        assert response.json() == {
            "projects": [
                {"project": "P1", "nodes": 1, "role": "owner"},
                {"project": "P9", "nodes": 4, "role": "owner"},
            ]
        }
        query, params = graph["read_many"][0]
        assert "$projects" in query
        assert params == {"projects": None}

    def test_requires_a_session(self, client, graph):
        assert client.get("/projects").status_code == 401


class TestCreateProject:
    def test_creates_with_caller_as_owner(self, client, graph):
        headers = _headers("mem@dg.local")

        response = client.post("/projects", json={"project": "New One"}, headers=headers)

        assert response.status_code == 201
        assert response.json() == {"project": "New One", "role": "owner"}
        assert auth.get_role("mem@dg.local", "New One") == "owner"
        query, params = graph["read_single"][0]
        assert "$project" in query and "New One" not in query
        assert params == {"project": "New One"}

    def test_second_registration_of_the_same_name_conflicts(self, client, graph):
        first = _headers("one@dg.local")
        second = _headers("two@dg.local")
        assert client.post("/projects", json={"project": "Taken"}, headers=first).status_code == 201

        response = client.post("/projects", json={"project": "Taken"}, headers=second)

        assert response.status_code == 409
        assert _code(response) == "PROJECT_NAME_UNAVAILABLE"
        assert auth.get_role("two@dg.local", "Taken") is None

    def test_name_already_on_graph_nodes_conflicts(self, client, graph):
        graph["single"] = {"present": True}
        headers = _headers("mem@dg.local")

        response = client.post("/projects", json={"project": "Legacy"}, headers=headers)

        assert response.status_code == 409
        assert _code(response) == "PROJECT_NAME_UNAVAILABLE"
        assert auth.get_role("mem@dg.local", "Legacy") is None

    @pytest.mark.parametrize("name", ["../x", "a" * 65, "", " lead", "a/b", "semi;colon"])
    def test_invalid_names_are_rejected(self, client, graph, name):
        headers = _headers("mem@dg.local")

        response = client.post("/projects", json={"project": name}, headers=headers)

        assert response.status_code == 422
        assert _code(response) == "PROJECT_NAME_INVALID"
        assert graph["read_single"] == []

    def test_sixty_four_characters_is_accepted(self, client, graph):
        headers = _headers("mem@dg.local")
        name = "a" * 64

        response = client.post("/projects", json={"project": name}, headers=headers)

        assert response.status_code == 201


class TestInvites:
    def test_owner_adds_existing_user_directly(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("Eval@dg.local")

        response = client.post(
            "/auth/invites",
            json={"username": "Eval@dg.local", "project": "P1", "role": "editor"},
            headers=owner,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "member-added"}
        assert auth.get_role("eval@dg.local", "P1") == "editor"

    def test_owner_invites_new_username_with_a_one_time_code(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = client.post(
            "/auth/invites",
            json={"username": "newbie@dg.local", "project": "P1", "role": "viewer"},
            headers=owner,
        )

        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "invited"
        assert body["inviteCode"].startswith("dgi_")
        assert body["expiresAt"].endswith("Z")
        assert auth.get_user("newbie@dg.local") is None  # no account until accepted
        assert auth.get_role("newbie@dg.local", "P1") is None

    def test_admin_role_is_not_invitable(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = client.post(
            "/auth/invites",
            json={"username": "newbie@dg.local", "project": "P1", "role": "admin"},
            headers=owner,
        )

        assert response.status_code == 422
        assert _code(response) == "ROLE_INVALID"

    def test_editor_cannot_invite(self, client, graph):
        editor = _headers("ed@dg.local", memberships={"P1": "editor"})

        response = client.post(
            "/auth/invites",
            json={"username": "newbie@dg.local", "project": "P1", "role": "viewer"},
            headers=editor,
        )

        assert response.status_code == 403
        assert _code(response) == "PROJECT_FORBIDDEN"

    def test_owner_of_another_project_cannot_invite_into_this_one(self, client, graph):
        other = _headers("owner2@dg.local", memberships={"P2": "owner"})

        response = client.post(
            "/auth/invites",
            json={"username": "newbie@dg.local", "project": "P1", "role": "viewer"},
            headers=other,
        )

        assert response.status_code == 403

    def test_demoting_the_last_owner_by_invite_is_refused(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = client.post(
            "/auth/invites",
            json={"username": "owner@dg.local", "project": "P1", "role": "viewer"},
            headers=owner,
        )

        assert response.status_code == 409
        assert _code(response) == "LAST_OWNER"
        assert auth.get_role("owner@dg.local", "P1") == "owner"


def _mint_invite(client, owner_headers, username, project="P1", role="editor"):
    response = client.post(
        "/auth/invites",
        json={"username": username, "project": project, "role": role},
        headers=owner_headers,
    )
    assert response.status_code == 200
    return response.json()["inviteCode"]


class TestAcceptInvite:
    def test_accept_creates_account_role_and_session(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        code = _mint_invite(client, owner, "newbie@dg.local", role="editor")
        fresh = TestClient(app, raise_server_exceptions=False)

        response = fresh.post(
            "/auth/accept-invite",
            json={"inviteCode": code, "password": GOOD_PASSWORD},
            headers=CSRF,
        )

        assert response.status_code == 200
        assert response.json() == {"username": "newbie@dg.local", "isAdmin": False}
        assert auth.SESSION_COOKIE_NAME in response.headers.get("set-cookie", "")
        me = fresh.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["memberships"] == [{"project": "P1", "role": "editor"}]
        assert me.json()["isAdmin"] is False

    def test_code_is_single_use(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        code = _mint_invite(client, owner, "newbie@dg.local")
        body = {"inviteCode": code, "password": GOOD_PASSWORD}
        assert client.post("/auth/accept-invite", json=body, headers=CSRF).status_code == 200

        again = TestClient(app, raise_server_exceptions=False).post(
            "/auth/accept-invite", json=body, headers=CSRF
        )

        assert again.status_code == 400
        assert _code(again) == "INVITE_INVALID"

    def test_short_password_is_rejected_and_the_code_stays_usable(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        code = _mint_invite(client, owner, "newbie@dg.local")
        fresh = TestClient(app, raise_server_exceptions=False)

        short = fresh.post(
            "/auth/accept-invite",
            json={"inviteCode": code, "password": "x" * 11},
            headers=CSRF,
        )
        assert short.status_code == 422
        assert auth.get_user("newbie@dg.local") is None

        ok = fresh.post(
            "/auth/accept-invite",
            json={"inviteCode": code, "password": GOOD_PASSWORD},
            headers=CSRF,
        )
        assert ok.status_code == 200

    def test_unknown_and_malformed_codes_share_one_generic_error(self, client, graph):
        for code in ("dgi_not-a-real-code", "garbage", ""):
            response = client.post(
                "/auth/accept-invite",
                json={"inviteCode": code, "password": GOOD_PASSWORD},
                headers=CSRF,
            )
            assert response.status_code == 400
            assert _code(response) == "INVITE_INVALID"

    def test_code_for_a_username_that_now_exists_never_touches_that_account(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        code = _mint_invite(client, owner, "victim@dg.local", role="owner")
        victim = auth_fixtures.make_user("victim@dg.local")  # account appears after the invite
        before = auth.get_user("victim@dg.local")["password_hash"]

        response = TestClient(app, raise_server_exceptions=False).post(
            "/auth/accept-invite",
            json={"inviteCode": code, "password": GOOD_PASSWORD},
            headers=CSRF,
        )

        assert response.status_code == 400
        assert _code(response) == "INVITE_INVALID"
        assert auth.get_user("victim@dg.local")["password_hash"] == before
        assert auth.verify_password(victim["password"], before)
        assert auth.get_role("victim@dg.local", "P1") is None

    def test_accept_requires_the_csrf_header(self, client, graph):
        response = client.post(
            "/auth/accept-invite", json={"inviteCode": "dgi_x", "password": GOOD_PASSWORD}
        )

        assert response.status_code == 403
        assert _code(response) == "CSRF_HEADER_REQUIRED"


class TestMembers:
    def test_owner_lists_members(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("ed@dg.local", memberships={"P1": "editor"})
        auth_fixtures.make_user("elsewhere@dg.local", memberships={"P2": "owner"})

        response = client.get("/projects/P1/members", headers=owner)

        assert response.status_code == 200
        assert response.json() == {
            "project": "P1",
            "members": [
                {"username": "ed@dg.local", "role": "editor"},
                {"username": "owner@dg.local", "role": "owner"},
            ],
        }

    def test_editor_cannot_list_members(self, client, graph):
        editor = _headers("ed@dg.local", memberships={"P1": "editor"})

        assert client.get("/projects/P1/members", headers=editor).status_code == 403

    def test_delete_the_only_owner_conflicts(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = client.delete("/projects/P1/members/owner@dg.local", headers=owner)

        assert response.status_code == 409
        assert _code(response) == "LAST_OWNER"
        assert auth.get_role("owner@dg.local", "P1") == "owner"

    def test_delete_an_owner_when_another_remains(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        auth_fixtures.make_user("co@dg.local", memberships={"P1": "owner"})

        response = client.delete("/projects/P1/members/co@dg.local", headers=owner)

        assert response.status_code == 204
        assert auth.get_role("co@dg.local", "P1") is None

    def test_delete_unknown_member_is_404(self, client, graph):
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})

        response = client.delete("/projects/P1/members/ghost@dg.local", headers=owner)

        assert response.status_code == 404
        assert _code(response) == "MEMBER_NOT_FOUND"

    def test_removed_member_loses_access_immediately(self, client, graph, monkeypatch):
        monkeypatch.setattr(app_module, "list_validation_runs", lambda project: [])
        owner = _headers("owner@dg.local", memberships={"P1": "owner"})
        member = _headers("ed@dg.local", memberships={"P1": "editor"})
        assert client.get("/validation/runs/P1", headers=member).status_code == 200

        assert client.delete("/projects/P1/members/ed@dg.local", headers=owner).status_code == 204

        after = client.get("/validation/runs/P1", headers=member)
        assert after.status_code == 403
        assert _code(after) == "PROJECT_FORBIDDEN"


class TestNoOpenRegistration:
    def test_no_open_account_creation_route_exists(self):
        offenders = [
            (method, path)
            for method, path in route_policy.ROUTE_POLICIES
            if "register" in path or "signup" in path
        ]
        assert offenders == []

    @pytest.mark.parametrize("path", ["/auth/register", "/auth/signup", "/auth/users", "/register"])
    def test_probing_common_registration_paths_finds_nothing(self, client, path):
        headers = _headers("mem@dg.local")
        response = client.post(path, json={"username": "x@dg.local", "password": GOOD_PASSWORD}, headers=headers)

        assert response.status_code in (404, 405)
