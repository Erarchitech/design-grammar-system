"""Tests for the known-default secret policy (Phase 1205, ALGN12-19, D-11).

Covers every behavior bullet in 1205-01-PLAN.md Task 1. Uses only synthetic
values -- never the real committed n8n password -- and monkeypatches a
synthetic digest into KNOWN_DEFAULT_SHA256 to test the digest rule without
touching the real plaintext.
"""

from __future__ import annotations

import hashlib
import logging

import pytest

import secrets_policy


# -- classify_secret --


def test_known_literal_default():
    assert secrets_policy.classify_secret("NEO4J_PASSWORD", "12345678") == [
        "known-default"
    ]


@pytest.mark.parametrize(
    "value",
    ["Change_Me-anything", "change-me-anything", "CHANGE_ME_ANYTHING"],
)
def test_known_prefix_default_case_and_separator_insensitive(value):
    assert secrets_policy.classify_secret("X", value) == ["known-default"]


@pytest.mark.parametrize("value", [None, ""])
def test_missing_value(value):
    assert secrets_policy.classify_secret("X", value) == ["missing"]


def test_missing_value_blank_after_strip():
    assert secrets_policy.classify_secret("X", "   ") == ["missing"]


def test_service_token_exact_min_length_passes():
    token = "a" * 32
    assert secrets_policy.classify_secret("DG_SERVICE_TOKEN", token) == []


def test_service_token_one_under_min_length_fails():
    token = "a" * 31
    assert secrets_policy.classify_secret("DG_SERVICE_TOKEN", token) == [
        "too-short"
    ]


def test_bootstrap_admin_password_exact_min_length_passes():
    assert secrets_policy.classify_secret("DG_BOOTSTRAP_ADMIN_PASSWORD", "x" * 12) == []


def test_bootstrap_admin_password_one_under_min_length_fails():
    assert secrets_policy.classify_secret(
        "DG_BOOTSTRAP_ADMIN_PASSWORD", "x" * 11
    ) == ["too-short"]


def test_llm_master_secret_min_length_boundary():
    assert secrets_policy.classify_secret("LLM_MASTER_SECRET", "b" * 32) == []
    assert secrets_policy.classify_secret("LLM_MASTER_SECRET", "b" * 31) == [
        "too-short"
    ]


def test_digest_rule_matches_synthetic_digest(monkeypatch):
    synthetic_value = "totally-not-the-real-n8n-password"
    synthetic_digest = hashlib.sha256(synthetic_value.encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        secrets_policy, "KNOWN_DEFAULT_SHA256", frozenset({synthetic_digest})
    )
    assert secrets_policy.classify_secret("N8N_PASSWORD", synthetic_value) == [
        "known-default"
    ]


def test_digest_rule_does_not_match_unrelated_value(monkeypatch):
    synthetic_digest = hashlib.sha256(b"something-else").hexdigest()
    monkeypatch.setattr(
        secrets_policy, "KNOWN_DEFAULT_SHA256", frozenset({synthetic_digest})
    )
    assert secrets_policy.classify_secret("N8N_PASSWORD", "unrelated-value-32chars!") == []


def test_value_can_carry_both_known_default_and_too_short():
    # Short enough to fail DG_BOOTSTRAP_ADMIN_PASSWORD's 12-char minimum AND
    # match the change-me prefix rule.
    value = "change-me"
    reasons = secrets_policy.classify_secret("DG_BOOTSTRAP_ADMIN_PASSWORD", value)
    assert set(reasons) == {"known-default", "too-short"}


def test_real_committed_digest_never_matches_a_plausible_password():
    # The real digest entry should never accidentally match an unrelated
    # random-looking value in this test file.
    assert secrets_policy.classify_secret(
        "N8N_PASSWORD", "some-other-random-looking-value-987"
    ) == []


# -- enforce_startup_secrets --


def test_enforce_startup_secrets_multi_user_raises_naming_keys_only(caplog):
    env = {
        "NEO4J_PASSWORD": "12345678",
        "LLM_MASTER_SECRET": "b" * 32,
        "DG_SERVICE_TOKEN": "a" * 32,
        "DG_BOOTSTRAP_ADMIN_PASSWORD": "x" * 12,
    }
    logger = logging.getLogger("test-secrets-policy-multiuser")
    with pytest.raises(RuntimeError) as excinfo:
        secrets_policy.enforce_startup_secrets(env, "multi-user", logger)
    message = str(excinfo.value)
    assert "NEO4J_PASSWORD" in message
    assert "known-default" in message
    assert "12345678" not in message


def test_enforce_startup_secrets_multi_user_passes_when_all_ok():
    env = {
        "NEO4J_PASSWORD": "some-strong-rotated-value-xyz",
        "LLM_MASTER_SECRET": "b" * 32,
        "DG_SERVICE_TOKEN": "a" * 32,
        "DG_BOOTSTRAP_ADMIN_PASSWORD": "x" * 12,
    }
    logger = logging.getLogger("test-secrets-policy-multiuser-ok")
    failing = secrets_policy.enforce_startup_secrets(env, "multi-user", logger)
    assert failing == []


def test_enforce_startup_secrets_local_warns_and_returns_keys(caplog):
    env = {
        "NEO4J_PASSWORD": "12345678",
        "LLM_MASTER_SECRET": "b" * 32,
        "DG_SERVICE_TOKEN": "a" * 32,
        "DG_BOOTSTRAP_ADMIN_PASSWORD": "x" * 12,
    }
    logger = logging.getLogger("test-secrets-policy-local")
    with caplog.at_level(logging.WARNING, logger="test-secrets-policy-local"):
        failing = secrets_policy.enforce_startup_secrets(env, "local", logger)

    assert any("NEO4J_PASSWORD" in entry for entry in failing)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "NEO4J_PASSWORD" in warnings[0].getMessage()
    assert "12345678" not in warnings[0].getMessage()


def test_enforce_startup_secrets_unknown_profile_raises_value_error():
    logger = logging.getLogger("test-secrets-policy-unknown-profile")
    with pytest.raises(ValueError):
        secrets_policy.enforce_startup_secrets({}, "staging", logger)


# -- module-level constants sanity --


def test_known_default_sha256_holds_one_valid_hex_digest():
    assert len(secrets_policy.KNOWN_DEFAULT_SHA256) == 1
    (digest,) = secrets_policy.KNOWN_DEFAULT_SHA256
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_pending_rotation_keys_are_the_ten_pre_existing_keys():
    assert set(secrets_policy.PENDING_ROTATION_KEYS) == {
        "NEO4J_PASSWORD",
        "N8N_USER",
        "N8N_PASSWORD",
        "POSTGRES_PASSWORD",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
        "LLM_MASTER_SECRET",
        "SPECKLE_SESSION_SECRET",
        "SPECKLE_WRITE_TOKEN",
        "SPECKLE_READ_TOKEN",
    }
