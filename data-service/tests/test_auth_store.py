"""Tests for the server-side identity store (Phase 1205 "Security and Tenancy
Release Gate", ALGN12-17, D-01/D-02/D-04/D-05/D-07/D-19).

Follows the test_connectors.py header pattern: sys.path insert so `auth` and
`connectors` import as top-level modules, and LLM_MASTER_SECRET set before
any data-service import (llm_gateway reads it at import time in some
modules). Persistence is redirected to a per-test tmp_path by patching the
module-level *_FILE globals (auth.py) and connectors.CREDENTIALS_FILE.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import auth  # noqa: E402
import connectors  # noqa: E402


@pytest.fixture(autouse=True)
def _redirect_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "auth-users.json")
    monkeypatch.setattr(auth, "SESSIONS_FILE", tmp_path / "auth-sessions.json")
    monkeypatch.setattr(auth, "MEMBERSHIPS_FILE", tmp_path / "auth-memberships.json")
    monkeypatch.setattr(auth, "INVITES_FILE", tmp_path / "auth-invites.json")
    monkeypatch.setattr(connectors, "CREDENTIALS_FILE", tmp_path / "connector-credentials.json")
    yield


# ── hash_password / verify_password (D-01) ──


def test_hash_password_uses_scrypt_encoding():
    encoded = auth.hash_password("correct horse battery staple")
    assert encoded.startswith("scrypt$16384$8$1$")


def test_verify_password_correct_and_wrong():
    encoded = auth.hash_password("correct horse battery staple")
    assert auth.verify_password("correct horse battery staple", encoded) is True
    assert auth.verify_password("wrong password entirely", encoded) is False


def test_hash_password_same_password_twice_yields_different_encodings():
    a = auth.hash_password("same-password-value")
    b = auth.hash_password("same-password-value")
    assert a != b


def test_verify_password_malformed_encoding_returns_false():
    assert auth.verify_password("whatever", "not-a-valid-encoding") is False


# ── validate_password_policy ──


def test_validate_password_policy_rejects_11_chars():
    with pytest.raises(ValueError):
        auth.validate_password_policy("a" * 11)


def test_validate_password_policy_rejects_129_chars():
    with pytest.raises(ValueError):
        auth.validate_password_policy("a" * 129)


def test_validate_password_policy_accepts_12_and_128_chars():
    auth.validate_password_policy("a" * 12)
    auth.validate_password_policy("a" * 128)


# ── normalize_username ──


def test_normalize_username_strips_and_lowercases():
    assert auth.normalize_username("  Alice@Example.com  ") == "alice@example.com"


def test_normalize_username_rejects_invalid_chars():
    with pytest.raises(ValueError):
        auth.normalize_username("no spaces allowed")


def test_normalize_username_rejects_too_short():
    with pytest.raises(ValueError):
        auth.normalize_username("ab")


# ── create_user ──


def test_create_user_refuses_duplicate_username():
    auth.create_user("alice", "correct-horse-battery")
    with pytest.raises(ValueError):
        auth.create_user("ALICE", "another-password-1234")


def test_create_user_stores_no_plaintext_password():
    auth.create_user("bob", "super-secret-passw0rd")
    text = auth.USERS_FILE.read_text(encoding="utf-8")
    assert "super-secret-passw0rd" not in text


# ── create_session / authenticate_session ──


def test_create_session_returns_dgs_token_and_authenticates():
    auth.create_user("carol", "carol-password-1234")
    token = auth.create_session("carol")
    assert token.startswith(auth.SESSION_TOKEN_PREFIX)
    record = auth.authenticate_session(token)
    assert record is not None
    assert record["username"] == "carol"


def test_raw_session_token_absent_from_sessions_file():
    auth.create_user("dave", "dave-password-1234")
    token = auth.create_session("dave")
    text = auth.SESSIONS_FILE.read_text(encoding="utf-8")
    assert token not in text


# ── expiry boundaries ──


def test_session_expiry_boundary_inclusive():
    auth.create_user("erin", "erin-password-1234")
    start = 1_000_000
    token = auth.create_session("erin", now=start)
    ttl = int(os.environ.get("DG_SESSION_TTL_SECONDS", "43200"))
    expires_at = start + ttl
    assert auth.authenticate_session(token, now=expires_at - 1) is not None
    # A fresh, separate session avoids the idle-timeout interfering with the
    # boundary-exactly-at-expiry check.
    token2 = auth.create_session("erin", now=start)
    assert auth.authenticate_session(token2, now=expires_at) is None


def test_session_idle_boundary_inclusive(monkeypatch):
    monkeypatch.setenv("DG_SESSION_IDLE_SECONDS", "100")
    auth.create_user("frank", "frank-password-1234")
    start = 2_000_000
    token = auth.create_session("frank", now=start)
    assert auth.authenticate_session(token, now=start + 100 - 1) is not None
    token2 = auth.create_session("frank", now=start)
    assert auth.authenticate_session(token2, now=start + 100) is None


def test_session_touch_updates_last_seen_only_after_interval(monkeypatch):
    monkeypatch.setenv("DG_SESSION_IDLE_SECONDS", "7200")
    auth.create_user("grace", "grace-password-1234")
    start = 3_000_000
    token = auth.create_session("grace", now=start)
    # Below the touch interval: last_seen_at must not move.
    record = auth.authenticate_session(token, now=start + 30)
    assert record["last_seen_at"] == start
    # At/above the touch interval: last_seen_at must move.
    record = auth.authenticate_session(token, now=start + auth.SESSION_TOUCH_INTERVAL_SECONDS)
    assert record["last_seen_at"] == start + auth.SESSION_TOUCH_INTERVAL_SECONDS


# ── revoke_session / revoke_user_sessions ──


def test_revoke_session_makes_token_fail():
    auth.create_user("heidi", "heidi-password-1234")
    token = auth.create_session("heidi")
    assert auth.revoke_session(token) is True
    assert auth.authenticate_session(token) is None


def test_revoke_user_sessions_keeps_excepted_token():
    auth.create_user("ivan", "ivan-password-1234")
    keep_token = auth.create_session("ivan")
    drop_token = auth.create_session("ivan")
    keep_hash = auth.hashlib.sha256(keep_token.encode()).hexdigest()
    revoked_count = auth.revoke_user_sessions("ivan", except_token_hash=keep_hash)
    assert revoked_count == 1
    assert auth.authenticate_session(keep_token) is not None
    assert auth.authenticate_session(drop_token) is None


# ── resolve_service_principal ──


def test_resolve_service_principal_matching_header(monkeypatch):
    monkeypatch.setenv("DG_SERVICE_TOKEN", "super-secret-service-token-value")
    principal = auth.resolve_service_principal("super-secret-service-token-value")
    assert principal is not None
    assert principal.kind == "service"


def test_resolve_service_principal_mismatch(monkeypatch):
    monkeypatch.setenv("DG_SERVICE_TOKEN", "super-secret-service-token-value")
    assert auth.resolve_service_principal("wrong-value") is None


def test_resolve_service_principal_unset_env_never_authenticates(monkeypatch):
    monkeypatch.delenv("DG_SERVICE_TOKEN", raising=False)
    assert auth.resolve_service_principal("") is None
    assert auth.resolve_service_principal("anything") is None


def test_resolve_service_principal_empty_env_never_authenticates(monkeypatch):
    monkeypatch.setenv("DG_SERVICE_TOKEN", "")
    assert auth.resolve_service_principal("") is None


# ── resolve_connector_principal ──


def test_resolve_connector_principal_valid_token_with_project():
    _record, token = connectors.create_credential("grasshopper", project="p1")
    principal = auth.resolve_connector_principal(token)
    assert principal is not None
    assert principal.kind == "connector"
    assert principal.bound_project == "p1"


def test_resolve_connector_principal_no_project_defaults():
    _record, token = connectors.create_credential("grasshopper")
    principal = auth.resolve_connector_principal(token)
    assert principal.bound_project == "default-project"


def test_resolve_connector_principal_revoked_returns_none():
    record, token = connectors.create_credential("grasshopper", project="p1")
    connectors.revoke_credential(record["connector_id"], record["credential_id"])
    assert auth.resolve_connector_principal(token) is None


def test_resolve_connector_principal_non_dgc_string_returns_none():
    assert auth.resolve_connector_principal("dgs_not-a-connector-token") is None
    assert auth.resolve_connector_principal("") is None


# ── deployment_profile ──


def test_deployment_profile_unset_defaults_to_local(monkeypatch):
    monkeypatch.delenv("DG_DEPLOYMENT", raising=False)
    assert auth.deployment_profile() == "local"


def test_deployment_profile_multi_user():
    assert auth.deployment_profile({"DG_DEPLOYMENT": "multi-user"}) == "multi-user"


def test_deployment_profile_invalid_raises():
    with pytest.raises(ValueError):
        auth.deployment_profile({"DG_DEPLOYMENT": "prod"})
