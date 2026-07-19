from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Any
import time
import urllib.request
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
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

import reasoner
import dg_context
import cg_recognition
import dg_identity
from dg_identity import MintRequest, BindRepresentationRequest, SharedPropertyWriteRequest
import gh_bridge
import computgraph_publish

app = FastAPI()

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

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

EXECUTION_RESULTS: dict[str, dict[str, Any]] = {}
WORKFLOW_STATUS: dict[str, dict[str, Any]] = {}
VALIDATION_GRAPH = "ValidGraph"
SPEC_GRAPH = "SpecGraph"
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


def call_n8n_sync(webhook_path: str, body: dict, timeout: int = 120) -> dict:
    """Fire n8n webhook, poll EXECUTION_RESULTS until completed or timeout."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{N8N_INTERNAL_URL}/webhook/{webhook_path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        ack = json.loads(resp.read())
    execution_id = ack.get("executionId")
    if not execution_id:
        raise HTTPException(status_code=502, detail="n8n did not return executionId")
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

    write_query(
        """
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
            run.rulesJson = $rulesJson,
            run.statePayloadJson = $statePayloadJson,
            run.status = 'completed',
            run.ValidStatus = $validStatus,
            run.SendStatus = true,
            run.createdAt = $createdAt
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
            run.shaclReportJson AS shaclReportJson
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
    rows = read_many(
        """
        MATCH (ve:ValidationEntity {graph:$graph, project:$project, runId:$runId})
        WHERE $ruleId IS NULL OR ve.ruleId = $ruleId
        RETURN ve.dgEntityId AS dgEntityId, ve.displayName AS displayName, ve.status AS status
        ORDER BY ve.dgEntityId
        """,
        {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id, "ruleId": rule_id},
    )
    seen_failed: dict[str, dict[str, str]] = {}
    seen_passed: dict[str, dict[str, str]] = {}
    for row in rows:
        status = row.get("status")
        dg_entity_id = row.get("dgEntityId")
        if not dg_entity_id:
            continue
        entry = {"dgEntityId": dg_entity_id, "displayName": row.get("displayName") or dg_entity_id}
        if status == "failed":
            if dg_entity_id not in seen_failed:
                seen_failed[dg_entity_id] = entry
            seen_passed.pop(dg_entity_id, None)
        elif status == "passed" and dg_entity_id not in seen_failed and dg_entity_id not in seen_passed:
            seen_passed[dg_entity_id] = entry
    return {"failed": list(seen_failed.values()), "passed": list(seen_passed.values())}


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


@app.on_event("startup")
def ensure_spec_indexes():
    """Create full-text index and parent class hub nodes for SpecGraph."""
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


@app.get("/")
def read_root():
    return {"status": "Data Service is running"}


@app.post("/create_node/")
def create_node(label: str, name: str):
    with driver.session() as session:
        session.run(f"CREATE (n:{label} {{label: $name}})", name=name)
    return {"status": f"Node {name} with label {label} created"}


@app.get("/integration/speckle/project/{project}")
def get_speckle_project_config(project: str):
    config = get_integration_config(project)
    if config is None:
        raise HTTPException(status_code=404, detail="No Speckle project configuration found for this DG project.")
    return config.model_dump()


@app.get("/settings/speckle")
def get_speckle_runtime_settings():
    return get_speckle_settings_response()


@app.put("/settings/speckle")
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


@app.get("/llm/settings")
def get_llm_settings():
    """Read LLM settings (provider, model, masked key, status)."""
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    return get_llm_settings_response(settings, master_secret)


@app.put("/llm/settings")
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


@app.delete("/llm/settings", status_code=204)
def delete_llm_settings():
    """Clear all LLM settings. Gateway falls back to Ollama on next call."""
    save_persisted_llm_settings({})
    return None


@app.post("/llm/generate")
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


