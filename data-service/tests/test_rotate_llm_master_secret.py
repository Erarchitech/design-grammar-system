"""Tests for rotate_llm_master_secret.py (D-13, plan 1205-04 Task 2).

Follows test_llm_gateway.py's sys.path bootstrap. Every test uses a settings
file under `tmp_path` -- never the live data-service `data/` directory (see
this plan's <security_rules>) -- and every OLD/NEW secret and the plaintext
API key used here are obviously fake test values.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import llm_gateway  # noqa: E402
import rotate_llm_master_secret as rotate_mod  # noqa: E402

OLD_SECRET = "test-old-master-secret"
NEW_SECRET = "test-new-master-secret"
PLAINTEXT_API_KEY = "sk-fake-test-key-not-real-0000000000"


def _write_settings(tmp_path, api_key_ciphertext: str | None, extra: dict | None = None):
    settings_file = tmp_path / "llm-settings.json"
    payload = dict(extra or {})
    payload["provider"] = "anthropic"
    payload["model"] = "claude-fake"
    if api_key_ciphertext is not None:
        payload["apiKey"] = api_key_ciphertext
    settings_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return settings_file


class TestRotateSuccess:
    def test_rotate_reencrypts_apikey_and_old_no_longer_decrypts(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_ROTATED

        new_payload = json.loads(settings_file.read_text(encoding="utf-8"))
        new_ciphertext = new_payload["apiKey"]
        assert new_ciphertext != ciphertext_old

        # Decrypts under NEW to the original plaintext.
        assert llm_gateway.decrypt_value(new_ciphertext, NEW_SECRET) == PLAINTEXT_API_KEY

        # No longer decrypts under OLD.
        import pytest
        from cryptography.fernet import InvalidToken

        with pytest.raises(InvalidToken):
            llm_gateway.decrypt_value(new_ciphertext, OLD_SECRET)

        # Other fields are preserved untouched.
        assert new_payload["provider"] == "anthropic"
        assert new_payload["model"] == "claude-fake"

    def test_rotate_preserves_extra_unknown_fields(self, tmp_path, monkeypatch):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old, extra={"baseUrl": "https://example.test"})

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])
        assert exit_code == 0

        new_payload = json.loads(settings_file.read_text(encoding="utf-8"))
        assert new_payload["baseUrl"] == "https://example.test"


class TestRotateWrongOldSecret:
    def test_wrong_old_secret_exits_2_and_leaves_file_unchanged(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)
        original_bytes = settings_file.read_bytes()

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, "definitely-the-wrong-secret")
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])

        assert exit_code == 2
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_OLD_SECRET_DOES_NOT_DECRYPT
        assert settings_file.read_bytes() == original_bytes


class TestRotateMissingEnv:
    def test_missing_old_env_exits_3_and_leaves_file_unchanged(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)
        original_bytes = settings_file.read_bytes()

        monkeypatch.delenv(rotate_mod.OLD_SECRET_ENV_VAR, raising=False)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])

        assert exit_code == 3
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_MISSING_ENV
        assert settings_file.read_bytes() == original_bytes

    def test_missing_new_env_exits_3_and_leaves_file_unchanged(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)
        original_bytes = settings_file.read_bytes()

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.delenv(rotate_mod.NEW_SECRET_ENV_VAR, raising=False)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])

        assert exit_code == 3
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_MISSING_ENV
        assert settings_file.read_bytes() == original_bytes

    def test_missing_both_env_exits_3(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)

        monkeypatch.delenv(rotate_mod.OLD_SECRET_ENV_VAR, raising=False)
        monkeypatch.delenv(rotate_mod.NEW_SECRET_ENV_VAR, raising=False)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])
        assert exit_code == 3


class TestRotateNothingToRotate:
    def test_no_apikey_present_exits_0_nothing_to_rotate(self, tmp_path, monkeypatch, capsys):
        settings_file = _write_settings(tmp_path, api_key_ciphertext=None)
        original_bytes = settings_file.read_bytes()

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_NOTHING_TO_ROTATE
        assert settings_file.read_bytes() == original_bytes

    def test_missing_settings_file_exits_0_nothing_to_rotate(self, tmp_path, monkeypatch, capsys):
        settings_file = tmp_path / "does-not-exist.json"

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file)])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_NOTHING_TO_ROTATE
        assert not settings_file.exists()


class TestRotateDryRun:
    def test_dry_run_verifies_round_trip_without_writing(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)
        original_bytes = settings_file.read_bytes()

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file), "--dry-run"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_DRY_RUN_OK
        assert settings_file.read_bytes() == original_bytes

    def test_dry_run_with_wrong_old_secret_still_reports_failure_and_writes_nothing(
        self, tmp_path, monkeypatch, capsys
    ):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)
        original_bytes = settings_file.read_bytes()

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, "wrong-secret")
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        exit_code = rotate_mod.main(["--settings-file", str(settings_file), "--dry-run"])

        assert exit_code == 2
        captured = capsys.readouterr()
        assert captured.out.strip() == rotate_mod.STATUS_OLD_SECRET_DOES_NOT_DECRYPT
        assert settings_file.read_bytes() == original_bytes


class TestOutputHygiene:
    """T-1205-04-02: stdout/stderr never carry a secret or the plaintext key."""

    def test_successful_rotation_prints_only_the_status_word(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, OLD_SECRET)
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        rotate_mod.main(["--settings-file", str(settings_file)])

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert OLD_SECRET not in combined
        assert NEW_SECRET not in combined
        assert PLAINTEXT_API_KEY not in combined
        assert combined.strip() == rotate_mod.STATUS_ROTATED

    def test_wrong_secret_failure_prints_only_the_status_word(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)

        monkeypatch.setenv(rotate_mod.OLD_SECRET_ENV_VAR, "wrong-secret-value")
        monkeypatch.setenv(rotate_mod.NEW_SECRET_ENV_VAR, NEW_SECRET)

        rotate_mod.main(["--settings-file", str(settings_file)])

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "wrong-secret-value" not in combined
        assert NEW_SECRET not in combined
        assert PLAINTEXT_API_KEY not in combined
        assert combined.strip() == rotate_mod.STATUS_OLD_SECRET_DOES_NOT_DECRYPT

    def test_missing_env_failure_prints_only_the_status_word(self, tmp_path, monkeypatch, capsys):
        ciphertext_old = llm_gateway.encrypt_value(PLAINTEXT_API_KEY, OLD_SECRET)
        settings_file = _write_settings(tmp_path, ciphertext_old)

        monkeypatch.delenv(rotate_mod.OLD_SECRET_ENV_VAR, raising=False)
        monkeypatch.delenv(rotate_mod.NEW_SECRET_ENV_VAR, raising=False)

        rotate_mod.main(["--settings-file", str(settings_file)])

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert combined.strip() == rotate_mod.STATUS_MISSING_ENV


class TestArgparseNoSecretFlag:
    def test_parser_defines_only_settings_file_and_dry_run(self):
        parser = rotate_mod.build_arg_parser()
        actions = {action.dest for action in parser._actions if action.dest != "help"}
        assert actions == {"settings_file", "dry_run"}
