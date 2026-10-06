"""DeGram pairing token (Phase 1301, plan 17, D-25, D-26, D-27, DGCL-01, DGCL-05).

The Connectors tab issues the DeGram agent its credential: a ``dgp_`` pairing
token, created by a signed-in user, bound to that user and to no project
(D-26), with no expiry (D-27, revoke only). DeGram keeps it encrypted on the PC
and trades it at ``POST /auth/degram/exchange`` for the same short-lived
``dgd_`` token a cookie session mints (``delegation.py``). The relay and the
tools therefore see an unchanged delegated principal.

A pairing token is not a principal (1300 D-07): ``auth.require_principal``
answers 401 ``PAIRING_NOT_A_PRINCIPAL`` for it on every route except the
exchange, so no connector or session code path can resolve it. Its store is
separate from ``connector-credentials.json`` for the same reason.

Storage is ``degram-pairings.json`` next to the other auth stores, written
through ``auth._load`` / ``auth._save`` under ``auth._STORE_LOCK``. Only the
SHA-256 hash of the token is persisted; the raw token is returned once at
creation and is never logged.

A pairing ends when its owner or an admin revokes it, when its user changes
their password, or when its user no longer exists. Every ``dgd_`` minted from
it ends at the same moment: ``delegation`` re-checks the pairing on each
request (``is_live``) and the revoke also marks those tokens revoked.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import auth

PAIRINGS_FILE_NAME = "degram-pairings.json"
PAIRING_TOKEN_PREFIX = "dgp_"

CONNECTOR_ID = "degram"
CONNECTOR_NAME = "DeGram"
CATEGORY = "Agents"

_KEY = "pairings"


def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / PAIRINGS_FILE_NAME


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -- errors -----------------------------------------------------------------


def pairing_auth_failed():
    return auth.auth_error(
        "Invalid or revoked DeGram pairing token.",
        "Create a new DeGram pairing on the Connectors tab.",
        "PAIRING_AUTH_FAILED",
        401,
    )


def pairing_not_a_principal():
    return auth.auth_error(
        "A DeGram pairing token is accepted only by POST /auth/degram/exchange.",
        "Exchange the pairing token for a delegated token first.",
        "PAIRING_NOT_A_PRINCIPAL",
        401,
    )


def pairing_not_found():
    return auth.auth_error(
        "DeGram pairing not found.",
        "Use a pairing id from GET /connectors.",
        "PAIRING_NOT_FOUND",
        404,
    )


# -- issue ------------------------------------------------------------------


def issue_pairing(username: str, label: str | None = None, *, now: int | None = None) -> tuple[str, str]:
    """Create a pairing for `username`. Returns ``(raw_token, pairing_id)``;
    the raw token is never stored."""
    token = PAIRING_TOKEN_PREFIX + secrets.token_urlsafe(32)
    record: dict[str, Any] = {
        "pairing_id": uuid.uuid4().hex,
        "username": username.strip().lower(),
        "label": (label or "").strip()[:120],
        "token_hash": _hash(token),
        "created_at": auth._now(now),
        "last_exchange": None,
        "revoked": False,
        "expires_at": None,  # D-27: no expiry, revoke only
    }
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        rows.append(record)
        auth._save(_file(), _KEY, rows)
    return token, record["pairing_id"]


# -- resolve ----------------------------------------------------------------


def _usable(record: dict[str, Any], current: int) -> bool:
    if record.get("revoked"):
        return False
    expires_at = record.get("expires_at")
    if expires_at is not None and current >= int(expires_at):
        return False
    return auth.get_user(record.get("username") or "") is not None


def authenticate_pairing(token: str, *, now: int | None = None) -> dict[str, Any]:
    """Return the live pairing record (without its hash) for `token`, or raise
    401 ``PAIRING_AUTH_FAILED`` for an unknown, revoked or expired pairing or
    one whose user no longer exists."""
    if not token or not token.startswith(PAIRING_TOKEN_PREFIX):
        raise pairing_auth_failed()
    digest = _hash(token)
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        record = next((r for r in rows if r.get("token_hash") == digest), None)
    if record is None or not _usable(record, current):
        raise pairing_auth_failed()
    public = dict(record)
    public.pop("token_hash", None)
    return public


def is_live(pairing_id: str, username: str, *, now: int | None = None) -> bool:
    """True while the pairing `pairing_id` of `username` is usable."""
    if not pairing_id:
        return False
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
    record = next((r for r in rows if r.get("pairing_id") == pairing_id), None)
    return (
        record is not None
        and record.get("username") == username.strip().lower()
        and _usable(record, current)
    )


def record_exchange(pairing_id: str, *, now: int | None = None) -> None:
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        for row in rows:
            if row.get("pairing_id") == pairing_id:
                row["last_exchange"] = current
                auth._save(_file(), _KEY, rows)
                return


# -- list -------------------------------------------------------------------


def list_pairings(username: str | None) -> list[dict[str, Any]]:
    """Pairings of `username`, or of every user when None (admin). Never a
    token or hash."""
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
    normalized = username.strip().lower() if username is not None else None
    out: list[dict[str, Any]] = []
    for row in rows:
        if normalized is not None and row.get("username") != normalized:
            continue
        entry = {
            "credential_id": row.get("pairing_id"),
            "label": row.get("label", ""),
            "created_at": _iso(row.get("created_at")),
            "last_exchange": _iso(row.get("last_exchange")),
            "revoked": bool(row.get("revoked")),
        }
        if normalized is None:
            entry["username"] = row.get("username")
        out.append(entry)
    return out


def connector_card(username: str, is_admin: bool, derive_status) -> dict[str, Any]:
    """The DeGram entry of ``GET /connectors``. `derive_status` is
    ``connectors.derive_status`` (ISO timestamp in, status out)."""
    pairings = list_pairings(None if is_admin else username)
    stamps = [p["last_exchange"] for p in pairings if p["last_exchange"]]
    last = max(stamps) if stamps else None
    return {
        "id": CONNECTOR_ID,
        "name": CONNECTOR_NAME,
        "category": CATEGORY,
        "status": derive_status(last.replace("Z", "+00:00") if last else None),
        "last_connection": last,
        "credentials": pairings,
    }


# -- revoke -----------------------------------------------------------------


def _revoke_where(predicate) -> list[str]:
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        ended: list[str] = []
        for row in rows:
            if not row.get("revoked") and predicate(row):
                row["revoked"] = True
                ended.append(row.get("pairing_id") or "")
        if ended:
            auth._save(_file(), _KEY, rows)
    return ended


def revoke_pairing(pairing_id: str, *, username: str, is_admin: bool) -> bool:
    """Revoke `pairing_id` if the caller owns it or is an admin, and every
    ``dgd_`` minted from it. False when unknown or not the caller's, so the
    route answers both with the same 404."""
    import delegation  # noqa: PLC0415 -- delegation imports this module

    normalized = username.strip().lower()
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        record = next((r for r in rows if r.get("pairing_id") == pairing_id), None)
        if record is None or (not is_admin and record.get("username") != normalized):
            return False
        if not record.get("revoked"):
            record["revoked"] = True
            auth._save(_file(), _KEY, rows)
    delegation.revoke_for_pairing(pairing_id)
    return True


def revoke_for_user(username: str) -> int:
    """Revoke every pairing of `username` and their delegated tokens
    (password change)."""
    import delegation  # noqa: PLC0415

    normalized = username.strip().lower()
    ended = _revoke_where(lambda r: r.get("username") == normalized)
    for pairing_id in ended:
        delegation.revoke_for_pairing(pairing_id)
    return len(ended)
