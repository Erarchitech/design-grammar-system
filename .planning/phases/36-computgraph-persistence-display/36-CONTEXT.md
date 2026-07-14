# Phase 36 Context: Computgraph Persistence and Graph Layer Display

**Milestone:** v9.0 AI Workflow Intelligence (restructured 2026-07-08)
**Requirements:** CGPD-01..05
**Depends on:** Phase 32 (serializer/ids); Phase 32.1 (cross-platform `dgId` — every published entity carries it); Phase 35 (confirmed structures — though a fully hand-tagged canvas can publish without Phase 35).

## What this phase is

Confirmed canvas structure becomes a persistent Neo4j subgraph — the ontology's Computgraph layer gets its first runtime data — and the ui-v2 graph viewer renders it as a distinct, filterable layer.

## Decided

1. **`POST /computgraph/publish`** (app.py): input = confirmed `cgContextJson v1` (only `source: tagged|recognized` entities; untagged never publishes). Label/relation mapping per `../32-computgraph-serialization-core/32-RESEARCH.md` §2:
   - Nodes: `Object` (`objectName`, optional `classIri`), `Behavior`, `Algorithm` (`algorithmName`, `algIndex`), `Procedure` (`procedureName`, `procIndex`), `Pattern` (`patternName`), `Parameter` (`parameterName`, `paramKind` ∈ Variable|Constant|Emergent, `dataType` ∈ Float|Integer|Text|Boolean|Geometry, `domainMin/Max/Step` when slider), `Interface` (`interfaceName`, `ifaceType` ∈ Input|Output) — every node `graph:'Computgraph'`, `project`
   - Relations: `HAS_BEHAVIOR`, `HAS_ALGORITHM`, `HAS_PROCEDURE`, `HAS_PATTERN`, `PATTERN_HOST_TO`, `HAS_PARAMETER`, `HAS_INTERFACE`, `PARAM_LINK`; optional `REFERS_TO` from `Object` to the OntoGraph `Class` when `classIri` present (cross-layer bridge, mirrors Metagraph atoms → OntoGraph pattern)
2. **MERGE keys:** `cgId` = deterministic id from Phase 32 (`cg:<alg>:<kind>:<conventionName>`) + `definitionId` + `project`. Re-publish updates properties, never duplicates (`MERGE (n:Pattern {cgId, definitionId, project})`). Entities absent from a re-publish are **not** auto-deleted in v9.0 — stale-entity cleanup is reported, deletion is explicit (avoid silent data loss; note in report). Every published node additionally carries its Phase 32.1 `dgId` property (cross-platform identity — representation bindings and shared properties key on it and must survive re-publish; see `spec/DG-ID.md`).
3. **Provenance per node:** `source` (tagged | recognized), `provider`/`model` (recognized only, from the recognition response), `confidence` (recognized only), `definitionId`, `fileName`, `publishedAt` (ISO).
4. **Plugin publish path (CGPD-05):** a `Publish` trigger on DG STRUCTURE CONFIRM (or a small **DG COMPUTGRAPH PUBLISH** component — decide in planning) that POSTs the confirmed context to `/computgraph/publish`, following the `ValidationPublishClient` pattern (static HttpClient, `dataServiceUrl` input, camelCase JSON, status output). Confirm→publish completes without leaving Grasshopper.
5. **Schema propagation checklist** (the CLAUDE.md standing rule): `cypher_template.txt`, `training/dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md schema tables (add Computgraph rows to Node Labels + Relationships), n8n/orchestrator prompts via the Phase 29 catalog (Computgraph block), `.github/copilot-instructions.md`, README.md.
6. **ui-v2 display** (NOT legacy `graph-viewer/` — v8.0 cutover): Computgraph layer in the orbital datascape (`ui-v2/src/graph/` ring mapper + styling for the 7 new labels; per-project filter toggle in the Graph screen). Node display property: `objectName`/`algorithmName`/`procedureName`/`patternName`/`parameterName`/`interfaceName` respectively.

## Constraints

- Project isolation on every node — the single-database convention is non-negotiable.
- Publish is transactional per definition (one Cypher transaction; partial writes must not survive failure).
- `graph:'Computgraph'` exactly (v4-era `ValidationGraph`→`ValidGraph` migration pain — get the string right once).
- Idempotency proven by count query in tests, not assumed.
- data-service Cypher goes through parameterized queries (no string-interpolated names).

## Open for planning

- Whether `Behavior` gets its own node or is collapsed (ontology says Object→hasBehavior→Behavior→hasAlgorithm→Algorithm; keep the node — cross-layer queries and v10 need it).
- Wire topology persistence: v9.0 persists the ontology entities; raw node/wire substrate (`CgNode`/`CgWire`) is NOT persisted per-node in v9.0 (volume) — store the full `cgContextJson` as a property/attachment on `Algorithm` (`contextJson`) for reconstruction, revisit granular persistence in v10.
- ui-v2 ring mapping: new ring vs shared ring with per-label colors.

## Verification sketch

Publish confirmed Frame → `MATCH (o:Object {project:$p})-[:HAS_BEHAVIOR]->()-[:HAS_ALGORITHM]->(a)-[:HAS_PROCEDURE]->(pr)` returns 1/1/2 with patterns/params/interfaces at expected counts; publish again → identical counts; provenance query returns source/model/timestamp per node; ui-v2 Graph screen shows the layer, filterable per project.
