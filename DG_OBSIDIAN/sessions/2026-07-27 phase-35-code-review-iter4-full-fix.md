# Session: Phase 35 Code Review Iteration 4 — Full Fix

**Date:** 2026-07-27  
**Duration:** Full session  
**Outcome:** All 12 Critical + Warning findings from iter3 fixed and verified

## Summary

Phase 35 had three prior review iterations. Iteration 3 reported 17 findings (3 critical, 9 warning, 5 info) that were never fixed. This session:

1. Re-verified all 17 findings against current HEAD independently — all still present.
2. Widened the review to the full phase scope (41 files) — no new defects found beyond the 17.
3. Fixed all 12 Critical + Warning findings (deferred 5 Info: pass `--all` to fix those).
4. Added 11 hermetic regression tests covering the fixes.
5. Verified: baseline 89 → 100 passed, 1 skipped, 1 deselected.

## Key Fixes

### Critical

**CR-01** (`few_shot_permutations` duplicate orderings):  
Arms A0/A0f resolve a 1-example few-shot list. The old code branched on the requested count `n`, not list length, so `reversed([x]) == [x]` and `k = 1//2 or 1` made the rotation a no-op — three identical orderings billed as independent calls, written to one cassette 3×, reported as a sub-sweep measuring example-order stability. Fixed by branching on list length and deduplicating: `A0: 3→1 distinct`, `A3/A4: 3 distinct`. No published numbers had to be withdrawn (the sub-sweep in EVAL-REPORT was `--arms=A3`, which had 5 examples → genuinely 3 distinct).

**CR-02** (`TestEndToEndDriver` hardcoded `json_schema_strict`):  
Mode is a cassette-key input. A4's real mode is `json_object` (DeepSeek rejects `json_schema`/`strict`), but the driver hardcoded the naive placeholder, so A4 — the *one* arm the harness exists to distinguish — could never replay. Fixed at the source: `run_arm`'s default `negotiated_mode` is now `resolve_real_negotiated_mode(arm)` instead of a known-wrong placeholder, so a caller forgetting the override still gets the right mode. Verified: `--arm=A4` now `1 passed` (was `CassetteMissError`).

**CR-03** (tautological paid test):  
The sole assertion checked `status` against exactly the literals `live_sweep` assigns, so it could not fail for any input — a record run with no credentials skipped every arm, spent nothing, and exited green, indistinguishable from success. Fixed: assertions now check recordings exist, no combo failed after spending, and cost was tracked. Added: `run_live_sweep` refuses to start when `LLM_MASTER_SECRET` is the test placeholder, so misconfiguration fails *before* spending.

### Warnings

- **WR-01**: Per-combo exception isolation; failed combos become `"failed"` status and the accumulated cost/token record survives (previously escaped and lost everything).
- **WR-02**: Unpriced calls flagged separately (`priced=False`) instead of silently reading as free.
- **WR-03**: `permutations < 1` rejected at both entry points; shortfall vs. distinct orderings recorded as a named detail.
- **WR-04**: `run_report_sweep(..., permutations=N)` replays the few-shot sub-sweep; verified A3 hits 4 distinct cassette keys. The sub-sweep is now regenerable from committed state.
- **WR-05**: Skip guard in `test_options_registered_with_expected_defaults` now covers all 5 asserted options.
- **WR-06**: `CassetteAdapter` refuses the placeholder `"test-api-key"` on the live branch.
- **WR-07**: `resolve_real_negotiated_mode` raises on unmapped provider labels instead of silently probing HTTP.
- **WR-08**: Base URLs masked in error messages (scheme://host, dropping credential-bearing path segments).
- **WR-09**: `_compute_scored_row` → public `compute_scored_row`; `live_sweep` is a contract consumer.

## Structural Change

`few_shot_permutations` moved from `live_sweep.py` to `arms.py` (its natural home, where few-shot artifacts are resolved) so `report.py` can reuse the generator on the replay side without creating a cycle. Re-exported from `live_sweep` — all callers unaffected.

## Commits

- `e61952f` — CR-02, WR-07
- `0e496b6` — CR-01, WR-01, WR-02, WR-03, WR-06, WR-08, WR-09
- `0a46d63` — CR-03, WR-04, WR-05
- `209e066` — docs(35): add code review fix report (iteration 4, 12/12 fixed)

## Test Coverage Added

11 new regression tests in `TestLiveSweepHelpers` covering:
- Permutation distinctness across list lengths
- Non-positive counts rejected at entry points
- Unpriced-call flagging and `cost_summary` output
- URL masking in error messages
- `--permutations` flag validation
- Sub-sweep replay from committed cassettes

Plus: `TestArms::test_live_mode_refuses_the_placeholder_api_key` for WR-06.

## Deferred

The 5 Info findings (IN-01…IN-05) remain unfixed — pass `--all` to include them in a future fix run.

## Context for Next Session

- Phase 35 is now code-review clean at Critical + Warning severity.
- The full-phase review widening turned up no new findings in the files iter 1–3 never covered.
- A3's permutation sub-sweep is now fully reproducible from committed cassettes.
