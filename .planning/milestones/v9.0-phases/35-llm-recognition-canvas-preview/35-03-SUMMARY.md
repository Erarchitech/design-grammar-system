---
phase: 35-llm-recognition-canvas-preview
plan: 03
subsystem: canvas
tags: [csharp, grasshopper, canvas-bridge, preview-registry, undo-record, ui-thread-marshalling]

# Dependency graph
requires:
  - phase: 35-llm-recognition-canvas-preview (plan 02)
    provides: PreviewRegistry (ConcurrentDictionary-backed)/PreviewEntry/ProposalDto, CanvasAnnotationStyles.PreviewPrefix, RawGroup.Recognized read path
provides:
  - CanvasListenerComponent.HandlePreviewStructure/HandleClearPreview/HandleGetPreviewStatus (real handlers replacing the three v9.0 StubResult lambdas)
  - CanvasListenerComponent.InvokeOnCanvasWrite(Func<GH_Document, object?>) -- UI-thread direct-mutation write-marshalling helper (write counterpart to the existing read-only InvokeOnCanvas)
  - Bridge wire behavior: preview_structure/clear_preview/get_preview_status now return live results (no longer "Not supported in v9.0")
affects: [35-04, wave-2-canvas-preview-components]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "InvokeOnCanvasWrite mirrors InvokeOnCanvas's TaskCompletionSource + RhinoApp.InvokeOnUiThread shape but mutates GH_Document directly on the UI thread (no ScheduleSolution -- the bridge command never runs inside another component's SolveInstance) and calls Grasshopper.Instances.InvalidateCanvas() before resolving, so the TCP response is sent only after the preview objects genuinely exist on canvas"
    - "Component-instance field (_previewLegendGuid) used for legend-scribble bookkeeping that doesn't belong in the shared PreviewRegistry (which only tracks per-proposal group guids)"

key-files:
  created: []
  modified:
    - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs

key-decisions:
  - "InvokeOnCanvasWrite implemented as a private instance method (not static as the task text literally said) because it calls the inherited OnPingDocument() to obtain the live document -- a truly static method has no instance to call it on. Signature (Func<GH_Document, object?>) and behavior (direct mutation, InvalidateCanvas before resolving, exception->tcs.SetException) match the plan's intent exactly."
  - "ParseProposals synthesizes a stable per-request index-based proposalId (p0, p1, ...) because the wire proposal shape emitted by cg_recognition.py carries kind/suggestedName/procedureIndex/memberIds/confidence/rationale but no id of its own, while PreviewRegistry.RegisterAll (Plan 35-02) zips created group guids against ProposalDto by ProposalId."
  - "HandlePreviewStructure catches ProposalDto.ToEntityTagKind()'s ArgumentOutOfRangeException per-proposal and guard-and-continues (skips just that proposal) rather than aborting the whole render over one LLM-suggested unrecognized kind string."
  - "Confidence rendered in the group NickName as a rounded percentage via (confidence*100).ToString(\"F0\") -- e.g. [?] MyProc (85%) -- matching the plan's `[?] <suggestedName> (<confidence>)` truth."
  - "get_preview_status derives memberCount live from the on-canvas GH_Group's ObjectIDs.Count (looked up by the registry's stored GroupGuid) rather than storing a redundant count in PreviewEntry, since PreviewEntry (frozen from Plan 35-02) has no such field."

patterns-established:
  - "Write-marshalling counterpart to a read-marshalling helper: when a background-thread bridge command must mutate GH_Document (not just read it), add a parallel InvokeOnCanvasWrite rather than overloading InvokeOnCanvas's read-only contract."

requirements-completed: [RCGN-02]

