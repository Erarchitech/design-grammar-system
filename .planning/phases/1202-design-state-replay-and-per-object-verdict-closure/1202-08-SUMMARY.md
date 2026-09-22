---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 08
subsystem: database
tags: [de01, canonical-hash, cross-language-parity, csharp, python, gap-closure]

# Dependency graph
requires:
  - phase: 1202-02
    provides: "DesignStateCanonicalProjection (C#) and design_state_projection.py (Python) canonical projections, plus mixed-verdicts.json's original (now superseded) expectedCanonicalStateHash"
  - phase: 1202-03
    provides: "ClassIri added to ObjStateDto and wired through both DesignStatePayloadV2Serializer mapping directions (D-05), which this plan confirmed live"
  - phase: 1202-07
    provides: "The first genuine four-leg DE-01 live run and its retained not_applicable state-hash evidence, the exact baseline this plan supersedes"
provides:
  - "A --replay-fixture CLI shorthand on run_de01.py selecting fixtures/golden/replay/mixed-verdicts.json as a complete, live-runnable DE-01 fixture (additive rule/atoms/objects/expectedOutcomes keys)"
  - "fixtures/golden/replay/seed-replay.cypher seeding the DG-1202-REPLAY project with a round-trippable statePayloadJson"
  - "DG.De01Harness emitting a canonical DesignState hash wrapper alongside its evidence envelope, giving the csharp leg a genuine second, independent hash source"
  - "A live DE-01 run reporting Agreement: agree with silent_disagreement_count 0, retained as the new de01-evidence/ baseline"
  - "A fixed get_validation_run Cypher query (data-service/app.py) that actually returns statePayloadJson, closing a real pre-existing bug where the view endpoint's canonicalStateHash was always null"
affects: [1202-verification, phase-1202-signoff, future-de01-live-runs]

# Tech tracking
tech-stack:
  added: []
  patterns: ["wrapper-with-sentinel-key stdout shape for backward-compatible harness output", "publish-before-read leg ordering hazard in run_de01.py (data-service always shadows a seeded run)"]

key-files:
  created:
    - fixtures/golden/replay/seed-replay.cypher
    - .planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/README.md
  modified:
    - fixtures/golden/replay/mixed-verdicts.json
    - fixtures/golden/replay/README.md
    - tools/de01/run_de01.py
    - tools/de01/legs.py
    - tools/de01/tests/test_de01_runner.py
    - DG/tools/DG.De01Harness/Program.cs
    - data-service/app.py
    - .planning/REQUIREMENTS.md
    - .planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.json
    - .planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.md

key-decisions:
  - "Kept the csharp/replay agree hash (69D4289C...) as the retained evidence's canonical outcome rather than forcing agreement with the fixture's stale expectedCanonicalStateHash (3D2D5EDF...) -- the stale value was computed via a parse_float=Decimal path neither leg's double-typed Design State model can reach in production, so matching it would have required diverging the two live legs from each other"
  - "Tried and reverted a parse_float=Decimal fix to data-service's _compute_canonical_state_hash after discovering it broke cross-language agreement -- documented the full investigation in the function's own docstring rather than silently dropping the finding"
  - "run_leg_data_service now forwards fixture.get('statePayloadJson') to /validation/publish instead of a hardcoded None, because that leg's own publish always runs before run_leg_replay's bare GET (which resolves to newest-by-createdAt) within one invocation -- without this, the data-service leg's own fresh hash-less publish permanently shadows any seeded evidence"
  - "seed-replay.cypher's raw :Run/Run_Id node (mirroring seed.cypher's own precedent) is retained but is NOT the live hash path -- /validation/view/* reads :ValidationRun/runId only (documented label drift); the seed remains useful for direct Cypher inspection and dg-reasoner's run_id-addressed SHACL call"

patterns-established:
  - "Wrapper stdout shape {envelope, canonicalStateHash, canonicalizationVersion} with 'envelope' as the reader's sentinel key, keeping the bare-envelope shape byte-compatible for un-rebuilt harness binaries"

requirements-completed: [ALGN12-09, ALGN12-11]

