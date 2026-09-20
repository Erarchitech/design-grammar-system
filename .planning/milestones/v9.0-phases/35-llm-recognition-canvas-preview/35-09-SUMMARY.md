---
phase: 35-llm-recognition-canvas-preview
plan: 09
subsystem: ui
tags: [grasshopper, undo-stack, gh-undorecord, publishability-gate, shacl, uat-f4, uat-f5]

requires:
  - phase: 35-llm-recognition-canvas-preview
    provides: CanvasListenerComponent preview/clear_preview handlers, StructureConfirmComponent Accept/Reject, CanvasAnnotationParser.InferParameterDataType
provides:
  - Coherent preview undo stack — one GH_UndoRecord spans remove-previous + render-new
  - Undoable explicit clear_preview (was a latent identical crash)
  - CanvasAnnotationParser.TryInferParameterDataType — public seam delegating to the private inference
  - Per-entity accept-time publishability gate in DG STRUCTURE CONFIRM (G12)
affects: [36-computgraph-persistence-display, 35-verification]

tech-stack:
  added: []
  patterns:
    - "Record-then-remove ordering: add GH_RemoveObjectAction to the owning record BEFORE doc.RemoveObject"
    - "One coherent undo record per user-visible action, rather than trying to discard a stale record (GH exposes no supported way to mutate the undo stack)"
    - "Delegation seam over re-implementation: the gate asks the parser the same question the context pull will ask"

key-files:
  created: []
  modified:
    - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
    - DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs
    - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs
    - DG/tests/DG.Tests/CanvasAnnotationParserTests.cs
    - .planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-UAT.md

key-decisions:
  - "F4 fixed with 'one coherent record' (the finding's option 2) rather than discarding the stale record — Grasshopper exposes no supported way to mutate the undo stack"
  - "TryInferParameterDataType delegates verbatim to the existing private InferParameterDataType — delegation, not a second implementation. A copy of the inference rules in the Grasshopper layer would drift, and a divergence between what the gate accepts and what the parser types is precisely how F5 recurs"
  - "The gate is per-entity, deliberately not all-or-nothing: a blocked proposal stays PENDING (neither accepted nor rejected) so the architect can fix the canvas and re-Apply, and the rest of the Apply lands"
  - "Gated kinds are Var/Const/Emg only — Proc and Pat carry no dataType and IntF carries ifaceType, so gating them would block on a property they lack"
  - "Empty member groups stay quiet — tag-then-populate is a normal workflow and the publish component's pre-flight covers those"
  - "HandleClearPreview carried the identical latent crash and now pushes its own 'DG clear preview' record; behavior change: the explicit clear is undoable where it was not"

patterns-established:
  - "What+Where+How-to-fix warning format for canvas-side blocks, naming the offending component"

requirements-completed: [RCGN-02, RCGN-03]

coverage:
  - id: D1
    description: "F4 fixed — re-preview no longer orphans the prior undo record; one GH_UndoRecord spans remove-previous + render-new, so Ctrl+Z #2 finds its objects present"
    requirement: RCGN-02
    verification:
      - kind: manual_procedural
        ref: "35-UAT.md test 6 — live on UrbanBlock_V7, provenance-checked binary (DG.gha SHA256 65927F65...)"
        status: pass
    human_judgment: false
  - id: D2
    description: "clear_preview path made undoable — it carried the identical latent crash (preview -> clear_preview -> Ctrl+Z threw the same error)"
    requirement: RCGN-02
    verification:
      - kind: manual_procedural
        ref: "35-UAT.md test 6 — GammaOne/GammaTwo, cleared: 2, one Ctrl+Z restored both, a second removed them, no dialog"
        status: pass
    human_judgment: false
  - id: D3
    description: "CanvasAnnotationParser.TryInferParameterDataType public seam delegating to the private inference"
    requirement: RCGN-03
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasAnnotationParserTests.cs — 4 seam tests: slider, bare Number, untypeable member, empty-group quiet path"
        status: pass
    human_judgment: false
  - id: D4
    description: "G12 per-entity accept-time publishability gate — an untypeable Var/Const/Emg proposal is blocked and left PENDING with a named warning while the rest of the Apply lands; Status gains a 'blocked N' segment"
    requirement: RCGN-03
    verification:
      - kind: manual_procedural
        ref: "35-UAT.md test 7 — recorded PENDING: code complete + unit-tested, but observing per-entity blocking needs a live Rhino session"
        status: unknown
    human_judgment: true
    rationale: "Per-entity blocking behaviour in DG STRUCTURE CONFIRM is only observable in a running Grasshopper session. Since 028ff0e types bare Number/Integer/Text/geometry params, triggering it now requires a member in neither the widget nor the primitive tier"

duration: unrecorded
completed: 2026-07-26
status: complete
---

# Phase 35-09: F4 Undo Fix + G12 Publishability Gate Summary

**F4's hard crash is closed and live-verified; the G12 accept-time gate now blocks an unpublishable proposal per-entity at the moment the architect can act on it, instead of detonating as a whole-payload 422 three phases later.**

## Performance

