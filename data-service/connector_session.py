"""Connector sign-in session (Phase 1308, plan 03, D-25..D-29, D-32, D-33, WEBUI-07).

A connector add-in (Grasshopper, Revit, ...) signs in with the user's DG account
and receives a ``dgk_`` Bearer token bound to ONE project and ONE connector. After
D-49 ``dgk_`` is the only connector credential: there is no pasted project token.
The token is a derived, non-ambient credential, so it dies with whatever it was
derived from. It is re-validated live on every request:

* the user must still exist;
* the project's company assignment (``company.py``) must be unchanged;
* the user must still be authorized for the connector
  (``connector_access.is_authorized``): an owner or an admin is exempt, an
  editor or a viewer needs an active per-connector access row (D-29). A missing
  grant is refused with ``CONNECTOR_ACCESS_REQUIRED`` and the session row is
  kept, so the session works again as soon as access is granted;
* its own expiry (``DEFAULT_TTL_SECONDS``, overridable with
  ``DG_CONNECTOR_SESSION_TTL_SECONDS``, D-27), or an explicit revoke.

Storage is a JSON file next to the other auth stores
(``auth-connector-sessions.json``, key ``sessions``) written through
``auth._load`` / ``auth._save`` under ``auth._STORE_LOCK``. Only the SHA-256 hash
of the token is persisted; the raw token is returned once at issue time and is
never logged, stored or echoed again.

Revoked and expired rows are kept for ``_RETENTION_SECONDS`` (90 days) after
expiry so a connector that signed in once keeps reading ``stale`` rather than
``never_connected`` (D-32); after that it reads ``never_connected`` again.

Failures use named, generic ``{error, hint, code}`` answers:

====================================  ======  =====================================
``CONNECTOR_AUTH_FAILED``             401     unknown or malformed token
``CONNECTOR_SESSION_EXPIRED``         401     past its own expiry
``CONNECTOR_SESSION_ENDED``           401     revoked, user gone or company changed
``CONNECTOR_ACCESS_REQUIRED``         403     no active per-connector access row
====================================  ======  =====================================
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Mapping

import auth
import company
import connector_access

SESSIONS_FILE_NAME = "auth-connector-sessions.json"
SESSION_TOKEN_PREFIX = "dgk_"
DEFAULT_TTL_SECONDS = 28800  # 8 hours
TTL_ENV = "DG_CONNECTOR_SESSION_TTL_SECONDS"

# Rows stay readable this long after expiry so `status_for` can answer `stale`.
_RETENTION_SECONDS = 90 * 24 * 3600

_KEY = "sessions"

REASON_EXPLICIT = "explicit"
REASON_USER_GONE = "user_gone"
REASON_SCOPE_CHANGED = "scope_changed"
REASON_MEMBERSHIP_REMOVED = "membership_removed"
REASON_GRANT_REVOKED = "grant_revoked"
REASON_PROJECT_SCOPE = "project_scope_changed"
REASON_UNAUTHORIZED = "unauthorized"


def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / SESSIONS_FILE_NAME


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_ttl_seconds(env: Mapping[str, str] | None = None) -> int:
    """The session lifetime in seconds: ``DG_CONNECTOR_SESSION_TTL_SECONDS`` when
    it is a positive integer, else ``DEFAULT_TTL_SECONDS`` (D-27)."""
    raw = (env if env is not None else os.environ).get(TTL_ENV)
    if raw is None:
        return DEFAULT_TTL_SECONDS
    try:
        value = int(str(raw).strip())
    except ValueError:
        return DEFAULT_TTL_SECONDS
    return value if value > 0 else DEFAULT_TTL_SECONDS


# -- errors -----------------------------------------------------------------


def auth_failed():
    return auth.auth_error(
        "Invalid connector session.",
        "Sign in again from the add-in with your DG account.",
        "CONNECTOR_AUTH_FAILED",
        401,
    )


def session_expired():
    return auth.auth_error(
        "The connector session has expired.",
        "Sign in again from the add-in with your DG account.",
        "CONNECTOR_SESSION_EXPIRED",
        401,
    )


def session_ended():
    return auth.auth_error(
        "The connector session has ended.",
        "Sign in again from the add-in with your DG account.",
        "CONNECTOR_SESSION_ENDED",
        401,
    )


# -- helpers ----------------------------------------------------------------


def effective_role_for(username: str, project: str) -> str | None:
    """``owner`` for an admin user, else the stored role of (username, project)
    or None. Mirrors ``auth.effective_role`` for a user principal."""
    user = auth.get_user(username)
    if user is not None and user.get("is_admin"):
        return "owner"
    return auth.get_role(username, project)


def _public(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    digest = out.pop("token_hash", None) or ""
    out["session_id"] = digest[:16]
    return out


# -- issue ------------------------------------------------------------------


def issue(
    *,
    username: str,
    project: str,
    connector_id: str,
    now: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Mint a ``dgk_`` session for `username`, `project` and `connector_id`, bound
    to the project's current company. Returns ``(raw_token, public_record)``; the
    record never carries the hash (it carries ``session_id`` instead). The caller
    must already have proved the user's credentials and authorization."""
    current = auth._now(now)
    normalized = username.strip().lower()
    token = SESSION_TOKEN_PREFIX + secrets.token_urlsafe(32)
    record: dict[str, Any] = {
        "token_hash": _hash(token),
        "username": normalized,
        "project": project,
        "connector_id": connector_id,
        "company": company.company_for_project(project),
        "issued_at": current,
        "expires_at": current + session_ttl_seconds(),
        "last_seen": current,
        "revoked": False,
    }
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        kept = [
            r for r in rows if int(r.get("expires_at", 0)) + _RETENTION_SECONDS >= current
        ]
        kept.append(record)
        auth._save(_file(), _KEY, kept)
    return token, _public(record)