coverage:
  - id: D1
    description: "A live DE-01 run exercises a real, round-trippable Design State end-to-end and reports Agreement: agree (not not_applicable), with csharp and replay legs both Present: True reporting the same 64-char hash"
    requirement: "ALGN12-09"
    verification:
      - kind: other
        ref: "python tools/de01/run_de01.py --replay-fixture -- exit 0, silent_disagreement_count=0, canonical state hash agreement=agree, available legs=[data-service, dg-reasoner, csharp, replay]"
        status: pass
      - kind: other
        ref: "python -c \"import json,jsonschema; jsonschema.validate(json.load(open('.de01/de01-report.json')), json.load(open('tools/de01/report_schema.json')))\" -- report schema OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "run_de01.py accepts fixtures/golden/replay/mixed-verdicts.json as a selectable live input via --replay-fixture without repointing or mutating the frozen default fixture.json"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py::TestReplayFixtureFlag (6 tests) -- 63/63 passing under -k \"not live\", up from 50-test baseline"
        status: pass
      - kind: other
        ref: "git diff --numstat fixtures/golden/fixture.json fixtures/golden/seed.cypher fixtures/golden/canonical-vectors.json -- empty output, frozen trio byte-untouched"
        status: pass
    human_judgment: false
  - id: D3
    description: "The C# leg computes and reports a canonical DesignState hash via DesignStateCanonicalProjection.ComputeHash, giving compare_state_hashes a second independent hash source"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py::TestRunLegCsharpWrapperExtraction (6 tests, including test_wrapper_csharp_round_trip_populates_state_hash_and_valid_envelope and test_bare_envelope_csharp_round_trip_still_works) -- all passing"
        status: pass
      - kind: other
        ref: "dotnet build DG/tools/DG.De01Harness/DG.De01Harness.csproj -c Release -- 0 errors, 0 warnings; dotnet test DG/tests/DG.Tests/ -v minimal -- 543/543 passing"
        status: pass
    human_judgment: false
  - id: D4
    description: "ALGN12-11's REQUIREMENTS.md checkbox reads [x], matching the verified-on-disk ON CREATE SET/SET split implementation"
    requirement: "ALGN12-11"
    verification:
      - kind: other
        ref: "grep -c '^- \\[x\\] \\*\\*ALGN12-11\\*\\*' .planning/REQUIREMENTS.md == 1; scoped 1-insertion/1-deletion diff, no other checkbox touched"
        status: pass
    human_judgment: false

duration: ~2h30min (incl. Docker rebuilds and live investigation)
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 08: Live DE-01 Replay and Cross-Language Canonical Hash Agreement Summary

**A live DE-01 run now reports `Agreement: agree` (not `not_applicable`) with two independent legs — C# and Python — computing the identical canonical DesignState hash `69D4289C722DE31B42D57E5F3C41BAB39272BE7DAC8957870512EC86C0707A84`, closing VERIFICATION.md gap 1 by fixing a real cross-service bug found live rather than only wiring a new fixture path.**

## Performance

- **Duration:** ~2h30min (includes two Docker Desktop `--no-cache` rebuild cycles and a live investigation that found and fixed a genuine pre-existing bug)
- **Tasks:** 4/4 completed (Tasks 1-3 auto, Task 4 checkpoint — Docker Desktop was available throughout, so the checkpoint ran to completion rather than pausing)
- **Files modified:** 10 (2 new, 8 modified)

## Accomplishments

