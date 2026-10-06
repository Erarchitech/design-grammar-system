"""Delegated user-scoped token (Phase 1301, plan 05, D-06, D-08, DGCL-05).

The local DeGram agent reads DG on behalf of a signed-in user. It does not hold
the browser cookie, a connector token or the service token; it holds a
``dgd_`` Bearer token minted from the user's cookie session for ONE project.
The token is short-lived (``DELEGATED_TOKEN_TTL_SECONDS``) and is a derived,
non-ambient credential, so it dies with whatever it was derived from:

* the parent session (logout, password change, expiry, idle timeout, a user who
  no longer exists) -- re-validated on every request through the session hash;
* the user's membership on the bound project (checked live, never cached);
* the project's company assignment (``company.py``) -- a token records the
  company it was issued under and is refused once the assignment differs;
* its own expiry, or an explicit ``DELETE /auth/delegated-token``.

Phase 1301 plan 17 (D-25): a token can also be minted from a DeGram pairing
(``degram_pairing.py``) through ``POST /auth/degram/exchange``. Its record has
``parent_kind`` ``"pairing"`` and a ``pairing_id`` in place of the session
hash; the live pairing replaces the live session in every re-check, and a
revoked pairing answers ``DELEGATED_SESSION_ENDED`` like an ended session.

It never inherits admin ownership: ``is_admin`` is always False and project
authorization is bound-project equality plus the user's *stored* role.
Delegated use does not refresh the parent session's idle timer, so an agent
cannot keep an abandoned browser session alive.

Storage is a JSON file next to the other auth stores
(``auth-delegated-tokens.json``) written through ``auth._load`` / ``auth._save``
under ``auth._STORE_LOCK``. Only the SHA-256 hash of the token is persisted; the
raw token is returned once at issue time and is never logged. Each failure uses
a named, generic ``{error, hint, code}`` answer:

====================================  ======  =====================================
``DELEGATED_AUTH_FAILED``             401     unknown, malformed or explicitly revoked
``DELEGATED_EXPIRED``                 401     past its own expiry
``DELEGATED_SESSION_ENDED``           401     parent session ended / revoked / idle
``PROJECT_FORBIDDEN``                 403     membership on the bound project is gone
``DELEGATED_SCOPE_CHANGED``           403     project reassigned to another company
====================================  ======  =====================================
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Any, Callable

import auth
import company

TOKENS_FILE_NAME = "auth-delegated-tokens.json"
DELEGATED_TOKEN_PREFIX = "dgd_"
DELEGATED_TOKEN_TTL_SECONDS = 900  # 15 minutes

# Revoked and expired rows stay readable for this long after expiry so a late
# caller still gets the named reason, then they are pruned.
_RETENTION_SECONDS = 3600

_KEY = "tokens"

REASON_SESSION_ENDED = "session_ended"
REASON_MEMBERSHIP_REMOVED = "membership_removed"
REASON_SCOPE_CHANGED = "scope_changed"
REASON_EXPLICIT = "explicit"


def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / TOKENS_FILE_NAME


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# -- errors -----------------------------------------------------------------


def _auth_failed():
    return auth.auth_error(
        "Invalid or revoked delegated token.",
        "Request a new delegated token with POST /auth/delegated-token.",
        "DELEGATED_AUTH_FAILED",
        401,
    )


def _expired():
    return auth.auth_error(
        "The delegated token has expired.",
        "Request a new delegated token with POST /auth/delegated-token.",
        "DELEGATED_EXPIRED",
        401,
    )


def _session_ended():
    return auth.auth_error(
        "The session behind this delegated token has ended.",
        "Sign in again and request a new delegated token.",
        "DELEGATED_SESSION_ENDED",
        401,
    )


def _project_forbidden():
    return auth.auth_error(
        "Not authorized for the requested project.",
        "Request project access from a project owner.",
        "PROJECT_FORBIDDEN",
        403,
    )


def _scope_changed():
    return auth.auth_error(
        "The project scope of this delegated token has changed.",
        "Request a new delegated token with POST /auth/delegated-token.",
        "DELEGATED_SCOPE_CHANGED",
        403,
    )


_REVOKED_ERRORS: dict[str, Callable[[], Exception]] = {
    REASON_SESSION_ENDED: _session_ended,
    REASON_MEMBERSHIP_REMOVED: _project_forbidden,
    REASON_SCOPE_CHANGED: _scope_changed,
    REASON_EXPLICIT: _auth_failed,
}


# -- issue ------------------------------------------------------------------


def issue_delegated_token(
    *,
    session_hash: str | None = None,
    pairing_id: str | None = None,
    username: str,
    project: str,
    now: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Mint a ``dgd_`` token for `username` and `project`, bound to ONE parent
    -- the session identified by `session_hash` or the DeGram pairing
    `pairing_id` -- and to the project's current company. Returns
    ``(raw_token, public_record)``; the record never carries a hash. The caller
    must already have proved membership and a live parent."""
    if bool(session_hash) == bool(pairing_id):
        raise ValueError("exactly one parent: session_hash or pairing_id")
    current = auth._now(now)
    normalized = username.strip().lower()
    token = DELEGATED_TOKEN_PREFIX + secrets.token_urlsafe(32)
    record: dict[str, Any] = {
        "token_hash": _hash(token),
        "parent_kind": "pairing" if pairing_id else "session",
        "session_hash": session_hash,
        "pairing_id": pairing_id,
        "username": normalized,
        "project": project,
        "company": company.company_for_project(project),
        "issued_at": current,
        "expires_at": current + DELEGATED_TOKEN_TTL_SECONDS,
        "revoked": False,
    }
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        kept = [
            r for r in rows if int(r.get("expires_at", 0)) + _RETENTION_SECONDS > current
        ]
        kept.append(record)
        auth._save(_file(), _KEY, kept)
    public = dict(record)
    public.pop("token_hash", None)
    public.pop("session_hash", None)
    return token, public


