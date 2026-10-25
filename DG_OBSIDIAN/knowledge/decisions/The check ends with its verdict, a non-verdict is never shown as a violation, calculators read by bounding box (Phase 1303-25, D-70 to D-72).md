---
tags: [decision, phase-1303, property-calculator, run-property-check, evidence, d70, d71, d72]
date: 2026-10-25
---

# The check ends with its verdict; a non-verdict is never shown as a violation; calculators read by bounding box

Fixes for the live check of 2026-10-25 afternoon (evidence `test/str-openings-01/evidence/live-check-1303-24.json`). Implemented by plan 1303-25 (owner chose "plan 25 first, offline, TDD"); see [[sessions/2026-10-25 Phase 1303 live check of plan 24 and plan 25 executed — verdict-gated one-shot, no-verdict presentation, bbox helpers]].

## D-70 — the one-shot is released by the solution that produced the verdict

`VerdictGate` (DG.Core) keeps the listener's one-shot (SendValid and Paint) armed through solutions in which VALIDATOR had no rule, at most 3 solution ends or 120 s; "verdict produced" = every VALIDATOR of the property-check group has a RuleName output (it publishes synchronously in that same SolveInstance). The one-shot is armed for every non-clear run; the hand SendValid guard waits the same way. The listener reports `oneShotPending`; data-service waits for it and re-reads the status once the published runs are found. **Why:** METAGRAPH loads rules asynchronously; after a fresh placement the run's first solution had no rules, SendValid went off, nothing was published (422 "Rule input is required"). **How to apply:** a run is finished when its verdict exists, not at the first solution end.

## D-71 — a non-verdict is never shown as a violation

VALIDATOR gets an appended `Status` output (canonical status per ObjState); `ValidStatus` is unchanged. The Revit highlighter paints red only for failed/error, grey for any other non-passed status, green for passed (falls back to ValidStatus without Status). `/validation/view` objectSets gains `unknown`; `failed` keeps failed and error; the Model Viewer draws and lists the unknown set apart. Recorded in `spec/EVIDENCE-CONTRACT.md` §5.0. **Why:** D-66 made "no data" `unknown` in the evidence, but every display surface read the legacy boolean and showed 313 such boxes as violations. **How to apply:** any new surface that colours or lists objects reads the canonical status, never `ValidStatus`.

## D-72 — generated calculators read neighbours by bounding box

The calculator shell offers `ctx.near(box, categories, max_mm)`, `ctx.host_floors(box)` and `ctx.plan_gap_mm(a, b)`; CONTEXT_API names them (prompt pin 2297 characters, sha256 `60405fd9…`). **Why:** `ctx.intersecting` is a solid test; an opening box sits in the slab's hole and a column 200 mm away never touches it, so the generated clearance calculator found nothing on all 313 boxes. **How to apply:** the regenerated calculator (one paid call per owner "yes") should use these helpers.

Related: [[Calculators return None for nothing found, SendValid is one-shot and a retired calculator can be regenerated (Phase 1303-24, D-66 to D-68)]], [[Run check right after a fresh placement published nothing because the one-shot ended before METAGRAPH delivered its rules (Phase 1303)]].
