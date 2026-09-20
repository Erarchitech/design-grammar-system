---
phase: 39-designstate-auto-validation-investigation
plan: 03
subsystem: api
tags: [neo4j, shacl, dg-reasoner, docker, pytest, measurement, python]

requires:
  - "39-01 (dsav_watcher.py: the eight Cypher constants, poll_once, upsert_auto_validation_config)"
  - "39-02 (POST /designstate/capture + the FastAPI lifespan that owns the watcher daemon)"
provides:
  - "test_dsav_live_loop.py — 6-test live-Docker driver: the only place in Phase 39 where the loop runs against real uvicorn, real Neo4j 5.26.28 and the real dg-reasoner SHACL sidecar"
  - "39-EVIDENCE.json — the measured SC1/SC2 artifact Plan 05's investigation note and the DSAV-03 ADR cite as fact"
  - "F-39-01 / F-39-02 — two derived findings promoted out of the numbers for the ADR"
  - "39-RESEARCH.md assumption A2 discharged: all eight [ASSUMED] Cypher shapes executed live"
  - "data-service/tests/README.md Phase 39 run story incl. the p39-autoval reservation and both-tier counts"
affects: ["39-04 (the single deliberate Speckle publish)", "39-05 (DSAV-03 ADR + investigation note)"]

tech-stack:
  added: []
  patterns:
    - "Evidence-emitting test module: a module-scoped accumulator serialized once at teardown, with a `missing_measurements` list so an unrun scenario is a visible hole rather than a plausible-looking number"
    - "Row-sourced timing (P-13): latency is completedAt - capturedAt parsed off the node, never an in-process stopwatch, so the number is auditable and does not fold in the poll interval's phase offset"
    - "Daemon parking: setting debounceWindowSeconds to 3600 pins the live watcher on `debounce_wait` so a test can drive poll_once against the same live session with a future `now` without racing it"
    - "Rate-window drain derived from row timestamps — the only observable proxy for the daemon's in-process limiter state (D-15)"

key-files:
  created:
    - data-service/tests/test_dsav_live_loop.py
    - .planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json
  modified:
    - data-service/tests/README.md

key-decisions:
  - "The runs-per-minute burst uses a cycle schedule (4 captures at 1s intervals, then 8s idle) rather than the plan's literal 'a capture every second': a uniform 1 Hz stream against a 5s debounce re-arms the window forever and would have measured 0 runs/min — debounce starvation, not the rate limiter the test exists to demonstrate"
  - "Each measured scenario first drains the rate-limit window (bounded wait until no completion falls inside the trailing 60s), because the limiter is in-process and carries over between tests in one module run"
  - "The D-08 ladder parks the live daemon on a 3600s debounce and drives poll_once itself with a future `now`; without parking, the real daemon completes the row and the ladder never steps"
  - "The evidence writer emits nothing when nothing was measured, rather than an artifact of nulls — Plan 05 cites this file as measured fact"

requirements-completed: [DSAV-02]

