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
import re
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from pydantic import BaseModel

import dg_knowledge
from llm_gateway import (
    GenerateRequest,
    get_adapter,
    load_persisted_llm_settings,
    resolve_active_provider,
)


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
    # 29-06 gap closure: describes the REAL shipped shape per app.py's
    # store_validation_run()/list_validation_runs() -- DesignState/Run (the
    # aspirational node labels the LLM's schema-correct-but-wrong
    # MATCH (:DesignState ...) query targeted, per 29-UAT.md Success
    # Criterion 4's debug session) are intentionally NOT here; no
    # :DesignState nodes exist for live runs.
    "node_labels": ["ValidationRun", "ValidationEntity", "IntegrationConfig"],
    # Kinds of state ENTRIES inside statePayloadJson (see
    # state_payload_json_shape below) -- NOT first-class node labels. Kept
    # for backward compat with 29-03's existing assertion.
    "design_state_kinds": ["ObjState", "ParamState", "PropState"],
    "key_properties": {
        "ValidationRun": "graph+project+runId",
        "ValidationEntity": "graph+project+runId+ruleId+dgEntityId",
    },
    "relationship_types": ["HAS_ENTITY"],
    "run_properties": ["ValidStatus", "SendStatus", "status", "createdAt", "rulesJson", "statePayloadJson"],
    "design_state_storage": (
        "Design states are NOT separate graph nodes. Each validation run "
        "MERGEs exactly one (:ValidationRun {graph:'ValidGraph', project, "
        "runId}) node whose `statePayloadJson` property holds the whole "
        "captured design-state snapshot serialized as a JSON string. Answer "
        "a design-state question by MATCHing ValidationRun for the project "
        "and reading run.statePayloadJson -- never by matching a "
        ":DesignState node, since none exist for live runs."
    ),
    "state_payload_json_shape": {
        "version": "2",
        "stateId": "string",
        "label": "string",
        "capturedAtUtc": "ISO-8601 string",
        "objStates": "list (ObjState entries)",
        "paramStates": "list (ParamState entries)",
        "propStates": "list (PropState entries)",
        "v1_fallback": "pre-v2 payloads carry a flat `parameters` list instead of the three typed lists above",
    },
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

# Mirrors app.py's VALIDATION_GRAPH constant (duplicated, not imported, for
# the same circular-import reason _get_driver() is its own copy: app.py
# imports dg_context, so dg_context cannot import app).
VALIDATION_GRAPH = "ValidGraph"

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


# ── Live existing-design-states helper (Phase 29-06 gap closure: CTXA-01/04) ──
#
# Closes Phase 29 UAT Success Criterion 4: the graph_query context previously
# carried only the aspirational Validgraph schema description, never any
# LIVE ValidationRun data -- so the LLM had nothing to reason over except a
# schema it could not verify against real data. This mirrors
# fetch_existing_entities() (D-17) for the ValidGraph layer.


def _summarize_state_payload(state_payload_json: str | None) -> dict[str, Any] | None:
    """Lightweight port of app.py's `_project_state_summary()`, extended with
    a per-kind (ObjState/ParamState/PropState) count breakdown so the
    assembled context carries the v4 kind values a Cypher MATCH cannot
    introspect from the opaque `statePayloadJson` string.

    Returns None for absent, empty, or malformed payloads. Never raises.
    """
    if not state_payload_json:
        return None
    try:
        parsed = json.loads(state_payload_json)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        return None
    if not isinstance(parsed, dict):
        return None

    if parsed.get("version") == "2":
        return {
            "stateId": parsed.get("stateId") or "",
            "label": parsed.get("label"),
            "capturedAtUtc": parsed.get("capturedAtUtc"),
            "objStateCount": len(parsed.get("objStates") or []),
            "paramStateCount": len(parsed.get("paramStates") or []),
            "propStateCount": len(parsed.get("propStates") or []),
        }

    # v1 fallback (ParamState-only, no `version` field).
    parameters = parsed.get("parameters")
    return {
        "stateId": parsed.get("stateId") or "",
        "label": parsed.get("label"),
        "capturedAtUtc": parsed.get("capturedAtUtc"),
        "objStateCount": 0,
        "paramStateCount": len(parameters) if isinstance(parameters, list) else 0,
        "propStateCount": 0,
    }


