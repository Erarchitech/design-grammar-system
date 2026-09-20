---
phase: 34-ontology-tagging-components
reviewed: 2026-07-18T22:28:54Z
depth: standard
iteration: 3
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
  warning: 2
  info: 9
  total: 11
status: issues_found
---

# Phase 34: Code Review Report (iteration 3 — WR-09 fix verification, FINAL)

**Reviewed:** 2026-07-18T22:28:54Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Re-review after the iteration-2 fix commit `e261eb3` (WR-09 — symmetric group-guid filtering in the Pat re-tag equality predicate). Verified the fix line-by-line against the live `CanvasContextExtractor` contract, traced every Guid string source, rebuilt `DG.sln` Release (0 warnings / 0 errors) and ran the factory suite (38/38 pass).

**WR-09 fix verdict — the equality predicate is now correct for the motivating scenario, but partially: two residual defects remain in the flow the fix enables.**

What the fix gets right (verified):

- **Symmetric filtering:** `groupGuids` is built from live `doc.Objects.OfType<GH_Group>()` at the same solve moment as `ExtractRaw`, and is applied identically to `selectedIds` (→ `selectedCore`, line 245) and to each candidate's `MemberIds` (→ `core`, line 253). No one-sided filtering path exists.
- **Guid string format consistency:** all three id sources use default `Guid.ToString()` (lowercase "D" format) — extractor `MemberIds` (`CanvasContextExtractor.cs:171`), `selectedIds` (`EntityTagComponent.cs:195`), `groupGuids` (`EntityTagComponent.cs:243`). `StringComparer.Ordinal`/`StringComparison.Ordinal` is therefore sound; no case or format mismatch is possible.
- **Primary scenario resolved:** tag M as `11_Pat_1` → nest `11_Var_X` (its group guid lands in `Pat_1.MemberIds` via `AttachToHost`) → re-select M and re-tag Pat: the predicate now matches (`core` excludes the Var group guid), `patternIndex` 1 is reused, and the CR-01 duplicate+nest no longer occurs.

What the fix leaves broken — filed below as WR-10 and WR-11:

- **WR-10:** the predicate treats child-group guids as non-identity bookkeeping, but `TagOrUpdateGroup`'s membership rebuild does not — a matched re-tag removes ALL `ObjectIDs` and re-adds only `selected`, silently destroying the parent→child nesting edge the match deliberately ignored. WR-09's own motivating scenario (label-only re-tag of a child-hosting Pattern) now corrupts nesting instead of duplicating.
- **WR-11:** the explicitly-questioned "Pattern consisting ONLY of nested groups" case DOES break the predicate — both sides filter to empty, `0 == 0` plus a vacuous `All` matches the FIRST same-NN all-group Pattern regardless of its actual members, hijacking an unrelated pattern-of-patterns.

**Hard constraints — all upheld:**

- `CanvasAnnotationParser.cs` is byte-identical: `git diff 82875c4..HEAD` over the file is empty; the file's last commits are Phase-32 (`120f58e`, `ccc7779`); working tree clean for it.
- `#if GRASSHOPPER_SDK` / `#else` stubs intact: `EntityTagComponent.cs:484-490`, `ObjectMarkerComponent.cs:236-242`, `DgIcons.cs:75-81`; `CanvasAnnotationStyles.cs` and `CanvasContextExtractor.cs` correctly gated.
- Factory round-trip guarantee holds: `e261eb3` touched only `EntityTagComponent.cs`; DG.Core factory/grammar unchanged since iteration 2; 38/38 tests pass (incl. Cyrillic, Pat with/without label, WR-07 newline rejections).

