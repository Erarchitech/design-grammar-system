---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 07
subsystem: testing
tags: [de01, evidence-contract, python, pytest, classification, cross-service-validation]

requires:
  - phase: 1200-05
    provides: tools/de01/report.py compare_legs and the DE-01 unit test suite
provides:
  - Corrected compare_legs non-declarable guard that fires on any non-empty set of non-declarable statuses, matching the module docstring's stated rule
  - Regression tests pinning the exact CR-02 shape (passed vs unsupported+warning -> silent_disagreement) and the reviewer's unknown-status variant
  - An over-correction guard test proving declared_non_equivalence still exists as a classification
affects: [1200-08]

tech-stack:
  added: []
  patterns:
    - "Non-declarable guard uses truthiness of a set difference (non_declarable_statuses) rather than a size threshold — correct for 'any non-declarable status disqualifies declared classification'"

key-files:
  created: []
  modified:
    - tools/de01/report.py
    - tools/de01/tests/test_de01_runner.py

key-decisions:
  - "Fixed a second, previously undetected instance of the same CR-02 defect in test_unavailable_leg_all_error_rows_are_visible_not_dropped (passed vs error+warning wrongly asserted as declared_non_equivalence) as a Rule 1 auto-fix, since it is the identical bug shape under a different name and was not on the plan's protected-test list"
  - "Kept the non-declarable guard change to a single condition (len(...)>1 to truthiness) with no other logic touched, per the plan's prohibition on changing pair-union, ordering, or multi-row handling"

requirements-completed: [ALGN12-04]

coverage:
  - id: D1
    description: "compare_legs classifies a lone non-declarable status differing from a declarable+warned status as silent_disagreement, not declared_non_equivalence (CR-02 fix)"
    requirement: "ALGN12-04"
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py#TestCompareLegsSilentDisagreement::test_lone_non_declarable_status_beside_declarable_is_silent"
        status: pass
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py#TestCompareLegsSilentDisagreement::test_unknown_beside_declarable_warned_status_is_silent"
        status: pass
    human_judgment: false
  - id: D2
    description: "Declared non-equivalence classification survives for two differing declarable-and-warned statuses (over-correction guard)"
    requirement: "ALGN12-04"
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py#TestCompareLegsSilentDisagreement::test_two_declarable_warned_statuses_differing_is_still_declared"
        status: pass
    human_judgment: false
  - id: D3
    description: "Previously-passing behaviors (agreement, two non-declarable statuses differing, declarable-without-warning, pair-in-one-leg-only) unmodified and still passing"
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py -q -k 'not live' (13 passed, 1 deselected)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 07: DE-01 silent-disagreement classification fix (CR-02) Summary

**Fixed `compare_legs`'s non-declarable guard to fire on any non-empty set of non-declarable statuses instead of requiring two or more, closing CR-02 where a `passed`-to-`unsupported` regression was wrongly certified as a declared non-equivalence.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Removed the test that certified the CR-02 defect (`test_same_difference_with_unsupported_plus_warning_produces_zero`) and added three tests pinned against the module docstring's rule instead
- Fixed `compare_legs`'s guard condition from `len(non_declarable_statuses) > 1` to `if non_declarable_statuses:`, bringing the code into agreement with its own docstring (report.py lines 4-17)
- Discovered and fixed a second instance of the identical CR-02 shape hiding in an unrelated test (`test_unavailable_leg_all_error_rows_are_visible_not_dropped`), which asserted `passed` vs `error`+warning was declared — the same lone-non-declarable-status bug under a different name
- Confirmed the over-correction guard: two differing declarable-and-warned statuses (`unsupported`+warning vs `error`+warning) still classify as `declared_non_equivalence`
- `_DECLARABLE_STATUSES` untouched — still exactly `{"unsupported", "error", "not_evaluated", "indeterminate"}`

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace the wrong test and add the missing regression tests** - `6873003` (test)
2. **Task 2: Fire the non-declarable guard on any non-empty set** - `e0059a8` (fix)

