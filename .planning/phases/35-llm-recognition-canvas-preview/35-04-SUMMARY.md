---
phase: 35-llm-recognition-canvas-preview
plan: 04
subsystem: canvas
tags: [csharp, grasshopper, dg-core, structure-confirm, preview-registry, value-table, undo-record]

# Dependency graph
requires:
  - phase: 35-llm-recognition-canvas-preview (plan 02)
    provides: PreviewRegistry (ConcurrentDictionary-backed)/PreviewEntry/ProposalDto, CanvasAnnotationStyles.PreviewPrefix, RawGroup.Recognized read path
  - phase: 35-llm-recognition-canvas-preview (plan 03)
    provides: CanvasListenerComponent's real preview_structure/clear_preview/get_preview_status handlers that populate PreviewRegistry
provides:
  - StructureConfirmComponent (DG STRUCTURE CONFIRM) -- lists pending proposals; Apply accepts (preview -> permanent convention group + dg.recognized.<guid> marker) or rejects (clean removal); partial accept
  - PreviewEntry.ProcedureIndex (additive) -- carries the proposal's NN token forward so accept-time nickname re-derivation works for every EntityTagKind, not just Pat
affects: [36, wave-2-canvas-preview-components]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Accept-time read-before-write name re-derivation: CanvasContextExtractor.ExtractRaw + CanvasAnnotationNameFactory.ForEntity re-computed at confirm time instead of trusting the LLM's suggestedName captured at preview time -- guards against a name collision if the architect tagged something in the interim"
    - "Rising-edge Apply trigger (_lastApply initialized true) -- same ParameterReinstateComponent/EntityTagComponent precedent applied to a third component"

key-files:
  created:
    - DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs
  modified:
    - DG/src/DG.Grasshopper/DgIcons.cs
    - DG/src/DG.Grasshopper/Properties/StructureConfirm24.png
    - DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs

key-decisions:
  - "PreviewEntry (frozen from Plan 35-02) extended with a ProcedureIndex field, populated from ProposalDto.ProcedureIndex in RegisterAll -- CanvasAnnotationNameFactory.ForEntity requires procIndex >= 10 for every EntityTagKind (not just Pat), and PreviewEntry had no way to supply it without this addition"
  - "Nested-Pattern detection at accept time only computed for EntityTagKind.Pat (the only kind ForKind's nested parameter affects), mirroring EntityTagComponent's host-group subset scan against the freshly re-extracted RawCanvas rather than any stored preview-time state"
  - "GH_UndoRecord('DG confirm structure') is only pushed when at least one accept or reject actually mutated the canvas -- an Apply where every listed id turned out invalid/stale produces no empty undo entry"
  - "A group whose GroupGuid no longer resolves on the live canvas (already removed by other means) is treated as stale: its registry entry is silently dropped rather than surfaced as a warning, since there is nothing left to restyle or remove"

patterns-established:
  - "Additive record extension under deviation Rule 3: when a frozen upstream record type is missing a field a downstream task's contract literally requires, add the field (verified single construction site) rather than reconstructing the value through side-channel lookups"

requirements-completed: [RCGN-03]

