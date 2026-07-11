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
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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

TOKEN_PREFIX = "dgc_"
STALE_THRESHOLD_DAYS = 7


# ── Pydantic Models ──


class CredentialCreatePayload(BaseModel):
    """Request body for POST /connectors/{connector_id}/credentials."""

    label: str | None = None


class CredentialCreatedResponse(BaseModel):
    """Response for credential creation — the ONLY time the token is visible."""

    credential_id: str
    token: str


class HeartbeatResponse(BaseModel):
    """Response for POST /connectors/heartbeat."""

    connector_id: str
    status: str


# ── Persistence (mirrors llm_gateway settings persistence) ──

DATA_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
CREDENTIALS_FILE = DATA_DIR / "connector-credentials.json"


def load_credentials() -> list[dict[str, Any]]:
    """Read the credential list from the JSON store.

    Returns an empty list if the file is missing, malformed, or empty.
    """
    if not CREDENTIALS_FILE.exists():
        return []
    try:
        payload = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    credentials = payload.get("credentials")
    if not isinstance(credentials, list):
        return []
    return [c for c in credentials if isinstance(c, dict)]


def save_credentials(credentials: list[dict[str, Any]]) -> None:
    """Write the credential list to the JSON store. Creates parent dir if needed."""
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(
        json.dumps({"credentials": credentials}, indent=2),
        encoding="utf-8",
    )


# ── Token Utilities ──


def generate_token() -> str:
    """Mint a new connector token: dgc_ + 32 bytes of url-safe randomness."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a token. Only the hash is ever persisted."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Credential Lifecycle ──


def create_credential(connector_id: str, label: str | None = None) -> tuple[dict[str, Any], str]:
    """Create and persist a credential for a connector.

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
        "token_hash": hash_token(token),
        "created_at": _utc_now_iso(),
        "revoked": False,
        "last_connection": None,
    }
    credentials = load_credentials()
    credentials.append(record)
    save_credentials(credentials)
    return record, token


def revoke_credential(connector_id: str, credential_id: str) -> bool:
    """Mark a credential as revoked. Returns True if found and revoked.

    Revoked credentials stop authenticating heartbeats immediately (CONNB-01).
    """
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
    for record in load_credentials():
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
    credentials = load_credentials()
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


def get_connector_overview(now: datetime | None = None) -> list[dict[str, Any]]:
    """Registry joined with per-connector status, last-connection date, and
    credential summaries. Never exposes tokens or token hashes (CONNB-01, CONNB-04).
    """
    credentials = load_credentials()
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
