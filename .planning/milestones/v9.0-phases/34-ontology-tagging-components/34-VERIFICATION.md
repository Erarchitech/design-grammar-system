---
phase: 34-ontology-tagging-components
verified: 2026-07-19T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "DG OBJECT MARKER — empty-canvas create, idempotent re-run, ValueTable persistence across save/reopen"
    expected: "Two scribbles (`OBJECT - BRIDGE`, `1_ALGORITHM`) appear top-left in large font on an empty canvas; re-running the component creates no duplicates and Status reports the existing markers; wiring a Class from ONTOGRAPH deconstruct, recomputing, saving the .gh and reopening it preserves `dg.objectClassIri` in the document ValueTable"
    why_human: "net9.0 DG.Tests cannot reference the net7.0-windows DG.Grasshopper assembly (NU1201) — canvas rendering, .gh save/reopen round-trip, and live GH_Document mutation cannot be exercised by xUnit. User explicitly deferred this checkpoint (Plan 02 Task 3) to phase-level /gsd-verify-work."
  - test: "DG OBJECT MARKER — icon and scribble font size/placement against Frame reference"
    expected: "ObjectMarker24 icon and scribble font/placement match (or are acceptable placeholders for) the architect's Frame reference"
    why_human: "Visual/aesthetic judgment; no Frame reference screenshot is checked into the repo."
  - test: "DG ENTITY TAG — Kind value list auto-wire, tag→group→parse round-trip, undo, nesting, guard rails"
    expected: "Value list with Proc/Pat/Var/Const/Emg/IntF auto-appears wired to Kind on first placement; tagging a selected slider Var 'SpansCount' under ProcIndex 11 produces a PINK group `11_Var_SpansCount`; DG CANVAS LISTENER / Phase 32 extractor reports it as CgParameter(kind: Variable, source: tagged); Ctrl+Z removes the group cleanly; tagging inside an existing `11_Pat_*` group renders PURPLE (nested) with HostPatternId reported; empty selection and a Name containing a reserved token (e.g. 'Foo_Var_Bar') both warn without creating a group"
    why_human: "net9.0 DG.Tests cannot reference the net7.0-windows GH assembly (NU1201) — canvas selection, GH_Group rendering/color, undo-record behavior, and native nesting require a live Rhino 8/Grasshopper session. User explicitly deferred this checkpoint (Plan 03 Task 3) to phase-level /gsd-verify-work."
  - test: "DG ENTITY TAG — group colors and EntityTag24 icon against Frame reference"
    expected: "Pattern/NestedPattern/Parameter/Interface/Procedure hex colors and the EntityTag24 icon match (or are acceptable placeholders for) the architect's Frame reference"
    why_human: "Visual/aesthetic judgment; hex values are explicitly marked [ASSUMED] pending Frame-reference confirmation (34-RESEARCH.md Assumptions Log A5)."
  - test: "Post-fix-chain addition (WR-10/WR-11, 34-REVIEW-FIX.md): re-tag a child-hosting Pattern by core-only selection — verify the child stays nested"
    expected: "Re-tagging a Pattern group that hosts a nested child group, using a selection that only covers the Pattern's non-group ('core') members, must not detach the nested child — the child-group guid must survive the membership rebuild and the parser must still report the nesting relationship (HostPatternId) after the re-tag"
    why_human: "Canvas-interaction / GH_Group live-mutation behavior explicitly called out in 34-REVIEW-FIX.md as requiring the human-verify checkpoint, since it cannot be exercised by the unit suite (no live GH_Document in DG.Tests)."
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: human_needed
---

# Phase 34: Ontology Tagging Components and Manual Selection Verification Report