- **Tasks:** 4 of 4 executed (task 4's live-verify gate: F4 verified, G12 recorded PENDING)
- **Files modified:** 5 (4 source/test + UAT record)
- **Commits:** 4 across the plan's lifetime

## Accomplishments

- **Closed the only outright FAIL in `35-UAT.md`.** Running `preview_structure` twice left the first render's `GH_UndoRecord` on the stack holding `GH_AddObjectActions` for objects the WR-01 auto-clear had already removed untracked. Ctrl+Z #1 undid the second record fine; Ctrl+Z #2 undid the first and Grasshopper threw "Undo failed: Object could not be found".
- **Fixed it with one coherent record.** `RemovePendingPreviewObjects` now takes the `GH_UndoRecord` that owns the removal and adds a `GH_RemoveObjectAction` per object *before* `doc.RemoveObject` — the same record-then-remove ordering `StructureConfirmComponent.ApplyToDocument` already uses for its reject branch (WR-05, live-proven by test 5). `HandlePreviewStructure` builds its "DG structure proposal" record before the auto-clear and hands it in, so one record spans remove-previous + render-new. The legend scribble is tracked the same way.
- **Found and fixed the same latent crash on the clear path.** `HandleClearPreview` left the preview's add-record live after an explicit clear too, so `preview → clear_preview → Ctrl+Z` threw the identical error. It now pushes its own "DG clear preview" record when anything was actually removed.
- **Shipped the G12 accept-time gate.** Nothing validated `dataType` at accept time, so DG STRUCTURE CONFIRM would happily convert an untypeable proposal into a permanent group and Phase 36's SHACL-backed publish would then 422 the *entire* payload — 11 valid entities unable to land because of 1 invalid one, three phases away from the cause. The architect experiences that as "the AI made me break my publish." Now the component asks the parser the same question it will ask at context-pull time, before any mutation of an accepted group.

## Task Commits

1. **F4 — re-preview orphans the prior undo record** — `f2f518c` (fix)
2. **F4 live verification on UrbanBlock_V7** — `a82ab03` (test)
3. **G12 accept-time publishability gate** — `ae6d805` (feat)

Related, landed just ahead of this plan: `028ff0e` (fix) — F5's parser half, the bare-param `dataType` inference gap and the publish pre-flight.

## Files Created/Modified

- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` — record-then-remove in `RemovePendingPreviewObjects`; one record from `HandlePreviewStructure`; new "DG clear preview" record in `HandleClearPreview`
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` (+22) — `TryInferParameterDataType` public seam
- `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` (+45) — per-entity gate, `blocked N` status segment
- `DG/tests/DG.Tests/CanvasAnnotationParserTests.cs` (+57) — 4 seam tests
- `.planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-UAT.md` — test 6 FAIL → pass; test 7 added as PENDING

## Decisions Made

- **Delegation, not a second implementation.** `TryInferParameterDataType` delegates verbatim to the existing private method. A copy of the inference rules in the Grasshopper layer would drift, and a divergence between what the gate accepts and what the parser types is precisely how F5 recurs.
- **Per-entity, not all-or-nothing.** A null `dataType` on a non-empty member set blocks *that* proposal, names the offending component in a What+Where+How-to-fix warning, leaves it PENDING (neither accepted nor rejected, so the architect can fix the canvas and re-Apply), and lets the rest of the Apply land.
- **Gated kinds are Var/Const/Emg only.** Proc and Pat carry no `dataType` and IntF carries `ifaceType`, so gating them would block on a property they lack.
- **Empty member groups stay quiet** — tag-then-populate is a normal workflow, and the publish component's pre-flight covers those.

## Deviations from Plan

Tasks 1 and 4 of the plan were already satisfied before the final commit: F4 was fixed in `f2f518c` and verified live on UrbanBlock_V7 in `a82ab03` (UAT test 6 now passes). They were not re-touched in `ae6d805`.

## Issues Encountered

**Two live-testing notes recorded for future re-runs** (from `a82ab03`):

- F4 only reproduces when `preview_structure` runs twice in the **same** listener session. A Rhino restart empties the in-process `PreviewRegistry`, so the first preview after a restart auto-clears nothing and the double-undo walks an unrelated record — a **false pass**. The first attempt that session hit exactly that.
- A preview left on canvas at shutdown becomes a permanent orphan on reopen: unreachable by `clear_preview` and invisible to DG STRUCTURE CONFIRM.

## User Setup Required

None.

## Next Phase Readiness

- **Open, carried forward:** UAT test 7 (G12 per-entity blocking) is recorded **PENDING** — the code is complete and unit-tested, but observing the behaviour needs a live Rhino session. Since `028ff0e` types bare Number/Integer/Text/geometry params, triggering it now requires a member in neither the widget nor the primitive tier.
- Phase 36's publish can no longer be broken from the canvas by an accepted-but-untypeable parameter.
- F5c (per-entity publish rejection server-side) remains deliberately open — partial-write semantics change the `/computgraph/publish` response contract and interact with MERGE idempotency, so it is a design call, not a mechanical fix. Off the critical path now that the pre-flight makes the wholesale 422 unreachable from the canvas.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*
*Summary reconstructed from commits f2f518c, a82ab03, ae6d805 (and related 028ff0e) during Wave 1 close-out (2026-07-26).*
