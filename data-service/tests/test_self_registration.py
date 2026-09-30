"""Self-registration in the `local` deployment profile (Phase 1205 follow-up,
amendment of D-05 made 2026-09-30).

GET /auth/options and POST /auth/register. Invite-only onboarding stays the
rule in `multi-user`, where /auth/register answers 404 like an unknown route.

D-20: no auth-dependency override and no app-side bypass. Every account here is
created by the real route against temp stores; the only monkeypatching is the
store-file redirect and the graph reads behind GET/POST /projects.
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
    monkeypatch.delenv("DG_ALLOW_SELF_REGISTRATION", raising=False)
    monkeypatch.delenv("DG_THROTTLE_LIMIT_IP", raising=False)
    monkeypatch.delenv("DG_TRUSTED_PROXIES", raising=False)
    auth.throttle_reset_all()
    yield
    auth.throttle_reset_all()


@pytest.fixture(autouse=True)
def _graph(monkeypatch):
    """The graph holds no project rows: listing is empty and every name is free."""
    monkeypatch.setattr(app_module, "read_many", lambda query, parameters=None: [])
    monkeypatch.setattr(app_module, "read_single", lambda query, parameters=None: None)


@pytest.fixture
def local(monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", "local")


@pytest.fixture
def multi_user(monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", "multi-user")


def _client():
    return TestClient(app, raise_server_exceptions=False)


def _register(client, username="newcomer@dg.local", password=GOOD_PASSWORD, **extra):
    return client.post(
        "/auth/register",
        json={"username": username, "password": password, **extra},
        headers=CSRF,
    )


def _code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


# -- the toggle (unit level) ---------------------------------------------------


class TestToggle:
    def test_default_follows_the_profile(self):
        assert auth.self_registration_enabled({"DG_DEPLOYMENT": "local"}) is True
        assert auth.self_registration_enabled({}) is True
        assert auth.self_registration_enabled({"DG_DEPLOYMENT": "multi-user"}) is False

    def test_blank_value_follows_the_profile(self):
        assert auth.self_registration_enabled({"DG_ALLOW_SELF_REGISTRATION": "  "}) is True
        assert (
            auth.self_registration_enabled(
                {"DG_ALLOW_SELF_REGISTRATION": "", "DG_DEPLOYMENT": "multi-user"}
            )
            is False
        )

    @pytest.mark.parametrize("value", ["true", "TRUE", " True "])
    def test_true_overrides_the_profile(self, value):
        env = {"DG_ALLOW_SELF_REGISTRATION": value, "DG_DEPLOYMENT": "multi-user"}
        assert auth.self_registration_enabled(env) is True

    @pytest.mark.parametrize("value", ["false", "FALSE", " False "])
    def test_false_overrides_the_profile(self, value):
        env = {"DG_ALLOW_SELF_REGISTRATION": value, "DG_DEPLOYMENT": "local"}
        assert auth.self_registration_enabled(env) is False

    @pytest.mark.parametrize("value", ["1", "yes", "on", "tru", "enabled"])
    def test_any_other_value_raises(self, value):
        with pytest.raises(ValueError):
            auth.self_registration_enabled({"DG_ALLOW_SELF_REGISTRATION": value})

    def test_startup_refuses_an_invalid_value(self, monkeypatch):
        monkeypatch.setenv("DG_ALLOW_SELF_REGISTRATION", "maybe")
        with pytest.raises(ValueError):
            with TestClient(app):
                pass


# -- local profile, default ----------------------------------------------------


class TestLocalDefault:
    def test_options_reports_enabled(self, local):
        response = _client().get("/auth/options")
        assert response.status_code == 200
        assert response.json() == {"selfRegistration": True}

    def test_register_creates_account_and_logs_in(self, local):
        client = _client()

        response = _register(client)

        assert response.status_code == 201
        assert response.json() == {"username": "newcomer@dg.local", "isAdmin": False}
        assert auth.SESSION_COOKIE_NAME in response.headers.get("set-cookie", "")
        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json() == {"username": "newcomer@dg.local", "isAdmin": False, "memberships": []}

    def test_new_account_is_not_admin_and_has_no_memberships(self, local):
        _register(_client())

        user = auth.get_user("newcomer@dg.local")
        assert user is not None
        assert user["is_admin"] is False
        assert auth.list_memberships("newcomer@dg.local") == []

    def test_username_is_normalized(self, local):
        response = _register(_client(), username="  MixedCase@DG.Local ")
        assert response.status_code == 201
        assert response.json()["username"] == "mixedcase@dg.local"

    def test_new_user_lists_no_projects_then_creates_and_owns_one(self, local):
        client = _client()
        assert _register(client).status_code == 201

        listed = client.get("/projects")
        assert listed.status_code == 200
        assert listed.json() == {"projects": []}

        created = client.post("/projects", json={"project": "Mine"}, headers=CSRF)
        assert created.status_code == 201
        assert created.json() == {"project": "Mine", "role": "owner"}
        assert auth.get_role("newcomer@dg.local", "Mine") == "owner"

    def test_new_user_cannot_read_another_projects_data(self, local):
        auth_fixtures.make_user("owner@dg.local", memberships={"Private": "owner"})
        client = _client()
        assert _register(client).status_code == 201

        for path in ("/graph/Private", "/rules/Private", "/projects/Private/members"):
            response = client.get(path)
            assert response.status_code in (403, 404), path

    def test_register_response_never_carries_admin(self, local):
        response = _register(_client(), is_admin=True, isAdmin=True, admin=True, role="owner")
        assert response.status_code == 201
        assert response.json()["isAdmin"] is False
        assert auth.get_user("newcomer@dg.local")["is_admin"] is False
        assert auth.list_memberships("newcomer@dg.local") == []


class TestRegistrationRefusals:
    def test_duplicate_username_is_a_generic_400(self, local):
        auth_fixtures.make_user("taken@dg.local")

        response = _register(_client(), username="taken@dg.local")

        assert response.status_code == 400
        assert _code(response) == "REGISTRATION_INVALID"
        assert "exist" not in response.text.lower()
        assert auth.SESSION_COOKIE_NAME not in response.headers.get("set-cookie", "")

    def test_duplicate_and_weak_password_share_the_code(self, local):
        auth_fixtures.make_user("taken@dg.local")
        dup = _register(_client(), username="taken@dg.local")
        weak = _register(_client(), username="fresh@dg.local", password="short")
        assert dup.status_code == weak.status_code == 400
        assert _code(dup) == _code(weak) == "REGISTRATION_INVALID"

    def test_duplicate_does_not_touch_the_existing_account(self, local):
        record = auth_fixtures.make_user("taken@dg.local")
        _register(_client(), username="taken@dg.local", password="another-password-1")
        assert auth.get_user("taken@dg.local")["password_hash"] == record["password_hash"]

    def test_weak_password_is_a_400_and_creates_nothing(self, local):
        response = _register(_client(), password="short")
        assert response.status_code == 400
        assert _code(response) == "REGISTRATION_INVALID"
        assert auth.get_user("newcomer@dg.local") is None

    def test_overlong_password_is_a_400(self, local):
        response = _register(_client(), password="x" * (auth.PASSWORD_MAX_LENGTH + 1))
        assert response.status_code == 400
        assert auth.get_user("newcomer@dg.local") is None

    def test_invalid_username_is_a_422(self, local):
        response = _register(_client(), username="no spaces allowed")
        assert response.status_code == 422
        assert _code(response) == "USERNAME_INVALID"

    def test_missing_csrf_header_is_a_403(self, local):
        response = _client().post(
            "/auth/register", json={"username": "newcomer@dg.local", "password": GOOD_PASSWORD}
        )
        assert response.status_code == 403
        assert _code(response) == "CSRF_HEADER_REQUIRED"
        assert auth.get_user("newcomer@dg.local") is None

    def test_a_logged_in_caller_can_still_register_another_account(self, local):
        client = _client()
        assert _register(client, username="first@dg.local").status_code == 201
        assert _register(client, username="second@dg.local").status_code == 201
        assert auth.get_user("second@dg.local") is not None


class TestThrottle:
    def test_repeated_failures_on_one_username_lock_it(self, local):
        client = _client()
        # five free failures, the sixth starts the lock (same as login)
        for _ in range(auth.THROTTLE_LIMIT_USER + 1):
            assert _register(client, password="short").status_code == 400

        locked = _register(client, password=GOOD_PASSWORD)

        assert locked.status_code == 429
        assert _code(locked) == "AUTH_THROTTLED"
        assert int(locked.headers["Retry-After"]) > 0
        assert auth.get_user("newcomer@dg.local") is None

    def test_duplicate_attempts_count_toward_the_same_throttle(self, local):
        auth_fixtures.make_user("taken@dg.local")
        client = _client()
        for _ in range(auth.THROTTLE_LIMIT_USER + 1):
            assert _register(client, username="taken@dg.local").status_code == 400
        assert _register(client, username="taken@dg.local").status_code == 429

    def test_another_username_is_not_locked(self, local):
        client = _client()
        for _ in range(auth.THROTTLE_LIMIT_USER + 1):
            _register(client, username="locked@dg.local", password="short")
        assert _register(client, username="other@dg.local").status_code == 201

    def test_login_lock_carries_over_to_register(self, local):
        """Register and login share the per-username counter."""
        auth.throttle_record_failure("user:newcomer@dg.local", limit=0)
        auth.throttle_record_failure("user:newcomer@dg.local", limit=0)
        response = _register(_client())
        assert response.status_code == 429


# -- multi-user profile, default -----------------------------------------------


class TestMultiUserDefault:
    def test_options_reports_disabled(self, multi_user):
        response = _client().get("/auth/options")
        assert response.status_code == 200
        assert response.json() == {"selfRegistration": False}

    def test_register_is_404_like_an_unknown_route(self, multi_user):
        client = _client()
        unknown = client.post("/auth/definitely-not-a-route", json={}, headers=CSRF)

        response = _register(client)

        assert response.status_code == 404
        assert unknown.status_code == 404
        assert response.json() == unknown.json()
        assert auth.get_user("newcomer@dg.local") is None
        assert auth.SESSION_COOKIE_NAME not in response.headers.get("set-cookie", "")

    def test_register_is_404_even_without_the_csrf_header(self, multi_user):
        """A 403 for the missing header would reveal that the route exists."""
        client = _client()
        bare = client.post("/auth/register", json={"username": "a@dg.local", "password": GOOD_PASSWORD})
        unknown = client.post("/auth/definitely-not-a-route", json={})
        assert bare.status_code == 404
        assert bare.json() == unknown.json()

    def test_invite_path_still_works(self, multi_user):
        auth_fixtures.make_user("owner@dg.local", memberships={"P1": "owner"})
        owner = _client()
        owner.cookies.set(
            auth.SESSION_COOKIE_NAME, auth_fixtures.session_cookie_for("owner@dg.local")
        )
        minted = owner.post(
            "/auth/invites",
            json={"username": "guest@dg.local", "project": "P1", "role": "viewer"},
            headers=CSRF,
        )
        assert minted.status_code == 200
        accepted = _client().post(
            "/auth/accept-invite",
            json={"inviteCode": minted.json()["inviteCode"], "password": GOOD_PASSWORD},
            headers=CSRF,
        )
        assert accepted.status_code == 200


# -- the toggle overrides the profile in both directions ----------------------


class TestToggleOverrides:
    def test_multi_user_with_toggle_true_allows_registration(self, multi_user, monkeypatch):
        monkeypatch.setenv("DG_ALLOW_SELF_REGISTRATION", "true")
        client = _client()
        assert client.get("/auth/options").json() == {"selfRegistration": True}
        assert _register(client).status_code == 201

    def test_local_with_toggle_false_disables_registration(self, local, monkeypatch):
        monkeypatch.setenv("DG_ALLOW_SELF_REGISTRATION", "false")
        client = _client()
        assert client.get("/auth/options").json() == {"selfRegistration": False}
        response = _register(client)
        assert response.status_code == 404
        assert response.json() == client.post("/auth/nope", json={}, headers=CSRF).json()
        assert auth.get_user("newcomer@dg.local") is None

    def test_toggle_is_case_insensitive(self, local, monkeypatch):
        monkeypatch.setenv("DG_ALLOW_SELF_REGISTRATION", "FALSE")
        assert _client().get("/auth/options").json() == {"selfRegistration": False}

    def test_an_unreadable_toggle_fails_closed_at_request_time(self, local, monkeypatch):
        monkeypatch.setenv("DG_ALLOW_SELF_REGISTRATION", "maybe")
        client = _client()
        assert client.get("/auth/options").json() == {"selfRegistration": False}
        assert _register(client).status_code == 404


class TestOptionsIsMinimal:
    def test_options_carries_nothing_but_the_flag(self, local):
        response = _client().get("/auth/options")
        assert set(response.json()) == {"selfRegistration"}
        assert isinstance(response.json()["selfRegistration"], bool)

    def test_options_needs_no_credentials_or_csrf(self, local):
        assert _client().get("/auth/options").status_code == 200
