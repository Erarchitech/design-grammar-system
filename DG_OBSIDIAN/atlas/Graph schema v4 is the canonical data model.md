---
tags: [atlas, schema, v4, ontology, swrl]
date: 2026-07-05
graphify_communities: ["Community 180", "Community 213", "Community 214", "Community 237", "Community 262", "Community 286", "Community 288", "Community 31", "Community 45", "Community 63", "Match Step (Neo4j Full-Text Search, No LLM)", "Model Viewer (graph-viewer/model-viewer/)", "Phase 3: n8n Knowledge Workflows + LLM Ingest/Query", "Product Bridges Natural Language Rules to Graph-Based Val...", "Validation Endpoints (publish/runs/view)", "Validation Results Publish to Speckle as Overlay Versions", "ValidationGeometryPayload", "Worktree Branch Commits with Spurious Deletions", "code: 17 nodes", "code: rule", "extractErrorMessage()", "n8n Workflow Orchestrator for LLM Rule Ingestion and Queries", "v4.0 BOT Ontology Bridge"]
---

# Graph Schema v4 is the Canonical Data Model

The v4 schema (defined in `training/dataset_schema.json` and `cypher_template.txt`) is the single source of truth for all generated Cypher, UI labels, prompts, and validation logic. v4 shipped in milestone v7.0 (Phase 14) and is the **current live runtime schema**.

Schema v3 migration history: see the v3→v4 migration notes in `spec/DATABASE.md`.

## Schema Files

| File | Role |
|------|------|
| `cypher_template.txt` | v4 Cypher template with placeholders — LLM prompt source |
| `training/dataset_schema.json` | Formal JSON schema for node types, keys, properties (v4) |
| `training/updated_cypher_reference_examples_v3.cypher` | Complete reference Cypher examples (v4 successor in progress) |
| `graph-viewer/config.template.js` | NeoVis label/display configuration matching v4 |

## Graph Separation (4 layers)

| Graph Value | Contains | Purpose |
|-------------|----------|---------|
| `OntoGraph` | Class, DatatypeProperty, ObjectProperty | Domain ontology terms |
| `Metagraph` | Rule, Atom, Builtin, Var, Literal | SWRL rules and decomposed atom structures |
| `ValidGraph` | DesignState, Run, IntegrationConfig, ValidationEntity | Validation run state and metadata |
| `SpecGraph` | SpecNote, SpecTag, SpecSession, SpecClass | Project spec storage (notes, tags, sessions) |

## DesignState Kinds

DesignState nodes carry a `kind` property ∈ {ObjState, ParamState, PropState}:

| Kind | Prefix | Captures |
|------|--------|----------|
| `ObjState` | `OS_` | Object reference + Geometry + Label |
| `ParamState` | `DS_` | Typed parameters (Number/Integer/Boolean) via PARAMETER STATE |
| `PropState` | `PS_` | Rule + DataProperty + PropValue via PROPERTY STATE |

## Run Properties (ValidGraph)

| Property | Type | Description |
|----------|------|-------------|
| `Run_Id` | string | Key property |
| `ValidStatus` | Boolean[] | Per-ObjState validation results (index-matched) |
| `SendStatus` | Boolean | Whether results were published to Speckle |
| `statePayloadJson` | JSON (v2) | Envelope with objStates/paramStates/propStates keys |

## Rule-Level Properties

| Property | Replaces | Description |
|----------|----------|-------------|
| `SWRL` | `text` (v3) | Full SWRL rule expression |
| `RuleName` | `title` (v3) | Human-readable rule name |
| `RuleDescription` | (new) | Optional extended description |

## Rule ID Format

```
R_<DOMAIN>_<PROPERTY>_<LIMIT>_V
Example: R_URB_HEIGHT_MAX_75_V
```

## Atom ID Format

```
Body atoms: {Rule_Id}_A1, _A2, _A3, ...
Head atoms: {Rule_Id}_H1, _H2, ...
```

