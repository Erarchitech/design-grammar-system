"""RETIRED DeGram pairing token (Phase 1301 plan 17, retired by plan 30 / D-39).

Plan 17 let any signed-in user create a ``dgp_`` pairing token on the Connectors
tab and paste it into DeGram. Owner decision D-39 (2026-10-11) replaced that
with access issued by a DG admin or the project owner (``degram_grants.py``):
the key never leaves the server and DeGram trades the user's DG session for a
delegated token (``POST /auth/degram/session-exchange``).

What remains here is only the wall around the old credential:

* a ``dgp_`` Bearer is never a principal. ``auth.require_principal`` answers 401
  ``PAIRING_NOT_A_PRINCIPAL`` for it on every route except the retired
  ``POST /auth/degram/exchange``, where ``authenticate_pairing`` always answers
  401 ``PAIRING_RETIRED`` (DeGram 0.1.9 maps any exchange 401 to "pairing
  revoked" and clears its stored token);
* every stored pairing is treated as revoked (``is_live`` is always False), so
  a ``dgd_`` token minted from one before the retirement answers
  ``DELEGATED_SESSION_ENDED`` at its next request;
* ``DELETE /connectors/degram/pairings/{id}`` stays for cleanup of the stored
  rows. Nothing creates a pairing any more.

Storage is ``degram-pairings.json`` next to the other auth stores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import auth

PAIRINGS_FILE_NAME = "degram-pairings.json"
PAIRING_TOKEN_PREFIX = "dgp_"

_KEY = "pairings"


def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / PAIRINGS_FILE_NAME


# -- errors -----------------------------------------------------------------


def pairing_retired(status_code: int = 401):
    """401 for a presented token (the exchange), 410 for the creation route."""
    return auth.auth_error(
        "DeGram pairing tokens are retired.",
        "Sign in to DG in DeGram; access is granted by the project owner or a DG admin.",
        "PAIRING_RETIRED",
        status_code,
    )


def pairing_not_a_principal():
    return auth.auth_error(
        "A DeGram pairing token is not a credential any more.",
        "Sign in to DG in DeGram; access is granted by the project owner or a DG admin.",
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


# -- resolve ----------------------------------------------------------------


def authenticate_pairing(token: str, *, now: int | None = None) -> dict[str, Any]:
    """Always raises 401 ``PAIRING_RETIRED``: a pairing token no longer
    resolves to anything."""
    raise pairing_retired()


def is_live(pairing_id: str, username: str, *, now: int | None = None) -> bool:
    """Always False: a ``dgd_`` token minted from a pairing has ended."""
    return False


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
