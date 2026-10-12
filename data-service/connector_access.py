"""Per-connector access grants and requests (Phase 1301 plan 40, D-46, DGCL-05, DGCL-06).

A project owner, editor and an admin create connector credentials (Grasshopper,
Revit, ...) without ceremony. A project *viewer* can ask for access to one
connector of the project; the owner or an admin approves it, and only then may
that viewer create the connector's credential. Approving = issuing: issuing
access closes the viewer's pending request for the same connector.

A grant is a record of authorization only. It carries no secret and no route
returns one; the credential token still comes from
``POST /connectors/{connector_id}/credentials`` and is shown once to the caller.

A grant is bound to ``(username, project, connector_id)``. It is active while it
is not revoked, its user still exists and the user is still a stored member of
its project. Removing the membership revokes the user's grants of that project
(``revoke_for_user_project``), so a member who is later re-added does not
silently regain access. Deleting the user revokes every grant of the user
(``revoke_for_user``).

Storage is ``connector-access.json`` (``grants`` and ``requests``) next to the
other auth stores, written atomically under ``auth._STORE_LOCK``.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import auth
import connectors

FILE_NAME = "connector-access.json"
NOTE_MAX = 200

STATE_AVAILABLE = "available"
STATE_REQUESTABLE = "requestable"
STATE_PENDING = "pending"

STATUS_PENDING = "pending"
STATUS_CLOSED = "closed"

_GRANTS_KEY = "grants"
_REQUESTS_KEY = "requests"


def _file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / FILE_NAME


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    from datetime import datetime, timezone  # noqa: PLC0415

    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = _file()
    return auth._load(path, _GRANTS_KEY), auth._load(path, _REQUESTS_KEY)


def _save(grants: list[dict[str, Any]], requests: list[dict[str, Any]]) -> None:
    """Write both lists in one atomic replace (``auth._save`` writes one key)."""
    path = _file()
    with auth._STORE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        try:
            tmp_path.write_text(
                json.dumps({_GRANTS_KEY: grants, _REQUESTS_KEY: requests}, indent=2),
                encoding="utf-8",
            )
            try:
                os.chmod(tmp_path, 0o600)
            except OSError:
                pass
            for attempt in range(8):
                try:
                    os.replace(tmp_path, path)
                    break
                except PermissionError as exc:
                    if (
                        os.name != "nt"
                        or getattr(exc, "winerror", None) not in (5, 32, 33)
                        or attempt == 7
                    ):
                        raise
                    time.sleep(min(0.01 * (2**attempt), 0.1))
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass


# -- errors -----------------------------------------------------------------


def access_required():
    return auth.auth_error(
        "Access to this connector has not been granted to you for this project.",
        "Request access to the connector; the project owner or a DG admin approves it.",
        "CONNECTOR_ACCESS_REQUIRED",
        403,
    )


def access_exists():
    return auth.auth_error(
        "You can already create credentials for this connector in this project.",
        "Create the credential on the Connectors tab.",
        "ACCESS_EXISTS",
        409,
    )


def access_not_found():
    return auth.auth_error(
        "Connector access not found.",
        "Use an access id from GET /projects/{project}/connector-access.",
        "ACCESS_NOT_FOUND",
        404,
    )


def connector_not_found():
    return auth.auth_error(
        "Unknown connector.",
        "Use a connector id from GET /connectors (DeGram access is requested separately).",
        "CONNECTOR_NOT_FOUND",
        404,
    )


def not_a_member():
    return auth.auth_error(
        "That user is not a member of this project.",
        "Add the user to the project first, then grant connector access.",
        "NOT_A_MEMBER",
        409,
    )


def access_invalid(hint: str):
    return auth.auth_error("The connector access request is not valid.", hint, "ACCESS_INVALID", 422)


def check_connector(connector_id: str) -> None:
    # DeGram is not a registry connector: no dgc_ token exists for it (D-39).
    if connector_id not in connectors.CONNECTOR_IDS:
        raise connector_not_found()


# -- serializers (none of them carries a secret) -----------------------------


def _is_active(row: dict[str, Any]) -> bool:
    if row.get("revoked"):
        return False
    username = row.get("username") or ""
    return auth.get_user(username) is not None and auth.get_role(username, row.get("project") or "") is not None


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "access_id": row.get("access_id"),
        "username": row.get("username"),
        "project": row.get("project"),
        "connector_id": row.get("connector_id"),
        "issued_by": row.get("issued_by"),
        "created_at": _iso(row.get("created_at")),
        "revoked": bool(row.get("revoked")),
        "active": _is_active(row),
    }


def _public_mine(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": row.get("project"),
        "connector_id": row.get("connector_id"),
        "created_at": _iso(row.get("created_at")),
        "active": _is_active(row),
    }


def _public_request(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": row.get("request_id"),
        "username": row.get("username"),
        "project": row.get("project"),
        "connector_id": row.get("connector_id"),
        "note": row.get("note", ""),
        "created_at": _iso(row.get("created_at")),
        "status": row.get("status", STATUS_PENDING),
    }


# -- resolve ----------------------------------------------------------------


def can_create(username: str, project: str, connector_id: str) -> bool:
    """True while `username` holds an active access for `connector_id` on
    `project`. Owner, editor and admin never need one (the handler checks the
    role first)."""
    normalized = (username or "").strip().lower()
    with auth._STORE_LOCK:
        grants, _requests = _load()
    return any(
        g.get("username") == normalized
        and g.get("project") == project
        and g.get("connector_id") == connector_id
        and _is_active(g)
        for g in grants
    )


def is_exempt(role: str | None) -> bool:
    """True for an owner (stored) or an admin (effective role ``owner``): they
    never need a per-connector access row (Phase 1308, D-29). Editor, viewer and
    a missing role are not exempt."""
    return auth.role_satisfies(role, "owner")


def is_authorized(username: str, project: str, connector_id: str, *, role: str | None) -> bool:
    """The connector sign-in predicate (Phase 1308, D-29): an exempt role, or an
    active per-connector access row for this (user, project, connector)."""
    return is_exempt(role) or can_create(username, project, connector_id)


def _has_pending(username: str, project: str, connector_id: str, requests) -> bool:
    return any(
        r.get("username") == username
        and r.get("project") == project
        and r.get("connector_id") == connector_id
        and r.get("status") == STATUS_PENDING
        for r in requests
    )


def access_state(username: str, project: str, role: str | None, connector_id: str) -> str:
    """The caller's access to one connector in one project: ``available`` for
    an owner/editor (or an admin, whose effective role is owner) or an active
    grant, ``pending`` for an open request, else ``requestable``."""
    if auth.role_satisfies(role, "editor"):
        return STATE_AVAILABLE
    normalized = (username or "").strip().lower()
    with auth._STORE_LOCK:
        grants, requests = _load()
    if any(
        g.get("username") == normalized
        and g.get("project") == project
        and g.get("connector_id") == connector_id
        and _is_active(g)
        for g in grants
    ):
        return STATE_AVAILABLE
    if _has_pending(normalized, project, connector_id, requests):
        return STATE_PENDING
    return STATE_REQUESTABLE


# -- requests ---------------------------------------------------------------


def create_request(
    username: str,
    project: str,
    connector_id: str,
    note: str | None = None,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Record a pending request of a project viewer. A second request of the
    same (user, project, connector) replaces the note instead of adding a row.
    409 ``ACCESS_EXISTS`` when the caller is already an owner/editor of the
    project or holds an active access."""
    check_connector(connector_id)
    clean_note = (note or "").strip()
    if len(clean_note) > NOTE_MAX:
        raise access_invalid(f"note must be at most {NOTE_MAX} characters.")
    normalized = username.strip().lower()
    current = auth._now(now)
    with auth._STORE_LOCK:
        if auth.role_satisfies(auth.get_role(normalized, project), "editor") or can_create(
            normalized, project, connector_id
        ):
            raise access_exists()
        grants, requests = _load()
        record = next(
            (
                r
                for r in requests
                if r.get("username") == normalized
                and r.get("project") == project
                and r.get("connector_id") == connector_id
                and r.get("status") == STATUS_PENDING
            ),
            None,
        )
        if record is None:
            record = {
                "request_id": uuid.uuid4().hex,
                "username": normalized,
                "project": project,
                "connector_id": connector_id,
                "created_at": current,
                "status": STATUS_PENDING,
            }
            requests.append(record)
        record["note"] = clean_note
        _save(grants, requests)
    return _public_request(record)


