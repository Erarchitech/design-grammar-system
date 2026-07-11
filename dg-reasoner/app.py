"""dg-reasoner sidecar — FastAPI app.

Isolated OWL 2 DL consistency-check + SHACL-validation service. Reads Neo4j
directly over bolt (same env-var contract as data-service/app.py) and owns
the whole Cypher -> RDFLib -> HermiT pipeline: `POST /reason/consistency`
and `POST /shacl/validate` delegate to `reasoning.py` (Plan 821-03), which
in turn builds on `ontology_export.build_graph` (Plan 821-02).
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from pydantic import BaseModel

import reasoning

app = FastAPI()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# Reserved for the reasoning pipeline's hard subprocess timeout (Plan 821-03).
DG_REASONER_TIMEOUT_SECONDS = int(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90"))

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@app.get("/health")
def health():
    """Always returns 200; reports Neo4j reachability without failing the probe."""
    neo4j_status = "down"
    try:
        with driver.session() as session:
            session.run("RETURN 1", timeout=3).consume()
        neo4j_status = "up"
    except (ServiceUnavailable, Neo4jError, Exception):  # pragma: no cover - defensive
        neo4j_status = "down"

    return {"status": "ok", "neo4j": neo4j_status}


class ConsistencyRequest(BaseModel):
    project: str
    engine: str = "hermit"


class ShaclRequest(BaseModel):
    project: str


@app.post("/reason/consistency")
def reason_consistency(payload: ConsistencyRequest):
    """Hybrid OWL 2 DL consistency check (D-09/D-10 contract).

    Unions the static TBox + curated disjointness overlay + the live project
    export, strips HermiT-unsupported builtin rules, and runs HermiT under a
    hard server-side timeout. Returns the D-10 response dict on success, or
    the same dict with HTTP 504 if the reasoner subprocess is killed on
    timeout expiry.
    """
    if payload.engine not in reasoning.SUPPORTED_ENGINES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported engine '{payload.engine}'. Supported: {sorted(reasoning.SUPPORTED_ENGINES)}",
        )

    with driver.session() as session:
        result = reasoning.run_consistency(payload.project, payload.engine, session=session)

    if result.get("error") == "timeout":
        return JSONResponse(status_code=504, content=result)
    return result


@app.post("/shacl/validate")
def shacl_validate(payload: ShaclRequest):
    """pySHACL validation against a placeholder/empty shapes graph (D-11).

    Proves the real pySHACL plumbing end-to-end; real shapes land in Phase 823.
    """
    with driver.session() as session:
        return reasoning.run_shacl(payload.project, session=session)
