---
tags: [debugging, computgraph, parser, publish, phase-34, phase-35, phase-36]
date: 2026-07-25
updated: 2026-07-26
status: fixed
---

# F5 — Bare Number component infers null dataType with no warning, 422s the whole publish

**Context:** v9.0-PIPELINE-UAT Group 4.4/4.5, live on UrbanBlock_V7. A synthetic Const proposal targeting a bare `Number` component was accepted cleanly in Phase 35, then rejected the entire Phase 36 publish payload with a 422.

## Root cause

`InferParameterDataType` (`DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs:447-488`) only classifies four component kinds: slider, value list, panel, boolean. A `Number` component matches none of them, so `classified.Count == 0` returns `(null, null, null)` — **null dataType and no warning**.

## Compounding effects

1. **Silent at parse time.** The context pull looked clean (0 warnings) while carrying an unpublishable parameter.
2. **No accept-time validation.** Phase 35's StructureConfirmComponent happily converts the proposal into a permanent group — nothing checks dataType before confirming.
3. **All-or-nothing publish.** SHACL correctly rejects it (`ParameterShape_dataType requires it, sh:minCount 1`), but the 422 kills the ENTIRE payload — 11 otherwise-valid nodes couldn't land because of 1 bad one.

## Live repro

```
Unsupported dataType None on parameter 'cg:1:const:12_Const_Num'.
ParameterShape_dataType requires it (sh:minCount 1).
Allowed values: ['Boolean', 'Float', 'Geometry', 'Integer', 'Text'].
```

**Workaround used:** ungrouped the offending `12_Const_Num` group in Grasshopper (not deleted — that would take the `Number` component too), then re-published successfully.

## Suggested fix

- Infer a sane default (e.g. `Float`) for numeric-ish untyped members, OR
- Emit a warning at parse time when `classified.Count == 0`, AND
- Validate dataType at Phase 35 accept time (before the group becomes permanent), AND
- Consider per-entity rather than all-or-nothing publish rejection so one bad node doesn't block a whole subgraph.

**Severity:** high — blocks the terminal integration gate (36 SC1) on any canvas with an untyped Constant source, which is a completely ordinary authoring pattern.

**Cross-phase:** 34 (parser) → 35 (accept, no validation) → 36 (publish, SHACL rejects everything).

## Fix Applied (2026-07-26)

Implemented all three parts:

1. **Parser inference (commit `028ff0e`):** Two-tier precedence. Widgets (slider > value list > panel > toggle) still win; when absent, a new **primitive fallback tier** (Number > Integer > Text > geometry) types bare GH params. `Number`→Float, `Integer`→Integer, `Text`/`String`→Text, 15 exact geometry names→Geometry.
   
2. **Parse-time warning:** Members present but untypeable now append `"…dataType is unset and publishing will reject the payload"` instead of returning silently. Member-less groups stay quiet (tag-then-populate is normal).

3. **Accept-time + publish-side validation:**
   - Phase 35 (parallel session, commit `ae6d805`): G12 gate blocks individual proposals whose dataType cannot be inferred; offender stays PENDING so the architect can fix the canvas and re-apply.
   - Phase 36 (commit `028ff0e`): `DG COMPUTGRAPH PUBLISH` pre-flights null dataTypes, names them in status, refuses to POST.

**Verification:** 384/384 C# tests pass. Live-verified on Rhino: `cg:1:const:11_Const_Num` (bare Number) publishes as Constant/Float; subgraph went 11→12 nodes. MERGE idempotency re-confirmed.

**Part (c) deliberately not taken:** Per-entity publish rejection would change the response contract and interact with MERGE idempotency + stale-entity reporting — a design call, not a fix. Off the critical path now that the pre-flight catches it first.

## Related

- [[debugging/Phase 36 provider-model-confidence never persisted (F6)]]
- [[sessions/2026-07-26 Phase 35 F5 fix — dataType inference on bare params]]
- `.planning/phases/35-llm-recognition-canvas-preview/35-UAT.md` F5 status
- `.planning/phases/36-computgraph-persistence-display/36-UAT.md` SC3