_EXISTING_DESIGN_STATES_QUERY = (
    "MATCH (run:ValidationRun {graph:$graph, project:$project}) "
    "OPTIONAL MATCH (run)-[:HAS_ENTITY]->(ve:ValidationEntity) "
    "RETURN run.runId AS runId, run.createdAt AS createdAt, "
    "run.statePayloadJson AS statePayloadJson, run.ValidStatus AS validStatus, "
    "run.SendStatus AS sendStatus, count(DISTINCT ve) AS entityCount "
    "ORDER BY run.createdAt DESC, run.runId "
    "LIMIT 25"
)


def fetch_existing_design_states(project: str, session: Any = None) -> list[dict[str, Any]]:
    """Live per-project union of existing ValidationRun rows (mirrors
    `list_validation_runs()`'s graph filter exactly, so this returns the SAME
    runs the user sees in the Model Viewer), each parsed into a compact
    {runId, createdAt, entityCount, validStatus, sendStatus, state} dict via
    `_summarize_state_payload()`.

    `$graph`/`$project` are bound parameters, never string-interpolated
    (T-29-06 per-project isolation, same invariant as T-29-03a). `session` is
    duck-typed identically to `fetch_existing_entities()` -- pass a
    FixtureSession in unit tests, omit in production for a lazily-opened live
    session. Ordering is deterministic (ORDER BY + LIMIT), preserving CTXA-05.
    """
    if session is not None:
        result = session.run(_EXISTING_DESIGN_STATES_QUERY, graph=VALIDATION_GRAPH, project=project)
        rows = [dict(record) for record in result]
    else:
        with _get_driver().session() as live_session:
            result = live_session.run(_EXISTING_DESIGN_STATES_QUERY, graph=VALIDATION_GRAPH, project=project)
            rows = [dict(record) for record in result]

    return [
        {
            "runId": row.get("runId"),
            "createdAt": row.get("createdAt"),
            "entityCount": int(row.get("entityCount") or 0),
            "validStatus": row.get("validStatus"),
            "sendStatus": row.get("sendStatus"),
            "state": _summarize_state_payload(row.get("statePayloadJson")),
        }
        for row in rows
    ]


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

    if req.type == "graph_query":
        # 29-06 gap closure: live ValidationRun/statePayloadJson data, so the
        # LLM has real design-state data to reason over (D-17 pattern) --
        # graph_query only, no extra Validgraph query on the ingest/edit path.
        context["existing_design_states"] = fetch_existing_design_states(req.project, session=session)

    return context


# ── Cypher validator (Phase 29-04: CTXA-04 -- PRIMARY security control) ──
#
# This is the phase's mitigation for T-29-01 (hallucinated/malformed Cypher
# reaching Neo4j tx/commit) and T-29-02 (prompt injection via rules_text
# attempting to make the LLM emit destructive Cypher). No LLM-generated
# Cypher is executed until it passes every check below. Replaces n8n's ad
# hoc "Parse LLM Output" (rules-to-metagraph.json) and "Parse Cypher"
# (graph-query-mcp.json) JS checks with a pytest-covered Python function.

# Schema-level allow-lists, straight from cypher_template.txt's GRAPH SCHEMA
# + OUTPUT RULES sections and CLAUDE.md's Relationships table. HAS_ENTITY
# (ValidationRun -> ValidationEntity) is the REAL ValidGraph-side
# relationship (app.py store_validation_run()); VALIDATES is also part of
# the schema the validator must recognize, not emitted by LLM ingest.
ALLOWED_LABELS: set[str] = {
    "Class",
    "DatatypeProperty",
    "ObjectProperty",
    "Builtin",
    "Rule",
    "Atom",
    "Var",
    "Literal",
    "ValidationRun",
    "IntegrationConfig",
    "ValidationEntity",
    "Representation",
    "SharedProperty",
}

ALLOWED_RELATIONSHIPS: set[str] = {
    "HAS_BODY",
    "HAS_HEAD",
    "REFERS_TO",
    "ARG",
    "HAS_ENTITY",
    "VALIDATES",
    "HAS_REPRESENTATION",
    "HAS_SHARED_PROPERTY",
}

