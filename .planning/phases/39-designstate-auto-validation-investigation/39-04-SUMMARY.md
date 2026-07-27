---
phase: 39-designstate-auto-validation-investigation
plan: 04
subsystem: api
tags: [speckle, neo4j, shacl, docker, pytest, measurement, python, integration]

requires:
  - "39-01 (dsav_watcher.py: upsert_auto_validation_config, poll_once's publish branch)"
  - "39-02 (POST /designstate/capture, the lifespan-owned daemon, and _auto_publish_run)"
  - "39-03 (the live-Docker driver whose helpers, scrub discipline and evidence-accumulator pattern this module reuses)"
provides:
  - "test_dsav_publish_leg.py — the phase's single publishEnabled=true run, double-marked integration+live"
  - "39-EVIDENCE.json measurements.speckle_publish — the real measured D-11 Speckle data point (status: published)"
  - "Speckle version 2ab708e884 — the human-confirmed artifact discharging SC1's '(if enabled) publishes to Speckle' clause"
  - "F-39-03 — a routine suite run destroyed the phase's published run row; the live marker now prevents it"
affects: ["39-05 (DSAV-03 ADR + investigation note: the Speckle-noise column is measured, not estimated)"]

tech-stack:
  added: []
  patterns:
    - "Double-marked live module: `integration` for the compose network plus `live` for external/destructive side effects, so conftest.py's default deselection is the safety mechanism rather than developer discipline"
    - "Blocked-as-evidence: an unmeasurable measurement is written as {status: blocked, reason} and fails loudly, never omitted and never estimated (P-16 / T-39-12)"
    - "External-truth readback: the minted version is proven by diffing Speckle's own version list before/after, not by trusting the field this repo wrote to its own row"
    - "Unconditional flag teardown that asserts its own postcondition (zero AutoValidation config rows remain)"

key-files:
  created:
    - data-service/tests/test_dsav_publish_leg.py
  modified:
    - .planning/phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json
    - data-service/tests/test_dsav_live_loop.py
    - data-service/tests/README.md

key-decisions:
  - "The preflight probes the dev stack for a working Speckle configuration rather than requiring a provider:'Speckle' row on the fixture project specifically — p39-autoval is a synthetic string with no Speckle project of its own, so the literal probe would have recorded a false-negative `blocked` for a stack that demonstrably works (T-39-12 cuts both ways)"
  - "The published run row was NOT recreated by hand after a routine suite run deleted it, and the publish leg was NOT re-run — D-11 permits exactly one publish-enabled run, so the deletion is recorded as fact in the artifact"
  - "Operator authorized adding the `live` marker to test_dsav_live_loop.py (a Wave 3 file, outside this plan's declared file scope) to close the footgun"

requirements-completed: [DSAV-02]

coverage:
  - id: D1
    description: "One auto-run with publishEnabled true mints a real Speckle version and the row carries SendStatus true plus the Speckle identifier fields, written in place without calling store_validation_run (D-11)"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_publish_leg.py#test_publish_leg_mints_exactly_one_real_speckle_version"
        status: pass
    human_judgment: false
  - id: D2
    description: "The run completes before it publishes; the publish leg never moves the run off 'completed' (P-07 inverted ordering)"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_publish_leg.py#test_publish_leg_mints_exactly_one_real_speckle_version"
        status: pass
    human_judgment: false
  - id: D3
    description: "A human confirmed the Speckle version is visible in the viewer for the fixture project"
    requirement: "DSAV-02"
    verification:
      - kind: manual
        ref: "39-VALIDATION.md § Manual-Only Verifications — 'Single Speckle publish leg produced a real version'"
        status: pass
    human_judgment: true
    rationale: "No assertion in this repo can make this confirmation on the operator's behalf. Operator opened the Speckle URL and replied 'Approved — version is there'."
  - id: D4
    description: "The Speckle-noise data point in 39-EVIDENCE.json is a real measured version, not an estimate"
    requirement: "DSAV-01"
    verification:
      - kind: integration
        ref: ".planning/phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json#measurements.speckle_publish"
        status: pass
    human_judgment: false
  - id: D5
    description: "publishEnabled is reset off and the provider:'AutoValidation' row removed; zero such rows remain anywhere (T-39-11)"
    requirement: "DSAV-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_dsav_publish_leg.py#publish_flag_guard"
        status: pass
    human_judgment: false
  - id: D6
    description: "The investigation note comparing trigger architectures with latency/publish-flood/Speckle-noise analysis (DSAV-01)"
    verification: []
    human_judgment: true
    rationale: "This plan supplies the measured Speckle-noise input; authoring the note is Plan 05's explicit scope. DSAV-01 stays open."

