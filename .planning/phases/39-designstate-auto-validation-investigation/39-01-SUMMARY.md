---
phase: 39-designstate-auto-validation-investigation
plan: 01
subsystem: api
tags: [neo4j, fastapi, threading, shacl, dg-reasoner, python]

requires: []
provides:
  - "dsav_watcher.py — standalone, importable watcher module implementing the full capture -> debounce -> coalesce -> validate -> complete/fail state machine as a pure poll_once() function"
  - "Eight parameterized Cypher constants for the ValidationRun capture/config state machine, corrected per P-09 (FOREACH not UNWIND for coalesce; WITH-bound attempt increment for fail)"
  - "derive_valid_status() — pure P-02 focusLabel-join implementation mapping a SHACL verdict back onto ObjState ValidStatus indices"
  - "In-memory guardrail state (debounce read off the row, rate-limit window) plus thread lifecycle (start_watcher/stop_watcher) never started at import time"
  - "dsav_fixtures.py + test_dsav_watcher.py — 18-test host-tier suite, zero live Neo4j, zero thread, zero sleep"
affects: ["39-02 (POST /designstate/capture route + app.py wiring)", "39-03 (live-Docker verification)", "39-05 (DSAV-03 ADR)"]

tech-stack:
  added: []
  patterns:
    - "Injectable-session pure function (dg_context.py precedent): every public function takes session=None, threading a private _run_read/_run_write helper that branches on session is not None vs. a lazily-opened driver.session()"
    - "Query-identity dispatch test double (DsavFixtureSession): a single duck-typed session routes multiple distinct Cypher constants per tick by a unique substring marker, since poll_once() issues several different queries per call, unlike single-query precedents in this suite"
    - "D-08 departure from Phase 823 degrade-never-raise: the same _call_shacl_validate-shaped status dict is treated as fatal-to-completion (not fatal-to-process) by this caller, unlike publish_validation's caller"

key-files:
  created:
    - data-service/dsav_watcher.py
    - data-service/tests/dsav_fixtures.py
    - data-service/tests/test_dsav_watcher.py
  modified: []

key-decisions:
  - "COALESCE_QUERY additionally returns the kept row's statePayloadJson (beyond the plan's minimum RETURN spec) so poll_once() can call derive_valid_status() without a second read — the plan's Cypher shapes did not specify where this comes from"
  - "poll_once() treats config-row-absent-or-disabled inside the per-project loop as skip reason no_captured_rows (defensive only — ENABLED_PROJECTS_QUERY already filters enabled=true at the Cypher level, so this branch is unreachable against real Neo4j)"
  - "FAIL_QUERY's reason parameter uses the literal SHACL status string (timeout/unavailable) or no_response when shacl_fn is absent/returns None, giving lastError a stable small vocabulary"

requirements-completed: [DSAV-02]

coverage:
  - id: D1
    description: "poll_once() runs to completion against an injected FixtureSession with zero live Neo4j, zero thread, zero time.sleep (D-03)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_no_enabled_projects_returns_noop_summary_and_issues_no_writes"
        status: pass
    human_judgment: false
  - id: D2
    description: "A project with no IntegrationConfig{provider:'AutoValidation'} row is invisible to the watcher — poll_once() no-ops (D-13)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_get_auto_validation_config_absent_row_returns_none"
        status: pass
    human_judgment: false
  - id: D3
    description: "N captured rows for one project inside the debounce window collapse to exactly 1 validated run; the other N-1 carry status:'superseded' (D-14)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_debounce_release_coalesces_five_captured_rows_marks_four_superseded"
        status: pass
    human_judgment: false
  - id: D4
    description: "A SHACL sidecar failure leaves the row status:'captured' and increments attempts; the maxAttempts-th failure flips it to status:'failed' with a reason (D-08 departure from Phase 823 degrade-never-raise)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_fail_path_shacl_timeout_flips_to_failed_on_third_attempt"
        status: pass
    human_judgment: false
  - id: D5
    description: "A completed auto-run carries trigger:'auto' and verdictSource:'shacl' (D-07)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_debounce_release_coalesces_five_captured_rows_marks_four_superseded"
        status: pass
    human_judgment: false
  - id: D6
    description: "derive_valid_status() correctly maps a SHACL verdict onto ObjState indices via the focusLabel join key, including the conservative unmapped-violation fallback (P-02)"
    requirement: "DSAV-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_derive_valid_status_mapped_violation_flips_exactly_one_index"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dsav_watcher.py#test_derive_valid_status_unmapped_violation_flips_every_index_and_reports_it"
        status: pass
    human_judgment: false
  - id: D7
    description: "Live-Docker verification that the eight Cypher constants execute correctly against real Neo4j 5.26 (RESEARCH.md A2: the shapes are synthesized proposals, never executed live in research)"
    verification: []
    human_judgment: true
    rationale: "This plan is host-tier only by design (Wave 0). Live-Neo4j execution is explicitly Plan 03's scope, not verifiable without the Docker Compose stack."

