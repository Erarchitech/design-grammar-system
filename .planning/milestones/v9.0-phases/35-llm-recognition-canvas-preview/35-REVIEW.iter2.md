---
phase: 35-llm-recognition-canvas-preview
reviewed: 2026-07-19T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - data-service/cg_recognition.py
  - data-service/app.py
  - data-service/gh_bridge.py
  - data-service/fixtures/frame_recognition_fewshot.json
  - data-service/tests/test_cg_recognition.py
  - data-service/tests/test_gh_bridge.py
  - DG/src/DG.Core/Models/Computgraph/RawCanvas.cs
  - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs
  - DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs
  - DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
  - DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs
  - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
  - DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
  - DG/tests/DG.Tests/CanvasAnnotationParserRecognizedSourceTests.cs
findings:
  critical: 1
  warning: 6
  info: 8
  total: 15
status: issues_found
---

# Phase 35: Code Review Report

**Reviewed:** 2026-07-19
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 35 adds the LLM recognition backend (`cg_recognition.py` + `/computgraph/recognize`), the on-canvas preview render (`HandlePreviewStructure` / `HandleClearPreview` / `HandleGetPreviewStatus` in the listener), the shared `PreviewRegistry`, and the `DG STRUCTURE CONFIRM` component. The phase contracts are largely honored: `cg_recognition.py` genuinely mirrors `dg_context.generate_validated_cypher()`'s bounded-retry loop (adapter resolved once, in-process `adapter.generate()`, feedback appended to the ORIGINAL prompt), the validator hard-rejects `unknown_member_id`/`tagged_overlap` as validator checks (not prompt-only), there is **no Neo4j write path anywhere in the flow** (verified: no driver/session usage in `cg_recognition.py` or the new handlers), all GH-dependent C# sits behind `#if GRASSHOPPER_SDK`, the preview render sits inside a single `GH_UndoRecord`, and `PreviewRegistry` uses `ConcurrentDictionary` with snapshot reads.

However, the confirm (accept) path is systematically broken by a cross-module naming-contract mismatch (CR-01): the LLM is explicitly taught to emit full convention names (`11_IntF_ParSplitAt`), and `StructureConfirmComponent` feeds that full name into `CanvasAnnotationNameFactory.ForEntity`, whose `ValidateName` hard-rejects any name containing a reserved infix token (`_IntF_`, `_Pat_`, ...). Every convention-conformant proposal therefore fails to accept. DG.Tests 350/350 green does not cover this: the GH-dependent confirm path compiles only under `GRASSHOPPER_SDK` and has no test.

## Critical Issues

### CR-01: Accept path rejects every convention-conformant proposal — `suggestedName` double-prefix contract mismatch

**File:** `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs:185` (with `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs:84-148,231-241` and `data-service/fixtures/frame_recognition_fewshot.json:23,31`)
**Issue:** The recognition prompt and the bundled few-shot fixture teach the LLM to emit `suggestedName` as a FULL convention name (`"11_IntF_ParSplitAt"`, `"11_IntF_TrussConfig"` — matching the `<NN>_IntF_<Name>` grammar the rationale cites). `PreviewEntry.SuggestedName` carries this raw wire value, and the accept path calls:

```csharp
nickname = CanvasAnnotationNameFactory.ForEntity(entry.Kind, entry.ProcedureIndex, entry.SuggestedName, patternIndex);
```

`ForEntity` treats its `name` argument as the BARE trailing name and calls `ValidateName`, which throws `ArgumentException` for any name containing a reserved infix token (`CanvasAnnotationGrammar.ReservedInfixTokens` includes `_IntF_`, `_Pat_`, `_Var_`, `_Const_`, `_Emg_`, `_Proc - `). So `ForEntity(IntF, 11, "11_IntF_ParSplitAt")` throws, the `catch (ArgumentException)` at line 187 emits a warning and `continue`s, and the proposal is never accepted — for **every** proposal whose suggestedName follows the convention, i.e. the normal LLM output. The feature's core accept flow is dead on arrival; even if `ValidateName` were lenient, the result would be a double-prefixed nickname (`11_IntF_11_IntF_ParSplitAt`).
**Fix:** Strip the convention prefix before re-deriving the name. E.g., in `ApplyToDocument`, parse `entry.SuggestedName` against the grammar to extract the bare name:

```csharp
// Derive the bare name: drop a leading "NN_<Infix>" prefix if the LLM
// emitted a full convention name (the prompt/few-shot teach exactly that).
var bareName = StripConventionPrefix(entry.SuggestedName, entry.Kind, entry.ProcedureIndex);
nickname = CanvasAnnotationNameFactory.ForEntity(entry.Kind, entry.ProcedureIndex, bareName, patternIndex);
```

