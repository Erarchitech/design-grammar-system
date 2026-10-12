"""Connector credential backend — registry, token minting, persistence, status derivation.

Mirrors the llm_gateway settings-persistence style: JSON file under DATA_DIR,
small load/save helpers, module-level file path constant (patched in tests).

Security model: connector tokens (`dgc_` + secrets.token_urlsafe(32)) are
generated server-side and returned exactly once on creation. Only the SHA-256
hash of the token is persisted — hashing beats encryption here because we never
need the plaintext back (CONNB-02).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel


# ── Connector Registry (fixed data — Phase 812 contract) ──

CONNECTOR_CATEGORIES: list[str] = [
    "VPL Platforms",
    "BIM Authoring",
    "BIM Coordination",
    "BCF Trackers",
    "Visualization",
]

CONNECTOR_REGISTRY: list[dict[str, str]] = [
    {"id": "grasshopper", "name": "Grasshopper", "category": "VPL Platforms"},
    {"id": "dynamo", "name": "Dynamo", "category": "VPL Platforms"},
    {"id": "revit", "name": "Revit", "category": "BIM Authoring"},
    {"id": "blender", "name": "Blender", "category": "BIM Authoring"},
    {"id": "tekla", "name": "Tekla", "category": "BIM Authoring"},
    {"id": "archicad", "name": "Archicad", "category": "BIM Authoring"},
    {"id": "civil3d", "name": "Civil3D", "category": "BIM Authoring"},
    {"id": "infraworks", "name": "Infraworks", "category": "BIM Authoring"},
    {"id": "navisworks", "name": "Navisworks", "category": "BIM Coordination"},
    {"id": "solibri", "name": "Solibri", "category": "BIM Coordination"},
    {"id": "bimcollab", "name": "BIMCollab", "category": "BCF Trackers"},
    {"id": "bimtrack", "name": "BIMTrack", "category": "BCF Trackers"},
    {"id": "lumion", "name": "Lumion", "category": "Visualization"},
    {"id": "twinmotion", "name": "Twinmotion", "category": "Visualization"},
]

CONNECTOR_IDS: set[str] = {c["id"] for c in CONNECTOR_REGISTRY}


def tokens_retired(status_code: int = 410) -> HTTPException:
    """The structured error of the retired connector-token creation route
    (Phase 1308, D-31): 410 for ``POST /connectors/{id}/credentials``. Built
    here, not through ``auth.auth_error``, because ``auth`` imports this module
    (same ``{error, hint, code}`` detail shape)."""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": "Connector tokens are retired.",
            "hint": "Sign in from the connector with your DG account (POST /auth/connector-session).",
            "code": "CONNECTOR_TOKENS_RETIRED",
        },
    )

TOKEN_PREFIX = "dgc_"
STALE_THRESHOLD_DAYS = 7


# ── Pydantic Models ──


class CredentialCreatePayload(BaseModel):
    """Request body for POST /connectors/{connector_id}/credentials."""

    label: str | None = None
    # Phase 825 (CONNG-03): the token is project-scoped. The project bound here
    # is what the heartbeat echoes back so the CONNECTOR component no longer needs
    # a Project input. Missing → server defaults to "default-project".
    project: str | None = None


class CredentialCreatedResponse(BaseModel):
    """Response for credential creation — the ONLY time the token is visible."""

    credential_id: str
    token: str


class Neo4jBundle(BaseModel):
    """Neo4j connection bundle returned by the heartbeat (Phase 825, CONNG-03).

    Derived from data-service env. `uri` is the HOST-facing bolt URI
    (NEO4J_PUBLIC_URI) so an off-Docker connector (e.g. Grasshopper on the host)
    can reach Neo4j — never the Docker-internal bolt://neo4j:7687.
    """

    uri: str
    user: str
    password: str
    database: str


class HeartbeatResponse(BaseModel):
    """Response for POST /connectors/heartbeat."""

    connector_id: str
    status: str
    # Phase 825: project scope + connection bundle unlocked by a valid token.
    # Optional so pre-825 clients that ignore them keep working.
    project: str | None = None
    neo4j: Neo4jBundle | None = None


# ── Persistence (mirrors llm_gateway settings persistence) ──

DATA_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
CREDENTIALS_FILE = DATA_DIR / "connector-credentials.json"


class CredentialStoreError(RuntimeError):
    """The credential store exists but cannot be read as a credential list.

    WR-03 (1205 review): a corrupt file is an ERROR, never an empty list --
    treating it as empty would let the next mint overwrite (and so wipe) every
    existing credential, and would silently un-revoke nothing but also
    authenticate nothing.
    """


# Serialises every read-modify-write on the credential file (routes are sync
# `def`, so they run concurrently on the threadpool). Single process, so an
# in-process lock is sufficient -- same model as auth._STORE_LOCK.
_STORE_LOCK = threading.RLock()


def load_credentials() -> list[dict[str, Any]]:
    """Read the credential list from the JSON store.

    Returns an empty list only when the file does not exist yet. Raises
    CredentialStoreError when it exists but is unreadable, empty, or not a
    credential document.
    """
    with _STORE_LOCK:
        if not CREDENTIALS_FILE.exists():
            return []
        try:
            payload = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CredentialStoreError(
                f"connector credential store {CREDENTIALS_FILE.name} is unreadable: {type(exc).__name__}"
            ) from exc
        if not isinstance(payload, dict):
            raise CredentialStoreError(
                f"connector credential store {CREDENTIALS_FILE.name} is not a JSON object"
            )
        if "credentials" not in payload:
            return []
        credentials = payload["credentials"]
        if not isinstance(credentials, list):
            raise CredentialStoreError(
                f"connector credential store {CREDENTIALS_FILE.name} has a malformed credentials list"
            )
        return [c for c in credentials if isinstance(c, dict)]


def save_credentials(credentials: list[dict[str, Any]]) -> None:
    """Write the credential list to the JSON store atomically (temp file +
    os.replace, owner-only permissions). Creates the parent dir if needed."""
    with _STORE_LOCK:
        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = CREDENTIALS_FILE.parent / f".{CREDENTIALS_FILE.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        try:
            tmp_path.write_text(json.dumps({"credentials": credentials}, indent=2), encoding="utf-8")
            try:
                os.chmod(tmp_path, 0o600)
            except OSError:
                pass  # best effort (e.g. Windows bind mounts)
            os.replace(tmp_path, CREDENTIALS_FILE)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass


# ── Token Utilities ──


def generate_token() -> str:
    """Mint a new connector token: dgc_ + 32 bytes of url-safe randomness."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a token. Only the hash is ever persisted."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Credential Lifecycle ──


