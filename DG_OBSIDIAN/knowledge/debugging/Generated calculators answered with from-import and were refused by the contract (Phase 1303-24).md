---
tags: [debugging, phase-1303, property-calculator, llm]
date: 2026-10-25
---

# Generated calculators answered with `from ... import` and were refused by the contract

## Symptom

Two paid generations in a row for `hasMinProjectionClearanceMm` (provider openai) came back as `generation invalid: forbidden construct: ImportFrom` (14:49 and 14:56 UTC, after the first calculator was rejected with a reason). The property was left without a calculator (`rejected`, `regenerateRequested = true`).

## Cause (probable, not proven)

`validate_function` forbids `ast.Import`/`ImportFrom`, but the prompt only said "No imports" in `SYSTEM`; `CONTEXT_API` never said which names are already available. A rejection reason that asks for projection geometry invites an import of geometry helpers.

## Fix

`CONTEXT_API` now says "Write no import statements: math, DB, List, TOL_FT, FEET_TO_MM, element_solids and bbox_corners are already available" (commit `25297dd`, prompt pin re-pinned: 1746 characters, sha256 `61afb4e2…`). Not yet verified live: the owner declined a third paid call in this session.

## Lesson

A refused answer still costs a paid call. Validate the contract text against what the model actually gets (the user prompt, not only `SYSTEM`) before spending calls, and cap retries: one regeneration per owner "yes".

## Related

[[Calculators return None for nothing found, SendValid is one-shot and a retired calculator can be regenerated (Phase 1303-24, D-66 to D-68)]], [[sessions/2026-10-25 Phase 1303 plan 24 executed — no-data calculators, run check, regenerate retired, derived edges, rollout 23ed720]]
