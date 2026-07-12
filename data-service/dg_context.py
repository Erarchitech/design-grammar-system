"""DG-aware context assembler -- Cypher expression catalog loader (Phase 29:
CTXA-02) and the deterministic context assembler (Phase 29-03: CTXA-01/04/05).

Mirrors the reasoner.py / connectors.py module layout: a small module-level
registry/index built from a versioned data artifact, plus a defensive
`load_*()` helper that never raises on a missing or malformed file.

`llm/cypher_catalog.json` (repo-root, NOT inside `data-service/`) is the one
externally-versioned artifact this module owns -- it documents the six
standard SWRL/Cypher rule shapes (max_limit, min_limit, range, ratio,
boolean_requirement, existence_count), each with a worked example. SWRL
convention data and the Computgraph concept catalog are read-only Python
data structures that live in the sibling `dg_knowledge.py` module (created
in plan 29-02), not in this file.

Path resolution: inside the data-service Docker container the repo root is
mounted read-only at `/mnt/repo` (see `docker-compose.yml`'s
`.:/mnt/repo:ro` volume + `DG_KNOWLEDGE_REPO_ROOT: /mnt/repo` env var), so
`CYPHER_CATALOG_FILE` resolves to `/mnt/repo/llm/cypher_catalog.json` at
runtime with zero Dockerfile changes. Outside the container (e.g. a
repo-root venv), the same env var is unset and the path falls back to
`<repo-root>/llm/cypher_catalog.json`, computed relative to this file.

`assemble_context()` (added Plan 29-03) is the CTXA-01 core: it unions the
static per-layer V7 concept subset (Ontograph/Metagraph/Validgraph, plus the
forward-prep-only Computgraph block from `dg_knowledge.load_computgraph_catalog()`),
the SWRL conventions (`dg_knowledge.swrl_conventions()`), a deterministic
keyword-matched subset of this module's own Cypher catalog, and a LIVE
Neo4j query for the project's existing Ontograph entities (D-17, porting
n8n's "Fetch Existing Entities" node). `GET /context/debug` (app.py) calls
this exact same function -- no parallel code path (D-04). Selection is
deterministic keyword/entity matching only, never embeddings (CTXA-05).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from pydantic import BaseModel

import dg_knowledge


# ── Cypher expression catalog (versioned artifact: llm/cypher_catalog.json) ──

CYPHER_CATALOG_FILE = (
    Path(os.getenv("DG_KNOWLEDGE_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
    / "llm"
    / "cypher_catalog.json"
)

EXPECTED_SHAPE_IDS: set[str] = {
    "max_limit",
    "min_limit",
    "range",
    "ratio",
    "boolean_requirement",
    "existence_count",
}

_EMPTY_CATALOG: dict[str, Any] = {"version": 0, "shapes": []}


def load_cypher_catalog() -> dict[str, Any]:
    """Read the Cypher expression catalog from CYPHER_CATALOG_FILE.

    Defensive by design -- callers (including /context/debug, added in a
    later plan) must never 500 because of a catalog file issue. Returns
    `{"version": 0, "shapes": []}` if the file is missing, unreadable,
    malformed JSON, or does not have the expected top-level shape.
    """
    if not CYPHER_CATALOG_FILE.exists():
        return dict(_EMPTY_CATALOG)
    try:
        payload = json.loads(CYPHER_CATALOG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_EMPTY_CATALOG)
    if not isinstance(payload, dict) or not isinstance(payload.get("shapes"), list):
        return dict(_EMPTY_CATALOG)
    return payload


def cypher_shape_ids() -> set[str]:
    """Derived index of shape ids present in the currently-loaded catalog."""
    return {shape["id"] for shape in load_cypher_catalog().get("shapes", []) if "id" in shape}


# Derived shape-id index, computed once at import time from the real catalog
# on disk (mirrors reasoner.py's REASONER_IDS / connectors.py's CONNECTOR_IDS
# module-constant pattern). Call cypher_shape_ids() directly if the catalog
# file's contents might have changed since import (e.g. in tests).
CYPHER_SHAPE_IDS: set[str] = cypher_shape_ids()


# ── Context assembler request model (Phase 29-03: CTXA-01, D-01/D-02) ──

CONTEXT_REQUEST_TYPES: set[str] = {"rule_ingest", "rule_edit", "graph_query"}


class ContextAssembleRequest(BaseModel):
    """Request body for POST /context/assemble (and GET /context/debug's
    equivalent query params, D-04 -- identical param contract, identical
    assembled result, no parallel code path).

    `type` is `str`, not a Pydantic `Literal` -- validity is checked by
    `assemble_context()` against `CONTEXT_REQUEST_TYPES` (module-level set),
    raising `ValueError` on an unknown value. This mirrors connectors.py's
    `create_credential()` "validate against an id set, raise ValueError"
    pattern (not FastAPI's own automatic literal-validation error body) so
    app.py's routes can translate an unknown type into this project's own
    `{error, hint, code}` structured-error shape (CONTEXT_TYPE_INVALID).
    """

    type: str
    project: str
    rules_text: str | None = None
    question: str | None = None


# ── Static per-layer V7 concept subset (Phase 29-03: CTXA-01) ──
#
# Schema-level facts (allowed labels/relationships/key properties/graph
# values) straight from cypher_template.txt's GRAPH SCHEMA section --
# fine-grained domain concepts (e.g. "Building"/"height") are NOT catalogued
# here separately; they surface naturally through the selected Cypher
# catalog shape's own `worked_example` text (see _match_shape_ids below).

ONTOGRAPH_CONCEPTS: dict[str, Any] = {
    "layer": "Ontograph",
    "graph_value": "OntoGraph",
    "node_labels": ["Class", "DatatypeProperty", "ObjectProperty"],
    "key_properties": {
        "Class": "iri",
        "DatatypeProperty": "iri",
        "ObjectProperty": "iri",
    },
    "display_properties": {
        "Class": "label",
        "DatatypeProperty": "SWRL_label",
        "ObjectProperty": "label",
    },
    "iri_prefixes": {"domain_terms": "ex:"},
}

METAGRAPH_CONCEPTS: dict[str, Any] = {
    "layer": "Metagraph",
    "graph_value": "Metagraph",
    "node_labels": ["Rule", "Atom", "Var", "Literal", "Builtin"],
    "relationship_types": ["HAS_BODY", "HAS_HEAD", "REFERS_TO", "ARG"],
    "key_properties": {
        "Rule": "Rule_Id",
        "Atom": "Atom_Id",
        "Var": "name+project",
        "Literal": "lex+datatype",
        "Builtin": "iri",
    },
    "iri_prefixes": {"builtins": "swrlb:"},
}

VALIDGRAPH_CONCEPTS: dict[str, Any] = {
    "layer": "Validgraph",
    "graph_value": "ValidGraph",
    "node_labels": ["DesignState", "Run"],
    "design_state_kinds": ["ObjState", "ParamState", "PropState"],
    "key_properties": {
        "DesignState": "StateId+project",
        "Run": "Run_Id+project",
    },
    "run_properties": ["ValidStatus", "SendStatus"],
}


# ── rule_edit guidance (Pitfall 3 RESOLVED per 29-03-PLAN.md / 29-CONTEXT.md) ──
#
# Rule_Id embeds the numeric threshold (R_<DOMAIN>_<PROPERTY>_<LIMIT>_V), so a
# numeric-limit edit REGENERATES Rule_Id and requires the old Rule + old Atom
# subgraph to be cleaned up via MATCH-DELETE (as n8n's "Prepare Graph Payload"
# already does). CONTEXT.md's "preserve iri/SWRL_label, change only Literal
# values" is scoped to ONTOLOGY entities and metagraph atom semantics -- it
# does NOT freeze Rule_Id. Confirmed by the Task 3 human-verify checkpoint.

_RULE_EDIT_GUIDANCE: dict[str, Any] = {
    "rule_id_regenerates_on_numeric_change": True,
    "statement": (
        "A numeric-threshold edit changes Rule_Id -- the limit is embedded in "
        "the R_<DOMAIN>_<PROPERTY>_<LIMIT>_V format itself, so editing the "
        "threshold REGENERATES Rule_Id to a new value (e.g. "
        "R_URB_HEIGHT_MAX_75_V -> R_URB_HEIGHT_MAX_80_V)."
    ),
    "old_atom_cleanup": (
        "The OLD Rule node and its old HAS_BODY/HAS_HEAD Atom subgraph MUST "
        "be removed via a MATCH-DELETE cleanup step before/alongside writing "
        "the new Rule_Id -- mirrors n8n's existing 'Prepare Graph Payload' "
        "cleanupStatements. This is the convention Phase 31 RING-02's "
        "atom-level diff-preview design builds on."
    ),
    "ontology_entities_preserved": (
        "Class/DatatypeProperty/ObjectProperty entities are matched by their "
        "existing `iri` and their `SWRL_label`/`label` is REUSED, never "
        "regenerated -- only `Literal.lex` changes for a numeric threshold "
        "edit (cypher_template.txt's PROPERTY REUSE ON EDIT rule)."
    ),
    "scope_note": (
        "Resolves Pitfall 3: CONTEXT.md's 'preserve iri/SWRL_label, change "
        "only Literal values' is scoped to ONTOLOGY entities and metagraph "
        "atom semantics -- it does NOT freeze Rule_Id, which is a derived "
        "key encoding the threshold, not an ontology entity identifier."
    ),
}


# ── Deterministic keyword matcher (Phase 29-03: CTXA-01/D-03) ──
#
# Ports the keyword-matching precedent already live in
# n8n/workflows/graph-query-mcp.json's "Build Cypher Prompt" guidance text
# (height/maximum -> numeric-limit query pattern, "list rules" -> Rule
# listing) into a single reusable, deterministic matcher against the six
# Cypher catalog shapes. Fixed iteration order (not the CYPHER_SHAPE_IDS set)
# is what keeps selection byte-identical across repeat calls (CTXA-05).

_SHAPE_ID_ORDER: tuple[str, ...] = (
    "max_limit",
    "min_limit",
    "range",
    "ratio",
    "boolean_requirement",
    "existence_count",
)

_SHAPE_KEYWORD_PATTERNS: dict[str, tuple[str, ...]] = {
    "max_limit": ("maximum", "at most", "no more than", "not exceed", "shall not exceed", "up to"),
    "min_limit": ("minimum", "at least", "no less than", "not less than"),
    "range": ("between",),
    "ratio": ("ratio", "percentage", "proportion", "window-to-wall", "wwr"),
    "boolean_requirement": ("must have", "shall have", "required to have", "mandatory", "must be provided"),
    "existence_count": ("number of", "count of", "quantity of", "how many"),
}


def _match_shape_ids(text: str | None) -> list[str]:
    """Deterministic keyword match against the Cypher catalog shapes.

    Case-insensitive substring match against a fixed keyword list, checked in
    a fixed shape-id order -- no embeddings, no randomness (CTXA-05). Returns
    an empty list if nothing matches (e.g. a "list rules" graph_query
    question, which selects no emission shape).
    """
    haystack = (text or "").lower()
    return [
        shape_id
        for shape_id in _SHAPE_ID_ORDER
        if any(keyword in haystack for keyword in _SHAPE_KEYWORD_PATTERNS.get(shape_id, ()))
    ]


# ── Live per-project OntoGraph entity union (Phase 29-03: CTXA-01/D-17) ──
#
# Ports n8n's "Fetch Existing Entities" node Cypher (rules-to-metagraph.json
# ~294-312) verbatim, with one addition: an `AND n.project = $project` bound
# parameter. The original n8n query had no project filter at all; per-project
# isolation is a standing invariant of this system (CLAUDE.md: "Single Neo4j
# database with project isolation via project property on every node"), so
# this port adds it as a bound parameter (never string-interpolated, T-29-03a).

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

_EXISTING_ENTITIES_QUERY = (
    "MATCH (n) WHERE (n:Class OR n:DatatypeProperty OR n:ObjectProperty) "
    "AND n.graph = 'OntoGraph' AND n.project = $project "
    "RETURN labels(n)[0] AS nodeLabel, n.iri AS iri, "
    "coalesce(n.label, '') AS label, coalesce(n.SWRL_label, '') AS swrl_label, "
    "coalesce(n.range, '') AS range "
    "ORDER BY nodeLabel, iri"
)

_driver: Any = None


def _get_driver() -> Any:
    """Lazily open this module's own Neo4j driver (never at import time).

    Kept separate from app.py's module-level `driver` to avoid a circular
    import (app.py imports dg_context) -- functionally equivalent, same env
    vars, same lazy-connect behavior as `GraphDatabase.driver(...)`.
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def fetch_existing_entities(project: str, session: Any = None) -> list[dict[str, Any]]:
    """Live per-project union of existing OntoGraph Class/DatatypeProperty/
    ObjectProperty entities (D-17), replacing n8n's "Fetch Existing Entities"
    HTTP node.

    `session` is duck-typed to the `neo4j.Session.run(query, **params)`
    contract (iterable of mapping-like rows) -- matches the FixtureSession
    precedent already proven in dg-reasoner/tests (STATE.md Phase 821 Plan
    02). Pass a FixtureSession in unit tests for zero live Neo4j; omit it in
    production and this lazily opens a real session against this module's
    own driver.
    """
    if session is not None:
        result = session.run(_EXISTING_ENTITIES_QUERY, project=project)
        return [dict(record) for record in result]
    with _get_driver().session() as live_session:
        result = live_session.run(_EXISTING_ENTITIES_QUERY, project=project)
        return [dict(record) for record in result]


# ── The assembler itself (Phase 29-03: CTXA-01/04/05) ──


def assemble_context(req: ContextAssembleRequest, session: Any = None) -> dict[str, Any]:
    """Deterministically assemble the per-layer V7 concept subset + SWRL
    conventions + selected Cypher catalog shapes + live existing entities for
    one of the three request types (rule_ingest, rule_edit, graph_query).

    Raises ValueError on an unknown `req.type` (app.py's routes translate
    this to a CONTEXT_TYPE_INVALID 422 structured error).

    Deterministic by construction (CTXA-05): every value here is either a
    fixed module-level constant, a fixed-order keyword match, or a live Neo4j
    query with an explicit ORDER BY -- no embeddings, no timestamps, no
    set-derived (unordered) collections reach the returned dict. The same
    request issued twice serializes byte-identically.
    """
    if req.type not in CONTEXT_REQUEST_TYPES:
        raise ValueError(f"Unknown context type: {req.type}")

    text_for_matching = req.question if req.type == "graph_query" else req.rules_text
    matched_shape_ids = _match_shape_ids(text_for_matching)

    catalog = load_cypher_catalog()
    shapes_by_id = {shape["id"]: shape for shape in catalog.get("shapes", []) if "id" in shape}
    selected_shapes = [shapes_by_id[shape_id] for shape_id in matched_shape_ids if shape_id in shapes_by_id]

    existing_entities = fetch_existing_entities(req.project, session=session)

    context: dict[str, Any] = {
        "type": req.type,
        "project": req.project,
        "ontograph": dict(ONTOGRAPH_CONCEPTS),
        "metagraph": dict(METAGRAPH_CONCEPTS),
        "validgraph": dict(VALIDGRAPH_CONCEPTS),
        "computgraph": dg_knowledge.load_computgraph_catalog(),
        "swrl_conventions": dg_knowledge.swrl_conventions(),
        "selected_cypher_shapes": selected_shapes,
        "existing_entities": existing_entities,
    }

    if req.type == "rule_edit":
        context["edit_guidance"] = dict(_RULE_EDIT_GUIDANCE)

    return context
