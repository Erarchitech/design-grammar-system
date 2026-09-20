---
phase: 34-ontology-tagging-components
reviewed: 2026-07-18T22:14:12Z
depth: standard
iteration: 2
files_reviewed: 7
files_reviewed_list:
  - DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs
  - DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs
  - DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs
  - DG/src/DG.Grasshopper/Components/EntityTagComponent.cs
  - DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
  - DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs
findings:
  critical: 0
  warning: 1
  info: 9
  total: 10
status: issues_found
---

# Phase 34: Code Review Report (iteration 2 — fix verification)

**Reviewed:** 2026-07-18T22:14:12Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Re-review after the iteration-1 fix chain (bc20cf2..879887e, 9 commits — CR-01 + WR-01..WR-08). Verified each fix against the original finding, traced the new logic paths (`TryExtractPatternIndex`/`retagTargetNickname` re-tag reuse, `DetachFromStaleHosts` undo recording, expire-on-success-only flow), rebuilt `DG.sln` Release (0 warnings / 0 errors — `GRASSHOPPER_SDK` is defined unconditionally in the csproj, so all SDK-surface fix code actually compiled), and ran the full factory test suite (38/38 pass, including the three new WR-07 newline cases).

**Fix resolution verdict — all 9 iteration-1 findings resolved:**

| Finding | Verdict |
|---|---|
| CR-01 Pattern re-tag duplicates+nests | RESOLVED for the identical-selection case (double-press, label change) — but the equality predicate has a residual false-negative, re-filed as WR-09 |
| WR-01 host-group undo + stale-host detach | RESOLVED — `AttachToHost` records the host via `GH_GenericObjectAction` before mutating (line 404), `DetachFromStaleHosts` removes the child from every other Pattern host and records each before mutation (lines 415-428); action ordering (snapshot before mutation) is correct in all branches |
| WR-02 duplicate value lists on file open | RESOLVED — authoritative re-check of `Params.Input[0].Sources.Count` inside the scheduled delegate (lines 87-94) |
| WR-03 silent deferred-mutation failure | RESOLVED — both components carry failure in `_lastError` component state; EntityTag re-emits it on every non-rising-edge solve (lines 148-151), ObjectMarker re-emits in CREATE mode (lines 155-158) and no longer self-expires on failure so the delegate's message survives |
| WR-04 unbounded schedule→fail→expire loop | RESOLVED — `ExpireSolution(false)` moved inside the try, executed only after successful mutation (ObjectMarker line 185); the failure path leaves the component un-expired, so retry waits for a real user-triggered solve |
| WR-05 misreported canvas state | RESOLVED — per-artifact "Created:"/"Kept existing:" status, ObjectName output reflects `context.Object?.Name`, conflict Warning on input-vs-canvas identity mismatch (lines 199-223) |
| WR-06 Class IRI dropped in REPORT mode | RESOLVED — REPORT mode compares stored vs. input IRI, schedules a `ValueTable.SetValue` update on change, and reports the binding in Status (lines 119-144) |
| WR-07 `ForObjectScribble` newline round-trip hole | RESOLVED — factory-level rejection of `\n`/`\r` (factory lines 46-53) + 3 new theory cases (`\n`, `\r`, `\r\n`) in the test suite; round-trip guarantee is now enforced inside the factory itself |
| WR-08 direct `ObjectIDs.Clear()` | RESOLVED — membership rebuilt via `RemoveObject`/`AddObject` over a `ToList()` snapshot, followed by `ExpireCaches()` (lines 351-361) |

**Hard constraints — all upheld:**
- `CanvasAnnotationParser.cs` is byte-identical (empty `git diff` over the phase range; working tree clean for all in-scope sources).
- `#if GRASSHOPPER_SDK` + `#else` stub structure intact in both components (EntityTag 468-474, ObjectMarker 236-242); `DgIcons.cs` and `CanvasAnnotationStyles.cs` remain correctly gated.
- Round-trip guarantee holds for every factory-emitted shape reachable from the components (38/38 tests, including Cyrillic and Pat with/without label; the WR-07 fix closes the last factory-side hole).

