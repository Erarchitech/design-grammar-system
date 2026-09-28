"""Server-side identity store (Phase 1205 "Security and Tenancy Release Gate",
D-01/D-02/D-04/D-05/D-07/D-19). No route wiring lives here -- this module is a
pure data layer consumed by 1205-07 (require_principal dependency) and later
plans in this phase.

Storage choice (Claude's discretion, recorded in 1205-02-PLAN.md): JSON files
under ``AUTH_DIR`` mirroring ``connectors.py``'s persistence idiom -- NOT
Neo4j nodes. This keeps the Schema Change Propagation list in CLAUDE.md
deliberately untouched: no ``cypher_template.txt``, ``dataset_schema.json``,
SHACL, LPG-OWL-MAPPING or ``spec/DATABASE.md`` change is needed for this
module to exist.

Single-process invariant: ``data-service/Dockerfile`` runs one uvicorn
worker process (no ``--workers`` flag), so a single ``threading.RLock``
(``_STORE_LOCK``) safely serialises every read-modify-write across the four
JSON stores. A multi-worker deployment would need a cross-process file lock
instead -- recorded as a constraint in ``spec/SECURITY-BOUNDARY.md`` (1205-16).

Nothing in this module logs or returns a password, session token, service
token or invite code in the clear. Store functions never reveal *why* a
lookup failed (unknown user vs. wrong password vs. revoked vs. expired) --
they return ``None``/``False`` uniformly, so no distinct return shape, log
line or message leaks which of those occurred.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import connectors

# ── Constants (Claude's discretion per 1205-02-PLAN.md Artifacts table) ──

SESSION_COOKIE_NAME = "dg_session"
SESSION_TOKEN_PREFIX = "dgs_"
INVITE_CODE_PREFIX = "dgi_"
CSRF_HEADER = "X-DG-CSRF"
SERVICE_TOKEN_HEADER = "X-DG-Service-Token"

ROLES: tuple[str, ...] = ("viewer", "editor", "owner")
ROLE_RANK: dict[str, int] = {"viewer": 0, "editor": 1, "owner": 2}

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

SESSION_TOUCH_INTERVAL_SECONDS = 60
INVITE_TTL_SECONDS = 259200  # 72 hours

DEPLOYMENT_PROFILES: tuple[str, ...] = ("local", "multi-user")

_USERNAME_RE = re.compile(r"^[a-z0-9._@+-]{3,254}$")

# ── Persistence (mirrors connectors.py's DATA_DIR / load / save idiom) ──

AUTH_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
USERS_FILE = AUTH_DIR / "auth-users.json"
SESSIONS_FILE = AUTH_DIR / "auth-sessions.json"
MEMBERSHIPS_FILE = AUTH_DIR / "auth-memberships.json"
INVITES_FILE = AUTH_DIR / "auth-invites.json"

# Serialises every read-modify-write against the four JSON stores above (see
# module docstring: single uvicorn worker process, so a threading lock is
# sufficient -- no cross-process file lock is needed).
_STORE_LOCK = threading.RLock()


def _load(path: Path, key: str) -> list[dict[str, Any]]:
    """Read a row list from a JSON store.

    Fail-soft: returns ``[]`` if the file is missing, malformed, or empty --
    mirrors ``connectors.load_credentials``.
    """
    with _STORE_LOCK:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, dict):
            return []
        rows = payload.get(key)
        if not isinstance(rows, list):
            return []
        return [r for r in rows if isinstance(r, dict)]


def _save(path: Path, key: str, rows: list[dict[str, Any]]) -> None:
    """Write a row list to a JSON store atomically (temp file + os.replace)."""
    with _STORE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        tmp_path.write_text(
            json.dumps({key: rows}, indent=2), encoding="utf-8"
        )
        os.replace(tmp_path, path)


def _now(now: int | None) -> int:
    return int(now) if now is not None else int(time.time())


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return env if env is not None else os.environ


# ── Passwords (D-01) ──


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def hash_password(password: str) -> str:
    """Hash a password with stdlib scrypt (n=16384, r=8, p=1, dklen=64) and a
    per-user random 16-byte salt. Encoding: ``scrypt$16384$8$1$<salt_b64>$<hash_b64>``.
    Two calls with the same password yield different encodings (random salt).
    """
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64
    )
    return "scrypt$16384$8$1$" + _b64encode(salt) + "$" + _b64encode(derived)


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against a `hash_password` encoding. Returns False on
    any parse error, mismatch, or wrong password -- never raises.
    """
    try:
        parts = encoded.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = _b64decode(parts[4])
        stored_hash = _b64decode(parts[5])
        derived = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(stored_hash)
        )
        return hmac.compare_digest(derived, stored_hash)
    except Exception:
        return False