# -- authenticate -----------------------------------------------------------


def _mark_revoked(rows: list[dict[str, Any]], record: dict[str, Any], reason: str) -> None:
    record["revoked"] = True
    record["revoked_reason"] = reason
    auth._save(_file(), _KEY, rows)


def authenticate(token: str | None, *, now: int | None = None) -> dict[str, Any] | None:
    """Resolve a ``dgk_`` Bearer token to its public session record.

    Returns None when `token` is not a ``dgk_`` string (the caller falls through
    to the next credential kind). Otherwise returns the record or raises the
    named ``HTTPException`` (see the module docstring). The user, the company
    and the connector authorization are re-checked on every call."""
    if not token or not isinstance(token, str) or not token.startswith(SESSION_TOKEN_PREFIX):
        return None
    digest = _hash(token)
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        record = next((r for r in rows if r.get("token_hash") == digest), None)
        if record is None:
            raise auth_failed()
        if record.get("revoked"):
            raise session_ended()
        if current >= int(record.get("expires_at", 0)):
            raise session_expired()

        username = record.get("username") or ""
        project = record.get("project") or ""
        connector_id = record.get("connector_id") or ""
        if auth.get_user(username) is None:
            _mark_revoked(rows, record, REASON_USER_GONE)
            raise session_ended()
        if company.company_for_project(project) != record.get("company"):
            _mark_revoked(rows, record, REASON_SCOPE_CHANGED)
            raise session_ended()
        role = effective_role_for(username, project)
        if not connector_access.is_authorized(username, project, connector_id, role=role):
            raise connector_access.access_required()
        return _public(record)


# -- revoke -----------------------------------------------------------------


def _revoke_where(
    predicate: Callable[[dict[str, Any]], bool], reason: str = REASON_EXPLICIT
) -> int:
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


def revoke_token(token: str | None) -> bool:
    """Revoke the one session `token`. False if unknown or already revoked."""
    if not token or not isinstance(token, str):
        return False
    digest = _hash(token)
    return _revoke_where(lambda r: r.get("token_hash") == digest, REASON_EXPLICIT) > 0


def revoke_for_user(username: str, reason: str = REASON_USER_GONE) -> int:
    """Revoke every live session of `username` (password change, deletion)."""
    normalized = (username or "").strip().lower()
    return _revoke_where(lambda r: r.get("username") == normalized, reason)


