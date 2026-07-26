---
tags: [debugging, computgraph, parser, publish, phase-34, phase-35, phase-36]
date: 2026-07-25
status: open
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

## Related

- [[debugging/Phase 36 provider-model-confidence never persisted (F6)]]
- `.planning/phases/35-llm-recognition-canvas-preview/35-UAT.md` test 4
- `.planning/phases/36-computgraph-persistence-display/36-UAT.md` test 1