IN-01..IN-09 are carried forward as Info per scope (line references refreshed for the +16-line shift from `e261eb3`; IN-03's WR-09 cross-reference updated). No security regressions: T-34-01 reserved-token validation is unchanged and on every component-reachable name path.

## Warnings

### WR-10: Pat re-tag match/rebuild asymmetry — a matched re-tag silently detaches the Pattern's nested child groups

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:246-255` (match) vs `367-375` (rebuild)
**Issue:** The WR-09 fix makes the equality predicate deliberately ignore child-group guids in `MemberIds` ("bookkeeping added by `AttachToHost`, not user-selected membership"). But the update branch it now routes into does the opposite: `foreach (var id in existingGroup.ObjectIDs.ToList()) existingGroup.RemoveObject(id);` followed by re-adding only `selected`. In the exact scenario WR-09 was filed for — (1) tag M as `11_Pat_1`; (2) tag a subset as `11_Var_X`, whose group guid `AttachToHost` adds to `Pat_1.ObjectIDs`; (3) re-select M (core only, child group object not selected) and re-tag to add a label — the match now succeeds (good), but the rebuild strips the Var group's guid and never restores it. Consequences: the child group is structurally un-nested (loses GH visual containment; for a nested child *Pattern*, `CanvasContextExtractor.NestedGroupIds` no longer reports it, so the parsed Computgraph hierarchy changes) while the child keeps its purple `NestedPattern` colour — precisely the colour/structure disagreement the WR-01 fix (`DetachFromStaleHosts`) was built to prevent, now re-introduced from the parent side. Secondary hazard on the same lines: when the drag-selection fully covers the parent Pattern, `selected` includes the re-tag target group object itself, and the rebuild executes `existingGroup.AddObject(existingGroup.InstanceGuid)` — a self-referencing group (the extractor's nesting scan skips self, but the guid still pollutes `MemberIds` and GH's handling of self-membership is undefined).
**Fix:** Preserve the bookkeeping guids the match ignored, and never add the group to itself:

```csharp
// Child-group guids the equality predicate deliberately ignored (WR-09) must
// survive the rebuild, or a matched re-tag silently destroys nesting (WR-10).
var liveGroupGuids = currentDoc.Objects.OfType<GH_Group>()
    .Select(g => g.InstanceGuid).ToHashSet();
var preservedChildIds = existingGroup.ObjectIDs
    .Where(id => liveGroupGuids.Contains(id) && id != existingGroup.InstanceGuid)
    .ToList();

foreach (var id in existingGroup.ObjectIDs.ToList())
{
    existingGroup.RemoveObject(id);
}

foreach (var obj in selected)
{
    if (obj.InstanceGuid != existingGroup.InstanceGuid)
    {
        existingGroup.AddObject(obj.InstanceGuid);
    }
}

foreach (var childId in preservedChildIds.Where(id => !existingGroup.ObjectIDs.Contains(id)))
{
    existingGroup.AddObject(childId);
}
```

Cover "re-tag a child-hosting Pattern by core-only selection, then verify the child is still nested" in the human-verify checkpoint.

### WR-11: Empty-core vacuous match — a group-only selection hijacks the first same-NN pattern-of-patterns instead of creating a new one

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:246-255`
**Issue:** When the current selection contains only group objects (legal: `GH_Group` is selectable and passes the `selected.Count == 0` guard; selecting existing tag groups and pressing Tag is the natural way to build a pattern-of-patterns, and the create branch then produces a Pattern whose `MemberIds` are ALL group guids), `selectedCore` filters to empty. Any existing `NN_Pat_*` group whose members are likewise all groups also filters to an empty `core`, so the predicate degenerates to `0 == 0 && [].All(...)` — vacuously true for the FIRST such candidate in `raw.Groups` iteration order, regardless of which groups it actually contains. Sequence: (1) select child groups {A, B}, tag Pat → creates `11_Pat_1` with members {A, B} (all groups); (2) select DIFFERENT child groups {C, D}, tag Pat intending a new parent → predicate matches `11_Pat_1` (both cores empty), `patternIndex` 1 is reused, `retagTargetNickname` set, and `TagOrUpdateGroup` rewires `11_Pat_1` to {C, D} — the {A, B} parent is hijacked and its children orphaned instead of a `11_Pat_2` being created. Even with an identical selection, two all-group Patterns under the same NN make the `FirstOrDefault` pick order-dependent (dictionary iteration order of `groupsByGuid`), so the wrong one can be re-tagged. The pre-fix predicate handled this case correctly (it compared the full guid sets); the fix regressed it.
**Fix:** Fall back to full-set comparison when the filtered cores are empty, so group-only selections keep exact-identity matching:

```csharp
var existingPat = raw.Groups.FirstOrDefault(g =>
{
    if (!g.Nickname.StartsWith(patPrefix, StringComparison.Ordinal))
    {
        return false;
    }

    var core = g.MemberIds.Where(id => !groupGuids.Contains(id)).ToList();
    if (core.Count == 0 && selectedCore.Count == 0)
    {
        // Group-only pattern vs group-only selection: cores are vacuous --
        // compare the full member sets exactly (WR-11).
        return g.MemberIds.Count == selectedIds.Count
            && selectedIds.All(id => g.MemberIds.Contains(id));
    }

    return core.Count == selectedCore.Count && selectedCore.All(id => core.Contains(id));
});
```

## Info

### IN-01: `ForEntity` accepts a negative or zero `patternIndex` (carried from iteration 1)

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs:126-144`
**Issue:** `procIndex` is range-checked but `patternIndex` is not; `ForEntity(Pat, 11, "", patternIndex: -3)` emits `"11_Pat_-3"`. Still round-trips (parser idx capture is `[^ ]+`, kept as a string), and the component path can no longer produce it (`TryExtractPatternIndex` requires `index > 0`), but direct API callers (Phase 35) still can.
**Fix:** Throw `ArgumentOutOfRangeException` when `patternIndex < 1`.

### IN-02: `ReservedInfixTokens` is a publicly mutable static array (carried)

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs:46-55`
**Issue:** `public static readonly string[]` protects the reference, not the contents — a caller can overwrite an element and silently disable T-34-01 validation process-wide.
**Fix:** Expose as `IReadOnlyList<string>` backed by a private array, or `ImmutableArray<string>`.

### IN-03: Selection capture does not exclude the component itself or its trigger UI (carried; interaction updated)

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:182`
**Issue:** `doc.Objects.Where(o => o.Attributes is { Selected: true })` includes the DG ENTITY TAG component, its Button/Toggle, and the auto-created Kind value list if they fall inside the drag-selection — polluting the group's `MemberIds` with tagging scaffolding. (Interaction updated for the WR-09 fix: these are non-group objects, so they now land in `selectedCore` and still defeat the re-tag equality predicate; the fix's group filter does not help here.)
**Fix:** Filter out `o.InstanceGuid == InstanceGuid` and objects wired into this component's inputs before grouping.

### IN-04: Scribbles stamped at fixed pivots — second algorithm scribble lands on top of the first (carried)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:166-171, 226-234`
**Issue:** Hardcoded pivots (10,10)/(10,60); stamping `2_ALGORITHM` onto a canvas that already has `1_ALGORITHM` visually stacks them.
**Fix:** Offset by existing algorithm count or place relative to the component's own `Attributes.Pivot`.

### IN-05: Host group resolved by nickname, not identity (carried)

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:288-294, 412-413, 433-437`
**Issue:** Host detection carries only a nickname across the read/write boundary; `AttachToHost` matches by `NickName` with `FirstOrDefault`, and `DetachFromStaleHosts` excludes the new host by nickname — with duplicate-nicknamed Pattern groups the child can be attached to (or left attached to) the wrong instance. Root cause unchanged: `RawGroup` does not carry `InstanceGuid`.
**Fix:** Detect the host from live `GH_Group` objects inside the scheduled delegate, or add an `InstanceId` field to `RawGroup` (additive extractor change) and attach/detach by guid.

### IN-06: Emg/Emr drift guard in the grammar test is weak (carried)

**File:** `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs:29-32`
**Issue:** `Assert.Contains("Emg", source)` / `"Emr"` pass if the tokens appear anywhere in the parser file, including a comment.
**Fix:** Assert the full alternation literal: `Assert.Contains("_(?<tag>Emg|Emr)_", source);`.

### IN-07: `ValidateName` over-restricts OBJECT names relative to the actual grammar risk (carried)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:96`
**Issue:** Reserved *group-nickname* infix tokens cannot make a scribble re-parse as a different Kind, yet `ValidateName` on ObjectName rejects legitimate names like `Wall_Var_A` with a confusing "reserved grammar infix token" message. (WR-07's fix gives `ForObjectScribble` its own newline guard, so the over-restriction is purely the reserved-token part.)
**Fix:** Scope OBJECT validation to non-empty/no-newline, or document the deliberate over-restriction in the component description.

### IN-08: ObjectMarker `_lastError` lifecycle is asymmetric — stale deferred errors can ghost-reappear (carried from iteration 2)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:22, 125-137, 155-158`
**Issue:** `_lastError` is re-emitted only in CREATE mode and cleared only on CREATE-mode success. REPORT mode neither re-emits nor clears it, and the REPORT-mode class-binding delegate sets it on failure but never clears it on a later success. A failure recorded long ago is re-surfaced as a current Error the next time the component enters CREATE mode, for one solve pass. Contrast EntityTag, which clears `_lastError` on every new rising-edge attempt.
**Fix:** Clear `_lastError` at the top of each new CREATE attempt (before scheduling), and clear it in the REPORT-mode delegate's success path; optionally re-emit it in REPORT mode for symmetry.

### IN-09: Outputs remain optimistic under the deferred-mutation model — on failure, Status/GroupName still claim success alongside the Error (carried from iteration 2)

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:310-326`; `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:214-223`
**Issue:** Both components set success outputs (`Tagged: ...` / `Created: ...`, plus EntityTag's GroupName pointing at a group that may never be created) before the scheduled mutation runs. The WR-03/WR-04 fixes make the failure *visible*, but ObjectMarker's data outputs are not refreshed on failure (no expire by design), so downstream wiring briefly consumes a claimed-created identity that does not exist on the canvas. Inherent to the deferred model; acceptable given the visible Error, recorded for completeness.
**Fix:** If desired, have ObjectMarker's failure path set a state flag that the next solve maps to an `"Error: ..."` Status output (mirroring EntityTag's `_status` overwrite in the delegate).

---

_Reviewed: 2026-07-18T22:28:54Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (iteration 3 — WR-09 fix verification, final)_