# -- authenticate -----------------------------------------------------------


def _mark_revoked(rows: list[dict[str, Any]], record: dict[str, Any], reason: str) -> None:
    record["revoked"] = True
    record["revoked_reason"] = reason
    auth._save(_file(), _KEY, rows)


def authenticate_delegated_token(token: str, *, now: int | None = None) -> "auth.Principal":
    """Resolve a ``dgd_`` Bearer token to a ``delegated`` Principal, or raise
    the named ``HTTPException`` (see the module docstring). Re-validates the
    parent session, the live membership and the company on every call."""
    if not token or not token.startswith(DELEGATED_TOKEN_PREFIX):
        raise _auth_failed()
    digest = _hash(token)
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        record = next((r for r in rows if r.get("token_hash") == digest), None)
        if record is None:
            raise _auth_failed()
        if record.get("revoked"):
            raise _REVOKED_ERRORS.get(record.get("revoked_reason") or "", _auth_failed)()
        if current >= int(record.get("expires_at", 0)):
            raise _expired()

        username = record.get("username") or ""
        project = record.get("project") or ""
        if record.get("parent_kind") == "pairing":
            import degram_pairing  # noqa: PLC0415 -- degram_pairing imports this module

            parent_live = degram_pairing.is_live(
                record.get("pairing_id") or "", username, now=current
            )
        else:
            session = auth.authenticate_session_hash(
                record.get("session_hash") or "", now=current
            )
            parent_live = session is not None and session.get("username") == username
        if not parent_live or auth.get_user(username) is None:
            raise _session_ended()

        # No admin elevation: the stored membership row only.
        if auth.get_role(username, project) is None:
            _mark_revoked(rows, record, REASON_MEMBERSHIP_REMOVED)
            raise _project_forbidden()

        if company.company_for_project(project) != record.get("company"):
            _mark_revoked(rows, record, REASON_SCOPE_CHANGED)
            raise _scope_changed()

    return auth.Principal(
        kind="delegated",
        username=username,
        is_admin=False,
        bound_project=project,
        credential_id=digest[:16],
        session_hash=record.get("session_hash"),
        company=record.get("company"),
    )


# -- revoke -----------------------------------------------------------------


def _revoke_where(predicate: Callable[[dict[str, Any]], bool], reason: str) -> int:
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        count = 0
        for row in rows:
            if not row.get("revoked") and predicate(row):
                row["revoked"] = True
                row["revoked_reason"] = reason
                count += 1
        if count:
            auth._save(_file(), _KEY, rows)
        return count


def revoke_for_session(session_hash: str, reason: str = REASON_SESSION_ENDED) -> int:
    """Revoke every live token minted from the session `session_hash`."""
    if not session_hash:
        return 0
    return _revoke_where(lambda r: r.get("session_hash") == session_hash, reason)


def revoke_for_pairing(pairing_id: str, reason: str = REASON_SESSION_ENDED) -> int:
    """Revoke every live token minted from the DeGram pairing `pairing_id`."""
    if not pairing_id:
        return 0
    return _revoke_where(lambda r: r.get("pairing_id") == pairing_id, reason)


def revoke_for_user(username: str, reason: str = REASON_SESSION_ENDED) -> int:
    """Revoke every live token of `username` (password change)."""
    normalized = username.strip().lower()
    return _revoke_where(lambda r: r.get("username") == normalized, reason)


def revoke_for_user_project(
    username: str, project: str, reason: str = REASON_MEMBERSHIP_REMOVED
) -> int:
    """Revoke the live tokens of `username` bound to `project` (membership
    removal)."""
    normalized = username.strip().lower()
    return _revoke_where(
        lambda r: r.get("username") == normalized and r.get("project") == project, reason
    )


def revoke_for_project(project: str, reason: str = REASON_SCOPE_CHANGED) -> int:
    """Revoke every live token bound to `project` (company reassignment)."""
    return _revoke_where(lambda r: r.get("project") == project, reason)


def revoke_token(token: str) -> bool:
    """Revoke the one token `token` (explicit self-revoke). False if unknown
    or already revoked."""
    if not token:
        return False
    digest = _hash(token)
    return _revoke_where(lambda r: r.get("token_hash") == digest, REASON_EXPLICIT) > 0
