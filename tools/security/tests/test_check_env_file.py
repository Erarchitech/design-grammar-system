"""Tests for tools/security/check_env_file.py (Phase 1205, ALGN12-19, D-10/D-11).

Bootstraps `sys.path` to `tools/security` (no `__init__.py` there per
1205-01-PLAN.md) so this test can `import check_env_file` directly. Writes
temp `.env`/`.env.example` pairs under `tmp_path` and asserts on captured
stdout only -- never on any live `.env`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import check_env_file  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_ok_when_every_key_present_and_valid(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "DG_SERVICE_TOKEN=change-me-dg-service-token\n")
    _write(env, "DG_SERVICE_TOKEN=" + ("z" * 40) + "\n")

    exit_code = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "DG_SERVICE_TOKEN: ok" in out


def test_missing_key_fails_and_reports_missing(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "DG_SERVICE_TOKEN=change-me-dg-service-token\n")
    _write(env, "# empty, key not set\n")

    exit_code = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "DG_SERVICE_TOKEN: missing" in out


def test_known_default_value_fails_and_reports_known_default(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "NEO4J_PASSWORD=change-me-neo4j-password\n")
    _write(env, "NEO4J_PASSWORD=12345678\n")

    exit_code = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "NEO4J_PASSWORD: known-default" in out
    assert "12345678" not in out


def test_too_short_value_fails_and_reports_too_short(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    synthetic_short_token = "s" * 20  # under the 32-char DG_SERVICE_TOKEN minimum
    _write(example, "DG_SERVICE_TOKEN=change-me-dg-service-token\n")
    _write(env, f"DG_SERVICE_TOKEN={synthetic_short_token}\n")

    exit_code = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "DG_SERVICE_TOKEN: too-short" in out
    assert synthetic_short_token not in out


def test_pending_rotation_key_passes_only_with_flag(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "NEO4J_PASSWORD=change-me-neo4j-password\n")
    _write(env, "NEO4J_PASSWORD=12345678\n")

    exit_code_without_flag = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )
    out_without_flag = capsys.readouterr().out
    assert exit_code_without_flag == 1
    assert "NEO4J_PASSWORD: known-default" in out_without_flag

    exit_code_with_flag = check_env_file.main(
        [
            "--env-file",
            str(env),
            "--example",
            str(example),
            "--allow-pending-rotation",
        ]
    )
    out_with_flag = capsys.readouterr().out
    assert exit_code_with_flag == 0
    assert "NEO4J_PASSWORD: pending-rotation" in out_with_flag


def test_non_pending_rotation_key_never_passes_via_flag(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "DG_SERVICE_TOKEN=change-me-dg-service-token\n")
    _write(env, "DG_SERVICE_TOKEN=change-me-dg-service-token\n")

    exit_code = check_env_file.main(
        [
            "--env-file",
            str(env),
            "--example",
            str(example),
            "--allow-pending-rotation",
        ]
    )
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "DG_SERVICE_TOKEN: known-default" in out


def test_optional_blank_key_is_ok_when_left_blank(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "SPECKLE_PROJECT_ID=\n")
    _write(env, "SPECKLE_PROJECT_ID=\n")

    exit_code = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "SPECKLE_PROJECT_ID: ok" in out


def test_extra_key_reported_but_does_not_fail(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    _write(example, "DG_SERVICE_TOKEN=change-me-dg-service-token\n")
    _write(env, "DG_SERVICE_TOKEN=" + ("z" * 40) + "\nSOME_UNKNOWN_KEY=whatever\n")

    exit_code = check_env_file.main(
        ["--env-file", str(env), "--example", str(example)]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "SOME_UNKNOWN_KEY: extra" in out


def test_synthetic_values_never_appear_in_stdout(tmp_path, capsys):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    secret_value = "totally-synthetic-value-never-printed-9f8e"
    _write(example, "DG_BOOTSTRAP_ADMIN_PASSWORD=change-me-dg-bootstrap-admin-password\n")
    _write(env, f"DG_BOOTSTRAP_ADMIN_PASSWORD={secret_value}\n")

    check_env_file.main(["--env-file", str(env), "--example", str(example)])
    out = capsys.readouterr().out
    assert secret_value not in out


def test_repo_env_example_reports_known_default_for_every_secret_key(capsys):
    real_example = REPO_ROOT / ".env.example"
    assert real_example.exists()

    exit_code = check_env_file.main(
        ["--env-file", str(real_example), "--example", str(real_example)]
    )
    out = capsys.readouterr().out

    assert exit_code == 1  # placeholders must fail closed
    secret_keys = [
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
        "DG_SERVICE_TOKEN",
        "DG_BOOTSTRAP_ADMIN_USER",
        "DG_BOOTSTRAP_ADMIN_PASSWORD",
    ]
    for key in secret_keys:
        assert f"{key}: known-default" in out, f"expected {key} to be known-default in:\n{out}"