duration: ~30min
completed: 2026-07-27
status: complete
---

# Phase 39 Plan 01: DesignState Auto-Validation Watcher Core Summary

**Pure `poll_once()` state machine (capture -> debounce -> coalesce -> SHACL verdict -> complete/fail) in a new `dsav_watcher.py` module, fully exercised by an 18-test host-tier suite with zero live Neo4j, zero thread, and zero sleep.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-07-27
- **Tasks:** 2 completed
- **Files modified:** 3 (all new)

## Accomplishments
- `data-service/dsav_watcher.py`: the whole DSAV-02 state machine as one importable, side-effect-free module — no `app.py` import, no thread started at import time, all eight Cypher constants parameterized with the P-09 corrections (`FOREACH` not `UNWIND` for the coalesce tail; a `WITH`-bound attempt increment before the fail `SET`)
- `derive_valid_status()` implements P-02's `focusLabel` join against `label or objectRef or stateId`, including the conservative "unmapped violation flips every index" fallback
- In-memory guardrail state (debounce read off the row's `capturedAt`, per-project rate-limit window) plus a `threading.Event`-gated daemon thread lifecycle (`start_watcher`/`stop_watcher`), matching D-15's accepted "restart resets the window" limitation
- `dsav_fixtures.py` (`FIXTURE_PROJECT = "p39-autoval"`, v2 envelope + SHACL verdict builders, `DsavFixtureSession` query-identity dispatcher) and `test_dsav_watcher.py` (18 tests covering every `<behavior>` bullet in the plan)
- Host suite confirmed green: 677 passed, same 4 pre-existing `test_dg_context.py` failures as the documented baseline, plus pre-existing Neo4j-DNS-resolution integration-test errors verified (via a stash-isolated re-run) to be unrelated to this plan's changes

## Task Commits

1. **Task 1: Create data-service/dsav_watcher.py** - `93a0b0b` (feat)
2. **Task 2: Create dsav_fixtures.py + test_dsav_watcher.py** - `c2aefb1` (test)

_Plan metadata commit pending below._

## Files Created/Modified
- `data-service/dsav_watcher.py` - watcher state machine: config/capture API, `derive_valid_status()`, `poll_once()`, guardrail state, thread lifecycle
- `data-service/tests/dsav_fixtures.py` - `FIXTURE_PROJECT`, envelope/SHACL builders, `DsavFixtureSession`
- `data-service/tests/test_dsav_watcher.py` - 18-test host-tier suite

## Decisions Made
- **COALESCE_QUERY returns `statePayloadJson` for the kept row**, beyond the plan's minimum specified `RETURN` list (`keptRunId` + tail size). `derive_valid_status(state_payload_json, shacl_body)` needs the envelope to build its objState index map, and nothing else in the plan's eight-constant spec provides that read after coalesce runs. Adding it as an extra `RETURN` column is additive and satisfies every acceptance-criteria grep for `COALESCE_QUERY` (still contains `FOREACH`, still scoped to `status:'captured'`, still no `UNWIND` on the stale tail). Documented here rather than applied silently per Rule 2 (missing critical functionality — without it, the "ok" branch of `poll_once()` could never derive a `ValidStatus`).
- **The disabled/absent-config branch inside `poll_once()`'s per-project loop reports `no_captured_rows`** rather than inventing a fourth skip reason. `ENABLED_PROJECTS_QUERY` already filters `enabled = true` at the Cypher level, so this branch is defensive-only and unreachable against a real Neo4j instance; it exists purely so a synthetic test double that violates that invariant still degrades safely instead of raising.
- **`FAIL_QUERY`'s `reason` parameter** is the literal SHACL status string (`"timeout"`/`"unavailable"`) when `shacl_fn` returns one, or the literal `"no_response"` when `shacl_fn` is `None`/returns `None` — kept as a small, stable vocabulary for `lastError` rather than a free-text message.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `statePayloadJson` to `COALESCE_QUERY`'s `RETURN`**
- **Found during:** Task 1 (writing `poll_once()`'s complete-path logic)
- **Issue:** The plan's `<behavior>` block requires `derive_valid_status(state_payload_json, shacl_body)` to run in the "ok" branch, but neither `NEWEST_CAPTURED_QUERY` nor `COALESCE_QUERY`'s specified `RETURN` columns (`keptRunId` + superseded count) supply the envelope JSON. Without it, `poll_once()` could coalesce and call SHACL but could never derive a `ValidStatus`.
- **Fix:** Added `kept.statePayloadJson AS statePayloadJson` as an additional `RETURN` column on `COALESCE_QUERY`. No other column, clause, or the `FOREACH`/`status:'captured'` scoping changed.
- **Files modified:** `data-service/dsav_watcher.py`
- **Verification:** `test_debounce_release_coalesces_five_captured_rows_marks_four_superseded` and `test_complete_path_with_unmapped_violation_flips_every_objstate_and_counts_it` both assert the derived `ValidStatus` on the resulting `COMPLETE_QUERY` call.
- **Committed in:** `93a0b0b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary for the state machine to actually derive a verdict; no scope creep — everything else in the eight Cypher constants matches the plan's specified shape exactly, verified by the plan's own acceptance-criteria greps.

## Issues Encountered
- **Unrelated pre-existing dirty working tree.** At session start, several DG.Core/DG.Grasshopper build-artifact files (`bin/`/`obj/`) and three legitimate files (`.claude/settings.local.json`, `.graphifyignore`, `.planning/STATE.md`) were already modified/uncommitted from a prior session. A `git status` check mid-task (to isolate whether the 25 pytest `ERROR`s in `test_cg_structure_checks.py`/`test_computgraph_consult.py` were caused by this plan) required a `git stash`; the subsequent `git stash pop` failed because the build-artifact files had been regenerated on disk in the interim, producing a merge conflict entirely within disposable `bin/`/`obj/` cache files. Resolved non-destructively: restored the three legitimate files (`git checkout stash@{0} -- <path>` then `git restore --staged`) without touching the conflicting build artifacts; the stash (`stash@{0}`) is left in the stash list, untouched, for the user to inspect or drop at their discretion. No task file, no prior commit, and no `.planning`/config content was lost. This is unrelated to Phase 39 and pre-dates this session.
- Confirmed (via that same stash-isolated re-run) that the 25 pytest `ERROR`s in `test_cg_structure_checks.py`/`test_computgraph_consult.py` are pre-existing `neo4j` DNS-resolution failures (the `neo4j` hostname only resolves inside the Docker Compose network, per `conftest.py`'s own comment) — identical with or without this plan's new files present. Not a regression introduced by this plan; not one of the four failures the plan's acceptance criteria names, but confirmed unrelated by direct A/B test.

## User Setup Required
None - no external service configuration required. This plan is host-tier only; no Docker/Neo4j/dg-reasoner interaction happens in Task 1 or Task 2.

## Next Phase Readiness
- `dsav_watcher.py`'s public API (`capture_state`, `poll_once`, `get_auto_validation_config`/`upsert_auto_validation_config`, `start_watcher`/`stop_watcher`) is ready for Plan 02 to wire into `app.py`'s new `POST /designstate/capture` route and `lifespan` startup hook.
- The eight Cypher constants are syntactically confirmed only by string-shape assertions on the host tier (per this plan's explicit Wave 0 scope) — RESEARCH.md's Assumption A2 (live-Neo4j execution correctness) remains open and is Plan 03's job, not proven here.
- No blockers for Plan 02.

---
*Phase: 39-designstate-auto-validation-investigation*
*Completed: 2026-07-27*

## Self-Check: PASSED

All claimed files exist on disk and both task commits (`93a0b0b`, `c2aefb1`) are present in git history.
