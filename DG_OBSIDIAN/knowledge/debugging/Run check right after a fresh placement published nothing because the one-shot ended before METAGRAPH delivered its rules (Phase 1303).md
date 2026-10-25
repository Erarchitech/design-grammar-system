---
tags: [debugging, phase-1303, run-property-check, grasshopper, metagraph]
date: 2026-10-25
---

# Run check right after a fresh placement published nothing

## Symptom

2026-10-25 15:33–15:36 UTC, DeGram "Run check" on `str-openings-01` (stack `25297dd`/`23ed720`, DG.gha `96796214…`): the chain was re-placed (new calculator), the calculator report was complete, but the answer was 422 "The check did not run correctly; no verdict: error VALIDATOR: Rule input is required." and no `ValidationRun` was created. `sendValidGuard.disarmed = 1`. A later status read showed VALIDATOR with all 5 rules.

## Cause

`MetagraphComponent.StartLoad` loads rules asynchronously and schedules a new solution when they arrive (`Task.WhenAll(...).ContinueWith(... ScheduleSolution(1, ExpireSolution))`). After the placement the run's first solution had no rule at VALIDATOR (it returns before its outputs and before publishing). The listener's one-shot switched SendValid off at the end of that first solution; the next solution, with rules, did not publish. Supported by the manual publish at 15:50 (rules loaded: 5 of 5 runs published); not observed solution by solution.

## Fix

Plan 1303-25, D-70: `VerdictGate` keeps the one-shot armed until the solution that produced the verdict (bounded: 3 solution ends or 120 s); `oneShotPending` in the status; data-service waits for it and re-reads the status after the published runs are found. Needs DG.gha from `9d95481` or later.

## Lesson

"The run's solution ended" is not "the run's verdict exists" when an upstream component loads asynchronously. Wait on the output that proves the verdict (VALIDATOR RuleName), never on the first solution end.

Related: [[The check ends with its verdict, a non-verdict is never shown as a violation, calculators read by bounding box (Phase 1303-25, D-70 to D-72)]], [[Run check answers BUSY because the solution blocks the Rhino UI thread longer than 10 s, and SendValid left True loops publishing (Phase 1303)]].
