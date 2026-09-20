---
phase: 34-ontology-tagging-components
reviewed: 2026-07-18T21:50:36Z
depth: standard
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
  critical: 1
  warning: 8
  info: 7
  total: 16
status: issues_found
---

# Phase 34: Code Review Report

**Reviewed:** 2026-07-18T21:50:36Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the Phase 34 canvas annotation write path: grammar constants, the pure name factory + tests, the shared color palette, and the two GH components (DG OBJECT MARKER, DG ENTITY TAG). Cross-checked against the read-only context files `CanvasAnnotationParser.cs` (regex grammar, `SplitNn`) and `CanvasContextExtractor.cs` (null-doc guard, `MemberIds` Guid formatting), plus `GhCastingHelpers.Unwrap` and the embedded icon resources (`EntityTag24.png` / `ObjectMarker24.png` exist and match the `Properties\*.png` EmbeddedResource glob).

The pure core (grammar constants, factory, round-trip tests) is solid: every `ForEntity` shape re-parses through the verified parser regexes, `NextFreePatternIndex` prefix matching is collision-safe against longer NN tokens (ordinal `StartsWith` on `"11_Pat_"` cannot match `"111_Pat_..."`), and Guid string comparison between selection (`InstanceGuid.ToString()`) and extractor output (`ObjectIDs.Select(id => id.ToString())`) is format-consistent. The hard round-trip constraint holds for all component-reachable paths.

The defects concentrate in the GH component layer: the Pattern kind can never satisfy the component's own documented "re-tag updates, never duplicates" contract (Critical), undo records do not cover host-group mutation, deferred-mutation failures are invisible to the user (and can loop in OBJECT MARKER), and OBJECT MARKER's partial-annotation reporting misstates canvas state. One factory-level contract hole exists (`ForObjectScribble` accepts newlines, breaking its own round-trip guarantee).

Security scope (ASVS L1, T-34-01): reserved-infix-token rejection is correctly implemented in `ValidateName`, called on every component-reachable name path, and surfaced as GH runtime warnings via the `ArgumentException` catch in both components. No hardcoded secrets, no injection surfaces, no unsafe deserialization in the reviewed files.

## Critical Issues

### CR-01: Pattern kind can never re-tag — every Tag press creates a duplicate Pattern group and spuriously nests it inside the previous one

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:207-211` (with 232-239 and 275-301)
**Issue:** The component's documented contract (lines 16-18: "updates membership on re-tag (same nickname) instead of creating a duplicate group") is unreachable for `EntityTagKind.Pat`. For Pat, `patternIndex` is always `NextFreePatternIndex(...)` — i.e. always max+1 — so the emitted nickname (`11_Pat_2`, `11_Pat_3`, ...) is never equal to an existing group's nickname, and `TagOrUpdateGroup`'s update branch can never fire. Concretely: the user presses Tag twice on the same selection (Button press/release/press = two rising edges, a completely ordinary action):

1. First press creates `11_Pat_1` wrapping the selection.
2. Second press computes index 2, and the nesting detector (lines 232-239: selection ⊆ `11_Pat_1`'s members — `All` treats an equal set as a subset) marks the new group nested, so `11_Pat_2` is created purple and attached inside `11_Pat_1`.

The canvas now silently carries two Patterns for one intent, one wrongly nested in the other; `CanvasAnnotationParser` will faithfully emit both as distinct `CgPattern`s with a bogus `HostPatternId` chain. There is also no path to fix or update a mis-tagged Pattern's membership through the component — every attempt compounds the duplication. This corrupts the authored annotation layer that the whole Phase 32-37 pipeline treats as ground truth.
**Fix:** Before auto-incrementing, check for an existing Pattern group under the same NN whose member set equals (or intersects) the current selection and reuse its index — routing into the update branch instead of creating a new group. Sketch:

```csharp
// Re-tag detection for Pat: reuse the index of an existing NN_Pat_* group whose
// member set matches the current selection (optionally also matching the label).
var prefix = procIndex.ToString(CultureInfo.InvariantCulture) + CanvasAnnotationGrammar.PatternInfix;
var existingPat = raw.Groups.FirstOrDefault(g =>
    g.Nickname.StartsWith(prefix, StringComparison.Ordinal)
    && g.MemberIds.Count == selectedIds.Count
    && selectedIds.All(id => g.MemberIds.Contains(id)));
patternIndex = existingPat is not null
    ? ExtractIdx(existingPat.Nickname, prefix)          // reuse -> update branch fires
    : CanvasAnnotationNameFactory.NextFreePatternIndex(raw.Groups.Select(g => g.Nickname), procIndex);