- **Task 1:** `fixtures/golden/replay/mixed-verdicts.json` gained additive `rule`/`atoms`/`objects`/`expectedOutcomes` keys (copied by value from `fixture.json`), making it a complete DE-01 fixture. New `fixtures/golden/replay/seed-replay.cypher` seeds the `DG-1202-REPLAY` project with the round-trippable `statePayloadJson`. `run_de01.py` gained `--replay-fixture` as a documented shorthand; the `--fixture` default stayed the frozen `fixture.json`. Offline tests: 50 → 57 passing under `-k "not live"`.
- **Task 2:** `DG.De01Harness` (`Program.cs`) now emits a `{envelope, canonicalStateHash, canonicalizationVersion}` wrapper when the fixture supplies a top-level `statePayloadJson`, computed via `DesignStateCanonicalProjection.ComputeHash`; the bare envelope shape is preserved byte-identically for fixtures without one (including the frozen `fixture.json`). `run_leg_csharp` (`tools/de01/legs.py`) detects the wrapper via its `envelope` sentinel key and extracts only that sub-object for schema validation. Offline tests: 57 → 63 passing.
- **Task 3:** `.planning/REQUIREMENTS.md`'s stale `ALGN12-11` checkbox reconciled to `[x]` — a scoped, one-line edit; the separate `ALGN12-09` premature-check observation (below) recorded rather than silently altered.
- **Task 4 (checkpoint):** Docker Desktop was up throughout, so the live run proceeded to completion. What started as "just seed the project and run the command" surfaced a genuine pre-existing bug in `data-service/app.py`'s `get_validation_run` (its Cypher `RETURN` clause never selected `statePayloadJson`, so the view endpoint's `canonicalStateHash` was always `null` regardless of what was actually stored — this affected every project, not just the replay one, and is the real reason the golden project's own retained evidence was `not_applicable` too). Fixed the query, fixed a leg-ordering shadow bug in `run_leg_data_service`, tried and correctly reverted an over-fix (`parse_float=Decimal`) that would have broken cross-language agreement to chase a stale fixture value instead. Final live run: `Agreement: agree`, `silent_disagreement_count: 0`, exit 0, all four legs `available: True`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Seed the replay project and make mixed-verdicts.json a selectable live DE-01 input** - `922afea` (feat)
2. **Task 2: Give the C# leg a canonical state hash for cross-language agreement** - `b624de9` (feat)
3. **Task 3: Reconcile the ALGN12-11 REQUIREMENTS.md checkbox** - `09a520b` (docs)
4. **Task 4: Live DE-01 replay run as gap-1 exit evidence (checkpoint)** - `3e9c842` (feat)

_Sequential-mode execution: this executor owns STATE.md/ROADMAP.md updates itself (no worktree isolation for this run), per the orchestrator's explicit instruction._

## Files Created/Modified

- `fixtures/golden/replay/seed-replay.cypher` - New. Seeds `DG-1202-REPLAY` with the round-trippable `:DesignState.statePayloadJson`; never touches `DG-1200-GOLDEN`. Retained for direct Cypher inspection and `dg-reasoner`'s `run_id`-addressed SHACL call, but is NOT the live hash path (see Deviations).
- `fixtures/golden/replay/mixed-verdicts.json` - Additive `rule`/`atoms`/`objects`/`expectedOutcomes` keys (Task 1); `expectedCanonicalStateHashNote` rewritten (Task 4) to record the measured cross-language finding, superseding its stale ClassIri premise. `expectedCanonicalStateHash`'s VALUE unchanged throughout.
- `fixtures/golden/replay/README.md` - New section documenting the seed/run sequence.
- `tools/de01/run_de01.py` - New `--replay-fixture` flag; `--fixture` default unchanged.
- `tools/de01/legs.py` - `run_leg_csharp` wrapper-extraction branch (Task 2); `run_leg_data_service`'s publish body now forwards `fixture.get("statePayloadJson")` instead of a hardcoded `None` (Task 4).
- `tools/de01/tests/test_de01_runner.py` - 13 new offline tests across `TestReplayFixtureFlag` and `TestRunLegCsharpWrapperExtraction`.
- `DG/tools/DG.De01Harness/Program.cs` - Wrapper stdout shape, `TryComputeCanonicalStateHash` helper with typed-absence degradation.
- `data-service/app.py` - `get_validation_run`'s Cypher `RETURN` clause now selects `statePayloadJson` (real bug fix); `_compute_canonical_state_hash`'s docstring records the tried-and-reverted `parse_float=Decimal` investigation.
- `.planning/REQUIREMENTS.md` - `ALGN12-11` checkbox `[x]`.
- `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.json`/`.md` - Refreshed from the final live run.
- `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/README.md` - New. Records the command, fixture, date, verdict, and full investigation trail.

## Decisions Made