metrics:
  duration: ~50min
  completed: 2026-07-27
  tasks: 2
  files: 4

status: complete
---

# Phase 39 Plan 04: The Single Speckle Publish Leg Summary

**One auto-validation run, with `publishEnabled` on for the only time in the phase, minted a real Speckle version — `2ab708e884`, human-confirmed in the viewer — turning the DSAV-01 Speckle-noise column from an estimate into a measured 1 version per capture, and the flag is off again with zero config rows left behind.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-27
- **Tasks:** 2 completed (1 auto, 1 blocking human-verify checkpoint — **passed**)
- **Files modified:** 4 (1 new, 3 modified)

## The measured data point

| Signal | Measured |
|---|---|
| `measurements.speckle_publish.status` | **`published`** — not blocked, not estimated |
| Speckle version minted | **`2ab708e884`** in project `44088eefc6`, model `a6d1e0c5da` (`dg-validation`) |
| Versions minted / captures issued | **1 / 1** → **1 Speckle version per capture** |
| Run | `0afe92c2e2324a85a988d42c4ffedc95`, `trigger: auto`, `verdictSource: shacl`, `SendStatus: true` |
| `capturedAt` → `completedAt` | 20:04:53.204Z → 20:04:57.503Z (4.30 s) |
| Speckle `created_at` | 20:04:58.470Z — **0.97 s after** `completedAt`, the P-07 ordering visible in wall-clock |
| `ValidStatus` | `[false, false]` — F-39-01, expected, not a defect |
| `ValidationEntity` count | **0** — the version is a state-level marker with an empty entity/rules payload |
| Direct Speckle URL | `http://localhost:8090/projects/44088eefc6/models/a6d1e0c5da@2ab708e884` |

**The emptiness is the finding.** A captured DesignState envelope carries no per-entity geometry and no `failedRuleIds`, so `_auto_publish_run` sends `rules=[]` and `entities=[]` by construction. With the flag on, every capture that survives debounce and the rate limiter appends one near-empty commit to the project's `dg-validation` model. That is the Speckle-noise characteristic DSAV-01 needs, and it is now measured rather than reasoned about.

**The version is proven externally, not self-reported.** The test diffs Speckle's own version list before and after the run and asserts the delta is exactly one and equal to the id on the row. A field this repo wrote to its own node would not have been evidence.

**P-07's inverted ordering was observed, not assumed.** At the instant the run reached `completed` it still carried the persist-only defaults (`sendStatus: false`, `validationVersionId: null`) — captured in the artifact as `verdict_state_before_publish`. The test then polls for the version id while asserting on *every* poll that the status is still `completed` and `completedAt` is unchanged. A Speckle failure would have left the run completed rather than reverting the verdict.

## The human-verify gate: PASSED

The operator's reply, verbatim:

> **1. Speckle version verification: APPROVED — "Approved — version is there".**
>
> The operator opened the Speckle URL and confirmed version `2ab708e884` exists for the fixture project with the expected ~2026-07-27 20:04:58 UTC timestamp and an empty state-level payload.
>
> **2. Deleted run row / test-isolation decision: option (b) — ADD THE `live` MARKER.**
>
> The operator chose: "Add the `live` marker — Mark test_dsav_live_loop.py as `live` so a routine suite run no longer collects it and can't scrub phase evidence." This is explicitly authorized despite being outside plan 39-04's declared `files_modified`, and is to be folded in before Plan 05 runs.

This discharges the **"Single Speckle publish leg produced a real version"** row in `39-VALIDATION.md` § Manual-Only Verifications.

## F-39-03 — a routine suite run destroyed the phase's published run row

