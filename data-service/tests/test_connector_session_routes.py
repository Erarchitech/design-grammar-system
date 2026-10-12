"""Phase 1308 plan 06 (WEBUI-07, WEBUI-10, D-25, D-26, D-29, D-34, D-36): the
``dgk_`` connector sign-in session as a principal and the mint/revoke routes.

Every request goes through the real ``require_principal``; credentials come
from the 1205-08 fixtures and from ``connector_session`` itself.
"""

from __future__ import annotations

import hashlib
import os
import secrets
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


def _stored_legacy_token(project):
    """A retired ``dgc_`` token that is still present, hashed and non-revoked, in
    the credential store -- the strongest case a refusal has to cover (D-26).
    Built without the legacy minting helpers."""
    token = "dgc_" + secrets.token_urlsafe(32)
    connectors.save_credentials(
        connectors.load_credentials()
        + [
            {
                "credential_id": secrets.token_hex(16),
                "connector_id": GH,
                "label": "",
                "project": project,
                "token_hash": hashlib.sha256(token.encode()).hexdigest(),
                "created_at": "2026-01-01T00:00:00+00:00",
                "revoked": False,
                "last_connection": None,
            }
        ]
    )
    return token


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


def test_resolver_refuses_a_stored_legacy_dgc_token():
    token = _stored_legacy_token(P1)
    assert auth.resolve_connector_principal(token) is None


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


# -- POST /auth/connector-session (D-25, D-29, D-34, D-36) -------------------

MINT_KEYS = {"token", "project", "connectorId", "username", "company", "expiresAt", "expiresInSeconds"}


def _mint(client, username, *, project=P1, connector_id=GH, headers=None):
    body = {"connector_id": connector_id}
    if project is not None:
        body["project"] = project
    return client.post(
        "/auth/connector-session",
        json=body,
        headers=headers if headers is not None else _session_headers(username),
    )


def test_owner_mint_answers_201_with_the_exact_shape(client):
    response = _mint(client, OWNER)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == MINT_KEYS | {"neo4j"}
    assert body["token"].startswith(connector_session.SESSION_TOKEN_PREFIX)
    assert body["project"] == P1 and body["connectorId"] == GH and body["username"] == OWNER
    assert body["expiresInSeconds"] == connector_session.DEFAULT_TTL_SECONDS
    assert response.headers["cache-control"] == "no-store"


def test_minted_token_authenticates_on_a_connector_route(client):
    token = _mint(client, OWNER).json()["token"]
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code not in (401, 403), response.text


def test_admin_on_an_existing_project_is_exempt(client):
    response = _mint(client, ROOT)
    assert response.status_code == 201, response.text
    assert response.json()["username"] == ROOT


def test_admin_on_a_project_without_members_is_forbidden(client):
    response = _mint(client, ROOT, project="Ghost")
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize("who", [EDITOR, VIEWER])
def test_editor_and_viewer_with_a_grant_get_a_session(client, who):
    _grant(who)
    response = _mint(client, who)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("who", [EDITOR, VIEWER])
def test_editor_and_viewer_without_a_grant_are_refused(client, who):
    response = _mint(client, who)
    assert response.status_code == 403
    assert _code(response) == "CONNECTOR_ACCESS_REQUIRED"
    assert not auth._load(connector_session._file(), "sessions")


def test_a_grant_for_another_connector_does_not_help(client):
    _grant(EDITOR, connector_id="revit")
    response = _mint(client, EDITOR)
    assert response.status_code == 403
    assert _code(response) == "CONNECTOR_ACCESS_REQUIRED"


def test_non_member_is_forbidden(client):
    response = _mint(client, OUTSIDER)
    assert response.status_code == 403
    assert _code(response) == "PROJECT_FORBIDDEN"


@pytest.mark.parametrize("connector_id", ["nonesuch", "degram"])
def test_unknown_connector_and_degram_are_404(client, connector_id):
    response = _mint(client, OWNER, connector_id=connector_id)
    assert response.status_code == 404
    assert _code(response) == "CONNECTOR_NOT_FOUND"


def test_invalid_project_name_is_422(client):
    response = _mint(client, OWNER, project="../x")
    assert response.status_code == 422
    assert _code(response) == "PROJECT_NAME_INVALID"


def test_multi_user_profile_withholds_the_neo4j_bundle(client, monkeypatch):
    monkeypatch.setenv("DG_DEPLOYMENT", "multi-user")
    response = _mint(client, OWNER)
    assert response.status_code == 201, response.text
    assert set(response.json()) == MINT_KEYS