- **Kept `agree` at `69D4289C...` over forcing a match to the fixture's stored `expectedCanonicalStateHash` (`3D2D5EDF...`).** Both values are legitimate outputs of legitimate parse strategies, but only one (`69D4289C...`, the scale-0 "double path") is reachable by *both* legs' actual production code — the C# leg's `NumberValue` is `double`-typed and the Python `design_state_projection.py`'s own `_build_parameter_value` deliberately mirrors that scale-0 collapse. The stored `3D2D5EDF...` value was computed via a `parse_float=Decimal` invocation neither leg's real model can reach. Cross-language agreement between the two live legs is what DE-01 exists to prove — matching a value neither leg can naturally produce would have been the wrong target.
- **Tried, then reverted, `parse_float=Decimal` in `_compute_canonical_state_hash`.** This is documented rather than silently dropped: the function's own docstring in `data-service/app.py` now records why the fix was attempted and why it was wrong, so a future reader doesn't rediscover the same dead end.
- **`run_leg_data_service` now carries the fixture's real `statePayloadJson` through to its own publish call.** This was necessary because that leg's publish always runs before `run_leg_replay`'s bare `GET /validation/view/{project}` (resolves to newest run by `createdAt`) within a single `run_de01.py` invocation — without this change, the data-service leg's own fresh hash-less publish permanently shadowed the seeded evidence, structurally reproducing gap 1 on every run regardless of seeding. This leg's own reported canonical statuses are unaffected; only the forwarded sidecar payload changed. For the frozen `fixture.json` (no top-level `statePayloadJson` key), this is a byte-identical no-op.
- **`ALGN12-09` premature-checkbox observation (Task 3, carried forward for phase signoff):** `ALGN12-09` is marked `[x]` in `.planning/REQUIREMENTS.md`, but `1202-VERIFICATION.md` records it as PARTIALLY SATISFIED — it is the target of both this plan and 1202-09 (which closed VERIFICATION.md gap 2). This plan closes gap 1. Whether the checkbox was prematurely checked, or is now genuinely satisfied given both gap-closure plans, is a phase-signoff question left for re-verification with both plans in view — not resolved here per Task 3's explicit instruction not to alter that checkbox in this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `get_validation_run`'s Cypher query never selected `statePayloadJson`**
- **Found during:** Task 4 (live checkpoint run, investigating why `replay` stayed `Present: False` after a correctly-seeded, correctly-round-trippable payload)
- **Issue:** `data-service/app.py`'s `get_validation_run` `RETURN` clause omitted `run.statePayloadJson`, so `build_view_payload`'s `_compute_canonical_state_hash(run.get("statePayloadJson"))` always received `None` regardless of what was actually persisted on the matched `:ValidationRun` node. This affected every project's view endpoint, not only the replay fixture's — it is the real, structural reason the golden project's own historical evidence was `not_applicable` too, independent of any fixture shape issue.
- **Fix:** Added `run.statePayloadJson AS statePayloadJson` to the `RETURN` clause.
- **Files modified:** `data-service/app.py`
- **Verification:** Live: `curl /validation/view/DG-1202-REPLAY` returned a real 64-char `canonicalStateHash` after the fix, `None` before it, against the identical stored node.
- **Committed in:** `3e9c842` (Task 4 commit)

**2. [Rule 1 - Bug, then reverted after further investigation] `_compute_canonical_state_hash`'s float-scale collapse**
- **Found during:** Task 4, immediately after fix #1, when `replay`'s new hash disagreed with `csharp`'s
- **Issue:** Investigated whether `_compute_canonical_state_hash`'s plain `json.loads` (which decodes JSON numbers to Python `float`, later collapsed to scale-0 `Decimal`) was losing precision relative to the fixture's stored `expectedCanonicalStateHash`. Recomputing with `parse_float=Decimal` did reproduce the stored value — but this diverged from the `csharp` leg's independently-computed hash, which is `double`-typed on the C# side and structurally cannot preserve decimal scale either.
- **Fix:** Applied `parse_float=Decimal`, rebuilt, confirmed it broke `csharp`/`replay` agreement (verdict flipped from `agree` to `disagree` against the wrong pairing), then reverted to plain `json.loads`, restoring `csharp`/`replay` agreement. The investigation and its conclusion are recorded in the function's docstring rather than being silently dropped.
- **Files modified:** `data-service/app.py`
- **Verification:** Live re-run after revert: `Agreement: agree`, both legs report `69D4289C...`.
- **Committed in:** `3e9c842` (Task 4 commit, net change is the docstring only — behavior is unchanged from before the investigation)