One residual defect from the CR-01 fix is filed below (WR-09). The 7 iteration-1 Info findings were intentionally not fixed (out of critical/warning scope) and are carried forward unchanged (IN-01..IN-07, re-verified as still accurate against the current code); two new Info findings from the fix commits are added (IN-08, IN-09). No security regressions: reserved-token validation (T-34-01) is unchanged and still on every component-reachable name path.

## Warnings

### WR-09: Pat re-tag equality predicate false-negatives once the Pattern hosts a nested child group — CR-01's duplicate+nest returns for an identical selection

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:236-239` (with `CanvasContextExtractor.cs:171`)
**Issue:** The CR-01 fix detects a re-tag by exact member-set equality: `g.MemberIds.Count == selectedIds.Count && selectedIds.All(id => g.MemberIds.Contains(id))`. But the extractor's `MemberIds` is the group's raw `ObjectIDs` — which, after any nested tagging, also contains the *child group's* `InstanceGuid` (that is exactly what `AttachToHost` adds). Ordinary sequence: (1) tag objects M as `11_Pat_1`; (2) tag a subset as `11_Var_X` — `AttachToHost` adds the Var group's guid to `11_Pat_1.ObjectIDs`; (3) press Tag again on the same selection M with Kind=Pat (e.g. to add a label). Now `MemberIds.Count == |M| + 1 ≠ |M|`, the equality check fails, `patternIndex` auto-increments, and the nesting detector (selection ⊆ `11_Pat_1` members) creates `11_Pat_2` purple *inside* `11_Pat_1` — the exact CR-01 duplicate+nest corruption, resurfacing as soon as a Pattern hosts any nested entity, which is a headline workflow of this component. Related limitation (design ambiguity, lower severity): a membership-*changing* re-tag (grown selection) can never match equality either, so "update a Pattern's membership" silently creates an overlapping duplicate instead; and a successful re-tag with an empty Name input silently strips an existing trailing label (nickname is rebuilt from current inputs).
**Fix:** Compare against the group's *non-group* members, symmetric on both sides:

```csharp
var groupGuids = doc.Objects.OfType<GH_Group>()
    .Select(g => g.InstanceGuid.ToString())
    .ToHashSet(StringComparer.Ordinal);
var selectedCore = selectedIds.Where(id => !groupGuids.Contains(id)).ToList();
var existingPat = raw.Groups.FirstOrDefault(g =>
{
    if (!g.Nickname.StartsWith(patPrefix, StringComparison.Ordinal)) return false;
    var core = g.MemberIds.Where(id => !groupGuids.Contains(id)).ToList();
    return core.Count == selectedCore.Count && selectedCore.All(id => core.Contains(id));
});
```

This also tolerates a drag-selection that happens to include the nested child group object itself. Cover the "Pattern with nested child re-tagged by identical selection" case in the human-verify checkpoint. Optionally preserve the existing trailing label when the Name input is empty on a re-tag.

## Info

### IN-01: `ForEntity` accepts a negative or zero `patternIndex` (carried from iteration 1)

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs:126-144`
**Issue:** `procIndex` is range-checked but `patternIndex` is not; `ForEntity(Pat, 11, "", patternIndex: -3)` emits `"11_Pat_-3"`. Still round-trips (parser idx capture is `[^ ]+`, kept as a string), and the component path can no longer produce it (`TryExtractPatternIndex` requires `index > 0`), but direct API callers (Phase 35) still can.
**Fix:** Throw `ArgumentOutOfRangeException` when `patternIndex < 1`.

### IN-02: `ReservedInfixTokens` is a publicly mutable static array (carried)

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs:46-55`
**Issue:** `public static readonly string[]` protects the reference, not the contents — a caller can overwrite an element and silently disable T-34-01 validation process-wide.
**Fix:** Expose as `IReadOnlyList<string>` backed by a private array, or `ImmutableArray<string>`.

### IN-03: Selection capture does not exclude the component itself or its trigger UI (carried)

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:182`
**Issue:** `doc.Objects.Where(o => o.Attributes is { Selected: true })` includes the DG ENTITY TAG component, its Button/Toggle, and the auto-created Kind value list if they fall inside the drag-selection — polluting the group's `MemberIds` with tagging scaffolding. (Also interacts with WR-09: a selected group object inflates `selectedIds` and defeats the equality predicate.)
**Fix:** Filter out `o.InstanceGuid == InstanceGuid` and objects wired into this component's inputs before grouping.