def validate_password_policy(password: str) -> None:
    """Raise ValueError unless PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH."""
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"password must be between {PASSWORD_MIN_LENGTH} and "
            f"{PASSWORD_MAX_LENGTH} characters"
        )


def normalize_username(username: str) -> str:
    """Strip and lowercase a username; raise ValueError unless it matches
    ``^[a-z0-9._@+-]{3,254}$`` after normalization."""
    normalized = username.strip().lower()
    if not _USERNAME_RE.match(normalized):
        raise ValueError("invalid username")
    return normalized


# ── Users (D-01) ──


def create_user(username: str, password: str, *, is_admin: bool = False) -> dict[str, Any]:
    """Create a new user. Raises ValueError for a duplicate normalized
    username or a password failing `validate_password_policy`."""
    normalized = normalize_username(username)
    validate_password_policy(password)
    with _STORE_LOCK:
        users = _load(USERS_FILE, "users")
        for u in users:
            if u.get("username") == normalized:
                raise ValueError("username already exists")
        record: dict[str, Any] = {
            "username": normalized,
            "password_hash": hash_password(password),
            "is_admin": bool(is_admin),
            "created_at": int(time.time()),
        }
        users.append(record)
        _save(USERS_FILE, "users", users)
        return dict(record)


def get_user(username: str) -> dict[str, Any] | None:
    """Return the stored user record (without exposing raw file structure),
    or None if the username is unknown. Never raises on malformed input."""
    if not username:
        return None
    normalized = username.strip().lower()
    with _STORE_LOCK:
        for u in _load(USERS_FILE, "users"):
            if u.get("username") == normalized:
                return dict(u)
    return None


def set_password(username: str, new_password: str) -> bool:
    """Validate and replace a user's password hash. Returns False if the
    user does not exist."""
    validate_password_policy(new_password)
    normalized = username.strip().lower()
    with _STORE_LOCK:
        users = _load(USERS_FILE, "users")
        changed = False
        for u in users:
            if u.get("username") == normalized:
                u["password_hash"] = hash_password(new_password)
                changed = True
        if changed:
            _save(USERS_FILE, "users", users)
        return changed


# ── Sessions (D-01) ──


def create_session(username: str, *, now: int | None = None) -> str:
    """Mint a new opaque session token (dgs_ + 32 random bytes). Only the
    SHA-256 hash of the token is persisted. Prunes revoked/expired sessions
    for this user opportunistically."""
    normalized = username.strip().lower()
    current = _now(now)
    ttl = int(os.getenv("DG_SESSION_TTL_SECONDS", "43200"))
    token = SESSION_TOKEN_PREFIX + secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _STORE_LOCK:
        sessions = _load(SESSIONS_FILE, "sessions")
        kept: list[dict[str, Any]] = []
        for s in sessions:
            if s.get("username") != normalized:
                kept.append(s)
                continue
            if s.get("revoked") or int(s.get("expires_at", 0)) <= current:
                continue  # prune revoked/expired sessions for this user
            kept.append(s)
        record: dict[str, Any] = {
            "token_hash": token_hash,
            "username": normalized,
            "created_at": current,
            "last_seen_at": current,
            "expires_at": current + ttl,
            "revoked": False,
        }
        kept.append(record)
        _save(SESSIONS_FILE, "sessions", kept)
    return token


