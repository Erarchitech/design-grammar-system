---
phase: 36-computgraph-persistence-display
fixed_at: 2026-07-19T18:55:00Z
review_path: .planning/phases/36-computgraph-persistence-display/36-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 36: Code Review Fix Report

**Fixed at:** 2026-07-19T18:55:00Z
**Source review:** .planning/phases/36-computgraph-persistence-display/36-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 11 (2 critical, 9 warning — `fix_scope: critical_warning`, Info findings IN-01..IN-04 excluded)
- Fixed: 11
- Skipped: 0

## Fixed Issues

### CR-01: GH → data-service publish request always rejected with 422 (camelCase vs snake_case field name)

**Files modified:** `data-service/app.py`
**Commit:** 2ca8030
**Applied fix:** Renamed the `ComputgraphPublishRequest.cg_context` field to `cgContext`, matching `ComputgraphPublishClient`'s `JsonNamingPolicy.CamelCase` wire format and the same camelCase-field convention used by `ValidationPublishRequest` elsewhere in `app.py`. No C# change was needed — `JsonNamingPolicy.CamelCase` was already lowering `CgContext` to `cgContext` on the wire; the mismatch was entirely server-side. Updated the route body and error hint to reference `payload.cgContext`.

### CR-02: Property truncation feeds the inline editor — editing any long property silently corrupts it in Neo4j

**Files modified:** `ui-v2/src/screens/GraphScreen.jsx`, `ui-v2/src/components/display/PropertiesTable.jsx`
**Commit:** bbf0127
**Applied fix:** `rowsOf()` now returns both the truncated display `value` and an untruncated `rawValue` for every property row. `PropertiesTable.begin()` now seeds the edit draft from `r.rawValue ?? r.value`, so committing an edit on a property longer than 200 characters (e.g. `Algorithm.contextJson`) writes the full original value back to Neo4j instead of the truncated `…`-suffixed display string.

### WR-01: dataset_schema.json still documents Algorithm merge key as `cgId`

**Files modified:** `training/dataset_schema.json`
**Commit:** 3b22116
**Applied fix:** Replaced the Algorithm node's `key` block with `{algIndex: integer, definitionId: string, project: default-project}`, dropping the stale `cgId` placeholder, matching the actual MERGE key used in `computgraph_publish.py:407` and the already-corrected `cypher_template.txt`/`spec/DATABASE.md`.

### WR-02: copilot-instructions.md Algorithm key line not fixed by 4e441d3

**Files modified:** `.github/copilot-instructions.md`, `CLAUDE.md`
**Commit:** eddfe80
**Applied fix:** Updated the Algorithm key entry in both files' node/schema tables from `cgId+definitionId+project` to `algIndex+definitionId+project`, closing out the schema-propagation surfaces the earlier fix commit (4e441d3) missed.

### WR-03: DATABASE.md carries contradictory PARAM_LINK semantics within the same document

**Files modified:** `spec/DATABASE.md`
**Commit:** 9fb93f4
**Applied fix:** Reworded the Parameter section's `PARAM_LINK` bullet from "links parameters across procedures" to "connects this parameter to the Interface nodes its wires feed (wire-derived)", aligning it with the corrected relationships table and the actual Parameter→Interface implementation in `computgraph_publish.py:582`.

### WR-04: Publish accepts null/empty merge-key inputs

**Files modified:** `data-service/computgraph_publish.py`
**Commit:** 06a240b
**Applied fix:** Added explicit `ValueError` validation in `_build_publish_params` for every merge-key input that was previously silently defaulted: `algorithm.index` (was `None`-able, would hit Neo4j's opaque "cannot merge node using null property value" `ClientError`), and `procedure.id`/`pattern.id`/`parameter.id`/`interface.id` (previously `.get("id") or ""`, which let id-less entities silently collapse onto the same node). All 5 existing `test_computgraph_publish.py` tests pass unchanged (fixtures already supply real ids/indices).

### WR-05: Publish route surfaces Neo4j/driver failures as raw 500s

**Files modified:** `data-service/app.py`
**Commit:** e8ccf73
**Applied fix:** Added a broad `except Exception` handler to `post_computgraph_publish`, mirroring the adjacent `/computgraph/recognize` route's structured-error convention — maps any non-`ValueError` failure (e.g. `ServiceUnavailable`, auth errors, the WR-04 null-merge-key `ClientError`) to a `COMPUTGRAPH_PUBLISH_FAILED` / 502 structured error envelope instead of an unstructured FastAPI 500.

### WR-06: Provenance trio (provider/model/confidence) is unreachable dead code for GH-originated publishes

**Files modified:** `spec/DATABASE.md`, `training/dataset_schema.json`
**Commit:** ba7c9ee
**Applied fix:** Took the documentation-deferral option explicitly offered in the review (rather than extending the C# `Cg*Dto` wire types and the Phase-35 accept path, which is a larger cross-cutting change out of scope for a targeted fix pass). Added a "Known gap (Phase 36 WR-06)" note to the Object section of `spec/DATABASE.md` and a `note` field on the Object entry in `training/dataset_schema.json`, both explaining that `provider`/`model`/`confidence` are read+written by `computgraph_publish.py` for every `recognized` entity but are always `null` on GH-originated publishes until `ComputgraphContextSerializer.cs`'s `Cg*Dto` types carry them.

### WR-07: SHACL shapes demand properties the publish path treats as optional

**Files modified:** `data-service/computgraph_publish.py`
**Commit:** 3e76bb2
**Applied fix:** Made the publish path the stricter side (matching `spec/DATABASE.md`, which already lists both properties without an "(optional)" marker): added a `ValueError` check requiring `procedure.index` (matches `ProcedureShape_procIndex`'s `sh:minCount 1`), and tightened the `dataType` check from "optional but validated if present" to "required and validated" (matches `ParameterShape_dataType`'s `sh:minCount 1`). All 5 existing tests pass unchanged.

### WR-08: buildRings has no caption for `Behavior`

**Files modified:** `ui-v2/src/graph/buildRings.js`
**Commit:** 752a856
**Applied fix:** Added `Behavior: ["definitionId"]` to `CAPTIONS`, so Behavior nodes now render/sort/search by `definitionId` instead of falling back to the literal label string "Behavior".

### WR-09: No timeout on the publish HttpClient

**Files modified:** `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs`
**Commit:** 5b3cad7
**Applied fix:** Set an explicit 15-second `Timeout` on the shared `HttpClient` and wrapped the `PostAsJsonAsync(...).GetAwaiter().GetResult()` call in a `try/catch (TaskCanceledException)` that surfaces a clear "data-service did not respond within 15s" `InvalidOperationException` instead of freezing Rhino's UI for up to the previous 100s default. Verified via `dotnet build ./DG/DG.sln -c Release` — 0 errors, 0 warnings.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-07-19T18:55:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
