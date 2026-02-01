from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship, Path
import os
import re

app = FastAPI()

# Подключение к Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

EXECUTION_RESULTS = {}
WORKFLOW_STATUS = {}

class ExecutionResult(BaseModel):
    executionId: str
    status: str
    payload: dict | None = None
    workflow: str | None = None
    step: int | None = None
    progress: float | None = None
    message: str | None = None

def normalize_value(value):
    if isinstance(value, Node):
        node_id = getattr(value, "id", None)
        if node_id is None:
            node_id = getattr(value, "element_id", None)
        return {
            "_type": "node",
            "id": node_id,
            "labels": list(value.labels),
            "properties": dict(value)
        }
    if isinstance(value, Relationship):
        rel_id = getattr(value, "id", None)
        if rel_id is None:
            rel_id = getattr(value, "element_id", None)
        start_id = getattr(value.start_node, "id", None)
        if start_id is None:
            start_id = getattr(value.start_node, "element_id", None)
        end_id = getattr(value.end_node, "id", None)
        if end_id is None:
            end_id = getattr(value.end_node, "element_id", None)
        return {
            "_type": "relationship",
            "id": rel_id,
            "type": value.type,
            "start": start_id,
            "end": end_id,
            "properties": dict(value)
        }
    if isinstance(value, Path):
        return {
            "_type": "path",
            "nodes": [normalize_value(n) for n in value.nodes],
            "relationships": [normalize_value(r) for r in value.relationships]
        }
    if isinstance(value, list):
        return [normalize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize_value(v) for k, v in value.items()}
    return value

def is_write_query(cypher):
    return re.search(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b", cypher, re.IGNORECASE) is not None

@app.get("/")
def read_root():
    return {"status": "Data Service is running"}

@app.post("/create_node/")
def create_node(label: str, name: str):
    with driver.session() as session:
        session.run(f"CREATE (n:{label} {{name: $name}})", name=name)
    return {"status": f"Node {name} with label {label} created"}

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
                        "description": "Return Neo4j labels, relationship types, property keys, graphs, and projects."
                    },
                    {
                        "name": "neo4j_query",
                        "description": "Run a read-only Cypher query and return records."
                    }
                ]
            }
        }

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "neo4j-mcp",
                    "version": "1.0"
                }
            }
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
            "projects": projects
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": "schema"}],
                "data": data
            }
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
        data = {
            "keys": keys,
            "records": records
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": "query"}],
                "data": data
            }
        }

    raise HTTPException(status_code=400, detail="Unknown tool name")

@app.post("/execution-result")
def store_execution_result(result: ExecutionResult):
    entry = {
        "status": result.status,
        "payload": result.payload or {}
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
            "payload": result.payload or {}
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