### IN-04: Scribbles stamped at fixed pivots — second algorithm scribble lands on top of the first (carried)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:166-171, 226-234`
**Issue:** Hardcoded pivots (10,10)/(10,60); stamping `2_ALGORITHM` onto a canvas that already has `1_ALGORITHM` visually stacks them.
**Fix:** Offset by existing algorithm count or place relative to the component's own `Attributes.Pivot`.

### IN-05: Host group resolved by nickname, not identity (carried; surface slightly broadened by the WR-01 fix)

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:272-278, 396-397, 417-419`
**Issue:** Host detection carries only a nickname across the read/write boundary; `AttachToHost` matches by `NickName` with `FirstOrDefault`, and `DetachFromStaleHosts` now also *excludes* the new host by nickname — with duplicate-nicknamed Pattern groups the child can be attached to (or left attached to) the wrong instance. Root cause unchanged: `RawGroup` does not carry `InstanceGuid`.
**Fix:** Detect the host from live `GH_Group` objects inside the scheduled delegate, or add an `InstanceId` field to `RawGroup` (additive extractor change) and attach/detach by guid.

### IN-06: Emg/Emr drift guard in the grammar test is weak (carried)

**File:** `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs:29-32`
**Issue:** `Assert.Contains("Emg", source)` / `"Emr"` pass if the tokens appear anywhere in the parser file, including a comment.
**Fix:** Assert the full alternation literal: `Assert.Contains("_(?<tag>Emg|Emr)_", source);`.

### IN-07: `ValidateName` over-restricts OBJECT names relative to the actual grammar risk (carried)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:96`
**Issue:** Reserved *group-nickname* infix tokens cannot make a scribble re-parse as a different Kind, yet `ValidateName` on ObjectName rejects legitimate names like `Wall_Var_A` with a confusing "reserved grammar infix token" message. (WR-07's fix now gives `ForObjectScribble` its own newline guard, so the over-restriction is purely the reserved-token part.)
**Fix:** Scope OBJECT validation to non-empty/no-newline, or document the deliberate over-restriction in the component description.

### IN-08: ObjectMarker `_lastError` lifecycle is asymmetric — stale deferred errors can ghost-reappear (new, introduced by WR-03/WR-06 fixes)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:22, 125-137, 155-158`
**Issue:** `_lastError` is re-emitted only in CREATE mode and cleared only on CREATE-mode success. REPORT mode neither re-emits nor clears it, and the REPORT-mode class-binding delegate sets it on failure but never clears it on a later success. Consequence: a failure recorded long ago (e.g. a transient scribble or IRI-binding failure, since resolved manually) is re-surfaced as a current Error the next time the component enters CREATE mode, for one solve pass until the fresh mutation succeeds and clears it. Contrast EntityTag, which clears `_lastError` on every new rising-edge attempt.
**Fix:** Clear `_lastError` at the top of each new CREATE attempt (before scheduling), and clear it in the REPORT-mode delegate's success path; optionally re-emit it in REPORT mode for symmetry.

### IN-09: Outputs remain optimistic under the deferred-mutation model — on failure, Status/GroupName still claim success alongside the Error (new, residual of the accepted WR-03/WR-04 design)

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:307-310`; `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:214-223`
**Issue:** Both components set success outputs (`Tagged: ...` / `Created: ...`, plus EntityTag's GroupName pointing at a group that was never created) before the scheduled mutation runs. The WR-03/WR-04 fixes make the failure *visible* (Error message + `_status = "Error: ..."` on EntityTag's post-expire pass), but ObjectMarker's data outputs are not refreshed on failure (no expire by design), so downstream wiring briefly consumes a claimed-created identity that does not exist on the canvas. Inherent to the deferred model; acceptable given the visible Error, recorded for completeness.
**Fix:** If desired, have ObjectMarker's failure path set a state flag that the next solve maps to a `"Error: ..."` Status output (mirroring EntityTag's `_status` overwrite in the delegate).

---

_Reviewed: 2026-07-18T22:14:12Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (iteration 2 — fix verification)_
