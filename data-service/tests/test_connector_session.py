"""Phase 1308 plan 03 (WEBUI-07, D-25..D-29, D-32, D-33): the ``dgk_`` connector
sign-in session store and the owner/admin exemption helpers.

Module-level tests: the store is redirected to ``tmp_path`` through the same
``auth.MEMBERSHIPS_FILE`` redirect the delegated-token tests use; users,
memberships and grants are real (``auth_fixtures``, ``connector_access``).
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import company  # noqa: E402
import connector_access  # noqa: E402
import connector_session  # noqa: E402
import connectors  # noqa: E402
import auth_fixtures  # noqa: E402

DG_TEST_PRINCIPAL = "none"

PROJECT = "p"
OTHER = "q"
OWNER = "o@dg.local"
EDITOR = "e@dg.local"
VIEWER = "v@dg.local"
ROOT = "root@dg.local"
NOW = 1_800_000_000


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    monkeypatch.delenv(connector_session.TTL_ENV, raising=False)
    auth_fixtures.make_user(OWNER, memberships={PROJECT: "owner"})
    auth_fixtures.make_user(EDITOR, memberships={PROJECT: "editor"})
    auth_fixtures.make_user(VIEWER, memberships={PROJECT: "viewer"})
    auth_fixtures.make_user(ROOT, is_admin=True)


def _issue(username, project=PROJECT, connector_id="grasshopper", now=NOW):
    return connector_session.issue(
        username=username, project=project, connector_id=connector_id, now=now
    )


def _code(exc_info) -> str:
    return exc_info.value.detail["code"]


def _rows() -> list[dict]:
    return auth._load(connector_session._file(), "sessions")


def _grant(username, project=PROJECT, connector_id="grasshopper"):
    return connector_access.issue_access(project, username, connector_id, OWNER, now=NOW)


# -- exemption helpers ------------------------------------------------------


def test_is_exempt_matrix():
    assert connector_access.is_exempt("owner") is True
    assert connector_access.is_exempt("editor") is False
    assert connector_access.is_exempt("viewer") is False
    assert connector_access.is_exempt(None) is False


def test_is_authorized_owner_needs_no_row():
    assert connector_access.is_authorized(OWNER, PROJECT, "grasshopper", role="owner") is True


def test_is_authorized_editor_needs_a_matching_active_row():
    assert connector_access.is_authorized(EDITOR, PROJECT, "grasshopper", role="editor") is False
    _grant(EDITOR)
    assert connector_access.is_authorized(EDITOR, PROJECT, "grasshopper", role="editor") is True
    # another connector, another project
    assert connector_access.is_authorized(EDITOR, PROJECT, "revit", role="editor") is False
    assert connector_access.is_authorized(EDITOR, OTHER, "grasshopper", role="editor") is False


def test_is_authorized_none_role_without_row_is_false():
    assert connector_access.is_authorized(VIEWER, PROJECT, "grasshopper", role=None) is False


# -- issue ------------------------------------------------------------------


def test_effective_role_for_elevates_admin_only():
    assert connector_session.effective_role_for(ROOT, PROJECT) == "owner"
    assert connector_session.effective_role_for(OWNER, PROJECT) == "owner"
    assert connector_session.effective_role_for(VIEWER, PROJECT) == "viewer"
    assert connector_session.effective_role_for(VIEWER, OTHER) is None


def test_issue_mints_prefixed_token_and_stores_only_the_hash():
    token, record = _issue(OWNER)
    assert connector_session.SESSION_TOKEN_PREFIX == "dgk_"
    assert token.startswith("dgk_") and len(token) > 40
    assert "token_hash" not in record
    assert record["session_id"]
    assert record["username"] == OWNER
    assert record["project"] == PROJECT
    assert record["connector_id"] == "grasshopper"
    assert record["issued_at"] == NOW
    assert record["expires_at"] == NOW + 28800
    assert record["revoked"] is False
    content = connector_session._file().read_text(encoding="utf-8")
    assert token not in content
    assert connector_session._hash(token) in content
    assert [r["token_hash"] for r in _rows()] == [connector_session._hash(token)]


def test_issue_records_the_project_company_and_last_seen():
    company.set_project_company(PROJECT, "Acme")
    _, record = _issue(OWNER)
    assert record["company"] == "Acme"
    assert record["last_seen"] == NOW


def test_issue_prunes_rows_past_retention():
    old_token, _ = _issue(OWNER, now=NOW)
    far = NOW + 28800 + 90 * 86400 + 1
    _issue(OWNER, now=far)
    hashes = {r["token_hash"] for r in _rows()}
    assert connector_session._hash(old_token) not in hashes
    assert len(hashes) == 1


def test_issue_keeps_expired_rows_inside_retention():
    old_token, _ = _issue(OWNER, now=NOW)
    _issue(OWNER, now=NOW + 28800 + 86400)
    assert connector_session._hash(old_token) in {r["token_hash"] for r in _rows()}


# -- authenticate -----------------------------------------------------------


def test_authenticate_owner_round_trip():
    token, _ = _issue(OWNER)
    record = connector_session.authenticate(token, now=NOW + 5)
    assert record["username"] == OWNER
    assert record["project"] == PROJECT
    assert record["connector_id"] == "grasshopper"
    assert "token_hash" not in record


def test_authenticate_admin_without_membership():
    token, _ = _issue(ROOT)
    record = connector_session.authenticate(token, now=NOW + 5)
    assert record["username"] == ROOT


@pytest.mark.parametrize("who", [EDITOR, VIEWER])
def test_authenticate_member_with_grant(who):
    _grant(who)
    token, _ = _issue(who)
    assert connector_session.authenticate(token, now=NOW + 5)["username"] == who


def test_authenticate_editor_without_grant_is_403_and_row_survives():
    token, _ = _issue(EDITOR)
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=NOW + 5)
    assert exc.value.status_code == 403
    assert _code(exc) == "CONNECTOR_ACCESS_REQUIRED"
    assert _rows()[0]["revoked"] is False
    _grant(EDITOR)
    assert connector_session.authenticate(token, now=NOW + 6)["username"] == EDITOR


def test_authenticate_unknown_token_is_auth_failed():
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate("dgk_nope", now=NOW)
    assert exc.value.status_code == 401
    assert _code(exc) == "CONNECTOR_AUTH_FAILED"


def test_authenticate_revoked_is_session_ended():
    token, _ = _issue(OWNER)
    assert connector_session._revoke_where(lambda r: True) == 1
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=NOW + 5)
    assert exc.value.status_code == 401
    assert _code(exc) == "CONNECTOR_SESSION_ENDED"


def test_authenticate_expiry_boundary():
    token, record = _issue(OWNER)
    expires_at = record["expires_at"]
    assert connector_session.authenticate(token, now=expires_at - 1)["username"] == OWNER
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=expires_at)
    assert exc.value.status_code == 401
    assert _code(exc) == "CONNECTOR_SESSION_EXPIRED"


def test_authenticate_revoked_wins_over_expired():
    token, record = _issue(OWNER)
    connector_session.revoke_token(token)
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=record["expires_at"] + 10)
    assert _code(exc) == "CONNECTOR_SESSION_ENDED"


def test_authenticate_after_user_deleted_ends_and_marks_revoked():
    token, _ = _issue(OWNER)
    auth._save(auth.USERS_FILE, "users", [u for u in auth._load(auth.USERS_FILE, "users") if u["username"] != OWNER])
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=NOW + 5)
    assert _code(exc) == "CONNECTOR_SESSION_ENDED"
    assert _rows()[0]["revoked"] is True


def test_authenticate_after_company_change_ends_and_marks_revoked():
    company.set_project_company(PROJECT, "Acme")
    token, _ = _issue(OWNER)
    company.set_project_company(PROJECT, "Other Co")
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=NOW + 5)
    assert _code(exc) == "CONNECTOR_SESSION_ENDED"
    assert _rows()[0]["revoked"] is True


def test_authenticate_after_grant_revoked_is_refused_next_request():
    grant = _grant(VIEWER)
    token, _ = _issue(VIEWER)
    assert connector_session.authenticate(token, now=NOW + 5)
    assert connector_access.revoke_access(PROJECT, grant["access_id"], OWNER)
    with pytest.raises(HTTPException) as exc:
        connector_session.authenticate(token, now=NOW + 6)
    assert _code(exc) == "CONNECTOR_ACCESS_REQUIRED"


@pytest.mark.parametrize("value", ["", None, "dgd_abc", "Bearer dgk_x", "abc"])
def test_authenticate_non_dgk_input_returns_none(value):
    assert connector_session.authenticate(value, now=NOW) is None


def test_raw_token_never_in_store_bytes_after_mutations():
    token, _ = _issue(OWNER)
    connector_session.authenticate(token, now=NOW + 1)
    connector_session.revoke_token(token)
    assert token.encode() not in connector_session._file().read_bytes()


# -- Task 2: revoke cascades, touch, status, public answer, TTL --------------


def _live_count() -> int:
    return sum(1 for r in _rows() if not r["revoked"])


def test_revoke_token_true_once_false_for_unknown():
    token, _ = _issue(OWNER)
    assert connector_session.revoke_token(token) is True
    assert connector_session.revoke_token(token) is False
    assert connector_session.revoke_token("dgk_unknown") is False
    assert connector_session.revoke_token("") is False


def test_revoke_for_user_touches_only_that_user():
    _issue(OWNER)
    _issue(OWNER, connector_id="revit")
    _issue(ROOT)
    assert connector_session.revoke_for_user(OWNER) == 2
    assert connector_session.revoke_for_user(OWNER) == 0
    assert _live_count() == 1


def test_revoke_for_user_project():
    auth.set_membership(OWNER, OTHER, "owner")
    _issue(OWNER, project=PROJECT)
    _issue(OWNER, project=OTHER)
    assert connector_session.revoke_for_user_project(OWNER, PROJECT) == 1
    assert _live_count() == 1


def test_revoke_for_project():
    _issue(OWNER, project=PROJECT)
    _issue(ROOT, project=PROJECT)
    _issue(ROOT, project=OTHER)
    assert connector_session.revoke_for_project(PROJECT) == 2
    assert _live_count() == 1


def test_revoke_for_connector_grant_matches_the_triple_only():
    _issue(VIEWER, connector_id="grasshopper")
    _issue(VIEWER, connector_id="revit")
    _issue(EDITOR, connector_id="grasshopper")
    assert connector_session.revoke_for_connector_grant(VIEWER, PROJECT, "grasshopper") == 1
    assert _live_count() == 2


def test_revoke_unauthorized_keeps_authorized_sessions():
    _grant(VIEWER, connector_id="grasshopper")
    _issue(VIEWER, connector_id="grasshopper")
    _issue(VIEWER, connector_id="revit")  # never granted
    _issue(OWNER, connector_id="revit")  # exempt, other user
    assert connector_session.revoke_unauthorized(VIEWER, PROJECT) == 1
    live = [(r["username"], r["connector_id"]) for r in _rows() if not r["revoked"]]
    assert sorted(live) == [(OWNER, "revit"), (VIEWER, "grasshopper")]


def test_revoke_unauthorized_after_demotion():
    _issue(OWNER, connector_id="grasshopper")
    auth.set_membership(OWNER, PROJECT, "viewer")
    assert connector_session.revoke_unauthorized(OWNER, PROJECT) == 1


def test_touch_updates_last_seen_of_a_live_session():
    token, _ = _issue(OWNER)
    record = connector_session.touch(token, now=NOW + 60)
    assert record["last_seen"] == NOW + 60
    assert _rows()[0]["last_seen"] == NOW + 60
    assert "token_hash" not in record


def test_touch_none_for_revoked_expired_unknown_and_foreign_prefix():
    token, record = _issue(OWNER)
    assert connector_session.touch(token, now=record["expires_at"]) is None
    assert connector_session.touch("dgk_unknown", now=NOW) is None
    assert connector_session.touch("abc", now=NOW) is None
    assert connector_session.touch(None, now=NOW) is None
    connector_session.revoke_token(token)
    assert connector_session.touch(token, now=NOW + 1) is None


def test_status_never_connected_without_rows():
    answer = connector_session.status_for("grasshopper", projects={PROJECT}, now=NOW)
    assert answer == {"status": "never_connected", "active_sessions": 0, "last_sign_in": None}


def test_status_active_counts_live_sessions_and_last_sign_in():
    _issue(OWNER, now=NOW)
    _issue(ROOT, now=NOW + 100)
    answer = connector_session.status_for("grasshopper", projects={PROJECT}, now=NOW + 200)
    assert answer["status"] == "active"
    assert answer["active_sessions"] == 2
    assert answer["last_sign_in"] == "2027-01-15T08:01:40Z"


def test_status_stale_when_rows_exist_but_none_live():
    token, record = _issue(OWNER, now=NOW)
    later = record["expires_at"] + 1
    assert connector_session.status_for("grasshopper", projects={PROJECT}, now=later)["status"] == "stale"
    _, _ = _issue(OWNER, now=later)
    connector_session.revoke_for_user(OWNER)
    answer = connector_session.status_for("grasshopper", projects={PROJECT}, now=later)
    assert answer["status"] == "stale"
    assert answer["active_sessions"] == 0
    assert answer["last_sign_in"] is not None


def test_status_boundary_expires_at_is_not_live():
    _, record = _issue(OWNER, now=NOW)
    at = connector_session.status_for("grasshopper", projects=None, now=record["expires_at"])
    before = connector_session.status_for("grasshopper", projects=None, now=record["expires_at"] - 1)
    assert at["status"] == "stale"
    assert before["status"] == "active"


def test_status_projects_filter_and_none_means_all():
    _issue(ROOT, project=OTHER)
    assert connector_session.status_for("grasshopper", projects={PROJECT}, now=NOW)["status"] == "never_connected"
    assert connector_session.status_for("grasshopper", projects={OTHER}, now=NOW)["status"] == "active"
    assert connector_session.status_for("grasshopper", projects=None, now=NOW)["status"] == "active"
    assert connector_session.status_for("grasshopper", projects=set(), now=NOW)["status"] == "never_connected"


def test_status_is_per_connector():
    _issue(OWNER, connector_id="revit")
    assert connector_session.status_for("grasshopper", projects=None, now=NOW)["status"] == "never_connected"
    assert connector_session.status_for("revit", projects=None, now=NOW)["status"] == "active"


def test_public_answer_keys_and_expires_at_format():
    token, record = _issue(OWNER)
    answer = connector_session.public_answer(token, record)
    assert set(answer) == {
        "token", "project", "connectorId", "username", "company", "expiresAt", "expiresInSeconds",
    }
    assert answer["token"] == token
    assert answer["connectorId"] == "grasshopper"
    assert answer["username"] == OWNER
    assert answer["expiresAt"] == "2027-01-15T16:00:00Z"
    assert answer["expiresInSeconds"] == 28800


def test_public_answer_adds_neo4j_only_when_given():
    token, record = _issue(OWNER)
    bundle = {"uri": "bolt://localhost:7687", "user": "u", "password": "p", "database": "neo4j"}
    assert "neo4j" not in connector_session.public_answer(token, record)
    assert connector_session.public_answer(token, record, neo4j=bundle)["neo4j"] == bundle


def test_ttl_env_override(monkeypatch):
    monkeypatch.setenv(connector_session.TTL_ENV, "60")
    assert connector_session.session_ttl_seconds() == 60
    _, record = _issue(OWNER)
    assert record["expires_at"] == record["issued_at"] + 60


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "", "1.5"])
def test_ttl_env_invalid_falls_back(monkeypatch, bad):
    monkeypatch.setenv(connector_session.TTL_ENV, bad)
    assert connector_session.session_ttl_seconds() == 28800


def test_ttl_accepts_explicit_env_mapping():
    assert connector_session.session_ttl_seconds({connector_session.TTL_ENV: "120"}) == 120
    assert connector_session.session_ttl_seconds({}) == 28800
