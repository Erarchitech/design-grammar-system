"""Known-default secret policy (Phase 1205 "Security and Tenancy Release Gate",
ALGN12-19, D-11).

This module is the single in-code source of truth for what counts as a
"known default" (never-safe-to-ship) secret value across the stack. Two
callers read it:

- ``app.py`` (wired in Phase 1205 plan 1205-07) calls
  :func:`enforce_startup_secrets` once at process startup. It raises in the
  ``multi-user`` deployment profile when a required secret still equals a
  known default or is too short, and logs a single WARNING (naming keys
  only) in the ``local`` profile instead of refusing to start.
- ``tools/security/check_env_file.py`` (Phase 1205 plan 1205-01, this plan)
  is an owner-run CLI that classifies every key in a ``.env`` file against
  this same policy and never prints a secret value.

This list is mirrored in ``spec/SECURITY-BOUNDARY.md`` (authored in Phase
1205 plan 1205-16); a drift test there keeps the two copies equal.

``KNOWN_DEFAULT_SHA256`` holds exactly one digest: the SHA-256 hex digest of
the committed n8n basic-auth password default
(``docker-compose.yml``'s ``N8N_BASIC_AUTH_PASSWORD`` fallback). That
default looks like a real personal password (1205-CONTEXT.md "Specific
Ideas"), so it is represented here only as a digest -- never as plaintext.
``classify_secret`` hashes the candidate value and compares hex digests;
this module must never gain a second entry carrying that value in the
clear.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Mapping

# Generic known-default literals observed in docker-compose.yml (Correction 6
# in 1205-CONTEXT.md): NEO4J_AUTH/NEO4J_PASSWORD, the Neo4j username reused as
# a value, MinIO's root credentials, the Speckle Postgres user/password/db,
# and other bare "obviously not random" placeholders.
KNOWN_DEFAULT_LITERALS: frozenset[str] = frozenset(
    {
        "12345678",
        "minioadmin",
        "speckle",
        "neo4j",
        "password",
        "admin",
    }
)

# Any value that, after lowercasing and normalising `_` to `-`, starts with
# one of these prefixes is a known default. Covers both the `change-me-...`
# and `change_me_...` placeholder spellings.
KNOWN_DEFAULT_PREFIXES: tuple[str, ...] = ("change-me",)

# SHA-256 hex digest(s) of known-default values that must never be
# represented as plaintext in this file (see module docstring). Holds
# exactly one entry: the committed n8n basic-auth password default,
# computed from `git show 799ec40:docker-compose.yml` and never pasted here
# in the clear.
KNOWN_DEFAULT_SHA256: frozenset[str] = frozenset(
    {
        "e80168a5205e76b3632e451c075e2a6715963f8fd6c3e55f7572fc7ff0f40256",
    }
)

# Minimum acceptable length for secrets that are randomly generated (not
# owner-chosen usernames). Anything shorter than this fails closed even if it
# is not on the known-default lists above.
MIN_LENGTHS: dict[str, int] = {
    "DG_SERVICE_TOKEN": 32,
    "LLM_MASTER_SECRET": 32,
    "DG_BOOTSTRAP_ADMIN_PASSWORD": 12,
}

# The secrets data-service itself depends on at startup (D-11). Evaluated by
# enforce_startup_secrets(). NEO4J_PASSWORD has no MIN_LENGTHS entry -- it is
# still checked against the known-default literal/prefix/digest rules.
DATA_SERVICE_SECRET_KEYS: tuple[str, ...] = (
    "NEO4J_PASSWORD",
    "LLM_MASTER_SECRET",
    "DG_SERVICE_TOKEN",
    "DG_BOOTSTRAP_ADMIN_PASSWORD",
)

# Pre-existing live secrets that plan 1205-01 copies into .env unchanged (D-13):
# rotating them to fresh values is deliberately deferred to plan 1205-18, so
# --allow-pending-rotation lets an owner-run check_env_file.py pass on these
# without pretending the rotation already happened.
PENDING_ROTATION_KEYS: tuple[str, ...] = (
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
)


def classify_secret(name: str, value: str | None) -> list[str]:
    """Classify a candidate secret value. Returns reason codes only -- never
    echoes ``value`` itself, in the return value, a log line, or an
    exception message.

    Reason codes: ``"missing"`` (value is ``None`` or blank after
    stripping -- returned alone, no other reason is evaluated), ``"known-default"``
    (matches a literal, the change-me prefix rule, or a known SHA-256 digest),
    ``"too-short"`` (``name`` is in :data:`MIN_LENGTHS` and the value is
    shorter than the minimum). A value may carry both "known-default" and
    "too-short" at once.
    """
    if value is None or value.strip() == "":
        return ["missing"]

    reasons: list[str] = []

    normalized = value.lower().replace("_", "-")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    if (
        value in KNOWN_DEFAULT_LITERALS
        or normalized.startswith(KNOWN_DEFAULT_PREFIXES)
        or digest in KNOWN_DEFAULT_SHA256
    ):
        reasons.append("known-default")

    min_length = MIN_LENGTHS.get(name)
    if min_length is not None and len(value) < min_length:
        reasons.append("too-short")

    return reasons


def enforce_startup_secrets(
    env: Mapping[str, str], profile: str, logger: logging.Logger
) -> list[str]:
    """Evaluate every key in :data:`DATA_SERVICE_SECRET_KEYS` against
    :func:`classify_secret`.

    Under ``profile == "multi-user"``, raises ``RuntimeError`` naming the
    failing keys (and their reason codes) if any fail -- never a value.
    Under ``profile == "local"``, logs exactly one WARNING with the same
    key list and returns it without raising. Any other profile raises
    ``ValueError``.
    """
    if profile not in ("local", "multi-user"):
        raise ValueError(f"unknown deployment profile: {profile!r}")

    failing: list[str] = []
    for key in DATA_SERVICE_SECRET_KEYS:
        reasons = classify_secret(key, env.get(key))
        if reasons:
            failing.append(f"{key}({','.join(reasons)})")

    if not failing:
        return failing

    if profile == "multi-user":
        raise RuntimeError(
            "refusing to start in multi-user profile: secrets failing policy: "
            + ", ".join(failing)
        )

    logger.warning(
        "secrets failing policy in local profile (continuing): %s",
        ", ".join(failing),
    )
    return failing