coverage:
  - id: D1
    description: "StructureConfirmComponent shell (GUID A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14): Accept/Reject/Apply inputs, Pending/Status outputs, icon, conditional-compilation guard; stub SolveInstance reads PreviewRegistry.Pending into the Pending output (name, kind, confidence, live member count)"
    requirement: "RCGN-03"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (0 errors)"
        status: pass
      - kind: unit
        ref: "grep -c A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14 StructureConfirmComponent.cs == 1, unique across Components/"
        status: pass
    human_judgment: false
  - id: D2
    description: "SolveInstance: rising-edge Apply resolves Accept ('*' or explicit ids)/Reject, warns+skips unknown ids; Accept re-derives the permanent nickname/colour (read-before-write) and writes dg.recognized.<guid>; Reject removes the group; both remove the PreviewRegistry entry leaving unlisted ids pending (partial accept); single GH_UndoRecord; no persistence call anywhere in the file"
    requirement: "RCGN-03"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (0 errors, 0 warnings) && dotnet test DG/tests/DG.Tests/ (350/350 pass)"
        status: pass
      - kind: unit
        ref: "grep -vE '^\\s*#|^\\s*//' StructureConfirmComponent.cs | grep -cE 'HttpClient|data-service|neo4j|Neo4j' == 0"
        status: pass
      - kind: unit
        ref: "grep -c '_lastApply = true' StructureConfirmComponent.cs == 1 (rising-edge guard, no first-solve auto-fire)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Live-Rhino behavior: Pending lists proposals correctly; Accept converts a preview group to a permanent convention group matching a Phase-34 manual tag's color/name and source:recognized survives a save/reopen + re-pull; Reject removes cleanly with no orphan; partial accept (accept one + reject one + leave a third) preserves the remainder; nothing contacts Neo4j/data-service during confirm"
    verification: []
    human_judgment: true
    rationale: "net9.0 DG.Tests cannot reference the net7.0-windows GH assembly (NU1201 TFM incompatibility) -- canvas restyle, undo-stack behavior, ValueTable save/reopen persistence, and the live re-serialize round-trip can only be observed in a live Rhino 8/Grasshopper session, not xUnit. Deferred to phase-level manual UAT per project precedent (Phases 33, 34-02, 34-03, 35-03)."

# Metrics
duration: 10min
completed: 2026-07-19
status: complete
---

# Phase 35 Plan 04: DG STRUCTURE CONFIRM Summary