## IRI Prefixes

- `ex:` — domain terms (classes, properties, violation predicates)
- `swrlb:` — SWRL builtins (greaterThan, lessThan, equal, notEqual)

## Semantic Mapping (Violation Pattern)

| NL Phrase | SWRL Body Builtin | Meaning |
|-----------|-------------------|---------|
| "Maximum / at most X" | `swrlb:greaterThan(?val, X)` | Body fires when value exceeds limit |
| "Minimum / at least X" | `swrlb:lessThan(?val, X)` | Body fires when value is below limit |
| "Equal to X" | `swrlb:notEqual(?val, X)` | Body fires when value differs |
| "Between min and max" | Two separate rules | One for min, one for max |

See [[Violation rules invert the constraint in SWRL body]].

## Mandatory Propagation

When changing graph generation or query logic, update ALL:
1. `cypher_template.txt`
2. `training/dataset_schema.json`
3. n8n workflow prompts and validators
4. `graph-viewer/config.template.js` (NeoVis labels)
5. `data-service/app.py` (Cypher queries)
6. `.github/copilot-instructions.md`
7. `README.md`
8. `spec/DATABASE.md`

## Component Re-Wiring

See `docs/RELEASE-NOTES-v7.0.md` for the full v7.0 component re-wiring guide with ASCII diagrams covering CLASSIFICATOR removal, VALIDATION RUNS→VALIDATION GRAPH, REINSTATE→PARAMETER REINSTATE, DESIGN STATE split, CONNECTOR port renames, RULE DECONSTRUCT extended, and VALIDATOR rework.

## Related

- [[Neo4j stores ontology and metagraph in a single database]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[Cypher MERGE idempotent node creation pattern]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Community 180|Community 180]]
- [[graphify/communities/Community 213|Community 213]]
- [[graphify/communities/Community 214|Community 214]]
- [[graphify/communities/Community 237|Community 237]]
- [[graphify/communities/Community 262|Community 262]]
- [[graphify/communities/Community 286|Community 286]]
- [[graphify/communities/Community 288|Community 288]]
- [[graphify/communities/Community 31|Community 31]]
- [[graphify/communities/Community 45|Community 45]]
- [[graphify/communities/Community 63|Community 63]]
- [[graphify/communities/Match Step (Neo4j Full-Text Search, No LLM)|Match Step (Neo4j Full-Text Search, No LLM)]]
- [[graphify/communities/Model Viewer (graph-viewermodel-viewer) (279)|Model Viewer (graph-viewer/model-viewer/)]]
- [[graphify/communities/Phase 3 n8n Knowledge Workflows + LLM IngestQuery|Phase 3: n8n Knowledge Workflows + LLM Ingest/Query]]
- [[graphify/communities/Product Bridges Natural Language Rules to Graph-Based Val...|Product Bridges Natural Language Rules to Graph-Based Val...]]
- [[graphify/communities/Validation Endpoints (publishrunsview)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/Validation Results Publish to Speckle as Overlay Versions|Validation Results Publish to Speckle as Overlay Versions]]
- [[graphify/communities/ValidationGeometryPayload|ValidationGeometryPayload]]
- [[graphify/communities/Worktree Branch Commits with Spurious Deletions|Worktree Branch Commits with Spurious Deletions]]
- [[graphify/communities/code 17 nodes|code: 17 nodes]]
- [[graphify/communities/code rule|code: rule]]
- [[graphify/communities/extractErrorMessage()|extractErrorMessage()]]
- [[graphify/communities/n8n Workflow Orchestrator for LLM Rule Ingestion and Queries|n8n Workflow Orchestrator for LLM Rule Ingestion and Queries]]
- [[graphify/communities/v4.0 BOT Ontology Bridge|v4.0 BOT Ontology Bridge]]
<!-- graphify:connections:end -->
