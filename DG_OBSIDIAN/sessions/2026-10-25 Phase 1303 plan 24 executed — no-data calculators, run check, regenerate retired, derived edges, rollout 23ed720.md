---
tags: [session, phase-1303, dgopn-05, dgopn-06, plan-24]
date: 2026-10-25
---

# Session: 2026-10-25 (afternoon) — Phase 1303 plan 1303-24 executed and rolled out

Model: claude-sonnet-5-5. Branch `feature/mapping-mvp`, worktree `dg-mapping`. Nothing pushed. A parallel development session works in the same worktree: only committed state went into images and the plugin, and every commit named its files.

## What Was Done

- **Publish loop check.** Stopped (last `POST /validation/publish` 10:09:21 UTC, `SendValid=False`, listener answered). 50 `ValidationRun` of 2026-10-25 (09:15–10:08) = 50 Speckle versions in model `dg-validation` (a6d1e0c5da, 435 versions in all); earlier loops: 232 runs on 21.10, 10 on 22.10. The owner chose **not to delete** anything.
- **Plan 1303-24** (`.planning/phases/1303-pravilo-gh-obekt/1303-24-PLAN.md`, SUMMARY written). The DSH hub was unreachable (`hub_reachable=false`); the owner chose "implement myself, TDD". One commit per task: `6d0df1f` (D-66), `34db9e7` and `e3e08d5` (D-67), `c9fe4a8` (D-68 backend), `23ed720` (D-68 UI, D-69), `414a7ab` (rollout evidence), `0bfa322` (SUMMARY), `25297dd` (no-import prompt line).
- **Rollout.** Images `dg-mapping-data-service:25297dd` (since 14:57) and `dg-mapping-ui:23ed720`; rollback files in `D:\dgb\mapping-release-23ed720\` and `D:\dgb\mapping-release-25297dd\` (previous images are kept). DG.gha `96796214…` built from `git archive 23ed720` and **installed by the owner** (hash checked); backup `D:\dgb\plugin-backup\DG-20261025-pre-23ed720`.
- **Gate** (committed state): data-service 4 failed / 6533 passed / 25 errors (the 1303-18/23 baseline names), de01 1 baseline failure, DG.Tests 822 passed + 5 environmental, ui-v2 381/381.
- **Live LLM generation (owner "yes", three paid calls in total):** the old stored source of `hasMinProjectionClearanceMm` failed the new contract (return 0.0 in an `is None` branch), so one call made `calc_gen_2ee367e280` (all not-found branches return `None`, but it read only columns and the first host wall: participants Slab and Wall missing, `CALCULATOR_PARTICIPANT_MISMATCH`; for an opening hosted by a slab `host_walls` is empty, so almost every box would be no data). It was rejected with a reason and regenerated; two further calls (the regeneration and one retry) were refused by the contract: `forbidden construct: ImportFrom`. A line "Write no import statements..." was added to `CONTEXT_API` (`25297dd`); the owner declined a third paid attempt.

## Decisions Made

- D-66 no data is `None`, never 0 for a measured distance; D-67 one `run_property_check`, no blind retry, SendValid is one-shot; D-68 regenerate a retired copy from the UI; D-69 derived class edges (already decided 2026-10-25). See [[Calculators return None for nothing found, SendValid is one-shot and a retired calculator can be regenerated (Phase 1303-24, D-66 to D-68)]].
- Act 5 of plan 1303-18 will use `hasMinProjectionClearanceMm` (owner), not a new height rule.

## Issues Encountered

- [[Generated calculators answered with from-import and were refused by the contract (Phase 1303-24)]].
- The Bash tool collapses `\\x00`/`\\n` escapes inside heredocs: Python edits with such escapes were corrupted twice (NUL byte, real newline); use the Edit tool for those.

## State at the end of the session

- **Property `hasMinProjectionClearanceMm` has no calculator** (status rejected, `regenerateRequested = true`, rejected hashes: `b09939e5…`); the next "Generate check" makes one paid LLM call. The other four rules compute.
- Rhino/Revit were closed at the end (listener on 8720 refused). Plan 1303-18 Task 3 (second project reuse, isolation, `promotion-live.json`, PROTOCOL "Akt 5", UAT 13) and the closing of 1303-18 and 1303-23 are **not done**.

## Next Steps

1. Owner: allow one more LLM generation for `hasMinProjectionClearanceMm` (or accept no calculator for this property), open Rhino + Revit + `phase1303-test-revit.gh`.
2. Run the check from the Mapping panel: expect the new chain to be placed (calculator sha differs), `nodata=` in the report, `unknown` (not violations) for boxes without data; publish once by hand (`SendValid` True, F5; it should switch itself off) and confirm no loop.
3. Plan 1303-18 Task 3 act 5, then SUMMARY/UAT/STATE/ROADMAP/REQUIREMENTS (DGOPN-05, DGOPN-06) for 1303-18 and 1303-23, then `/gsd-verify-work 1303`.
4. Open proofs from plan 1303-24: a `None` item keeps the positional ObjState pairing (VALIDATOR `unknown` on exactly those boxes); the SendValid auto-off does not cut the asynchronous Speckle upload.
5. 1303-06, 1303-07, 1303-14 remain unexecuted; `.planning/STATE.md` and `config.json` carry another session's uncommitted edits: reconcile before closing plans.

## Related Notes

- [[sessions/2026-10-25 Phase 1303 live acceptance of 18 and 23 — stack rolled to f0e27a1, acts 1-4, findings|morning session (findings)]]
- [[Run check answers BUSY because the solution blocks the Rhino UI thread longer than 10 s, and SendValid left True loops publishing (Phase 1303)]]
- [[Generated property calculators return 0.0 when no related element is found (Phase 1303)]]
- [[Graph Viewer draws class-to-class edges derived from ObjectProperty domain and range (Phase 1303)]]
