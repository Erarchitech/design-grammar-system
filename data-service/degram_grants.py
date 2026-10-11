"""DeGram access grants (Phase 1301, plan 30, D-39, D-40, DGCL-01, DGCL-05).

DeGram access is issued by a DG admin or the owner of a project, per project
member, on the Connectors tab. The key never leaves the server and the user
never handles a credential: a grant is only a *record of authorization*. It
carries no secret and no route returns one. The user signs in to DG, and
``POST /auth/degram/session-exchange`` trades the cookie session for the
usual short-lived ``dgd_`` token (``delegation.py``) once an active grant for
the project exists.

A grant is bound to one ``(username, project)`` pair; there is at most one
active grant per pair (issuing again replaces the old one and ends its
tokens). A grant is active while it is not revoked, its user still exists and
the user is still a stored member of its project. ``delegation`` re-checks
that on every ``dgd_`` request (``is_live``), and every revoking path also
marks the grant's delegated tokens revoked, so access ends at once when the
owner/admin revokes the grant, the member is removed or the user is deleted.
A password change ends the tokens (``delegation.revoke_for_user``) but not the
grant, which is the admin's decision.

A member without a grant can ask for one (D-40): a pending request is listed
beside the grants for the project's owners and admins and is closed when a
grant is issued.

Storage is ``degram-grants.json`` and ``degram-grant-requests.json`` next to
the other auth stores, written through ``auth._load`` / ``auth._save`` under
``auth._STORE_LOCK``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import auth

GRANTS_FILE_NAME = "degram-grants.json"
REQUESTS_FILE_NAME = "degram-grant-requests.json"

LABEL_MAX = 120
PURPOSE_MAX = 200
NOTE_MAX = 200

CONNECTOR_ID = "degram"
CONNECTOR_NAME = "DeGram"
CATEGORY = "Agents"
CARD_DESCRIPTION = (
    "DeGram access is issued by the project owner or a DG admin. "
    "Sign in to DG in DeGram; no key is shown or copied."
)

_GRANTS_KEY = "grants"
_REQUESTS_KEY = "requests"

STATUS_PENDING = "pending"
STATUS_CLOSED = "closed"


def _grants_file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / GRANTS_FILE_NAME


def _requests_file() -> Path:
    return auth.MEMBERSHIPS_FILE.parent / REQUESTS_FILE_NAME


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -- errors -----------------------------------------------------------------


def grant_required():
    return auth.auth_error(
        "DeGram access for this project has not been granted to you.",
        "Ask the project owner or a DG admin to grant DeGram access on the Connectors tab.",
        "GRANT_REQUIRED",
        403,
    )


def not_a_member():
    return auth.auth_error(
        "That user is not a member of this project.",
        "Add the user to the project first, then grant DeGram access.",
        "NOT_A_MEMBER",
        409,
    )


def grant_invalid(hint: str):
    return auth.auth_error("The DeGram grant request is not valid.", hint, "GRANT_INVALID", 422)


def grant_not_found():
    return auth.auth_error(
        "DeGram grant not found.",
        "Use a grant id from GET /projects/{project}/degram-grants.",
        "GRANT_NOT_FOUND",
        404,
    )


def grant_exists():
    return auth.auth_error(
        "DeGram access is already granted for this project.",
        "Open DeGram and sign in to DG.",
        "GRANT_EXISTS",
        409,
    )


# -- serializers (none of them carries a secret) -----------------------------


def _is_active(row: dict[str, Any]) -> bool:
    if row.get("revoked"):
        return False
    username = row.get("username") or ""
    return auth.get_user(username) is not None and auth.get_role(username, row.get("project") or "") is not None


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "grant_id": row.get("grant_id"),
        "username": row.get("username"),
        "project": row.get("project"),
        "label": row.get("label", ""),
        "purpose": row.get("purpose", ""),
        "issued_by": row.get("issued_by"),
        "created_at": _iso(row.get("created_at")),
        "last_used": _iso(row.get("last_used")),
        "revoked": bool(row.get("revoked")),
        "active": _is_active(row),
    }


def _public_mine(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": row.get("project"),
        "label": row.get("label", ""),
        "purpose": row.get("purpose", ""),
        "created_at": _iso(row.get("created_at")),
        "last_used": _iso(row.get("last_used")),
        "active": _is_active(row),
    }


def _public_request(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": row.get("request_id"),
        "username": row.get("username"),
        "project": row.get("project"),
        "note": row.get("note", ""),
        "created_at": _iso(row.get("created_at")),
        "status": row.get("status", STATUS_PENDING),
    }


# -- issue ------------------------------------------------------------------


def _clean(value: str | None, limit: int, field: str) -> str:
    text = (value or "").strip()
    if not text or len(text) > limit:
        raise grant_invalid(f"{field} must be 1-{limit} characters.")
    return text


def issue_grant(
    project: str,
    username: str,
    label: str,
    purpose: str,
    issued_by: str,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Issue the grant for `username` on `project`. The target must be an
    existing user holding a stored membership of the project. An earlier active
    grant of the same pair is revoked together with its delegated tokens, and
    any pending request of the pair is closed. Returns the public record."""
    import delegation  # noqa: PLC0415 -- delegation imports this module

    clean_label = _clean(label, LABEL_MAX, "label")
    clean_purpose = _clean(purpose, PURPOSE_MAX, "purpose")
    normalized = username.strip().lower()
    current = auth._now(now)
    with auth._STORE_LOCK:
        if auth.get_user(normalized) is None or auth.get_role(normalized, project) is None:
            raise not_a_member()
        rows = auth._load(_grants_file(), _GRANTS_KEY)
        replaced: list[str] = []
        for row in rows:
            if (
                not row.get("revoked")
                and row.get("username") == normalized
                and row.get("project") == project
            ):
                row["revoked"] = True
                row["revoked_at"] = current
                row["revoked_by"] = issued_by
                replaced.append(row.get("grant_id") or "")
        record: dict[str, Any] = {
            "grant_id": uuid.uuid4().hex,
            "username": normalized,
            "project": project,
            "label": clean_label,
            "purpose": clean_purpose,
            "issued_by": (issued_by or "").strip().lower(),
            "created_at": current,
            "last_used": None,
            "revoked": False,
        }
        rows.append(record)
        auth._save(_grants_file(), _GRANTS_KEY, rows)
        _close_requests(normalized, project, record["grant_id"], current)
    for grant_id in replaced:
        delegation.revoke_for_grant(grant_id)
    return _public(record)


