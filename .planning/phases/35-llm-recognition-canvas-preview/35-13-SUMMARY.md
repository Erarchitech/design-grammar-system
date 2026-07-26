---
phase: 35-llm-recognition-canvas-preview
plan: 13
subsystem: recognition-eval
tags: [eval-harness, cassette-record-replay, ablation-arms, sc1-gate, pytest, stdlib-only]

requires:
  - phase: 35-llm-recognition-canvas-preview
    plan: 11
    provides: recognition_eval.scoring (match_blocks + M1..M9 metrics) and recognition_eval.corpus (load/assert_provenance/assert_context_unchanged), plus Corpus A (frame_ablated)
  - phase: 35-llm-recognition-canvas-preview
    plan: 12
    provides: recognize_structure() as a two-tier orchestrator with resolved-once provider/adapter/negotiated-mode seams, GRAMMAR_CITATION_PATTERNS
provides:
  - recognition_eval.cassette (CassetteAdapter, cassette_key, CASSETTE_VERSION) -- keyed record/replay with a loud miss, zero net-new dependencies
  - recognition_eval.arms (Arm, ArmArtifacts, ARMS, resolve_arm_artifacts, run_arm) -- the seven A0-A5 ablation arms as declarative configurations of one pipeline, never a fork
  - recognition_eval.report (ScoredRow, SkippedRow, run_report_sweep, render_markdown, render_json) -- the committed, diffable run report
  - test_recognition_eval.py driver: the conjunctive SC1 gate (assert_sc1_gate), the A0 validity check (assert_a0_validity), E0 evidence stamping, and a gated (corpus x arm) end-to-end test
  - conftest.py: --corpus/--arm/--arms/--sc1-gate/--permutations CLI options, eval/live marker registration, default live-test deselection
affects: [35-15]

tech-stack:
  added: []
  patterns:
    - "Pure-function gate logic, unit-tested with synthetic numbers, decoupled from live data: assert_sc1_gate() and assert_a0_validity() are plain functions taking pre-computed metrics, so their failing-conjunct message behavior is provable today even though no cassette exists until 35-15 records one"
    - "run_arm() patches cg_recognition's existing module-level seams (get_adapter, negotiate_structured_output, resolve_active_provider, load_persisted_llm_settings, build_recognition_system_prompt, _load_frame_fewshot) and cg_topology.classify via save/restore try/finally -- no pytest monkeypatch fixture required, so it is callable identically from a test or from report.py's standalone CLI sweep"
    - "A cassette miss in run_report_sweep() becomes a SkippedRow, never a crash -- report.py always produces a report, honestly listing every skipped (corpus x arm) combo with its exact refresh command rather than silently omitting unmeasured work"
    - "resolve_arm_artifacts() resolves the pre-35-08 few-shot fixture sha via git log/show at RUN TIME (matching commit subject '35-08'), never a hardcoded guess -- raises loudly if the replacement commit or an earlier commit cannot be found"

key-files:
  created:
    - data-service/tests/recognition_eval/cassette.py
    - data-service/tests/recognition_eval/arms.py
    - data-service/tests/recognition_eval/report.py
  modified:
    - data-service/tests/test_recognition_eval.py
    - data-service/tests/conftest.py
    - data-service/Dockerfile

