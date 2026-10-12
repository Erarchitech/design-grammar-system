"""Connector registry, session-based overview, and legacy credential cleanup.

The JSON credential store remains only for revoking tokens issued before the
account sign-in transition; it cannot mint or authenticate a connector token.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import connector_session
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

STALE_THRESHOLD_DAYS = 7


# ── Pydantic Models ──


class CredentialCreatePayload(BaseModel):
    """Legacy request body accepted by the retired creation route (410)."""

    label: str | None = None
    # Retained so old request bodies still reach the 410 tombstone; neither
    # field can cause a credential to be created.
    project: str | None = None


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

    A corrupt file must fail closed, not be treated as an empty list: cleanup
    must not overwrite or silently omit legacy credentials.
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


# ── Cleanup-only credential lifecycle ──


def revoke_credential(connector_id: str, credential_id: str) -> bool:
    """Mark a legacy credential as revoked for cleanup. Returns True if found."""
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


# ── Status Derivation ──


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


def get_connector_overview(
    now: datetime | None = None, *, projects: set[str] | None = None
) -> list[dict[str, Any]]:
    """Registry joined with sign-in session status for the caller's visible projects.

    `projects` limits status and the last sign-in to visible projects; None
    means every project (admin). Legacy credentials are cleanup-only and do
    not affect status or appear in the overview.
    """
    current = int(now.timestamp()) if now is not None else None
    overview: list[dict[str, Any]] = []
    for connector in CONNECTOR_REGISTRY:
        session_status = connector_session.status_for(
            connector["id"], projects=projects, now=current
        )
        overview.append(
            {
                "id": connector["id"],
                "name": connector["name"],
                "category": connector["category"],
                "status": session_status["status"],
                "last_connection": session_status["last_sign_in"],
                "active_sessions": session_status["active_sessions"],
            }
        )
    return overview