@app.post("/llm/settings/test")
def test_llm_settings():
    """Test saved LLM configuration with a minimal provider call.

    Returns success/failure with latency measurement and live model list.
    """
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()

    provider, model, api_key = resolve_active_provider(settings, master_secret)

    if not api_key:
        return TestResult(success=False, error="No API key configured")

    start = time.time()
    try:
        adapter = get_adapter(provider, settings.get("baseUrl"))
        test_req = GenerateRequest(prompt="test", model=model)
        adapter.generate(test_req, api_key)
        latency_ms = (time.time() - start) * 1000.0

        models = list_models_for_provider(provider, api_key, settings.get("baseUrl"))

        return TestResult(success=True, latencyMs=latency_ms, models=models)
    except Exception as exc:
        error_msg, _hint, _code = map_provider_error(exc)
        return TestResult(success=False, error=error_msg)


@app.get("/llm/models")
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


@app.get("/connectors")
def get_connectors():
    """Connector registry joined with per-connector status, last-connection
    date, and credential summaries (never tokens or hashes). CONNB-01, CONNB-04.
    """
    return {
        "categories": connectors.CONNECTOR_CATEGORIES,
        "connectors": connectors.get_connector_overview(),
    }


@app.post("/connectors/{connector_id}/credentials", status_code=201)
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


@app.delete("/connectors/{connector_id}/credentials/{credential_id}", status_code=204)
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


@app.post("/connectors/heartbeat")
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
    return HeartbeatResponse(
        connector_id=record["connector_id"],
        status=connectors.derive_status(record["last_connection"]),
        # Phase 825: unlock the project scope + host-facing Neo4j connection bundle
        # for the authenticated connector. Old records without a project read as
        # "default-project".
        project=record.get("project") or "default-project",
        neo4j=connectors.Neo4jBundle(
            uri=NEO4J_PUBLIC_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        ),
    )


# ---------------------------------------------------------------------------
# Reasoner settings endpoints (Phase 814: REAS-01..03)
# ---------------------------------------------------------------------------


class ReasonerSettingsPayload(BaseModel):
    reasoner: str


@app.get("/reasoner/settings")
def get_reasoner_settings():
    """Return the reasoner registry and currently selected reasoner id."""
    settings = reasoner.load_settings()
    return {
        "reasoners": reasoner.REASONER_REGISTRY,
        "selected": settings.get("selected", None),
    }


@app.put("/reasoner/settings")
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


@app.post("/reasoner/consistency")
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


@app.post("/computgraph/context/pull")
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


@app.post("/computgraph/recognize")
def post_computgraph_recognize(payload: RecognizeRequest):
    """Classify untagged canvas entities into a schema-valid proposed-structure
    (RCGN-01), bounded-retry validated against the submitted cg_context
    (RCGN-04: hard-rejects hallucinated/tagged-overlap member ids). Thin route
    -- all logic delegates to cg_recognition.recognize_structure(), mirroring
    post_context_generate_cypher()'s delegation + error-mapping shape.
    """
    try:
        return cg_recognition.recognize_structure(payload.cg_context, payload.procedure_index)
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


@app.post("/computgraph/publish")
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


@app.post("/context/assemble")
def post_context_assemble(payload: dg_context.ContextAssembleRequest):
    """Assemble the per-layer V7 concept subset + SWRL conventions + selected
    Cypher catalog shapes + live existing entities for one request (D-01).
    Thin route -- all logic delegates to dg_context.assemble_context()."""
    try:
        with driver.session() as session:
            return dg_context.assemble_context(payload, session=session)
    except ValueError as exc:
        raise _context_type_invalid_error(exc)


@app.get("/context/debug")
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


@app.post("/context/generate-cypher")
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


@app.post("/identity/mint")
def post_identity_mint(payload: MintRequest):
    """Deterministically mint + persist a dgId for a Computgraph entity.

    Idempotent — safe to call unconditionally from the publish path; re-minting the
    same (project, definitionId, cgId) triple returns the same dgId without
    duplicating the node.
    """
    with driver.session() as session:
        dg_id = dg_identity.mint_identity(
            session, payload.project, payload.definition_id, payload.cg_id
        )
    return {"dgId": dg_id}


@app.get("/identity/resolve")
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