def test_local_profile_carries_the_neo4j_bundle(client):
    body = _mint(client, OWNER).json()
    assert set(body["neo4j"]) == {"uri", "user", "password", "database"}


# -- blank project (D-36) ---------------------------------------------------


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_project_picks_the_only_eligible_project(client, blank):
    response = _mint(client, OWNER, project=blank)
    assert response.status_code == 201, response.text
    assert response.json()["project"] == P1


def test_blank_project_with_two_eligible_is_422_listing_both(client):
    auth.set_membership(OWNER, P2, "owner")
    response = _mint(client, OWNER, project=None)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "PROJECT_REQUIRED"
    assert P1 in detail["hint"] and P2 in detail["hint"]


def test_blank_project_counts_only_authorized_projects(client):
    auth.set_membership(EDITOR, P2, "owner")  # exempt in P2, needs a grant in P1
    response = _mint(client, EDITOR, project=None)
    assert response.status_code == 201, response.text
    assert response.json()["project"] == P2


def test_blank_project_with_none_eligible_is_403_access_required(client):
    response = _mint(client, EDITOR, project=None)
    assert response.status_code == 403
    assert _code(response) == "CONNECTOR_ACCESS_REQUIRED"


def test_blank_project_hint_never_lists_foreign_projects(client):
    auth.set_membership("someone@dg.local", "Secret", "owner")
    auth.set_membership(OWNER, P2, "owner")
    hint = _mint(client, OWNER, project=None).json()["detail"]["hint"]
    assert "Secret" not in hint


# -- who can mint (T-1308-06-02, T-1308-06-05) --------------------------------


def test_mint_without_csrf_is_refused(client):
    headers = _session_headers(OWNER)
    headers.pop(auth.CSRF_HEADER)
    response = _mint(client, OWNER, headers=headers)
    assert response.status_code == 403
    assert _code(response) == "CSRF_HEADER_REQUIRED"


def test_mint_without_credentials_is_401(client):
    response = _mint(client, OWNER, headers={})
    assert response.status_code == 401


def test_a_dgk_session_cannot_mint_another_session(client):
    token, _ = connector_session.issue(username=OWNER, project=P1, connector_id=GH)
    response = _mint(client, OWNER, headers={**_bearer(token), **CSRF})
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_a_delegated_token_cannot_mint_a_session(client):
    minted = client.post(
        "/auth/delegated-token", json={"project": P1}, headers=_session_headers(OWNER)
    )
    assert minted.status_code == 201, minted.text
    token = minted.json()["token"]
    assert token.startswith(delegation.DELEGATED_TOKEN_PREFIX)
    response = _mint(client, OWNER, headers={**_bearer(token), **CSRF})
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_a_delegated_token_cannot_reach_connector_write_routes(client):
    token = client.post(
        "/auth/delegated-token", json={"project": P1}, headers=_session_headers(OWNER)
    ).json()["token"]
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_a_legacy_dgc_token_cannot_mint(client):
    token = _stored_legacy_token(P1)
    response = _mint(client, OWNER, headers={**_bearer(token), **CSRF})
    assert response.status_code == 401
    assert _code(response) == "CONNECTOR_AUTH_FAILED"


def test_the_store_holds_only_the_hash(client):
    token = _mint(client, OWNER).json()["token"]
    raw = connector_session._file().read_text(encoding="utf-8")
    assert token not in raw


# -- DELETE /auth/connector-session ------------------------------------------


def test_delete_with_the_session_answers_204_then_the_token_is_ended(client):
    token = _mint(client, OWNER).json()["token"]
    response = client.delete("/auth/connector-session", headers=_bearer(token))
    assert response.status_code == 204
    again = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert again.status_code == 401
    assert _code(again) == "CONNECTOR_SESSION_ENDED"


def test_delete_twice_the_second_is_401_ended(client):
    token = _mint(client, OWNER).json()["token"]
    assert client.delete("/auth/connector-session", headers=_bearer(token)).status_code == 204
    second = client.delete("/auth/connector-session", headers=_bearer(token))
    assert second.status_code == 401
    assert _code(second) == "CONNECTOR_SESSION_ENDED"


def test_delete_with_a_cookie_only_is_refused(client):
    response = client.delete("/auth/connector-session", headers=_session_headers(OWNER))
    assert response.status_code == 403
    assert _code(response) == "PRINCIPAL_NOT_PERMITTED"


