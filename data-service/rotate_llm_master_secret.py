"""Re-encrypt the stored LLM API key under a new LLM_MASTER_SECRET (D-13).

Runs in-container, against the persisted `llm-settings.json` file
(`llm_gateway.LLM_SETTINGS_FILE`), decrypting the `apiKey` field under the OLD
master secret and re-encrypting it under the NEW one. Reuses
`llm_gateway.decrypt_value`/`encrypt_value`/`_derive_key` directly -- no new
crypto is introduced here.

This is step 5 of the rotation runbook in `spec/SECURITY-BOUNDARY.md` (authored
by plan 1205-16): after every secret in `docker-compose.yml`/`.env` has been
rotated per D-10/D-13, `LLM_MASTER_SECRET` changing means the previously
encrypted `apiKey` no longer decrypts under the new value unless it is
re-encrypted first -- this script does exactly that, and nothing else.

**Invocation (owner-run, in-container; values never on the command line):**

    docker exec \\
      -e DG_ROTATE_OLD_LLM_MASTER_SECRET \\
      -e DG_ROTATE_NEW_LLM_MASTER_SECRET \\
      data-service python rotate_llm_master_secret.py

The two secret values are exported as environment variables in the owner's own
shell beforehand (`export DG_ROTATE_OLD_LLM_MASTER_SECRET=...`) and `docker
exec -e NAME` (no `=value`) forwards the *name*, reading the value from the
owner's shell -- the value itself never appears in a shell history entry
belonging to this script's invocation, a commit, a log, or a report. This
script never accepts either secret as a CLI argument, and never prints either
secret or the decrypted plaintext API key -- only one of the five fixed status
words below.

After this script reports ``rotated``, the owner must also: (1) update
``LLM_MASTER_SECRET`` in `.env` to the NEW value, and (2) restart data-service
(`docker compose up -d data-service`) so the running process picks up the new
secret for all future encrypt/decrypt calls -- until both of those happen, the
container's own `LLM_MASTER_SECRET` env var and the just-rewritten on-disk
ciphertext are for different secrets.

**Exit codes / status words:**

- ``0`` / ``rotated`` -- apiKey was re-encrypted under NEW; file rewritten.
- ``0`` / ``nothing-to-rotate`` -- no apiKey present in the settings file;
  file unchanged.
- ``0`` / ``dry-run-ok`` -- ``--dry-run``: decrypt/encrypt/verify succeeded,
  file unchanged.
- ``2`` / ``old-secret-does-not-decrypt`` -- the OLD secret does not decrypt
  the stored apiKey (wrong value, or already rotated); file unchanged.
- ``3`` / ``missing-env`` -- one or both of
  DG_ROTATE_OLD_LLM_MASTER_SECRET/DG_ROTATE_NEW_LLM_MASTER_SECRET is unset;
  file unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from cryptography.fernet import InvalidToken

import llm_gateway

OLD_SECRET_ENV_VAR = "DG_ROTATE_OLD_LLM_MASTER_SECRET"
NEW_SECRET_ENV_VAR = "DG_ROTATE_NEW_LLM_MASTER_SECRET"

STATUS_ROTATED = "rotated"
STATUS_NOTHING_TO_ROTATE = "nothing-to-rotate"
STATUS_DRY_RUN_OK = "dry-run-ok"
STATUS_OLD_SECRET_DOES_NOT_DECRYPT = "old-secret-does-not-decrypt"
STATUS_MISSING_ENV = "missing-env"

EXIT_OK = 0
EXIT_OLD_SECRET_INVALID = 2
EXIT_MISSING_ENV = 3


def _read_settings_json(settings_file: Path) -> dict[str, Any] | None:
    """Read the settings file's raw JSON dict, or ``None`` if absent/malformed.

    Reads the JSON directly (not through
    ``llm_gateway.load_persisted_llm_settings``) so every field -- including
    any this script does not touch -- is preserved exactly, and so the raw
    encrypted ``apiKey`` string is available for round-trip verification
    without an intermediate normalization pass.
    """
    if not settings_file.is_file():
        return None
    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _write_settings_json_atomically(settings_file: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` to ``settings_file`` via a temp file + ``os.replace``.

    ``os.replace`` is atomic on both POSIX and Windows for a same-filesystem
    rename, so a crash mid-write never leaves a truncated or half-written
    settings file (T-1205-04-03).
    """
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = settings_file.with_suffix(settings_file.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, settings_file)