```

Additionally, exclude an exact-match group from the nesting-host detection so a re-tagged Pattern is never treated as its own host.

## Warnings

### WR-01: Undo records do not cover the host-group mutation, and re-tag never detaches from a stale host

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:287-299, 303-318, 321-335`
**Issue:** Both undo paths record only the tag group itself (`GH_GenericObjectAction(existingGroup)` / `GH_AddObjectAction(group)`), but `AttachToHost` then mutates a *second* document object — the host Pattern group's `ObjectIDs` — with no corresponding undo action. Consequences: (a) undoing a "DG Tag Entity" record removes the new group but leaves its now-dangling `InstanceGuid` inside the host group's `ObjectIDs` (the extractor will report a phantom nested-group id); (b) undoing an update restores the tag group's old membership but not the host's. Separately, the update branch only ever *adds* to a host: if a group was previously nested and the new selection no longer sits inside that Pattern (`hostGroupNickname == null` or a different host), the old host still contains the group's guid — the colour flips to non-nested orange while the structural nesting silently persists, so colour and structure disagree.
**Fix:** In both branches, when `hostGroupNickname` participates, add `updateRecord.AddAction(new GH_GenericObjectAction(hostGroup))` (resolve the host *before* mutating it) so the host's state is captured in the same undo record. In the update branch, also remove the group's guid from any *other* Pattern group whose `ObjectIDs` contains it before attaching to the newly detected host (recording those hosts too).

### WR-02: `GH_ValueList` auto-wiring decision is made in `AddedToDocument` but executed later — duplicate value lists on file open

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:74-98`
**Issue:** `AddedToDocument` also fires when a saved .gh file containing the component is opened. The `Params.Input[0].Sources.Count > 0` guard runs synchronously at that moment, but during document load the wire topology may not yet be restored when the object is added, so the guard can read `Sources.Count == 0` for a component that *is* wired in the file — and the scheduled delegate then unconditionally creates and wires a second value list. Each open would add another orphan value list wired into Kind (an item-access input with multiple sources → merged data, broken Kind resolution). The decision (guard) and the mutation (delegate) are separated across the exact window in which wire state changes.
**Fix:** Re-check inside the scheduled delegate, where wire restoration is guaranteed complete:

```csharp
document.ScheduleSolution(1, d =>
{
    try
    {
        if (Params.Input.Count == 0 || Params.Input[0].Sources.Count > 0)
        {
            return; // wired by now (e.g. file load restored the connection)
        }
        // ... create + wire value list as before
    }
    catch { /* UX convenience, never fatal */ }
});
```

### WR-03: Deferred-mutation failures are invisible — optimistic status plus error messages wiped by the forced re-solve

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:245-264`; `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:128-160`
**Issue:** Both components set success outputs *before* the scheduled mutation runs (`_status = "Tagged: ..."` at line 263; `da.SetData(2, $"Created: ...")` at line 160). If the mutation throws, the catch calls `AddRuntimeMessage(Error, ...)` — but the very next statement is `ExpireSolution(false)`, which forces the component to re-solve in the same scheduled solution; re-solving clears runtime messages, so the error the user was supposed to see is erased and the component continues to display "Tagged:/Created:" while nothing was written to the canvas. Failure is fully silent.
**Fix:** Track failure in component state instead of (only) a transient message: set e.g. `_status = $"Error: {ex.Message}"` in the catch (EntityTag already has the `_status` field; ObjectMarker needs an equivalent) and re-emit it as a runtime Error from `SolveInstance` on the post-expire pass. Alternatively, skip `ExpireSolution(false)` on the failure path so the message added in the delegate survives.