**`StructureConfirmComponent` (`DG STRUCTURE CONFIRM`): lists `PreviewRegistry` proposals and, on a rising-edge Apply, accepts (read-before-write re-derived permanent nickname/colour + `dg.recognized.<guid>` ValueTable marker) or rejects (clean removal) selected proposals, with partial-accept support and zero Neo4j calls.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-19T09:49:00Z
- **Completed:** 2026-07-19T09:58:36Z
- **Tasks:** 2 automated tasks completed; 1 checkpoint (live-Rhino UAT) deferred per project convention
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `StructureConfirmComponent` (`DG STRUCTURE CONFIRM`, GUID `A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14`): `Accept`/`Reject`/`Apply` inputs, `Pending`/`Status` outputs, `DgIcons.StructureConfirm24` icon, `#if GRASSHOPPER_SDK` guard with `#else` stub -- registered on the `DG`/`Actions` category alongside `PARAMETER REINSTATE`
- `Pending` output always refreshes from `PreviewRegistry.Pending`, rendering "name, kind, confidence%, N member(s)" per proposal with a live on-canvas member count (mirrors `CanvasListenerComponent.HandleGetPreviewStatus`'s precedent rather than storing a redundant count)
- Rising-edge `Apply` (`_lastApply` initialized `true`, no first-solve auto-fire) resolves the `Accept` set (`*` expands to every pending id) and `Reject` set, warns and drops any id not currently pending, then defers the actual mutation via `ScheduleSolution` (GH SDK forbids document mutation mid-solve)
- **Accept:** read-before-write re-derives the permanent nickname via `CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationNameFactory.ForEntity` (never the possibly-stale LLM `suggestedName`, T-35-06 mitigation), restyles to the permanent Phase-34 `CanvasAnnotationStyles.ForKind` colour (nested-Pattern variant detected via an `EntityTagComponent`-style host-group subset scan), and writes `doc.ValueTable.SetValue("dg.recognized.<guid>", "true")`
- **Reject:** `RemoveObject` on the preview group, no ValueTable write
- Both paths remove the proposal from `PreviewRegistry`; any id in neither list stays pending (partial accept). One `GH_UndoRecord("DG confirm structure")` covers the whole Apply, pushed only when at least one accept/reject actually mutated the canvas
- No Neo4j/data-service call anywhere in the file (source assertion enforced by grep)

## Task Commits

Each task was committed atomically:

1. **Task 1: Register DG STRUCTURE CONFIRM shell (icon, GUID, ports, #if guard + stub)** - `428888f` (feat)
2. **Task 2: SolveInstance -- Accept/Reject on rising-edge Apply, restyle + ValueTable marker** - `253e863` (feat)

**Plan metadata:** (this commit) `docs(35-04): complete DG STRUCTURE CONFIRM plan`

## Files Created/Modified

- `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` (new) - `DG STRUCTURE CONFIRM` component: shell + full Accept/Reject/Apply logic
- `DG/src/DG.Grasshopper/DgIcons.cs` - Added `StructureConfirm24` icon entry
- `DG/src/DG.Grasshopper/Properties/StructureConfirm24.png` (new) - Placeholder icon (copy of `OntoGraph24.png`, per the `ObjectMarker24`/`EntityTag24` precedent)
- `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs` - `PreviewEntry` gains a `ProcedureIndex` field (additive), populated from `ProposalDto.ProcedureIndex` in `RegisterAll`

## Decisions Made

- `PreviewEntry` (frozen from Plan 35-02) extended with `ProcedureIndex`, sourced from the already-available `ProposalDto.ProcedureIndex` -- `CanvasAnnotationNameFactory.ForEntity` requires `procIndex >= 10` for every `EntityTagKind` (not only `Pat`), and the frozen record had no field carrying it forward from proposal to confirm time. Verified as the sole `PreviewEntry` construction site before extending.
- Nested-Pattern colour detection at accept time is only computed for `EntityTagKind.Pat` (the only kind `CanvasAnnotationStyles.ForKind`'s `nested` parameter affects), reusing a simplified version of `EntityTagComponent`'s host-group subset scan against the freshly re-extracted `RawCanvas.Groups`.
- The confirm `GH_UndoRecord` is pushed only when `accepted > 0 || rejected > 0`, avoiding an empty undo entry when an entire Apply consisted of stale/unknown ids.
- A `PreviewEntry` whose `GroupGuid` no longer resolves to a live `GH_Group` (removed by some other means) is treated as stale and its registry entry is silently dropped -- there is nothing left to restyle or remove, and this is not a user-facing error condition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `PreviewEntry` (Plan 35-02) had no field to carry the proposal's `ProcedureIndex` into the confirm step**
- **Found during:** Task 2 (SolveInstance Accept logic)
- **Issue:** `CanvasAnnotationNameFactory.ForEntity(kind, procIndex, name, patternIndex)` requires a valid `procIndex >= 10` for every `EntityTagKind`, not only `Pat`. `PreviewEntry` (frozen from Plan 35-02) carries `ProposalId`/`GroupGuid`/`Kind`/`SuggestedName`/`Confidence`/`Rationale` but no `ProcedureIndex` -- the wire proposal shape's `ProcedureIndex` field was dropped when `RegisterAll` projected `ProposalDto` into `PreviewEntry`. Without it, Task 2's accept-time name re-derivation (the plan's own locked decision) could not be implemented at all.
- **Fix:** Added `ProcedureIndex` (int) to `PreviewEntry`, populated from `proposal.ProcedureIndex` (already present on `ProposalDto`) in `PreviewRegistry.RegisterAll`. Verified `RegisterAll` is the only construction site for `PreviewEntry` before making the additive change.
- **Files modified:** `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs` (not in the plan's `files_modified` frontmatter list, but required to satisfy Task 2's explicit acceptance criteria)
- **Verification:** `dotnet build DG/DG.sln -c Release` clean (0 errors, 0 warnings); `dotnet test DG/tests/DG.Tests/` 350/350 pass; `HandleGetPreviewStatus`'s existing named-property access to `PreviewEntry` fields is unaffected since the new field is additive and the sole construction site was updated in the same commit.
- **Committed in:** `428888f` (Task 1's commit, since the field addition was needed before Task 2's implementation could compile)

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** Necessary for correctness -- Task 2's explicit "re-derive the permanent name via ... CanvasAnnotationNameFactory" instruction is otherwise unimplementable for any non-`Pat` kind. No scope creep: one additive field on an internal record, zero call-site breakage, zero architectural change.

## Issues Encountered

None beyond the deviation documented above. `dotnet test DG/tests/DG.Tests/` ran 350/350 green (0 failures) this session -- the project-memory-documented env-dependent Neo4j-down baseline did not manifest, consistent with Plan 35-03's session (Neo4j was reachable); this plan's changes touch only `Components`/`Canvas` files, nowhere near that dependency, so this is incidental either way.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All automatable work for RCGN-03's confirm gate is complete and green (build 0/0, DG.Tests 350/350, GUID uniqueness, source assertion). Phase 35's three canvas-preview components (`CanvasListenerComponent`'s preview handlers from Plan 35-03, and this plan's `StructureConfirmComponent`) are all in place; confirmed structure carries `source: recognized` end-to-end from ValueTable write (this plan) through the Plan 35-02 read path into `CanvasAnnotationParser`.
- **Task 3 (live-Rhino UAT) is explicitly DEFERRED to phase-level `/gsd-verify-work 35`, not self-approved as passed** -- per this plan's `checkpoint_policy` (precedent: Phases 33, 34-02, 34-03, 35-03). The following checks remain human_needed and must be exercised in a live Rhino 8 / Grasshopper session before Phase 35 is accepted:
  1. Build `dotnet build DG/DG.sln -c Release`, load `DG.gha`. On the Frame definition, run recognition + `preview_structure` (Plan 35-03) so preview groups + a legend are on canvas. Place `DG STRUCTURE CONFIRM`; confirm its `Pending` output lists each proposal (name, kind, confidence, member count).
  2. ACCEPT one proposal id, leave `Apply=false`, then toggle `Apply=true` (rising edge). Confirm the preview group loses the `[?] ` prefix/desaturation and becomes a permanent convention group whose colour/name match a Phase-34 manual tag of the same kind. Confirm the legend/pending list updates and that proposal is no longer pending.
  3. Re-serialize the canvas (`POST /computgraph/context/pull`) and confirm the accepted entity reports `source: "recognized"`. Save the `.gh`, reopen, re-pull -- confirm `source: recognized` survived save/reopen (ValueTable persistence).
  4. REJECT a different proposal id, toggle `Apply`. Confirm the preview group is removed cleanly (no orphan group/scribble) and leaves the pending list.
  5. PARTIAL ACCEPT: with 3+ proposals pending, accept one and reject one in the same Apply. Confirm the third stays pending and can be applied later.
  6. NO-NEO4J: confirm nothing in this flow contacted Neo4j/data-service for persistence -- the graph is unchanged until Phase 36.
- No blockers for Phase 36 (confirmed-only publish) -- the `dg.recognized.<guid>` write path (this plan) and the `Recognized` read path (Plan 35-02) are both in place and unit-tested; only the live-canvas save/reopen/re-serialize round-trip needs human confirmation.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-19*

## Self-Check: PASSED

`DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` confirmed created on disk; `DG/src/DG.Grasshopper/DgIcons.cs`, `DG/src/DG.Grasshopper/Properties/StructureConfirm24.png`, and `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs` confirmed modified on disk; commits `428888f` and `253e863` confirmed in `git log`; `dotnet build DG/DG.sln -c Release` (0 errors, 0 warnings) and `dotnet test DG/tests/DG.Tests/` (350/350 pass) re-confirmed at SUMMARY-writing time; GUID `A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14` appears exactly once in `StructureConfirmComponent.cs` and nowhere else under `Components/`; source-assertion grep for `HttpClient|data-service|neo4j|Neo4j` returns 0 matches.