def rotate(
    settings_file: Path,
    old_secret: str,
    new_secret: str,
    dry_run: bool = False,
) -> str:
    """Perform the rotation (or its dry-run verification) and return a status word.

    Never raises ``InvalidToken`` to the caller -- a wrong OLD secret is
    caught here and reported as :data:`STATUS_OLD_SECRET_DOES_NOT_DECRYPT`.
    The file is written only on the genuine (non-dry-run) rotation path, and
    only after the NEW ciphertext has been verified to decrypt back to the
    original plaintext under NEW.
    """
    payload = _read_settings_json(settings_file)
    if not payload:
        return STATUS_NOTHING_TO_ROTATE

    encrypted_api_key = payload.get("apiKey")
    if not encrypted_api_key or not isinstance(encrypted_api_key, str):
        return STATUS_NOTHING_TO_ROTATE

    try:
        plaintext = llm_gateway.decrypt_value(encrypted_api_key, old_secret)
    except InvalidToken:
        return STATUS_OLD_SECRET_DOES_NOT_DECRYPT

    new_ciphertext = llm_gateway.encrypt_value(plaintext, new_secret)

    # Round-trip verification (T-1205-04-03): confirm the NEW ciphertext
    # decrypts back to the exact original plaintext under NEW before writing
    # anything. A verification failure here would be a defect in this
    # script's own encrypt/decrypt round trip, not a wrong-secret condition
    # (that was already handled above) -- so it is intentionally not caught;
    # letting it propagate is safer than reporting a false "rotated".
    verified_plaintext = llm_gateway.decrypt_value(new_ciphertext, new_secret)
    assert verified_plaintext == plaintext, (
        "round-trip verification failed: re-encrypted value did not decrypt "
        "back to the original plaintext under the new secret"
    )

    if dry_run:
        return STATUS_DRY_RUN_OK

    payload["apiKey"] = new_ciphertext
    _write_settings_json_atomically(settings_file, payload)
    return STATUS_ROTATED


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rotate_llm_master_secret.py",
        description=(
            "Re-encrypt the stored LLM API key from DG_ROTATE_OLD_LLM_MASTER_SECRET to "
            "DG_ROTATE_NEW_LLM_MASTER_SECRET (D-13). Both secrets are read only from "
            "environment variables, never from a command-line argument."
        ),
    )
    parser.add_argument(
        "--settings-file",
        default=None,
        help=(
            "Path to the LLM settings JSON file (default: "
            "llm_gateway.LLM_SETTINGS_FILE, i.e. $DG_DATA_DIR/llm-settings.json)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Verify the decrypt/re-encrypt/decrypt round trip without writing the "
            "settings file."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    old_secret = os.environ.get(OLD_SECRET_ENV_VAR)
    new_secret = os.environ.get(NEW_SECRET_ENV_VAR)
    if not old_secret or not new_secret:
        print(STATUS_MISSING_ENV)
        return EXIT_MISSING_ENV

    settings_file = (
        Path(args.settings_file) if args.settings_file else llm_gateway.LLM_SETTINGS_FILE
    )

    status = rotate(settings_file, old_secret, new_secret, dry_run=args.dry_run)
    print(status)

    if status == STATUS_OLD_SECRET_DOES_NOT_DECRYPT:
        return EXIT_OLD_SECRET_INVALID
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
