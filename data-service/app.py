from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Any
from urllib.parse import urlparse
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from neo4j import GraphDatabase
from neo4j.graph import Node, Path, Relationship
from pydantic import BaseModel, Field

from speckle_validation import (
    SpeckleConnectionSettings,
    SpeckleValidationError,
    build_client,
    get_latest_model_version_id,
    get_or_create_validation_model_id,
    normalize_url,
    publish_validation_version,
)

app = FastAPI()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

EXECUTION_RESULTS: dict[str, dict[str, Any]] = {}
WORKFLOW_STATUS: dict[str, dict[str, Any]] = {}
VALIDATION_GRAPH = "ValidationGraph"
DATA_DIR = FilePath(os.getenv("DG_DATA_DIR", "/app/data"))
SPECKLE_SETTINGS_FILE = DATA_DIR / "speckle-settings.json"


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
    rules: list[ValidationPublishRulePayload] = Field(default_factory=list)
    ruleResults: list[ValidationPublishRuleResultPayload] = Field(default_factory=list)
    entities: list[ValidationPublishEntityPayload] = Field(default_factory=list)


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
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
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
            run.status = 'completed',
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
            run.createdAt AS createdAt
        ORDER BY run.createdAt DESC
        LIMIT 1
    """
    return read_single(query, {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id})


def get_validation_entity_sets(project: str, run_id: str, rule_id: str | None = None) -> dict[str, list[str]]:
    rows = read_many(
        """
        MATCH (ve:ValidationEntity {graph:$graph, project:$project, runId:$runId})
        WHERE $ruleId IS NULL OR ve.ruleId = $ruleId
        RETURN ve.dgEntityId AS dgEntityId, ve.status AS status
        ORDER BY ve.dgEntityId
        """,
        {"graph": VALIDATION_GRAPH, "project": project, "runId": run_id, "ruleId": rule_id},
    )
    object_sets = {"failed": [], "passed": []}
    for row in rows:
        status = row.get("status")
        dg_entity_id = row.get("dgEntityId")
        if not dg_entity_id:
            continue
        if status == "failed":
            if dg_entity_id not in object_sets["failed"]:
                object_sets["failed"].append(dg_entity_id)
            if dg_entity_id in object_sets["passed"]:
                object_sets["passed"].remove(dg_entity_id)
        elif status == "passed" and dg_entity_id not in object_sets["failed"] and dg_entity_id not in object_sets["passed"]:
            object_sets["passed"].append(dg_entity_id)
    return object_sets


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
        "rules": rules,
        "objectSets": object_sets,
    }


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


@app.put("/integration/speckle/project/{project}")
def put_speckle_project_config(project: str, payload: SpeckleProjectConfigPayload):
    payload = normalize_speckle_project_config_payload(payload)
    if not payload.speckleProjectId or not payload.baseModelId:
        raise HTTPException(status_code=400, detail="speckleProjectId and baseModelId are required.")
    config = upsert_integration_config(project, payload)
    return config.model_dump()


@app.post("/validation/publish")
def publish_validation(payload: ValidationPublishRequest):
    config = get_integration_config(payload.project)
    if config is None:
        raise HTTPException(status_code=404, detail="No Speckle integration config found for this DG project.")
    config = normalize_speckle_project_config_payload(config)

    settings = get_speckle_settings()
    if not settings.write_token:
        raise HTTPException(
            status_code=500,
            detail="Speckle write token is not configured. Save it in the DG home page Speckle Settings card or set SPECKLE_WRITE_TOKEN on data-service.",
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
        )
        return {
            "status": "published",
            "runId": run_id,
            "validationModelId": publish_result["validationModelId"],
            "validationVersionId": publish_result["validationVersionId"],
            "baseVersionId": publish_result["baseVersionId"],
            "modelViewerUrl": publish_result["modelViewerUrl"],
        }
    except SpeckleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Validation publish failed: {exc}") from exc


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