# Identity-registry property allow-list (Phase 32.1) -- properties on
# Representation and SharedProperty nodes, plus dgId on Computgraph entities,
# that the validator must recognize to avoid false-positive unknown-property
# rejections on generated Cypher touching the identity registry.
ALLOWED_PROPERTIES: set[str] = {
    "dgId",
    "nativeId",
    "nativeIdKind",
    "platform",
    "connector",
    "boundAt",
    "propertyName",
    "writtenAt",
}


# DesignState.kind enum (v4/v7 schema) -- same three values already exposed
# via VALIDGRAPH_CONCEPTS["design_state_kinds"] above; kept as its own
# module-level constant here so the validator's bad_kind_enum check doesn't
# need to reach back into the assembler's concept dict. Note (29-06): these
# values now describe statePayloadJson entry kinds, not a first-class
# :DesignState node property -- the check below is moot for read-only
# graph_query but harmless, kept as-is (out of this gap's scope).
DESIGNSTATE_KINDS: set[str] = {"ObjState", "ParamState", "PropState"}

# Verb policy (T-29-01/T-29-02 mitigation): rule_ingest/rule_edit may ONLY
# emit MERGE/SET (cypher_template.txt OUTPUT RULES: "Use only MERGE and
# SET"); graph_query must be fully read-only.
WRITE_VERBS: set[str] = {"MERGE", "SET"}
DISALLOWED_VERBS: set[str] = {"DELETE", "REMOVE", "DETACH", "DROP", "CREATE"}