coverage:
  - id: D1
    description: "BuildDispatcher routes preview_structure/clear_preview/get_preview_status to real handlers (no StubResult reference remains); InvokeOnCanvasWrite exists and calls InvalidateCanvas() after the delegate; get_preview_status is a live read of PreviewRegistry.Pending via the existing InvokeOnCanvas read path"
    requirement: "RCGN-02"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (0 errors, GRASSHOPPER_SDK branch compiled against real Rhino 8 / Grasshopper.dll)"
        status: pass
      - kind: unit
        ref: "grep -n StubResult DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs (zero matches)"
        status: pass
    human_judgment: false
  - id: D2
    description: "HandlePreviewStructure draws one desaturated [?]-prefixed GH_Group per proposal plus one scribble legend inside exactly one GH_UndoRecord(\"DG structure proposal\"), registers them into PreviewRegistry; HandleClearPreview removes every pending group + the legend and empties the registry; unparseable/absent member ids and unrecognized kinds are guard-and-continue"
    requirement: "RCGN-02"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release && dotnet test DG/tests/DG.Tests/ (350/350 pass, 0 failed)"
        status: pass
      - kind: unit
        ref: "grep -c 'GH_UndoRecord(\"DG structure proposal\")' CanvasListenerComponent.cs == 1"
        status: pass
    human_judgment: false
  - id: D3
    description: "Live-Rhino behavior: preview groups render visually distinct (desaturated + [?] prefix + legend), one Ctrl+Z removes every trace with no orphans, clear_preview leaves no residue and get_preview_status reports zero pending afterward, and the write survives a concurrent-solve safety exercise (Assumption A2)"
    verification: []
    human_judgment: true
    rationale: "net9.0 DG.Tests cannot reference the net7.0-windows GH assembly (NU1201 TFM incompatibility) -- canvas rendering, undo-stack behavior, and concurrent-solve safety can only be observed in a live Rhino 8/Grasshopper session, not xUnit. Deferred to phase-level manual UAT per project precedent (Phases 33, 34-02, 34-03, 29-03)."

# Metrics
duration: 9min
completed: 2026-07-19
status: complete
---

# Phase 35 Plan 03: Real Canvas Preview Handlers Summary

**`CanvasListenerComponent`'s three preview bridge commands are now real: `preview_structure` draws desaturated `[?] <name> (<confidence>%)` `GH_Group`s plus a scribble legend inside one `GH_UndoRecord`, `clear_preview` removes them programmatically, and `get_preview_status` reads the shared `PreviewRegistry` -- all via a new `InvokeOnCanvasWrite` UI-thread write-marshalling helper.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-19T09:37:01Z
- **Completed:** 2026-07-19T09:46:00Z
- **Tasks:** 2 automated tasks completed; 1 checkpoint (live-Rhino UAT) deferred per project convention
- **Files modified:** 1

## Accomplishments

- `BuildDispatcher` now wires `preview_structure`/`clear_preview`/`get_preview_status` to real method-group handlers -- zero remaining `StubResult` references
- New `InvokeOnCanvasWrite(Func<GH_Document, object?>)`: mirrors the existing read-only `InvokeOnCanvas`'s `TaskCompletionSource`/`RhinoApp.InvokeOnUiThread` shape but mutates the document directly on the UI thread (no `ScheduleSolution` -- the bridge command never runs inside another component's `SolveInstance`), calls `Grasshopper.Instances.InvalidateCanvas()` before resolving, and resolves a null-document case to a structured result instead of throwing
- `HandleGetPreviewStatus` is a pure read (`InvokeOnCanvas`) of `PreviewRegistry.Pending`, projecting `proposalId`/`kind`/`suggestedName`/`confidence`/a live `memberCount` derived from the on-canvas `GH_Group.ObjectIDs.Count`
- `HandlePreviewStructure` parses the bridge's `{"proposals":[...]}` parameters into `ProposalDto`s (synthesizing a stable `p0`/`p1`/... id, since the wire shape carries none), draws one preview `GH_Group` per proposal (`CanvasAnnotationStyles.Preview(ForKind(...))` color, `[?] <suggestedName> (<confidence>%)` NickName) plus one `GH_Scribble` legend, all inside a single `GH_UndoRecord("DG structure proposal")`, then registers the created groups into `PreviewRegistry`
- `HandleClearPreview` removes every group in `PreviewRegistry.Pending` plus the stashed legend scribble and empties the registry
- Guard-and-continue throughout: unparseable/absent member ids are skipped without throwing; an unrecognized proposal `kind` skips just that proposal instead of aborting the whole render

## Task Commits

Each task was committed atomically (Task 1 dispatcher/read-path wiring and Task 2 write-path bodies landed in one commit -- see Deviations for why):

1. **Task 1 + Task 2: Real preview handlers + InvokeOnCanvasWrite + undo-record render/clear** - `596758c` (feat)

**Plan metadata:** (this commit) `docs(35-03): complete real canvas preview handlers plan`

## Files Created/Modified

- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` - Real `HandlePreviewStructure`/`HandleClearPreview`/`HandleGetPreviewStatus` handlers, `InvokeOnCanvasWrite` write-marshalling helper, `ParseProposals`/`TryGetJsonString` JSON-parsing helpers, `_previewLegendGuid` bookkeeping field

## Decisions Made

- `InvokeOnCanvasWrite` implemented as a private **instance** method (not static as the task text literally described) because it must call the inherited `OnPingDocument()` to get the live document; behavior and signature otherwise match the plan's intent exactly.
- Synthesized `p{index}` proposal ids since the wire proposal shape (data-service `cg_recognition.py`) has no id field of its own, while `PreviewRegistry.RegisterAll` (Plan 35-02, frozen) requires one to zip against created group guids.
- Confidence rendered as a rounded percentage (`(confidence*100).ToString("F0")`) in the group NickName, matching the plan's `[?] <suggestedName> (<confidence>)` truth literally.
- `memberCount` in `get_preview_status` is derived live from the on-canvas group's `ObjectIDs.Count` rather than stored redundantly, since `PreviewEntry` (frozen from Plan 35-02) carries no member-count field.
- An unrecognized proposal `kind` (an `ArgumentOutOfRangeException` from `ProposalDto.ToEntityTagKind()`) is caught per-proposal and skipped (guard-and-continue) rather than letting one malformed LLM suggestion abort the entire preview batch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `InvokeOnCanvasWrite` is an instance method, not static**
- **Found during:** Task 1 (InvokeOnCanvasWrite + BuildDispatcher swap)
- **Issue:** The task text described `InvokeOnCanvasWrite` as "private static" while also requiring it to "pass `OnPingDocument()` into work" -- `OnPingDocument()` is an inherited instance method with no static-callable overload, so a literally-static method cannot obtain the document itself.
- **Fix:** Declared `InvokeOnCanvasWrite` as a private instance method. Signature (`Func<GH_Document, object?>`), the `TaskCompletionSource`/`RhinoApp.InvokeOnUiThread` shape, the null-document guard, and the `InvalidateCanvas()`-before-resolve behavior are all otherwise identical to the plan's description.
- **Files modified:** DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
- **Verification:** `dotnet build DG/DG.sln -c Release` compiles clean against the real Grasshopper SDK (Rhino 8 present on this machine, GRASSHOPPER_SDK branch actually compiled, not just the `#else` stub).
- **Committed in:** 596758c

**2. [Rule 1 - Bug/robustness] Synthesized proposal ids -- wire shape carries none**
- **Found during:** Task 2 (ParseProposals / HandlePreviewStructure)
- **Issue:** `data-service/cg_recognition.py`'s proposed-structure JSON has fields `kind`/`suggestedName`/`procedureIndex`/`memberIds`/`confidence`/`rationale` per proposal -- no `proposalId`. `ProposalDto` (Plan 35-02, frozen) requires one, and `PreviewRegistry.RegisterAll` zips `(proposalId, groupGuid)` pairs against `ProposalDto`s by that id; leaving it empty for every proposal would collide (all "" keys) and silently drop all but one registration.
- **Fix:** `ParseProposals` synthesizes a stable per-request index-based id (`p0`, `p1`, ...) for each parsed proposal.
- **Files modified:** DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
- **Verification:** `HandlePreviewStructure`'s `created` list pairs each group with its proposal's synthesized id 1:1; `PreviewRegistry.RegisterAll` (unit-tested in Plan 35-02) zips them without collision since ids are unique within a single request.
- **Committed in:** 596758c

**3. [Rule 1 - Bug/robustness] Unrecognized proposal `kind` is guard-and-continue, not fatal**
- **Found during:** Task 2 (HandlePreviewStructure)
- **Issue:** `ProposalDto.ToEntityTagKind()` throws `ArgumentOutOfRangeException` for an unrecognized kind string (by design, Plan 35-02 -- "never guess"). Left unguarded, one malformed LLM-suggested kind in a batch would throw inside `InvokeOnCanvasWrite`'s UI-thread callback, propagating to `tcs.SetException` and turning the *entire* `preview_structure` call into a `HANDLER_ERROR` -- discarding every other valid proposal in the same batch.
- **Fix:** Wrapped the `ToEntityTagKind()` call in a try/catch per proposal; an unrecognized kind skips just that proposal (`continue`) rather than aborting the whole render.
- **Files modified:** DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
- **Verification:** Mirrors the plan's explicit guard-and-continue philosophy for member ids (same acceptance criterion category); build clean, no regression in the 350-test DG.Tests suite.
- **Committed in:** 596758c