def revoke_grant(project: str, grant_id: str, actor: str, *, now: int | None = None) -> bool:
    """Revoke `grant_id` of `project` and every ``dgd_`` minted from it. False
    when no such grant exists under the project (the route answers an unknown id
    and another project's id with the same 404)."""
    import delegation  # noqa: PLC0415

    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
        record = next(
            (r for r in rows if r.get("grant_id") == grant_id and r.get("project") == project),
            None,
        )
        if record is None:
            return False
        if not record.get("revoked"):
            record["revoked"] = True
            record["revoked_at"] = current
            record["revoked_by"] = (actor or "").strip().lower()
            auth._save(_grants_file(), _GRANTS_KEY, rows)
    delegation.revoke_for_grant(grant_id)
    return True


# -- resolve ----------------------------------------------------------------


def active_grant(username: str, project: str) -> dict[str, Any] | None:
    """The active grant (raw row) of `username` on `project`, or None."""
    normalized = username.strip().lower()
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
    return next(
        (
            r
            for r in rows
            if r.get("username") == normalized and r.get("project") == project and _is_active(r)
        ),
        None,
    )


def is_live(grant_id: str, username: str, project: str) -> bool:
    """True while grant `grant_id` is active and belongs to `username` and
    `project` (the re-check ``delegation`` runs on every ``dgd_`` request)."""
    if not grant_id:
        return False
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
    record = next((r for r in rows if r.get("grant_id") == grant_id), None)
    return (
        record is not None
        and record.get("username") == username.strip().lower()
        and record.get("project") == project
        and _is_active(record)
    )


def record_use(grant_id: str, *, now: int | None = None) -> None:
    current = auth._now(now)
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
        for row in rows:
            if row.get("grant_id") == grant_id:
                row["last_used"] = current
                auth._save(_grants_file(), _GRANTS_KEY, rows)
                return


# -- list -------------------------------------------------------------------


def list_for_project(project: str) -> list[dict[str, Any]]:
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
    return [_public(r) for r in rows if r.get("project") == project]


def list_all() -> list[dict[str, Any]]:
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
    return [_public(r) for r in rows]


def list_mine(username: str) -> list[dict[str, Any]]:
    """The caller's own grants only (D-40): no grant id, no other user's row."""
    normalized = username.strip().lower()
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
    return [_public_mine(r) for r in rows if r.get("username") == normalized]


