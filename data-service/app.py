from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Any
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase
from neo4j.graph import Node, Path, Relationship
from pydantic import BaseModel, Field

from speckle_validation import (
    SpeckleConnectionSettings,
    SpeckleValidationError,
    build_client,
    delete_validation_version,
    get_latest_model_version_id,
    get_or_create_validation_model_id,
    normalize_url,
    publish_validation_version,
)

from llm_gateway import (
    LLMSettingsPayload,
    LLMSettingsResponse,
    GenerateRequest,
    GenerateResponse,
    TestConnectionPayload,
    TestResult,
    get_adapter,
    load_persisted_llm_settings,
    save_persisted_llm_settings,
    get_llm_settings_response,
    resolve_active_provider,
    list_models_for_provider,
    map_provider_error,
    mask_key,
    encrypt_value,
    decrypt_value,
    init_ollama_models,
    SEED_MODELS,
    LLM_SETTINGS_FILE,
)

import connectors
from connectors import (
    CredentialCreatePayload,
    CredentialCreatedResponse,
    HeartbeatResponse,
)

import auth
import auth_routes
import route_policy
import secrets_policy

import reasoner
import dg_context
import cg_recognition
import dg_identity
from dg_identity import MintRequest, BindRepresentationRequest, SharedPropertyWriteRequest
import gh_bridge
import computgraph_publish
import cg_structure_checks
import cg_input_bindings
import cg_input_generation
import cg_paramstate_store
import dsav_watcher
import evidence_contract
import design_state_projection
import canonical_json


# Phase 39 (DSAV-02): the first startup hook in this file to use `lifespan`.
# There was no `lifespan` and no `threading` usage in data-service before this
# phase; `ensure_spec_indexes` was registered with the startup-event decorator
# deprecated in FastAPI 0.93.
#
# Those two mechanisms are mutually exclusive, not additive: Starlette only runs
# the `on_startup` handlers through the DEFAULT lifespan it installs when no
# `lifespan=` is passed. Supplying one replaces that default outright, and any
# startup-event handler is then registered but silently never invoked. So
# `ensure_spec_indexes` is called here explicitly and its decorator was removed
# -- keeping the decorator would have quietly disabled the SpecGraph index
# bootstrap and `init_ollama_models()` at startup.
#
# The watcher thread is `daemon=True` purely as a container-kill safety net;
# the stop event plus the bounded `join` in `stop_watcher()` is what actually
# makes it deterministically stoppable.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Phase 1205 (D-05/D-07/D-11/D-19): profile validation, the known-default
    # secret refusal, and the bootstrap admin all run first and let their
    # exceptions propagate -- unlike the watcher below, a refused start here
    # must be a failed start, not a degraded one.
    _profile = auth.deployment_profile()
    secrets_policy.enforce_startup_secrets(os.environ, _profile, logging.getLogger(__name__))
    auth.ensure_bootstrap_admin(os.environ, _profile, logging.getLogger(__name__))

    # Late module-global lookups on purpose: `ensure_spec_indexes`,
    # `_call_shacl_validate` and `_auto_publish_run` are all defined further
    # down this module, and this body runs at startup, long after import.
    ensure_spec_indexes()
    try:
        dsav_watcher.start_watcher(
            shacl_fn=_call_shacl_validate,
            publish_fn=_auto_publish_run,
        )
    except Exception:
        # T-39-08: a watcher that cannot start must never prevent the service
        # from serving. Auto-validation is an opt-in background feature; the
        # rest of data-service does not depend on it.
        logging.getLogger(__name__).exception(
            "dsav_watcher: start_watcher failed; continuing without auto-validation"
        )

    yield

    try:
        dsav_watcher.stop_watcher(timeout=5.0)
    except Exception:
        logging.getLogger(__name__).exception("dsav_watcher: stop_watcher failed during shutdown")


# Phase 1205 (D-07/D-19): docs exposure is gated by the import-time deployment
# profile, read directly from the environment (not through auth.deployment_profile,
# which raises on an unknown value -- an import-time crash on an unrelated typo
# would be worse than fail-closed docs). Anything other than exactly "local"
# disables /docs, /redoc and /openapi.json (fail closed).
_DOCS_PROFILE = os.getenv("DG_DEPLOYMENT", "local")
_DOCS_ENABLED = _DOCS_PROFILE == "local"

app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)
app.include_router(auth_routes.router)

# Phase 1205 (D-03): every data-service route below is registered on this one
# router, whose dependency runs the deny-by-default auth.require_principal.
# The router is included as the LAST statement of this module, after every
# route definition (a route added to `app` directly would bypass the guard;
# tests/test_route_inventory.py fails the suite if any route lacks it).
router = APIRouter(dependencies=[Depends(auth.require_principal)])

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# Phase 825 (CONNG-03): host-facing bolt URI + database returned in the connector
# heartbeat bundle. NEO4J_URI above is the Docker-internal address used by
# data-service itself; an off-Docker connector (Grasshopper on the host) needs the
# host-facing URI instead — hence a separate env, defaulting to localhost.
NEO4J_PUBLIC_URI = os.getenv("NEO4J_PUBLIC_URI", "bolt://localhost:7687")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# dg-reasoner sidecar (Plan 821-01 compose env; internal-only, D-12) --
# reached exclusively through the thin proxy route below (D-06).
DG_REASONER_URL = os.getenv("DG_REASONER_URL", "http://dg-reasoner:8000")

# SHACL sidecar proxy timeout (Phase 823 Plan 03, D-02) -- short by design so a
# slow/hung sidecar degrades the publish hot path to a status dict instead of
# hanging it; unlike DG_REASONER_TIMEOUT_SECONDS this call is a non-fatal sidecar.
DG_SHACL_HTTP_TIMEOUT_SECONDS = float(os.getenv("DG_SHACL_HTTP_TIMEOUT_SECONDS", "15"))

# Phase 39 (DSAV-02, T-39-07): UTF-8 byte cap on the caller-supplied
# statePayloadJson accepted by POST /designstate/capture. A capture writes an
# unbounded caller-controlled string straight into ValidGraph, so the only
# thing standing between an authenticated connector and an arbitrarily large
# Neo4j property is this cap. 1 MiB comfortably fits a real DesignState v2
# envelope.
DSAV_MAX_STATE_PAYLOAD_BYTES = int(os.getenv("DSAV_MAX_STATE_PAYLOAD_BYTES", "1048576"))

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

EXECUTION_RESULTS: dict[str, dict[str, Any]] = {}

# Phase 1205 (T-1205-10-03): the per-execution owner record. The n8n relay
# (plan 1205-14) records who started each execution; GET /execution-result/{id}
# then answers only that user. The former global "latest per workflow" slot
# (last-write-wins across all callers) no longer exists.
EXECUTION_OWNERS: dict[str, dict[str, Any]] = {}
_EXECUTION_OWNERS_LOCK = threading.Lock()
EXECUTION_OWNERS_CAP = 1000


def record_execution_owner(
    execution_id: str, username: str, project: str | None, workflow: str | None
) -> None:
    """Bind `execution_id` to the user who started it. Oldest entries are
    evicted once the map holds EXECUTION_OWNERS_CAP records."""
    if not execution_id or not username:
        return
    with _EXECUTION_OWNERS_LOCK:
        EXECUTION_OWNERS.pop(execution_id, None)
        EXECUTION_OWNERS[execution_id] = {
            "username": username,
            "project": project,
            "workflow": workflow,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        while len(EXECUTION_OWNERS) > EXECUTION_OWNERS_CAP:
            EXECUTION_OWNERS.pop(next(iter(EXECUTION_OWNERS)))
VALIDATION_GRAPH = "ValidGraph"
SPEC_GRAPH = "SpecGraph"
# Phase 1200 (D-06): the serviceVersion this data-service instance stamps into every
# evidence envelope it emits. Bump when this file's publish-path evidence-producing
# behavior changes meaningfully, independent of EVIDENCE_CONTRACT_VERSION (which
# versions the envelope shape/vocabulary itself, not this producer).
EVIDENCE_SERVICE_VERSION = "1.0.0"
DATA_DIR = FilePath(os.getenv("DG_DATA_DIR", "/app/data"))
SPECKLE_SETTINGS_FILE = DATA_DIR / "speckle-settings.json"
KNOWLEDGE_REPO_ROOT = FilePath(os.getenv("DG_KNOWLEDGE_REPO_ROOT", "/mnt/repo"))

N8N_INTERNAL_URL = os.getenv("N8N_INTERNAL_URL", "http://n8n:5678")


def word_diff_html(original: str, proposed: str) -> str:
    """Word-level diff as HTML with <span class='diff-del'> and <span class='diff-ins'> markers."""
    import difflib
    import html as html_mod
    original_words = original.split()
    proposed_words = proposed.split()
    matcher = difflib.SequenceMatcher(None, original_words, proposed_words, autojunk=False)
    parts: list[str] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            parts.extend(html_mod.escape(w) for w in original_words[i1:i2])
        elif op == "replace":
            for w in original_words[i1:i2]:
                parts.append(f'<span class="diff-del">{html_mod.escape(w)}</span>')
            for w in proposed_words[j1:j2]:
                parts.append(f'<span class="diff-ins">{html_mod.escape(w)}</span>')
        elif op == "delete":
            for w in original_words[i1:i2]:
                parts.append(f'<span class="diff-del">{html_mod.escape(w)}</span>')
        elif op == "insert":
            for w in proposed_words[j1:j2]:
                parts.append(f'<span class="diff-ins">{html_mod.escape(w)}</span>')
    return " ".join(parts)


def fire_n8n_webhook(webhook_path: str, body: dict, timeout: int = 15) -> str:
    """POST `body` to the internal n8n webhook and return the ack executionId.

    Phase 1205 (D-04/D-08): every data-service -> n8n request carries the
    service token in X-DG-Service-Token (checked by the workflows' Verify Relay
    Token node). With DG_SERVICE_TOKEN unset the call fails closed with
    RELAY_UNAVAILABLE before any network request; an ack without an
    executionId is RELAY_NO_EXECUTION_ID (there is no latest-slot fallback).
    """
    token = (os.getenv("DG_SERVICE_TOKEN") or "").strip()
    if not token:
        raise _structured_error_response(
            "The workflow relay is not configured.",
            "Set DG_SERVICE_TOKEN for the data-service and n8n containers.",
            "RELAY_UNAVAILABLE",
            503,
        )
    req = urllib.request.Request(
        f"{N8N_INTERNAL_URL}/webhook/{webhook_path}",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            auth.SERVICE_TOKEN_HEADER: token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        raise _structured_error_response(
            "The workflow engine could not be reached.",
            "Check that the n8n service is running and retry.",
            "RELAY_UNAVAILABLE",
            503,
        )
    try:
        ack = json.loads(raw)
    except (ValueError, TypeError):
        ack = None
    execution_id = ack.get("executionId") if isinstance(ack, dict) else None
    if not execution_id or not isinstance(execution_id, (str, int)):
        raise _structured_error_response(
            "The workflow engine did not return an execution id.",
            "Check that the n8n workflow responds immediately with its executionId.",
            "RELAY_NO_EXECUTION_ID",
            502,
        )
    return str(execution_id)


def call_n8n_sync(webhook_path: str, body: dict, timeout: int = 120) -> dict:
    """Fire n8n webhook, poll EXECUTION_RESULTS until completed or timeout."""
    execution_id = fire_n8n_webhook(webhook_path, body)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        entry = EXECUTION_RESULTS.get(execution_id, {})
        if entry.get("status") == "completed":
            return entry.get("payload", {})
        if entry.get("status") == "failed":
            raise HTTPException(status_code=502, detail="LLM workflow failed")
        time.sleep(1.5)
    raise HTTPException(status_code=504, detail="LLM workflow timed out")


class ExecutionResult(BaseModel):
    executionId: str
    status: str
    payload: dict | None = None
    workflow: str | None = None
    step: int | None = None
    progress: float | None = None
    message: str | None = None


class SpeckleProjectConfigPayload(BaseModel):
    speckleProjectId: str = Field(default="")
    baseModelId: str = Field(default="")
    baseModelName: str | None = None
    validationModelId: str | None = None


class SpeckleSettingsPayload(BaseModel):
    baseUrl: str | None = None
    writeToken: str | None = None
    readToken: str | None = None


class ValidationPublishRulePayload(BaseModel):
    ruleId: str
    ruleName: str = ""
    ruleDescription: str = ""


class ValidationPublishRuleResultPayload(BaseModel):
    ruleId: str
    passed: bool
    failedEntityIds: list[str] = Field(default_factory=list)
    passedEntityIds: list[str] = Field(default_factory=list)


class ValidationGeometryItemPayload(BaseModel):
    kind: str
    vertices: list[float] = Field(default_factory=list)
    faces: list[list[int]] = Field(default_factory=list)
    colors: list[int] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)


class ValidationGeometryPayload(BaseModel):
    units: str = "m"
    items: list[ValidationGeometryItemPayload] = Field(default_factory=list)


class ValidationPublishEntityPayload(BaseModel):
    dgEntityId: str
    displayName: str | None = None
    geometry: ValidationGeometryPayload | None = None
    ruleIds: list[str] = Field(default_factory=list)
    failedRuleIds: list[str] = Field(default_factory=list)
    passedRuleIds: list[str] = Field(default_factory=list)
    overallStatus: str = "unknown"
    # Phase 1201 (D-03 additive / D-04): {ruleId: canonical status wire name} for
    # producers that already know the typed outcome. The legacy
    # failedRuleIds/passedRuleIds lists cannot express no_population, unsupported,
    # not_evaluated or indeterminate, so a producer that has one had no way to say
    # so and the row degraded to `unknown`. Absent or unparseable entries keep the
    # pre-1201 behavior exactly; this never infers a canonical status from a legacy
    # boolean, it only stops discarding one the producer supplied.
    canonicalStatuses: dict[str, str] | None = None


class ValidationPublishRequest(BaseModel):
    project: str
    # statePayloadJson carries the captured DesignState snapshot as JSON. v4.0
    # ParamState payloads use DS_-prefixed stateId values (unchanged from v2.0);
    # OS_-prefixed ObjState references join this payload from Phase 11
    # onward (see CLAUDE.md Graph Schema v4 / DesignState kind vocabulary).
    statePayloadJson: str | None = None
    # validStatus carries per-ObjState Boolean list from Phase 18 GHVL-05.
    # Index-matched to DesignState.ObjStates order. None for pre-v7.0 clients.
    validStatus: list[bool] | None = None
    rules: list[ValidationPublishRulePayload] = Field(default_factory=list)
    ruleResults: list[ValidationPublishRuleResultPayload] = Field(default_factory=list)
    entities: list[ValidationPublishEntityPayload] = Field(default_factory=list)


class DesignStateCaptureRequest(BaseModel):
    """Body of POST /designstate/capture (Phase 39, DSAV-02).

    A deliberate subset of ValidationPublishRequest: no rules, no entities, no
    validStatus -- a capture carries only the raw DesignState snapshot, and the
    verdict is derived later by the watcher from SHACL, never supplied by the
    caller. Unlike on the publish request, statePayloadJson is required and
    non-empty here: a capture with no state is meaningless.
    """

    project: str
    statePayloadJson: str = Field(min_length=1)


class DesignStateCaptureResponse(BaseModel):
    runId: str
    project: str
    status: str
    capturedAt: str


class FolderIngestRequest(BaseModel):
    project: str
    path: str  # relative path inside mount root (e.g. "DG_OBSIDIAN/knowledge")


class NoteUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class UpdateMatchRequest(BaseModel):
    prompt: str
    project: str


class UpdateProposeRequest(BaseModel):
    prompt: str
    project: str
    noteIds: list[str]


class NoteConfirmItem(BaseModel):
    noteId: str
    content: str
    updatedAt: str


class UpdateConfirmRequest(BaseModel):
    prompt: str
    project: str
    notes: list[NoteConfirmItem]


def normalize_value(value: Any):
    if isinstance(value, Node):
        node_id = getattr(value, "id", None) or getattr(value, "element_id", None)
        return {
            "_type": "node",
            "id": node_id,
            "labels": list(value.labels),
            "properties": dict(value),
        }
    if isinstance(value, Relationship):
        rel_id = getattr(value, "id", None) or getattr(value, "element_id", None)
        start_id = getattr(value.start_node, "id", None) or getattr(value.start_node, "element_id", None)
        end_id = getattr(value.end_node, "id", None) or getattr(value.end_node, "element_id", None)
        return {
            "_type": "relationship",
            "id": rel_id,
            "type": value.type,
            "start": start_id,
            "end": end_id,
            "properties": dict(value),
        }
    if isinstance(value, Path):
        return {
            "_type": "path",
            "nodes": [normalize_value(node) for node in value.nodes],
            "relationships": [normalize_value(rel) for rel in value.relationships],
        }
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_value(item) for key, item in value.items()}
    return value