def authenticate_session(token: str, *, now: int | None = None) -> dict[str, Any] | None:
    """Return the session record (without the hash) if `token` identifies a
    non-revoked, unexpired, non-idle-timed-out session; else None. Touches
    last_seen_at only when at least SESSION_TOUCH_INTERVAL_SECONDS elapsed.

    Boundary rules (inclusive-expired): now >= expires_at is expired;
    now - last_seen_at >= idle is expired.
    """
    if not token or not token.startswith(SESSION_TOKEN_PREFIX):
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    current = _now(now)
    idle = int(os.getenv("DG_SESSION_IDLE_SECONDS", "7200"))
    with _STORE_LOCK:
        sessions = _load(SESSIONS_FILE, "sessions")
        for s in sessions:
            if s.get("token_hash") != digest:
                continue
            if s.get("revoked"):
                return None
            if current >= int(s.get("expires_at", 0)):
                return None
            last_seen = int(s.get("last_seen_at", 0))
            if current - last_seen >= idle:
                return None
            if current - last_seen >= SESSION_TOUCH_INTERVAL_SECONDS:
                s["last_seen_at"] = current
                _save(SESSIONS_FILE, "sessions", sessions)
            result = dict(s)
            result.pop("token_hash", None)
            return result
    return None


def revoke_session(token: str) -> bool:
    """Mark the session identified by `token` as revoked. Returns False if
    unknown or already revoked."""
    if not token:
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    with _STORE_LOCK:
        sessions = _load(SESSIONS_FILE, "sessions")
        changed = False
        for s in sessions:
            if s.get("token_hash") == digest and not s.get("revoked"):
                s["revoked"] = True
                changed = True
        if changed:
            _save(SESSIONS_FILE, "sessions", sessions)
        return changed


def revoke_user_sessions(username: str, *, except_token_hash: str | None = None) -> int:
    """Revoke every non-revoked session for `username`, except one whose
    token_hash equals `except_token_hash` (if given). Returns the count
    revoked."""
    normalized = username.strip().lower()
    with _STORE_LOCK:
        sessions = _load(SESSIONS_FILE, "sessions")
        count = 0
        for s in sessions:
            if s.get("username") != normalized:
                continue
            if except_token_hash and s.get("token_hash") == except_token_hash:
                continue
            if not s.get("revoked"):
                s["revoked"] = True
                count += 1
        if count:
            _save(SESSIONS_FILE, "sessions", sessions)
        return count


# ── Principals (D-04) ──


@dataclass(frozen=True)
class Principal:
    """A resolved caller identity. `kind` is one of anonymous/user/connector/service."""

    kind: str
    username: str | None = None
    is_admin: bool = False
    bound_project: str | None = None
    credential_id: str | None = None
    session_hash: str | None = None


def resolve_session_principal(token: str, *, now: int | None = None) -> Principal | None:
    """Resolve a session cookie value to a user Principal. None if the
    session is invalid/expired, or if the user it names no longer exists."""
    record = authenticate_session(token, now=now)
    if record is None:
        return None
    user = get_user(record.get("username", ""))
    if user is None:
        return None
    return Principal(
        kind="user",
        username=user["username"],
        is_admin=bool(user.get("is_admin")),
        session_hash=hashlib.sha256(token.encode()).hexdigest(),
    )


def resolve_connector_principal(token: str) -> Principal | None:
    """Resolve a `dgc_` connector token via connectors.authenticate_token --
    this is an auth check, not a liveness stamp, so it must never touch
    last_connection. None for a revoked/unknown token or a non-`dgc_`-prefixed
    string.
    """
    if not token or not token.startswith(connectors.TOKEN_PREFIX):
        return None
    record = connectors.authenticate_token(token)
    if record is None:
        return None
    bound_project = record.get("project") or "default-project"
    return Principal(
        kind="connector",
        bound_project=bound_project,
        credential_id=record.get("credential_id"),
    )


def resolve_service_principal(
    header_value: str | None, *, env: Mapping[str, str] | None = None
) -> Principal | None:
    """Resolve the internal service-token header to a service Principal.
    Fails closed: an unset or blank DG_SERVICE_TOKEN never authenticates
    anything, even against an empty header value."""
    expected = _env(env).get("DG_SERVICE_TOKEN", "") or ""
    if not expected.strip():
        return None
    if not header_value:
        return None
    if not hmac.compare_digest(header_value, expected):
        return None
    return Principal(kind="service")