# Duplicated (not imported) from app.py's is_write_query() -- same verb set,
# same regex text -- to reuse that exact precedent for the graph_query
# read-only check without introducing a circular import (app.py imports
# dg_context, so dg_context cannot import app).
_WRITE_QUERY_PATTERN = re.compile(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b", re.IGNORECASE)
# Superset used for the rule_ingest/rule_edit policy -- adds DETACH, which
# is not its own verb in is_write_query() but IS an explicit disallowed verb
# per cypher_template.txt/CONTEXT.md ("reject DELETE/REMOVE/DETACH/DROP").
_ALL_VERB_PATTERN = re.compile(r"\b(MERGE|SET|CREATE|DELETE|REMOVE|DETACH|DROP)\b", re.IGNORECASE)

# Label extraction -- port of graph-query-mcp.json's "Parse Cypher" labelRegex,
# extended to walk EVERY `:Label` in a multi-label chain (n:LabelA:LabelB),
# not just the last one (the original JS regex only captures the final
# colon-separated label per node due to its greedy `[^\)]*` prefix).
_LABEL_CHAIN_PATTERN = re.compile(r"\(\s*(?:[A-Za-z_][A-Za-z0-9_]*)?((?::[A-Za-z_][A-Za-z0-9_]*)+)")
_SINGLE_LABEL_PATTERN = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")

# Relationship-type extraction -- port of "Parse Cypher"'s relRegex, splitting
# pipe-separated types (HAS_BODY|HAS_HEAD) into individual entries.
_REL_TYPE_PATTERN = re.compile(r"-\s*\[[^\]]*:\s*([A-Za-z_][A-Za-z0-9_|]*)")

# var -> label map (first `(var:Label` occurrence wins) -- lets a later
# `var.prop = ...` SET clause be resolved back to the node's label.
_NODE_VAR_LABEL_PATTERN = re.compile(r"\(\s*(\w+)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)")

# Whole `MERGE (var:Label {props})` node pattern -- feeds the QUALITY CHECKS
# key-name checks (Rule_Id/Atom_Id/project) below. `[^}]*` spans newlines
# (it excludes only the literal `}` char), so multi-line templates work.
_MERGE_NODE_PATTERN = re.compile(
    r"MERGE\s*\(\s*(\w+)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}\s*\)",
    re.IGNORECASE,
)

# DesignState.kind enum checks -- inline (`{kind: '...'}` within the same
# MERGE) and SET-based (`var.kind = '...'` after a separate MERGE).
_KIND_INLINE_PATTERN = re.compile(r"DesignState\s*\{[^}]*\bkind\s*:\s*'([^']*)'")
_KIND_SET_PATTERN = re.compile(r"(\w+)\.kind\s*=\s*'([^']*)'")

# Generic `var.prop = ...` assignment -- feeds the DatatypeProperty
# display-property check (SWRL_label, not label).
_DOT_ASSIGN_PATTERN = re.compile(r"(\w+)\.(\w+)\s*=")


def has_valid_nesting(cypher: str) -> bool:
    """Port of n8n's hasValidNesting() (rules-to-metagraph.json "Parse LLM
    Output" node functionCode) -- strips quoted strings first (so a stray
    bracket inside a string literal doesn't break the stack match), then
    verifies every (), {}, [] opened is closed in the same order. Ported
    near-verbatim; do NOT re-derive from scratch (this function is already
    battle-tested against live LLM output noise per RESEARCH.md)."""
    unquoted = re.sub(r"'[^']*'", "", cypher)
    stack: list[str] = []
    pairs = {"(": ")", "{": "}", "[": "]"}
    closers = {")", "}", "]"}
    for ch in unquoted:
        if ch in pairs:
            stack.append(ch)
        elif ch in closers:
            if not stack or pairs[stack.pop()] != ch:
                return False
    return not stack


def _extract_labels(cypher: str) -> set[str]:
    labels: set[str] = set()
    for match in _LABEL_CHAIN_PATTERN.finditer(cypher):
        labels.update(_SINGLE_LABEL_PATTERN.findall(match.group(1)))
    return labels


def _extract_relationships(cypher: str) -> set[str]:
    rels: set[str] = set()
    for match in _REL_TYPE_PATTERN.finditer(cypher):
        rels.update(part.strip() for part in match.group(1).split("|") if part.strip())
    return rels


def _var_label_map(cypher: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for var, label in _NODE_VAR_LABEL_PATTERN.findall(cypher):
        mapping.setdefault(var, label)
    return mapping


def validate_cypher(cypher: str, request_type: str) -> dict[str, Any]:
    """Validate LLM-generated Cypher against the v4 schema (allowed labels,
    relationships, DesignState `kind` enum, Rule_Id/Atom_Id/SWRL_label naming,
    Var `project` merge key) AND a request-type-aware write-verb policy
    (CTXA-04 -- the phase's PRIMARY security control, mitigating T-29-01/
    T-29-02).

    Returns `{"valid": bool, "violations": [{"code", "message", "path"?}]}`.
    Never raises on malformed Cypher -- every schema/verb problem becomes a
    violation, not an exception. Raises ValueError only for an unrecognized
    `request_type` (mirrors assemble_context()'s ValueError-dispatch
    convention, app.py maps this to a structured error).
    """
    if request_type not in CONTEXT_REQUEST_TYPES:
        raise ValueError(f"Unknown request type: {request_type}")

    violations: list[dict[str, Any]] = []

    if not has_valid_nesting(cypher):
        violations.append(
            {
                "code": "unbalanced_brackets",
                "message": (
                    "Bracket/parenthesis/brace nesting is unbalanced outside "
                    "quoted strings. Where: the full Cypher statement. How to "
                    "fix: ensure every (), {}, [] opened is closed, in the "
                    "same order."
                ),
            }
        )

    for label in sorted(_extract_labels(cypher) - ALLOWED_LABELS):
        violations.append(
            {
                "code": "unknown_label",
                "message": (
                    f"Label '{label}' is not one of the allowed schema labels "
                    f"({', '.join(sorted(ALLOWED_LABELS))}). Where: node label "
                    f"'{label}'. How to fix: reuse an allowed label, or MERGE "
                    f"an existing node instead of introducing a new one."
                ),
                "path": label,
            }
        )

    for rel in sorted(_extract_relationships(cypher) - ALLOWED_RELATIONSHIPS):
        violations.append(
            {
                "code": "unknown_relationship",
                "message": (
                    f"Relationship type '{rel}' is not one of the allowed "
                    f"schema relationships ({', '.join(sorted(ALLOWED_RELATIONSHIPS))}). "
                    f"Where: relationship '{rel}'. How to fix: use HAS_BODY/"
                    f"HAS_HEAD/REFERS_TO/ARG (or HAS_ENTITY/VALIDATES for "
                    f"ValidGraph)."
                ),
                "path": rel,
            }
        )

    var_label = _var_label_map(cypher)

    for value in _KIND_INLINE_PATTERN.findall(cypher):
        if value not in DESIGNSTATE_KINDS:
            violations.append(
                {
                    "code": "bad_kind_enum",
                    "message": (
                        f"DesignState.kind value '{value}' is not one of "
                        f"{sorted(DESIGNSTATE_KINDS)}. Where: a DesignState "
                        f"node's `kind` property. How to fix: use ObjState, "
                        f"ParamState, or PropState."
                    ),
                    "path": value,
                }
            )
    for var, value in _KIND_SET_PATTERN.findall(cypher):
        if var_label.get(var) == "DesignState" and value not in DESIGNSTATE_KINDS:
            violations.append(
                {
                    "code": "bad_kind_enum",
                    "message": (
                        f"DesignState.kind value '{value}' (on `{var}`) is not "
                        f"one of {sorted(DESIGNSTATE_KINDS)}. Where: "
                        f"`{var}.kind`. How to fix: use ObjState, ParamState, "
                        f"or PropState."
                    ),
                    "path": var,
                }
            )

    for var, label, props in _MERGE_NODE_PATTERN.findall(cypher):
        if label == "Rule" and "Rule_Id" not in props:
            violations.append(
                {
                    "code": "bad_key_name",
                    "message": (
                        f"Rule node `{var}` is not keyed on Rule_Id. Where: "
                        f"MERGE ({var}:Rule {{...}}). How to fix: the Rule key "
                        f"property is Rule_Id, not id (cypher_template.txt "
                        f"QUALITY CHECKS)."
                    ),
                    "path": var,
                }
            )
        elif label == "Atom" and "Atom_Id" not in props:
            violations.append(
                {
                    "code": "bad_key_name",
                    "message": (
                        f"Atom node `{var}` is not keyed on Atom_Id. Where: "
                        f"MERGE ({var}:Atom {{...}}). How to fix: the Atom key "
                        f"property is Atom_Id, not id."
                    ),
                    "path": var,
                }
            )
        elif label == "Var" and not re.search(r"\bproject\s*:", props):
            violations.append(
                {
                    "code": "missing_project_key",
                    "message": (
                        f"Var node `{var}` MERGE is missing the `project` "
                        f"property in its merge key. Where: MERGE "
                        f"({var}:Var {{...}}). How to fix: Var MERGE keys on "
                        f"both `name` and `project` -- omitting it "
                        f"reintroduces the v2.0 cross-project variable-"
                        f"collision bug (SWRL_CONVENTIONS.argument_rules)."
                    ),
                    "path": var,
                }
            )

    for var, prop in _DOT_ASSIGN_PATTERN.findall(cypher):
        if var_label.get(var) == "DatatypeProperty" and prop == "label":
            violations.append(
                {
                    "code": "bad_key_name",
                    "message": (
                        f"DatatypeProperty `{var}` sets `.label` -- its "
                        f"display property is SWRL_label, not label. Where: "
                        f"`{var}.label`. How to fix: SET {var}.SWRL_label = "
                        f"... instead."
                    ),
                    "path": var,
                }
            )

    if request_type in ("rule_ingest", "rule_edit"):
        for verb in sorted({v.upper() for v in _ALL_VERB_PATTERN.findall(cypher)}):
            if verb not in WRITE_VERBS:
                violations.append(
                    {
                        "code": "disallowed_verb",
                        "message": (
                            f"'{verb}' is not an allowed write verb for "
                            f"{request_type} -- only MERGE and SET are "
                            f"permitted (cypher_template.txt OUTPUT RULES). "
                            f"Where: '{verb}' in the generated Cypher. How to "
                            f"fix: rewrite using only MERGE/SET; never emit "
                            f"DELETE/REMOVE/DETACH/DROP/CREATE."
                        ),
                        "path": verb,
                    }
                )
    elif request_type == "graph_query":
        if _WRITE_QUERY_PATTERN.search(cypher):
            for verb in sorted({v.upper() for v in _WRITE_QUERY_PATTERN.findall(cypher)}):
                violations.append(
                    {
                        "code": "disallowed_verb",
                        "message": (
                            f"'{verb}' is a write verb; graph_query Cypher "
                            f"must be fully read-only (reuses app.py's "
                            f"is_write_query() precedent). Where: '{verb}' in "
                            f"the generated Cypher. How to fix: rewrite as a "
                            f"read-only MATCH/RETURN query with no write "
                            f"clauses."
                        ),
                        "path": verb,
                    }
                )

    # De-duplicate identical violations (same code+path) while preserving order.
    seen: set[tuple[str, str | None]] = set()
    unique_violations: list[dict[str, Any]] = []
    for violation in violations:
        key = (violation["code"], violation.get("path"))
        if key in seen:
            continue
        seen.add(key)
        unique_violations.append(violation)

    return {"valid": len(unique_violations) == 0, "violations": unique_violations}


# ── Bounded retry loop + n8n-facing endpoint request model (Phase 29-04: D-06/D-07) ──


def append_corrective_feedback(prompt: str, violations: list[dict[str, Any]]) -> str:
    """Append structured violations to the original prompt as corrective
    feedback for the next LLM attempt (What+Where+How-to-fix tone, mirroring
    the ErrorMessageTemplates vocabulary discipline already standard on the
    C# side)."""
    lines = [
        prompt,
        "",
        "--- CORRECTIVE FEEDBACK: the previous Cypher failed validation ---",
    ]
    for violation in violations:
        where = f" (at: {violation['path']})" if violation.get("path") else ""
        lines.append(f"- [{violation['code']}] {violation['message']}{where}")
    lines.append(
        "Regenerate the Cypher, fixing every violation listed above. Output "
        "Cypher only -- no JSON, no markdown fences, no commentary."
    )
    return "\n".join(lines)


def generate_validated_cypher(
    prompt: str, request_type: str, max_retries: int = 2
) -> dict[str, Any]:
    """The single n8n-facing generate+validate+retry orchestrator (D-06/D-07,
    RESEARCH.md Open Question 1 resolution: one endpoint, prompt-in ->
    validated-cypher-out).

    Calls the LLM gateway adapter directly in-process (resolve_active_provider
    -> get_adapter -> adapter.generate -- the exact llm_generate() sequence
    at app.py:996-1027) -- this NEVER re-POSTs to /llm/generate (RESEARCH.md
    Anti-pattern guard: avoids a redundant network hop + provider
    re-resolution on every retry attempt).

    Validates every attempt with validate_cypher(); on failure, appends
    structured corrective feedback to the ORIGINAL prompt and retries,
    bounded at `max_retries` (default 2 retries = 3 attempts total per
    CONTEXT.md D-07). n8n only ever sees the final result -- a valid Cypher
    string or a final structured violation list; intermediate failed
    attempts never surface (D-06).
    """
    if request_type not in CONTEXT_REQUEST_TYPES:
        # Fail fast on an unknown type -- never touch the adapter/LLM for a
        # request that validate_cypher() would reject anyway (app.py maps
        # this ValueError to CONTEXT_TYPE_INVALID, same as assemble_context()).
        raise ValueError(f"Unknown request type: {request_type}")

    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    provider, model, api_key = resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))

    current_prompt = prompt
    violations: list[dict[str, Any]] = []
    for attempt in range(max_retries + 1):
        req = GenerateRequest(prompt=current_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key)
        result = validate_cypher(response.text, request_type)
        if result["valid"]:
            return {"valid": True, "cypher": response.text, "attempts": attempt + 1}
        violations = result["violations"]
        current_prompt = append_corrective_feedback(prompt, violations)

    return {"valid": False, "violations": violations, "attempts": max_retries + 1}


class GenerateCypherRequest(BaseModel):
    """Request body for POST /context/generate-cypher -- the ONE n8n-facing
    call wrapping prompt-in -> validated-cypher-out (Open Question 1
    resolution: no separate /context/validate HTTP surface).

    `type` is plain str (not Pydantic Literal), validated by
    validate_cypher()/generate_validated_cypher() against
    CONTEXT_REQUEST_TYPES and raising ValueError on an unknown value --
    mirrors ContextAssembleRequest's established ValueError-dispatch
    convention (29-03) so app.py can translate it to the same
    CONTEXT_TYPE_INVALID structured-error shape.

    `project`/`model`/`provider` are accepted for schema symmetry with
    GenerateRequest/ContextAssembleRequest but are NOT wired to override
    resolution in this plan -- out of this plan's scope.
    """

    prompt: str
    type: str
    project: str | None = None
    model: str | None = None
    provider: str | None = None
