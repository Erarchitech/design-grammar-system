# Phase 36: Computgraph Persistence and Graph Layer Display - Research

**Researched:** 2026-07-19
**Domain:** Neo4j persistence endpoint (FastAPI/Python) + Grasshopper HTTP publish component (C#) + ui-v2 graph-viewer layer wiring (React/JS)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Decided (locked)

1. **`POST /computgraph/publish`** (app.py): input = confirmed `cgContextJson v1` (only `source: tagged|recognized` entities; untagged never publishes). Label/relation mapping per `../32-computgraph-serialization-core/32-RESEARCH.md` §2:
   - Nodes: `Object` (`objectName`, optional `classIri`), `Behavior`, `Algorithm` (`algorithmName`, `algIndex`), `Procedure` (`procedureName`, `procIndex`), `Pattern` (`patternName`), `Parameter` (`parameterName`, `paramKind` ∈ Variable|Constant|Emergent, `dataType` ∈ Float|Integer|Text|Boolean|Geometry, `domainMin/Max/Step` when slider), `Interface` (`interfaceName`, `ifaceType` ∈ Input|Output) — every node `graph:'Computgraph'`, `project`
   - Relations: `HAS_BEHAVIOR`, `HAS_ALGORITHM`, `HAS_PROCEDURE`, `HAS_PATTERN`, `PATTERN_HOST_TO`, `HAS_PARAMETER`, `HAS_INTERFACE`, `PARAM_LINK`; optional `REFERS_TO` from `Object` to the OntoGraph `Class` when `classIri` present
2. **MERGE keys:** `cgId` = deterministic id from Phase 32 (`cg:<alg>:<kind>:<conventionName>`) + `definitionId` + `project`. Re-publish updates properties, never duplicates (`MERGE (n:Pattern {cgId, definitionId, project})`). Entities absent from a re-publish are **not** auto-deleted in v9.0 — stale-entity cleanup is reported, deletion is explicit. Every published node additionally carries its Phase 32.1 `dgId` property.
3. **Provenance per node:** `source` (tagged | recognized), `provider`/`model` (recognized only), `confidence` (recognized only), `definitionId`, `fileName`, `publishedAt` (ISO).
4. **Plugin publish path (CGPD-05):** a `Publish` trigger on DG STRUCTURE CONFIRM (or a small **DG COMPUTGRAPH PUBLISH** component — decide in planning) that POSTs the confirmed context to `/computgraph/publish`, following the `ValidationPublishClient` pattern.
5. **Schema propagation checklist**: `cypher_template.txt`, `training/dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md schema tables (add Computgraph rows to Node Labels + Relationships), n8n/orchestrator prompts via the Phase 29 catalog (Computgraph block), `.github/copilot-instructions.md`, README.md.
6. **ui-v2 display** (NOT legacy `graph-viewer/`): Computgraph layer in the orbital datascape; per-project filter toggle in the Graph screen. Node display property: `objectName`/`algorithmName`/`procedureName`/`patternName`/`parameterName`/`interfaceName` respectively.

### Constraints

- Project isolation on every node — the single-database convention is non-negotiable.
- Publish is transactional per definition (one Cypher transaction; partial writes must not survive failure).
- `graph:'Computgraph'` exactly (v4-era `ValidationGraph`→`ValidGraph` migration pain — get the string right once).
- Idempotency proven by count query in tests, not assumed.
- data-service Cypher goes through parameterized queries (no string-interpolated names).

### Claude's Discretion (open for planning)

- Whether `Behavior` gets its own node or is collapsed (ontology says Object→hasBehavior→Behavior→hasAlgorithm→Algorithm; keep the node — cross-layer queries and v10 need it) — **CONTEXT.md leans "keep the node."**
- Wire topology persistence: v9.0 persists the ontology entities; raw node/wire substrate (`CgNode`/`CgWire`) is NOT persisted per-node in v9.0 — store the full `cgContextJson` as a property/attachment on `Algorithm` (`contextJson`) for reconstruction, revisit granular persistence in v10.
- ui-v2 ring mapping: new ring vs shared ring with per-label colors. **UI-SPEC.md has since locked this: distinct ring position between SpecGraph and ValidGraph, 3 orbits, no new accent color (see below).**

### Deferred Ideas (OUT OF SCOPE)

- Nothing explicitly deferred within Phase 36 beyond what CONTEXT.md's "Open for planning" section resolves during this planning pass. Script-part generation, on-canvas editing, and structural/consult validation (SVAL) are out of Phase 36's scope per REQUIREMENTS.md and belong to Phase 37/v10.

### UI-SPEC.md binding contract (locked, supersedes "Claude's Discretion" ring-mapping item above)

- **Layer key fix (blocking):** `ui-v2/src/graph/buildRings.js` currently uses `"ComputGraph"` (wrong casing) in `LAYER_ORDER` and `ORBITS`. Must become `"Computgraph"` exactly, in the same list position (between `SpecGraph` and `ValidGraph`).
- **Orbit assignment (3 orbits, 7 labels):** `Object/Behavior/Algorithm` → orbit 0 (identity chain); `Procedure/Pattern` → orbit 1 (structural decomposition); `Parameter/Interface` → orbit 2 (leaf entities).
- **Captions:** `CAPTIONS.Object=["objectName"]`, `Algorithm=["algorithmName"]`, `Procedure=["procedureName"]`, `Pattern=["patternName"]`, `Parameter=["parameterName"]`, `Interface=["interfaceName"]`. `Behavior` has NO caption entry — intentionally falls through to the generic fallback (`props.label || props.name || props.id || label`), rendering the literal string `"Behavior"`.
- **No new color/accent** — monochrome + Signal Red system stays; Computgraph nodes render in `TH.ink`/`TH.dim` like every other layer, never a new hue.
- **Per-project filter (CGPD-04) is already satisfied** by `GraphScreen`'s existing `project` prop scoping `fetchGraph(project)` — no new UI control.
- **Large-property guard (new risk):** `contextJson` on `Algorithm` nodes can be multi-KB. `GraphScreen.jsx`'s `rowsOf()` (both the 6-row hover mapper at line ~876 and the 24-row detail mapper at line ~897) must truncate any property value longer than 200 chars (`value.slice(0, 200) + "…"`) before handing rows to `PropertiesTable`. One-line change, no new component.
- **No new components/CSS/copy** — this phase adds zero new UI primitives; it wires 7 new labels into the existing ring-mapper and existing panels only.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CGPD-01 | `POST /computgraph/publish` persists a confirmed structure to Neo4j — labels `Object\|Behavior\|Algorithm\|Procedure\|Pattern\|Parameter\|Interface` with `graph:'Computgraph'` + project isolation; 8 relationship types | §Architecture Patterns (endpoint shape), §Code Examples (Cypher publish pattern), §Common Pitfalls (transaction atomicity, label-string exactness) |
| CGPD-02 | Publishing is MERGE-idempotent on stable entity ids (definition id + convention name); re-publish creates zero duplicates | §Common Pitfalls (dgId/cgId anchor mismatch — the load-bearing finding), spec/DG-ID.md normative note quoted verbatim |
| CGPD-03 | Every published node carries provenance (source, provider/model, definitionId, timestamp) queryable via Cypher | §Code Examples (provenance property set), matches `store_validation_run`'s existing provenance-property precedent |
| CGPD-04 | ui-v2 graph viewer renders the Computgraph layer distinctly, filterable per project; schema propagation checklist completed | §UI-SPEC binding contract above (already locked), §Schema Propagation Checklist findings below |
| CGPD-05 | A publish path exists from the plugin (DG COMPUTGRAPH PUBLISH trigger, ValidationPublishClient HTTP pattern) so confirm→publish completes without leaving Grasshopper | §Architecture Patterns (component decision), §Common Pitfalls (StructureConfirmComponent's zero-network invariant) |
</phase_requirements>

## Summary

Phase 36 is the first runtime writer of the Computgraph layer: it takes the `cgContextJson v1` envelope Phase 32 already serializes (and Phase 32.1 already stamps with deterministic `dgId`s) and turns it into real Neo4j nodes/relationships, then makes that layer visible in the existing ui-v2 datascape. Nothing about this phase requires new external packages — it is 100% composition of patterns already shipped in this codebase: the FastAPI thin-route + domain-module split (`dg_identity.py`, `cg_recognition.py`), the `ValidationPublishClient` static-HttpClient GH component pattern, and `buildRings.js`'s existing layer/orbit/caption tables.

Two facts from adjacent phases are load-bearing for how this phase must be planned, and neither is spelled out in CONTEXT.md — they were discovered by reading Phase 32/32.1 code directly:

1. **The MERGE-key anchor used by `/identity/mint` (`MERGE (e {cgId, definitionId, project})`) creates a completely unlabeled node.** Neo4j's `MERGE` matches on the full pattern *including labels* — a later `MERGE (n:Pattern {cgId, definitionId, project})` from the publish endpoint will NOT coincide with a pre-minted unlabeled node; it will create a second, duplicate node and silently orphan the first. `spec/DG-ID.md`'s own text says these must "coincide as ONE node, never duplicate" but the current `mint_identity` implementation cannot deliver that against a labeled MERGE. The safe resolution for Phase 36: **do not call `dg_identity.mint_identity()` from the publish path.** Instead, call the pure function `dg_identity.compute_dg_id(project, definition_id, cg_id)` directly (no DB round-trip, no anchor node) to get the `dgId` string, and set it as a property inside the SAME `MERGE (n:Pattern {cgId, definitionId, project}) SET n.dgId = $dgId, ...` statement the publish endpoint already needs to run. This sidesteps the label mismatch entirely and is simpler than trying to fix `mint_identity`'s anchor semantics in this phase.
2. **`CgObject` collapses `Object`/`Behavior` in the `cgContextJson v1` envelope — there is no `Behavior` entity in the wire format, and `CgAlgorithm` carries no `DgId` field.** `CgContextDgIdAssigner.AssignDgIds` (the actual C# code, verified) only stamps `dgId` on Object/Procedure/Pattern/Parameter/Interface — never Algorithm, and there's no Behavior model at all. This matches DGID-01's literal scope ("Object, Procedure, Pattern, Parameter, Interface") but contradicts `spec/DATABASE.md` line 113, which currently (incorrectly) lists `dgId` as present on `:Algorithm` too — a stale-doc bug this phase's schema-propagation pass should fix. Because the envelope has no `Behavior` entity, **the publish endpoint must synthesize the `Behavior` node and its MERGE key itself** (e.g. `MERGE (b:Behavior {definitionId:$definitionId, project:$project})` — no `cgId`/`dgId` needed since it isn't a DGID-01 entity and there is exactly one per Object per definition).

**Primary recommendation:** Build the publish logic as a new `data-service/computgraph_publish.py` module (mirroring the `dg_identity.py`/`cg_recognition.py` split — domain logic separate from the thin `app.py` route, testable with a duck-typed fixture session with zero live Neo4j), issue ONE parameterized Cypher statement per publish call (chained `UNWIND`/`WITH` blocks covering Object→Behavior→Algorithm→Procedures→[Patterns,Parameters,Interfaces]→relationships) so `write_query()`'s existing single-auto-commit-transaction semantics satisfy "one Cypher transaction" without any new transaction-API surface, and build the plugin side as a brand-new `ComputgraphPublishComponent`/`ComputgraphPublishClient` pair — not an addition to `StructureConfirmComponent`, which currently has a grep-enforced zero-network-call invariant from Phase 35.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Confirmed-structure re-extraction + dgId stamping | Grasshopper Plugin (DG.Core/DG.Grasshopper) | — | `CanvasContextExtractor` + `CanvasAnnotationParser` + `CgContextDgIdAssigner` already run in-process on the canvas; re-extracting at publish time (not trusting a stale in-memory copy) matches the Phase 35 "read-before-write" precedent |
| HTTP publish transport | Grasshopper Plugin → Data Service | — | `ComputgraphPublishClient` (new, mirrors `ValidationPublishClient`) POSTs `cgContextJson` to `/computgraph/publish`; no Neo4j driver in the plugin process |
| Cypher construction, MERGE-idempotent write, provenance stamping | API/Backend (data-service) | — | `computgraph_publish.py` owns all Cypher; parameterized, project-scoped, single-transaction |
| Persistence | Database/Storage (Neo4j) | — | `graph:'Computgraph'` partition; MERGE keys `cgId+definitionId+project` (typed entities) or `definitionId+project` (Behavior) |
| Schema-consistency surfaces (docs, catalogs, validator allow-lists) | API/Backend (data-service) + repo docs | — | `cypher_template.txt`, `dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md, `.github/copilot-instructions.md`, README.md; the Phase 29 OWL-derived catalog needs verification only, not an edit (see Common Pitfalls) |
| Graph-viewer layer rendering, project filter | Frontend Server/Client (ui-v2, client-rendered SPA) | — | `buildRings.js` (pure function, browser-side) + existing `GraphScreen.jsx` fetch/panel machinery; no new backend endpoint needed for read (existing `fetchGraph()` already does `MATCH (n) WHERE n.project = $project`) |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | unpinned (repo `requirements.txt`) | `POST /computgraph/publish` route | Already the framework for every data-service endpoint in this repo; zero new dependency |
| neo4j (Python driver) | unpinned (repo `requirements.txt`) | Cypher execution via existing `driver`/`write_query`/`read_many` helpers | Already used by every persistence path in app.py |
| pydantic | via FastAPI | Request body models (`ComputgraphPublishRequest`) | Matches `ComputgraphContextPullRequest`/`RecognizeRequest`/`MintRequest` precedent |
| httpx | unpinned (repo `requirements.txt`) | Not needed by this endpoint directly (no outbound call); already used elsewhere in app.py for the SHACL sidecar pattern if a similar proxy call is ever needed | Existing dependency, no version change required |
| System.Net.Http (BCL) | .NET 7/9 built-in | `ComputgraphPublishClient`'s static `HttpClient`, mirrors `ValidationPublishClient` exactly | Zero new NuGet package — same pattern as every other GH→data-service publish path in this repo |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| React 18 / Vite 5 (existing `ui-v2/`) | ^18.3.1 / ^5.4.14 | No new component — `buildRings.js` edits only | Already the only frontend stack in scope per UI-SPEC.md |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single parameterized Cypher statement with chained UNWIND/WITH blocks | Neo4j explicit transaction API (`session.execute_write` with multiple `tx.run()` calls) | The explicit-transaction API is more idiomatic for multi-statement atomicity and is used by neo4j driver docs as the standard pattern, but **this repo has zero existing precedent for it** — every write path (`store_validation_run`, `mint_identity`, `_persist_shacl_report`) uses the single-statement `write_query()` helper. A single UNWIND-chained statement achieves the same one-transaction guarantee with zero new code pattern to introduce; use the explicit-transaction API only if the single-statement approach proves unwieldy at review time. |
| `data-service/computgraph_publish.py` new module | Inline in `app.py` like `store_validation_run` | `store_validation_run` is NOT actually atomic across its two separate `write_query()` calls (run node write, then entity rows write) — it is the wrong precedent to copy for a phase whose CONTEXT.md explicitly demands one-transaction atomicity. A new module keeps the Cypher testable via a duck-typed session fixture (Phase 32.1's `test_dg_identity.py` `FakeGraph`/`FakeResult` pattern) without touching `app.py`'s already-large surface. |

**Installation:**
```bash
# No new packages. Verify existing pins are unchanged:
pip show fastapi neo4j httpx pydantic   # data-service/requirements.txt, unpinned versions
```

**Version verification:** `data-service/requirements.txt` pins no explicit versions for `fastapi`, `httpx`, `neo4j` — confirmed via direct read 2026-07-19. No `npm install` needed in `ui-v2/` (no new frontend dependency). No new NuGet package needed in `DG.Grasshopper` (BCL `HttpClient`, same as `ValidationPublishClient.cs`).

## Package Legitimacy Audit

**No new external packages are introduced by this phase.** Every dependency (`fastapi`, `neo4j`, `httpx`, `pydantic` in data-service; BCL `System.Net.Http`/`System.Text.Json` in DG.Grasshopper; React/Vite in ui-v2) already exists in the repo and has been verified/used across 30+ prior phases. Package Legitimacy Gate is not applicable — skip the registry/postinstall checks.

**Packages removed due to [SLOP] verdict:** none (no packages evaluated).
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Grasshopper Plugin (DG.Grasshopper) ───────────────────────────┐
│                                                                                              │
│  DG STRUCTURE CONFIRM ──(canvas mutation only, zero network — Phase 35 invariant)──┐        │
│                                                                                     │        │
│  Live GH_Document (confirmed convention groups: source=tagged|recognized)          │        │
│         │                                                                          │        │
│         ▼ (re-extract, read-before-write — Phase 35 precedent)                     │        │
│  CanvasContextExtractor.ExtractRaw() → RawCanvas                                   │        │
│         │                                                                          │        │
│         ▼                                                                          │        │
│  CanvasAnnotationParser.Parse(RawCanvas) → CgContext                               │        │
│         │                                                                          │        │
│         ▼                                                                          │        │
│  CgContextDgIdAssigner.AssignDgIds(context, project) → CgContext (+dgId per        │        │
│         │   entity: Object/Procedure/Pattern/Parameter/Interface — NOT Algorithm)  │        │
│         ▼                                                                          │        │
│  ComputgraphContextSerializer.Serialize(context) → cgContextJson string            │        │
│         │                                                                          │        │
│         ▼                                                                          │        │
│  NEW: ComputgraphPublishComponent (DG COMPUTGRAPH PUBLISH) ◄───────────────────────┘        │
│         │  (rising-edge Publish trigger, mirrors StructureConfirmComponent's Apply pattern) │
│         ▼                                                                                   │
│  NEW: ComputgraphPublishClient.Publish(cgContextJson, dataServiceUrl)                       │
│         │  static HttpClient, camelCase JSON — mirrors ValidationPublishClient.cs           │
└─────────┼─────────────────────────────────────────────────────────────────────────────────┘
          │ HTTP POST /computgraph/publish
          ▼
┌─────────────────────────── data-service (FastAPI) ─────────────────────────────────────────┐
│  app.py: thin route post_computgraph_publish(payload)                                       │
│         │  delegates to →                                                                   │
│         ▼                                                                                   │
│  NEW: computgraph_publish.py: publish_structure(session, project, cg_context)               │
│         │  1. compute_dg_id() inline (pure fn, NOT mint_identity — avoids unlabeled-node     │
│         │     MERGE mismatch, see Common Pitfalls)                                           │
│         │  2. build ONE parameterized Cypher (UNWIND/WITH chain: Object→Behavior→Algorithm  │
│         │     →Procedures→[Patterns,Parameters,Interfaces]→8 relationship types)             │
│         │  3. single write_query() call = single Neo4j auto-commit transaction              │
│         ▼                                                                                   │
└─────────┼─────────────────────────────────────────────────────────────────────────────────┘
          │ Bolt (parameterized Cypher, one transaction)
          ▼
┌─────────────────────────── Neo4j ───────────────────────────────────────────────────────────┐
│  graph:'Computgraph' partition                                                              │
│  (:Object)-[:HAS_BEHAVIOR]->(:Behavior)-[:HAS_ALGORITHM]->(:Algorithm)                      │
│       (:Algorithm)-[:HAS_PROCEDURE]->(:Procedure)                                           │
│            (:Procedure)-[:HAS_PATTERN]->(:Pattern)-[:PATTERN_HOST_TO]->(:Pattern) (nesting) │
│            (:Procedure)-[:HAS_PARAMETER]->(:Parameter)                                      │
│            (:Procedure)-[:HAS_INTERFACE]->(:Interface)                                      │
│            (:Parameter)-[:PARAM_LINK]->(:Interface)                                         │
│  (:Object)-[:REFERS_TO]->(:Class)  (optional cross-layer bridge, OntoGraph)                 │
└─────────┬─────────────────────────────────────────────────────────────────────────────────┘
          │ Neo4j HTTP tx/commit (existing, unchanged — via nginx /neo4j proxy)
          ▼
┌─────────────────────────── ui-v2 (React/Vite, browser) ────────────────────────────────────┐
│  graphApi.js: fetchGraph(project) → MATCH (n) WHERE n.project = $project (UNCHANGED)         │
│         │                                                                                    │
│         ▼                                                                                   │
│  EDIT: buildRings.js — LAYER_ORDER "ComputGraph"→"Computgraph", ORBITS (3 buckets),          │
│         CAPTIONS (6 of 7 labels; Behavior falls through to generic fallback)                 │
│         │                                                                                    │
│         ▼                                                                                   │
│  GraphScreen.jsx — EDIT: rowsOf() truncates values >200 chars (contextJson guard)            │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
data-service/
├── app.py                      # + thin route: POST /computgraph/publish
├── computgraph_publish.py      # NEW — mirrors dg_identity.py/cg_recognition.py split
└── tests/
    └── test_computgraph_publish.py   # NEW — duck-typed FakeGraph/FakeResult (mirrors test_dg_identity.py)

DG/src/DG.Grasshopper/
├── Components/
│   └── ComputgraphPublishComponent.cs   # NEW — DG COMPUTGRAPH PUBLISH
├── Validation/                          # (existing folder — reuse, don't create Computgraph/)
│   ├── ComputgraphPublishClient.cs      # NEW — mirrors ValidationPublishClient.cs
│   └── ComputgraphPublishContract.cs    # NEW — mirrors ValidationPublishContract.cs
└── Properties/
    └── ComputgraphPublish24.png         # NEW icon (copy an existing 24px placeholder per precedent)

ui-v2/src/graph/
└── buildRings.js                # EDIT ONLY — LAYER_ORDER, ORBITS, CAPTIONS

ui-v2/src/screens/
└── GraphScreen.jsx              # EDIT ONLY — rowsOf() truncation guard
```

### Pattern 1: Single-statement multi-entity atomic publish (UNWIND/WITH chain)

**What:** One parameterized Cypher string handles the entire confirmed structure (potentially dozens of Pattern/Parameter/Interface nodes) as a sequence of `UNWIND $rows AS row MERGE (...) SET (...) WITH ...` blocks, executed through the existing `write_query()` helper (single `session.run(...).consume()` = one Neo4j auto-commit transaction).

**When to use:** Whenever CONTEXT.md's "one Cypher transaction; partial writes must not survive failure" constraint applies and the write spans more than one node/relationship type — which is every publish call in this phase.

**Example (shape, not final):**
```python
# Source: pattern derived from data-service/app.py store_validation_run (session.run shape)
# and dg_identity.py mint_identity (single MERGE anchor) — CONTEXT.md's transactional
# constraint requires collapsing what would otherwise be N separate write_query() calls
# into ONE statement.
write_query(
    """
    MERGE (o:Object {objectDgId:$objectDgId, definitionId:$definitionId, project:$project})
    SET o.objectName = $objectName, o.classIri = $classIri, o.dgId = $objectDgId,
        o.source = $objectSource, o.definitionId = $definitionId, o.fileName = $fileName,
        o.publishedAt = $publishedAt, o.graph = 'Computgraph', o.project = $project
    MERGE (b:Behavior {definitionId:$definitionId, project:$project})
    SET b.graph = 'Computgraph', b.project = $project, b.publishedAt = $publishedAt
    MERGE (o)-[:HAS_BEHAVIOR]->(b)
    WITH o, b
    UNWIND $algorithms AS alg
      MERGE (a:Algorithm {algIndex:alg.index, definitionId:$definitionId, project:$project})
      SET a.algorithmName = alg.name, a.graph = 'Computgraph', a.project = $project,
          a.contextJson = alg.contextJson, a.publishedAt = $publishedAt
      MERGE (b)-[:HAS_ALGORITHM]->(a)
      WITH a, alg
      UNWIND alg.procedures AS proc
        MERGE (pr:Procedure {cgId:proc.cgId, definitionId:$definitionId, project:$project})
        SET pr.procedureName = proc.name, pr.procIndex = proc.index, pr.dgId = proc.dgId,
            pr.source = proc.source, pr.graph = 'Computgraph', pr.project = $project,
            pr.definitionId = $definitionId, pr.publishedAt = $publishedAt
        MERGE (a)-[:HAS_PROCEDURE]->(pr)
        // ... nested UNWIND for proc.patterns / proc.parameters / proc.interfaces follows
    """,
    {...}
)
```

### Pattern 2: Deterministic dgId computed inline, never via `mint_identity`

**What:** Call `dg_identity.compute_dg_id(project, definition_id, cg_id)` (pure function, no DB call) to get each entity's `dgId`, and set it as a plain property in the SAME `MERGE (n:Label {cgId, definitionId, project})` statement the publish endpoint already builds.

**When to use:** Every entity that has a `cgId` in the envelope (Object uses the synthetic key `"obj:" + objectName`, matching `CgContextDgIdAssigner`'s C# convention exactly; Procedure/Pattern/Parameter/Interface use their `id` field verbatim).

**Why not `mint_identity()`:** it MERGEs an anonymous (label-less) anchor node (`MERGE (e {cgId, definitionId, project})`) — Neo4j MERGE matches on label + properties together, so a labeled `MERGE (n:Pattern {...})` from publish will never coincide with that anchor and will create a duplicate node. See Common Pitfalls.

### Pattern 3: Component split mirrors `ValidationPublishClient`/`ValidationPublishContract`, NOT `StructureConfirmComponent`

**What:** A dedicated `ComputgraphPublishComponent` (rising-edge `Publish` trigger, `Status`/`RunId`-equivalent outputs) that re-extracts the live canvas, assigns dgIds, serializes, and calls a dedicated `ComputgraphPublishClient.Publish(...)` static method — the exact three-file shape (`*Component.cs` + `*Client.cs` + `*Contract.cs`) already used for validation publish.

**When to use:** This phase's CGPD-05 deliverable. Do NOT add a network call inside `StructureConfirmComponent.cs` — see Common Pitfalls.

### Anti-Patterns to Avoid

- **Multiple sequential `write_query()` calls for one publish** (mirroring `store_validation_run`'s two-call shape): breaks the "one Cypher transaction" constraint — a crash between calls leaves partial Computgraph state. Use Pattern 1 instead.
- **Calling `dg_identity.mint_identity()` from the publish path:** creates a second, unlabeled, orphaned node per entity (see Pattern 2). Use `compute_dg_id()` directly.
- **Adding `HttpClient`/data-service calls to `StructureConfirmComponent.cs`:** violates the Phase 35 grep-enforced source assertion (`grep -cE 'HttpClient|data-service|neo4j|Neo4j' StructureConfirmComponent.cs == 0`) that is part of that component's locked test coverage. Build a separate component.
- **Trusting the LLM's/preview-time `suggestedName` for the published entity name:** Phase 35's `StructureConfirmComponent` already re-derives the permanent name at Accept time (read-before-write). The publish component should re-extract the CURRENT canvas state (post-confirm), not cache anything from before Confirm ran.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deterministic dgId computation | A second hashing implementation in Python or a call through the identity registry's anchor node | `dg_identity.compute_dg_id()` (already exists, already golden-vector-tested) | Cross-language parity (C# `DgIdMintingService.Mint` ↔ Python `compute_dg_id`) is a locked Phase 32.1 contract; a second implementation risks silent drift |
| Camel-case JSON HTTP client from Grasshopper | A raw `HttpClient` + manual `JsonSerializer` calls scattered in the new component | `ComputgraphPublishClient` mirroring `ValidationPublishClient`'s static `HttpClient` + `JsonSerializerOptions{PropertyNamingPolicy=CamelCase}` | Single owner of the HTTP/JSON contract, consistent error surfacing (`InvalidOperationException` with status+body) |
| Structured error responses on the FastAPI side | Ad hoc `HTTPException(...)` raises | `_structured_error_response(message, hint, code, status)` — the repo-wide What+Where+How-to-fix pattern used by every other endpoint (`SPECKLE_CONFIG_MISSING`, `DGID_NOT_FOUND`, `RECOGNIZE_REQUEST_INVALID`, …) | Consistency for the UI's existing error-surfacing conventions; a bespoke error shape here would be the only inconsistent endpoint in the file |
| Canvas re-extraction/parsing | Any new parsing logic in the publish component | `CanvasContextExtractor.ExtractRaw()` + `CanvasAnnotationParser.Parse()` + `CgContextDgIdAssigner.AssignDgIds()` (all shipped, Phase 32/32.1) | These are the single source of truth for the annotation grammar; re-implementing risks drift from the Frame fixture's pinned acceptance test |

**Key insight:** Every piece this phase needs already exists somewhere in the codebase in a slightly different shape (validation publish for the HTTP client pattern, identity registry for dgId computation, recognition/context-pull for the FastAPI thin-route pattern, `buildRings.js` for the ring-mapper tables). The work is composition and one genuinely new pattern (atomic multi-entity Cypher), not net-new architecture.

## Common Pitfalls

### Pitfall 1: `mint_identity`'s label-less MERGE anchor cannot coincide with publish's labeled MERGE

**What goes wrong:** If the publish endpoint calls `dg_identity.mint_identity(session, project, definition_id, cg_id)` to get a `dgId` before writing the labeled entity node, Neo4j creates TWO nodes: one unlabeled (from `mint_identity`'s `MERGE (e {cgId, definitionId, project})`) and one labeled (from publish's own `MERGE (n:Pattern {cgId, definitionId, project})`). `spec/DG-ID.md` explicitly requires them to "coincide as ONE node, never duplicate" but the current `mint_identity` implementation cannot deliver that.

**Why it happens:** Neo4j's `MERGE` clause matches on the FULL pattern including any label(s) specified. `(e {props})` and `(n:Pattern {props})` are different patterns even with identical properties.

**How to avoid:** In the publish path, call the pure function `dg_identity.compute_dg_id(project, definition_id, cg_id)` (no DB interaction) to get the `dgId` string, then set it as a plain property inside the publish endpoint's own labeled `MERGE`. Never call `mint_identity()` from the publish flow.

**Warning signs:** A count query after re-publish shows MORE nodes than expected even though `cgId`/`definitionId`/`project` values look identical — check for an unlabeled duplicate via `MATCH (n) WHERE n.cgId = $cgId AND NOT n:Pattern RETURN n`.

### Pitfall 2: `graph:'Computgraph'` string exactness (repeat of the ValidationGraph→ValidGraph class of bug)

**What goes wrong:** A typo or casing drift (`ComputGraph`, `Computgraph `, `computgraph`) anywhere across the publish Cypher, `buildRings.js`, `dg_context.py` allow-lists, or `spec/DATABASE.md` creates an invisible-until-queried mismatch — exactly the historical `graph:'ValidationGraph'` (pre-v4) vs `graph:'ValidGraph'` migration pain documented in CLAUDE.md's Known Gotchas.

**Why it happens:** The string is typed independently in ≥5 places (Cypher literal, `buildRings.js`'s `LAYER_ORDER`, `spec/DATABASE.md`, CLAUDE.md, and any test assertions) with no single source of truth enforcing it.

**How to avoid:** `spec/DG-ID.md` and `spec/DATABASE.md` already document `graph:'Computgraph'` as the correct string (verified via direct read — Computgraph section already exists from Phase 32.1's schema-propagation pass, added for `Representation`/`SharedProperty`). Copy that exact literal everywhere; grep for `Computgraph` (not `ComputGraph`) as a pre-commit sanity check on every file this phase touches.

**Warning signs:** `buildRings.js`'s current stub literally has this bug today (`"ComputGraph"`, capital G) — UI-SPEC.md already flags this as the #1 blocking fix.

### Pitfall 3: `store_validation_run` is NOT a safe atomicity precedent to copy

**What goes wrong:** `store_validation_run` (the nearest existing "publish a subgraph" function) issues 2 separate `write_query()` calls — one for the `ValidationRun` node, one (conditionally) for `ValidationEntity` rows. These are two independent Neo4j auto-commit transactions, not one. If a planner copies this shape for Computgraph publish, a crash between the two calls leaves a partial Computgraph subgraph — directly violating CONTEXT.md's "partial writes must not survive failure" constraint.

**Why it happens:** `store_validation_run` predates Phase 36's explicit atomicity requirement; nothing forced it to be atomic when written.

**How to avoid:** Build ONE parameterized Cypher statement (UNWIND/WITH chain, see Pattern 1) instead of N sequential `write_query()` calls.

### Pitfall 4: `CgObject` has no `Behavior` entity in the wire format — Neo4j needs one anyway

**What goes wrong:** Naively iterating the `cgContextJson` envelope's top-level fields (`object`, `algorithms`) will not produce a `Behavior` node, because `CgContext.Object` (`CgObject.cs`, verified) collapses Object/Behavior into one JSON entity. But CONTEXT.md decision #1 and the OWL ontology both require `Object -[:HAS_BEHAVIOR]-> Behavior -[:HAS_ALGORITHM]-> Algorithm` as three separate Neo4j nodes.

**Why it happens:** The envelope was designed (Phase 32) around what the canvas annotation convention can express (there is no `BEHAVIOR` scribble/group — only `OBJECT - <NAME>` and `<n>_ALGORITHM`); Behavior is purely a Neo4j/ontology-side synthesis with no canvas-side representation.

**How to avoid:** Synthesize the Behavior node server-side: `MERGE (b:Behavior {definitionId:$definitionId, project:$project})` (no `cgId`/`dgId` — it's not a DGID-01 entity and there's exactly one per Object per definition, so `definitionId+project` alone is a sufficient MERGE key).

### Pitfall 5: `spec/DATABASE.md`'s current `dgId` entity list is stale (includes Algorithm; code does not)

**What goes wrong:** `spec/DATABASE.md` line 113 (as of 2026-07-19) reads "Every Computgraph entity node (`:Algorithm`, `:Procedure`, `:Pattern`, `:Parameter`, `:Interface`) carries an optional `dgId` property" — but `CgContextDgIdAssigner.AssignDgIds` (the actual C# implementation, verified directly) never assigns a `DgId` to `CgAlgorithm` (the model has no `DgId` field at all), and DGID-01's own requirement text lists "Object, Procedure, Pattern, Parameter, Interface" — no Algorithm, and (implicitly, since it's not a canvas-taggable entity) no Behavior either.

**Why it happens:** `spec/DATABASE.md`'s Phase 32.1-07 update generalized "Computgraph entity" without cross-checking the actual C# model shapes.

**How to avoid:** Phase 36's schema-propagation pass should correct this line to read `Object, Procedure, Pattern, Parameter, Interface` (dropping `Algorithm`, and NOT adding `Behavior`) — matching the verified C# source of truth, not perpetuating the stale doc.

### Pitfall 6: The Phase 29 OWL-derived Computgraph catalog likely needs verification only, not an edit

**What goes wrong:** CONTEXT.md's schema-propagation checklist item "n8n/orchestrator prompts via the Phase 29 catalog (Computgraph block)" could be read as "add new content to the catalog." Direct inspection of `data-service/dg_knowledge.py`'s `load_computgraph_catalog()` shows it parses the Computgraph portion **directly from `ontology/DesignGrammar-V7.owl`** at runtime — the ontology classes (`dgc:Algorithm`, `Procedure`, `Pattern`, `Parameter`, `Interface`) already exist in the OWL file (Phase 32's own research doc cites their exact line numbers). Phase 36 adds RUNTIME INSTANCES of these ontology concepts; it does not introduce new ontology concepts.

**Why it happens:** The propagation-checklist item name is ambiguous between "update the catalog's content" and "verify the catalog already covers the new runtime shape."

**How to avoid:** Treat this checklist item as a verification task (confirm `load_computgraph_catalog()`'s output still names all 7 Computgraph labels correctly, e.g. via `/context/debug?type=graph_query&project=...`), not a code-change task — unless verification actually surfaces a gap.

### Pitfall 7: `dg_context.py`'s LLM-Cypher-validator allow-lists are a SEPARATE surface from the publish path — do not conflate

**What goes wrong:** `ALLOWED_LABELS`/`ALLOWED_RELATIONSHIPS` in `data-service/dg_context.py` gate LLM-*generated* Cypher for `rule_ingest`/`rule_edit`/`graph_query` request types (CTXA-04). The Computgraph publish endpoint writes Cypher directly from trusted Python code, not from an LLM — it does NOT go through this validator and does NOT need these labels added to unblock publish itself.

**Why it happens:** Both surfaces mention "Computgraph" and live in the same file family, inviting confusion about which propagation is actually required.

**How to avoid:** Only add Computgraph labels/relationships to `ALLOWED_LABELS`/`ALLOWED_RELATIONSHIPS` if a FUTURE phase's `graph_query` NL-to-Cypher flow needs to reference Computgraph nodes (that's Phase 37/40 territory, not 36). For Phase 36 itself, leave `dg_context.py`'s allow-lists untouched unless the planner explicitly decides `graph_query` should already answer Computgraph questions this phase (not required by CGPD-01..05).

## Runtime State Inventory

> Not applicable — this is a greenfield persistence phase (first writer of the Computgraph layer), not a rename/refactor/migration. No prior runtime data references the old scheme; there is no "old scheme" to migrate away from.

## Code Examples

### FastAPI thin route (mirrors `post_computgraph_recognize`/`pull_computgraph_context`)

```python
# Source: pattern verified from data-service/app.py lines 1276-1330 (existing computgraph routes)
class ComputgraphPublishRequest(BaseModel):
    """Body for POST /computgraph/publish. `cg_context` is the confirmed
    cgContextJson v1 envelope (already carries dgId per entity, stamped
    client-side by CgContextDgIdAssigner before serialization)."""
    project: str
    cg_context: dict


@app.post("/computgraph/publish")
def post_computgraph_publish(payload: ComputgraphPublishRequest):
    try:
        with driver.session() as session:
            return computgraph_publish.publish_structure(session, payload.project, payload.cg_context)
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cg_context shape (cgContextJson v1 envelope).",
            "COMPUTGRAPH_PUBLISH_REQUEST_INVALID",
            422,
        )
```

### C# publish client (mirrors `ValidationPublishClient.Publish`)

```csharp
// Source: pattern verified from DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs
internal static class ComputgraphPublishClient
{
    private static readonly HttpClient HttpClient = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public static ComputgraphPublishResponse Publish(string cgContextJson, string project, string dataServiceUrl)
    {
        var endpoint = $"{NormalizeUrl(dataServiceUrl)}/computgraph/publish";
        var request = new ComputgraphPublishRequest { Project = project, CgContext = JsonSerializer.Deserialize<JsonElement>(cgContextJson) };
        using var response = HttpClient.PostAsJsonAsync(endpoint, request, JsonOptions).GetAwaiter().GetResult();
        var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Computgraph publish failed ({(int)response.StatusCode}): {body}");
        return JsonSerializer.Deserialize<ComputgraphPublishResponse>(body, JsonOptions)
            ?? throw new InvalidOperationException("Computgraph publish failed: backend returned an empty response.");
    }
    // NormalizeUrl identical to ValidationPublishClient's private helper.
}
```

### `buildRings.js` fix (locked by UI-SPEC.md — verbatim)

```javascript
// Source: ui-v2/src/graph/buildRings.js (existing file, line 8/17)
const LAYER_ORDER = ["OntoGraph", "Metagraph", "KnowledgeGraph", "SpecGraph", "Computgraph", "ValidGraph"];
// ...
ORBITS.Computgraph = {
  Object: 0, Behavior: 0, Algorithm: 0,
  Procedure: 1, Pattern: 1,
  Parameter: 2, Interface: 2
};
CAPTIONS.Object = ["objectName"];
CAPTIONS.Algorithm = ["algorithmName"];
CAPTIONS.Procedure = ["procedureName"];
CAPTIONS.Pattern = ["patternName"];
CAPTIONS.Parameter = ["parameterName"];
CAPTIONS.Interface = ["interfaceName"];
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Computgraph layer exists only in the OWL ontology + `cgContextJson` envelope (no runtime graph data) | Computgraph layer has live Neo4j instances, queryable and browsable | Phase 36 (this phase) | First runtime consumer of the ontology's Computgraph partition; enables Phase 37 (SVAL structural validation), Phase 38 (GHIN input generation), and Phase 40 (E2E integration) |

**Deprecated/outdated:** N/A — nothing in this phase deprecates prior work; it is additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A single UNWIND/WITH-chained Cypher statement is sufficient to express the full Object→Behavior→Algorithm→Procedures→[Patterns,Parameters,Interfaces]→relationships write in one transaction, without needing Neo4j's explicit multi-statement transaction API | Standard Stack, Pattern 1 | If the nested UNWIND depth (Procedure→Pattern nesting via `PATTERN_HOST_TO`, which requires a self-referential MERGE) proves awkward in one statement, the planner may need to fall back to `session.execute_write()` with multiple `tx.run()` calls in one managed transaction — same atomicity guarantee, more code. Low risk; verify with a Cypher spike against the Frame fixture before finalizing the plan's task breakdown. |
| A2 | `spec/DATABASE.md` line 113's `dgId`-entity list (currently including `:Algorithm`) is simply stale documentation, not evidence of an intended-but-unimplemented `Algorithm.dgId` | Common Pitfalls (Pitfall 5) | If a future phase actually needs `Algorithm.dgId` (e.g. for a v10 script-intelligence use case), correcting the doc now would need to be re-reverted. Low risk — DGID-01's own requirement text and the verified C# assigner code both agree Algorithm is out of scope; this is very likely a genuine doc bug, not a design gap. |
| A3 | The `DG COMPUTGRAPH PUBLISH` component's `Publish` trigger should re-extract the canvas fresh at publish time (not reuse an in-memory `CgContext` cached from an earlier solve) | Architecture Patterns, Anti-Patterns | If a cached/stale context is published instead, the graph could diverge from what STRUCTURE CONFIRM actually left on canvas (e.g. a group renamed after confirm but before publish). This mirrors Phase 35's own "read-before-write" mitigation for the identical class of staleness risk (T-35-06), so the pattern is well-precedented, but the specific re-extraction call site needs to be planned explicitly. |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Does the `contextJson` stored on `Algorithm` need to be the FULL confirmed envelope, or just the algorithm-scoped subset?**
   - What we know: CONTEXT.md says "store the full `cgContextJson` as a property/attachment on `Algorithm` (`contextJson`) for reconstruction." The envelope's `Untagged`/`Nodes`/`Wires` fields are document-scoped, not algorithm-scoped, so "full" literally means the whole received JSON string repeated on every Algorithm node if there's more than one.
   - What's unclear: Whether multiple Algorithms in one definition (rare but structurally possible per the model) should each carry the identical full document, or whether the planner should scope it to just that algorithm's subtree.
   - Recommendation: For v9.0's typical case (one Algorithm per definition, per the Frame convention `1_ALGORITHM`), store the full received JSON string verbatim on the single Algorithm node. Flag as revisit-if-multi-algorithm-definitions-appear; do not over-engineer a per-algorithm JSON slicer for a case not yet observed in the fixture.

2. **What does "stale-entity cleanup is reported, deletion is explicit" (CONTEXT.md) mean for the publish response shape?**
   - What we know: Re-publish must not auto-delete entities absent from the new payload (avoiding silent data loss), but should surface which prior entities are now stale.
   - What's unclear: Whether this requires an extra Cypher read (diff prior published `cgId`s for this `definitionId` against the new payload's set) inside the SAME publish call, or is deferred to a separate future endpoint/phase.
   - Recommendation: A lightweight `OPTIONAL MATCH` diff (prior nodes for this `definitionId`+`project` not present in the new `cgId` set) appended read-only to the publish transaction, returned as a `staleEntityIds` list in the response — no deletion Cypher. This satisfies "reported" without adding deletion logic (explicitly out of scope per CONTEXT.md).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Neo4j | Publish persistence, ui-v2 read | Not probed this session (Docker services not queried live) | Neo4j 5 (per CLAUDE.md tech stack) | — (hard requirement; publish/display cannot function without it — same as every prior persistence phase) |
| data-service (FastAPI container) | `/computgraph/publish` route | Not probed this session | Python 3 / FastAPI | — |
| Live Rhino/Grasshopper session | `DG COMPUTGRAPH PUBLISH` component UAT | Not probed this session (host-machine dependency, not Docker) | Rhino 8 | Deferred to phase-level manual UAT, same precedent as Phases 33/34/35 (net9.0 `DG.Tests` cannot reference the net7.0-windows GH assembly — NU1201 TFM incompatibility, confirmed pre-existing project convention) |

**Missing dependencies with no fallback:** none identified — all three above are standard project dependencies already required by every adjacent phase (32-35); no new environment requirement is introduced by Phase 36.

**Missing dependencies with fallback:** Live-Rhino UAT steps (canvas publish round-trip, Neo4j write, re-publish idempotency observed live) will need the standard phase-level manual UAT deferral already used by Phases 33, 34, and 35 — `DG.Tests` (net9.0) structurally cannot exercise `DG.Grasshopper` (net7.0-windows) components.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (data-service) | pytest, `fastapi.testclient.TestClient(app, raise_server_exceptions=False)`, duck-typed `FakeGraph`/`FakeResult` session fixtures (see `test_dg_identity.py`) — zero live Neo4j required |
| Framework (DG.Core, GH-free) | xUnit (`DG.Tests`, net9.0) |
| Framework (DG.Grasshopper, GH-dependent) | None automatable — requires live Rhino 8/Grasshopper (NU1201 TFM incompatibility blocks `DG.Tests` from referencing `DG.Grasshopper`) |
| Framework (ui-v2) | None — no test runner configured (`package.json` has no test script; consistent with all prior ui-v2 phases 21-27, which rely on manual/visual verification) |
| Config file | `data-service/tests/` (pytest, no dedicated config beyond `sys.path.insert` header pattern); `DG/tests/DG.Tests/DG.Tests.csproj` |
| Quick run command | `python -m pytest data-service/tests/test_computgraph_publish.py -q` |
| Full suite command | `python -m pytest data-service/tests/ -q` && `dotnet test DG/tests/DG.Tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CGPD-01 | Publish confirmed Frame structure yields expected labels/relationships, project-scoped | integration (duck-typed session) | `pytest data-service/tests/test_computgraph_publish.py::test_publish_frame_structure -x` | ❌ Wave 0 |
| CGPD-02 | Re-publishing the same definition changes zero node counts | integration | `pytest data-service/tests/test_computgraph_publish.py::test_republish_is_idempotent -x` | ❌ Wave 0 |
| CGPD-03 | Every published node answers a provenance query (source/model/timestamp) | integration | `pytest data-service/tests/test_computgraph_publish.py::test_provenance_properties_present -x` | ❌ Wave 0 |
| CGPD-04 | ui-v2 shows the Computgraph layer distinctly, filterable per project | manual-only | N/A — browser visual check (no ui-v2 test runner exists) | N/A |
| CGPD-05 | Confirm→publish completes without leaving Grasshopper | manual-only (live Rhino) | N/A — deferred to phase-level UAT per Phase 33/34/35 precedent | N/A |
| — | `dgId` inline-compute path matches golden vector `(p1, frame.gh, cg:1:proc:11_Proc) → dg:BC8E62EE137E2B56` | unit | `pytest data-service/tests/test_computgraph_publish.py::test_dgid_matches_golden_vector -x` | ❌ Wave 0 (reuses the existing golden vector from `test_dg_identity.py`) |

### Sampling Rate

- **Per task commit:** `python -m pytest data-service/tests/test_computgraph_publish.py -q` (and `dotnet build DG/DG.sln -c Release` if any C# file touched)
- **Per wave merge:** `python -m pytest data-service/tests/ -q` && `dotnet test DG/tests/DG.Tests/`
- **Phase gate:** Full suite green before `/gsd-verify-work`; live-Rhino UAT items explicitly deferred and tracked in a `36-UAT.md`, matching Phase 35's precedent.

### Wave 0 Gaps

- [ ] `data-service/tests/test_computgraph_publish.py` — covers CGPD-01/02/03, reusing the `FakeGraph`/`FakeResult` duck-typed session pattern from `test_dg_identity.py` (import the Frame fixture's `cgContextJson` shape from `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` or a Python-side equivalent constructed from the same worked example)
- [ ] No new framework install needed — pytest and xUnit are already configured in this repo

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Endpoint reuses the existing unauthenticated data-service surface (consistent with every other `/computgraph/*` and `/validation/*` route in this repo — no new auth model introduced) |
| V3 Session Management | no | Stateless HTTP publish, no session concept |
| V4 Access Control | no | Project isolation via `project` parameter (not a security boundary in this single-tenant self-hosted deployment, consistent with the rest of the system) |
| V5 Input Validation | yes | Pydantic `ComputgraphPublishRequest` model validates JSON shape at the FastAPI boundary; `cg_context` dict structure should be validated before Cypher parameter binding (reject malformed envelopes with a 422, matching `RECOGNIZE_REQUEST_INVALID`'s precedent) |
| V6 Cryptography | no | `dgId` hashing (SHA-256) is an identity/idempotency mechanism, not a cryptographic security control — no secret material involved |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via unparameterized entity names (e.g. a malicious `procedureName` containing Cypher syntax) | Tampering | Parameterized queries only — every value from `cg_context` must flow through `$paramName` bound parameters, never string-interpolated into the Cypher text (matches the repo-wide convention already enforced in `dg_identity.py`'s module docstring: "identity strings are NEVER f-string/%/.format interpolated into query text") |
| Untagged/unconfirmed entities reaching Neo4j (data integrity, not classic security) | Tampering | Structural guarantee already exists: `CgContext.Algorithms` only ever contains parsed, typed entities with `source: tagged\|recognized`; `Untagged` is a separate field the publish endpoint should never read into the write Cypher — an explicit assertion/test that `payload.cg_context.get("untagged")` is ignored is worth adding |
| Oversized `contextJson` payload (multi-KB raw envelope stored per Algorithm node) causing unbounded property growth on repeated re-publish of large definitions | Denial of Service (mild — self-hosted, single-tenant) | No hard limit currently proposed; UI-SPEC's 200-char truncation is a DISPLAY guard only, not a storage guard. Low risk for v9.0's expected definition sizes (the Frame fixture is well under any practical Neo4j property-size concern); flag as a v10 consideration if definitions grow much larger |

## Sources

### Primary (HIGH confidence — direct code read this session)

- `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` + `ValidationPublishContract.cs` — HTTP publish client pattern
- `data-service/app.py` (lines 280-400, 453-582, 1260-1460, 1634-1743) — `write_query`/`store_validation_run`/`/computgraph/context/pull`/`/computgraph/recognize`/`/identity/*` route patterns
- `data-service/dg_identity.py` — `compute_dg_id`, `mint_identity`'s label-less MERGE anchor (Pitfall 1's source)
- `spec/DG-ID.md` — normative dgId format, MERGE-key contract, "coincide as ONE node" requirement
- `DG/src/DG.Core/Models/Computgraph/*.cs` (CgContext, CgObject, CgAlgorithm, CgProcedure, CgPattern, CgParameter, CgInterface) — verified exact envelope shape, confirmed Behavior is absent from the wire format, confirmed Algorithm has no DgId field
- `DG/src/DG.Core/Services/CgContextDgIdAssigner.cs` — verified exactly which entities get `dgId` (Object/Procedure/Pattern/Parameter/Interface, NOT Algorithm)
- `.planning/phases/32-computgraph-serialization-core/32-RESEARCH.md` — ontology label/relationship mapping (§2), cgContextJson v1 envelope shape (§5)
- `.planning/phases/32-computgraph-serialization-core/32-05-SUMMARY.md` — Frame fixture composition (34 nodes, 2 procedures, nested patterns, interfaces, variables/constants/emergents)
- `.planning/phases/32.1-cross-platform-identity-and-mapping-dg-id/32.1-07-SUMMARY.md` — schema-propagation precedent (which 8 surfaces get touched, "document-only-comment-block" pattern)
- `.planning/phases/35-llm-recognition-canvas-preview/35-04-SUMMARY.md` — `StructureConfirmComponent`'s zero-network-call invariant (Pitfall/Anti-pattern source), read-before-write precedent
- `ui-v2/src/graph/buildRings.js` — current stub (confirmed the `"ComputGraph"` casing bug UI-SPEC.md flags)
- `ui-v2/src/lib/graphApi.js` — confirmed `fetchGraph(project)` already project-scopes with no Computgraph-specific change needed
- `data-service/dg_context.py` (lines 505-560) — confirmed `ALLOWED_LABELS`/`ALLOWED_RELATIONSHIPS` is the LLM-Cypher-validator surface, separate from the publish path (Pitfall 7)
- `data-service/dg_knowledge.py` (`load_computgraph_catalog`) — confirmed the Phase 29 catalog parses live from the OWL file (Pitfall 6)
- `data-service/tests/test_dg_identity.py` — golden vector `(p1, frame.gh, cg:1:proc:11_Proc) → dg:BC8E62EE137E2B56`, `FakeGraph`/`FakeResult` duck-typed test pattern
- `data-service/requirements.txt`, `ui-v2/package.json` — confirmed no new package needed
- `.planning/phases/36-computgraph-persistence-display/36-CONTEXT.md`, `36-UI-SPEC.md` — locked user decisions (reproduced verbatim above)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — requirement text, prior-phase decisions, v9.0 phase history
- `CLAUDE.md` — project constraints, schema propagation checklist, graph schema v4 tables

### Secondary (MEDIUM confidence)

- None — this phase's research was entirely groundable in existing repo artifacts; no external web search was needed or performed.

### Tertiary (LOW confidence)

- None.

## Project Constraints (from CLAUDE.md)

- **Schema Change Propagation (standing rule):** any graph-structure change updates ALL of: `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompts, `config.template.js`, `data-service/app.py` Cypher, `.github/copilot-instructions.md`, `README.md`, `spec/DATABASE.md`, `ontology/dg-shapes.ttl` (SHACL shapes). Phase 36 adds 7 new node labels + 8 relationships — this checklist is mandatory, not optional, and should be its own plan/task, following the exact file-by-file shape of `32.1-07-SUMMARY.md`.
- **`config.template.js` and `ontology/dg-shapes.ttl` are named in CLAUDE.md's checklist but NOT in CONTEXT.md's decision #5 list** — CONTEXT.md's propagation list omits them. Recommend including both anyway per CLAUDE.md's authority (SHACL shapes for the new Computgraph node/relationship types would need `dgc:` prefix constraints mirroring the `RepresentationShape`/`SharedPropertyShape` precedent from 32.1-07; `config.template.js` should be checked for any Computgraph-adjacent config it currently omits).
- **Docker rebuild gotcha:** any `ui-v2/` change requires `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` — browser cache also requires a hard refresh to observe the `buildRings.js` fix.
- **Rule partition policy (`spec/RULE-PARTITION-POLICY.md`):** not directly implicated by Phase 36 (no new validation-rule category is introduced), but the schema-propagation pass should sanity-check whether the new Computgraph labels warrant a policy-table row, following the Phase 32.1-07 precedent of adding one for the identity registry.
- **Single Neo4j database, project-isolated via property, no wider label migration:** every new node/relationship in this phase follows this exactly (`project` property, `graph:'Computgraph'` property, existing single-database convention) — no deviation needed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, every pattern verified against actual shipped code this session
- Architecture: HIGH — endpoint/component/UI wiring patterns all have direct precedent in the codebase; the one genuinely new pattern (atomic multi-entity Cypher) is a straightforward application of existing Cypher/UNWIND idiom, not a novel architecture
- Pitfalls: HIGH — Pitfalls 1, 4, and 5 were discovered by direct code inspection (not inferred), and are load-bearing for correct MERGE-key design; these are the most valuable findings in this research pass

**Research date:** 2026-07-19
**Valid until:** 30 days (stable, internal-only domain; no external library version drift risk since zero new dependencies)
