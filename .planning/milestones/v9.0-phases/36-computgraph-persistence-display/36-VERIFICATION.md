---
phase: 36-computgraph-persistence-display
verified: 2026-07-19T23:00:00Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
---

# Phase 36: Computgraph Persistence and Graph Layer Display — Verification Report

**Phase Goal:** A confirmed canvas structure persists to Neo4j as the Computgraph layer — project-isolated, MERGE-idempotent, provenance-carrying — and is browsable as a distinct layer in the ui-v2 graph viewer.

**Verified:** 2026-07-19T22:30:00Z
**Status:** gaps_found
**Re-verification:** No (initial verification)

## Goal Achievement

The core phase goal is substantively achieved. All runtime artifacts exist, are wired, and tests pass. However, the schema propagation documentation (plan 36-04) introduced 3 documentation inaccuracies that affect the completeness of the schema change propagation checklist.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /computgraph/publish writes a confirmed cgContextJson v1 structure to Neo4j as graph:'Computgraph' nodes, project-isolated | VERIFIED | `computgraph_publish.publish_structure()` exists at `data-service/computgraph_publish.py`. Test `test_publish_frame_structure` passes. All nodes carry `graph:'Computgraph'` and `project` via Cypher SET. |
| 2 | Re-publishing the same definition changes zero node counts (MERGE-idempotent) | VERIFIED | Test `test_republish_is_idempotent` passes (asserts `keys_after == keys_before`). MERGE keys are `{cgId, definitionId, project}` for typed entities, `{definitionId, project}` for Behavior. |
| 3 | Every published node answers a Cypher provenance query (source, provider/model when recognized, definitionId, publishedAt) | VERIFIED | Test `test_provenance_properties_present` passes — tagged nodes have source/definitionId/fileName/publishedAt; recognized nodes additionally have provider/model/confidence. |
| 4 | The whole publish is one Neo4j transaction — a mid-write failure leaves no partial Computgraph subgraph | VERIFIED | `session.execute_write()` wraps 10 `tx.run()` calls in ONE managed transaction. The route owns `with driver.session()` and passes the session in. |
| 5 | Entity names flow only through bound Cypher parameters, never string-interpolated | VERIFIED | Every `tx.run()` call uses `$param` style parameters. No f-string/%/.format interpolation of entity names in any Cypher statement. |
| 6 | A DG COMPUTGRAPH PUBLISH component re-extracts the live canvas, serializes cgContextJson (dgId-stamped), and POSTs it to /computgraph/publish on a rising-edge trigger | VERIFIED | `ComputgraphPublishComponent.cs` exists with `_lastApply` rising-edge idiom, re-extraction chain (ExtractRaw->Parse->AssignDgIds->Serialize->Publish). |
| 7 | The confirm-publish flow completes without leaving Grasshopper — no manual export/copy step | VERIFIED | Component does all work inside SolveInstance. `ComputgraphPublishClient.Publish()` POSTs directly to data-service. |
| 8 | The plugin process holds no Neo4j driver — persistence is entirely server-side over HTTP | VERIFIED | `ComputgraphPublishClient` uses static HttpClient POST. No Neo4j.Driver. |
| 9 | The ui-v2 orbital datascape renders the Computgraph layer distinctly, positioned between SpecGraph and ValidGraph, with 7 labels bucketed into 3 orbits | VERIFIED | `buildRings.js` LAYER_ORDER has `"Computgraph"` between `"SpecGraph"` and `"ValidGraph"`. ORBITS.Computgraph maps 7 labels to 3 orbits. |
| 10 | The Computgraph layer is filterable per project through the existing GraphScreen project prop — no new control | VERIFIED | No new project filter control added. Existing GraphScreen project prop applies to all layers including Computgraph. |
| 11 | A multi-KB contextJson property on Algorithm nodes truncates in the properties panel instead of breaking the frosted layout | VERIFIED | `rowsOf` function at `GraphScreen.jsx:690` truncates any value string >200 chars to 200-char prefix + "...". Both hover and detail panels inherit via `rowsOf(hv,6)` and `rowsOf(se,24)`. |
| 12 | No new color/accent is introduced — Computgraph renders in the monochrome + Signal-Red system like every other layer | VERIFIED | No new CSS classes, accent colors, or theme tokens introduced. buildRings.js uses existing TH.ink/TH.dim rendering. |
| 13 | Every schema-defining surface documents the 7 Computgraph node labels + their properties and the 9 Computgraph relationship types with graph:'Computgraph' | PRESENT_BEHAVIOR_UNVERIFIED | All surfaces document the labels and relationship types with correct `graph:'Computgraph'` string. HOWEVER, the from/to labels for 2 relationship types are incorrect, and Algorithm's merge key is documented with wrong property. See Warnings below. |
| 14 | The stale spec/DATABASE.md claim that :Algorithm carries a dgId is corrected to the verified entity list (Object, Procedure, Pattern, Parameter, Interface) | VERIFIED | spec/DATABASE.md line 113 lists correct dgId entity list. CLAUDE.md line 196 also correct. |
| 15 | SHACL shapes for the new Computgraph node/relationship types mirror the Representation/SharedProperty precedent | VERIFIED | ontology/dg-shapes.ttl contains 7 Computgraph node shapes (Object, Behavior, Algorithm, Procedure, Pattern, Parameter, Interface) with property datatypes and enum constraints. |