**4. [Process note] Tasks 1 and 2 landed as a single commit, not two**
- **Found during:** Implementation
- **Issue:** Both tasks edit the exact same method bodies (`HandlePreviewStructure`/`HandleClearPreview`) in the exact same file -- Task 1's own text explicitly describes its stub bodies as scaffolding "so the file compiles," to be replaced by Task 2's real bodies. Committing an intermediate stub-only state and then immediately overwriting it in the very next commit would not represent meaningful project history.
- **Fix:** Implemented both tasks' final state directly and committed once (`596758c`), after independently verifying every acceptance criterion listed under both Task 1 and Task 2 in the plan.
- **Files modified:** DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
- **Verification:** All Task 1 acceptance criteria (dispatcher wiring, `InvokeOnCanvasWrite` existence/behavior, `get_preview_status` read-marshalling) and Task 2 acceptance criteria (single `GH_UndoRecord`, `RegisterAll`/`Clear` calls, guard-and-continue) independently confirmed via grep + build + test, documented above.
- **Committed in:** 596758c

---

**Total deviations:** 4 (3 auto-fixed under Rules 1/3, 1 commit-granularity process note).
**Impact on plan:** All three code-level fixes were necessary for correctness (a static method that cannot call an instance method would not compile; an un-synthesized proposal id would silently break registry zipping; an unguarded unrecognized kind would abort an entire valid batch over one bad entry). No scope creep -- no new files, no architectural changes, no new dependencies.

## Issues Encountered

None beyond the deviations documented above. `dotnet test DG/tests/DG.Tests/` ran 350/350 green this session (0 failures) -- the project-memory-documented env-dependent Neo4j-down baseline (3-4 `DesignStateValidationFlowTests.E2E` failures) did not manifest, indicating Neo4j was reachable during this run; this plan's changes are nowhere near that dependency (`Components`/`Canvas` files only) so this is incidental, not a regression signal either way.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All automatable work for RCGN-02's preview-render/clear/status contract is complete and green (build + 350/350 tests). `PreviewRegistry` now has real writers (`HandlePreviewStructure`) and a real reader path (`HandleGetPreviewStatus`), ready for Plan 35-04's `StructureConfirmComponent` (Accept/Reject/Apply) to consume.
- **Task 3 (live-Rhino UAT) is explicitly DEFERRED to phase-level `/gsd-verify-work 35`, not self-approved as passed** -- per this plan's `checkpoint_policy` (precedent: Phases 33, 34-02, 34-03, 29-03). The following checks remain human_needed and must be exercised in a live Rhino 8 / Grasshopper session before Phase 35 is accepted:
  1. Build `dotnet build DG/DG.sln -c Release`, load `DG.gha` into Rhino 8/Grasshopper, open the Frame definition, place `DG CANVAS LISTENER` with `Run=true`.
  2. `POST /computgraph/context/pull` -> `POST /computgraph/recognize` -> send a `preview_structure` bridge command (via `/mcp gh_preview_structure` or a direct bridge call) with the returned proposals.
  3. Confirm preview groups render: desaturated color, NickName begins `[?] `, includes the suggested name and a confidence percentage; a scribble legend reads `"N proposal(s) pending"`; visually distinct from manual Phase-34 tag groups.
  4. Press Ctrl+Z ONCE -- confirm every preview group AND the legend scribble disappear together (single undo record), no orphans.
  5. Re-run `preview_structure`, then send `clear_preview` -- confirm all preview objects are removed and `get_preview_status` then reports zero pending.
  6. **Concurrent-solve safety (Assumption A2):** while dragging/actively editing another part of the canvas (a solve in progress), send a `preview_structure` command -- confirm no document corruption, no exception, previews still render correctly.
  7. Confirm the documented scope relaxation ("dashed" -> desaturated + `[?] ` prefix + legend; legend is text-only) is visually sufficient against the Frame reference, or note if it is not.
- No blockers for Plan 35-04 -- `PreviewRegistry`'s writer (this plan) and the frozen reader/mutator surface (`TryGet`/`Remove`/`Clear`) from Plan 35-02 are both in place.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-19*

## Self-Check: PASSED

File `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` confirmed modified on disk; commit `596758c` confirmed in `git log`; `dotnet build DG/DG.sln -c Release` (0 errors) and `dotnet test DG/tests/DG.Tests/` (350/350 pass) re-confirmed at SUMMARY-writing time; `grep -c "GH_UndoRecord(\"DG structure proposal\")"` == 1; zero remaining `StubResult` references in the file.