@app.post("/identity/bind")
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


@app.get("/identity/{dg_id}/representations")
def get_identity_representations(dg_id: str, project: str):
    """List all platform representations bound to a dgId within a project."""
    with driver.session() as session:
        return dg_identity.list_representations(session, dg_id, project)


@app.delete("/identity/{dg_id}/representations")
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


@app.post("/identity/{dg_id}/properties")
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


@app.get("/identity/{dg_id}/properties")
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


@app.put("/integration/speckle/project/{project}")
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


@app.post("/validation/publish")
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


@app.get("/validation/runs/{project}")
def get_validation_runs(project: str):
    return {"project": project, "runs": list_validation_runs(project)}


@app.delete("/validation/run/{project}/{run_id}")
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


@app.get("/validation/view/{project}")
def get_latest_validation_view(project: str):
    run = get_validation_run(project)
    if run is None:
        raise HTTPException(status_code=404, detail="No validation run found for this DG project.")

    object_sets = get_validation_entity_sets(project, run["runId"])
    return build_view_payload(project, run, object_sets)


@app.get("/validation/view/{project}/{run_id}")
def get_validation_view_for_run(project: str, run_id: str):
    run = get_validation_run(project, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")

    object_sets = get_validation_entity_sets(project, run_id)
    return build_view_payload(project, run, object_sets)


@app.get("/validation/view/{project}/{run_id}/{rule_id}")
def get_rule_validation_view(project: str, run_id: str, rule_id: str):
    run = get_validation_run(project, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")

    object_sets = get_validation_entity_sets(project, run_id, rule_id)
    return build_view_payload(project, run, object_sets, rule_id=rule_id)


@app.post("/mcp")
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


@app.post("/execution-result")
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
    if result.workflow:
        WORKFLOW_STATUS[result.workflow] = {
            "executionId": result.executionId,
            "status": result.status,
            "payload": result.payload or {},
        }
        if result.step is not None:
            WORKFLOW_STATUS[result.workflow]["step"] = result.step
        if result.progress is not None:
            WORKFLOW_STATUS[result.workflow]["progress"] = result.progress
        if result.message is not None:
            WORKFLOW_STATUS[result.workflow]["message"] = result.message
    return {"status": "ok"}


@app.get("/execution-result/{execution_id}")
def get_execution_result(execution_id: str):
    return EXECUTION_RESULTS.get(execution_id, {"status": "running"})


@app.get("/execution-result/latest/{workflow}")
def get_latest_workflow_result(workflow: str):
    return WORKFLOW_STATUS.get(workflow, {"status": "unknown"})


MAX_FILE_SIZE = 100 * 1024  # 100KB


@app.post("/knowledge/ingest/folder")
def ingest_folder(payload: FolderIngestRequest):
    root = validate_ingest_path(payload.path)
    md_files = list(root.rglob("*.md"))

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    for md_file in md_files:
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

    return {"inserted": inserted, "skipped": skipped}


# ---------------------------------------------------------------------------
# Knowledge CRUD endpoints
# ---------------------------------------------------------------------------


@app.get("/knowledge/notes/{project}")
def list_knowledge_notes(project: str):
    rows = read_many(
        "MATCH (n:SpecNote {project: $project, graph: $graph}) "
        "RETURN n.noteId AS noteId, n.title AS title, n.source AS source, "
        "       n.createdAt AS createdAt, n.updatedAt AS updatedAt "
        "ORDER BY n.updatedAt DESC",
        {"project": project, "graph": SPEC_GRAPH},
    )
    return {"project": project, "notes": rows}


@app.get("/knowledge/note/{note_id}")
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


@app.put("/knowledge/note/{note_id}")
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


@app.delete("/knowledge/note/{note_id}")
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


@app.get("/knowledge/sessions/{project}")
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


@app.post("/design-rule-sessions")
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


@app.get("/design-rule-sessions/{project}")
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


@app.post("/knowledge/update/match")
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


@app.post("/knowledge/update/propose")
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


@app.post("/knowledge/update/confirm")
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