### WR-04: OBJECT MARKER can enter an unbounded schedule→fail→expire→schedule loop on persistent mutation failure

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:128-156`
**Issue:** OBJECT MARKER has no rising-edge trigger — CREATE mode schedules a mutation on *every* solve while the canvas lacks the scribbles. The scheduled delegate ends with `ExpireSolution(false)` unconditionally, which re-runs `SolveInstance` in the just-scheduled solution. On success this terminates (REPORT mode is reached), but if `AddScribble`/`ValueTable.SetValue` throws persistently, each re-solve re-enters CREATE mode, schedules another mutation, fails again, and expires again — an endless solve/schedule cycle with no backoff and (per WR-03) no visible error.
**Fix:** Add a retry latch: set a `_createFailed` flag in the catch and short-circuit `SolveInstance` to a warning/report path while it is set (cleared when inputs change), or only call `ExpireSolution(false)` when the mutation succeeded.

### WR-05: OBJECT MARKER partial-annotation path reports canvas state it did not create and contradicts the actual canvas

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:111-125, 158-160`
**Issue:** REPORT mode requires *both* `context.Object` and the matching algorithm. In the mixed case — e.g. canvas already has `OBJECT - FRAME` but the requested `2_ALGORITHM` is missing — the component correctly skips the object scribble (`needsObjectScribble == false`) but then outputs the *input* `ObjectName` and the status `"Created: OBJECT - BEAM / 2_ALGORITHM"`: it claims to have created an OBJECT scribble it deliberately did not create, and the ObjectName output (`BEAM`) contradicts the identity actually on the canvas (`FRAME`). Downstream consumers wiring the ObjectName output now disagree with what `CanvasAnnotationParser` will extract. The inverse case (algorithm exists, object missing) misreports symmetrically.
**Fix:** Report per-artifact truth: output `context.Object?.Name ?? objectName` for ObjectName, and build the status from `needsObjectScribble`/`needsAlgorithmScribble`, e.g. `"Kept existing: OBJECT - FRAME; Created: 2_ALGORITHM"`. Optionally emit a Warning when the input ObjectName conflicts with an existing canvas OBJECT identity instead of silently ignoring the input.

### WR-06: Class IRI binding silently dropped whenever the canvas is already annotated (REPORT mode)

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:111-120, 126, 142-145`
**Issue:** `dg.objectClassIri` is written to `GH_Document.ValueTable` only inside the CREATE-mode scheduled delegate. In REPORT mode (object + algorithm both present) the method returns at line 119 before the Class input is ever considered — so wiring an OntologyClass into an already-annotated canvas does nothing, with no warning. The stated feature ("Optionally binds a dg:Class IRI to the document") thus only works on the very first stamping; changing or adding the Class later is silently ignored. A stale IRI also persists forever once written (never cleared/updated).
**Fix:** Hoist the ValueTable write out of the CREATE-only branch: in REPORT mode, if `classIri` is non-empty and differs from the stored value, schedule a small solution that updates `dg.objectClassIri` (ValueTable mutation still belongs inside `ScheduleSolution`). Include the current binding in the REPORT status string so the user can see it.

### WR-07: `ForObjectScribble` violates the factory's round-trip guarantee for names containing newlines

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs:32-44`
**Issue:** The class contract (lines 22-27) says "Every name this factory builds is guaranteed to parse back through CanvasAnnotationParser.Parse". `ForObjectScribble` only rejects null/whitespace — it does not reject embedded newlines (unlike `ValidateName`, which `ForEntity` routes every name through). `ForObjectScribble("FOO\nBAR")` returns `"OBJECT - FOO\nBAR"`, which the parser's `^OBJECT - (?<name>.+)$` (no `Singleline`/`Multiline`) cannot match — the scribble silently falls into the untagged set, i.e. a factory-built name that does NOT round-trip. `ObjectMarkerComponent` happens to compensate by calling `ValidateName(objectName.Trim())` first (line 94), but the factory's own guarantee must not depend on caller discipline — any future caller (Phase 35 LLM-driven tagging is the obvious one) hits the hole.
**Fix:** Reject newlines inside `ForObjectScribble` itself:

```csharp
if (name.Contains('\n') || name.Contains('\r'))
{
    throw new ArgumentException(
        "What: Object name contains a newline. " +
        "Where: CanvasAnnotationNameFactory.ForObjectScribble. " +
        "How to fix: remove line breaks from the Object name.",
        nameof(name));
}
```

Add a factory test asserting `ForObjectScribble` throws on `"FOO\nBAR"`.