coverage:
  - id: D1
    description: "On live Docker, one authenticated POST /designstate/capture produces a completed :ValidationRun with trigger:'auto' and verdictSource:'shacl' with no further human action (SC1)"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_live_loop.py#test_sc1_loop_closes_hands_off"
        status: pass
    human_judgment: false
  - id: D2
    description: "A burst of N rapid captures inside the debounce window produces exactly 1 non-superseded run; the other N-1 rows carry status:'superseded' and remain queryable (SC2)"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_live_loop.py#test_sc2_debounce_collapse_ratio"
        status: pass
    human_judgment: false
  - id: D3
    description: "The capture-to-run latency, collapse ratio and runs-per-minute figures exist as numbers in a committed artifact, not as prose"
    requirement: "DSAV-01"
    verification:
      - kind: integration
        ref: ".planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_dsav_live_loop.py#test_sc2_runs_per_minute_under_burst"
        status: pass
    human_judgment: false
  - id: D4
    description: "list_validation_runs returns without raising for a project containing captured, superseded, failed and shacl-verdicted completed rows"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_live_loop.py#test_list_runs_tolerates_auto_rows"
        status: pass
    human_judgment: false
  - id: D5
    description: "The watcher's Cypher shapes execute against live Neo4j 5.26 without error (39-RESEARCH.md A2)"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_live_loop.py#test_cypher_shapes_execute_on_live_neo4j"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-08's departure proven live: an unavailable sidecar leaves the row captured with attempts incrementing, and only the maxAttempts-th failure flips it to failed"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_live_loop.py#test_shacl_unavailable_leaves_row_captured_then_failed"
        status: pass
    human_judgment: false
  - id: D7
    description: "The investigation note comparing trigger architectures with latency/publish-flood/Speckle-noise analysis (DSAV-01)"
    verification: []
    human_judgment: true
    rationale: "This plan supplies the measured inputs the note cites; authoring the note itself is Plan 05's explicit scope. DSAV-01 stays open."

metrics:
  duration: ~60min
  completed: 2026-07-27
  tasks: 2
  files: 3

status: complete
---

# Phase 39 Plan 03: Live-Docker Loop Measurement Summary

**The DesignState auto-validation loop closed hands-off on live Docker in 2.679 s, collapsed 8 rapid captures into 1 run with 7 superseded, and held throughput at exactly its configured 3 runs/min under a 20-capture burst — all read off the rows themselves and committed as `39-EVIDENCE.json`.**

## Performance

- **Duration:** ~60 min
- **Completed:** 2026-07-27
- **Tasks:** 2 completed
- **Files modified:** 3 (2 new, 1 modified)

## The measured numbers

Every figure below was observed on live Docker. Nothing is estimated, extrapolated, or carried over from the plan's example values.

| Signal | Measured | Configuration that produced it |
|---|---|---|
| **SC1** capture → run latency | **2.679 s** (`capturedAt` 19:44:51.686809Z → `completedAt` 19:44:54.365992Z) | debounce 2.0 s, rate limit 30/min, poll interval 2.0 s, publish off |
| **SC2** collapse ratio | **8 captures in → 1 run out**, 7 `superseded` (burst spanned 0.12 s) | debounce 5.0 s, rate limit 3/min |
| **SC2** runs per minute | **3** completions in a 60.0 s window from **20** captures, against a configured limit of **3** | debounce 5.0 s, rate limit 3/min, 4-captures-then-8 s-idle cycles |
| **D-08** failure ladder | attempts `1 → 2 → 3`, statuses `captured → captured → failed`, `lastError: "unavailable"` | maxAttempts 3, injected unavailable sidecar |
| Cypher shapes | all **8** constants executed without error | Neo4j Kernel **5.26.28** (community) |
| `GET /validation/runs/p39-autoval` | **200**, 5 runs returned (1 captured, 2 superseded, 1 failed, 1 completed) | — |

The SC1 latency decomposes as: the 2.0 s debounce window, plus up to one 2.0 s poll interval of capture-to-next-tick phase offset, plus a ~1.5 s dg-reasoner SHACL round-trip. Three independent runs of the module produced 3.427 s, 2.801 s and 2.679 s — the spread is the poll-interval phase offset, exactly as predicted.

Phase 40 closing runbook decision D5: the ~1.5 s round-trip figure is an estimate that the two deliverables already refuse; the recorded totals 3.427 s, 2.801 s, and 2.679 s are the measured values.

## Accomplishments