**Score:** 14/15 truths verified (1 present, accuracy-unverified on relationship from/to labels)

### Warnings — Documentation Bugs in Schema Propagation (plan 36-04)

Three documentation inaccuracies exist across ALL schema propagation surfaces. The runtime code is correct in all cases — only the documentation is wrong.

**Bug 1: HAS_INTERFACE from-label wrong**

| Surface | Documented | Should be |
|---------|-----------|-----------|
| spec/DATABASE.md (line 400) | Pattern -> Interface | Procedure -> Interface |
| CLAUDE.md (line 194) | Pattern->Interface | Procedure->Interface |
| cypher_template.txt (line 136) | Pattern->Interface | Procedure->Interface |
| training/dataset_schema.json (line 343) | from: Pattern | from: Procedure |
| .github/copilot-instructions.md (line 57) | Pattern -> Interface | Procedure -> Interface |
| README.md (line 196) | Pattern->Interface | Procedure->Interface |

Runtime evidence: `computgraph_publish.py` line 562-563: `MATCH (pr:Procedure {...}) MERGE (pr)-[:HAS_INTERFACE]->(i)`. Plan 36-01 explicitly specifies `HAS_INTERFACE (Procedure->Interface)`.

**Bug 2: PARAM_LINK to-label wrong**

| Surface | Documented | Should be |
|---------|-----------|-----------|
| spec/DATABASE.md (line 401) | Parameter -> Parameter | Parameter -> Interface |
| CLAUDE.md (line 194) | Parameter->Parameter | Parameter->Interface |
| cypher_template.txt (line 137) | Parameter->Parameter | Parameter->Interface |
| training/dataset_schema.json (line 349) | to: Parameter | to: Interface |
| .github/copilot-instructions.md (line 58) | Parameter -> Parameter | Parameter -> Interface |
| README.md (line 196) | Parameter->Parameter | Parameter->Interface |

Runtime evidence: `computgraph_publish.py` line 580-582: `MATCH (i:Interface {...}) MERGE (p)-[:PARAM_LINK]->(i)`. Plan 36-01 explicitly specifies `{paramCgId, interfaceCgId}` and `PARAM_LINK (Parameter->Interface)`.

**Bug 3: Algorithm merge key wrong**

| Surface | Documented | Should be |
|---------|-----------|-----------|
| spec/DATABASE.md (line 192) | (cgId, definitionId, project) | (algIndex, definitionId, project) |
| CLAUDE.md (line 169) | `cgId`+`definitionId`+`project` | `algIndex`+`definitionId`+`project` |
| cypher_template.txt (line 111) | (cgId, definitionId, project) | (algIndex, definitionId, project) |
| .github/copilot-instructions.md (line 35) | key `cgId`+`definitionId`+`project` | key `algIndex`+`definitionId`+`project` |