def deployment_profile(env: Mapping[str, str] | None = None) -> str:
    """Read DG_DEPLOYMENT (D-07/D-19). Defaults to 'local'; raises ValueError
    for any value outside DEPLOYMENT_PROFILES."""
    value = _env(env).get("DG_DEPLOYMENT", "local")
    if value not in DEPLOYMENT_PROFILES:
        raise ValueError(f"unknown deployment profile: {value!r}")
    return value


# ── Memberships (D-02) ──


def set_membership(username: str, project: str, role: str) -> dict[str, Any]:
    """Upsert one membership row for (username, project). Raises ValueError
    for a role outside ROLES."""
    if role not in ROLES:
        raise ValueError(f"invalid role: {role!r}")
    normalized = username.strip().lower()
    with _STORE_LOCK:
        rows = _load(MEMBERSHIPS_FILE, "memberships")
        record: dict[str, Any] | None = None
        for r in rows:
            if r.get("username") == normalized and r.get("project") == project:
                r["role"] = role
                r["granted_at"] = int(time.time())
                record = r
                break
        if record is None:
            record = {
                "username": normalized,
                "project": project,
                "role": role,
                "granted_at": int(time.time()),
            }
            rows.append(record)
        _save(MEMBERSHIPS_FILE, "memberships", rows)
        return dict(record)


def get_role(username: str, project: str) -> str | None:
    """Return the stored role for (username, project), or None."""
    normalized = username.strip().lower()
    with _STORE_LOCK:
        for r in _load(MEMBERSHIPS_FILE, "memberships"):
            if r.get("username") == normalized and r.get("project") == project:
                return r.get("role")
    return None


def remove_membership(username: str, project: str) -> bool:
    """Remove the membership row for (username, project). Returns False if
    the pair was not a member."""
    normalized = username.strip().lower()
    with _STORE_LOCK:
        rows = _load(MEMBERSHIPS_FILE, "memberships")
        new_rows = [
            r
            for r in rows
            if not (r.get("username") == normalized and r.get("project") == project)
        ]
        if len(new_rows) == len(rows):
            return False
        _save(MEMBERSHIPS_FILE, "memberships", new_rows)
        return True


def list_memberships(username: str) -> list[dict[str, Any]]:
    """Return [{project, role}] for every project this user is a member of."""
    normalized = username.strip().lower()
    with _STORE_LOCK:
        rows = _load(MEMBERSHIPS_FILE, "memberships")
    return [
        {"project": r["project"], "role": r["role"]}
        for r in rows
        if r.get("username") == normalized
    ]


def list_members(project: str) -> list[dict[str, Any]]:
    """Return [{username, role}] for every member of `project`."""
    with _STORE_LOCK:
        rows = _load(MEMBERSHIPS_FILE, "memberships")
    return [
        {"username": r["username"], "role": r["role"]}
        for r in rows
        if r.get("project") == project
    ]


def list_member_projects(username: str) -> list[str]:
    """Return the sorted list of project names this user is a member of."""
    return sorted({m["project"] for m in list_memberships(username)})


def project_has_members(project: str) -> bool:
    """True if `project` has at least one membership row."""
    return len(list_members(project)) > 0


def count_owners(project: str) -> int:
    """Count members of `project` with role == owner."""
    return sum(1 for m in list_members(project) if m.get("role") == "owner")


def role_satisfies(role: str | None, min_role: str) -> bool:
    """True if `role` outranks or equals `min_role`. A None role never
    satisfies anything."""
    if role is None:
        return False
    return ROLE_RANK.get(role, -1) >= ROLE_RANK.get(min_role, len(ROLE_RANK))


def effective_role(principal: "Principal", project: str) -> str | None:
    """Return "owner" for an admin user principal, the stored role for a
    plain user principal, and None for every other principal kind (connector
    and service principals are authorized by route scope, not by role)."""
    if principal.kind == "user":
        if principal.is_admin:
            return "owner"
        return get_role(principal.username or "", project)
    return None