Recorded in the artifact as `measurements.speckle_publish.row_lifecycle`.

`test_dsav_live_loop.py`'s `live_session` fixture `DETACH DELETE`s every `:ValidationRun` and `:IntegrationConfig` scoped to `p39-autoval`, at **both** setup and teardown. The module was `integration`-marked but not `live`-marked, so a bare in-container `pytest tests/ -q` collected it. That bare run was executed ~4 minutes after the publish leg — as the acceptance check that the publish leg is *not* collected by default — and it silently deleted the published run row.

Immediately after the leg the acceptance criterion held:

```
SendStatus=true runs for p39-autoval: 1
{'runId': '0afe92c2...', 'status': 'completed', 'trigger': 'auto',
 'verdictSource': 'shacl', 'sendStatus': True, 'vvid': '2ab708e884'}
```

Now it reads `0`. **The row was not recreated by hand and the leg was not re-run** — D-11 permits exactly one publish-enabled run in the phase, and a re-run would mint a second Speckle version. The deletion is reported rather than repaired, and the artifact records both the pre- and post-deletion observations so a later reader cannot be misled by a `speckle_publish` block describing a row that no longer exists.

**The Speckle-side proof is durable and independent**, which is why this is a recoverable annoyance rather than lost evidence: version `2ab708e884` carries message `DG validation run 0afe92c2e2324a85a988d42c4ffedc95` and `created_at` 2026-07-27T20:04:58.470Z, and the operator has now seen it with their own eyes.

The plan's Task 2 step 5 also expected "the burst rows from Plan 03 still visible as `superseded`". They were already gone before this plan started: Wave 3's own module teardown scrubs them when that plan finishes. Nothing this plan did removed them.

## Task Commits

1. **Task 1: the publish leg + evidence merge** — `a7b347c` (test)
2. **Task 1b: record the row deletion in the artifact** — `171504d` (docs)
3. **Task A (operator-authorized): `live`-mark the Wave 3 driver** — `c37a8bc` (test)

_Plan metadata commit follows below._

## Files Created/Modified

- `data-service/tests/test_dsav_publish_leg.py` — **new.** One test, double-marked `integration` + `live`, with the P-16 preflight, the unconditional flag teardown, and the external version-delta readback.
- `.planning/phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json` — `measurements.speckle_publish` merged in **additively**: `git diff --numstat` reported `50 0`, then `16 0` — **zero deletions across both commits**, so all six Wave 3 measurements are preserved byte-for-byte.
- `data-service/tests/test_dsav_live_loop.py` — operator-authorized `live` marker.
- `data-service/tests/README.md` — the publish-leg run story, the `-m live` corollary warning, and the corrected collection counts.

## Decisions Made

- **The preflight probes the dev stack, not the fixture project.** See the deviation below — the literal probe would have produced a false negative.
- **The blocked branch is a written outcome, not a skip.** `_record_blocked` writes `{status: "blocked", reason, detail}` into the evidence file and *then* `pytest.fail`s with the reason in the message. Both P-16 blockers are probed (`speckle_token_missing`, `speckle_config_missing`), and the config probe additionally proves the Speckle project and base model are readable with the write token before anything is enabled — an unreachable Speckle is a blocker to be discovered up front, not a publish failure to be discovered halfway through.
- **A separate evidence file.** The module writes `/app/data/dsav-publish-evidence.json`, never Wave 3's `dsav-evidence.json`, so it is structurally incapable of overwriting the earlier measurements. The executor merged one key across by script with an assertion that every prior key survived.
- **Teardown asserts its own postcondition.** The guard fixture resets `publishEnabled`, deletes both `IntegrationConfig` rows for the fixture project, then asserts zero `provider:'AutoValidation'` rows remain — T-39-11 is enforced by the test, not just performed by it.
- **Scrub at setup only.** Unlike the Wave 3 driver, this module does not scrub at teardown: the published row is the plan's evidence and the acceptance criteria are checked against the database after the module exits.

## Deviations from Plan

### 1. [Rule 3 - Blocking] The preflight probes the dev stack for Speckle config, not the fixture project specifically