def create_credential(
    connector_id: str,
    label: str | None = None,
    project: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Create and persist a credential for a connector.

    Args:
        project: Project this token is scoped to (Phase 825, CONNG-03). Persisted
            on the record and echoed by the heartbeat; defaults to
            "default-project" when not supplied.

    Returns:
        Tuple of (persisted credential record, plaintext token). The plaintext
        token is returned once here and never stored.

    Raises:
        ValueError: If connector_id is not in the registry.
    """
    if connector_id not in CONNECTOR_IDS:
        raise ValueError(f"Unknown connector: {connector_id}")

    token = generate_token()
    record: dict[str, Any] = {
        "credential_id": uuid.uuid4().hex,
        "connector_id": connector_id,
        "label": label or "",
        "project": project or "default-project",
        "token_hash": hash_token(token),
        "created_at": _utc_now_iso(),
        "revoked": False,
        "last_connection": None,
    }
    with _STORE_LOCK:
        credentials = load_credentials()
        credentials.append(record)
        save_credentials(credentials)
    return record, token


def revoke_credential(connector_id: str, credential_id: str) -> bool:
    """Mark a credential as revoked. Returns True if found and revoked.

    Revoked credentials stop authenticating heartbeats immediately (CONNB-01).
    """
    with _STORE_LOCK:
        credentials = load_credentials()
        changed = False
        for record in credentials:
            if (
                record.get("connector_id") == connector_id
                and record.get("credential_id") == credential_id
            ):
                record["revoked"] = True
                changed = True
        if changed:
            save_credentials(credentials)
        return changed


def authenticate_token(token: str) -> dict[str, Any] | None:
    """Match a plaintext token against non-revoked credentials by hash.

    Returns the credential record or None if unknown/revoked.
    """
    if not token:
        return None
    digest = hash_token(token)
    try:
        credentials = load_credentials()
    except CredentialStoreError:
        logging.getLogger(__name__).exception("connector credential store unreadable; refusing token")
        return None  # fail closed: an unreadable store authenticates nobody
    for record in credentials:
        if record.get("token_hash") == digest and not record.get("revoked"):
            return record
    return None


def record_heartbeat(token: str) -> dict[str, Any] | None:
    """Authenticate a token and stamp last_connection on its credential.

    Returns the updated credential record, or None if the token is
    unknown or revoked (caller maps this to 401).
    """
    if not token:
        return None
    digest = hash_token(token)
    # Read-modify-write under the lock so a heartbeat can never write back a
    # stale list over a concurrent revoke (WR-03).
    with _STORE_LOCK:
        try:
            credentials = load_credentials()
        except CredentialStoreError:
            logging.getLogger(__name__).exception("connector credential store unreadable; refusing token")
            return None
        for record in credentials:
            if record.get("token_hash") == digest and not record.get("revoked"):
                record["last_connection"] = _utc_now_iso()
                save_credentials(credentials)
                return record
    return None


# ── Status Derivation ──


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_status(last_connection: str | None, now: datetime | None = None) -> str:
    """Derive connector status from its most recent successful heartbeat.

    never_connected — no successful heartbeat ever
    active          — last connection <= STALE_THRESHOLD_DAYS days ago
    stale           — older than the threshold (or unparseable timestamp)
    """
    if not last_connection:
        return "never_connected"
    try:
        last = datetime.fromisoformat(last_connection)
    except ValueError:
        return "stale"
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current - last <= timedelta(days=STALE_THRESHOLD_DAYS):
        return "active"
    return "stale"


def connector_last_connection(
    connector_id: str,
    credentials: list[dict[str, Any]] | None = None,
) -> str | None:
    """Most recent last_connection across a connector's credentials (incl. revoked —
    a past successful connection still happened)."""
    if credentials is None:
        credentials = load_credentials()
    timestamps = [
        record["last_connection"]
        for record in credentials
        if record.get("connector_id") == connector_id and record.get("last_connection")
    ]
    return max(timestamps) if timestamps else None


def get_connector_overview(
    now: datetime | None = None, *, projects: set[str] | None = None
) -> list[dict[str, Any]]:
    """Registry joined with per-connector status, last-connection date, and
    credential summaries. Never exposes tokens or token hashes (CONNB-01, CONNB-04).

    `projects` (Phase 1205, T-1205-10-06): when given, credentials whose bound
    project is outside the set are dropped BEFORE status and last-connection
    are derived, so no cross-project activity leaks. None means all (admin).
    Records without a project read as "default-project".
    """
    credentials = load_credentials()
    if projects is not None:
        credentials = [
            record
            for record in credentials
            if (record.get("project") or "default-project") in projects
        ]
    overview: list[dict[str, Any]] = []
    for connector in CONNECTOR_REGISTRY:
        last_connection = connector_last_connection(connector["id"], credentials)
        summaries = [
            {
                "credential_id": record.get("credential_id"),
                "label": record.get("label", ""),
                "created_at": record.get("created_at"),
                "revoked": bool(record.get("revoked")),
            }
            for record in credentials
            if record.get("connector_id") == connector["id"]
        ]
        overview.append(
            {
                "id": connector["id"],
                "name": connector["name"],
                "category": connector["category"],
                "status": derive_status(last_connection, now),
                "last_connection": last_connection,
                "credentials": summaries,
            }
        )
    return overview