where `StripConventionPrefix` removes `$"{entry.ProcedureIndex}{InfixFor(entry.Kind)}"` (Ordinal) when present, or alternatively change the recognition output contract to carry a separate bare `name` field and keep `suggestedName` display-only. Add a test in DG.Tests against the GH-free part (prefix-stripping helper can live in DG.Core so it is testable).

## Warnings

### WR-01: Repeated `preview_structure` calls orphan previous preview groups and legend — un-clearable canvas pollution

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:337-338, 393-450`; `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs:26-53`
**Issue:** `ParseProposals` synthesizes per-request ids `p0, p1, ...`. A second `preview_structure` call (without an intervening `clear_preview`) re-uses the same ids, so `PreviewRegistry.RegisterAll` overwrites `_entries["p0"]` etc. with the new group GUIDs. The first call's preview groups remain on the canvas but are no longer registered — `clear_preview` cannot remove them and `DG STRUCTURE CONFIRM` cannot see them. `_previewLegendGuid` is likewise overwritten, orphaning the previous legend scribble. Nothing in the pipeline enforces clear-before-preview.
**Fix:** At the top of `HandlePreviewStructure`'s `InvokeOnCanvasWrite` delegate, remove all currently-pending preview groups and the stashed legend (reuse `HandleClearPreview`'s body) before rendering the new proposals — or make proposal ids request-unique (`{requestGuid}:p0`) AND still auto-clear, since stale un-registry-tracked groups are unreachable by design otherwise.

### WR-02: `kind` value is never validated server-side, and `Enum.TryParse` accepts numeric strings — mid-render throw leaves partial, un-undoable preview state

**File:** `data-service/cg_recognition.py:138-151`; `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs:103-107`; `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:295-311`
**Issue:** `validate_proposed_structure` checks only that `kind` is *present*, never that it is one of the allowed values — the LLM can return any string and it passes validation. On the C# side, `ToEntityTagKind()` uses `Enum.TryParse`, which succeeds for **numeric strings** (e.g. `"7"` parses to `(EntityTagKind)7` even though undefined), so the `catch (ArgumentOutOfRangeException)` guard at line 300 is bypassed. The subsequent `CanvasAnnotationStyles.ForKind(kind, ...)` at line 311 then throws `ArgumentOutOfRangeException` **outside** the guard, aborting the whole render after earlier proposals' groups were already `doc.AddObject`ed — with the undo record never pushed and `PreviewRegistry.RegisterAll` never called. Result: orphaned preview groups with no Ctrl+Z record and no registry entry.
**Fix:** (a) In `validate_proposed_structure`, add an `invalid_kind` violation when `proposal["kind"]` is not in `{"Proc","Pat","Var","Const","Emg","IntF"}` (or the catalog's entity classes); (b) in `ToEntityTagKind`, add `Enum.IsDefined(typeof(EntityTagKind), parsed)` to the success condition so numeric strings hit the throw path and the existing guard-and-continue applies.

### WR-03: No cross-proposal duplicate-member check — one node can be claimed by multiple proposals in the same response

**File:** `data-service/cg_recognition.py:126-203`
**Issue:** The validator checks each proposal's `memberIds` against `known_ids` and `tagged_ids` individually, but never checks proposals against **each other**. A response where `proposals[0]` and `proposals[1]` both claim `n4` passes validation; the preview then draws two overlapping groups containing the same node, and accepting both in `DG STRUCTURE CONFIRM` produces two permanent convention groups claiming the same member — the exact double-ownership state the `tagged_overlap` rule exists to prevent, just one confirmation step later.
**Fix:** After the per-proposal loop, collect member ids across all proposals and emit a violation (e.g. `duplicate_member`) for any id appearing in more than one proposal:

```python
seen: dict[str, int] = {}
for i, p in enumerate(proposals):
    for m in (p.get("memberIds") or [] if isinstance(p, dict) else []):
        if m in seen:
            violations.append({"code": "duplicate_member", "message": f"Member id {m!r} appears in proposals[{seen[m]}] and proposals[{i}]. How to fix: assign each node to exactly one proposal.", "path": f"proposals[{i}].memberIds"})
        else:
            seen[m] = i