def test_delete_without_credentials_is_401(client):
    assert client.delete("/auth/connector-session").status_code == 401


def test_delete_revokes_only_the_presented_session(client):
    first = _mint(client, OWNER).json()["token"]
    second = _mint(client, OWNER).json()["token"]
    assert client.delete("/auth/connector-session", headers=_bearer(first)).status_code == 204
    assert client.get(f"/validation/view/{P1}", headers=_bearer(second)).status_code not in (401, 403)


def test_policy_rows_are_the_documented_shape():
    import route_policy

    mint = route_policy.ROUTE_POLICIES[("POST", "/auth/connector-session")]
    revoke = route_policy.ROUTE_POLICIES[("DELETE", "/auth/connector-session")]
    assert mint.principals == frozenset({route_policy.PRINCIPAL_SESSION})
    assert mint.project_source is None
    assert revoke.principals == frozenset({route_policy.PRINCIPAL_CONNECTOR})
    assert revoke.project_source is None


# -- the retired dgc_ token is accepted nowhere (D-26, T-1308-13-01) ---------

LEGACY_SWEEP = [
    ("POST", "/connectors/heartbeat", None),
    ("POST", "/designstate/capture", {"project": P1, "statePayloadJson": "{}"}),
    ("POST", "/validation/publish", {"project": P1}),
    ("POST", "/computgraph/publish", {"project": P1}),
    ("GET", f"/validation/view/{P1}", None),
    ("DELETE", "/auth/connector-session", None),
]


@pytest.mark.parametrize("method,path,body", LEGACY_SWEEP, ids=[f"{m} {p}" for m, p, _ in LEGACY_SWEEP])
def test_a_stored_legacy_token_answers_401_on_every_connector_route(client, method, path, body):
    token = _stored_legacy_token(P1)
    kwargs = {"headers": _bearer(token)}
    if body is not None:
        kwargs["json"] = body
    response = client.request(method, path, **kwargs)
    assert response.status_code == 401, (method, path, response.status_code, response.text)
    assert _code(response) == "CONNECTOR_AUTH_FAILED"
    detail = response.json()["detail"]
    assert "POST /auth/connector-session" in detail["hint"]
    assert token not in response.text


def test_the_legacy_refusal_leaves_the_credential_row_untouched(client):
    token = _stored_legacy_token(P1)
    before = connectors.load_credentials()
    assert client.post("/connectors/heartbeat", headers=_bearer(token)).status_code == 401
    assert connectors.load_credentials() == before


# -- access-change cascades (D-33) -------------------------------------------


def _assert_ended(client, token, connector_id=GH):
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code == 401, response.text
    assert _code(response) == "CONNECTOR_SESSION_ENDED"
    status = connector_session.status_for(connector_id, projects={P1})
    assert status["status"] == "stale"
    assert status["active_sessions"] == 0


def _assert_live(client, token):
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code not in (401, 403), response.text


def test_password_change_ends_all_of_the_users_connector_sessions(client):
    # The autouse fixture creates OWNER; set a known test password for this request.
    password = "current-test-password-123"
    auth.set_password(OWNER, password)
    first = _mint(client, OWNER).json()["token"]
    second = _mint(client, OWNER).json()["token"]
    other = _mint(client, ROOT).json()["token"]
    changed = client.post(
        "/auth/password",
        json={"currentPassword": password, "newPassword": "new-test-password-123"},
        headers=_session_headers(OWNER),
    )
    assert changed.status_code == 204, changed.text
    for token in (first, second):
        response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
        assert response.status_code == 401 and _code(response) == "CONNECTOR_SESSION_ENDED"
    assert connector_session.status_for(GH, projects={P1})["active_sessions"] == 1
    _assert_live(client, other)


def test_member_removal_ends_only_that_members_project_sessions(client):
    _grant(EDITOR)
    token = _mint(client, EDITOR).json()["token"]
    other = _mint(client, OWNER).json()["token"]
    removed = client.delete(f"/projects/{P1}/members/{EDITOR}", headers=_session_headers(OWNER))
    assert removed.status_code == 204, removed.text
    response = client.get(f"/validation/view/{P1}", headers=_bearer(token))
    assert response.status_code == 401 and _code(response) == "CONNECTOR_SESSION_ENDED"
    assert connector_session.status_for(GH, projects={P1})["active_sessions"] == 1
    _assert_live(client, other)