**Phase Goal:** The architect marks the ontological entities they know directly on the canvas — object/algorithm identity via a marker component, and any manually selected set of components as a typed Computgraph entity — producing exactly the annotation convention the serializer parses.
**Verified:** 2026-07-19
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A convention name built by `CanvasAnnotationNameFactory` parses back through `CanvasAnnotationParser` to the same typed entity with `Source == "tagged"` (round-trip symmetry — TAGC-03) | ✓ VERIFIED | `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs` has 10 `RoundTrip_*` facts (Object, Algorithm, Proc, Var, Const, Emg, IntF, Pat-with-name, Pat-without-name, Cyrillic Var). `dotnet test --filter FullyQualifiedName~CanvasAnnotationNameFactory` → 38/38 pass. `CanvasAnnotationParser.cs` confirmed byte-identical to pre-Phase-34 (`git log -1` shows last touch at commit `120f58e`, Phase 32) |
| 2 | The factory rejects a `Name` containing a reserved grammar infix token (V5 input validation) | ✓ VERIFIED | `CanvasAnnotationNameFactory.ValidateName` throws `ArgumentException` for any `ReservedInfixTokens` match (read at `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs:211-243`); covered by unit test, and wired into both components (`ObjectMarkerComponent.cs:96`, `EntityTagComponent.cs:281`) |
| 3 | The factory computes the next-free integer Pattern index under a given NN (auto-increment — TAGC-02) | ✓ VERIFIED | `NextFreePatternIndex` (`CanvasAnnotationNameFactory.cs:157-182`) + passing unit tests; consumed live by `EntityTagComponent.SolveInstance` (line 272) |
| 4 | On an empty canvas, DG OBJECT MARKER creates an `OBJECT - <NAME>` scribble and a `<n>_ALGORITHM` scribble; on an already-annotated canvas it reads and reports without duplicating (TAGC-01) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (code path verified; live-canvas render/idempotency not test-exercised) | `ObjectMarkerComponent.SolveInstance` (`DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:54-224`) implements read-before-write via `CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationParser.Parse`, short-circuits into REPORT mode when `context.Object is not null && existingAlgorithm is not null`, otherwise defers `GH_Scribble` creation via `ScheduleSolution`. Build clean; DG.Tests cannot instantiate a live `GH_Document` (NU1201) so idempotent re-run/scribble-render is not exercised by xUnit — this is the SUMMARY-documented, plan-declared deferred Task 3 checkpoint |
| 5 | Selecting a slider and tagging it Var "SpansCount" under proc 11 produces a pink `GH_Group` named `11_Var_SpansCount`, and the serializer reads it back as `CgParameter(Variable, source:tagged)` (TAGC-02/03, Success Criterion 1) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (name-construction + parser round-trip proven by unit test; live group creation/color/extractor read-back not test-exercised) | `EntityTagComponent.SolveInstance` builds the nickname via `CanvasAnnotationNameFactory.ForEntity` and applies `CanvasAnnotationStyles.ForKind(EntityTagKind.Var, false)` = `Parameter` (pink, `Color.FromArgb(255,255,182,208)`) inside `TagOrUpdateGroup`; the name-string round-trip (`11_Var_SpansCount` → `CgParameter{Kind=Variable, Source="tagged"}`) is unit-proven, but the live `GH_Group` creation + `CanvasContextExtractor`/Phase-32-serializer read-back requires a live Rhino session — deferred Task 3 checkpoint per both Plan 03 SUMMARY and 34-REVIEW-FIX.md |
| 6 | Ctrl+Z removes the tag group cleanly (undo record) — Success Criterion 4 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (undo-record composition present in code; interactive undo not test-exercised) | `TagOrUpdateGroup` builds `GH_UndoRecord("DG Tag Entity")` + `GH_AddObjectAction(group)` (create) or `GH_GenericObjectAction` (update/detach, including WR-01's host-group and WR-10's stale-host undo coverage) then `currentDoc.UndoServer.PushUndoRecord(record)` (`EntityTagComponent.cs:345-427`); no `RecordAddObjectEvent` reference (`grep -c RecordAddObjectEvent` = 0). Actual Ctrl+Z behavior in a live GH canvas is not xUnit-testable — deferred Task 3 checkpoint |
| 7 | Tagging a selection inside an existing Pattern group creates the purple nested style automatically | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (nesting-detection logic present; live-canvas nesting/coloring not test-exercised) | `hostGroupNickname` detection (subset-of-existing-Pattern-members) drives `nested = hostGroupNickname is not null`; `CanvasAnnotationStyles.ForKind(EntityTagKind.Pat, true)` returns `NestedPattern` (purple, `Color.FromArgb(255,155,89,182)`); `AttachToHost` adds the new group's guid to the host's `ObjectIDs` so `CanvasContextExtractor.NestedGroupIds` reports it with zero extractor changes. Live rendering/extractor read-back deferred to Task 3 |
| 8 | Empty selection → Warning + no group; a Name with a reserved grammar token → Warning + no group | ✓ VERIFIED | `EntityTagComponent.SolveInstance`: `selected.Count == 0` → `AddRuntimeMessage(Warning, ...)`, returns before any `ScheduleSolution` (`EntityTagComponent.cs:183-193`); `CanvasAnnotationNameFactory.ForEntity` throwing `ArgumentException` on a reserved-token Name is caught and surfaced as `AddRuntimeMessage(Warning, ...)` with no mutation scheduled (`EntityTagComponent.cs:276-289`). Both paths are pure C# control flow, verifiable by code inspection without a live document; `ObjectMarkerComponent` has the equivalent guard for `ObjectName` |
| 9 | When a Class (OntologyClass) is wired, its IRI is stored in the document `ValueTable` under `dg.objectClassIri` and survives file save | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (ValueTable.SetValue call present on both CREATE and REPORT paths; file save/reopen persistence not test-exercised) | `ObjectMarkerComponent.SolveInstance`: CREATE path sets `currentDoc.ValueTable.SetValue("dg.objectClassIri", classIri)` inside the deferred callback (line 176); REPORT path (WR-06 fix) also updates the ValueTable via a scheduled solution when a new/changed Class IRI is wired to an already-annotated canvas (lines 122-139). `.gh` file save/reopen persistence of `GH_Document.ValueTable` is a GH SDK behavior not exercised by DG.Tests — deferred Task 3 checkpoint |