**3. [Rule 1 - Bug] `run_leg_data_service` shadowing any seeded evidence**
- **Found during:** Task 4, after fix #1, still seeing `replay: Present: False` on a full `run_de01.py --replay-fixture` run despite a direct `curl` publish proving the view endpoint now worked
- **Issue:** `run_leg_data_service`'s own `/validation/publish` call (hardcoded `statePayloadJson: None`) always runs before `run_leg_replay`'s bare `GET /validation/view/{project}` (no `runId` — resolves to newest run by `createdAt`) within one invocation. That fresh, hash-less publish became the newest run every time, permanently shadowing any previously-seeded or previously-published hash-bearing run — a structural race that would have reproduced gap 1 on every future invocation regardless of how carefully the project was seeded beforehand.
- **Fix:** `run_leg_data_service` now passes `fixture.get("statePayloadJson")` instead of a hardcoded `None`. No-op for the frozen `fixture.json` (no top-level key); for `mixed-verdicts.json`, its own real payload is now what gets published, so `run_leg_replay`'s later read sees the correct data.
- **Files modified:** `tools/de01/legs.py`
- **Verification:** Live: full `run_de01.py --replay-fixture` (all four legs, in the plan's exact leg order) reports `Agreement: agree`, `replay: Present: True`.
- **Committed in:** `3e9c842` (Task 4 commit)

**4. [Auxiliary, non-code] Stash-recovery episode**
- **Found during:** Between fix attempts #2 and #3, a `git stash`/`git stash pop` cycle (used to A/B test the `parse_float=Decimal` revert against a clean baseline) partially failed on unrelated untracked-directory conflicts (`graphify-out/`, `scratchpad/`), silently dropping the working-tree edits to `data-service/app.py`, `tools/de01/legs.py`, and `fixtures/golden/replay/mixed-verdicts.json` from the working tree (though preserved in the stash object itself).
- **Fix:** Recovered via `git checkout stash@{0} -- <exact paths>` (bypassing the conflicting untracked directories), verified every file's content byte-for-byte against what was intended before dropping the stash.
- **Files affected:** No permanent effect — recovery was verified complete before the stash was dropped.
- **Verification:** Grep/diff checks on all three files confirmed identical content to pre-stash state; full offline test suite (63/63) and a final live run (`agree`, exit 0) re-confirmed after recovery.

---

**Total deviations:** 4 (3 code-level Rule-1 fixes, 1 auxiliary git-recovery episode). All three code fixes were necessary for the plan's own stated goal (a live, non-`not_applicable` agreement verdict) to be reachable at all — none were scope creep. Fix #2 is net-zero behavior change (tried, measured wrong, reverted) but is documented rather than silently discarded, per the plan's own "declared, not silent" governing principle.

## Issues Encountered

Two Docker Desktop `--no-cache` rebuild cycles were required (one after each code fix to `data-service/app.py`) — `data-service` has no source volume mount, so each fix needed a full rebuild + `docker compose up -d data-service` + in-container marker grep before the next live run, per the project's documented "stale Docker images mask code state" gotcha. Each rebuild took ~10-45s; no blockers.

## Next Phase Readiness

- VERIFICATION.md gap 1 is closed: a live DE-01 run against the seeded `DG-1202-REPLAY` project reports `Agreement: agree` with two independent legs (C#, Python) computing the identical canonical hash from the same real, round-trippable Design State — the retained `de01-evidence/` report pair reflects this.
- `ALGN12-11`'s checkbox now matches its verified-on-disk state.
- The `ALGN12-09` premature-check observation (checkbox `[x]` vs. `1202-VERIFICATION.md`'s PARTIALLY SATISFIED classification) is carried forward for phase-level re-verification with both this plan and 1202-09 in view.
- The real bug fixed in `data-service/app.py`'s `get_validation_run` (missing `statePayloadJson` in the `RETURN` clause) benefits every project's `/validation/view/*` route going forward, not only the replay fixture — worth noting for phase signoff as a genuine production-code improvement discovered via live evidence-gathering, exactly as D-16 anticipates ("unit tests alone are not sufficient exit evidence").

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*