- **Found during:** Task 1, writing the P-16 preflight
- **Issue:** The plan says to "confirm a `provider:'Speckle'` `IntegrationConfig` row exists **for the fixture project**". `p39-autoval` is a synthetic project string reserved by this phase (P-03) that has never had a Speckle project of its own, and the Wave 3 driver's scrub deletes every `IntegrationConfig` scoped to it. The literal probe was therefore guaranteed to report `speckle_config_missing` — recording `blocked` for a stack that demonstrably **does** have working Speckle write configuration. T-39-12 cuts both ways: a false-negative `blocked` misrepresents the environment exactly as badly as a fabricated number, and it would have wrongly pushed Plan 05 onto the estimate path. D-11's actual requirement is "a working Speckle config **in the dev stack**".
- **Fix:** the preflight (a) requires a non-empty write token, (b) uses the fixture project's own `provider:'Speckle'` row when one exists, else **discovers** a donor row from the live database, (c) proves the Speckle project and base model readable with the write token, and only then (d) points the fixture project at that same real Speckle project. Nothing is invented — every identifier comes out of Neo4j or Speckle, and `speckle_config_source` in the artifact records which path was taken and which donor was used.
- **Files modified:** `data-service/tests/test_dsav_publish_leg.py`
- **Verification:** status `published`, version `2ab708e884` read back from Speckle's own version list.
- **Committed in:** `a7b347c`

**Cosmetic note, deliberately not fixed:** the donor picked by alphabetical order was DG project `nonexistent-project-xyz`, an unfortunately-named leftover. All three candidate rows point at the **identical** Speckle project `44088eefc6` and models, so the recorded identifiers are the same whichever was chosen. Re-running to get a prettier donor name would mint a second Speckle version and break D-11, so it was not done.

---

### 2. [Rule 2 - Missing Critical] The artifact recorded a run row that no longer existed

- **Found during:** Task 2 verification
- **Issue:** After the committed artifact was written, a routine suite run deleted the published `:ValidationRun` (F-39-03 above). A reader of `measurements.speckle_publish` would have found a `run_id`, `send_status: true` and a `completed_at` for a node that returns nothing from Neo4j, with no explanation.
- **Fix:** added `measurements.speckle_publish.row_lifecycle` recording the pre- and post-deletion observations, the deleting fixture by file and line, the mechanism, and an explicit statement that the row was not recreated and the leg not re-run.
- **Files modified:** `.planning/phases/39-designstate-auto-validation-investigation/39-EVIDENCE.json`
- **Verification:** `git diff --numstat` → `16 0`, additive only.
- **Committed in:** `171504d`

---

### 3. [Operator-authorized] `live`-marking `test_dsav_live_loop.py` — outside the declared file scope

- **Found during:** Task 2 checkpoint; **decided by the operator**, not auto-applied
- **Issue:** the footgun in F-39-03 — an `integration`-only module that scrubs shared live rows is collected by every routine suite run.
- **Why it needed authorization:** `test_dsav_live_loop.py` is a Wave 3 artifact and is not in this plan's `files_modified`. It was surfaced at the checkpoint as option (b) rather than applied unilaterally; the operator chose it explicitly.
- **Fix:** `pytestmark = [pytest.mark.integration, pytest.mark.live]`, matching `test_dsav_publish_leg.py` so both live modules behave identically under `-m "integration and live"`, plus docstring and README updates explaining why.
- **Files modified:** `data-service/tests/test_dsav_live_loop.py`, `data-service/tests/README.md`
- **Verification — the collection change is the point, so both numbers are reported:**

  | Run | Before | After |
  |---|---|---|
  | Container, bare `pytest tests/ -q` | 734 passed, 1 skipped, **2** deselected, 206.17s | **728** passed, 1 skipped, **8** deselected, **8.88s** |
  | Container, `-m "integration and live"` on the module | 6 passed, 190.82s (Wave 3) | **6 passed**, 192.74s |
  | Host, `pytest data-service/tests/ -q` | 699 passed, 4 failed, 1 skipped, 1 deselected, **31** errors | 699 passed, 4 failed, 1 skipped, **8** deselected, **25** errors |

  The 6-test drop in the default container run is the six moved tests and nothing else; they still pass when selected. On the host the 6 extra `neo4j`-DNS errors became deselections, returning that tier to the exact documented baseline of **699 passed / 4 failed / 25 errors**. The 23× speedup of the bare container run is a side benefit — those six were nearly all of its wall-clock.