```

### WR-04: `SplitNn` crashes on single-digit NN tokens — one malformed nickname aborts the entire canvas-context extraction

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs:287-292` (call sites 107, 145, 173, 209)
**Issue:** A user-typed group nickname like `1_Proc - Foo` matches `ProcedureRegex` (`\d+` accepts one digit), then `SplitNn("1")` executes `int.Parse(nn.Substring(1))` = `int.Parse("")` and throws `FormatException`. The exception escapes `Parse()`, so `SerializeContext` fails and `get_canvas_context` returns a bridge error — the entire recognition pipeline (`/computgraph/context/pull`, `/computgraph/recognize`) is unusable until the user finds and renames the offending group, with an error message (`FormatException`) that gives no hint which nickname is at fault. This contradicts the parser's own contract ("unrecognized text is routed to the untagged set", "throws only for a null raw"). The same crash applies to `1_Pat_1`, `1_Var_X`, `1_IntF_X`.
**Fix:** In `SplitNn`, guard `nn.Length < 2` (or make the callers treat a non-splittable NN as non-conforming and route the group to `untaggedGroups` with a warning):

```csharp
private static (int Algorithm, int ProcedureOrdinal) SplitNn(string nn)
{
    if (nn.Length < 2)
    {
        throw new FormatException($"NN token '{nn}' must have at least two digits (algorithm digit + ordinal).");
    }
    ...
}
```

plus try/catch at each call site that appends a warning and routes the group to untagged instead of propagating.

### WR-05: Reject-path undo records `GH_GenericObjectAction` for a removed object — Ctrl+Z will not restore the rejected group

**File:** `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs:222-224`
**Issue:** For rejected proposals the code does `record.AddAction(new GH_GenericObjectAction(group))` and then `currentDoc.RemoveObject(group, false)`. `GH_GenericObjectAction` archives an object's *state* for modify-undo; it does not re-add an object that was removed from the document. Undoing the "DG confirm structure" record will restore accepted groups' nickname/colour but will not resurrect rejected preview groups, so the record's stated "one undo covers the whole Apply" contract is only half true. (The listener's own render correctly uses `GH_AddObjectAction`; the removal counterpart is `GH_RemoveObjectAction`.)
**Fix:** Use the removal-specific undo action for rejects:

```csharp
record.AddAction(new Grasshopper.Kernel.Undo.Actions.GH_RemoveObjectAction(group));
currentDoc.RemoveObject(group, false);
```

Verify in Rhino that a single Ctrl+Z after a mixed accept/reject Apply restores both the renamed and the removed groups.

### WR-06: `unrecognized` block is never validated — hallucinated member ids pass through despite the module's stated safety contract

**File:** `data-service/cg_recognition.py:79-203` (contract stated at lines 18-23)
**Issue:** The module docstring promises "unrecognized blocks are reported with their member ids, never invented", and RCGN-04 frames hallucinated ids as a hard-reject *validator* check, never a prompt instruction alone. But `validate_proposed_structure` only validates `proposals`; `parsed["unrecognized"]` is returned verbatim with no `unknown_member_id` check, no shape check, and no size bound. The LLM can invent ids (or dump arbitrarily large content) into `unrecognized` and it flows straight back to the caller as validated output. It is report-only today (never rendered on canvas), but downstream consumers (Phase 36 publish, UI) will reasonably trust ids in a "validated" response.
**Fix:** Extend the validator: require `unrecognized` to be a list of `{memberIds, reason}` objects, check each `memberIds` entry against `known_ids` (reusing the `unknown_member_id` code with path `unrecognized[i].memberIds`), and bound the entry count (e.g. reuse `MAX_PROPOSALS`).

## Info

### IN-01: MCP tools/list still describes preview tools as "(stub in v9.0)"

**File:** `data-service/app.py:1870, 1874`
**Issue:** `gh_preview_structure` and `gh_clear_preview` descriptions still say "(stub in v9.0)" although Phase 35 wired them to real listener handlers (and `test_gh_bridge.py:115-116` explicitly asserts the stub shape is retired).
**Fix:** Update both descriptions to describe the live behavior.

### IN-02: Unreachable `except ValueError` 422 branch in `/computgraph/recognize`

**File:** `data-service/app.py:1321-1327`
**Issue:** Nothing in `recognize_structure`'s call chain raises `ValueError` for a bad `cg_context` shape — `validate_proposed_structure` never raises, `_collect_*` helpers tolerate any shape, and Pydantic already rejects a non-dict `cg_context` with its own 422. The `RECOGNIZE_REQUEST_INVALID` branch is dead code; a genuinely malformed-but-dict context silently yields a prompt with "(none)" sections instead.
**Fix:** Either delete the branch or make it live: have `recognize_structure` raise `ValueError` when `cg_context` lacks a `nodes` list (which would otherwise guarantee every proposal fails `unknown_member_id`).

### IN-03: `procedure_index` scoping silently widens to the full canvas when the index matches no tagged procedure