key-decisions:
  - "CassetteAdapter pins negotiated_mode and prompt_version at CONSTRUCTOR time, not per-call -- recognize_structure() resolves both ONCE before its retry loop and holds them fixed across every attempt, so threading them through generate() (which must keep the real adapter's exact (req, api_key, options=None) signature) would be the wrong scope, not a shortcut."
  - "The (corpus x arm) driver test and the SC1-gate/A0-validity real-data assertions are gated behind explicit --corpus/--arm CLI flags (pytest.skip() otherwise), not run unconditionally -- no cassette is recorded until 35-15, and the plan's own artifacts_this_phase_produces note says so explicitly ('cassette storage layout -- populated in 35-15'). The conjunctive gate logic itself (assert_sc1_gate/assert_a0_validity) is unit-tested today with synthetic numbers, so the FAILING-CONJUNCT behavior is proven now rather than deferred."
  - "E8 publishability failures are a documented PROXY, not a live re-simulation: the real check calls C#'s CanvasAnnotationParser.TryInferParameterDataType (35-11's generator invokes it directly), which this Python harness has no access to. report.py instead counts exact-matched proposals against reference blocks the corpus itself already marks publishable:false, and states this limitation in both the code comment and the rendered report's per-row e8_note field."
  - "Bare pytest run deselection is a pytest_collection_modifyitems hook (mirroring pytest's own -m mechanics), not an addopts config file -- this repo has no pytest.ini/pyproject.toml, so a config-file default marker expression was not available; the hook checks config.option.markexpr and only deselects live-marked items when the user did not pass -m explicitly themselves."

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "cassette.py: CassetteAdapter is a drop-in LLMAdapter (same generate(req, api_key, options=None) signature); cassette_key hashes all 8 identity inputs; a replay-mode miss raises naming the key and the exact refresh command without calling the wrapped adapter; a recorded cassette round-trips truncated/finish_reason/usage; promptBody is stored only for ip_class=='own'"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_recognition_eval.py::TestCassette (14 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "arms.py: ARMS contains exactly A0/A0f/A1/A2/A3/A4/A5 with the AI-SPEC-specified configurations; resolve_arm_artifacts() reads the pre-35-08 grammar-citing fixture out of git at run time (never a hardcoded sha) for A0/A0f and the current counterexample fixture for A1-A5; run_arm() returns a provenance block corpus.assert_provenance accepts; the module never forks recognize_structure"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_recognition_eval.py::TestArms (8 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "test_recognition_eval.py + conftest.py: --corpus/--arm/--arms/--sc1-gate/--permutations are registered pytest options; eval/live markers registered; a bare pytest run deselects live-marked tests; the SC1 gate is a single conjunctive assertion naming every failing conjunct; the A0 validity check states 'harness is wrong, not the model' on a non-failing A0; an incomplete provenance row is refused (raises); E0 rows for frame_ablated are stamped evidence:false with T0 gates inapplicable"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_recognition_eval.py::TestSC1GateConjunction, TestA0ValidityCheck, TestE0EvidenceStamping, TestProvenanceRefusal, TestConftestOptions (22 tests)"
        status: pass
      - kind: manual_procedural
        ref: "docker compose exec -e RECOGNITION_EVAL_MODE=replay data-service python -m pytest tests/test_recognition_eval.py -q --corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60 -- fails loudly with a CassetteMissError naming the key and refresh command (no cassette recorded yet), confirming the end-to-end path is wired correctly"
        status: pass
    human_judgment: false
  - id: D4
    description: "report.py: runnable as python -m tests.recognition_eval.report --out <path>, writes both .md and sibling .json, exits 0; renders M1 with Wilson interval + n=, ECE with per-bin counts, ship-gate and claim-threshold verdicts as two lines, a '## Not measured in this run' section naming every skipped combo and the uncalibrated E4-name/E7-soft dimensions, evidence:false stamps for tier0Evidence:false corpora; never writes a prompt body or API key"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_recognition_eval.py::TestReport (8 tests)"
        status: pass
      - kind: manual_procedural
        ref: "docker compose exec data-service python -m tests.recognition_eval.report --out /tmp/eval-report.md -- writes both files, exits 0, honestly reports 0 scored / 14 skipped combos (no cassette exists yet)"
        status: pass
    human_judgment: false

duration: ~1h10m
completed: 2026-07-26
status: complete
---

# Phase 35 Plan 13: Recognition Eval Harness Driver (Cassette, Arms, SC1 Gate, Report) Summary

**A replay-by-default eval harness that costs $0 and needs no secrets -- CassetteAdapter (keyed record/replay with a loud miss), the seven A0-A5 ablation arms as declarative configurations, a conjunctive SC1 gate + A0 validity check unit-tested with synthetic data, and a markdown+JSON report that honestly lists every combo it could not score.**

## Performance

- **Duration:** ~1h10m
- **Tasks:** 4 of 4
- **Files created:** 3 (cassette.py, arms.py, report.py)
- **Files modified:** 3 (test_recognition_eval.py built incrementally across all 4 tasks, conftest.py, Dockerfile)
- **Commits:** 4 (one per task)
- **Tests added:** 52 (14 cassette + 8 arms + 22 driver/gate/provenance/conftest + 8 report)
- **Full suite:** 474 passed, 1 skipped (the gated end-to-end driver test)

## Accomplishments

- **CI can score recognition deterministically at zero cost with no secrets.** `CassetteAdapter` is a drop-in `LLMAdapter` (identical `generate(req, api_key, options=None)` signature); `cassette_key` hashes all eight of `provider | model | promptVersion | system | userPrompt | temperature | negotiatedMode | maxTokens`, so any prompt change invalidates every recording by construction. A replay-mode miss raises a `CassetteMissError` naming the missing key AND the exact refresh command, and never touches the wrapped adapter -- the free path stays free.
- **The seven ablation arms are real, not aspirational.** `ARMS` holds exactly `A0, A0f, A1, A2, A3, A4, A5` per 35-AI-SPEC.md's table, each a plain `Arm` dataclass (few-shot source, system-prompt flag, Tier-0 flag, provider/model, structured-output flag) with its `claim` string carried verbatim so a report can say what each number is evidence for. `run_arm()` patches `cg_recognition`'s existing module-level seams and bypasses `cg_topology.classify` when `tier0=False` -- confirmed zero forked `recognize_structure` (`grep -c "def recognize_structure" arms.py` returns 0).
- **A0 provably runs the BROKEN prompt, not the fixed one.** `resolve_arm_artifacts()` resolves the pre-35-08 few-shot fixture's git sha at RUN TIME by matching the `35-08` replacement commit's subject in `git log`, then reads the file via `git show <sha>:<path>` -- never a hardcoded guess. Confirmed the resolved content's rationales contain the word "grammar" (A0/A0f) while the current counterexample fixture's do not (A1-A5).
- **The SC1 gate and the A0 validity check are pure, unit-tested functions.** `assert_sc1_gate()` is ONE conjunctive assertion (M1 >= threshold AND E1==0 AND silent_drop_count==0 AND grammar_citation_rate==0.00 AND confidence_spread_ok AND provenance complete) that names EVERY failing conjunct, proven with synthetic numbers (low-M1-only failure names M1 and nothing else; silent-drop-only failure names silent_drop_count and nothing else). `assert_a0_validity()` states "the HARNESS is wrong, not the model" when A0 does not fail as expected.
- **A run without complete provenance is refused, not scored.** Reuses 35-11's `corpus.assert_provenance`/`ProvenanceError` directly; a result row missing `negotiatedMode` raises rather than silently scoring with a gap.
- **E0 rows for Corpus A never masquerade as Tier-0 evidence.** `stamp_e0_evidence()`/`t0_gates_apply()` read `frame_ablated`'s real `tier0Evidence: false` field and stamp/exclude accordingly; `urbanblock_slice`'s `tier0Evidence: true` is unaffected.
- **The report is honest about what it did not measure.** `run_report_sweep()` attempts every requested `(corpus x arm)` combo through a replay `CassetteAdapter`; today, with zero cassettes recorded, ALL 14 combos across both corpora become `SkippedRow`s with their exact refresh command -- verified live: `python -m tests.recognition_eval.report --out /tmp/eval-report.md` writes both a `.md` and a `.json`, exits 0, and prints "scored 0 combo(s); skipped 14 combo(s)". The `## Not measured in this run` section is present even on this fully-skipped run, alongside the always-listed uncalibrated E4-name/E7-soft dimensions. Neither output file contains a prompt body or an API key (grepped for `sk-`/`api_key`: no matches).
- **Zero net-new dependencies**, matching the plan's own constraint -- `cassette.py`/`arms.py`/`report.py` use only `hashlib`, `json`, `subprocess`, `argparse`, `dataclasses`, and the existing `llm_gateway`/`cg_recognition`/`cg_topology`/`recognition_eval.{corpus,scoring}` modules.

## Task Commits

1. **Task 1: cassette.py -- keyed record/replay with a loud miss** - `0ae528b` (test)
2. **Task 2: arms.py -- the A0-A5 ablation arm definitions** - `8705924` (feat)
3. **Task 3: test_recognition_eval.py driver + conftest options + the SC1 gate** - `2cafc11` (test)
4. **Task 4: report.py -- the committed, diffable run report** - `918c9ab` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `data-service/tests/recognition_eval/cassette.py` - `CassetteAdapter`, `cassette_key`, `CASSETTE_VERSION`, `CassetteMissError`, `CassetteWriteError`
- `data-service/tests/recognition_eval/arms.py` - `Arm`, `ArmArtifacts`, `ARMS`, `resolve_arm_artifacts`, `run_arm`
- `data-service/tests/recognition_eval/report.py` - `ScoredRow`, `SkippedRow`, `run_report_sweep`, `render_markdown`, `render_json`, `main` (runnable via `python -m tests.recognition_eval.report --out <path>`)
- `data-service/tests/test_recognition_eval.py` - built incrementally across all 4 tasks: `TestCassette`, `TestArms`, `assert_sc1_gate`/`TestSC1GateConjunction`, `assert_a0_validity`/`TestA0ValidityCheck`, `stamp_e0_evidence`/`t0_gates_apply`/`TestE0EvidenceStamping`, `TestProvenanceRefusal`, `TestConftestOptions`, `TestEndToEndDriver` (gated), `TestReport`
- `data-service/tests/conftest.py` - `pytest_addoption` (`--corpus`/`--arm`/`--arms`/`--sc1-gate`/`--permutations`), `pytest_configure` (marker registration), `pytest_collection_modifyitems` (default live-test deselection)
- `data-service/Dockerfile` - added `git` to the apt-get install list (deviation, see below)

## Decisions Made

See `key-decisions` in frontmatter above. Highlights: `CassetteAdapter`'s `negotiated_mode`/`prompt_version` are constructor-time (matching `recognize_structure()`'s own resolved-once-before-the-loop discipline), the SC1-gate/A0-validity/driver logic is split into a pure conjunctive function (unit-tested today) plus a gated real-data test (deferred to post-cassette-recording), E8 is a documented proxy metric (no C# access from Python), and the default live-marker deselection is a `pytest_collection_modifyitems` hook rather than an ini `addopts` line since this repo has no `pytest.ini`/`pyproject.toml`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `data-service` container had no `git` binary, and `arms.py`'s repo-root resolution used a bare relative path that does not exist inside the container's `/app` layout**
- **Found during:** Task 2 verification (`resolve_arm_artifacts` needs `git log`/`git show` to read the pre-35-08 fixture)
- **Issue:** The container image bakes `/app` in at build time from `COPY . .` inside `./data-service` (the Docker build context) -- there is no `.git` directory anywhere under `/app`, and the `git` binary itself was never installed (`python:3.11-slim` base + `build-essential` only). A naive `parents[3]`-relative repo-root computation would resolve to the container's filesystem root even if `git` were present.
- **Fix:** (a) Added `git` to the Dockerfile's `apt-get install` list. (b) Switched `arms.py`'s `_REPO_ROOT` to the existing `DG_KNOWLEDGE_REPO_ROOT` convention (`dg_knowledge.py`'s own precedent, `docker-compose.yml`'s `.:/mnt/repo:ro` bind mount + `DG_KNOWLEDGE_REPO_ROOT: /mnt/repo` env var) so the same code resolves correctly both inside the container (`/mnt/repo`, which DOES have `.git`) and outside it (falls back to the path computed relative to the file). (c) Rebuilt and restarted the `data-service` container once (`docker compose build data-service && docker compose up -d data-service`) to bake in the new git binary -- unlike 35-11/35-12's precedent of avoiding a rebuild via the read-only `/mnt/repo` mount, this fix requires an actual image change (a new OS package), not just fresher source, so a rebuild was unavoidable.
- **Files modified:** `data-service/Dockerfile`, `data-service/tests/recognition_eval/arms.py` (the `_REPO_ROOT` line)
- **Verification:** `docker compose exec data-service which git` -> `/usr/bin/git`; `TestArms` (all 8 tests) pass; full suite 474 passed / 1 skipped afterward, confirming no regression from the rebuild.
- **Committed in:** `8705924` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking/infra)
**Impact on plan:** The fix is an OS-level dependency addition (git, not a Python package) required for the harness to function in ANY mode (replay, record, or live) -- without it, arm A0/A0f cannot resolve the as-shipped fixture at all, in the container or otherwise. No scope creep; no application logic changed.

## Known Stubs

None that block the plan's stated goal. One documented, non-blocking limitation: `report.py`'s E8 publishability-failure count is a PROXY (reads the reference corpus's own `publishable` field rather than re-simulating C#'s `CanvasAnnotationParser.TryInferParameterDataType`, which is not reachable from this Python harness) -- stated in code (`_e8_publishability_failures`'s docstring) and rendered into the report itself (`e8_note` field), not hidden.

## Threat Flags

None. No new network endpoints, auth paths, or trust-boundary schema changes -- `cassette.py`/`arms.py`/`report.py` are pure test-only utilities under `data-service/tests/`, confirmed unreachable from production (`grep -rn "recognition_eval" data-service/*.py` still returns no match, per 35-11's freeze-protocol guard). `report.py` and `cassette.py` are both explicitly asserted (by test and by grep) to never write a prompt body or API key into a committable artifact.

## Issues Encountered

- Windows/Git-Bash `MSYS_NO_PATHCONV` path-translation gotcha encountered during manual verification: a bare `docker compose exec ... --out /tmp/eval-report.md` from Git Bash silently rewrote `/tmp/eval-report.md` into a Windows host path before it ever reached the container, producing a misleading "file not found" failure that looked like a code bug. Not a code issue -- resolved by prefixing the verification command with `MSYS_NO_PATHCONV=1`. No source change; noted here so a future session recognizes the symptom immediately.

## User Setup Required

None. No external service configuration required. (The `RECOGNITION_EVAL_MODE=record` sweep that will populate real cassettes is 35-15's job and will need `LLM_MASTER_SECRET` + a configured provider at that time, per the plan's own scope boundary.)

## Next Phase Readiness

- 35-15 can run `RECOGNITION_EVAL_MODE=record python -m pytest tests/test_recognition_eval.py -m live --arms=A0,A0f,A1,A2,A3,A4,A5 --permutations=3` once Corpus B (35-14, already frozen) is in place, populating `fixtures/recognition_eval/cassettes/<arm>/<key>.json` for the first time.
- Once cassettes exist, `TestEndToEndDriver::test_scores_one_corpus_arm_combo_via_replay` (currently skipped) and the SC1-gate CI command (`--corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60`) will exercise the exact same code path already proven today against synthetic data -- no additional wiring needed.
- `report.py`'s sweep defaults to both corpora x all seven arms; after 35-15 records cassettes, the SAME `python -m tests.recognition_eval.report --out <path>` invocation will start rendering real `ScoredRow`s instead of an all-`SkippedRow` report.
- No blockers for 35-15. The one open flag carried from 35-11 (`nesting_agreement`'s `proposal_index -> host_proposal_index` mapping contract) remains unresolved here too -- `run_arm`/`report.py` do not yet compute nesting agreement, since no corpus x arm combo has run against real nested-Pattern data yet; flagged again for whichever plan first needs it (likely 35-15, once Corpus B's nested Pattern pair is actually scored).

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*

## Self-Check: PASSED

All 6 touched files found on disk (`cassette.py`, `arms.py`, `report.py`, `test_recognition_eval.py`, `conftest.py`, `Dockerfile`); all 4 task commit hashes (`0ae528b`, `8705924`, `2cafc11`, `918c9ab`) found in `git log`.