def test_company_reassignment_ends_project_sessions_even_if_reassigned_back(client):
    token = _mint(client, OWNER).json()["token"]
    changed = client.put(
        f"/projects/{P1}/company", json={"company": "Acme"}, headers=_session_headers(ROOT)
    )
    assert changed.status_code == 200, changed.text
    _assert_ended(client, token)
    restored = client.put(
        f"/projects/{P1}/company", json={"company": "Other"}, headers=_session_headers(ROOT)
    )
    assert restored.status_code == 200
    _assert_ended(client, token)


def test_access_revoke_ends_affected_connector_but_not_other_grants(client):
    grant = _grant(EDITOR)
    _grant(EDITOR, connector_id="revit")
    token = _mint(client, EDITOR).json()["token"]
    revit = _mint(client, EDITOR, connector_id="revit").json()["token"]
    revoked = client.delete(
        f"/projects/{P1}/connector-access/{grant['access_id']}", headers=_session_headers(OWNER)
    )
    assert revoked.status_code == 204, revoked.text
    _assert_ended(client, token)
    _assert_live(client, revit)


def test_revoking_an_old_access_does_not_end_a_replacement_session(client):
    old = _grant(EDITOR)
    replacement = _grant(EDITOR)
    token = _mint(client, EDITOR).json()["token"]
    removed = client.delete(
        f"/projects/{P1}/connector-access/{old['access_id']}", headers=_session_headers(OWNER)
    )
    assert removed.status_code == 204, removed.text
    assert replacement["active"]
    _assert_live(client, token)


def test_revoking_an_access_does_not_end_an_exempt_owners_session(client):
    grant = _grant(EDITOR)
    auth.set_membership(EDITOR, P1, "owner")
    token = _mint(client, EDITOR).json()["token"]
    removed = client.delete(
        f"/projects/{P1}/connector-access/{grant['access_id']}", headers=_session_headers(OWNER)
    )
    assert removed.status_code == 204, removed.text
    _assert_live(client, token)


def test_put_member_demotion_ends_unauthorized_session(client):
    auth.set_membership(EDITOR, P1, "owner")  # keep an owner after demoting OWNER
    token = _mint(client, OWNER).json()["token"]
    changed = client.put(
        f"/projects/{P1}/members/{OWNER}",
        json={"role": "editor"},
        headers=_session_headers(EDITOR),
    )
    assert changed.status_code == 200, changed.text
    _assert_ended(client, token)


def test_put_member_demotion_keeps_session_with_a_grant(client):
    auth.set_membership(EDITOR, P1, "owner")
    _grant(OWNER)
    token = _mint(client, OWNER).json()["token"]
    changed = client.put(
        f"/projects/{P1}/members/{OWNER}",
        json={"role": "editor"},
        headers=_session_headers(EDITOR),
    )
    assert changed.status_code == 200, changed.text
    _assert_live(client, token)


def test_existing_account_invite_demotion_ends_unauthorized_session(client):
    auth.set_membership(EDITOR, P1, "owner")
    token = _mint(client, OWNER).json()["token"]
    changed = client.post(
        "/auth/invites",
        json={"project": P1, "username": OWNER, "role": "viewer"},
        headers=_session_headers(EDITOR),
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "member-added"
    _assert_ended(client, token)


def test_accept_invite_cannot_lower_role_or_end_a_valid_session(client):
    password = "current-test-password-123"
    auth.set_password(OWNER, password)
    token = _mint(client, OWNER).json()["token"]
    code, _ = auth.create_invite(OWNER, P1, "viewer", created_by=EDITOR)
    accepted = client.post(
        "/auth/accept-invite",
        json={"inviteCode": code, "password": password},
        headers=CSRF,
    )
    assert accepted.status_code == 200, accepted.text
    assert auth.get_role(OWNER, P1) == "owner"
    _assert_live(client, token)


def test_accept_invite_role_raise_preserves_authorized_session(client):
    _grant(EDITOR)
    token = _mint(client, EDITOR).json()["token"]
    password = "current-test-password-123"
    auth.set_password(EDITOR, password)
    code, _ = auth.create_invite(EDITOR, P1, "owner", created_by=OWNER)
    accepted = client.post(
        "/auth/accept-invite",
        json={"inviteCode": code, "password": password},
        headers=CSRF,
    )
    assert accepted.status_code == 200, accepted.text
    assert auth.get_role(EDITOR, P1) == "owner"
    _assert_live(client, token)