def is_write_query(cypher: str) -> bool:
    return re.search(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b", cypher, re.IGNORECASE) is not None


def read_single(query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with driver.session() as session:
        record = session.run(query, parameters or {}).single()
    return None if record is None else record.data()


def read_many(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


def write_query(query: str, parameters: dict[str, Any] | None = None) -> None:
    with driver.session() as session:
        session.run(query, parameters or {}).consume()


def get_speckle_settings() -> SpeckleConnectionSettings:
    persisted = load_persisted_speckle_settings()
    base_url = os.getenv("SPECKLE_BASE_URL", "").strip() or persisted.get("baseUrl") or "http://localhost:8090"
    internal_url = os.getenv("SPECKLE_INTERNAL_URL", "").strip() or base_url
    write_token = os.getenv("SPECKLE_WRITE_TOKEN", "").strip() or persisted.get("writeToken", "")
    read_token = os.getenv("SPECKLE_READ_TOKEN", "").strip() or persisted.get("readToken", "") or write_token
    dg_base_url = os.getenv("DG_BASE_URL", "http://localhost:8080").strip()
    return SpeckleConnectionSettings(
        base_url=normalize_url(base_url),
        internal_url=normalize_url(internal_url),
        write_token=write_token,
        read_token=read_token,
        dg_base_url=normalize_url(dg_base_url),
    )


def load_persisted_speckle_settings() -> dict[str, str]:
    if not SPECKLE_SETTINGS_FILE.exists():
        return {}

    try:
        payload = json.loads(SPECKLE_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    settings: dict[str, str] = {}
    for key in ("baseUrl", "writeToken", "readToken"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            settings[key] = value.strip()
    return settings


def save_persisted_speckle_settings(settings: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in settings.items() if value}
    SPECKLE_SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def mask_token(token: str) -> str:
    normalized = (token or "").strip()
    if not normalized:
        return ""
    if len(normalized) <= 10:
        return normalized[0:2] + ("*" * max(0, len(normalized) - 4)) + normalized[-2:]
    return normalized[:6] + "..." + normalized[-6:]


def get_speckle_settings_response() -> dict[str, Any]:
    settings = get_speckle_settings()
    return {
        "baseUrl": settings.base_url,
        "writeTokenConfigured": bool(settings.write_token),
        "readTokenConfigured": bool(settings.read_token),
        "writeTokenPreview": mask_token(settings.write_token),
        "readTokenPreview": mask_token(settings.read_token),
    }


def normalize_speckle_project_id(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    if parsed.scheme and parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"projects", "streams"}:
            return parts[1]
    return normalized


def normalize_speckle_model_id(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    if parsed.scheme and parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 4 and parts[0] in {"projects", "streams"} and parts[2] in {"models", "branches"}:
            model_part = parts[3]
            return model_part.split("@", 1)[0]
    return normalized.split("@", 1)[0]


def normalize_speckle_project_config_payload(payload: SpeckleProjectConfigPayload) -> SpeckleProjectConfigPayload:
    return SpeckleProjectConfigPayload(
        speckleProjectId=normalize_speckle_project_id(payload.speckleProjectId),
        baseModelId=normalize_speckle_model_id(payload.baseModelId),
        baseModelName=(payload.baseModelName or "").strip() or None,
        validationModelId=normalize_speckle_model_id(payload.validationModelId),
    )


def get_integration_config(project: str) -> SpeckleProjectConfigPayload | None:
    row = read_single(
        """
        MATCH (cfg:IntegrationConfig {graph:$graph, provider:'Speckle', project:$project})
        RETURN
            cfg.speckleProjectId AS speckleProjectId,
            cfg.baseModelId AS baseModelId,
            cfg.baseModelName AS baseModelName,
            cfg.validationModelId AS validationModelId
        """,
        {"graph": VALIDATION_GRAPH, "project": project},
    )
    return None if row is None else normalize_speckle_project_config_payload(SpeckleProjectConfigPayload(**row))


def upsert_integration_config(project: str, payload: SpeckleProjectConfigPayload) -> SpeckleProjectConfigPayload:
    payload = normalize_speckle_project_config_payload(payload)
    write_query(
        """
        MERGE (cfg:IntegrationConfig {graph:$graph, provider:'Speckle', project:$project})
        SET
            cfg.speckleProjectId = $speckleProjectId,
            cfg.baseModelId = $baseModelId,
            cfg.baseModelName = $baseModelName,
            cfg.validationModelId = $validationModelId,
            cfg.updatedAt = $updatedAt
        """,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "speckleProjectId": payload.speckleProjectId,
            "baseModelId": payload.baseModelId,
            "baseModelName": payload.baseModelName,
            "validationModelId": payload.validationModelId,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    return get_integration_config(project) or payload


def store_validation_run(
    project: str,
    run_id: str,
    config: SpeckleProjectConfigPayload,
    publish_result: dict[str, str],
    rules_summary: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    state_payload_json: str | None = None,
    valid_status_param: list[bool] | None = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()

    # Use passed ValidStatus from the request if present (Phase 18 GHVL-05),
    # otherwise fall back to entity-based computation (backward compat for pre-v7.0 clients)
    if valid_status_param is not None:
        valid_status = valid_status_param
    else:
        valid_status = [
            len(entity.get("failedRuleIds") or []) == 0
            for entity in entities
        ]

    # D-15 (Phase 1202 plan 05, ALGN12-11): the MERGE key is (graph, project, runId), so
    # `ON CREATE SET` is what makes the immutability real, not merely declared -- it only
    # fires the first time this node is created, never on a re-publish of the same runId.
    #
    # Three-way classification (spec/DATABASE.md carries the same table):
    #   - Immutable, ON CREATE SET: rulesJson, statePayloadJson, createdAt. These describe
    #     *what was validated* and *when the run was created* -- the snapshot identity.
    #     A re-publish of the same runId must never change them.
    #   - Mutable operational, SET: status, ValidStatus, SendStatus. These describe *how
    #     the run is going* and legitimately change after creation -- the three other SET
    #     sites in this file (evidenceEnvelopeJson, shaclReportJson, the auto-complete
    #     SendStatus write) already mutate this same node independently after creation.
    #   - Mutable publish-output, SET: the eight Speckle/publish-result properties below.
    #     A re-publish genuinely produces a new Speckle version, so these are outputs of
    #     the publish operation, not properties of the validated snapshot -- pinning them
    #     under ON CREATE SET would leave the node pointing at a stale Speckle version
    #     after a legitimate re-publish, a worse failure than the one being fixed here.
    #
    # D-15 deliberately takes this write-once-clause-split over a physical
    # :StateSnapshot/:Run node split: no migration is introduced, and the split remains
    # available to a later phase if the requirement ever needs actual node separation.
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        ON CREATE SET
            run.rulesJson = $rulesJson,
            run.statePayloadJson = $statePayloadJson,
            run.createdAt = $createdAt
        SET
            run.speckleProjectId = $speckleProjectId,
            run.baseModelId = $baseModelId,
            run.baseVersionId = $baseVersionId,
            run.validationModelId = $validationModelId,
            run.validationVersionId = $validationVersionId,
            run.modelViewerUrl = $modelViewerUrl,
            run.baseResourceUrl = $baseResourceUrl,
            run.validationResourceUrl = $validationResourceUrl,
            run.status = 'completed',
            run.ValidStatus = $validStatus,
            run.SendStatus = true
        """,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "runId": run_id,
            "speckleProjectId": config.speckleProjectId,
            "baseModelId": config.baseModelId,
            "baseVersionId": publish_result["baseVersionId"],
            "validationModelId": publish_result["validationModelId"],
            "validationVersionId": publish_result["validationVersionId"],
            "modelViewerUrl": publish_result["modelViewerUrl"],
            "baseResourceUrl": publish_result["baseResourceUrl"],
            "validationResourceUrl": publish_result["validationResourceUrl"],
            "rulesJson": json.dumps(rules_summary),
            "statePayloadJson": state_payload_json,
            "validStatus": valid_status,
            "createdAt": created_at,
        },
    )

    entity_rows: list[dict[str, Any]] = []
    for entity in entities:
        display_name = entity.get("displayName")
        for rule_id in entity.get("failedRuleIds") or []:
            entity_rows.append(
                {
                    "ruleId": rule_id,
                    "dgEntityId": entity["dgEntityId"],
                    "displayName": display_name,
                    "status": "failed",
                }
            )
        for rule_id in entity.get("passedRuleIds") or []:
            if rule_id in entity.get("failedRuleIds", []):
                continue
            entity_rows.append(
                {
                    "ruleId": rule_id,
                    "dgEntityId": entity["dgEntityId"],
                    "displayName": display_name,
                    "status": "passed",
                }
            )

    if entity_rows:
        write_query(
            """
            MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
            UNWIND $entities AS entity
            MERGE (ve:ValidationEntity {
                graph:$graph,
                project:$project,
                runId:$runId,
                ruleId:entity.ruleId,
                dgEntityId:entity.dgEntityId
            })
            SET
                ve.displayName = entity.displayName,
                ve.status = entity.status
            MERGE (run)-[:HAS_ENTITY]->(ve)
            """,
            {
                "graph": VALIDATION_GRAPH,
                "project": project,
                "runId": run_id,
                "entities": entity_rows,
            },
        )


def get_validation_run(project: str, run_id: str | None = None) -> dict[str, Any] | None:
    query = """
        MATCH (run:ValidationRun {graph:$graph, project:$project})
        WHERE $runId IS NULL OR run.runId = $runId
        RETURN
            run.runId AS runId,
            run.speckleProjectId AS speckleProjectId,
            run.baseModelId AS baseModelId,
            run.baseVersionId AS baseVersionId,
            run.validationModelId AS validationModelId,
            run.validationVersionId AS validationVersionId,
            run.modelViewerUrl AS modelViewerUrl,
            run.baseResourceUrl AS baseResourceUrl,
            run.validationResourceUrl AS validationResourceUrl,
            run.rulesJson AS rulesJson,
            run.ValidStatus AS validStatus,
            run.SendStatus AS sendStatus,
            run.createdAt AS createdAt,
            run.shaclReportJson AS shaclReportJson,
            run.evidenceEnvelopeJson AS evidenceEnvelopeJson,
            run.statePayloadJson AS statePayloadJson
        ORDER BY run.createdAt DESC
        LIMIT 1
    """
    return read_single(query, {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id})


def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    """Return an HTTPException with a structured JSON detail body (error, hint, code)."""
    return HTTPException(
        status_code=status_code,
        detail={"error": error, "hint": hint, "code": code},
    )


def _format_prop_value(prop_value: Any) -> str:
    """Render a PropState propValue envelope as a compact display string.

    Accepts the {parameterId, displayName, type, value} shape produced by
    DesignStatePayloadV2Serializer. Returns "" for absent/malformed values —
    the UI renders an em dash in that case. Never raises.
    """
    if not isinstance(prop_value, dict):
        return ""
    value = prop_value.get("value")
    if value is None:
        return ""
    ptype = str(prop_value.get("type") or "").lower()
    if ptype == "boolean":
        return "Yes" if value else "No"
    if ptype == "integer":
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)
    if ptype == "number":
        try:
            num = float(value)
            return str(int(num)) if num.is_integer() else f"{num:g}"
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _project_prop_states(prop_states: Any) -> list[dict[str, str]]:
    """Project a v2 payload's propStates into compact {iri, label, value} rows
    for the Model Viewer tile-properties selector. Tolerates missing fields."""
    if not isinstance(prop_states, list):
        return []
    rows: list[dict[str, str]] = []
    for ps in prop_states:
        if not isinstance(ps, dict):
            continue
        prop_value = ps.get("propValue")
        label = (prop_value.get("displayName") if isinstance(prop_value, dict) else None) or ""
        rows.append(
            {
                "iri": ps.get("dataPropertyIri") or "",
                "label": label,
                "value": _format_prop_value(prop_value),
            }
        )
    return rows


def _project_state_summary(state_payload_json: str | None) -> dict[str, Any] | None:
    """Project a run's statePayloadJson into a compact summary for UI grouping.

    Returns None for absent, empty, or malformed payloads. Never raises.

    Vocabulary note (Phase 14, no behavior change): stateId values follow the
    DS_/OS_ ID-prefix convention established for the DesignState node hierarchy
    (DS_ = ParamState, OS_ = ObjState). This function only summarizes whatever
    stateId is present; OS_-prefixed payload extension lands in Phase 11.
    """
    if not state_payload_json:
        return None
    try:
        parsed = json.loads(state_payload_json)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        return None
    if not isinstance(parsed, dict):
        return None
    # v2 envelope detection via root version field
    version = parsed.get("version")
    if version == "2":
        obj_count = len(parsed.get("objStates") or [])
        param_count = len(parsed.get("paramStates") or [])
        prop_count = len(parsed.get("propStates") or [])
        return {
            "stateId": parsed.get("stateId") or "",
            "label": parsed.get("label"),
            "capturedAtUtc": parsed.get("capturedAtUtc"),
            "parameterCount": obj_count + param_count + prop_count,
            "props": _project_prop_states(parsed.get("propStates")),
        }

    # v1 fallback (ParamState-only)
    parameters = parsed.get("parameters")
    parameter_count = len(parameters) if isinstance(parameters, list) else 0
    return {
        "stateId": parsed.get("stateId") or "",
        "label": parsed.get("label"),
        "capturedAtUtc": parsed.get("capturedAtUtc"),
        "parameterCount": parameter_count,
    }


def list_validation_runs(project: str) -> list[dict[str, Any]]:
    rows = read_many(
        """
        MATCH (run:ValidationRun {graph:$graph, project:$project})
        OPTIONAL MATCH (run)-[:HAS_ENTITY]->(ve:ValidationEntity)
        RETURN
            run.runId AS runId,
            run.speckleProjectId AS speckleProjectId,
            run.baseModelId AS baseModelId,
            run.baseVersionId AS baseVersionId,
            run.validationModelId AS validationModelId,
            run.validationVersionId AS validationVersionId,
            run.modelViewerUrl AS modelViewerUrl,
            run.ValidStatus AS validStatus,
            run.SendStatus AS sendStatus,
            run.createdAt AS createdAt,
            run.rulesJson AS rulesJson,
            run.statePayloadJson AS statePayloadJson,
            count(DISTINCT ve) AS entityCount
        ORDER BY run.createdAt DESC
        """,
        {"graph": VALIDATION_GRAPH, "project": project},
    )

    runs: list[dict[str, Any]] = []
    for row in rows:
        rules = json.loads(row["rulesJson"]) if row.get("rulesJson") else []
        runs.append(
            {
                "runId": row["runId"],
                "speckleProjectId": row.get("speckleProjectId"),
                "baseModelId": row.get("baseModelId"),
                "baseVersionId": row.get("baseVersionId"),
                "validationModelId": row.get("validationModelId"),
                "validationVersionId": row.get("validationVersionId"),
                "modelViewerUrl": row.get("modelViewerUrl"),
                "createdAt": row.get("createdAt"),
                "ruleIds": [rule.get("ruleId", "") for rule in rules if rule.get("ruleId")],
                "ruleCount": len(rules),
                "failedRuleCount": sum(1 for rule in rules if not rule.get("passed")),
                "entityCount": int(row.get("entityCount") or 0),
                "state": _project_state_summary(row.get("statePayloadJson")),
            }
        )
    return runs


def delete_validation_run_metadata(project: str, run_id: str) -> None:
    write_query(
        """
        OPTIONAL MATCH (ve:ValidationEntity {graph:$graph, project:$project, runId:$runId})
        DETACH DELETE ve
        WITH 1 AS keepGoing
        OPTIONAL MATCH (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        DETACH DELETE run
        """,
        {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id},
    )


def get_validation_entity_sets(project: str, run_id: str, rule_id: str | None = None) -> dict[str, list]:
    """Roll up ValidationEntity rows to one verdict per dgEntityId.

    D-12 (Phase 1202 plan 05, ALGN12-10): rolls up via the shipped
    evidence_contract.ROLLUP_PRECEDENCE walk -- error outranks failed -- never a
    locally-ordered table and never boolean arithmetic/max-min over an enum ordinal.
    This reconciles the legacy failed-wins dedup this function used to run, which put
    `failed` ahead of `error`, the opposite of the shipped precedence.

    Legacy presentation bucketing: the rolled-up canonical status is mapped onto this
    function's existing {"failed": [...], "passed": [...]} return shape using
    evidence_contract.to_legacy_boolean, the sole sanctioned canonical->boolean
    direction -- `passed` buckets to "passed", every other status buckets to "failed".
    Per D-10 this whole function is legacy/non-authoritative: the canonical per-object
    verdict source is the evidence envelope, read in C# via
    IValidGraphRepository.GetPerObjectVerdictsAsync. This function's only remaining job
    is to not ship a second, disagreeing rollup.
    """
    rows = read_many(
        """
        MATCH (ve:ValidationEntity {graph:$graph, project:$project, runId:$runId})
        WHERE $ruleId IS NULL OR ve.ruleId = $ruleId
        RETURN ve.dgEntityId AS dgEntityId, ve.displayName AS displayName, ve.status AS status
        ORDER BY ve.dgEntityId
        """,
        {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id, "ruleId": rule_id},
    )

    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        dg_entity_id = row.get("dgEntityId")
        if not dg_entity_id:
            continue
        group = groups.setdefault(
            dg_entity_id,
            {"displayName": row.get("displayName") or dg_entity_id, "statuses": set()},
        )
        if row.get("displayName"):
            group["displayName"] = row["displayName"]

        status_raw = row.get("status")
        try:
            status = evidence_contract.CanonicalStatus(status_raw)
        except ValueError:
            logging.getLogger(__name__).warning(
                "get_validation_entity_sets: unrecognized ValidationEntity.status %r "
                "for dgEntityId=%r (project=%r, runId=%r) -- treated as UNKNOWN rather "
                "than discarded, per D-12.",
                status_raw, dg_entity_id, project, run_id,
            )
            status = evidence_contract.CanonicalStatus.UNKNOWN
        group["statuses"].add(status)

    failed: list[dict[str, str]] = []
    passed: list[dict[str, str]] = []
    for dg_entity_id, group in groups.items():
        entry = {"dgEntityId": dg_entity_id, "displayName": group["displayName"]}
        rolled_up = next(
            (candidate for candidate in evidence_contract.ROLLUP_PRECEDENCE if candidate in group["statuses"]),
            evidence_contract.CanonicalStatus.NO_POPULATION,
        )
        if evidence_contract.to_legacy_boolean(rolled_up):
            passed.append(entry)
        else:
            failed.append(entry)

    return {"failed": failed, "passed": passed}


def build_rules_summary(request: ValidationPublishRequest) -> list[dict[str, Any]]:
    results_by_id = {item.ruleId: item for item in request.ruleResults}
    summaries = []
    for rule in request.rules:
        result = results_by_id.get(rule.ruleId)
        summaries.append(
            {
                "ruleId": rule.ruleId,
                "ruleName": rule.ruleName,
                "ruleDescription": rule.ruleDescription,
                "passed": result.passed if result else False,
            }
        )
    return summaries


def _parse_shacl_report(shacl_report_json: str | None) -> dict[str, Any] | None:
    """Parse a persisted `shaclReportJson` string into a dict for the view payload.

    Returns None for absent/empty/malformed JSON or a non-object payload --
    never raises. Pre-823 runs (no shaclReportJson property) and corrupt data
    both degrade to the same quiet not-checked state (D-17), never an error.
    """
    if not shacl_report_json:
        return None
    try:
        parsed = json.loads(shacl_report_json)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_evidence_envelope(evidence_envelope_json: str | None) -> dict[str, Any] | None:
    """Parse a persisted `evidenceEnvelopeJson` string into a dict for the view payload.

    Returns None for absent/empty/malformed JSON or a non-object payload -- never
    raises. Pre-1200 runs (no evidenceEnvelopeJson property) and corrupt data both
    degrade to the same quiet not-checked state (D-08), never an error. Mirrors
    `_parse_shacl_report` exactly (Phase 823, D-17's same degrade-to-quiet
    convention).
    """
    if not evidence_envelope_json:
        return None
    try:
        parsed = json.loads(evidence_envelope_json)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _compute_canonical_state_hash(state_payload_json: str | None) -> str | None:
    """Compute the run's canonical DesignState hash from its persisted
    ``statePayloadJson`` for the view response.

    Returns ``None`` when the run carries no ``statePayloadJson`` (the existing
    absence convention -- "not recorded" rather than a missing key) and also
    returns ``None`` plus a logged warning when the stored payload is malformed
    or otherwise fails to project/hash, so a corrupt stored value never fails
    the whole view response -- the same degrade posture as the C# reader
    (`_parse_shacl_report`/`parse_evidence_envelope` above) and D-01's own
    projection contract (`design_state_projection.compute_state_hash`).

    Deliberately parses with plain ``json.loads`` (bare Python ``float``), NOT
    ``parse_float=Decimal`` (plan 1202-08, Task 4 live-run investigation --
    tried and reverted). ``design_state_projection._build_parameter_value``
    converts a bare float to ``Decimal`` via ``Decimal(repr(value)).normalize()``,
    which collapses to SCALE-0 (``Decimal("42")`` for ``42.0``) -- and this is
    the behavior that matches the C# leg, not a defect: the C# leg's
    ``NumberValue`` is typed ``double`` (`DesignStatePayloadV2Serializer.
    ParseNumber`), and `DesignStateCanonicalProjection.ToCanonicalDecimal`
    converts that ``double`` via ``Convert.ToDecimal``, which ALSO collapses to
    scale-0 for a whole-number double -- a ``double`` has no stored decimal
    scale to preserve on either leg. Using ``parse_float=Decimal`` here would
    preserve the JSON literal's scale (e.g. keep ``42.0`` at scale 1) on the
    Python side only, diverging from what the C# leg can ever produce through
    its own double-typed model -- confirmed live during 1202-08 Task 4: with
    ``parse_float=Decimal`` the replay leg matched
    ``fixtures/golden/replay/mixed-verdicts.json``'s stored
    ``expectedCanonicalStateHash`` but DISAGREED with the C# leg's hash: with
    plain ``json.loads`` (this code), the replay and C# legs AGREE with each
    other, which is the genuinely cross-language-consistent outcome DE-01
    exists to prove. The fixture's stored ``expectedCanonicalStateHash`` was
    computed via a ``parse_float=Decimal`` invocation that no double-typed
    Design State payload can ever reproduce -- see this fixture's own
    ``expectedCanonicalStateHashNote`` for the disposition.
    """
    if not state_payload_json:
        return None
    try:
        payload = json.loads(state_payload_json)
    except (TypeError, ValueError) as exc:
        logging.getLogger(__name__).warning(
            "_compute_canonical_state_hash: statePayloadJson was not valid JSON -- "
            "degrading to None rather than failing the view response: %s",
            exc,
        )
        return None
    try:
        return design_state_projection.compute_state_hash(payload)
    except (ValueError, TypeError) as exc:
        logging.getLogger(__name__).warning(
            "_compute_canonical_state_hash: statePayloadJson failed to project/hash -- "
            "degrading to None rather than failing the view response: %s",
            exc,
        )
        return None


def build_view_payload(project: str, run: dict[str, Any], object_sets: dict[str, list[str]], rule_id: str | None = None) -> dict[str, Any]:
    settings = get_speckle_settings()
    rules = json.loads(run["rulesJson"]) if run.get("rulesJson") else []
    return {
        "project": project,
        "runId": run["runId"],
        "selectedRuleId": rule_id,
        "speckleBaseUrl": settings.base_url,
        "readToken": settings.read_token,
        "baseProjectId": run["speckleProjectId"],
        "baseModelId": run["baseModelId"],
        "baseVersionId": run["baseVersionId"],
        "validationModelId": run["validationModelId"],
        "validationVersionId": run["validationVersionId"],
        "baseResourceUrl": run["baseResourceUrl"],
        "validationResourceUrl": run["validationResourceUrl"],
        "modelViewerUrl": run["modelViewerUrl"],
        "createdAt": run.get("createdAt"),
        "rules": rules,
        "objectSets": object_sets,
        "shaclReport": _parse_shacl_report(run.get("shaclReportJson")),
        "evidenceEnvelope": parse_evidence_envelope(run.get("evidenceEnvelopeJson")),
        "canonicalStateHash": _compute_canonical_state_hash(run.get("statePayloadJson")),
        "canonicalizationVersion": canonical_json.CANONICALIZATION_VERSION if run.get("statePayloadJson") else None,
    }


def validate_ingest_path(user_path: str) -> FilePath:
    """Resolve user-provided path against mount root; reject if outside root."""
    candidate = (KNOWLEDGE_REPO_ROOT / user_path).resolve()
    if not str(candidate).startswith(str(KNOWLEDGE_REPO_ROOT.resolve())):
        raise HTTPException(status_code=403, detail="Path outside allowed repository root")
    if not candidate.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    return candidate


def extract_title_from_md(file_path: FilePath) -> tuple[str, str]:
    """Return (title, content) from a markdown file. Title from first # heading or filename."""
    content = file_path.read_text(encoding="utf-8")
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped[2:].strip(), content
    return file_path.stem.replace("-", " ").replace("_", " "), content


def extract_frontmatter_tags(content: str) -> list[str]:
    """Extract tags from YAML frontmatter if present. Returns empty list if no frontmatter."""
    if not content.startswith("---"):
        return []
    parts = content.split("---", 2)
    if len(parts) < 3:
        return []
    frontmatter = parts[1]
    for line in frontmatter.split("\n"):
        line = line.strip()
        if line.lower().startswith("tags:"):
            tag_value = line[5:].strip()
            if tag_value.startswith("[") and tag_value.endswith("]"):
                return [t.strip().strip('"').strip("'").lower() for t in tag_value[1:-1].split(",") if t.strip()]
            elif tag_value:
                return [t.strip().lower() for t in tag_value.split(",") if t.strip()]
    return []


def generate_note_id(project: str, source_path: str) -> str:
    """Deterministic ID from project + source path for idempotent re-ingest."""
    return hashlib.sha256(f"{project}:{source_path}".encode()).hexdigest()[:16]


def ensure_spec_indexes():
    """Create full-text index and parent class hub nodes for SpecGraph.

    Invoked from the `lifespan` context manager at the top of this module.
    Phase 39 removed this function's deprecated startup-event decorator: once
    an explicit `lifespan=` is passed to the FastAPI constructor, Starlette
    never runs `on_startup` handlers, so leaving the decorator in place would
    have made this a no-op at runtime. Behavior is unchanged -- same call, same
    startup moment, same unguarded propagation if Neo4j is unreachable.
    """
    init_ollama_models()
    with driver.session() as session:
        session.run(
            "CREATE FULLTEXT INDEX spec_note_search IF NOT EXISTS "
            "FOR (n:SpecNote) ON EACH [n.title, n.content]"
        ).consume()
        # Ensure parent class hub nodes exist for graph connectivity
        session.run(
            "MERGE (c:SpecClass {name: 'SpecNote', graph: 'SpecGraph'}) "
            "SET c.label = 'SpecNote'"
        ).consume()
        session.run(
            "MERGE (c:SpecClass {name: 'SpecSession', graph: 'SpecGraph'}) "
            "SET c.label = 'SpecSession'"
        ).consume()
        # Backfill: connect any existing nodes that lack INSTANCE_OF links
        session.run(
            "MATCH (n:SpecNote) WHERE NOT (n)-[:INSTANCE_OF]->(:SpecClass) "
            "WITH n "
            "MERGE (c:SpecClass {name: 'SpecNote', graph: 'SpecGraph'}) "
            "MERGE (n)-[:INSTANCE_OF]->(c)"
        ).consume()
        session.run(
            "MATCH (s:SpecSession) WHERE NOT (s)-[:INSTANCE_OF]->(:SpecClass) "
            "WITH s "
            "MERGE (c:SpecClass {name: 'SpecSession', graph: 'SpecGraph'}) "
            "MERGE (s)-[:INSTANCE_OF]->(c)"
        ).consume()


@router.get("/")
def read_root():
    return {"status": "Data Service is running"}


@router.get("/integration/speckle/project/{project}")
def get_speckle_project_config(project: str):
    config = get_integration_config(project)
    if config is None:
        raise HTTPException(status_code=404, detail="No Speckle project configuration found for this DG project.")
    return config.model_dump()


@router.get("/settings/speckle")
def get_speckle_runtime_settings():
    return get_speckle_settings_response()


@router.put("/settings/speckle")
def put_speckle_runtime_settings(payload: SpeckleSettingsPayload):
    persisted = load_persisted_speckle_settings()

    base_url = (payload.baseUrl or "").strip()
    if base_url:
        persisted["baseUrl"] = base_url
    elif "baseUrl" not in persisted:
        env_base_url = os.getenv("SPECKLE_BASE_URL", "").strip()
        if env_base_url:
            persisted["baseUrl"] = env_base_url

    write_token = (payload.writeToken or "").strip()
    if write_token:
        persisted["writeToken"] = write_token

    read_token = (payload.readToken or "").strip()
    if read_token:
        persisted["readToken"] = read_token

    save_persisted_speckle_settings(persisted)
    return get_speckle_settings_response()


# ---------------------------------------------------------------------------
# LLM Gateway endpoints
# ---------------------------------------------------------------------------


@router.get("/llm/settings")
def get_llm_settings():
    """Read LLM settings (provider, model, masked key, status)."""
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    return get_llm_settings_response(settings, master_secret)


@router.put("/llm/settings")
def put_llm_settings(payload: LLMSettingsPayload):
    """Save LLM settings. Encrypts apiKey with Fernet before persisting."""
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    if not master_secret:
        raise HTTPException(status_code=500, detail="LLM_MASTER_SECRET not configured")

    VALID_PROVIDERS = {"anthropic", "openai", "ollama"}
    if payload.provider is not None and payload.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {payload.provider}. Valid options: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    settings = load_persisted_llm_settings()

    if payload.provider is not None:
        settings["provider"] = payload.provider
    if payload.model is not None:
        settings["model"] = payload.model
    if payload.baseUrl is not None:
        settings["baseUrl"] = payload.baseUrl
    if payload.apiKey:
        # Only encrypt+store if apiKey is non-empty (None or "" keeps existing)
        settings["apiKey"] = encrypt_value(payload.apiKey, master_secret)

    save_persisted_llm_settings(settings)
    # Re-read to return consistent state
    return get_llm_settings_response(load_persisted_llm_settings(), master_secret)


@router.delete("/llm/settings", status_code=204)
def delete_llm_settings():
    """Clear all LLM settings. Gateway falls back to Ollama on next call."""
    save_persisted_llm_settings({})
    return None


@router.post("/llm/generate")
def llm_generate(req: GenerateRequest):
    """Main gateway endpoint. Routes prompt to the active provider adapter.

    n8n sends provider:null per D-07 — gateway resolves active provider from
    saved settings. Request-level provider/model override saved values.
    """
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()

    provider, model, api_key = resolve_active_provider(settings, master_secret)

    # Request-level override (n8n sends null per D-07)
    if req.provider is not None:
        provider = req.provider
    if req.model is not None:
        model = req.model

    req_with_model = GenerateRequest(
        prompt=req.prompt,
        system=req.system,
        model=model,
        provider=provider,
    )

    try:
        adapter = get_adapter(provider, settings.get("baseUrl"))
        response = adapter.generate(req_with_model, api_key)
        return response
    except Exception as exc:
        error_msg, hint, code = map_provider_error(exc)
        raise _structured_error_response(error_msg, hint, code, 502)


# Local provider — reachability is the whole test, there is no key to check.
KEYLESS_PROVIDER = "ollama"


@router.post("/llm/settings/test")
def test_llm_settings(payload: TestConnectionPayload | None = None):
    """Test an LLM configuration with a minimal provider call.

    With no body, tests the saved configuration. With a body, tests the provider
    named there -- the settings panel sends its current selection so a provider
    the user holds no key for fails honestly instead of passing on the saved
    provider's key.

    Returns success/failure with latency measurement and live model list.
    """
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()

    provider, model, api_key = resolve_active_provider(settings, master_secret)
    base_url = settings.get("baseUrl")

    if payload and payload.provider:
        requested = payload.provider
        if payload.baseUrl:
            base_url = payload.baseUrl
        if payload.apiKey:
            api_key = payload.apiKey
        elif requested == KEYLESS_PROVIDER:
            api_key = None
        elif requested != provider:
            # One key slot, and it belongs to `provider` — not to `requested`.
            return TestResult(
                success=False,
                error=(
                    f"No API key configured for {requested}. Enter a key for "
                    f"{requested} and save it, or test the saved provider instead."
                ),
            )
        model = payload.model or (model if requested == provider else None)
        provider = requested

    # Only an EXPLICIT ollama request skips the key check; with no body at all the
    # unconfigured-gateway contract stays "No API key configured" rather than
    # silently probing whatever the fallback provider happens to be.
    if not api_key and not (payload and payload.provider == KEYLESS_PROVIDER):
        return TestResult(success=False, error="No API key configured")

    start = time.time()
    try:
        adapter = get_adapter(provider, base_url)
        test_req = GenerateRequest(prompt="test", model=model)
        adapter.generate(test_req, api_key)
        latency_ms = (time.time() - start) * 1000.0

        models = list_models_for_provider(provider, api_key, base_url)

        return TestResult(success=True, latencyMs=latency_ms, models=models)
    except Exception as exc:
        error_msg, _hint, _code = map_provider_error(exc)
        return TestResult(success=False, error=error_msg)


@router.get("/llm/models")
def get_llm_models(provider: str):
    """Return available model IDs for the given provider.

    Ollama: cached auto-discovery result (D-16).
    Anthropic/OpenAI with key: live API query.
    Anthropic/OpenAI without key: seed list (D-14).
    """
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    encrypted_key = settings.get("apiKey", "")
    api_key: str | None = None
    if encrypted_key:
        try:
            api_key = decrypt_value(encrypted_key, master_secret)
        except Exception:
            pass

    models = list_models_for_provider(provider, api_key, settings.get("baseUrl"))
    return models


# ---------------------------------------------------------------------------
# Connector credential endpoints (Phase 812: CONNB-01..04)
# ---------------------------------------------------------------------------


@router.get("/connectors")
def get_connectors(request: Request):
    """Connector registry joined with per-connector status, last-connection
    date, and credential summaries (never tokens or hashes). CONNB-01, CONNB-04.

    Phase 1205 (T-1205-10-06): only credentials bound to a project the caller
    is a member of are listed, and status / last-connection are derived from
    those credentials alone. An admin sees every credential.
    """
    principal = request.state.principal
    projects = None if principal.is_admin else set(auth.list_member_projects(principal.username))
    return {
        "categories": connectors.CONNECTOR_CATEGORIES,
        "connectors": connectors.get_connector_overview(projects=projects),
    }


@router.post("/connectors/{connector_id}/credentials", status_code=201)
def create_connector_credential(connector_id: str, payload: CredentialCreatePayload | None = None):
    """Mint a credential for a connector. The token is returned once here
    and never again — only its SHA-256 hash is persisted (CONNB-02).
    """
    if connector_id not in connectors.CONNECTOR_IDS:
        raise _structured_error_response(
            f"Unknown connector: {connector_id}",
            "Use a connector id from GET /connectors.",
            "CONNECTOR_NOT_FOUND",
            404,
        )
    label = payload.label if payload else None
    project = payload.project if payload else None
    record, token = connectors.create_credential(connector_id, label, project)
    return CredentialCreatedResponse(credential_id=record["credential_id"], token=token)


@router.delete("/connectors/{connector_id}/credentials/{credential_id}", status_code=204)
def revoke_connector_credential(connector_id: str, credential_id: str):
    """Revoke a credential. Revoked tokens stop authenticating heartbeats (CONNB-01)."""
    if connector_id not in connectors.CONNECTOR_IDS:
        raise _structured_error_response(
            f"Unknown connector: {connector_id}",
            "Use a connector id from GET /connectors.",
            "CONNECTOR_NOT_FOUND",
            404,
        )
    if not connectors.revoke_credential(connector_id, credential_id):
        raise _structured_error_response(
            f"Credential not found: {credential_id}",
            "Use a credential_id from GET /connectors.",
            "CREDENTIAL_NOT_FOUND",
            404,
        )
    return None


@router.post("/connectors/heartbeat")
def connector_heartbeat(request: Request):
    """Token-authenticated heartbeat. Updates the connector's last_connection
    and returns its derived status. 401 on unknown/revoked token (CONNB-03).
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[len("Bearer "):].strip() if auth_header.startswith("Bearer ") else ""
    record = connectors.record_heartbeat(token) if token.startswith(connectors.TOKEN_PREFIX) else None
    if record is None:
        raise _structured_error_response(
            "Invalid or revoked connector token.",
            "Create a new credential via POST /connectors/{connector_id}/credentials.",
            "CONNECTOR_AUTH_FAILED",
            401,
        )
    # Phase 1205 (D-07/D-19/T-1205-07-08): the Neo4j admin bundle is withheld
    # from every connector in the multi-user profile -- Bolt is not published
    # there and the GH direct-Bolt path is documented as local-only. `local`
    # keeps today's bundle so the trusted-local GH workflow is unaffected.
    neo4j_bundle = None
    if auth.deployment_profile() != "multi-user":
        neo4j_bundle = connectors.Neo4jBundle(
            uri=NEO4J_PUBLIC_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        )
    return HeartbeatResponse(
        connector_id=record["connector_id"],
        status=connectors.derive_status(record["last_connection"]),
        # Phase 825: unlock the project scope + host-facing Neo4j connection bundle
        # for the authenticated connector. Old records without a project read as
        # "default-project".
        project=record.get("project") or "default-project",
        neo4j=neo4j_bundle,
    )


# ---------------------------------------------------------------------------
# Reasoner settings endpoints (Phase 814: REAS-01..03)
# ---------------------------------------------------------------------------


class ReasonerSettingsPayload(BaseModel):
    reasoner: str


@router.get("/reasoner/settings")
def get_reasoner_settings():
    """Return the reasoner registry and currently selected reasoner id."""
    settings = reasoner.load_settings()
    return {
        "reasoners": reasoner.REASONER_REGISTRY,
        "selected": settings.get("selected", None),
    }


@router.put("/reasoner/settings")
def put_reasoner_settings(payload: ReasonerSettingsPayload):
    """Persist the selected reasoner id. Rejects unknown ids with 422."""
    if payload.reasoner not in reasoner.REASONER_IDS:
        raise _structured_error_response(
            f"Unknown reasoner: {payload.reasoner}",
            f"Valid reasoner ids: {', '.join(sorted(reasoner.REASONER_IDS))}",
            "REASONER_NOT_FOUND",
            422,
        )
    reasoner.save_settings({"selected": payload.reasoner})
    return {
        "reasoners": reasoner.REASONER_REGISTRY,
        "selected": payload.reasoner,
    }


class ReasonerConsistencyRequest(BaseModel):
    project: str
    engine: str = "hermit"


@router.post("/reasoner/consistency")
def post_reasoner_consistency(payload: ReasonerConsistencyRequest):
    """Thin proxy to the dg-reasoner sidecar's `POST /reason/consistency` (D-06).

    Forwards `{project, engine}` to `DG_REASONER_URL` over httpx with an
    EXPLICIT short timeout. This is the only thing that reaches the sidecar
    (D-12, internal-only, no nginx route, no host port) -- a sidecar hang
    surfaces here as a fast, caught 502/504, never a hang in this hot path.
    """
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/reason/consistency",
            json={"project": payload.project, "engine": payload.engine},
            # read must exceed the sidecar's own DG_REASONER_TIMEOUT_SECONDS ceiling
            # (default 90s) with margin, or the proxy returns false 504s on every
            # non-trivial HermiT run as the rule corpus grows (822-02 Pitfall 2).
            # connect/write/pool stay short so an unreachable sidecar still fails fast.
            timeout=httpx.Timeout(
                connect=2.0,
                read=float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90")) + 10,
                write=2.0,
                pool=2.0,
            ),
        )
    except httpx.TimeoutException:
        raise _structured_error_response(
            "Reasoner sidecar request timed out.",
            "The dg-reasoner sidecar is slow or unreachable. Try again later.",
            "REASONER_TIMEOUT",
            504,
        )
    except httpx.ConnectError:
        raise _structured_error_response(
            "Could not connect to the reasoner sidecar.",
            "Verify the dg-reasoner service is running.",
            "REASONER_UNAVAILABLE",
            502,
        )

    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}

    return JSONResponse(status_code=response.status_code, content=body)


# ---------------------------------------------------------------------------
# DG CANVAS LISTENER bridge (Phase 33 Plan 03: BRDG-02)
# ---------------------------------------------------------------------------


class ComputgraphContextPullRequest(BaseModel):
    project: str


@router.post("/computgraph/context/pull")
def pull_computgraph_context(payload: ComputgraphContextPullRequest):
    """Thin proxy to the live Grasshopper canvas via gh_bridge (BRDG-02).

    Forwards to `gh_bridge.get_canvas_context`, stamps `project` onto the
    returned document, and returns it as-is. Any bridge failure (refused/
    timeout -> 503 GH_BRIDGE_UNREACHABLE, listener error envelope -> 502)
    propagates unchanged -- gh_bridge already raises the structured error.
    """
    context = gh_bridge.get_canvas_context(payload.project)
    if isinstance(context, dict):
        context["project"] = payload.project
    return context


# ---------------------------------------------------------------------------
# Recognition pipeline (Phase 35: RCGN-01)
# ---------------------------------------------------------------------------


class RecognizeRequest(BaseModel):
    """Request body for POST /computgraph/recognize.

    `cg_context` is the cgContextJson v1 envelope (pull it live via
    POST /computgraph/context/pull first, then post the result here -- keeps
    this route synchronous, testable, and consistent with the no-message-queue
    architecture decision). `procedure_index` optionally scopes recognition
    to one procedure for large definitions.
    """

    cg_context: dict
    procedure_index: int | None = None
    project: str | None = None


def _violation_hint(message: str) -> str:
    """Extract the 'How to fix' clause from a cg_recognition violation
    message (What+Where+How-to-fix phrasing) rather than duplicating the
    guidance text a second time in the route."""
    marker = "How to fix:"
    idx = message.find(marker)
    if idx == -1:
        return "See the violation message for details."
    return message[idx + len(marker) :].strip()


@router.post("/computgraph/recognize")
def post_computgraph_recognize(payload: RecognizeRequest):
    """Classify untagged canvas entities into a schema-valid proposed-structure
    (RCGN-01) via the two-tier Tier-0 (deterministic topology)/Tier-1 (LLM)
    pipeline (Phase 35-12), bounded-retry validated against the submitted
    cg_context (RCGN-04: hard-rejects hallucinated/tagged-overlap member
    ids). Thin route -- all logic delegates to
    cg_recognition.recognize_structure(), mirroring
    post_context_generate_cypher()'s delegation + error-mapping shape.

    A `tier: "0"` response means Tier 0 decided every candidate and the LLM
    was never called. Non-retryable Tier-1 outcomes (`output_truncated`,
    `grammar_as_filter`, `provider_refusal`) return HTTP 200 with
    `valid: false` -- they are model-run outcomes the caller must be able to
    read alongside `attempts`/`violations`, and a 502 would discard that
    context. Only `empty_procedure_scope` -- a CALLER error, not a model
    failure -- is mapped to a 422.
    """
    try:
        result = cg_recognition.recognize_structure(payload.cg_context, payload.procedure_index)
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cg_context shape (cgContextJson v1 envelope).",
            "RECOGNIZE_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        error_msg, hint, code = map_provider_error(exc)
        raise _structured_error_response(error_msg, hint, code, 502)

    if not result.get("valid"):
        empty_scope_violation = next(
            (v for v in (result.get("violations") or []) if v.get("code") == "empty_procedure_scope"),
            None,
        )
        if empty_scope_violation is not None:
            raise _structured_error_response(
                empty_scope_violation["message"],
                _violation_hint(empty_scope_violation["message"]),
                "RECOGNIZE_EMPTY_PROCEDURE_SCOPE",
                422,
            )

    return result


# ---------------------------------------------------------------------------
# Computgraph publish endpoint (Phase 36-01: CGPD-01/02/03)
# ---------------------------------------------------------------------------


class ComputgraphPublishRequest(BaseModel):
    """Body for POST /computgraph/publish.

    `cgContext` is the confirmed cgContextJson v1 envelope (carries dgId per
    entity stamped by CgContextDgIdAssigner before serialization). The route
    recomputes dgId server-side regardless of any client-stamped value.

    Field is camelCase (not `cg_context`) to match ComputgraphPublishClient's
    JsonNamingPolicy.CamelCase wire format -- same convention as
    ValidationPublishRequest.statePayloadJson/ruleResults above.
    """

    project: str
    cgContext: dict


@router.post("/computgraph/publish")
def post_computgraph_publish(payload: ComputgraphPublishRequest):
    """Publish a confirmed cgContextJson v1 envelope as a Computgraph subgraph.

    Thin route -- opens its own session (so the whole write is one
    transaction), delegates to computgraph_publish.publish_structure(), and
    returns {status, publishedCounts, staleEntityIds}. Structured error on
    malformed input (CGPD-01/02/03).
    """
    try:
        with driver.session() as session:
            return computgraph_publish.publish_structure(
                session, payload.project, payload.cgContext
            )
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cgContext shape (cgContextJson v1 envelope).",
            "COMPUTGRAPH_PUBLISH_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        raise _structured_error_response(
            str(exc),
            "Check Neo4j availability and the publish payload.",
            "COMPUTGRAPH_PUBLISH_FAILED",
            502,
        )


class ComputgraphValidateRequest(BaseModel):
    """Body for POST /computgraph/validate. `definitionId` is optional --
    when omitted, cg_structure_checks.resolve_definition_id() resolves it
    against the project's published definitions. No validators beyond the
    type declarations -- domain validation raises from the delegate, not the
    model, matching ComputgraphPublishRequest's plainness."""

    project: str
    definitionId: str | None = None


@router.post("/computgraph/validate")
def post_computgraph_validate(payload: ComputgraphValidateRequest):
    """Run the deterministic, LLM-free structural + rule-mapped checks over
    the published Computgraph and return the documented report.

    Thin route -- opens one session, delegates to
    cg_structure_checks.build_validation_report(), and returns its result
    directly. Performs no write and never calls the LLM gateway.
    """
    try:
        with driver.session() as session:
            return cg_structure_checks.build_validation_report(
                session, payload.project, payload.definitionId
            )
    except cg_structure_checks.DefinitionResolutionError as exc:
        if exc.code == "COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION":
            hint = (
                "Multiple definitions are published for this project -- "
                f"retry with one of: {', '.join(exc.available)}."
            )
        elif exc.code == "COMPUTGRAPH_VALIDATE_NO_DEFINITION":
            hint = "Publish this definition first through POST /computgraph/publish."
        else:
            hint = "Publish this definition first through POST /computgraph/publish."
        raise _structured_error_response(str(exc), hint, exc.code, 422)
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the project and definitionId fields on the request body.",
            "COMPUTGRAPH_VALIDATE_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        raise _structured_error_response(
            str(exc),
            "Check Neo4j availability.",
            "COMPUTGRAPH_VALIDATE_FAILED",
            502,
        )


class ComputgraphConsultRequest(BaseModel):
    """Body for POST /computgraph/consult. Unlike ComputgraphValidateRequest,
    `definitionId` has no resolution fallback here -- spec/API.md documents
    all three fields as required, so a missing one is rejected by FastAPI's
    own request-body validation before any session is opened."""

    project: str
    definitionId: str
    question: str


@router.post("/computgraph/consult")
def post_computgraph_consult(payload: ComputgraphConsultRequest):
    """Read-only, grounded LLM consult over one published Computgraph
    subgraph (Phase 37 Plan 06: SVAL-03).

    Thin route -- opens one session, delegates to
    dg_context.consult_computgraph(), and returns its result directly.
    Executes nothing derived from the model's output; the endpoint never
    writes anything.
    """
    try:
        with driver.session() as session:
            return dg_context.consult_computgraph(
                payload.project, payload.definitionId, payload.question, session=session
            )
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the project, definitionId and question fields on the request body.",
            "COMPUTGRAPH_CONSULT_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        raise _structured_error_response(
            str(exc),
            "Check Neo4j availability and the configured LLM provider.",
            "COMPUTGRAPH_CONSULT_FAILED",
            502,
        )


class ComputgraphGenerateInputsRequest(BaseModel):
    """Body for POST /computgraph/generate-inputs. `definitionId` resolves
    the same way ComputgraphValidateRequest's does (omit for the project's
    sole published definition). No validators beyond the type declarations
    -- domain validation, including the 1..8 candidateCount bound, raises
    from the delegate (cg_input_generation.generate_inputs), matching the
    sibling Computgraph request models' documented plainness."""

    project: str
    definitionId: "str | None" = None
    ruleId: str
    candidateCount: "int | None" = None
    parameterOverrides: "list[str] | None" = None


@router.post("/computgraph/generate-inputs")
def post_computgraph_generate_inputs(payload: ComputgraphGenerateInputsRequest):
    """Generate AI candidate parameter sets for a Metagraph Rule from
    published Computgraph parameter bindings (Phase 38: GHIN-01..04).

    Thin route -- opens one session, delegates to
    cg_input_generation.generate_inputs(), and returns its result directly.
    Performs no write and has no code path to the Grasshopper canvas bridge
    (GHIN-04) -- enforced structurally by test_cg_input_boundary.py's
    ast-based import-closure assertion over the generation modules, not by
    this docstring alone. candidateCount's 1..8 bound is enforced ONLY
    inside cg_input_generation.generate_inputs(), never re-checked here.
    """
    try:
        with driver.session() as session:
            return cg_input_generation.generate_inputs(
                session,
                payload.project,
                payload.definitionId,
                payload.ruleId,
                candidate_count=payload.candidateCount,
                parameter_overrides=payload.parameterOverrides,
            )
    except cg_structure_checks.DefinitionResolutionError as exc:
        if exc.code == "COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION":
            hint = (
                "Multiple definitions are published for this project -- "
                f"retry with one of: {', '.join(exc.available)}."
            )
            code = "COMPUTGRAPH_GENERATE_INPUTS_AMBIGUOUS_DEFINITION"
        else:
            hint = "Publish this definition first through POST /computgraph/publish."
            code = "COMPUTGRAPH_GENERATE_INPUTS_NO_DEFINITION"
        raise _structured_error_response(str(exc), hint, code, 422)
    except cg_input_bindings.RuleNotFoundError as exc:
        raise _structured_error_response(
            str(exc),
            "Check that ruleId names an existing Metagraph Rule by Rule_Id in this project.",
            "COMPUTGRAPH_GENERATE_INPUTS_RULE_NOT_FOUND",
            422,
        )
    except cg_input_generation.NoEligibleParametersError as exc:
        reasons = sorted({row.get("reason") for row in exc.excluded if row.get("reason")})
        hint = (
            "No published parameter is eligible for this rule. Exclusion reasons "
            f"encountered: {', '.join(reasons) if reasons else 'none (zero candidate parameters exist)'}."
        )
        raise _structured_error_response(
            str(exc), hint, "COMPUTGRAPH_GENERATE_INPUTS_NO_ELIGIBLE_PARAMETERS", 422
        )
    except cg_input_bindings.InputBindingError as exc:
        raise _structured_error_response(
            str(exc),
            "Check llm/structure_rules.json's inputBindings entry for this rule.",
            "COMPUTGRAPH_GENERATE_INPUTS_REQUEST_INVALID",
            422,
        )
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check candidateCount is between 1 and 8, and the other request fields.",
            "COMPUTGRAPH_GENERATE_INPUTS_REQUEST_INVALID",
            422,
        )
    except cg_input_generation.DomainViolationExhaustedError as exc:
        raise _structured_error_response(
            str(exc),
            "The deterministic Tier 0 sampler could not produce a candidate; check the "
            "resolved bound parameters' domains.",
            "COMPUTGRAPH_GENERATE_INPUTS_DOMAIN_VIOLATION",
            502,
        )
    except Exception as exc:
        raise _structured_error_response(
            str(exc),
            "Check Neo4j availability and the configured LLM provider.",
            "COMPUTGRAPH_GENERATE_INPUTS_FAILED",
            502,
        )


class ComputgraphAcceptCandidateRequest(BaseModel):
    """Body for POST /computgraph/candidates/accept. `definitionId` is
    **required** here -- unlike ComputgraphGenerateInputsRequest, there is no
    resolution fallback, because accepting against an ambiguously-resolved
    definition would write a node bound to a definition the caller did not
    name. `candidate` is exactly one item from a prior generate-inputs
    response's candidates[] array, round-tripped verbatim by the caller."""

    project: str
    definitionId: str
    ruleId: str
    candidate: dict
    parameterOverrides: "list[str] | None" = None


@router.post("/computgraph/candidates/accept")
def post_computgraph_accept_candidate(payload: ComputgraphAcceptCandidateRequest):
    """Persist one architect-accepted AI-generated candidate as a standalone
    `ParamState` DesignState (Phase 38: GHIN-02/03/04).

    Two guarantees this route's contract makes: the server re-validates
    every parameter against the LIVE published domains before writing --
    the client round-trip is never trusted (T-38-17) -- and this is the
    ONLY route in the phase that writes anything; POST
    /computgraph/generate-inputs performs zero writes.

    `parameterOverrides`, when present, MUST be the same list the caller
    passed to POST /computgraph/generate-inputs to generate this candidate
    (CR-01) -- accept-time re-classification needs the identical override
    scope to resolve the same bound-parameter set, or a candidate generated
    with an override is unconditionally rejected as unknown/missing
    parameters.

    Thin route -- opens one session, delegates to
    cg_paramstate_store.accept_candidate(), and returns its result directly.
    """
    try:
        with driver.session() as session:
            return cg_paramstate_store.accept_candidate(
                session,
                payload.project,
                payload.definitionId,
                payload.ruleId,
                payload.candidate,
                parameter_overrides=payload.parameterOverrides,
            )
    except cg_paramstate_store.CandidateDomainViolation as exc:
        offending = sorted({v.get("parameterId") for v in exc.violations if v.get("parameterId")})
        hint = (
            "Re-validation against the live published domains found violations for: "
            f"{', '.join(offending) if offending else '(see violations)'}. Re-generate the "
            "candidate against the current domains rather than editing it by hand."
        )
        raise _structured_error_response(
            str(exc), hint, "COMPUTGRAPH_ACCEPT_CANDIDATE_DOMAIN_VIOLATION", 422
        )
    except (cg_paramstate_store.CandidateRequestInvalid, ValueError) as exc:
        raise _structured_error_response(
            str(exc),
            "Check that candidate is exactly one item round-tripped verbatim from a prior "
            "generate-inputs response, and that project/definitionId/ruleId are correct.",
            "COMPUTGRAPH_ACCEPT_CANDIDATE_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        raise _structured_error_response(
            str(exc),
            "Check Neo4j availability.",
            "COMPUTGRAPH_ACCEPT_CANDIDATE_FAILED",
            502,
        )


# ---------------------------------------------------------------------------
# Context assembler endpoints (Phase 29: CTXA-01..05)
# ---------------------------------------------------------------------------


def _context_type_invalid_error(exc: ValueError) -> HTTPException:
    return _structured_error_response(
        str(exc),
        "Valid types: rule_ingest, rule_edit, graph_query",
        "CONTEXT_TYPE_INVALID",
        422,
    )


@router.post("/context/assemble")
def post_context_assemble(payload: dg_context.ContextAssembleRequest):
    """Assemble the per-layer V7 concept subset + SWRL conventions + selected
    Cypher catalog shapes + live existing entities for one request (D-01).
    Thin route -- all logic delegates to dg_context.assemble_context()."""
    try:
        with driver.session() as session:
            return dg_context.assemble_context(payload, session=session)
    except ValueError as exc:
        raise _context_type_invalid_error(exc)


@router.get("/context/debug")
def get_context_debug(
    type: str,
    project: str,
    rules_text: str | None = None,
    question: str | None = None,
):
    """Inspection endpoint sharing /context/assemble's exact param contract and
    code path (D-04) -- what you inspect here is exactly what gets assembled."""
    try:
        req = dg_context.ContextAssembleRequest(
            type=type, project=project, rules_text=rules_text, question=question
        )
        with driver.session() as session:
            return dg_context.assemble_context(req, session=session)
    except ValueError as exc:
        raise _context_type_invalid_error(exc)


@router.post("/context/generate-cypher")
def post_context_generate_cypher(payload: dg_context.GenerateCypherRequest):
    """The single n8n-facing call wrapping prompt-in -> validated-cypher-out
    (CTXA-04, D-06/D-07). Retries internally, bounded at 2 retries (3
    attempts total) -- n8n sees only the final valid Cypher or a final
    structured violation list; intermediate failed attempts stay invisible.
    """
    try:
        return dg_context.generate_validated_cypher(payload.prompt, payload.type)
    except ValueError as exc:
        raise _context_type_invalid_error(exc)
    except Exception as exc:
        error_msg, hint, code = map_provider_error(exc)
        raise _structured_error_response(error_msg, hint, code, 502)


# ---------------------------------------------------------------------------
# Cross-platform identity registry endpoints (Phase 32.1: DGID-02/03/05)
# ---------------------------------------------------------------------------
#
# Thin routes — no Cypher lives here. Each opens `with driver.session() as session:`
# and delegates to dg_identity.py, translating DgIdentityError by its `code` into a
# What+Where+How-to-fix structured response via _structured_error_response.


def _dgid_not_found_error(dg_id: str) -> HTTPException:
    return _structured_error_response(
        f"No Computgraph entity found with dgId '{dg_id}'.",
        "Verify the dgId was minted via /identity/mint or the publish path before resolving/binding.",
        "DGID_NOT_FOUND",
        404,
    )


def _ambiguous_binding_error(native_id: str, existing_dg_id: str) -> HTTPException:
    return _structured_error_response(
        f"Native id '{native_id}' is already bound to dgId '{existing_dg_id}'.",
        "Detach the existing representation before re-binding, or confirm this is the intended object.",
        "DGID_AMBIGUOUS_BINDING",
        409,
    )


@router.post("/identity/mint")
def post_identity_mint(payload: MintRequest):
    """Deterministically mint + persist a dgId for a Computgraph entity.

    Idempotent — safe to call unconditionally from the publish path; re-minting the
    same (project, definitionId, cgId) triple returns the same dgId without
    duplicating the node.
    """
    with driver.session() as session:
        dg_id = dg_identity.mint_identity(
            session,
            payload.project,
            payload.definition_id,
            payload.cg_id,
            payload.entity_kind,
        )
    return {"dgId": dg_id}


@router.get("/identity/resolve")
def get_identity_resolve(platform: str, native_id: str, project: str):
    """Resolve a (platform, native_id) representation to its dgId (project-scoped)."""
    with driver.session() as session:
        dg_id = dg_identity.resolve_native_id(session, platform, native_id, project)
    if dg_id is None:
        raise _structured_error_response(
            f"No dgId is bound to native id '{native_id}' on platform '{platform}' in project '{project}'.",
            "Bind the native id via /identity/bind, or check the platform/project scope.",
            "DGID_NOT_FOUND",
            404,
        )
    return {"dgId": dg_id}


@router.post("/identity/bind")
def post_identity_bind(payload: BindRepresentationRequest):
    """Bind a native-id representation to a dgId — never a silent repoint.

    An existing binding to a DIFFERENT dgId returns a structured 409
    DGID_AMBIGUOUS_BINDING; an unminted dgId returns 404 DGID_NOT_FOUND.
    """
    try:
        with driver.session() as session:
            representation = dg_identity.bind_representation(
                session,
                payload.dg_id,
                payload.platform,
                payload.native_id_kind,
                payload.native_id,
                payload.connector,
                payload.project,
            )
    except dg_identity.DgIdentityError as exc:
        if exc.code == "DGID_AMBIGUOUS_BINDING":
            raise _ambiguous_binding_error(payload.native_id, exc.existing_dg_id or "")
        raise _dgid_not_found_error(payload.dg_id)
    return representation


@router.get("/identity/{dg_id}/representations")
def get_identity_representations(dg_id: str, project: str):
    """List all platform representations bound to a dgId within a project."""
    with driver.session() as session:
        return dg_identity.list_representations(session, dg_id, project)


@router.delete("/identity/{dg_id}/representations")
def delete_identity_representation(dg_id: str, platform: str, native_id: str, project: str):
    """Detach a representation from a dgId — removes ONLY the representation.

    The route never writes the entity node, so the dgId is untouched (DGID-02); a
    missing binding surfaces a structured 404 DGID_NOT_FOUND.
    """
    try:
        with driver.session() as session:
            dg_identity.detach_representation(session, dg_id, platform, native_id, project)
    except dg_identity.DgIdentityError:
        raise _dgid_not_found_error(dg_id)
    return {"detached": True}


@router.post("/identity/{dg_id}/properties")
def post_identity_properties(dg_id: str, payload: SharedPropertyWriteRequest, project: str):
    """Write (upsert) a cross-platform shared property on a dgId.

    The property is keyed by (dgId, propertyName, project) — any bound platform
    representation (GH writer, simulated Revit reader, …) sees the same value
    when reading by dgId (DGID-04: Ladybug-insulation cross-platform flow).
    """
    try:
        with driver.session() as session:
            result = dg_identity.write_shared_property(
                session,
                dg_id,
                payload.property_name,
                payload.value,
                payload.platform,
                payload.connector,
                project,
            )
    except dg_identity.DgIdentityError:
        raise _dgid_not_found_error(dg_id)
    return result


@router.get("/identity/{dg_id}/properties")
def get_identity_properties(dg_id: str, project: str, property_name: str = ""):
    """Read shared properties attached to a dgId.

    When ``property_name`` is provided, returns a single property dict; otherwise
    returns a list of all shared properties on this dgId within ``project``.
    """
    try:
        with driver.session() as session:
            if property_name:
                return dg_identity.read_shared_property(session, dg_id, property_name, project)
            return dg_identity.list_shared_properties(session, dg_id, project)
    except dg_identity.DgIdentityError as exc:
        raise _dgid_not_found_error(dg_id)


@router.put("/integration/speckle/project/{project}")
def put_speckle_project_config(project: str, payload: SpeckleProjectConfigPayload):
    payload = normalize_speckle_project_config_payload(payload)
    if not payload.speckleProjectId or not payload.baseModelId:
        raise HTTPException(status_code=400, detail="speckleProjectId and baseModelId are required.")
    config = upsert_integration_config(project, payload)
    return config.model_dump()


def _auto_configure_integration(project: str) -> SpeckleProjectConfigPayload | None:
    """Try to auto-create an IntegrationConfig from environment variables.

    Returns the created config if both SPECKLE_PROJECT_ID and SPECKLE_BASE_MODEL_ID
    are set in the environment, otherwise None.
    """
    speckle_project_id = os.getenv("SPECKLE_PROJECT_ID", "").strip()
    base_model_id = os.getenv("SPECKLE_BASE_MODEL_ID", "").strip()
    if not speckle_project_id or not base_model_id:
        return None
    return upsert_integration_config(
        project,
        SpeckleProjectConfigPayload(
            speckleProjectId=speckle_project_id,
            baseModelId=base_model_id,
        ),
    )


def _call_shacl_validate(project: str, run_id: str) -> dict[str, Any]:
    """Non-fatal proxy to the dg-reasoner sidecar's `POST /shacl/validate` (D-01/D-02).

    Mirrors `post_reasoner_consistency`'s httpx pattern but diverges on
    purpose: this proxy is catch-all non-fatal and NEVER raises -- a SHACL
    failure (unreachable/timeout/error) must never endanger the Speckle
    publish hot path. Returns a status dict:
      - `{"status": "ok", **body}` on success (body = the canonical
        `{conforms, results, counts}` envelope from Plan 823-02)
      - `{"status": "timeout"}` on httpx timeout, sidecar body `error == "timeout"`,
        or HTTP 504
      - `{"status": "unavailable"}` on connect error or any other exception
    """
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/shacl/validate",
            json={"project": project, "run_id": run_id},
            timeout=httpx.Timeout(
                connect=2.0,
                read=DG_SHACL_HTTP_TIMEOUT_SECONDS,
                write=2.0,
                pool=2.0,
            ),
        )
    except httpx.TimeoutException:
        return {"status": "timeout"}
    except Exception:
        # Catch-all (D-02): connect errors and anything unforeseen degrade to
        # "unavailable" -- this proxy must never raise into the caller.
        return {"status": "unavailable"}

    try:
        if response.status_code == 504:
            return {"status": "timeout"}
        body = response.json()
    except Exception:
        return {"status": "unavailable"}

    if isinstance(body, dict) and body.get("error") == "timeout":
        return {"status": "timeout"}

    if not isinstance(body, dict):
        return {"status": "unavailable"}

    return {"status": "ok", **body}


def persist_evidence_envelope(project: str, run_id: str, envelope_json: str) -> None:
    """Persist an evidence envelope JSON string as `evidenceEnvelopeJson` on the
    ValidationRun node.

    Additive, second write after `store_validation_run` -- ordering of the Speckle
    publish + store_validation_run is unchanged. Parameterized MERGE/SET keyed by
    {graph, project, runId}, never string-interpolated -- identical shape to
    `_persist_shacl_report`. Implements D-06 (emission point) / D-08 (additive
    sidecar, absence and corruption both read as not-recorded).

    A failure here (Neo4j error, serialization issue upstream) is logged and
    swallowed by the caller's wrapper -- an envelope that fails to persist degrades
    to not-recorded, exactly as an absent property does, and must never break the
    publish path that was working before this phase.
    """
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET run.evidenceEnvelopeJson = $evidenceEnvelopeJson
        """,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "runId": run_id,
            "evidenceEnvelopeJson": envelope_json,
        },
    )


def _parse_supplied_canonical_status(
    raw: Any,
) -> "evidence_contract.CanonicalStatus | None":
    """Parse a producer-supplied canonical status wire name, or None.

    Returns None for absent, non-string, or unrecognized values so the caller falls
    back to the legacy boolean path. Deliberately total: a malformed entry degrades
    to the pre-1201 behavior instead of failing the publish, matching the contract's
    own rule that an absent envelope means "not recorded", never an error.
    """
    if not isinstance(raw, str):
        return None
    try:
        return evidence_contract.CanonicalStatus(raw.strip())
    except ValueError:
        return None


def _build_publish_evidence_envelope(
    project: str, run_id: str, entity_dicts: list[dict[str, Any]]
) -> "evidence_contract.EvidenceEnvelope":
    """Build the evidence envelope for the `/validation/publish` stage boundary.

    Precedence: a canonical status the producer supplied in `canonicalStatuses`
    (Phase 1201) wins outright. Only when none was supplied does the legacy boolean
    discrimination run: an entity's rule id appearing in `failedRuleIds` is a genuine
    evaluated violation (`failed`); appearing in `passedRuleIds` (and not also failed)
    is a genuine evaluated pass (`passed`). Where a rule id is attached to the entity's
    `ruleIds` but present in neither list -- the publish path has no richer outcome for
    it, only the absence of a boolean signal -- the row is emitted as
    `CanonicalStatus.UNKNOWN` with an explanatory warning, per D-04: never guess
    `passed`/`failed` from a missing/collapsed boolean.

    Reading a supplied status is not a D-04 violation: D-04 forbids *inferring* a
    canonical status from a legacy boolean, which is the opposite direction. Before
    Phase 1201 a producer that knew an outcome the boolean pair cannot express
    (`no_population`, `unsupported`, `not_evaluated`, `indeterminate`) had no way to
    say so, and the row degraded to `unknown` -- losing information that already
    existed. An unparseable wire name falls through to the legacy path rather than
    raising, so a malformed entry can never turn a publish into an error.
    """
    rows: list[evidence_contract.EvidenceRow] = []
    for entity in entity_dicts:
        dg_entity_id = entity.get("dgEntityId", "")
        failed_rule_ids = set(entity.get("failedRuleIds") or [])
        passed_rule_ids = set(entity.get("passedRuleIds") or [])
        supplied_statuses = entity.get("canonicalStatuses") or {}
        all_rule_ids = entity.get("ruleIds") or []
        seen_rule_ids = set(all_rule_ids) | failed_rule_ids | passed_rule_ids
        for rule_id in seen_rule_ids:
            supplied = _parse_supplied_canonical_status(supplied_statuses.get(rule_id))
            if supplied is not None:
                status = supplied
                warnings = []
            elif rule_id in failed_rule_ids:
                status = evidence_contract.CanonicalStatus.FAILED
                warnings: list[str] = []
            elif rule_id in passed_rule_ids:
                status = evidence_contract.CanonicalStatus.PASSED
                warnings = []
            else:
                status = evidence_contract.CanonicalStatus.UNKNOWN
                warnings = [
                    f"Rule '{rule_id}' for object '{dg_entity_id}' has no evaluated "
                    "pass/fail outcome from this publish path -- the upstream "
                    "producer has not yet been migrated to emit a canonical status "
                    "(D-04: never inferred from a legacy boolean)."
                ]
            rows.append(
                evidence_contract.EvidenceRow(
                    ruleId=rule_id,
                    objectId=dg_entity_id,
                    canonicalStatus=status,
                    warnings=warnings,
                )
            )

    return evidence_contract.build_envelope(
        project=project,
        definition_id=run_id,
        service_name="data-service",
        service_version=EVIDENCE_SERVICE_VERSION,
        stage="validation.publish",
        rows=rows,
    )


def _persist_shacl_report(project: str, run_id: str, report_json: str) -> None:
    """Persist a SHACL status dict as `shaclReportJson` on the ValidationRun node.

    Additive, second write after `store_validation_run` -- ordering of the
    Speckle publish + store_validation_run is unchanged (D-06). Parameterized
    MERGE/SET keyed by {graph, project, runId}; never string-interpolated.
    """
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET run.shaclReportJson = $shaclReportJson
        """,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "runId": run_id,
            "shaclReportJson": report_json,
        },
    )


# Phase 39 (DSAV-02, P-07): SET the Speckle identifiers in place on a run the
# watcher has ALREADY completed. Same MERGE-key + SET-in-place template as
# _persist_shacl_report, and deliberately the same field names
# store_validation_run writes, so list_validation_runs and build_view_payload
# read an auto-published run identically to a manual one.
AUTO_COMPLETE_PUBLISH_QUERY = """
MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET
    run.speckleProjectId = $speckleProjectId,
    run.baseModelId = $baseModelId,
    run.baseVersionId = $baseVersionId,
    run.validationModelId = $validationModelId,
    run.validationVersionId = $validationVersionId,
    run.modelViewerUrl = $modelViewerUrl,
    run.baseResourceUrl = $baseResourceUrl,
    run.validationResourceUrl = $validationResourceUrl,
    run.SendStatus = true
"""


def _auto_publish_run(
    project: str, run_id: str, valid_status: list[bool] | None = None
) -> dict[str, Any]:
    """Best-effort Speckle publish for an auto-validated run (P-07).

    Ordering is inverted relative to the manual path on purpose. The manual
    `publish_validation` route mints a Speckle version BEFORE persisting and
    404s outright with SPECKLE_CONFIG_MISSING when Speckle is unconfigured. An
    auto-run completes and persists its verdict FIRST, and this adapter is
    reached only afterwards, and only when the per-project `publishEnabled`
    flag is on. Every failure -- missing config, missing write token, Speckle
    unreachable -- is swallowed and reported in the return value; the run stays
    `completed`. That is what makes D-09's persist-only default structural and
    removes the Speckle hard dependency, so auto-validation works on projects
    with no Speckle wiring at all.

    Never raises. Always returns `{"status": "published" | "skipped" | "error",
    ...}` with a `reason` on the non-success branches.

    `valid_status` is accepted but unused: the verdict is already durably on
    the run by the time this is called. It carries a default because
    `dsav_watcher.poll_once` invokes `publish_fn(project, run_id)` with exactly
    two positional arguments.

    The published version is a state-level marker: `rules` and `entities` are
    empty by construction, because a captured DesignState envelope carries no
    per-entity geometry and no failedRuleIds. For D-11 that is precisely the
    Speckle-noise data point being measured, not a missing feature.
    """
    config = get_integration_config(project)
    if config is None:
        # Deliberately NOT falling through to _auto_configure_integration the
        # way the manual route does: D-13 rejects extending that implicit-create
        # precedent, and an auto-run must never silently provision Speckle
        # configuration for a project.
        return {"status": "skipped", "reason": "speckle_config_missing", "runId": run_id}

    settings = get_speckle_settings()
    if not settings.write_token:
        return {"status": "skipped", "reason": "speckle_token_missing", "runId": run_id}

    try:
        config = normalize_speckle_project_config_payload(config)
        client = build_client(settings.internal_url, settings.write_token)
        validation_model_id = get_or_create_validation_model_id(
            client,
            config.speckleProjectId,
            config.validationModelId,
        )
        base_version_id = get_latest_model_version_id(
            client, config.speckleProjectId, config.baseModelId
        )
        publish_result = publish_validation_version(
            settings,
            dg_project=project,
            speckle_project_id=config.speckleProjectId,
            base_model_id=config.baseModelId,
            base_version_id=base_version_id,
            validation_model_id=validation_model_id,
            run_id=run_id,
            rules=[],
            entities=[],
        )

        write_query(
            AUTO_COMPLETE_PUBLISH_QUERY,
            {
                "graph": VALIDATION_GRAPH,
                "project": project,
                "runId": run_id,
                "speckleProjectId": config.speckleProjectId,
                "baseModelId": config.baseModelId,
                "baseVersionId": publish_result["baseVersionId"],
                "validationModelId": publish_result["validationModelId"],
                "validationVersionId": publish_result["validationVersionId"],
                "modelViewerUrl": publish_result["modelViewerUrl"],
                "baseResourceUrl": publish_result["baseResourceUrl"],
                "validationResourceUrl": publish_result["validationResourceUrl"],
            },
        )

        # Persist a newly created validation model id so the next auto-run
        # reuses it, exactly as publish_validation does.
        upsert_integration_config(
            project,
            SpeckleProjectConfigPayload(
                speckleProjectId=config.speckleProjectId,
                baseModelId=config.baseModelId,
                baseModelName=config.baseModelName,
                validationModelId=validation_model_id,
            ),
        )

        return {
            "status": "published",
            "runId": run_id,
            "validationModelId": publish_result["validationModelId"],
            "validationVersionId": publish_result["validationVersionId"],
            "modelViewerUrl": publish_result["modelViewerUrl"],
        }
    except Exception as exc:
        # The verdict is already persisted; a publish failure must not cost the
        # run, and must never propagate into the watcher tick.
        return {"status": "error", "reason": type(exc).__name__, "runId": run_id}


@router.post("/designstate/capture", status_code=202)
def capture_design_state(request: Request, payload: DesignStateCaptureRequest):
    """Accept a DesignState snapshot for later automatic validation (DSAV-02).

    This is Phase 39's only new public surface. It is the simulated-client
    capture path of D-02: driven by curl and pytest, with no Grasshopper
    component wiring and no live Rhino behind it -- the GH-side capture client
    is deferred to a follow-up milestone.

    Authentication is the inline connector-token check of P-01. The token is
    resolved through the connectors module's `authenticate_token`, deliberately
    NOT through its `record_heartbeat`: the latter stamps `last_connection` on
    the credential, which would misrepresent capture traffic as liveness.
    The credential's bound `project` must equal the body's `project` exactly
    (T-39-02) -- no other endpoint accepts a caller-supplied project alongside
    a connector token, so this comparison is new logic, not a borrowed idiom.

    202, not 200: a capture only ever *enqueues* work. Whether it ever produces
    a validation run at all depends on the per-project
    `IntegrationConfig{provider:'AutoValidation'}` row, which is absent -- and
    therefore disabled -- by default (D-13). A capture into a project with no
    such row is accepted, written, and never picked up.
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[len("Bearer "):].strip() if auth_header.startswith("Bearer ") else ""
    record = connectors.authenticate_token(token) if token.startswith(connectors.TOKEN_PREFIX) else None
    if record is None:
        raise _structured_error_response(
            "Invalid or revoked connector token.",
            "Create a new credential via POST /connectors/{connector_id}/credentials.",
            "CONNECTOR_AUTH_FAILED",
            401,
        )

    # T-39-02. The message is deliberately generic (T-39-06): it names neither
    # the credential's bound project nor the requested one, so this endpoint
    # cannot be used to probe which projects exist or which project a stolen
    # token belongs to.
    if (record.get("project") or "default-project") != payload.project:
        raise _structured_error_response(
            "This connector token is not authorized for the requested project.",
            "Create a credential scoped to the project you are capturing into, via "
            "POST /connectors/{connector_id}/credentials.",
            "CAPTURE_PROJECT_MISMATCH",
            403,
        )

    # T-39-07.
    if len(payload.statePayloadJson.encode("utf-8")) > DSAV_MAX_STATE_PAYLOAD_BYTES:
        raise _structured_error_response(
            "Captured DesignState payload is too large.",
            f"Reduce the snapshot below the {DSAV_MAX_STATE_PAYLOAD_BYTES} byte limit, or raise "
            "DSAV_MAX_STATE_PAYLOAD_BYTES on the data-service container.",
            "CAPTURE_PAYLOAD_TOO_LARGE",
            413,
        )

    run_id = uuid.uuid4().hex
    captured_at = datetime.now(timezone.utc).isoformat()

    # All Cypher for this path lives in dsav_watcher, the single writer of
    # CAPTURE_QUERY -- no query is embedded here.
    dsav_watcher.capture_state(
        project=payload.project,
        run_id=run_id,
        state_payload_json=payload.statePayloadJson,
        captured_at=captured_at,
    )

    return DesignStateCaptureResponse(
        runId=run_id,
        project=payload.project,
        status="captured",
        capturedAt=captured_at,
    )


@router.post("/validation/publish")
def publish_validation(payload: ValidationPublishRequest):
    config = get_integration_config(payload.project)
    if config is None:
        config = _auto_configure_integration(payload.project)
    if config is None:
        raise _structured_error_response(
            "No Speckle project configuration found.",
            "Set SPECKLE_PROJECT_ID and SPECKLE_BASE_MODEL_ID environment variables "
            "on the data-service container, or open the project's Speckle Settings card "
            "on the DG home page and save your Speckle project ID.",
            "SPECKLE_CONFIG_MISSING",
            404,
        )
    config = normalize_speckle_project_config_payload(config)

    settings = get_speckle_settings()
    if not settings.write_token:
        raise _structured_error_response(
            "Speckle write token not configured.",
            "Save it in the DG home page Speckle Settings card or set SPECKLE_WRITE_TOKEN on data-service.",
            "SPECKLE_TOKEN_MISSING",
            500,
        )

    try:
        client = build_client(settings.internal_url, settings.write_token)
        validation_model_id = get_or_create_validation_model_id(
            client,
            config.speckleProjectId,
            config.validationModelId,
        )
        base_version_id = get_latest_model_version_id(client, config.speckleProjectId, config.baseModelId)
        run_id = uuid.uuid4().hex
        rules_summary = build_rules_summary(payload)
        entity_dicts: list[dict[str, Any]] = []
        for entity in payload.entities:
            entity_dict = entity.model_dump()
            entity_dict["dgProject"] = payload.project
            entity_dict["validationRunId"] = run_id
            entity_dict["baseModelId"] = config.baseModelId
            entity_dict["baseVersionId"] = base_version_id
            entity_dicts.append(entity_dict)

        publish_result = publish_validation_version(
            settings,
            dg_project=payload.project,
            speckle_project_id=config.speckleProjectId,
            base_model_id=config.baseModelId,
            base_version_id=base_version_id,
            validation_model_id=validation_model_id,
            run_id=run_id,
            rules=rules_summary,
            entities=entity_dicts,
        )
        config = upsert_integration_config(
            payload.project,
            SpeckleProjectConfigPayload(
                speckleProjectId=config.speckleProjectId,
                baseModelId=config.baseModelId,
                baseModelName=config.baseModelName,
                validationModelId=validation_model_id,
            ),
        )
        store_validation_run(
            payload.project,
            run_id,
            config,
            publish_result,
            rules_summary,
            entity_dicts,
            state_payload_json=payload.statePayloadJson,
            valid_status_param=payload.validStatus,
        )

        # SHACL sidecar proxy (Phase 823 Plan 03, D-01/D-02) -- AFTER
        # store_validation_run so the run is already durably recorded; this
        # entire block is non-fatal by construction (_call_shacl_validate
        # never raises) with a defensive outer catch so even a persistence
        # failure can never change the publish response/status.
        try:
            shacl_result = _call_shacl_validate(payload.project, run_id)
            _persist_shacl_report(payload.project, run_id, json.dumps(shacl_result))
        except Exception:
            shacl_result = {"status": "unavailable"}

        # Evidence envelope sidecar (Phase 1200, D-06/D-08) -- additive third write
        # after store_validation_run, following _persist_shacl_report's exact
        # non-fatal shape. A build/validate/persist failure here is logged and
        # swallowed: the envelope degrades to not-recorded, exactly like an absent
        # property, and must never change the publish response/status that was
        # working before this phase.
        try:
            envelope = _build_publish_evidence_envelope(payload.project, run_id, entity_dicts)
            evidence_contract.validate_envelope(envelope)
            persist_evidence_envelope(
                payload.project, run_id, envelope.model_dump_json(exclude_none=True)
            )
        except Exception:
            logging.getLogger(__name__).warning(
                "Evidence envelope build/validate/persist failed for run %s -- "
                "degrading to not-recorded (D-08).",
                run_id,
                exc_info=True,
            )

        return {
            "status": "published",
            "runId": run_id,
            "validationModelId": publish_result["validationModelId"],
            "validationVersionId": publish_result["validationVersionId"],
            "baseVersionId": publish_result["baseVersionId"],
            "modelViewerUrl": publish_result["modelViewerUrl"],
            "shacl": shacl_result,
        }
    except SpeckleValidationError as exc:
        raise _structured_error_response(
            f"Validation publish failed: {exc}",
            "Check that Speckle server is reachable and project ID is correct.",
            "PUBLISH_VALIDATION_ERROR",
            400,
        ) from exc
    except Exception as exc:
        raise _structured_error_response(
            f"Validation publish failed: {exc}",
            "Check data-service logs for details.",
            "PUBLISH_INTERNAL_ERROR",
            500,
        ) from exc


@router.get("/validation/runs/{project}")
def get_validation_runs(project: str):
    return {"project": project, "runs": list_validation_runs(project)}


@router.delete("/validation/run/{project}/{run_id}")
def delete_validation_run(project: str, run_id: str):
    run = get_validation_run(project, run_id)
    if run is None:
        raise _structured_error_response(
            "Validation run not found.",
            "Verify the run ID exists for this project.",
            "RUN_NOT_FOUND",
            404,
        )

    settings = get_speckle_settings()
    if not settings.write_token:
        raise _structured_error_response(
            "Speckle write token not configured.",
            "Save it in the DG home page Speckle Settings card or set SPECKLE_WRITE_TOKEN on data-service.",
            "SPECKLE_TOKEN_MISSING",
            500,
        )

    validation_version_id = (run.get("validationVersionId") or "").strip()
    speckle_project_id = (run.get("speckleProjectId") or "").strip()
    if not validation_version_id or not speckle_project_id:
        raise _structured_error_response(
            "Validation run is missing Speckle identifiers required for deletion.",
            "This run may have been created before Speckle integration was configured.",
            "SPECKLE_IDS_MISSING",
            500,
        )

    try:
        delete_validation_version(
            settings,
            speckle_project_id=speckle_project_id,
            validation_version_id=validation_version_id,
        )
        delete_validation_run_metadata(project, run_id)
        return {
            "status": "deleted",
            "project": project,
            "runId": run_id,
            "validationModelId": run.get("validationModelId"),
            "validationVersionId": validation_version_id,
        }
    except SpeckleValidationError as exc:
        raise _structured_error_response(
            f"Validation delete failed: {exc}",
            "Check that Speckle server is reachable and project ID is correct.",
            "DELETE_VALIDATION_ERROR",
            400,
        ) from exc
    except Exception as exc:
        raise _structured_error_response(
            f"Validation delete failed: {exc}",
            "Check data-service logs for details.",
            "DELETE_INTERNAL_ERROR",
            500,
        ) from exc


@router.get("/validation/view/{project}")
def get_latest_validation_view(project: str):
    run = get_validation_run(project)
    if run is None:
        raise HTTPException(status_code=404, detail="No validation run found for this DG project.")

    object_sets = get_validation_entity_sets(project, run["runId"])
    return build_view_payload(project, run, object_sets)


@router.get("/validation/view/{project}/{run_id}")
def get_validation_view_for_run(project: str, run_id: str):
    run = get_validation_run(project, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")

    object_sets = get_validation_entity_sets(project, run_id)
    return build_view_payload(project, run, object_sets)


@router.get("/validation/view/{project}/{run_id}/{rule_id}")
def get_rule_validation_view(project: str, run_id: str, rule_id: str):
    run = get_validation_run(project, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")

    object_sets = get_validation_entity_sets(project, run_id, rule_id)
    return build_view_payload(project, run, object_sets, rule_id=rule_id)


@router.post("/mcp")
async def mcp(request: Request):
    payload = await request.json()
    method = payload.get("method")
    req_id = payload.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "neo4j_schema",
                        "description": "Return Neo4j labels, relationship types, property keys, graphs, and projects.",
                    },
                    {
                        "name": "neo4j_query",
                        "description": "Run a read-only Cypher query and return records.",
                    },
                    {
                        "name": "gh_get_context",
                        "description": "Return the live Grasshopper canvas as cgContextJson v1.",
                    },
                    {
                        "name": "gh_get_selection",
                        "description": "Return currently-selected object instance GUIDs.",
                    },
                    {
                        "name": "gh_preview_structure",
                        "description": "Preview a proposed Computgraph structure on the canvas (stub in v9.0).",
                    },
                    {
                        "name": "gh_clear_preview",
                        "description": "Clear any active canvas preview (stub in v9.0).",
                    },
                ]
            },
        }

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "neo4j-mcp", "version": "1.0"},
            },
        }

    if method != "tools/call":
        raise HTTPException(status_code=400, detail="Unsupported MCP method")

    params = payload.get("params") or {}
    tool_name = params.get("name")
    arguments = params.get("arguments") or {}

    if tool_name == "neo4j_schema":
        with driver.session() as session:
            labels = session.run("CALL db.labels()").value()
            rels = session.run("CALL db.relationshipTypes()").value()
            props = session.run("CALL db.propertyKeys()").value()
            graphs = session.run("MATCH (n) WHERE n.graph IS NOT NULL RETURN DISTINCT n.graph AS graph").value()
            projects = session.run("MATCH (n) WHERE n.project IS NOT NULL RETURN DISTINCT n.project AS project").value()
        data = {
            "labels": labels,
            "relationship_types": rels,
            "property_keys": props,
            "graphs": graphs,
            "projects": projects,
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "schema"}], "data": data},
        }

    if tool_name == "neo4j_query":
        cypher = (arguments.get("cypher") or "").strip()
        parameters = arguments.get("parameters") or {}
        if not cypher:
            raise HTTPException(status_code=400, detail="cypher is required")
        if is_write_query(cypher):
            raise HTTPException(status_code=400, detail="Only read-only Cypher is allowed")
        with driver.session() as session:
            result = session.run(cypher, parameters)
            keys = result.keys()
            records = [normalize_value(record.data()) for record in result]
        data = {"keys": keys, "records": records}
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "query"}], "data": data},
        }

    # The gh_bridge calls below do blocking socket I/O (5 s connect + 30 s read
    # worst case); /mcp is an async handler on the event loop, so they must run
    # in the threadpool or a hung listener freezes the whole service (WR-05).
    if tool_name == "gh_get_context":
        project = arguments.get("project", "")
        # raises _structured_error_response internally on failure
        context = await run_in_threadpool(gh_bridge.get_canvas_context, project)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "context"}], "data": context},
        }

    if tool_name == "gh_get_selection":
        selection = await run_in_threadpool(gh_bridge.get_selection)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "selection"}], "data": selection},
        }

    if tool_name == "gh_preview_structure":
        preview = await run_in_threadpool(gh_bridge.preview_structure, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "preview"}], "data": preview},
        }

    if tool_name == "gh_clear_preview":
        cleared = await run_in_threadpool(gh_bridge.clear_preview)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "preview-cleared"}], "data": cleared},
        }

    raise HTTPException(status_code=400, detail="Unknown tool name")


@router.post("/execution-result")
def store_execution_result(result: ExecutionResult):
    entry = {
        "status": result.status,
        "payload": result.payload or {},
    }
    if result.step is not None:
        entry["step"] = result.step
    if result.progress is not None:
        entry["progress"] = result.progress
    if result.message is not None:
        entry["message"] = result.message
    EXECUTION_RESULTS[result.executionId] = entry
    return {"status": "ok"}


@router.get("/execution-result/{execution_id}")
def get_execution_result(execution_id: str):
    # Phase 1205 (D-04, T-1205-10-03): only the user who started the execution
    # reaches this handler (the "execution" resolver answers everyone else with
    # EXECUTION_NOT_FOUND). An owned id with no result yet is still running.
    return EXECUTION_RESULTS.get(execution_id, {"status": "running"})


# ── Workflow relay (Phase 1205, D-08) ───────────────────────────────────────
#
# The browser no longer calls the n8n webhooks directly. These two routes are
# the only path from a signed-in user to a workflow: project-authorised by the
# route policy, relayed over the internal network with the service token, and
# owner-bound (the initiator is recorded before the 202 so only they can poll
# GET /execution-result/{executionId}). The n8n body is built from the
# validated request model only -- never from raw request data.


class WorkflowRulesIngestRequest(BaseModel):
    project: str = Field(min_length=1)
    rulesText: str = Field(min_length=1, max_length=20000)


class WorkflowGraphQueryRequest(BaseModel):
    project: str = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=4000)


def _relay_workflow(
    request: Request, workflow: str, webhook_path: str, project: str, body: dict
) -> dict:
    principal = getattr(request.state, "principal", None)
    username = getattr(principal, "username", None)
    if not username:
        raise _structured_error_response(
            "A signed-in user is required to start a workflow.",
            "Sign in and retry.",
            "RELAY_USER_REQUIRED",
            403,
        )
    execution_id = fire_n8n_webhook(webhook_path, body)
    # Bind the execution to its initiator BEFORE answering, so the owner's own
    # first poll never races the recording.
    record_execution_owner(execution_id, username, project, workflow)
    return {"status": "accepted", "executionId": execution_id}


@router.post("/workflows/rules-ingest", status_code=202)
def relay_rules_ingest(payload: WorkflowRulesIngestRequest, request: Request):
    return _relay_workflow(
        request,
        "rules-ingest",
        "dg/rules-ingest",
        payload.project,
        {
            "rules_text": payload.rulesText,
            "project": payload.project,
            "project_name": payload.project,
            "cypher_prompt": False,
        },
    )


@router.post("/workflows/graph-query", status_code=202)
def relay_graph_query(payload: WorkflowGraphQueryRequest, request: Request):
    return _relay_workflow(
        request,
        "graph-query",
        "dg/graph-query",
        payload.project,
        {
            "prompt": payload.prompt,
            "project": payload.project,
            "project_name": payload.project,
            "cypher_prompt": False,
        },
    )


MAX_FILE_SIZE = 100 * 1024  # 100KB


@router.post("/knowledge/ingest/folder")
def ingest_folder(payload: FolderIngestRequest):
    root = validate_ingest_path(payload.path)
    md_files = list(root.rglob("*.md"))
    repo_root = KNOWLEDGE_REPO_ROOT.resolve()

    inserted = 0
    skipped = 0
    skipped_hidden: list[dict[str, str]] = []
    hidden_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for md_file in md_files:
        # Phase 1205 (T-1205-10-05): the mounted repository holds `.secrets/`,
        # `.env*`, `.git/`, `.claude/` ... Any file below a path segment that
        # begins with a dot is never read.
        # Measured against the repository root (a superset of the requested
        # folder's own segments), so `path=".secrets"` is refused too.
        try:
            rel_parts = md_file.relative_to(repo_root).parts
        except ValueError:
            rel_parts = md_file.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts):
            skipped += 1
            hidden_count += 1
            if len(skipped_hidden) < 50:
                skipped_hidden.append(
                    {"path": "/".join(rel_parts), "reason": "hidden-path"}
                )
            continue
        try:
            if md_file.stat().st_size > MAX_FILE_SIZE:
                skipped += 1
                continue

            title, content = extract_title_from_md(md_file)
            tags = extract_frontmatter_tags(content)
            relative_path = str(md_file.relative_to(KNOWLEDGE_REPO_ROOT))
            note_id = generate_note_id(payload.project, relative_path)

            # MERGE note (idempotent: re-ingest updates, not duplicates)
            write_query(
                "MERGE (n:SpecNote {noteId: $noteId, project: $project, graph: $graph}) "
                "SET n.title = $title, n.content = $content, n.source = $source, "
                "    n.tags = $tags, "
                "    n.createdAt = coalesce(n.createdAt, $now), n.updatedAt = $now",
                {
                    "noteId": note_id,
                    "project": payload.project,
                    "graph": SPEC_GRAPH,
                    "title": title,
                    "content": content,
                    "source": relative_path,
                    "tags": tags,
                    "now": now,
                },
            )

            # Connect to parent class node
            write_query(
                "MATCH (n:SpecNote {noteId: $noteId, project: $project, graph: $graph}) "
                "MERGE (c:SpecClass {name: 'SpecNote', graph: $graph}) "
                "MERGE (n)-[:INSTANCE_OF]->(c)",
                {
                    "noteId": note_id,
                    "project": payload.project,
                    "graph": SPEC_GRAPH,
                },
            )

            # Create SpecTag nodes and TAGGED_WITH relationships
            for tag in tags:
                write_query(
                    "MERGE (t:SpecTag {name: $tagName, project: $project, graph: $graph}) "
                    "WITH t "
                    "MATCH (n:SpecNote {noteId: $noteId, project: $project, graph: $graph}) "
                    "MERGE (n)-[:TAGGED_WITH]->(t)",
                    {
                        "tagName": tag,
                        "project": payload.project,
                        "graph": SPEC_GRAPH,
                        "noteId": note_id,
                    },
                )

            inserted += 1
        except UnicodeDecodeError:
            skipped += 1
        except Exception:
            skipped += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "skippedHidden": hidden_count,
        "skippedFiles": skipped_hidden,
    }


# ---------------------------------------------------------------------------
# Knowledge CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/knowledge/notes/{project}")
def list_knowledge_notes(project: str):
    rows = read_many(
        "MATCH (n:SpecNote {project: $project, graph: $graph}) "
        "RETURN n.noteId AS noteId, n.title AS title, n.source AS source, "
        "       n.createdAt AS createdAt, n.updatedAt AS updatedAt "
        "ORDER BY n.updatedAt DESC",
        {"project": project, "graph": SPEC_GRAPH},
    )
    return {"project": project, "notes": rows}


@router.get("/knowledge/note/{note_id}")
def get_knowledge_note(note_id: str):
    row = read_single(
        "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) "
        "RETURN n.noteId AS noteId, n.title AS title, n.content AS content, "
        "       n.source AS source, n.tags AS tags, n.project AS project, "
        "       n.createdAt AS createdAt, n.updatedAt AS updatedAt",
        {"noteId": note_id, "graph": SPEC_GRAPH},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return row


@router.put("/knowledge/note/{note_id}")
def update_knowledge_note(note_id: str, payload: NoteUpdateRequest):
    existing = read_single(
        "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) RETURN n.noteId AS noteId",
        {"noteId": note_id, "graph": SPEC_GRAPH},
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Note not found")

    set_clauses = ["n.updatedAt = $now"]
    params: dict[str, Any] = {
        "noteId": note_id,
        "graph": SPEC_GRAPH,
        "now": datetime.now(timezone.utc).isoformat(),
    }
    if payload.title is not None:
        set_clauses.append("n.title = $title")
        params["title"] = payload.title
    if payload.content is not None:
        set_clauses.append("n.content = $content")
        params["content"] = payload.content
    if payload.tags is not None:
        set_clauses.append("n.tags = $tags")
        params["tags"] = payload.tags

    write_query(
        f"MATCH (n:SpecNote {{noteId: $noteId, graph: $graph}}) SET {', '.join(set_clauses)}",
        params,
    )
    return {"status": "updated", "noteId": note_id}


@router.delete("/knowledge/note/{note_id}")
def delete_knowledge_note(note_id: str):
    existing = read_single(
        "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) RETURN n.noteId AS noteId",
        {"noteId": note_id, "graph": SPEC_GRAPH},
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Note not found")

    write_query(
        "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) DETACH DELETE n",
        {"noteId": note_id, "graph": SPEC_GRAPH},
    )
    return {"status": "deleted", "noteId": note_id}


# ---------------------------------------------------------------------------
# Rule deletion (Rule + its Atoms + ORPHANED Literal/Var)
# ---------------------------------------------------------------------------
#
# Literal and Var nodes are SHARED across rules by design -- MERGE on `lex`/
# `name` means the Literal 'true' and the Var '?b' are single nodes every rule
# points at. Measured on a live project: deleting one height rule would orphan
# Literal '75' (0 other referrers) but Literal 'true' had 12 referrers and Var
# '?b' had 6. Deleting shared args unconditionally silently breaks every other
# rule, so both the preview and the delete count referrers first and touch only
# what nothing else points at.
#
# The delete runs as fixed, parameterized Cypher here -- the LLM never writes
# the destructive statement, it only resolves which Rule_Id the user meant.

_RULE_DELETE_SCOPE = (
    "MATCH (r:Rule {Rule_Id: $ruleId, project: $project}) "
    "OPTIONAL MATCH (r)-[:HAS_BODY|HAS_HEAD]->(a:Atom) "
    "OPTIONAL MATCH (a)-[:ARG]->(x) WHERE x:Literal OR x:Var "
)


def _rule_delete_preview(project: str, rule_id: str) -> dict[str, Any] | None:
    """What deleting `rule_id` would remove. None when the rule does not exist.

    `orphaned` args are referenced by no OTHER rule and will be deleted;
    `shared` args stay because another rule still points at them.
    """
    exists = read_single(
        "MATCH (r:Rule {Rule_Id: $ruleId, project: $project}) RETURN r.Rule_Id AS ruleId",
        {"ruleId": rule_id, "project": project},
    )
    if exists is None:
        return None

    atoms = read_many(
        _RULE_DELETE_SCOPE + "RETURN DISTINCT a.Atom_Id AS atomId, a.SWRL_label AS swrlLabel",
        {"ruleId": rule_id, "project": project},
    )
    args = read_many(
        _RULE_DELETE_SCOPE
        + "WITH DISTINCT x, r WHERE x IS NOT NULL "
        "WITH x, r, count { (other:Rule)-[:HAS_BODY|HAS_HEAD]->(:Atom)-[:ARG]->(x) "
        "                   WHERE other <> r } AS otherRefs "
        "RETURN labels(x)[0] AS label, coalesce(x.lex, x.name) AS value, otherRefs "
        "ORDER BY label, value",
        {"ruleId": rule_id, "project": project},
    )

    return {
        "project": project,
        "ruleId": rule_id,
        "atoms": [a for a in atoms if a.get("atomId") is not None],
        "orphaned": [a for a in args if (a.get("otherRefs") or 0) == 0],
        "shared": [a for a in args if (a.get("otherRefs") or 0) > 0],
    }


@router.get("/rules/{project}/{rule_id}/delete-preview")
def preview_rule_deletion(project: str, rule_id: str):
    """Exactly what a delete would remove -- the confirmation dialog's source.

    Read-only: call it, show the user, and only then call DELETE.
    """
    preview = _rule_delete_preview(project, rule_id)
    if preview is None:
        raise _structured_error_response(
            f"Rule '{rule_id}' not found in project '{project}'.",
            "Check the Rule_Id; it is case-sensitive.",
            "RULE_NOT_FOUND",
            404,
        )
    return preview


@router.delete("/rules/{project}/{rule_id}")
def delete_rule(project: str, rule_id: str):
    """Delete a Rule, its Atoms, and any Literal/Var left orphaned by that.

    Destructive and not undoable -- callers confirm with the user first
    (the preview endpoint above exists for that).
    """
    preview = _rule_delete_preview(project, rule_id)
    if preview is None:
        raise _structured_error_response(
            f"Rule '{rule_id}' not found in project '{project}'.",
            "Check the Rule_Id; it is case-sensitive.",
            "RULE_NOT_FOUND",
            404,
        )

    # Orphan check runs inside the same statement as the delete: computing it
    # here from the preview would race another ingest writing a rule that
    # starts referencing one of these args between the two calls.
    write_query(
        _RULE_DELETE_SCOPE
        + "WITH r, collect(DISTINCT a) AS atoms, collect(DISTINCT x) AS args "
        "UNWIND (CASE WHEN args = [] THEN [null] ELSE args END) AS arg "
        "WITH r, atoms, arg WHERE arg IS NULL OR NOT EXISTS { "
        "    MATCH (other:Rule)-[:HAS_BODY|HAS_HEAD]->(:Atom)-[:ARG]->(arg) "
        "    WHERE other <> r } "
        "WITH r, atoms, collect(arg) AS orphans "
        "FOREACH (n IN atoms | DETACH DELETE n) "
        "FOREACH (n IN orphans | DETACH DELETE n) "
        "DETACH DELETE r",
        {"ruleId": rule_id, "project": project},
    )

    return {
        "status": "deleted",
        "project": project,
        "ruleId": rule_id,
        "deletedAtoms": len(preview["atoms"]),
        "deletedArgs": len(preview["orphaned"]),
        "keptSharedArgs": len(preview["shared"]),
    }


class RuleDeleteResolvePayload(BaseModel):
    project: str
    request: str


@router.post("/rules/resolve-deletion")
def resolve_rule_deletion(payload: RuleDeleteResolvePayload):
    """Resolve a natural-language deletion request to concrete Rule_Ids, with a
    per-rule preview of what removing each would take with it.

    Selection only -- deletes nothing. The LLM picks WHICH rules match (it
    never writes Cypher); DELETE below removes them with fixed parameterized
    statements. An invented Rule_Id cannot match a real rule, and comes back
    under `hallucinated` so the caller can show it rather than act on it.
    """
    request_text = (payload.request or "").strip()
    if not request_text:
        raise _structured_error_response(
            "Deletion request is empty.",
            "Describe which rules to delete, e.g. 'all height rules above 50 m'.",
            "REQUEST_EMPTY",
            422,
        )

    try:
        selection = dg_context.select_rules_for_deletion(payload.project, request_text)
    except Exception as exc:  # provider/auth/network failure
        error_msg, hint, code = map_provider_error(exc)
        raise _structured_error_response(error_msg, hint, code, 502) from exc

    matches = []
    for rule in selection["matched"]:
        preview = _rule_delete_preview(payload.project, rule["ruleId"])
        if preview is None:
            continue  # deleted between selection and preview
        matches.append({**preview, "swrl": rule.get("swrl", ""), "description": rule.get("description", "")})

    return {
        "project": payload.project,
        "request": request_text,
        "reason": selection["reason"],
        "hallucinated": selection["hallucinated"],
        "matches": matches,
    }


class RuleBulkDeletePayload(BaseModel):
    project: str
    ruleIds: list[str]


@router.post("/rules/bulk-delete")
def bulk_delete_rules(payload: RuleBulkDeletePayload):
    """Delete an explicit list of Rule_Ids the user has confirmed.

    Takes ids, never a natural-language request: the confirmation the user gave
    was against a resolved list, so this endpoint re-deletes exactly that list
    and nothing it re-derives on its own. Each id goes through the same
    single-rule path, so the orphan rule is applied per rule and in order --
    an arg shared only between two rules in the same batch is correctly
    orphaned by the time the second one is removed.
    """
    if not payload.ruleIds:
        raise _structured_error_response(
            "No rules given to delete.",
            "Pass the ruleIds confirmed from /rules/resolve-deletion.",
            "REQUEST_EMPTY",
            422,
        )

    deleted: list[dict[str, Any]] = []
    missing: list[str] = []
    for rule_id in payload.ruleIds:
        try:
            deleted.append(delete_rule(payload.project, rule_id))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if detail.get("code") == "RULE_NOT_FOUND":
                missing.append(rule_id)
                continue
            raise

    return {
        "status": "deleted",
        "project": payload.project,
        "deleted": deleted,
        "missing": missing,
        "deletedRules": len(deleted),
    }


# ---------------------------------------------------------------------------
# Rule ingest conflict check (debug session rule-ingest-no-conflict-check,
# 2026-09-19) -- the missing preview/confirm stage of paper T1 ITcon R15.6
# §4's five-stage authoring process (tag -> recognise -> preview -> confirm
# -> publish). The UI calls this endpoint BEFORE POSTing to the n8n
# rules-ingest webhook; n8n and its workflow are unmodified (Decision 1).
#
# Deliberately synchronous and LLM-free (unlike deletion's select_rules_for_
# deletion): the conflict key -- (Class, DatatypeProperty, comparator) -- is
# a deterministic grounding fact per paper [P138], resolved by
# dg_context.check_rule_conflict() against this project's own known
# vocabulary. See that function's docstring for the ambiguity policy: an
# unresolved grounding always reports "no conflict", never guesses.
# ---------------------------------------------------------------------------


class RuleConflictCheckPayload(BaseModel):
    project: str
    rules_text: str


@router.post("/rules/check-conflict")
def check_rule_conflict(payload: RuleConflictCheckPayload):
    """Preview stage: does `rules_text` collide with a Rule already in the
    project's corpus? Read-only -- writes nothing, matching the read-only
    contract of /rules/resolve-deletion above.
    """
    rules_text = (payload.rules_text or "").strip()
    if not rules_text:
        raise _structured_error_response(
            "rules_text is empty.",
            "Provide the natural-language rule text to check.",
            "REQUEST_EMPTY",
            422,
        )

    return dg_context.check_rule_conflict(payload.project, rules_text)


# ---------------------------------------------------------------------------
# Rule supersession (Decision 3: Replace/Update never deletes). A
# SUPERSEDED_BY edge (old -> new) plus provenance is recorded on the OLD
# rule; the NEW rule is authored through the normal ingest path (unchanged)
# immediately afterward by the caller (ui-v2), or -- for "Keep both" -- the
# new rule is authored with no supersede edge at all, just a provenance flag
# recording that the architect knowingly accepted the overlap.
#
# Schema change: SUPERSEDED_BY is a new Metagraph relationship type. Per
# CLAUDE.md's Schema Change Propagation list this also touches
# spec/DATABASE.md, ontology/dg-shapes.ttl, cypher_template.txt,
# training/dataset_schema.json, .github/copilot-instructions.md, README.md
# (updated alongside this change, not deferred).
#
# Superseded-rule exclusion is enforced in THREE places, not just here:
#   1. This endpoint's own precondition check (a rule cannot supersede, or
#      be superseded by, an already-superseded rule -- no chains-of-chains
#      ambiguity).
#   2. dg_context._RULE_CONFLICT_QUERY (WHERE NOT EXISTS SUPERSEDED_BY) --
#      so a past revision does not collide with itself forever.
#   3. DG.Core.Data.Neo4jRuleRepository.RulesQuery (C#, the SWRL VALIDATOR's
#      own rule-corpus loader) -- see that file's diff; a superseded rule
#      that stayed visible there would still fire at validation time,
#      reproducing the exact bug this fix closes in a new form.
# ---------------------------------------------------------------------------


# Publishability precondition (debug session rule-ingest-no-conflict-check,
# UAT round 2, 2026-09-19): live browser UAT found that Rule_Id existence
# alone is NOT proof a rule is safe to hand enforcement over to. A real n8n
# ingest wrote a structurally-shaped Rule (correct HAS_BODY/HAS_HEAD/order)
# that was nonetheless untagged -- no `graph:'Metagraph'` on the Rule node,
# no `graph`/`SWRL_label` on any of its Atoms. supersede_rule()'s old
# precondition (`MATCH (r:Rule {Rule_Id: ..., project: ...})`) matched this
# stub happily, created the SUPERSEDED_BY edge, and the project was left
# with NO enforceable rule at all: the old rule was excluded from the SWRL
# VALIDATOR's corpus by the new supersession filter (working as designed),
# while the "replacement" was ALSO invisible to that same corpus query
# (Neo4jRuleRepository.RulesQuery matches on `graph:'Metagraph'`) --
# strictly worse than the original silent-duplicate-rules bug.
#
# This query checks exactly the three things Neo4jRuleRepository.RulesQuery/
# AtomsQuery (C#) actually require for a rule to be visible and evaluable:
# the Rule itself tagged Metagraph, at least one HAS_BODY atom, at least one
# HAS_HEAD atom, and EVERY one of those atoms also tagged Metagraph (a rule
# with a correctly-tagged Rule node but untagged atoms is just as invisible
# to AtomsQuery as one with no atoms at all -- this is what the real UAT
# case hit).
_RULE_PUBLISHABILITY_QUERY = """
MATCH (r:Rule {Rule_Id: $ruleId, project: $project})
OPTIONAL MATCH (r)-[:HAS_BODY]->(bodyAtom:Atom)
OPTIONAL MATCH (r)-[:HAS_HEAD]->(headAtom:Atom)
RETURN
    coalesce(r.graph, '') = 'Metagraph' AS ruleTagged,
    count(DISTINCT bodyAtom) AS bodyAtomCount,
    count(DISTINCT headAtom) AS headAtomCount,
    count(DISTINCT bodyAtom) + count(DISTINCT headAtom)
        - count(DISTINCT CASE WHEN coalesce(bodyAtom.graph, '') = 'Metagraph' THEN bodyAtom END)
        - count(DISTINCT CASE WHEN coalesce(headAtom.graph, '') = 'Metagraph' THEN headAtom END)
        AS untaggedAtomCount
"""


def _require_publishable_rule(rule_id: str, project: str) -> None:
    """Raise a structured 409 (RULE_NOT_PUBLISHABLE) naming the first failed
    precondition if `rule_id` is not safe to let take over enforcement from
    another rule. Raises nothing (returns normally) if the rule is
    publishable. Never partially applies anything -- purely a read-only
    check, called BEFORE any write in supersede_rule().
    """
    row = read_single(_RULE_PUBLISHABILITY_QUERY, {"ruleId": rule_id, "project": project})
    # row is None only if the Rule itself doesn't exist -- callers already
    # checked existence before calling this, but fail closed defensively.
    if row is None or not row.get("ruleTagged"):
        raise _structured_error_response(
            f"Rule '{rule_id}' cannot supersede another rule: it is not tagged graph:'Metagraph'.",
            "Re-ingest or manually tag this rule with graph:'Metagraph' before it can take over "
            "enforcement -- an untagged rule is invisible to the SWRL VALIDATOR's rule corpus.",
            "RULE_NOT_PUBLISHABLE",
            409,
        )
    if not row.get("bodyAtomCount"):
        raise _structured_error_response(
            f"Rule '{rule_id}' cannot supersede another rule: it has no HAS_BODY atoms.",
            "Re-ingest this rule -- a rule with no body atoms can never evaluate to a violation.",
            "RULE_NOT_PUBLISHABLE",
            409,
        )
    if not row.get("headAtomCount"):
        raise _structured_error_response(
            f"Rule '{rule_id}' cannot supersede another rule: it has no HAS_HEAD atoms.",
            "Re-ingest this rule -- a rule with no head atom can never set a violation flag.",
            "RULE_NOT_PUBLISHABLE",
            409,
        )
    if row.get("untaggedAtomCount"):
        raise _structured_error_response(
            f"Rule '{rule_id}' cannot supersede another rule: "
            f"{row['untaggedAtomCount']} of its atoms are not tagged graph:'Metagraph'.",
            "Re-ingest this rule, or manually tag its Atom nodes with graph:'Metagraph' -- "
            "an untagged atom is invisible to the SWRL VALIDATOR even if the Rule node itself "
            "is correctly tagged.",
            "RULE_NOT_PUBLISHABLE",
            409,
        )


class RuleSupersedePayload(BaseModel):
    project: str
    oldRuleId: str
    newRuleId: str
    prompt: str = ""
    actor: str = ""


@router.post("/rules/supersede")
def supersede_rule(payload: RuleSupersedePayload):
    """Record that `newRuleId` supersedes `oldRuleId`. Call this AFTER the
    new rule has been written by the normal ingest path (n8n rules-ingest),
    so both Rule nodes exist when the edge is created.

    Idempotent: re-running with the same pair is a no-op MERGE, not an
    error, so a retried request after a network blip does not create a
    duplicate edge or double-write provenance.

    Refuses (409 RULE_NOT_PUBLISHABLE, see `_require_publishable_rule()`) if
    `newRuleId` exists but is not actually usable by the SWRL VALIDATOR --
    missing `graph:'Metagraph'` on the Rule and/or its atoms, or missing
    HAS_BODY/HAS_HEAD atoms entirely. This precondition exists BECAUSE a
    real n8n ingest can produce exactly this: a Rule_Id that exists and has
    correctly-ordered atoms, but with none of it tagged. Without this check,
    supersession would exclude the old (working) rule from the validator
    corpus while its "replacement" stays invisible to that same corpus --
    net loss of enforcement, strictly worse than not superseding at all.
    The old rule is NEVER touched until this check passes; nothing is
    partially applied.
    """
    old_id = (payload.oldRuleId or "").strip()
    new_id = (payload.newRuleId or "").strip()
    if not old_id or not new_id:
        raise _structured_error_response(
            "oldRuleId and newRuleId are both required.",
            "Pass the Rule_Id being replaced and the Rule_Id of its replacement.",
            "REQUEST_EMPTY",
            422,
        )
    if old_id == new_id:
        raise _structured_error_response(
            f"oldRuleId and newRuleId are the same ('{old_id}').",
            "A rule cannot supersede itself.",
            "SUPERSEDE_SELF",
            422,
        )

    old_rule = read_single(
        "MATCH (r:Rule {Rule_Id: $ruleId, project: $project}) "
        "RETURN r.Rule_Id AS ruleId, "
        "EXISTS { (r)-[:SUPERSEDED_BY]->() } AS alreadySuperseded",
        {"ruleId": old_id, "project": payload.project},
    )
    if old_rule is None:
        raise _structured_error_response(
            f"Rule '{old_id}' not found in project '{payload.project}'.",
            "Check the Rule_Id; it is case-sensitive.",
            "RULE_NOT_FOUND",
            404,
        )
    if old_rule.get("alreadySuperseded"):
        raise _structured_error_response(
            f"Rule '{old_id}' has already been superseded.",
            "Refresh the conflict check -- it should now point at the current rule, not this one.",
            "ALREADY_SUPERSEDED",
            409,
        )

    new_rule = read_single(
        "MATCH (r:Rule {Rule_Id: $ruleId, project: $project}) RETURN r.Rule_Id AS ruleId",
        {"ruleId": new_id, "project": payload.project},
    )
    if new_rule is None:
        raise _structured_error_response(
            f"Rule '{new_id}' not found in project '{payload.project}'.",
            "Author the replacement rule first (normal ingest), then call this endpoint.",
            "RULE_NOT_FOUND",
            404,
        )

    _require_publishable_rule(new_id, payload.project)

    now = datetime.now(timezone.utc).isoformat()
    write_query(
        "MATCH (old:Rule {Rule_Id: $oldId, project: $project}) "
        "MATCH (new:Rule {Rule_Id: $newId, project: $project}) "
        "MERGE (old)-[s:SUPERSEDED_BY]->(new) "
        "SET s.supersededAt = $supersededAt, s.actor = $actor, s.prompt = $prompt",
        {
            "oldId": old_id,
            "newId": new_id,
            "project": payload.project,
            "supersededAt": now,
            "actor": (payload.actor or "").strip(),
            "prompt": (payload.prompt or "").strip()[:2000],
        },
    )

    return {
        "status": "superseded",
        "project": payload.project,
        "oldRuleId": old_id,
        "newRuleId": new_id,
        "supersededAt": now,
    }


class RuleAcceptOverlapPayload(BaseModel):
    project: str
    ruleId: str
    conflictsWith: list[str] = Field(default_factory=list)
    actor: str = ""


@router.post("/rules/accept-overlap")
def accept_rule_overlap(payload: RuleAcceptOverlapPayload):
    """'Keep both' provenance: record that the architect knowingly authored
    `ruleId` despite it overlapping with `conflictsWith`, without superseding
    anything. Call AFTER the new rule has been written by the normal ingest
    path.

    Deliberately NOT given the same publishability precondition as
    supersede_rule() (debug session rule-ingest-no-conflict-check, UAT round
    2): this endpoint never disarms anything -- it only SETs provenance
    properties on the new rule itself and creates no SUPERSEDED_BY edge, so
    a malformed new rule degrades to the pre-existing "malformed rule is
    invisible to the validator" gap (already tracked as a separate,
    out-of-scope follow-up), never to "the OLD rule stops being enforced."
    The two endpoints have different blast radii by design.

    This does not gate or block anything -- it is a provenance annotation
    only (paper [P129]/[P139]: "approved results are recorded in the
    project graph together with provenance"), so a future audit can
    distinguish "two rules overlap because nobody noticed" from "two rules
    overlap because an architect reviewed the conflict and chose to keep
    both".
    """
    rule_id = (payload.ruleId or "").strip()
    if not rule_id:
        raise _structured_error_response(
            "ruleId is required.",
            "Pass the Rule_Id of the newly authored rule.",
            "REQUEST_EMPTY",
            422,
        )

    rule = read_single(
        "MATCH (r:Rule {Rule_Id: $ruleId, project: $project}) RETURN r.Rule_Id AS ruleId",
        {"ruleId": rule_id, "project": payload.project},
    )
    if rule is None:
        raise _structured_error_response(
            f"Rule '{rule_id}' not found in project '{payload.project}'.",
            "Author the rule first (normal ingest), then call this endpoint.",
            "RULE_NOT_FOUND",
            404,
        )

    now = datetime.now(timezone.utc).isoformat()
    write_query(
        "MATCH (r:Rule {Rule_Id: $ruleId, project: $project}) "
        "SET r.acceptedOverlapWith = $conflictsWith, "
        "    r.acceptedOverlapAt = $acceptedAt, "
        "    r.acceptedOverlapBy = $actor",
        {
            "ruleId": rule_id,
            "project": payload.project,
            "conflictsWith": payload.conflictsWith,
            "acceptedAt": now,
            "actor": (payload.actor or "").strip(),
        },
    )

    return {
        "status": "overlap-accepted",
        "project": payload.project,
        "ruleId": rule_id,
        "conflictsWith": payload.conflictsWith,
        "acceptedAt": now,
    }


@router.get("/knowledge/sessions/{project}")
def list_knowledge_sessions(project: str):
    rows = read_many(
        "MATCH (s:SpecSession {project: $project, graph: $graph}) "
        "RETURN s.sessionId AS sessionId, s.mode AS mode, "
        "       s.prompt AS prompt, s.result AS result, s.createdAt AS createdAt "
        "ORDER BY s.createdAt DESC",
        {"project": project, "graph": SPEC_GRAPH},
    )
    return {"project": project, "sessions": rows}


class DesignRuleSessionPayload(BaseModel):
    project: str
    mode: str  # ingest, query, edit
    prompt: str
    result: str = ""


@router.post("/design-rule-sessions")
def store_design_rule_session(payload: DesignRuleSessionPayload):
    session_id = "drs-" + uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    write_query(
        "CREATE (s:DesignRuleSession {sessionId: $sessionId, project: $project, "
        "mode: $mode, prompt: $prompt, result: $result, createdAt: $createdAt, graph: 'Metagraph'})",
        {
            "sessionId": session_id,
            "project": payload.project,
            "mode": payload.mode,
            "prompt": payload.prompt,
            "result": payload.result[:2000],
            "createdAt": now,
        },
    )
    return {"sessionId": session_id}


@router.get("/design-rule-sessions/{project}")
def list_design_rule_sessions(project: str):
    rows = read_many(
        "MATCH (s:DesignRuleSession {project: $project}) "
        "RETURN s.sessionId AS sessionId, s.mode AS mode, "
        "       s.prompt AS prompt, s.result AS result, s.createdAt AS createdAt "
        "ORDER BY s.createdAt DESC",
        {"project": project},
    )
    return {"project": project, "sessions": rows}


MAX_CONTENT_SIZE = 100 * 1024  # 100KB per D-09 / Out of Scope


@router.post("/knowledge/update/match")
def knowledge_update_match(payload: UpdateMatchRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    rows = read_many(
        "CALL db.index.fulltext.queryNodes('spec_note_search', $query) "
        "YIELD node, score "
        "WHERE node.project = $project AND node.graph = $graph "
        "RETURN node.noteId AS noteId, node.title AS title, score "
        "ORDER BY score DESC LIMIT 10",
        {"query": payload.prompt, "project": payload.project, "graph": SPEC_GRAPH},
    )
    return {"candidates": rows}


@router.post("/knowledge/update/propose")
def knowledge_update_propose(payload: UpdateProposeRequest):
    if not payload.noteIds:
        raise HTTPException(status_code=400, detail="noteIds must not be empty")
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    results = []
    for note_id in payload.noteIds:
        note = read_single(
            "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) "
            "RETURN n.noteId AS noteId, n.title AS title, n.content AS content, n.updatedAt AS updatedAt",
            {"noteId": note_id, "graph": SPEC_GRAPH},
        )
        if note is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")
        llm_result = call_n8n_sync(
            webhook_path="dg/knowledge-update",
            body={"prompt_text": payload.prompt, "note_id": note_id, "current_content": note["content"], "project_name": payload.project},
        )
        proposed_text = llm_result.get("proposedText", "")
        if not proposed_text:
            proposed_text = note["content"]  # fallback: keep original if LLM returned empty
        diff_html = word_diff_html(note["content"], proposed_text)
        results.append({
            "noteId": note_id,
            "title": note["title"],
            "originalContent": note["content"],
            "proposedContent": proposed_text,
            "diffHtml": diff_html,
            "hasChanges": proposed_text.strip() != note["content"].strip(),
            "updatedAt": note["updatedAt"],
        })
    return {"diffs": results}


@router.post("/knowledge/update/confirm")
def knowledge_update_confirm(payload: UpdateConfirmRequest):
    if not payload.notes:
        raise HTTPException(status_code=400, detail="notes must not be empty")
    for item in payload.notes:
        if len(item.content.encode("utf-8")) > MAX_CONTENT_SIZE:
            raise HTTPException(status_code=413, detail=f"Content for {item.noteId} exceeds 100KB limit")
    affected = []
    now = datetime.now(timezone.utc).isoformat()
    for item in payload.notes:
        existing = read_single(
            "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) "
            "RETURN n.updatedAt AS updatedAt, n.title AS title",
            {"noteId": item.noteId, "graph": SPEC_GRAPH},
        )
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {item.noteId}")
        if existing["updatedAt"] != item.updatedAt:
            raise HTTPException(
                status_code=409,
                detail=f"Note {item.noteId} was modified since propose step - reload and retry",
            )
        write_query(
            "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) "
            "SET n.content = $content, n.updatedAt = $now",
            {"noteId": item.noteId, "graph": SPEC_GRAPH, "content": item.content, "now": now},
        )
        affected.append(existing.get("title") or item.noteId)
    # Write SpecSession per D-10 / UPDK-06
    session_id = "ks-" + uuid.uuid4().hex[:12]
    write_query(
        "MERGE (s:SpecSession {sessionId: $sessionId, project: $project, graph: $graph}) "
        "SET s.mode = 'update', s.prompt = $prompt, s.result = $result, s.createdAt = $createdAt",
        {
            "sessionId": session_id,
            "project": payload.project,
            "graph": SPEC_GRAPH,
            "prompt": payload.prompt,
            "result": json.dumps({"affectedNodes": affected})[:2000],
            "createdAt": now,
        },
    )
    # Connect to parent class node
    write_query(
        "MATCH (s:SpecSession {sessionId: $sessionId, graph: $graph}) "
        "MERGE (c:SpecClass {name: 'SpecSession', graph: $graph}) "
        "MERGE (s)-[:INSTANCE_OF]->(c)",
        {
            "sessionId": session_id,
            "graph": SPEC_GRAPH,
        },
    )
    return {"affectedNodes": affected, "sessionId": session_id}


# ---------------------------------------------------------------------------
# Resource-project resolvers (Phase 1205, D-03/D-15, ALGN12-20)
# ---------------------------------------------------------------------------
#
# Routes addressed by an opaque id alone (credential, note, execution) cannot
# read their project from the request. Each resolver derives it server-side
# from the stored resource. An unknown resource and an unauthorised one raise
# the SAME not-found, so no route reveals whether another project's resource
# exists.


def _credential_not_found() -> HTTPException:
    return _structured_error_response(
        "Credential not found.",
        "Use a credential_id from GET /connectors.",
        "CREDENTIAL_NOT_FOUND",
        404,
    )


def _resolve_credential_project(request: Request) -> str | None:
    connector_id = request.path_params.get("connector_id")
    credential_id = request.path_params.get("credential_id")
    for record in connectors.load_credentials():
        if (
            record.get("connector_id") == connector_id
            and record.get("credential_id") == credential_id
        ):
            return record.get("project") or "default-project"
    return None


def _note_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Note not found")


async def _resolve_note_project(request: Request) -> str | None:
    note_id = request.path_params.get("note_id")
    row = await run_in_threadpool(
        read_single,
        "MATCH (n:SpecNote {noteId: $noteId, graph: $graph}) RETURN n.project AS project",
        {"noteId": note_id, "graph": SPEC_GRAPH},
    )
    if row is None:
        return None
    return row.get("project") or "default-project"


def _execution_not_found() -> HTTPException:
    return _structured_error_response(
        "Execution not found.",
        "Poll an executionId returned to you by the workflow you started.",
        "EXECUTION_NOT_FOUND",
        404,
    )


def _resolve_execution_project(request: Request) -> str | None:
    """Owner-bound: only the user who started the execution resolves it, and
    only while they still hold membership of the recorded project (checked by
    the caller against the route's min_role). Anyone else -- including other
    members of the same project -- gets None (404)."""
    execution_id = request.path_params.get("execution_id")
    with _EXECUTION_OWNERS_LOCK:
        owner = EXECUTION_OWNERS.get(execution_id)
    principal = getattr(request.state, "principal", None)
    if owner is None or principal is None:
        return None
    if principal.username is None or principal.username != owner.get("username"):
        return None
    return owner.get("project") or None


route_policy.register_resource_resolver(
    "credential", _resolve_credential_project, _credential_not_found
)
route_policy.register_resource_resolver("note", _resolve_note_project, _note_not_found)
route_policy.register_resource_resolver(
    "execution", _resolve_execution_project, _execution_not_found
)


# ── Project tenancy (Phase 1205, D-02/D-05) ─────────────────────────────────
#
# Project listing/creation, membership administration and invitations. Every
# route reads the caller from request.state.principal, set by the router-level
# auth.require_principal dependency. There is deliberately no open
# self-service account creation route: an account is created only by accepting
# an invite minted by a project owner (POST /auth/invites -> POST
# /auth/accept-invite).

PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")

# Fixed statements: the project (or project list) is always a bound parameter.
PROJECT_NODE_COUNTS_QUERY = (
    "MATCH (n) WHERE n.project IS NOT NULL AND ($projects IS NULL OR n.project IN $projects) "
    "RETURN n.project AS project, count(n) AS nodes"
)
PROJECT_EXISTS_IN_GRAPH_QUERY = "MATCH (n) WHERE n.project = $project RETURN true AS present LIMIT 1"


class ProjectCreateRequest(BaseModel):
    project: str


class InviteRequest(BaseModel):
    username: str
    project: str
    role: str


class AcceptInviteRequest(BaseModel):
    inviteCode: str
    password: str


def _invite_invalid() -> HTTPException:
    """The one generic answer for every invite failure (unknown, used,
    expired, or naming an account that already exists)."""
    return _structured_error_response(
        "This invitation is not valid.",
        "Ask a project owner for a new invitation.",
        "INVITE_INVALID",
        400,
    )


def _iso_utc(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/projects")
def list_projects(request: Request):
    """Membership-scoped project listing. A member sees only the projects
    they belong to (with their role and node count); an admin sees every
    project -- graph projects plus membership projects -- as owner."""
    principal = request.state.principal
    if principal.is_admin:
        graph_rows = read_many(PROJECT_NODE_COUNTS_QUERY, {"projects": None})
        roles = {name: "owner" for name in auth.list_all_member_projects()}
        for row in graph_rows:
            roles.setdefault(row["project"], "owner")
    else:
        memberships = auth.list_memberships(principal.username or "")
        roles = {m["project"]: m["role"] for m in memberships}
        graph_rows = (
            read_many(PROJECT_NODE_COUNTS_QUERY, {"projects": sorted(roles)}) if roles else []
        )
    counts = {row["project"]: int(row["nodes"]) for row in graph_rows}
    return {
        "projects": [
            {"project": name, "nodes": counts.get(name, 0), "role": roles[name]}
            for name in sorted(roles)
        ]
    }


@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreateRequest, request: Request):
    """Register an unused project name with the caller as owner. The
    membership/graph existence check-and-set runs under the auth store lock
    (auth.create_project_if_unclaimed)."""
    principal = request.state.principal
    name = payload.project
    if not PROJECT_NAME_PATTERN.match(name):
        raise _structured_error_response(
            "That project name is not valid.",
            "Use 1-64 characters: letters, digits, spaces, dot, underscore or hyphen, starting with a letter or digit.",
            "PROJECT_NAME_INVALID",
            422,
        )
    exists_in_graph = read_single(PROJECT_EXISTS_IN_GRAPH_QUERY, {"project": name}) is not None
    if not auth.create_project_if_unclaimed(
        name, principal.username or "", exists_in_graph=exists_in_graph
    ):
        raise _structured_error_response(
            "That project name is unavailable.",
            "Choose a different project name.",
            "PROJECT_NAME_UNAVAILABLE",
            409,
        )
    return {"project": name, "role": "owner"}


@router.get("/projects/{project}/members")
def list_project_members(project: str):
    members = sorted(auth.list_members(project), key=lambda m: m["username"])
    return {"project": project, "members": members}


@router.delete("/projects/{project}/members/{username}", status_code=204)
def remove_project_member(project: str, username: str):
    with auth._STORE_LOCK:
        role = auth.get_role(username, project)
        if role is None:
            raise _structured_error_response(
                "That user is not a member of this project.",
                "List the project members and try again.",
                "MEMBER_NOT_FOUND",
                404,
            )
        if role == "owner" and auth.count_owners(project) <= 1:
            raise _structured_error_response(
                "A project must keep at least one owner.",
                "Promote another member to owner before removing this one.",
                "LAST_OWNER",
                409,
            )
        auth.remove_membership(username, project)
    return Response(status_code=204)


@router.post("/auth/invites")
def create_project_invite(payload: InviteRequest, request: Request):
    """Add an existing user to the project directly, or mint a one-time
    invite code for a username that has no account yet (D-05). An invite
    never sets or changes the password of an existing account."""
    principal = request.state.principal
    if payload.role not in auth.ROLES:
        raise _structured_error_response(
            "That role is not valid.",
            "Use one of: " + ", ".join(auth.ROLES) + ".",
            "ROLE_INVALID",
            422,
        )
    try:
        username = auth.normalize_username(payload.username)
    except ValueError as exc:
        raise _structured_error_response(
            "That username is not valid.",
            "Use 3-254 characters: lowercase letters, digits and . _ @ + -.",
            "USERNAME_INVALID",
            422,
        ) from exc

    if auth.get_user(username) is not None:
        with auth._STORE_LOCK:
            current = auth.get_role(username, payload.project)
            if (
                current == "owner"
                and payload.role != "owner"
                and auth.count_owners(payload.project) <= 1
            ):
                raise _structured_error_response(
                    "A project must keep at least one owner.",
                    "Promote another member to owner before changing this role.",
                    "LAST_OWNER",
                    409,
                )
            auth.set_membership(username, payload.project, payload.role)
        return {"status": "member-added"}

    code, record = auth.create_invite(
        username,
        payload.project,
        payload.role,
        created_by=principal.username or "",
    )
    return {"status": "invited", "inviteCode": code, "expiresAt": _iso_utc(record["expires_at"])}


@router.post("/auth/accept-invite")
def accept_invite(payload: AcceptInviteRequest, response: Response):
    """Public: turn a one-time invite code plus a chosen password into an
    account with the invited project role, and log it in. The password policy
    is checked BEFORE the code is consumed; an existing account is never
    modified (T-1205-12-01)."""
    try:
        auth.validate_password_policy(payload.password)
    except ValueError as exc:
        raise _structured_error_response(
            "The password does not meet the password policy.",
            str(exc),
            "PASSWORD_POLICY",
            422,
        ) from exc

    invite = auth.consume_invite(payload.inviteCode)
    if invite is None:
        raise _invite_invalid()
    try:
        user = auth.create_user(invite["username"], payload.password)
    except ValueError as exc:
        # The invited username now has an account: refuse without touching it.
        raise _invite_invalid() from exc
    auth.set_membership(user["username"], invite["project"], invite["role"])
    token = auth.create_session(user["username"])
    auth_routes.set_session_cookie(response, token)
    return {"username": user["username"], "isAdmin": False}


# ── Named graph endpoints (Phase 1205, D-06) ────────────────────────────────
#
# Replacements for the browser's former direct Cypher sites. Each endpoint runs
# ONE fixed module-level statement; the only variables are bound parameters
# ($project, $id, $key, $value, $ruleId, $runId, $dgEntityId). No endpoint
# accepts statement text, and the project is never interpolated. Project
# authorisation happens in the router dependency (ROUTE_POLICIES rows).

PROTECTED_NODE_KEYS = frozenset({"project", "graph"})
NODE_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

GRAPH_NODES_QUERY = (
    "MATCH (n) WHERE n.project = $project "
    "RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props LIMIT 2000"
)
GRAPH_RELS_QUERY = (
    "MATCH (a)-[r]->(b) WHERE a.project = $project AND b.project = $project "
    "RETURN id(a) AS source, type(r) AS type, id(b) AS target LIMIT 8000"
)
# The D-06 carve-out (spec'd by 1205-16): only nodes with NO project are moved,
# and never a node of a named project (default-project included).
CLAIM_UNTAGGED_QUERY = (
    "MATCH (n) WHERE n.project IS NULL SET n.project = $project RETURN count(n) AS claimed"
)
NODE_PROPERTY_UPDATE_QUERY = (
    "MATCH (n) WHERE id(n) = $id AND n.project = $project "
    "SET n[$key] = $value RETURN properties(n) AS props"
)
RULES_LIST_QUERY = (
    "MATCH (r:Rule) WHERE r.graph = 'Metagraph' AND r.project = $project "
    "RETURN r.Rule_Id AS ruleId, coalesce(r.SWRL, r.text, '') AS text ORDER BY r.Rule_Id"
)
RULE_DETAIL_QUERY = (
    "MATCH (r:Rule {Rule_Id: $ruleId}) WHERE r.project = $project "
    "RETURN r.SWRL AS swrl, r.RuleName AS name, r.RuleDescription AS description LIMIT 1"
)
ENTITY_STATUSES_QUERY = (
    "MATCH (ve:ValidationEntity {graph:'ValidGraph', project:$project, runId:$runId, dgEntityId:$dgEntityId}) "
    "RETURN ve.ruleId AS ruleId, ve.status AS status ORDER BY ruleId"
)
ACCEPTED_CANDIDATES_QUERY = (
    "MATCH (ds:DesignState {project: $project, kind: 'ParamState'}) "
    "WHERE ds.source = 'ai-generated' AND ($ruleId IS NULL OR ds.sourceRuleId = $ruleId) "
    "RETURN ds.StateId AS stateId, ds.sourceRuleId AS sourceRuleId, ds.provider AS provider, "
    "ds.model AS model, ds.generatedAt AS generatedAt, ds.acceptedAt AS acceptedAt, "
    "ds.strategy AS strategy ORDER BY ds.acceptedAt DESC"
)


class NodePropertyRequest(BaseModel):
    key: str
    value: Any = None


def write_single(query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Run one write statement and return its single result row (or None)."""
    with driver.session() as session:
        record = session.run(query, parameters or {}).single()
    return None if record is None else record.data()


def _graph_json_safe(value: Any):
    """normalize_value, plus a JSON-safe fallback for driver types (temporal,
    spatial) that a JSON response cannot encode."""
    value = normalize_value(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _graph_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_graph_json_safe(v) for v in value]
    iso = getattr(value, "iso_format", None)
    return iso() if callable(iso) else str(value)


@router.get("/graph/{project}")
def get_project_graph(project: str):
    node_rows = read_many(GRAPH_NODES_QUERY, {"project": project})
    rel_rows = read_many(GRAPH_RELS_QUERY, {"project": project})
    return {
        "nodes": [
            {
                "id": row["id"],
                "labels": _graph_json_safe(row["labels"]),
                "props": _graph_json_safe(row["props"]),
            }
            for row in node_rows
        ],
        "rels": [
            {"source": row["source"], "type": row["type"], "target": row["target"]}
            for row in rel_rows
        ],
    }


@router.post("/graph/{project}/claim-untagged")
def claim_untagged_nodes(project: str):
    row = write_single(CLAIM_UNTAGGED_QUERY, {"project": project})
    return {"claimed": int((row or {}).get("claimed") or 0)}


@router.put("/graph/{project}/node/{node_id}/property")
def update_node_property(project: str, node_id: int, payload: NodePropertyRequest):
    key = payload.key
    if not NODE_KEY_PATTERN.match(key):
        raise _structured_error_response(
            "That property name is not valid.",
            "Use letters, digits and underscore, starting with a letter or underscore (max 64 characters).",
            "NODE_KEY_INVALID",
            422,
        )
    if key in PROTECTED_NODE_KEYS:
        raise _structured_error_response(
            "That property cannot be edited.",
            "The project and graph properties are managed by the system.",
            "PROTECTED_PROPERTY",
            403,
        )
    value = payload.value
    if value is not None and (
        not isinstance(value, (str, int, float, bool))
        or (isinstance(value, float) and value != value)
        or (isinstance(value, float) and value in (float("inf"), float("-inf")))
    ):
        raise _structured_error_response(
            "That property value is not valid.",
            "Use a string, number, boolean or null.",
            "PROPERTY_VALUE_INVALID",
            422,
        )
    row = write_single(
        NODE_PROPERTY_UPDATE_QUERY,
        {"id": node_id, "project": project, "key": key, "value": value},
    )
    if row is None:
        # Same answer for an unknown node and another project's node.
        raise _structured_error_response(
            "Node not found.",
            "Reload the graph and try again.",
            "NODE_NOT_FOUND",
            404,
        )
    return {"props": _graph_json_safe(row["props"])}


@router.get("/rules/{project}")
def list_project_rules(project: str):
    rows = read_many(RULES_LIST_QUERY, {"project": project})
    return {
        "project": project,
        "rules": [{"ruleId": row["ruleId"], "text": row["text"] or ""} for row in rows],
    }


@router.get("/rules/{project}/{rule_id}")
def get_rule_detail(project: str, rule_id: str):
    row = read_single(RULE_DETAIL_QUERY, {"project": project, "ruleId": rule_id})
    if row is None:
        raise _structured_error_response(
            "Rule not found.",
            "Check the rule id and project.",
            "RULE_NOT_FOUND",
            404,
        )
    return {
        "ruleId": rule_id,
        "swrl": row.get("swrl") or "",
        "name": row.get("name") or "",
        "description": row.get("description") or "",
    }


@router.get("/validation/view/{project}/{run_id}/entity/{dg_entity_id}")
def get_entity_statuses(project: str, run_id: str, dg_entity_id: str):
    rows = read_many(
        ENTITY_STATUSES_QUERY,
        {"project": project, "runId": run_id, "dgEntityId": dg_entity_id},
    )
    return {"statuses": [{"ruleId": row["ruleId"], "status": row["status"]} for row in rows]}


@router.get("/computgraph/candidates/{project}")
def list_accepted_candidates(project: str, ruleId: str | None = Query(default=None)):
    rows = read_many(ACCEPTED_CANDIDATES_QUERY, {"project": project, "ruleId": ruleId or None})
    return {
        "candidates": [
            {
                key: _graph_json_safe(row.get(key))
                for key in (
                    "stateId",
                    "sourceRuleId",
                    "provider",
                    "model",
                    "generatedAt",
                    "acceptedAt",
                    "strategy",
                )
            }
            for row in rows
        ]
    }


app.include_router(router)