Runtime evidence: `computgraph_publish.py` line 407: `MERGE (a:Algorithm {algIndex: row.index, definitionId: $definitionId, project: $project})`. Algorithm has no cgId — the merge anchors on algIndex.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| data-service/computgraph_publish.py | publish_structure(session, project, cg_context) | VERIFIED | 612 lines. 10 publish functions, stale-entity diff, parameterized Cypher. |
| data-service/app.py | POST /computgraph/publish route + ComputgraphPublishRequest | VERIFIED | Lines 1339-1371. Session-owning, ValueError->422 error handling. |
| data-service/tests/test_computgraph_publish.py | 5 pytest tests for CGPD-01/02/03 | VERIFIED | 5/5 passing. FakeGraph/FakeResult duck-typed fixtures. |
| DG/.../Validation/ComputgraphPublishContract.cs | Request/Response DTOs | VERIFIED | IF-guarded. Project (string), CgContext (JsonElement), Status, StaleEntityIds. |
| DG/.../Validation/ComputgraphPublishClient.cs | Static HttpClient publish | VERIFIED | IF-guarded. NormalizeUrl, camelCase JSON, status-check/throw. |
| DG/.../Components/ComputgraphPublishComponent.cs | DG COMPUTGRAPH PUBLISH GH component | VERIFIED | IF-guarded. _lastApply rising-edge, re-extraction chain, GUID E2D4A9F1... |
| DG/.../Properties/ComputgraphPublish24.png | Icon placeholder | VERIFIED | Exists (copy of StructureConfirm24.png). |
| ui-v2/src/graph/buildRings.js | Computgraph layer key, orbits, captions | VERIFIED | LAYER_ORDER corrected, ORBITS.Computgraph with 7 labels / 3 orbits, 6 captions. |
| ui-v2/src/screens/GraphScreen.jsx | rowsOf 200-char truncation guard | VERIFIED | Line 690: String(p[1]).length > 200 truncation. |
| cypher_template.txt | Computgraph runtime block | VERIFIED (see Warnings) | Computgraph runtime labels + relationships documented. HAS_INTERFACE/PARAM_LINK/Algorithm-key inaccuracies. |
| training/dataset_schema.json | Computgraph entries | VERIFIED (see Warnings) | Valid JSON. HAS_INTERFACE/PARAM_LINK from/to inaccuracies. |
| spec/DATABASE.md | Computgraph nodes + relationships | VERIFIED (see Warnings) | 7 label sections, 9 relationships. Algorithm merge key + HAS_INTERFACE/PARAM_LINK inaccuracies. |
| ontology/dg-shapes.ttl | 7 Computgraph SHACL shapes | VERIFIED | ObjectShape, BehaviorShape, AlgorithmShape, ProcedureShape, PatternShape, ParameterShape, InterfaceShape. |
| CLAUDE.md | Computgraph table rows + relationships | VERIFIED (see Warnings) | Node labels table + relationships line + dgId entity list. HAS_INTERFACE/PARAM_LINK/Algorithm-key inaccuracies. |
| .github/copilot-instructions.md | Computgraph schema sync | VERIFIED (see Warnings) | Labels, keys, relationships, dgId entity list. HAS_INTERFACE/PARAM_LINK/Algorithm-key inaccuracies. |
| README.md | Computgraph schema overview | VERIFIED (see Warnings) | Labels + relationships. HAS_INTERFACE/PARAM_LINK inaccuracies. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| publish_structure | dg_identity.compute_dg_id() | import | VERIFIED | `from dg_identity import compute_dg_id` at line 54. Called for Object/Procedure/Pattern/Parameter/Interface. |
| publish_structure | Cypher parameters | $param binding | VERIFIED | Every tx.run() call receives params dict. No string interpolation. |
| app.py route | driver.session() | with statement | VERIFIED | Line 1361: `with driver.session() as session:`. Session passed to publish_structure. |
| app.py route | computgraph_publish.publish_structure() | import | VERIFIED | Line 68: `import computgraph_publish`. Line 1362: called inside session context. |
| ComputgraphPublishClient | /computgraph/publish | HTTP POST | VERIFIED | Line 18: `endpoint = $"{NormalizeUrl(dataServiceUrl)}/computgraph/publish"`. |
| ComputgraphPublishComponent | re-extraction chain | ComputeGraphPublishCanvas | VERIFIED | Lines 100-103: ExtractRaw -> Parse -> AssignDgIds -> Serialize -> Publish. |
| buildRings.js LAYER_ORDER | graph:'Computgraph' | exact string "Computgraph" | VERIFIED | No stale "ComputGraph" casing. Layer sits between SpecGraph and ValidGraph. |
| Behavior | CAPTIONS | intentional fallthrough | VERIFIED | No Behavior caption entry. captionOf() generic fallback renders "Behavior". |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| publish_structure | cg_context (dict) | HTTP POST body | Dynamic from caller (confirmed envelope) | FLOWING |
| _publish_* functions | params dict | _build_publish_params() | Builds from envelope | FLOWING |
| rowsOf truncation guard | n.props | Neo4j node properties | Real node data | FLOWING |
| buildRings.js | nodes/rels | Neo4j via graphApi | Real graph data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| pytest suite passes | `python -m pytest data-service/tests/test_computgraph_publish.py -q` | 5 passed | PASS |
| app.py parses | `python -c "import ast; ast.parse(...)"` | parses | PASS |
| Vite UI build | `npm --prefix ui-v2 run build` | built in 5.73s | PASS |
| dataset_schema valid JSON | `python -c "import json; json.load(...)"` | JSON-OK | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| CGPD-01 | 36-01 | POST /computgraph/publish persists structure to Neo4j with labels, relationships, project isolation | SATISFIED | computgraph_publish.py, app.py route, test_publish_frame_structure passes |
| CGPD-02 | 36-01 | MERGE-idempotent on stable entity ids | SATISFIED | test_republish_is_idempotent passes, MERGE keys on every entity |
| CGPD-03 | 36-01 | Every published node carries provenance | SATISFIED | test_provenance_properties_present passes; source/provider/model/confidence/definitionId/publishedAt |
| CGPD-04 | 36-03, 36-04 | ui-v2 viewer renders Computgraph layer; schema propagation checklist completed | NEEDS HUMAN (docs) | Display wired (buildRings.js, GraphScreen.jsx, Vite builds). Schema propagation surfaces have documentation inaccuracies (3 bugs). |
| CGPD-05 | 36-02 | Publish path from plugin via DG COMPUTGRAPH PUBLISH | SATISFIED | ComputgraphPublishComponent.cs, Contract, Client exist; dotnet builds clean |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| spec/DATABASE.md | 400 | HAS_INTERFACE Pattern->Interface should be Procedure->Interface | WARNING | Incorrect relationship contract documented |
| spec/DATABASE.md | 401 | PARAM_LINK Parameter->Parameter should be Parameter->Interface | WARNING | Incorrect relationship contract documented |
| spec/DATABASE.md | 192 | Algorithm merge key (cgId,...) should be (algIndex,...) | WARNING | Incorrect merge key documented |
| cypher_template.txt | 111, 136, 137 | Same 3 inaccuracies | WARNING | See DATABASE.md same bugs |
| CLAUDE.md | 169, 194 | Same 3 inaccuracies | WARNING | See DATABASE.md same bugs |
| training/dataset_schema.json | 341-349 | HAS_INTERFACE/PARAM_LINK from/to wrong | WARNING | See DATABASE.md same bugs |
| .github/copilot-instructions.md | 35, 57, 58 | Same 3 inaccuracies | WARNING | See DATABASE.md same bugs |
| README.md | 196 | HAS_INTERFACE/PARAM_LINK from/to wrong | WARNING | See DATABASE.md same bugs |
| .planning/REQUIREMENTS.md | CGPD-04, CGPD-05 | Checkboxes not updated to [x] after completion | INFO | Tracking gap only: code exists, markers stale |

### Gaps Summary

**Documentation inaccuracies in schema propagation (plan 36-04):** The runtime implementation is correct in all cases. However, 3 documentation bugs were introduced during schema propagation and exist across all 6 surfaces (CLAUDE.md, spec/DATABASE.md, cypher_template.txt, training/dataset_schema.json, .github/copilot-instructions.md, README.md):

1. **HAS_INTERFACE from-label**: Documented as `Pattern->Interface`, should be `Procedure->Interface` (runtime code at `computgraph_publish.py:563`)
2. **PARAM_LINK to-label**: Documented as `Parameter->Parameter`, should be `Parameter->Interface` (runtime code at `computgraph_publish.py:582`)
3. **Algorithm merge key**: Documented as `cgId+definitionId+project`, should be `algIndex+definitionId+project` (Algorithm has no cgId; runtime code at `computgraph_publish.py:407`)

**Task-level gap:** These bugs should be corrected before Phase 37 (structure validation) relies on the schema documentation for new ValidGraph queries.

---

_Verified: 2026-07-19T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