def create_project_if_unclaimed(
    project: str, owner_username: str, *, exists_in_graph: bool
) -> bool:
    """Atomically claim `project` for `owner_username` as owner, unless it
    already has members or already exists in the graph. Returns whether the
    claim succeeded."""
    with _STORE_LOCK:
        if project_has_members(project) or exists_in_graph:
            return False
        set_membership(owner_username, project, "owner")
        return True


# ── Invites (D-05) ──


def create_invite(
    username: str,
    project: str,
    role: str,
    *,
    created_by: str,
    now: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Mint a single-use invite code (dgi_ + 32 random bytes, 72h TTL). Only
    the SHA-256 hash of the code is persisted. Returns (raw_code, record)
    where record never carries the hash."""
    if role not in ROLES:
        raise ValueError(f"invalid role: {role!r}")
    current = _now(now)
    code = INVITE_CODE_PREFIX + secrets.token_urlsafe(32)
    record: dict[str, Any] = {
        "code_hash": hashlib.sha256(code.encode()).hexdigest(),
        "username": username.strip().lower(),
        "project": project,
        "role": role,
        "created_by": created_by,
        "created_at": current,
        "expires_at": current + INVITE_TTL_SECONDS,
        "used": False,
        "used_at": None,
    }
    with _STORE_LOCK:
        rows = _load(INVITES_FILE, "invites")
        rows.append(record)
        _save(INVITES_FILE, "invites", rows)
    public = dict(record)
    public.pop("code_hash", None)
    return code, public


def consume_invite(code: str, *, now: int | None = None) -> dict[str, Any] | None:
    """Mark an invite code used-once. Returns None for a second consume, an
    expired code (inclusive: now >= expires_at), or an unknown code."""
    if not code or not code.startswith(INVITE_CODE_PREFIX):
        return None
    digest = hashlib.sha256(code.encode()).hexdigest()
    current = _now(now)
    with _STORE_LOCK:
        rows = _load(INVITES_FILE, "invites")
        for r in rows:
            if r.get("code_hash") != digest:
                continue
            if r.get("used"):
                return None
            if current >= int(r.get("expires_at", 0)):
                return None
            r["used"] = True
            r["used_at"] = current
            _save(INVITES_FILE, "invites", rows)
            result = dict(r)
            result.pop("code_hash", None)
            return result
    return None


# ── Bootstrap admin (D-05) ──


def ensure_bootstrap_admin(
    env: Mapping[str, str], profile: str, logger: logging.Logger
) -> str:
    """Create the bootstrap admin from DG_BOOTSTRAP_ADMIN_USER/
    DG_BOOTSTRAP_ADMIN_PASSWORD when no admin exists yet. Never overwrites an
    existing admin. Returns "exists" | "created" | "missing-env" |
    "weak-password". A missing or too-short/invalid bootstrap secret raises
    RuntimeError in "multi-user" and logs a WARNING (creating nothing) in
    "local". Never logs the username above INFO or the password at any
    level."""
    if profile not in DEPLOYMENT_PROFILES:
        raise ValueError(f"unknown deployment profile: {profile!r}")

    with _STORE_LOCK:
        users = _load(USERS_FILE, "users")
        if any(u.get("is_admin") for u in users):
            return "exists"

        username = env.get("DG_BOOTSTRAP_ADMIN_USER")
        password = env.get("DG_BOOTSTRAP_ADMIN_PASSWORD")

        if not username or not password:
            message = (
                "DG_BOOTSTRAP_ADMIN_USER/DG_BOOTSTRAP_ADMIN_PASSWORD not set; "
                "no bootstrap admin created"
            )
            if profile == "multi-user":
                raise RuntimeError(message)
            logger.warning(message)
            return "missing-env"

        try:
            validate_password_policy(password)
        except ValueError:
            message = (
                "DG_BOOTSTRAP_ADMIN_PASSWORD does not meet the password policy; "
                "no bootstrap admin created"
            )
            if profile == "multi-user":
                raise RuntimeError(message)
            logger.warning(message)
            return "weak-password"

        create_user(username, password, is_admin=True)
        return "created"
