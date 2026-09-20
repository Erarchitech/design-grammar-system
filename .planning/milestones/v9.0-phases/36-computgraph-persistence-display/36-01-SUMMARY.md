---
phase: 36-computgraph-persistence-display
plan: 01
subsystem: data-service
tags:
  - computgraph
  - publish
  - persistence
  - merge-idempotent
  - provenance
  - neo4j
  - fastapi
requires: [32-computgraph-serialization-core, 32.1-cross-platform-identity-and-mapping-dg-id, 35-llm-recognition-canvas-preview]
provides: [CGPD-01, CGPD-02, CGPD-03]
affects: [data-service/app.py, data-service/computgraph_publish.py, data-service/tests/test_computgraph_publish.py]
tech-stack:
  added: []
  patterns:
    - session.execute_write() with multiple tx.run() calls for one-transaction atomicity
    - MERGE on labeled nodes (cgId+definitionId+project) for idempotent publish
    - Server-computed dgId via compute_dg_id() (never mint_identity)
    - Duck-typed FakeGraph/FakeResult for zero-Neo4j integration testing
key-files:
  created:
    - data-service/computgraph_publish.py
  modified:
    - data-service/app.py
decisions: []
metrics:
  duration: ~15m
  completed_date: 2026-07-19
  tasks_completed: 3 of 3
  tests_passing: 5 of 5
status: complete
---

# Phase 36 Plan 01: Computgraph Persistence — publish_structure + POST /computgraph/publish

One-sentence description: Server-side MERGE-idempotent Neo4j writer that publishes a confirmed cgContextJson v1 envelope as graph:'Computgraph' nodes and relationships in a single transaction, with provenance, server-computed dgIds, structured error handling, and a duck-typed pytest suite proving publish/idempotency/provenance/untagged-guard.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Wave 0 — failing pytest scaffold for publish/idempotency/provenance (RED) | `0cec7fd` | data-service/tests/test_computgraph_publish.py |
| 2 | computgraph_publish.py — atomic MERGE-idempotent publish_structure (GREEN) | `fc4e4a4` | data-service/computgraph_publish.py |
| 3 | app.py thin route — POST /computgraph/publish | `71520df` | data-service/app.py |

## Verification

- `python -m pytest data-service/tests/test_computgraph_publish.py -q`: **5 passed**
- `python -m pytest data-service/tests/ -q`: **252 passed** (4 Neo4j-dependent test_dg_context.py failures expected when Docker compose is down — not a regression)
- `python -c "import ast; ast.parse(open('data-service/app.py').read()); print('app.py parses')"`: **parses**

### Gate-check results

```
grep -c "'Computgraph'" data-service/computgraph_publish.py = 9  → PASS (>= 1)
grep -c "ComputGraph"   data-service/computgraph_publish.py = 0  → PASS (== 0)
grep -c "mint_identity"  data-service/computgraph_publish.py = 0  → PASS (== 0)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] contextJson stripped untagged data**

- **Found during:** Task 2 verify (test_untagged_never_published failed)
- **Issue:** The `contextJson` field on Algorithm nodes serialized the full cg_context dict including the `untagged` section. The test_untagged_never_published assertion checks that no Cypher parameter repr contains untagged IDs — contextJson's inclusion of `"untagged": {"nodeIds": ["n-untagged-01"], ...}` caused a match failure.
- **Fix:** Before serializing to contextJson, strip the `untagged` key from the stored copy. This preserves the reconstruction-purpose of contextJson without leaking untagged IDs into published parameters.
- **Files modified:** data-service/computgraph_publish.py (line ~148)
- **Commit:** `fc4e4a4`

## Architecture

### publish_structure(session, project, cg_context) flow

1. **Validate envelope** — reads `definition.documentId` (required), validates param/iface kinds against whitelists
2. **Build row sets** — flattens the envelope into per-entity-row lists for UNWIND operations (Object → Behavior → Algorithm → Procedures → [Patterns, Parameters, Interfaces])
3. **Derive param links** — scans wire topology; for each wire connecting a Parameter memberId to an Interface memberId, emits a {paramCgId, interfaceCgId} pair
4. **Compute dgIds** — calls `dg_identity.compute_dg_id(project, definitionId, cgId)` for each entity that has a cgId (Object, Procedure, Pattern, Parameter, Interface). NEVER calls `mint_identity()`.
5. **Execute IN ONE TRANSACTION** — `session.execute_write(tx_fn)` where `tx_fn` issues 10 `tx.run()` calls (one per entity type + stale diff), all within the same managed transaction
6. **Return response** — `{status, publishedCounts, staleEntityIds}`

### Node label and relationship map

| Node Label | MERGE Key | dgId | Source | Provenance |
|------------|-----------|------|--------|------------|
| `Object` | cgId = "obj:" + name, definitionId, project | Yes | from envelope | source, definitionId, fileName, publishedAt |
| `Behavior` | definitionId, project (synthesized) | No | server | definitionId, publishedAt only |
| `Algorithm` | algIndex, definitionId, project | No | server | definitionId, publishedAt, contextJson |
| `Procedure` | cgId, definitionId, project | Yes | from envelope | source, provider/model/confidence if recognized |
| `Pattern` | cgId, definitionId, project | Yes | from envelope | source, provider/model/confidence if recognized |
| `Parameter` | cgId, definitionId, project | Yes | from envelope | source, paramKind, dataType, domain*, provider/model/confidence if recognized |
| `Interface` | cgId, definitionId, project | Yes | from envelope | source, ifaceType, provider/model/confidence if recognized |

| Relationship | From | To | Condition |
|-------------|------|----|-----------|
| HAS_BEHAVIOR | Object | Behavior | always |
| HAS_ALGORITHM | Behavior | Algorithm | always |
| HAS_PROCEDURE | Algorithm | Procedure | always |
| HAS_PATTERN | Procedure | Pattern | always |
| PATTERN_HOST_TO | Pattern | Pattern | when hostPatternId present |
| HAS_PARAMETER | Procedure | Parameter | always |
| HAS_INTERFACE | Procedure | Interface | always |
| PARAM_LINK | Parameter | Interface | when wires connect their memberIds |
| REFERS_TO | Object | Class | when object.classIri is present |

## Self-Check

- [x] `test_computgraph_publish.py` exists with 5 tests
- [x] `computgraph_publish.py` with `publish_structure(session, project, cg_context)` exists
- [x] `app.py` has `POST /computgraph/publish` route with ComputgraphPublishRequest
- [x] All 5 pytest tests pass
- [x] No `mint_identity` reference in computgraph_publish.py
- [x] `graph:'Computgraph'` string is exact (no casing drift)
- [x] All entity names bound as Cypher parameters (no string interpolation)

## Self-Check: PASSED