def connector_card(username: str, is_admin: bool, derive_status) -> dict[str, Any]:
    """The DeGram entry of ``GET /connectors``: the caller's grants (an admin:
    everyone's). `derive_status` is ``connectors.derive_status``."""
    if is_admin:
        grants = list_all()
    else:
        normalized = username.strip().lower()
        grants = [g for g in list_all() if g["username"] == normalized]
    credentials: list[dict[str, Any]] = []
    for g in grants:
        entry = {
            "credential_id": g["grant_id"],
            "label": g["label"],
            "purpose": g["purpose"],
            "project": g["project"],
            "created_at": g["created_at"],
            "last_exchange": g["last_used"],
            "revoked": not g["active"],
        }
        if is_admin:
            entry["username"] = g["username"]
        credentials.append(entry)
    stamps = [c["last_exchange"] for c in credentials if c["last_exchange"]]
    last = max(stamps) if stamps else None
    return {
        "id": CONNECTOR_ID,
        "name": CONNECTOR_NAME,
        "category": CATEGORY,
        "description": CARD_DESCRIPTION,
        "status": derive_status(last.replace("Z", "+00:00") if last else None),
        "last_connection": last,
        "credentials": credentials,
    }


# -- requests (D-40) --------------------------------------------------------


def create_request(
    username: str, project: str, note: str | None = None, *, now: int | None = None
) -> dict[str, Any]:
    """Record a pending request of a member for a grant. A second request of
    the same pair replaces the note instead of adding a row. 409
    ``GRANT_EXISTS`` when an active grant already exists."""
    clean_note = (note or "").strip()
    if len(clean_note) > NOTE_MAX:
        raise grant_invalid(f"note must be at most {NOTE_MAX} characters.")
    normalized = username.strip().lower()
    current = auth._now(now)
    with auth._STORE_LOCK:
        if active_grant(normalized, project) is not None:
            raise grant_exists()
        rows = auth._load(_requests_file(), _REQUESTS_KEY)
        record = next(
            (
                r
                for r in rows
                if r.get("username") == normalized
                and r.get("project") == project
                and r.get("status") == STATUS_PENDING
            ),
            None,
        )
        if record is None:
            record = {
                "request_id": uuid.uuid4().hex,
                "username": normalized,
                "project": project,
                "created_at": current,
                "status": STATUS_PENDING,
            }
            rows.append(record)
        record["note"] = clean_note
        auth._save(_requests_file(), _REQUESTS_KEY, rows)
    return _public_request(record)


def list_requests(project: str) -> list[dict[str, Any]]:
    """Pending requests for `project`."""
    with auth._STORE_LOCK:
        rows = auth._load(_requests_file(), _REQUESTS_KEY)
    return [
        _public_request(r)
        for r in rows
        if r.get("project") == project and r.get("status") == STATUS_PENDING
    ]


def list_requests_mine(username: str) -> list[dict[str, Any]]:
    normalized = username.strip().lower()
    with auth._STORE_LOCK:
        rows = auth._load(_requests_file(), _REQUESTS_KEY)
    return [
        {"project": r.get("project"), "note": r.get("note", ""), "created_at": _iso(r.get("created_at"))}
        for r in rows
        if r.get("username") == normalized and r.get("status") == STATUS_PENDING
    ]


def _close_requests(username: str, project: str, grant_id: str, current: int) -> None:
    with auth._STORE_LOCK:
        rows = auth._load(_requests_file(), _REQUESTS_KEY)
        changed = False
        for row in rows:
            if (
                row.get("username") == username
                and row.get("project") == project
                and row.get("status") == STATUS_PENDING
            ):
                row["status"] = STATUS_CLOSED
                row["closed_at"] = current
                row["closed_by_grant"] = grant_id
                changed = True
        if changed:
            auth._save(_requests_file(), _REQUESTS_KEY, rows)


# -- revoke cascades --------------------------------------------------------


def _revoke_where(predicate, actor: str = "system") -> list[str]:
    import delegation  # noqa: PLC0415

    current = auth._now(None)
    with auth._STORE_LOCK:
        rows = auth._load(_grants_file(), _GRANTS_KEY)
        ended: list[str] = []
        for row in rows:
            if not row.get("revoked") and predicate(row):
                row["revoked"] = True
                row["revoked_at"] = current
                row["revoked_by"] = actor
                ended.append(row.get("grant_id") or "")
        if ended:
            auth._save(_grants_file(), _GRANTS_KEY, rows)
    for grant_id in ended:
        delegation.revoke_for_grant(grant_id)
    return ended


def revoke_for_user(username: str) -> int:
    """Revoke every grant of `username` and their delegated tokens (the user
    no longer exists)."""
    normalized = username.strip().lower()
    return len(_revoke_where(lambda r: r.get("username") == normalized))


def revoke_for_user_project(username: str, project: str) -> int:
    """Revoke the grant of `username` on `project` and its delegated tokens
    (membership removal)."""
    normalized = username.strip().lower()
    return len(
        _revoke_where(lambda r: r.get("username") == normalized and r.get("project") == project)
    )