- **Committed in:** `c37a8bc`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical) + 1 operator-authorized scope extension
**Impact on plan:** every acceptance criterion the plan set was met at the time of measurement; one (the `SendStatus = true` count) was subsequently invalidated by an unrelated suite run and is reported rather than repaired.

## Issues Encountered

- **The published run row is gone from Neo4j** (F-39-03). Reported, not repaired. The Speckle-side evidence is durable and human-confirmed.
- **`git checkout`/`stash`/`clean` were never used**, per the standing prohibition — the repo's many pre-existing uncommitted `DG/**/bin/`, `DG/**/obj/` artifacts were left untouched throughout, and no stash was created.
- **`39-PRE-DECISIONS.md` remains untracked** in the phase directory. It predates this plan and is not in its file scope, so it was left alone.

## Verification Evidence

| Check | Result |
|---|---|
| `docker compose exec -T data-service python -m pytest tests/test_dsav_publish_leg.py -q -m "integration and live"` | **1 passed** in 7.32s |
| `… pytest tests/test_dsav_publish_leg.py -q --collect-only` (no `-m`) | **no tests collected (1 deselected)** — P-15 holds |
| `measurements.speckle_publish.status` | `published`, `validation_version_id` `2ab708e884`, `versions_minted` 1 |
| Speckle version list read back independently | `2ab708e884` newest, created 2026-07-27T20:04:58.470Z, message `DG validation run 0afe92c2…` |
| Wave 3 measurements still in the artifact | all 6 present (`sc1_loop_closure`, `sc2_collapse`, `sc2_runs_per_minute`, `d08_failure_ladder`, `list_runs_tolerance`, `cypher_shapes`); `git diff --numstat` `50 0` then `16 0` |
| `MATCH (cfg:IntegrationConfig {provider:'AutoValidation', project:'p39-autoval'}) RETURN count(cfg)` | **0** |
| Same query without the project filter (anywhere in the DB) | **0** |
| `MATCH (cfg:IntegrationConfig {project:'p39-autoval'}) RETURN count(cfg)` | **0** — the provisioned Speckle row was cleaned up too |
| `SendStatus = true` rows for `p39-autoval` | **1** immediately after the leg; **0** now (F-39-03) |
| `grep -c "dgc_"` on the test module and the artifact | **0** and **0** |
| Token-shaped literal scan on both files | **0** |
| `git status --porcelain data-service/data/` | empty (gitignored) |
| Deletions in the Task 1 commit | **0** |
| No second Speckle version minted by the Wave 3 re-run | confirmed — `2ab708e884` still newest |

## User Setup Required

None. The compose stack was already running; `data-service` was rebuilt twice (once for the new test module, once for the `live` marker) because `data-service/tests/` has no bind mount.

**Standing warning:** `test_dsav_publish_leg.py` writes to a real Speckle server. A bare `pytest` cannot collect it, but a broad `-m live` (e.g. for the recognition eval) **can**. Select it by path when you mean it. Documented in `data-service/tests/README.md`.

## Next Phase Readiness

- **Plan 05 has a measured Speckle-noise data point**, not an estimate: 1 near-empty version per capture that survives debounce and the rate limiter. The DSAV-01 comparison table can state it as observed fact with a version id behind it, and the `accept-estimate` path is moot — it was never taken.
- **F-39-03 is available to the ADR** alongside F-39-01 and F-39-02, if the ADR wants to note that live-mutating test modules need the `live` marker as a matter of convention. That is optional; the fix is already applied.
- **The environment is clean:** auto-validation disabled, zero `AutoValidation` config rows anywhere, `publishEnabled` off.
- **DSAV-01 remains open** — authoring the investigation note is Plan 05's scope.
- No blockers for Plan 05.

---
*Phase: 39-designstate-auto-validation-investigation*
*Completed: 2026-07-27*
