---
tags: [debugging, phase-1303, property-calculator, d62]
date: 2026-10-25
---

# Generated property calculators return 0.0 when no related element is found

## Symptom

`hasMinProjectionClearanceMm` (rule `R_STR_OPENING_CLEARANCE_MIN_500_V`, "closer than 500 mm") gives `min=0.0 max=0.0` on all 313 boxes, so the rule is violated on every box. Both the 2026-10-21 generated script and the 2026-10-25 regeneration (D-62 prompt with participants Slab, Column, Wall) end with `if min_clear is None: return 0.0`.

## Cause

The generation contract lets a calculator return `0.0` for "nothing found". For a "minimum clearance" property that is the worst possible value, so absence of data becomes a violation instead of `unknown`. The shell (`calculator_shell.py.tmpl`) records exceptions as `None` but a normal fallback is not distinguishable.

## Not the cause

Participants and categories: the new script reads Columns/StructuralColumns/Walls (no Beam), `READS_CLASS` links Slab, Wall, Column correctly. Regenerating again would give the same pattern.

## Fix (planned, 1303-24)

Contract and prompt: a calculator returns `None` when no related element exists; PROPERTY STATE/VALIDATOR then report `unknown` (spec/EVIDENCE-CONTRACT.md) instead of a violation. Add a test that fails a source ending in `return 0.0` for the not-found branch.

## Related

[[Property calculators read elements by their DG mapping, not only by Revit category (Phase 1303-15)]], [[sessions/2026-10-25 Phase 1303 live acceptance of 18 and 23 — stack rolled to f0e27a1, acts 1-4, findings]]