- **`data-service/tests/test_dsav_live_loop.py`** — 6 integration-marked tests, the first and only Phase 39 code that runs against the real uvicorn process (whose `lifespan` owns the watcher daemon), real Neo4j, and the real `dg-reasoner` sidecar. Captures cross the same authenticated trust boundary a real connector does, using a freshly minted project-scoped credential that is revoked at teardown and never written anywhere.
- **`39-EVIDENCE.json`** — machine-readable, with a `configuration` block, a `software_context` block, one entry per scenario each carrying the parameters that produced it, a `missing_measurements` list (empty), and two derived `findings`.
- **39-RESEARCH.md assumption A2 discharged.** All eight watcher Cypher constants executed against live Neo4j 5.26.28. The load-bearing case — `COALESCE_QUERY` still returning its `keptRunId` row when exactly one captured row exists — passed, confirming P-09's `FOREACH`-over-`UNWIND` correction was necessary and correct.
- **Container brought in line with the host.** Rebuilt `data-service`; the lifespan path is confirmed live (the watcher's `ENABLED_PROJECTS_QUERY` fires every 2 s in the container logs) and `POST /designstate/capture` answers 401 rather than 404. Both tiers now collect **736**.

## Findings promoted for the DSAV-03 ADR

**F-39-01 — an auto-run is SHACL-validated before its own `ValidStatus` exists, so every auto-run currently self-violates.**
`poll_once` calls the sidecar and only *then* writes `ValidStatus` via `COMPLETE_QUERY`. At validation time the run node has no `ValidStatus`, which trips the shapes graph's own `RunStatusShape_valid`. That finding's `focusLabel` is the `runId`, which matches no objState, so P-02's conservative unmapped fallback flips **every** ObjState entry to `false`. Measured: `conforms: false`, one violation, `ValidStatus: [false, false]` for a 2-objState envelope.
*Consequence:* auto-run verdicts are structurally sound (they never claim a passing state they cannot attribute) but are **not yet discriminating** — they report all-false regardless of the design. Whether to reorder the ValidGraph export or scope the shapes graph is an open design question for the ADR; this investigation measures it rather than resolving it.

**F-39-02 — the rate limiter, not the debounce window, is what caps throughput under a sustained burst.**
20 captures produced 3 completions in the 60 s window against a configured limit of 3 — the limiter binds exactly. Captures arriving while it is saturated are skipped *before* coalesce, so their rows stay `captured` rather than being superseded or dropped (9 superseded, 8 left captured at window close). Throughput is capped without data loss, but a saturated project accumulates captured rows that existing readers already see, and the window resets on restart (D-15).

## Task Commits

1. **Task 1: live-Docker evidence driver** — `0fa6256` (test)
2. **Task 2: evidence artifact + run story** — `c716817` (docs)

_Plan metadata commit follows below._

## Files Created/Modified

- `data-service/tests/test_dsav_live_loop.py` — the 6-test driver plus the measurement accumulator, findings derivation and evidence writer
- `.planning/milestones/v9.0-phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json` — the committed measured artifact
- `data-service/tests/README.md` — Phase 39 additions: the three new modules, the `p39-autoval` reservation, the `dg-reasoner`/rebuild/restart prerequisites, and freshly measured both-tier counts

## Decisions Made

- **The runs-per-minute burst uses a cycle schedule, not a uniform 1 Hz stream.** See the deviation below — the literal reading would have measured zero.
- **Each measured scenario drains the rate-limit window first.** The limiter is in-process and shared across the whole module run: SC1's completion would otherwise still be inside SC2's 60 s window with a limit of 3, confounding both SC2 figures. The drain is derived from row `completedAt` timestamps, the only observable proxy for daemon state, and the seconds waited are recorded in the artifact.
- **The D-08 ladder parks the daemon rather than racing it.** Setting `debounceWindowSeconds` to 3600 pins the live watcher on `debounce_wait` while the test drives `poll_once` against the same live session with a `now` past that window. This keeps the config `enabled` (which `poll_once` requires) while guaranteeing determinism.
- **The evidence writer emits nothing when nothing was measured.** A file of nulls would be worse than no file for an artifact the ADR cites.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The runs-per-minute capture schedule would have measured 0**

- **Found during:** Task 1 (designing `test_sc2_runs_per_minute_under_burst`)
- **Issue:** The plan says to "post a capture roughly every second for the duration." Against the P-14 SC2 debounce of 5.0 s, a uniform 1 Hz stream re-arms the debounce window on every tick and it never lapses — `poll_once` reports `debounce_wait` for the entire minute and **zero** runs complete. The test would have passed its `<= rateLimitPerMinute` assertion with a measured 0, and the artifact would have recorded a runs-per-minute figure that reflected debounce starvation rather than the limiter the test exists to demonstrate. The plan's own sentence asks for the window to be "repeatedly re-armed **and then allowed to lapse**," which a uniform stream cannot do.
- **Fix:** a cycle schedule — 4 captures at 1 s intervals, then 8 s idle, repeated for 60 s (20 captures, 5 cycles). Each cycle re-arms the window and then lets it lapse, so a completion is *attempted* per cycle and the limiter is what caps the count. The exact schedule string is written into the artifact next to the number.
- **Files modified:** `data-service/tests/test_dsav_live_loop.py`
- **Verification:** measured 3 runs/min against a configured 3, from 20 captures — the limiter binding, with 5 completion opportunities and 2 rate-limited.
- **Committed in:** `0fa6256`

---

**2. [Rule 2 - Missing Critical] Rate-window drain between measured scenarios**

- **Found during:** Task 1
- **Issue:** The plan pins per-scenario guardrail parameters but does not address that the rate-limit window is **in-process and shared across the whole module run** (D-15). SC1's completion sits inside SC2's trailing 60 s window; with SC2's limit of 3, the collapse and runs-per-minute figures would both be silently confounded by earlier tests, and a re-run inside a minute would be worse still.
- **Fix:** `_wait_for_empty_rate_window()` — a bounded wait until no completion for the project falls inside the trailing `RATE_LIMIT_WINDOW_SECONDS`, run before each measured scenario and once at module setup (before the scrub, since surviving rows are the only proxy for daemon state). The seconds waited are recorded in the artifact.
- **Files modified:** `data-service/tests/test_dsav_live_loop.py`
- **Verification:** three consecutive module runs produced identical collapse and runs-per-minute figures.
- **Committed in:** `0fa6256`

---

**3. [Rule 3 - Blocking] The D-08 ladder needed the live daemon parked**

- **Found during:** Task 1
- **Issue:** The plan's preferred option is to "drive `dsav_watcher.poll_once` directly against the live session with a `shacl_fn` that returns the unavailable status dict." With the config enabled at normal parameters, the *real* daemon is polling the same rows every 2 s with the *real* sidecar and completes the row before the ladder can step it — the test would be nondeterministic at best. The plan's alternative (restarting the service with a dead `DG_REASONER_URL`) is not drivable from inside the container.
- **Fix:** the ladder test sets `debounceWindowSeconds` to 3600 so the daemon parks on `debounce_wait`, then calls `poll_once` with `now = time.time() + 7200` so its own call clears that window. The same parking keeps tests 5 and 6 deterministic.
- **Files modified:** `data-service/tests/test_dsav_live_loop.py`
- **Verification:** the observed sequence is exactly `1/captured, 2/captured, 3/failed` across three independent module runs.
- **Committed in:** `0fa6256`

---

**4. [Rule 2 - Missing Critical] Evidence writer guarded against a null artifact**

- **Found during:** Task 2
- **Issue:** The module-scoped writer fires at teardown unconditionally. On the host tier (where `neo4j` does not resolve) every test errors, no measurement is recorded, and the writer would still create an artifact of nulls — on Windows at `C:\app\data\dsav-evidence.json`, outside the repository. An artifact the ADR cites must never contain a number nobody observed.
- **Fix:** return without writing when the accumulator is empty.
- **Files modified:** `data-service/tests/test_dsav_live_loop.py`
- **Verification:** the host-tier run errors 6 tests and writes nothing; the container run writes the full artifact with `missing_measurements: []`.
- **Committed in:** `c716817`

---

**Total deviations:** 4 auto-fixed (1 bug, 2 missing critical, 1 blocking)
**Impact on plan:** every scenario the plan specified was measured; the changes are about making the numbers *mean* what the plan says they mean. No scope creep — file scope is exactly the three files the plan names.

## Issues Encountered

- **Wave 2's recorded host baseline is off by one.** It reports "698 passed, 4 failed, 25 errors"; the true baseline is **699 passed**, 4 failed, 1 skipped, 1 deselected, 25 errors. Confirmed by direct A/B without touching the working tree (`pytest --ignore=…/test_dsav_live_loop.py` gives 699/4/25; the full run gives 699/4/31, i.e. this plan's 6 host-tier errors and nothing else). No regression; the earlier figure was simply mis-transcribed.
- **The image had to be rebuilt three times** — once for the required lifespan prerequisite, then again after each edit to the test module, since `data-service/tests/` has no bind mount. Now documented prominently in the README's Phase 39 section.
- **`data-service/data/` is gitignored** (`.gitignore:4`), so the in-container artifact could not have been committed accidentally; only the explicit copy in the phase directory is tracked. Verified `git status --porcelain data-service/data/` is empty and the committed artifact contains no token prefix.

