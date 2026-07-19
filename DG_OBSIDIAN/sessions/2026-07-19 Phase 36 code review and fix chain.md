---
tags: [session, phase-36, code-review, fixes]
date: 2026-07-19
phase: 36
title: Phase 36 code review and fix chain
---

# Phase 36 Code Review & Fix Chain — 2026-07-19

## Summary

Executed `/gsd-code-review 36 --fix` on Phase 36 "Computgraph Persistence and Graph Layer Display" after autonomous execution completed 2026-07-19 morning. Code review surfaced 2 Critical + 9 Warning + 4 Info findings across 12 source files (Python data-service, C# Grasshopper plugin, React UI, schema docs). All 11 in-scope issues (Critical + Warning) fixed in one pass with atomic per-finding commits. 4 Info findings deferred (not in --fix scope).

## Findings Summary

### Critical (2 blockers)

**CR-01 — Publish flow wire-contract mismatch (SEVERITY: immediate blocker)**
- **File:** `data-service/app.py:1339`
- **Root cause:** ComputgraphPublishClient serializes with `JsonNamingPolicy.CamelCase` → sends `{"project", "cgContext"}`, but FastAPI declares `cg_context: dict` (snake_case, no alias) → every publish returns 422 "Field required: cg_context"
- **Impact:** Every GH COMPUTGRAPH PUBLISH would fail before reaching validation logic
- **Why caught now:** Unit tests call `publish_structure()` directly; never cross HTTP boundary
- **Fix:** Renamed pydantic field to `cgContext` to match wire contract (commit `2ca8030`)

**CR-02 — Data corruption on long property inline edit**
- **Files:** `ui-v2/src/screens/GraphScreen.jsx:690`, `ui-v2/src/components/display/PropertiesTable.jsx`
- **Root cause:** Truncation display (200 chars + "…") feeds directly into inline editor draft; saving truncated string back to Neo4j silently destroys e.g. `Algorithm.contextJson`
- **Impact:** Any user editing a long property (e.g. context JSON > 200 chars) would silently lose data
- **Fix:** Added `rawValue` field threading untruncated source through to editor (commit `bbf0127`)

### Warnings (9 items, all fixed)

**WR-01/WR-02 — Algorithm merge key still stale in 2 schema surfaces**
- Commit 4e441d3 corrected Algorithm key from `cgId` → `algIndex+definitionId+project` in cypher_template.txt + DATABASE.md, but missed dataset_schema.json + copilot-instructions.md
- **Fixed:** Updated `training/dataset_schema.json:228-242` (commit `3b22116`) + `.github/copilot-instructions.md` + CLAUDE.md (commit `eddfe80`)

**WR-03 — Contradictory PARAM_LINK documentation**
- DATABASE.md:279 says "PARAM_LINK links parameters across procedures" but corrected table at line 401 says "Parameter→Interface"
- **Fixed:** Aligned to Parameter→Interface (commit `9fb93f4`)

**WR-04/WR-05 — Merge-key validation gaps**
- `computgraph_publish.py` doesn't validate null/empty merge-key inputs → null `algorithm.index` triggers Neo4j "cannot merge using null property value" → raw 500 (not caught by error handler). Empty entity ids (`""`) silently collapse distinct entities into one node.
- **Fixed:** Added `ValueError` validation in `computgraph_publish.py` (commit `06a240b`) + structured 502 handler in `app.py` (commit `e8ccf73`)

**WR-06 — Unreachable provider/model/confidence provenance**
- Schema docs promise provenance fields but C# Cg* DTOs don't carry provider/model/confidence → always publishes null
- **Fixed:** Chose doc-deferral path (commit `ba7c9ee`); larger DTO change deferred to v9.1

**WR-07 — SHACL shape strictness mismatch**
- `dg-shapes.ttl` requires `dataType`/`procIndex`/`algIndex` at Violation severity, but `computgraph_publish.py` treats as optional → valid publishes fail SHACL
- **Fixed:** Made `procedure.index`/`parameter.dataType` required in publish validation (commit `3e76bb2`)

**WR-08 — Behavior nodes render as literal "Behavior" string**
- `buildRings.js` missing `Behavior` caption mapping → no `definitionId` display
- **Fixed:** Added caption entry (commit `752a856`)

**WR-09 — Publish HttpClient timeout unbounded**
- Default 100s timeout; stalled data-service freezes Rhino UI
- **Fixed:** Bounded to 15s in ComputgraphPublishClient (commit `5b3cad7`); verified `dotnet build ./DG/DG.sln -c Release` (0 errors/warnings)

### Info (4 items, deferred)

- Icon resource embedding and runtime loading verified clean
- Cypher injection surface checked (all parameters dict-passed, safe)
- DgId pure-function usage verified
- HAS_INTERFACE/PARAM_LINK directions in code verified vs. corrected docs

## Commits

**Review commits:**
- `aaa9f0f` — docs(36): add code review report
- `07626ae` — docs(36): add code review fix report

**Fix commits (11 total):**
1. `2ca8030` — fix(36): CR-01 ComputgraphPublishRequest.cg_context camelCase wire contract
2. `bbf0127` — fix(36): CR-02 PropertiesTable inline editor truncation data corruption
3. `3b22116` — fix(36): WR-01 Algorithm merge key in dataset_schema.json
4. `eddfe80` — fix(36): WR-02 Algorithm merge key in copilot-instructions.md + CLAUDE.md
5. `9fb93f4` — fix(36): WR-03 DATABASE.md PARAM_LINK semantics clarification
6. `06a240b` — fix(36): WR-04 computgraph_publish.py null/empty merge-key validation
7. `e8ccf73` — fix(36): WR-05 app.py structured 502 handler for publish failures
8. `ba7c9ee` — fix(36): WR-06 provenance gap documentation
9. `3e76bb2` — fix(36): WR-07 dataType/procIndex required validation
10. `752a856` — fix(36): WR-08 Behavior caption mapping in buildRings.js
11. `5b3cad7` — fix(36): WR-09 HttpClient 15s timeout bounded

## Verification Notes

- **All 11 fixes compile:** C# build, Python FastAPI lint, Vite build all pass
- **Schema consistency:** All schema surfaces (cypher_template.txt, dataset_schema.json, DATABASE.md, copilot-instructions.md, ontology/dg-shapes.ttl, CLAUDE.md) now aligned on Algorithm key and PARAM_LINK semantics
- **Live E2E recommended:** CR-01 and CR-02 should be smoke-tested with a real GH publish + long-property edit before v9.0 ships

## Next Steps

1. Manual smoke test: Grasshopper COMPUTGRAPH PUBLISH → verify 200 OK
2. Manual smoke test: Edit long property in Graph UI → verify full value saved
3. `/gsd-verify-work` — Phase 36 full UAT (6 in-Rhino checks deferred)
4. Phase 37 "Script Structure Validation MVP" context ready; phase 38 awaiting discuss

## Related

- [[decisions/Phase 36 Computgraph publish avoids mint_identity|Phase 36 design decisions]]
- [[debugging/Phase 36 publish contract schema mismatch|CR-01 wire contract root cause]]
- [[debugging/Phase 36 property truncation data loss|CR-02 truncation root cause]]