def revoke_for_user_project(
    username: str, project: str, reason: str = REASON_MEMBERSHIP_REMOVED
) -> int:
    """Revoke the live sessions of `username` bound to `project` (membership
    removal)."""
    normalized = (username or "").strip().lower()
    return _revoke_where(
        lambda r: r.get("username") == normalized and r.get("project") == project, reason
    )


def revoke_for_project(project: str, reason: str = REASON_PROJECT_SCOPE) -> int:
    """Revoke every live session bound to `project` (company reassignment,
    project deletion)."""
    return _revoke_where(lambda r: r.get("project") == project, reason)


def revoke_for_connector_grant(
    username: str, project: str, connector_id: str, reason: str = REASON_GRANT_REVOKED
) -> int:
    """Revoke the live sessions of one (user, project, connector) triple (the
    per-connector access grant was revoked)."""
    normalized = (username or "").strip().lower()
    return _revoke_where(
        lambda r: r.get("username") == normalized
        and r.get("project") == project
        and r.get("connector_id") == connector_id,
        reason,
    )


def revoke_unauthorized(username: str, project: str, reason: str = REASON_UNAUTHORIZED) -> int:
    """Revoke the live sessions of `username` on `project` for connectors the
    user is no longer authorized for (demotion, grant revoked), keeping the
    authorized ones. Keeps the connector status honest between requests."""
    normalized = (username or "").strip().lower()
    with auth._STORE_LOCK:
        role = effective_role_for(normalized, project)
        return _revoke_where(
            lambda r: r.get("username") == normalized
            and r.get("project") == project
            and not connector_access.is_authorized(
                normalized, project, r.get("connector_id") or "", role=role
            ),
            reason,
        )


# -- touch, status, answer --------------------------------------------------


def _is_live(row: dict[str, Any], current: int) -> bool:
    return not row.get("revoked") and current < int(row.get("expires_at", 0))


def touch(token: str | None, *, now: int | None = None) -> dict[str, Any] | None:
    """Stamp ``last_seen`` of a live session (heartbeat) and return its public
    record; None for a non-``dgk_``, unknown, revoked or expired token."""
    if not token or not isinstance(token, str) or not token.startswith(SESSION_TOKEN_PREFIX):
        return None
    digest = _hash(token)
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
        record = next((r for r in rows if r.get("token_hash") == digest), None)
        if record is None or not _is_live(record, current):
            return None
        record["last_seen"] = current
        auth._save(_file(), _KEY, rows)
        return _public(record)


def _iso(ts: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ts)))


def status_for(
    connector_id: str,
    *,
    projects: set[str] | frozenset[str] | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    """The sign-in status of one connector over `projects` (D-32; None means all
    projects, the admin view): ``active`` when at least one non-revoked,
    non-expired session exists, ``stale`` when sessions existed but none is
    live, ``never_connected`` when none is stored (or all were pruned)."""
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_file(), _KEY)
    scoped = [
        r
        for r in rows
        if r.get("connector_id") == connector_id
        and (projects is None or r.get("project") in projects)
    ]
    if not scoped:
        return {"status": "never_connected", "active_sessions": 0, "last_sign_in": None}
    live = sum(1 for r in scoped if _is_live(r, current))
    newest = max(int(r.get("issued_at", 0)) for r in scoped)
    return {
        "status": "active" if live else "stale",
        "active_sessions": live,
        "last_sign_in": _iso(newest),
    }


def public_answer(
    token: str, record: dict[str, Any], *, neo4j: Any = None
) -> dict[str, Any]:
    """The one answer shape of the sign-in mint (the only place the raw token is
    returned). `neo4j` (a dict or a model with ``model_dump``) is added only when
    given."""
    expires_at = int(record["expires_at"])
    answer: dict[str, Any] = {
        "token": token,
        "project": record["project"],
        "connectorId": record["connector_id"],
        "username": record["username"],
        "company": record.get("company"),
        "expiresAt": _iso(expires_at),
        "expiresInSeconds": expires_at - int(record["issued_at"]),
    }
    if neo4j is not None:
        answer["neo4j"] = neo4j.model_dump() if hasattr(neo4j, "model_dump") else neo4j
    return answer