## Verification Evidence

| Check | Result |
|---|---|
| `docker compose exec -T data-service python -m pytest tests/test_dsav_live_loop.py -q -m integration` | **6 passed** in 190.82 s |
| `docker compose exec -T data-service test -s /app/data/dsav-evidence.json` | exit 0 |
| Plan's Task 2 verify command on `39-EVIDENCE.json` | `evidence ok 2.679 8 3` |
| `docker compose exec -T data-service python -m pytest tests/ -q` | **734 passed**, 1 skipped, 1 deselected (736 collected) |
| `python -m pytest data-service/tests/ -q` (host) | 699 passed, 4 failed, 1 skipped, 1 deselected, 31 errors (736 collected) — baseline + this plan's 6 expected integration errors |
| `grep -c "dgc_"` on the test module and the artifact | 0 and 0 |
| `git status --porcelain data-service/data/` | empty |

The committed artifact is from the dedicated module run that finished at 19:48:07 UTC (`measured_at`); the later full-suite run reproduced the same figures.

## User Setup Required

None. The compose stack (`neo4j`, `dg-reasoner`, `data-service`) was already running; `data-service` was rebuilt as part of this plan.

To re-measure: `docker compose build data-service && docker compose up -d data-service`, then `docker compose exec -T data-service python -m pytest tests/test_dsav_live_loop.py -q -m integration`. Restart `data-service` between consecutive measured runs so the in-memory rate window (D-15) starts empty.

## Next Phase Readiness

- **Plan 04** can rely on a proven-live loop: the only thing it changes is flipping `publishEnabled` for its single deliberate Speckle publish. `_auto_publish_run` has still never published a real Speckle version — that remains Plan 04's explicit scope, and every run in this plan was persist-only (`SendStatus: false`, `validationVersionId: null`, zero `:ValidationEntity` nodes) per T-39-04.
- **Plan 05** has the three numbers SC1 and SC2 demand, plus F-39-01 and F-39-02 to fold into the ADR. F-39-01 in particular is a design question the ADR must address rather than inherit silently.
- **DSAV-01 remains open** — this plan supplies the note's measured inputs; authoring the note is Plan 05's scope.
- No blockers for Plan 04.

---
*Phase: 39-designstate-auto-validation-investigation*
*Completed: 2026-07-27*

## Self-Check: PASSED

All claimed files exist on disk (`test_dsav_live_loop.py`, `39-EVIDENCE.json`, `39-03-SUMMARY.md`, `README.md`) and both task commits (`0fa6256`, `c716817`) are present in git history.