**Plan metadata:** pending (this commit)

_Note: Task 1 was observed RED (2 of 3 new tests failing against unfixed code) before Task 2's fix turned them GREEN, per the plan's TDD requirement._

## Files Created/Modified
- `tools/de01/report.py` - `compare_legs`'s non-declarable guard changed from a size threshold (`> 1`) to a truthiness check (`if non_declarable_statuses:`); comment rewritten to state the corrected rule and reference CR-02
- `tools/de01/tests/test_de01_runner.py` - Removed `test_same_difference_with_unsupported_plus_warning_produces_zero`; added `test_lone_non_declarable_status_beside_declarable_is_silent`, `test_unknown_beside_declarable_warned_status_is_silent`, `test_two_declarable_warned_statuses_differing_is_still_declared`; corrected the classification assertion in `test_unavailable_leg_all_error_rows_are_visible_not_dropped`

## Decisions Made
- The guard's truthiness form (`if non_declarable_statuses:`) was chosen over an explicit `len(...) >= 1` for readability; both are semantically identical to "any non-empty set" and the verify command's regex accepts this form
- The second stale test (`test_unavailable_leg_all_error_rows_are_visible_not_dropped`) was corrected in place rather than deleted, per the plan's prohibition on deleting tests to make the suite green — its actual subject (an unavailable leg's error row still appearing in output, not dropped) is preserved via the unchanged `len(result.rows) == 1` assertion; only the classification expectation changed from the wrong value to the correct one

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected a second pre-existing instance of the CR-02 defect in an unrelated test**
- **Found during:** Task 2 (running the full suite after the guard fix)
- **Issue:** `test_unavailable_leg_all_error_rows_are_visible_not_dropped` asserted that `passed` (leg a) vs `error`+warning (leg b) classifies as `declared_non_equivalence`, with an inline comment stating "passed vs error with a warning IS declarable." This is the identical CR-02 shape — a lone non-declarable status (`passed`) differing from a declarable+warned status — under a different name and status pairing. Per the docstring's rule this plan enforces, `passed` is not declarable, so this must be `silent_disagreement`. This test was not named in the plan's list of tests required to survive unmodified, and fixing the guard correctly made it fail (previously it passed only because the guard's old, narrower form let this shape through).
- **Fix:** Corrected the classification assertion to `silent_disagreement` and `silent_disagreement_count == 1`, updated the inline comment to state the correct rule and reference CR-02, and preserved the test's actual subject (the unavailable leg's error row is still visible in `result.rows`, not dropped) via the unchanged `len(result.rows) == 1` assertion.
- **Files modified:** tools/de01/tests/test_de01_runner.py
- **Verification:** Full non-live suite passes (13/13) after the correction; the mechanical source-check in the plan's Task 2 verify command also passes.
- **Committed in:** e0059a8 (part of Task 2 commit, since the fix that exposed this stale assertion is the same commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 - bug)
**Impact on plan:** Necessary to keep the full suite green without reintroducing the CR-02 defect via an unfixed test; no scope creep — same bug shape, same governing docstring rule, no new files touched.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CR-02 / GAP-2 closed: `compare_legs` now implements its own docstring's rule exactly
- `_DECLARABLE_STATUSES` unchanged, so D-02's vocabulary freeze holds
- The declared classification survives for genuinely declarable-and-warned differences, so plan 1200-08's live four-leg run (expected to exercise the by-design `ObjectPropertyAtom` case) should still see it classified as `declared_non_equivalence`
- No blockers for 1200-08

---
*Phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt*
*Completed: 2026-09-20*

## Self-Check: PASSED

- FOUND: tools/de01/report.py
- FOUND: tools/de01/tests/test_de01_runner.py
- FOUND: .planning/phases/1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt/1200-07-SUMMARY.md
- FOUND commit: 6873003
- FOUND commit: e0059a8