**File:** `data-service/cg_recognition.py:319-321`
**Issue:** `_filtered_untagged_node_ids` returns ALL untagged node ids when `_procedure_member_ids` comes back empty (nonexistent index, or a procedure with no tagged members). A caller asking to scope recognition to procedure 99 gets an unscoped full-canvas prompt with no indication the scope was ignored — surprising both for prompt-size expectations and for result interpretation.
**Fix:** Return `[]` (or surface a warning field in the response) when the requested `procedure_index` resolves to no tagged members, so the caller sees the scope failed instead of silently paying for a full-canvas prompt.

### IN-04: `procedureIndex` is in the instructed output shape but not in the validator's required fields

**File:** `data-service/cg_recognition.py:138, 439` vs `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:417-421`
**Issue:** The output instruction tells the LLM to emit `procedureIndex` on every proposal, but the validator's required-field list omits it. A proposal without it passes validation; C# then defaults it to `0`, and the accept path later fails in `ForEntity` (`procIndex < 10` throws) with a per-proposal warning — the failure surfaces two hops away from its cause.
**Fix:** Add `procedureIndex` to the required-field tuple (and optionally validate it is an int >= 10) so the bounded-retry loop corrects the LLM instead of the GH user hitting a dead accept.

### IN-05: Legend scribble is never removed or updated by `DG STRUCTURE CONFIRM`

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:328-338, 46`; `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs:148-244`
**Issue:** `_previewLegendGuid` is private to the listener, so after the user accepts/rejects every pending proposal via `DG STRUCTURE CONFIRM`, the canvas keeps showing "[?] N proposal(s) pending -- run DG STRUCTURE CONFIRM" with a stale count, until an explicit `clear_preview` bridge call happens to run.
**Fix:** Move the legend GUID into `PreviewRegistry` (it is already the shared-state holder) so the confirm component can remove or re-text the legend when the pending count changes/hits zero.

### IN-06: Duplicate Proc-nickname groups silently drop their members from both the entity and the untagged set

**File:** `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs:111-123`
**Issue:** When two groups share a procedure nickname (`11_Proc - A` twice), only the first creates the `CgProcedure`, but `claimedMemberIds.UnionWith(group.MemberIds)` runs for both — the second group's members are claimed (so excluded from `Untagged.NodeIds`) yet attached to no entity. They vanish from the context entirely, contradicting the "never silently dropped" discipline.
**Fix:** Either merge the duplicate group's members into the existing procedure's `MemberIds`, or leave them unclaimed and append a warning naming the duplicate nickname.

### IN-07: Undo of an accept leaves the `dg.recognized.<guid>` ValueTable marker set

**File:** `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs:205`
**Issue:** `ValueTable.SetValue` is not part of the `GH_UndoRecord`, so Ctrl+Z after an accept restores the preview nickname/colour but the marker stays `true`. If the user later manually renames that group into a convention name, the parser will report `source: "recognized"` for an entity that was never confirmed.
**Fix:** Add a custom undo action that clears the marker, or document the asymmetry and clear stale markers when a group's nickname no longer parses as a convention name.

### IN-08: An all-malformed/empty proposals request still creates a legend scribble and pushes an undo record

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:328-340`
**Issue:** When `created.Count == 0` (every proposal skipped or `proposals` empty), the handler still adds a "[?] 0 proposal(s) pending" scribble, pushes an undo record, and overwrites `_previewLegendGuid` — canvas noise for a no-op request.
**Fix:** Short-circuit before the legend when `created.Count == 0` and return `{ previewed = 0 }`.

---

**Contract verification (phase requirements):**
- No Neo4j writes in the recognition flow: PASS — `cg_recognition.py` imports no Neo4j driver; `/computgraph/recognize` delegates only to `recognize_structure`; preview handlers touch only the GH document.
- Bounded-retry mirrors `dg_context`: PASS — adapter resolved once, in-process generate, feedback appended to the original prompt (tests assert non-accumulation), 3 attempts max.
- Hard-reject validator (not prompt-only) for hallucinated/tagged-overlap ids: PASS for `proposals`; GAP for `unrecognized` (WR-06).
- `#if GRASSHOPPER_SDK` guards: PASS — all five GH-dependent files carry the guard with stubs in the `#else` branch.
- Preview inside one `GH_UndoRecord`: PASS for the render (single record, single push); the confirm's reject undo is suspect (WR-05).
- `PreviewRegistry` thread safety: PASS — `ConcurrentDictionary`, snapshot `Pending`, all writers marshalled to the UI thread via `InvokeOnCanvasWrite`/`ScheduleSolution`.

_Reviewed: 2026-07-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
