#!/usr/bin/env python3
"""Owner-run `.env` completeness and known-default checker (Phase 1205,
"Security and Tenancy Release Gate", D-10 / D-11).

Bootstraps `sys.path` to `data-service/` (mirrors `tools/de01/legs.py:29-35`)
so it can import `secrets_policy.classify_secret` and compare every key
declared in `--example` (default `.env.example`) against the corresponding
value in `--env-file` (default `.env`).

SECURITY: this tool prints key names and verdicts only -- `KEY: status` --
and never a secret value, in stdout, a log line, or an exception message.
Claude never runs this against the real `.env`; plan 1205-01 Task 2 is an
owner-run checkpoint the owner runs in their own terminal.

Usage:
    python tools/security/check_env_file.py [--env-file .env] [--example .env.example] [--allow-pending-rotation]

Exit code 0 only when every key declared in `--example` reports `ok`, or
`pending-rotation` (under `--allow-pending-rotation`) for a key in
`secrets_policy.PENDING_ROTATION_KEYS` whose only failing reason is
`known-default`. Keys present in `--env-file` but absent from `--example`
report `extra` and never fail the run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERVICE_DIR = REPO_ROOT / "data-service"
if str(DATA_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_SERVICE_DIR))

import secrets_policy  # noqa: E402

# Keys allowed to stay blank in both --example and --env-file: optional
# Speckle project-scoping values (1205-CONTEXT.md D-10), not required
# secrets. Without this exemption an intentionally blank value would report
# "missing" and block the owner's exit-0 checkpoint (plan 1205-01 Task 2) --
# added here per Rule 2 (missing critical functionality for the plan's own
# acceptance criteria), not present in secrets_policy.classify_secret's
# unconditional missing-when-blank contract.
OPTIONAL_BLANK_KEYS: frozenset[str] = frozenset(
    {"SPECKLE_PROJECT_ID", "SPECKLE_BASE_MODEL_ID"}
)


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines. Ignores blank lines and `#` comments,
    strips one layer of matching quotes. Never logs or returns anything
    beyond the raw key/value pairs found on disk."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def classify(
    key: str,
    example_value: str | None,
    actual_value: str | None,
    allow_pending_rotation: bool,
) -> str:
    """Return one status word: ok | missing | known-default | too-short |
    pending-rotation. Never returns or logs the underlying value."""
    if (
        key in OPTIONAL_BLANK_KEYS
        and example_value == ""
        and (actual_value is None or actual_value.strip() == "")
    ):
        return "ok"

    reasons = secrets_policy.classify_secret(key, actual_value)
    if not reasons:
        return "ok"

    if (
        allow_pending_rotation
        and reasons == ["known-default"]
        and key in secrets_policy.PENDING_ROTATION_KEYS
    ):
        return "pending-rotation"

    if "known-default" in reasons:
        return "known-default"
    if "too-short" in reasons:
        return "too-short"
    return reasons[0]  # "missing"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--example", default=".env.example")
    parser.add_argument("--allow-pending-rotation", action="store_true")
    args = parser.parse_args(argv)

    example_values = parse_env_file(Path(args.example))
    actual_values = parse_env_file(Path(args.env_file))

    all_ok = True
    for key in sorted(example_values):
        status = classify(
            key,
            example_values[key],
            actual_values.get(key),
            args.allow_pending_rotation,
        )
        if status not in ("ok", "pending-rotation"):
            all_ok = False
        print(f"{key}: {status}")

    for key in sorted(set(actual_values) - set(example_values)):
        print(f"{key}: extra")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
