"""dg-reasoner sidecar — FastAPI app.

Isolated OWL 2 DL consistency-check + SHACL-validation service. Reads Neo4j
directly over bolt (same env-var contract as data-service/app.py) and owns
the whole Cypher -> RDFLib -> HermiT pipeline (real logic lands in Plan
821-03; this module only proves the container builds, serves /health, and
reads Neo4j).
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

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


@app.post("/reason/consistency")
def reason_consistency():
    """Stub — real HermiT/OWL 2 DL consistency check lands in Plan 821-03."""
    return JSONResponse(
        status_code=501,
        content={"status": "not-implemented", "plan": "821-03"},
    )


@app.post("/shacl/validate")
def shacl_validate():
    """Stub — real pySHACL pipeline lands in Plan 821-03."""
    return JSONResponse(
        status_code=501,
        content={"status": "not-implemented", "plan": "821-03"},
    )