def list_requests(project: str) -> list[dict[str, Any]]:
    """Pending requests for `project`."""
    with auth._STORE_LOCK:
        _grants, requests = _load()
    return [
        _public_request(r)
        for r in requests
        if r.get("project") == project and r.get("status") == STATUS_PENDING
    ]


def list_requests_mine(username: str) -> list[dict[str, Any]]:
    normalized = username.strip().lower()
    with auth._STORE_LOCK:
        _grants, requests = _load()
    return [
        {
            "project": r.get("project"),
            "connector_id": r.get("connector_id"),
            "note": r.get("note", ""),
            "created_at": _iso(r.get("created_at")),
        }
        for r in requests
        if r.get("username") == normalized and r.get("status") == STATUS_PENDING
    ]


# -- issue / revoke ---------------------------------------------------------


def issue_access(
    project: str,
    username: str,
    connector_id: str,
    issued_by: str,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Issue the access of `username` to `connector_id` on `project`. The target
    must be an existing user holding a stored membership of the project. An
    earlier active access of the same triple is revoked (one active row), and
    the pending request of the triple is closed. Returns the public record."""
    check_connector(connector_id)
    normalized = username.strip().lower()
    current = auth._now(now)
    actor = (issued_by or "").strip().lower()
    with auth._STORE_LOCK:
        if auth.get_user(normalized) is None or auth.get_role(normalized, project) is None:
            raise not_a_member()
        grants, requests = _load()
        for row in grants:
            if (
                not row.get("revoked")
                and row.get("username") == normalized
                and row.get("project") == project
                and row.get("connector_id") == connector_id
            ):
                row["revoked"] = True
                row["revoked_at"] = current
                row["revoked_by"] = actor
        record: dict[str, Any] = {
            "access_id": uuid.uuid4().hex,
            "username": normalized,
            "project": project,
            "connector_id": connector_id,
            "issued_by": actor,
            "created_at": current,
            "revoked": False,
        }
        grants.append(record)
        for row in requests:
            if (
                row.get("username") == normalized
                and row.get("project") == project
                and row.get("connector_id") == connector_id
                and row.get("status") == STATUS_PENDING
            ):
                row["status"] = STATUS_CLOSED
                row["closed_at"] = current
                row["closed_by_access"] = record["access_id"]
        _save(grants, requests)
    return _public(record)


def revoke_access(project: str, access_id: str, actor: str, *, now: int | None = None) -> bool:
    """Revoke `access_id` of `project`. False when no such access exists under
    the project (an unknown id and another project's id answer the same 404)."""
    current = auth._now(now)
    with auth._STORE_LOCK:
        grants, requests = _load()
        record = next(
            (g for g in grants if g.get("access_id") == access_id and g.get("project") == project),
            None,
        )
        if record is None:
            return False
        if not record.get("revoked"):
            record["revoked"] = True
            record["revoked_at"] = current
            record["revoked_by"] = (actor or "").strip().lower()
            _save(grants, requests)
    return True


def list_for_project(project: str) -> list[dict[str, Any]]:
    with auth._STORE_LOCK:
        grants, _requests = _load()
    return [_public(g) for g in grants if g.get("project") == project]


def list_mine(username: str) -> list[dict[str, Any]]:
    """The caller's own accesses only: no access id, no other user's row."""
    normalized = username.strip().lower()
    with auth._STORE_LOCK:
        grants, _requests = _load()
    return [_public_mine(g) for g in grants if g.get("username") == normalized]


# -- revoke cascades --------------------------------------------------------


def _revoke_where(predicate, actor: str = "system") -> int:
    current = auth._now(None)
    with auth._STORE_LOCK:
        grants, requests = _load()
        changed = 0
        for row in grants:
            if not row.get("revoked") and predicate(row):
                row["revoked"] = True
                row["revoked_at"] = current
                row["revoked_by"] = actor
                changed += 1
        # a pending request of the same scope ends with it
        for row in requests:
            if row.get("status") == STATUS_PENDING and predicate(row):
                row["status"] = STATUS_CLOSED
                row["closed_at"] = current
                changed += 1
        if changed:
            _save(grants, requests)
    return changed


def revoke_for_user(username: str) -> int:
    """Revoke every access (and close every request) of `username`."""
    normalized = username.strip().lower()
    return _revoke_where(lambda r: r.get("username") == normalized)


def revoke_for_user_project(username: str, project: str) -> int:
    """Revoke the accesses of `username` on `project` (membership removal)."""
    normalized = username.strip().lower()
    return _revoke_where(lambda r: r.get("username") == normalized and r.get("project") == project)