### WR-08: Update path mutates `GH_Group.ObjectIDs` directly via `Clear()` — bypasses the group's own membership API

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:290-294`
**Issue:** The re-tag branch clears membership with `existingGroup.ObjectIDs.Clear()` and then repopulates via `AddObject`. The GH SDK exposes `AddObject`/`RemoveObject` as the membership mutation API; `ObjectIDs` is a property whose returned-collection semantics (live internal list vs. defensive copy) are not documented, and even when live, direct `Clear()` skips whatever bookkeeping/attribute-cache expiry the removal API performs. If `ObjectIDs` returns a copy in the deployed Rhino 8 SDK version, `Clear()` is a silent no-op and a re-tag with a *smaller* selection leaves removed members in the group (membership only ever grows). This is the phase's only unverified SDK-surface assumption not covered by the checkpoint list (the verified constraints cover `ScheduleSolution`, undo, scribbles, ValueTable — not group-membership mutation).
**Fix:** Use the symmetric API and verify during the human-verify checkpoint that shrink-re-tag actually removes members:

```csharp
foreach (var id in existingGroup.ObjectIDs.ToList())
{
    existingGroup.RemoveObject(id);
}
foreach (var obj in selected)
{
    existingGroup.AddObject(obj.InstanceGuid);
}
existingGroup.ExpireCaches();
```

## Info

### IN-01: `ForEntity` accepts a negative or zero `patternIndex`

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs:114-132`
**Issue:** `procIndex` is range-checked but `patternIndex` is not; `ForEntity(Pat, 11, "", patternIndex: -3)` emits `"11_Pat_-3"`. It still round-trips (the parser's idx capture is `[^ ]+`, kept as a string), but it is outside the convention's integer-index model and `NextFreePatternIndex` would ignore it, so the same index can never be auto-avoided.
**Fix:** Throw `ArgumentOutOfRangeException` when `patternIndex < 1`.

### IN-02: `ReservedInfixTokens` is a publicly mutable static array

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs:46-55`
**Issue:** `public static readonly string[]` protects the reference, not the contents — any caller can do `CanvasAnnotationGrammar.ReservedInfixTokens[0] = "x"` and silently disable the T-34-01 validation for the whole process.
**Fix:** Expose as `IReadOnlyList<string>` backed by a private array, or `ImmutableArray<string>`.

### IN-03: Selection capture does not exclude the component itself or its trigger UI

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:161`
**Issue:** `doc.Objects.Where(o => o.Attributes is { Selected: true })` includes the DG ENTITY TAG component, its Button/Toggle, and the auto-created Kind value list if they happen to be inside the user's drag-selection — they then become members of the entity group and pollute the Computgraph `MemberIds` with tagging scaffolding.
**Fix:** Filter out `o.InstanceGuid == InstanceGuid` and (optionally) the objects wired into this component's inputs before grouping.

### IN-04: Scribbles are stamped at fixed pivots — second algorithm scribble lands exactly on top of the first

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:134-140, 163-171`
**Issue:** Both scribbles use hardcoded pivots (10,10)/(10,60). Stamping `2_ALGORITHM` on a canvas that already has `1_ALGORITHM` places the new scribble at the identical (10,60) pivot, visually stacking them; both also ignore existing canvas content at the origin.
**Fix:** Offset by existing algorithm count (e.g. `y = 60 + 50 * context.Algorithms.Count`) or place relative to the component's own `Attributes.Pivot`.

### IN-05: Host group resolved by nickname, not identity

**File:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs:232-237, 328-334`
**Issue:** Nesting host detection carries only the host's nickname across the read/write boundary; `AttachToHost` then matches by `NickName` with `FirstOrDefault`. GH group nicknames are not unique — with duplicate-nicknamed Pattern groups the child can be attached to the wrong instance. Root cause: `RawGroup` does not carry the group's `InstanceGuid`, forcing nickname round-tripping.
**Fix:** Detect the host directly from `currentDoc.Objects.OfType<GH_Group>()` inside the scheduled delegate (member-set check against live groups), or add an `InstanceId` field to `RawGroup` (additive extractor change) and attach by guid.

### IN-06: Emg/Emr drift guard in the grammar test is weak

**File:** `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs:29-32`
**Issue:** `Assert.Contains("Emg", source)` / `Assert.Contains("Emr", source)` pass if the tokens appear anywhere in the parser file — including a comment — so renaming the alternation while keeping a stale comment would not be caught. (Acknowledged in the in-test comment; the constant-equality asserts partially compensate.)
**Fix:** Assert the full alternation literal instead: `Assert.Contains("_(?<tag>Emg|Emr)_", source);`.

### IN-07: `ValidateName` over-restricts OBJECT names relative to the actual grammar risk

**File:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs:94`
**Issue:** OBJECT identities are scribbles; the reserved *group-nickname* infix tokens (`_Var_`, `_Proc - `, ...) cannot cause a scribble to re-parse as a different Kind (scribbles are only matched against the OBJECT/ALGORITHM regexes). Running `ValidateName` on ObjectName therefore rejects legitimate names like `Wall_Var_A` for a collision that cannot occur. Conservative and safe, but the rejection message ("reserved grammar infix token") will confuse users, and the behavior is undocumented.
**Fix:** Either scope OBJECT validation to what matters for scribbles (non-empty, no newlines — which WR-07's fix gives you inside `ForObjectScribble`), or document the deliberate over-restriction in the component description.

---

_Reviewed: 2026-07-18T21:50:36Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
