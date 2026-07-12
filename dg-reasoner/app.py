"""dg-reasoner sidecar — FastAPI app.

Isolated OWL 2 DL consistency-check + SHACL-validation service. Reads Neo4j
directly over bolt (same env-var contract as data-service/app.py) and owns
the whole Cypher -> RDFLib -> HermiT pipeline: `POST /reason/consistency`
and `POST /shacl/validate` delegate to `reasoning.py` (Plan 821-03), which
in turn builds on `ontology_export.build_graph` (Plan 821-02).
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase
from pydantic import BaseModel

import reasoning

logger = logging.getLogger(__name__)
app = FastAPI()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

if not os.getenv("NEO4J_PASSWORD"):
    logger.warning(
        "NEO4J_PASSWORD is not set — falling back to default '%s'. "
        "Set NEO4J_PASSWORD in production to avoid hardcoded credentials.",
        NEO4J_PASSWORD,
    )

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@app.get("/health")
def health():
    """Always returns 200; reports Neo4j reachability without failing the probe."""
    neo4j_status = "down"
    try:
        with driver.session() as session:
            session.run("RETURN 1", timeout=3).consume()
        neo4j_status = "up"
    except Exception:  # pragma: no cover - defensive (IN-01)
        neo4j_status = "down"

    return {"status": "ok", "neo4j": neo4j_status}


class ConsistencyRequest(BaseModel):
    project: str
    engine: str = "hermit"


class ShaclRequest(BaseModel):
    project: str
    run_id: str | None = None


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

    result = reasoning.run_consistency(payload.project, payload.engine)

    if result.get("error") == "timeout":
        return JSONResponse(status_code=504, content=result)
    return result


@app.post("/shacl/validate")
def shacl_validate(payload: ShaclRequest):
    """SHACL validation against the version-controlled shapes graph (D-07/D-08/D-09/D-10).

    Without `run_id`, validates the project-level Metagraph/OntoGraph export
    only -- the 821 backward-compatible contract. With `run_id`, additionally
    unions in that run's ValidGraph ABox (Plan 823-01) and re-derives a single
    batch-wide `owl:AllDifferent` over every minted individual from both
    exports. Returns the canonical `{conforms, results, counts}` envelope.
    """
    return reasoning.run_shacl(payload.project, run_id=payload.run_id)