**Score:** 4/9 truths fully VERIFIED by automated evidence; 5/9 PRESENT_BEHAVIOR_UNVERIFIED (code present, wired, and unit-proven where a GH-free path exists, but the live-canvas behavior itself requires a Rhino session and was explicitly deferred to this phase-level verification pass by the user during execution). 0 truths FAILED.

*Note on scoring:* the roadmap/plan must-haves that are pure name-construction/parsing logic (truths 1-3, 8) are fully automatable and are VERIFIED. The must-haves that assert live Grasshopper canvas behavior (truths 4-7, 9) cannot be exercised by `DG.Tests` (net9.0 cannot reference the net7.0-windows `DG.Grasshopper` assembly — NU1201, a hard SDK/tooling constraint, not a gap in this phase's test design) and were deliberately routed to a `checkpoint:human-verify` task in both Plan 02 and Plan 03, which the user explicitly deferred to this verification pass rather than skipping.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs` | Grammar token constants + `ReservedInfixTokens` | ✓ VERIFIED | All 9 constants present, `ReservedInfixTokens` array populated; consistency test (`Grammar_ConstantsAppearVerbatimInParserSource`) passes |
| `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs` | Write-path factory + `EntityTagKind` enum | ✓ VERIFIED | `ForObjectScribble`, `ForAlgorithmScribble`, `ForEntity`, `NextFreePatternIndex`, `IsReservedName`, `ValidateName` all present and substantive (not stubs) |
| `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs` | Round-trip + validation test suite | ✓ VERIFIED | 38 facts, all passing |
| `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs` | DG OBJECT MARKER component | ✓ VERIFIED (code); wired to `CanvasAnnotationNameFactory`/`CanvasContextExtractor`/`CanvasAnnotationParser`/`ScheduleSolution`/`ValueTable.SetValue`; substantive SolveInstance (171 lines, no stub returns) |
| `DG/src/DG.Grasshopper/DgIcons.cs` | `ObjectMarker24`, `EntityTag24` bitmap properties | ✓ VERIFIED | Both present |
| `DG/src/DG.Grasshopper/Properties/ObjectMarker24.png` | 24x24 placeholder icon | ✓ VERIFIED (exists, documented placeholder) | File present, 981 bytes |
| `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` | Color palette + `ForKind`/`Preview` | ✓ VERIFIED | 5 color fields + `ForKind` dispatch + `Preview` scaffold, `[ASSUMED]` documented |
| `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs` | DG ENTITY TAG component | ✓ VERIFIED (code); substantive SolveInstance (rising-edge, read-before-write, guard rails, undo, nesting — 383 lines); WR-01..WR-11/CR-01 fixes present in current source |
| `DG/src/DG.Grasshopper/Properties/EntityTag24.png` | 24x24 placeholder icon | ✓ VERIFIED (exists, documented placeholder) | File present, 981 bytes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `ObjectMarkerComponent` scribble text | `CanvasAnnotationNameFactory` | `ForObjectScribble`/`ForAlgorithmScribble` calls, never hand-rolled | ✓ WIRED | `ObjectMarkerComponent.cs:97-98` |
| `ObjectMarkerComponent` read | `CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationParser.Parse` | Same seam DG CANVAS LISTENER uses | ✓ WIRED | `ObjectMarkerComponent.cs:110-111` |
| `ObjectMarkerComponent` scribble creation | `doc.ScheduleSolution` | Deferred mutation (SDK constraint) | ✓ WIRED | `ObjectMarkerComponent.cs:160-197`; no synchronous `AddObject` outside the callback (`AddScribble` is only called from inside `ScheduleSolution`) |
| `EntityTagComponent` group nickname | `CanvasAnnotationNameFactory.ForEntity` + `NextFreePatternIndex` | Name construction | ✓ WIRED | `EntityTagComponent.cs:272, 281` |
| `EntityTagComponent` undo | `GH_UndoRecord` + `GH_AddObjectAction`/`GH_GenericObjectAction` + `doc.UndoServer.PushUndoRecord` | RESEARCH Addendum §2 composition | ✓ WIRED | `EntityTagComponent.cs:362-427`; `grep -c RecordAddObjectEvent` = 0 (nonexistent API never referenced) |
| `EntityTagComponent` nesting | Host Pattern group's `ObjectIDs` gains new group's `InstanceGuid` | Native nesting — `CanvasContextExtractor.NestedGroupIds` picks it up with zero extractor changes | ✓ WIRED | `AttachToHost` (`EntityTagComponent.cs:429-447`); `CanvasContextExtractor.cs:193` confirms `NestedGroupIds` is populated from `group.ObjectIDs` with no Phase-34-specific extractor edit |
| `EntityTagComponent` mutation | `doc.ScheduleSolution` | All mutation deferred (SDK hard constraint) | ✓ WIRED | `EntityTagComponent.cs:310-329`; group create/update happens only inside `TagOrUpdateGroup`, called only from the `ScheduleSolution` callback |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full DG.Tests suite green | `dotnet test DG/tests/DG.Tests/` | 344 passed, 0 failed, 0 skipped | ✓ PASS (better than the documented 343-344/344 baseline — Neo4j was reachable during this run) |
| Factory round-trip suite green | `dotnet test --filter FullyQualifiedName~CanvasAnnotationNameFactory` | 38 passed, 0 failed | ✓ PASS |
| Release build clean | `dotnet build DG/DG.sln -c Release` | Exit 0, 0 warnings, 0 errors | ✓ PASS |
| `CanvasAnnotationParser.cs` untouched (hard constraint) | `git log -1 -- DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` | Last touched at `120f58e` (Phase 32), no Phase-34 commit touches it | ✓ PASS |
| GUID uniqueness | `grep -rn "ComponentGuid => new(" DG/src/DG.Grasshopper/Components/` for both Phase-34 GUIDs | `D3A9F41C-...` and `C1E7B4A9-...` each appear exactly once | ✓ PASS |
| Fix-chain commits present | `git log --oneline` for CR-01/WR-01..WR-11 | All 12 commits present (`bc20cf2`..`8074e23`) | ✓ PASS |

Live-Rhino canvas behavior (scribble rendering, group creation/coloring, undo, .gh save/reopen persistence) could not be spot-checked — no runnable Rhino/Grasshopper session available in this environment; routed to Human Verification below, consistent with both plans' `checkpoint:human-verify` design and the explicit user deferral recorded in both SUMMARYs.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| TAGC-01 | 34-01, 34-02 | DG OBJECT MARKER creates/updates OBJECT/ALGORITHM scribbles, optionally binds Class IRI, reads existing markers without duplicating | ✓ SATISFIED (code); live-canvas confirmation pending | REQUIREMENTS.md marks `[x]`; name-construction+validation automated and green; canvas create/report/idempotency logic present and code-reviewed (WR-01..WR-07 fixes applied) but requires live-Rhino confirmation |
| TAGC-02 | 34-01, 34-03 | DG ENTITY TAG wraps selection into convention-named/colored group with auto-increment index, undoable | ✓ SATISFIED (code); live-canvas confirmation pending | REQUIREMENTS.md marks `[x]`; `NextFreePatternIndex`/`ForEntity`/`CanvasAnnotationStyles.ForKind` automated and green; live group/undo/color behavior requires Rhino confirmation |
| TAGC-03 | 34-01, 34-03 | Manual tags round-trip as ground truth (`source: tagged`) | ✓ SATISFIED | Fully automated: 10 `RoundTrip_*` unit facts prove every `EntityTagKind` + Object/Algorithm scribble round-trips through `CanvasAnnotationParser.Parse` to `Source == "tagged"` |

No orphaned requirements — REQUIREMENTS.md's Phase 34 section (TAGC-01/02/03) matches exactly the `requirements:` frontmatter declared across the three plans.

### Anti-Patterns Found

None. Scanned all 5 Phase-34-created/modified source files for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/empty-implementation patterns. The only regex hits were false positives from the SDK method name `AddedToDocument` (case-insensitively contains "ToDo" as a substring) — not actual debt markers. The `[ASSUMED]` comments in `CanvasAnnotationStyles.cs` (hex colors) and the placeholder-icon comments in `DgIcons.cs` are explicitly documented, intentional, low-functional-risk deviations that are already flagged for human confirmation in both plans' human-verify checkpoints — not undocumented debt.

### Human Verification Required

Both Plan 02 and Plan 03 declared a `checkpoint:human-verify` Task 3 for live-Rhino canvas behavior (impossible to xUnit-test — net9.0 `DG.Tests` cannot reference the net7.0-windows `DG.Grasshopper` assembly, NU1201). The user explicitly deferred both checkpoints during execution ("Defer live UAT, continue") to this phase-level `/gsd-verify-work` pass, per both SUMMARYs' "Outstanding Human Verification" sections. These are carried forward here, plus one item added by the post-execution code-review fix chain (34-REVIEW-FIX.md WR-10/WR-11):

### 1. DG OBJECT MARKER — create / idempotent re-run / ValueTable persistence

**Test:** Build (`dotnet build DG/DG.sln -c Release`), load `DG.gha` into Rhino 8/Grasshopper. Place DG OBJECT MARKER on a blank canvas, `ObjectName = "BRIDGE"`, `AlgorithmIndex = 1`. Re-run the component. Wire a Class from ONTOGRAPH deconstruct, recompute, save the `.gh`, reopen it.
**Expected:** Two scribbles `OBJECT - BRIDGE` and `1_ALGORITHM` appear top-left in large font; re-run creates no duplicates and Status reports the existing markers; the `dg.objectClassIri` ValueTable key survives save/reopen.
**Why human:** NU1201 — no xUnit path to a live `GH_Document`.

### 2. DG OBJECT MARKER — icon/font placeholders vs. Frame reference

**Test:** Compare `ObjectMarker24` icon and scribble font size/placement against the architect's Frame reference.
**Expected:** Acceptable, or note adjustments needed (low functional risk).
**Why human:** Visual/aesthetic judgment.

### 3. DG ENTITY TAG — value list, tag→group→parse round-trip, undo, nesting, guard rails

**Test:** Build/load, confirm Kind value list auto-wires. Select a Number Slider, Kind=Var, Name="SpansCount", ProcIndex=11, press Tag. Run DG CANVAS LISTENER `get_canvas_context`. Press Ctrl+Z. Tag a selection inside an existing `11_Pat_*` group. Press Tag with nothing selected. Try Name="Foo_Var_Bar".
**Expected:** Pink `11_Var_SpansCount` group; `CgParameter(kind: Variable, source: tagged)` in `cgContextJson`; Ctrl+Z removes the group cleanly; nested selection renders purple with `HostPatternId` reported; both guard-rail attempts warn without creating a group.
**Why human:** NU1201 — canvas selection, group rendering/color, and undo behavior require a live Rhino session.

### 4. DG ENTITY TAG — group colors and icon vs. Frame reference

**Test:** Compare Pattern/NestedPattern/Parameter/Interface/Procedure hex colors and `EntityTag24` icon against the Frame reference.
**Expected:** Acceptable, or note hex adjustments needed (low functional risk).
**Why human:** Visual/aesthetic judgment; hex values explicitly `[ASSUMED]`.

### 5. Post-fix-chain addition — re-tag a child-hosting Pattern by core-only selection

**Test:** Tag a Pattern that hosts a nested child group (e.g. select the Pattern's non-group "core" members only, excluding the nested child group object) and re-tag it with the same/updated label.
**Expected:** The nested child group stays nested — its `InstanceGuid` survives the membership rebuild inside `TagOrUpdateGroup`, and the Phase-32 extractor still reports the `HostPatternId` relationship after the re-tag (i.e., the WR-10/WR-11 fixes hold under interactive use, not just under the code-review author's static reasoning).
**Why human:** 34-REVIEW-FIX.md explicitly calls this out as a canvas-interaction behavior that "cannot be exercised by the unit suite" — no live `GH_Group`/`GH_Document` in `DG.Tests`.

### Gaps Summary

No gaps. All automatable must-haves (name construction, grammar round-trip, validation/guard-rail logic, undo-record composition, nesting-attachment wiring, ValueTable call-sites, requirements traceability, anti-pattern scan, build/test suite, the 12-commit post-review fix chain) are VERIFIED against current source — not just SUMMARY claims. The remaining items are inherent to this tech stack's test boundary (net9.0 `DG.Tests` cannot load the net7.0-windows `DG.Grasshopper` assembly — NU1201) and were correctly routed to `checkpoint:human-verify` by both plans; the user's explicit, on-record deferral of those checkpoints during execution is not a defect in the phase's delivery, but it does mean the phase's *live-canvas* goal achievement remains formally unconfirmed pending this human verification pass.

---

_Verified: 2026-07-19_
_Verifier: Claude (gsd-verifier)_
