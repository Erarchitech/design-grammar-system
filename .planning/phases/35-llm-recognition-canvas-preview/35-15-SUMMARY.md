---
phase: 35-llm-recognition-canvas-preview
plan: 15
subsystem: recognition-eval
tags: [eval-harness, live-llm-sweep, deepseek, sc1-measurement, cassette-record-mode, ablation-sweep]

requires:
  - phase: 35-llm-recognition-canvas-preview
    plan: 13
    provides: recognition_eval.{cassette,arms,report} + the SC1 gate/A0 validity pure functions, unit-tested but never run against real data
  - phase: 35-llm-recognition-canvas-preview
    plan: 14
    provides: Corpus B (urbanblock_slice) -- 32 reference blocks, tier0Evidence:true
provides:
  - "recognition_eval.live_sweep -- the record-mode driver 35-13-SUMMARY.md asserted was ready but never actually existed (built as an in-plan deviation)"
  - "The terminal SC1 measurement: A0 negative control (both corpora), A1-A4 ablation sweep + permutation sub-sweep (DeepSeek-only), replay reproducibility proof, and the ship-gate/claim-threshold verdicts -- 35-EVAL-REPORT.md"
  - "35-UAT.md test 1 closed out to a measured, single-line result (blocked on provider availability, not the prior vague 'quality unvalidated')"
affects: [35 phase closeout, any future frontier-key SC1 completion run]

tech-stack:
  added: []
  patterns:
    - "Additive, backward-compatible override parameters on arms.run_arm() (few_shot_examples_override, api_key_override, negotiated_mode_override) -- every existing replay-mode caller's behavior is byte-identical (all default to None), only the new live driver supplies real values"
    - "REAL_ADAPTER_MAP + resolve_real_negotiated_mode() live in arms.py as the single source of truth for provider-label -> real (llm_gateway tag, base_url) translation, so both the record-mode driver (needs a real decrypted key) and the replay-only report sweep (must never touch a secret) resolve the identical cassette key"
    - "UsageTrackingAdapter: a transparent LLMAdapter-shaped observer wrapper that records real per-call token usage/cost as a side effect without mutating the request or response -- reusable anywhere an adapter chain needs cost accounting"
    - "few_shot_permutations(): 3 fixed, deterministic orderings (identity/reversed/half-rotation), never a random shuffle, for the AI-SPEC's required example-order sub-sweep"

key-files:
  created:
    - data-service/tests/recognition_eval/live_sweep.py
    - .planning/phases/35-llm-recognition-canvas-preview/35-EVAL-REPORT.md
    - data-service/fixtures/recognition_eval/cassettes/A0/*.json (4 files)
    - data-service/fixtures/recognition_eval/cassettes/A1/*.json (2 files)
    - data-service/fixtures/recognition_eval/cassettes/A2/*.json (2 files)
    - data-service/fixtures/recognition_eval/cassettes/A3/*.json (7 files)
    - data-service/fixtures/recognition_eval/cassettes/A4/*.json (2 files)
  modified:
    - data-service/tests/recognition_eval/arms.py
    - data-service/tests/recognition_eval/report.py
    - data-service/tests/test_recognition_eval.py
    - .planning/phases/35-llm-recognition-canvas-preview/35-UAT.md
    - .planning/STATE.md

key-decisions:
  - "The record-mode driver did not exist (35-13-SUMMARY.md overstated readiness) -- built inside 35-15 as an in-plan deviation per explicit user decision, rather than routed back through gap-closure planning, since 35-15 is the sole consumer of the command line 35-13 documented."
  - "DeepSeek-only scope for this run (arms A0-A4; A0f/A5 skipped) -- no Anthropic/OpenAI key configured, per user decision and this plan's own pre-registered fallback branch. SC1 is reported as still blocked on provider availability, not computed as a pass/fail from DeepSeek-only arms."
  - "api_key_override and negotiated_mode_override on run_arm(): two live-call bugs (a literal \"test-api-key\" reaching the real adapter; a DeepSeek response_format 400 from an unconditional json_schema_strict assumption) were found and fixed via additive parameters, never by forking recognize_structure() or breaking any existing replay-mode caller."
  - "A0's validity verdict is read from a blocked (valid:False) G7 guardrail intercept on the required corpus (urbanblock_slice), not from the literal assert_a0_validity() shape (valid:True + scoreable proposals) that 35-13 wrote before Phase 35-12's G7 guardrail existed. G7's own trigger condition encodes F3's exact signature (grammar-citing rationale OR zero proposals for >= 5 residual candidates), so the block is read as harness validated, not harness broken."
  - "The AI-SPEC F3 pre-registered decision rule is reported as unresolved (none of its three branches selected) rather than forced -- every branch needs an A0f/A5 data point that does not exist this session."

requirements-completed: [RCGN-01, RCGN-02, RCGN-03, RCGN-04]

coverage:
  - id: D1
    description: "The missing record-mode live sweep driver (live_sweep.py + arms.py/report.py fixes + TestLiveRecordSweep) actually records cassettes from a real LLM call, resolving a real decrypted API key and the real negotiated structured-output mode -- not the eval harness's mocked test-api-key/json_schema_strict placeholders."
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/ -- full suite 474 passed / 1 skipped / 1 deselected after the fix (no regression)"
        status: pass
      - kind: manual_procedural
        ref: "Live A0/A1-A4/A3-permutation sweep against the real DeepSeek provider: 19 real calls, 193,325 tokens, ~$0.078 total, 17 cassettes recorded and committed"
        status: pass
    human_judgment: false
  - id: D2
    description: "A0 negative control run against both corpora; validity verdict recorded (harness validated -- G7 intercepts A0's pathology on the required corpus, Corpus B)"
    requirement: RCGN-01
    verification:
      - kind: manual_procedural
        ref: "35-EVAL-REPORT.md Task 1 section; cassettes at fixtures/recognition_eval/cassettes/A0/"
        status: pass
    human_judgment: false
  - id: D3
    description: "A1-A4 ablation sweep + permutation sub-sweep recorded and scored across both corpora; F3 decision-rule branch and permutation spread reported"
    requirement: RCGN-02
    verification:
      - kind: manual_procedural
        ref: "35-EVAL-REPORT.md Task 2 section; cassettes at fixtures/recognition_eval/cassettes/A{1,2,3,4}/"
        status: pass
    human_judgment: false
  - id: D4
    description: "SC1 ship-gate and claim-threshold verdicts computed and reported separately; replay reproducibility proven from the committed cassettes with zero misses; fast gate confirmed green"
    requirement: RCGN-03
    verification:
      - kind: automated
        ref: "docker compose exec -T -e RECOGNITION_EVAL_MODE=replay data-service python -m pytest tests/test_recognition_eval.py -q --corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60 (reproduces M1=0.03125 exactly; gate correctly FAILs on M1 alone) && docker compose exec -T data-service python -m pytest tests/ -q -m \"not live\" (474 passed, exit 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "35-UAT.md test 1 closed out to a measured single-line result; findings F1-F5 given resolution status; Gaps rewritten with all deferrals named; STATE.md deferred-items table updated"
    requirement: RCGN-04
    verification:
      - kind: automated
        ref: "node .claude/gsd-core/bin/gsd-tools.cjs query audit-uat -- test 1 (blocked) and test 7 (pending) both surface, no entries dropped"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-07-27
status: complete
---

# Phase 35 Plan 15: Live Recognition Eval Sweep and SC1 Verdict Summary

**Built the record-mode LLM sweep driver 35-13 asserted but never wired, then used it to run the real DeepSeek-only measurement: A0 confirms UAT F3's pathology is now caught in-band by G7; A1-A4 tie at best M1=0.031 (far below the 0.60 ship gate); SC1 is reported as still blocked on provider availability, not resolved to pass or fail, pending an Anthropic/OpenAI key to run arms A0f/A5.**

## Performance

- **Duration:** ~50 min (investigation + checkpoint + full live sweep + report/UAT closeout)
- **Tasks:** 4 of 4 (renumbered: a new Task 0/1a driver-build task was inserted before the plan's original Task 1, per explicit user decision at the mid-plan checkpoint)
- **Commits:** 6 (driver build, bug-fix, Task 1, Task 2, Task 3, Task 4)
- **Files created:** 3 code files + 17 cassette JSON files + 1 new report doc
- **Files modified:** 5
- **Live API calls made:** 19 (real DeepSeek), ~193,325 tokens, ~$0.078 total cost

## Accomplishments

- **Closed a real gap the phase's own prior plan asserted was already closed.** `35-13-SUMMARY.md` said `RECOGNITION_EVAL_MODE=record pytest ... -m live --arms=...` was ready to run; it was not — no test was ever marked `@pytest.mark.live`, and both `report.py` and `TestEndToEndDriver` hardcoded `mode="replay"`. Built `data-service/tests/recognition_eval/live_sweep.py`: real provider/key resolution (`REAL_ADAPTER_MAP` mapping the arm-level `"deepseek"`/`"anthropic"` provenance labels to real `llm_gateway.get_adapter()` calls), real per-call cost/token tracking (`UsageTrackingAdapter`), and the deterministic 3-permutation few-shot generator the AI-SPEC's sub-sweep requires.
- **Found and fixed two live-call bugs the eval harness's own mocks had been hiding.** (1) `run_arm()` always sent the literal string `"test-api-key"` to the real adapter — 401 on the first live call. (2) `run_arm()`/`report.py` assumed `"json_schema_strict"` whenever `arm.structured_output` was True, which 400s against DeepSeek (`llm_gateway`'s own documented "DeepSeek trap" — only `json_object` is supported). Both fixed with additive, backward-compatible override parameters; zero regression (474/1/1 unchanged before/after).
- **A0 (negative control) reproduces UAT F3's pathology on the required corpus, and the harness is validated.** Blocked (`valid:False`) by G7 — a guardrail added in Phase 35-12, after F3 was found, whose own trigger condition literally encodes F3's signature (grammar-citing rationale OR zero proposals for ≥5 residual candidates). Read as evidence the underlying model+prompt behavior still fires, intercepted earlier than F3's original observation, not as a scoring failure.
- **A1-A4 measured DeepSeek-only: best M1 = 0.031** (1/32 blocks, `urbanblock_slice`, all four tied). **A1/A2/A3 tie exactly** on both corpora because `cg_topology.classify()` (Tier 0) abstains on every scoped candidate in this data (decided=0 on 3 and 37 residual candidates) — confirmed by byte-identical recorded cassette hashes between A2 and A3. **A4's structured-output claim is a no-op against DeepSeek**: once negotiated correctly, `schema_for()` returns `None` for DeepSeek's real `json_object` mode, so `OpenAIAdapter` never sends a `response_format` at all — wire-identical to A3.
- **Permutation sub-sweep (arm A3, 3 fixed orderings): spread = 0.000** on both corpora — reported as a point estimate.
- **SC1 verdict: still blocked on provider availability**, both ship-gate (FAIL, M1 alone) and claim-threshold (FAIL, Wilson lower bound 0.006) reported as separate verdicts, exactly as the plan requires — no DeepSeek-only figure stands in for the SC1 result. The AI-SPEC's pre-registered F3 decision rule is reported unresolved (needs an A0f/A5 data point that does not exist this session).
- **Replay reproducibility proven with zero cassette misses**: the SC1-gate replay command reproduces Task 2's exact recorded M1 (0.03125) from the committed cassettes alone; the gate legitimately FAILs on M1 (expected, not a bug — every other conjunct passes). Fast gate green: 474 passed / 1 skipped / 1 deselected, no network call.
- **35-UAT.md test 1 closed out** to a single-line measured result naming arm/provider/model/corpus/promptVersion/M1-with-interval-and-n/ship-gate-verdict; findings F1 (resolved by G8), F2 (resolved by G9), F3 (partially resolved — DeepSeek half answered, frontier half open) all given resolution status; Gaps rewritten with all six deferrals named inline (five carried, one new: the A0f/A5 frontier sweep).

## Task Commits

0. **Driver build (deviation, pre-Task-1):** `dbaf635` (feat) — record-mode live sweep driver
1. **Bug fixes found running the driver:** `0075631` (fix) — test-api-key + DeepSeek response_format
2. **Task 1: A0 negative control (both corpora):** `f4d7f54` (feat) — 4 cassettes recorded
3. **Task 2: A1-A4 sweep + permutation sub-sweep + EVAL-REPORT.md:** `da17fd8` (feat) — 13 cassettes recorded
4. **Task 3: SC1 verdict, replay reproducibility proof, CI gate:** `398fa19` (test) — TestConftestOptions collateral fix
5. **Task 4: 35-UAT.md close-out + STATE.md deferred items:** `c820e64` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `data-service/tests/recognition_eval/live_sweep.py` — the record-mode driver: `REAL_ADAPTER_MAP` reuse, `resolve_live_adapter_and_key`, `UsageTrackingAdapter`, `few_shot_permutations`, `run_live_sweep`
- `data-service/tests/recognition_eval/arms.py` — `REAL_ADAPTER_MAP` + `resolve_real_negotiated_mode` (new, single source of truth); `run_arm()` gains `few_shot_examples_override`/`api_key_override`/`negotiated_mode_override` (all additive, default `None`)
- `data-service/tests/recognition_eval/report.py` — `run_report_sweep()` now calls `resolve_real_negotiated_mode()` instead of assuming `json_schema_strict`
- `data-service/tests/test_recognition_eval.py` — new `TestLiveRecordSweep` (`@pytest.mark.live`); `TestConftestOptions` gains a skip guard for sessions with explicit `--corpus`/`--arm`/`--arms`
- `.planning/phases/35-llm-recognition-canvas-preview/35-EVAL-REPORT.md` — new: provider inventory, A0 verdict, per-arm table, F3 decision-rule status, permutation spread, cost, the two SC1 verdicts, not-measured list
- `data-service/fixtures/recognition_eval/cassettes/{A0,A1,A2,A3,A4}/*.json` — 17 recorded, committed LLM responses
- `.planning/phases/35-llm-recognition-canvas-preview/35-UAT.md` — test 1 closed, F1/F2/F3 given status, Gaps rewritten
- `.planning/STATE.md` — deferred-items table corrected (Frame `.gh`) and extended (A0f/A5)

## Decisions Made

See `key-decisions` in frontmatter. Highlights: the driver gap was closed in-plan rather than deferred to gap-closure planning; the run scope is DeepSeek-only by explicit user decision, with SC1 reported as blocked-on-provider-availability rather than computed as pass/fail from an incomplete arm set; A0's validity verdict is read from a G7 guardrail block (a stronger, later-generation signal than the literal `assert_a0_validity()` shape anticipated); the F3 decision rule is left explicitly unresolved rather than forced into a branch the data cannot support.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2/3 — Missing critical functionality / blocking] The record-mode sweep driver did not exist**
- **Found during:** Task 1 investigation (the plan's own documented command line traced to no implemented test)
- **Issue:** `35-13-SUMMARY.md` asserted `RECOGNITION_EVAL_MODE=record pytest ... -m live --arms=...` was ready; no `@pytest.mark.live` test existed, and both `report.py`/`TestEndToEndDriver` hardcoded `mode="replay"`.
- **Fix:** Built `live_sweep.py` + additive `arms.run_arm()` parameters + `TestLiveRecordSweep`, per explicit user decision at the mid-plan checkpoint (not routed to gap-closure planning, since 35-15 is the sole consumer).
- **Files modified:** `data-service/tests/recognition_eval/live_sweep.py` (new), `arms.py`, `test_recognition_eval.py`
- **Verification:** Full suite 474/1/1 unchanged; safe credential-skip dry runs confirmed zero-cost behavior before any real spend.
- **Committed in:** `dbaf635`

**2. [Rule 1 — Bug] `"test-api-key"` literal reached the real adapter (401)**
- **Found during:** First live A0 attempt
- **Issue:** `run_arm()`'s patched `resolve_active_provider` always returned the literal string `"test-api-key"`, used verbatim by `recognize_structure()` as the Bearer/x-api-key header regardless of the real key resolved elsewhere.
- **Fix:** Additive `api_key_override` parameter (default `None`, preserves the placeholder for every existing/replay caller); `live_sweep.py` passes the real decrypted key through it.
- **Files modified:** `arms.py`, `live_sweep.py`
- **Verification:** Re-ran A0 live — 200 OK, real response recorded.
- **Committed in:** `0075631`

**3. [Rule 1 — Bug] DeepSeek `response_format` 400 from an unconditional `json_schema_strict` assumption**
- **Found during:** First live A1-A4 sweep attempt (arm A4)
- **Issue:** `arms.py`/`report.py` both assumed `negotiated_mode = "json_schema_strict" if arm.structured_output else "none"` — wrong for DeepSeek, whose real capability (per `llm_gateway.negotiate_structured_output`'s own documented "DeepSeek trap") is `json_object` only. `report.py`'s independent copy of this same wrong assumption ALSO caused a cassette-key mismatch (A4 showed as a cassette miss on replay despite being recorded moments earlier).
- **Fix:** `REAL_ADAPTER_MAP` + `resolve_real_negotiated_mode()` moved to `arms.py` as the single source of truth (hermetic — no network call needed for the `openai`/`anthropic` branches); additive `negotiated_mode_override` parameter on `run_arm()`; `report.py` calls the same shared function.
- **Files modified:** `arms.py`, `live_sweep.py`, `report.py`
- **Verification:** Re-ran the sweep — 8/8 calls succeeded; report.py replay: 9 scored / 1 skipped (the 1 being the honest G7 block, not a cassette problem).
- **Committed in:** `0075631`

**4. [Rule 3 — Blocking, pre-existing] `TestConftestOptions` collateral failure under the plan's own documented CLI args**
- **Found during:** Task 3 (running the exact `--corpus=urbanblock_slice --arm=A3 --sc1-gate=0.60` command from the plan)
- **Issue:** `test_options_registered_with_expected_defaults` hardcodes assertions that CLI options are at their bare defaults — structurally unable to hold when this plan's own documented, non-default CLI invocation is the active session (pytest options are process-global). Pre-existing in 35-13's suite, not caused by this plan's code changes.
- **Fix:** `pytest.skip()` guard mirroring `TestEndToEndDriver`'s own `--corpus`/`--arm` skip precedent.
- **Files modified:** `test_recognition_eval.py`
- **Verification:** Command now yields exactly one failure (the expected SC1-gate assertion) and zero collateral failures.
- **Committed in:** `398fa19`

---

**Total deviations:** 4 (1 missing-functionality + 3 bugs, 2 discovered mid-live-call and only catchable by making a real API call, which is exactly why the driver needed to exist)
**Impact on plan:** All four were necessary for the plan's own documented commands to work as written and for the SC1 measurement to be real rather than fabricated. No scope creep beyond what running the plan's own specified commands required.

## Known Stubs

None. Every reported figure (M1, tokens, cost, Wilson intervals) is computed from real, committed cassette data — no placeholder values.

## Threat Flags

None. `live_sweep.py` is test-only code under `data-service/tests/`, decrypts the API key only in-process via the existing `LLM_MASTER_SECRET` mechanism (never logs it, never writes it to a cassette — confirmed by the existing `TestCassette`/`TestReport` grep-for-`sk-`/`api_key` assertions, unaffected by this plan), and introduces no new network endpoint or auth path. Cassettes never store an API key.

## Issues Encountered

- **Cassette files are not visible on the host without an explicit copy.** `data-service`'s `/app` is baked into the Docker image at build time (no bind mount, unlike `DG_DATA_DIR`/`/mnt/repo`), so cassettes written inside the container during `record` mode are trapped in the container's writable layer until copied out via `docker compose cp`. Worked around manually each recording round; noted here so a future session doesn't lose recorded cassettes to a container restart before committing them.
- **Windows/Git-Bash path-translation gotcha** (same as 35-13): bare `docker compose exec` invocations with absolute container paths need `MSYS_NO_PATHCONV=1` from Git Bash, or the path silently rewrites to a Windows host path.

## User Setup Required

None for this session (DeepSeek-only, already configured). **To complete SC1**, a future session needs: an Anthropic (or genuine OpenAI) key configured via the LLM Settings panel (`POST /llm/settings`), then `RECOGNITION_EVAL_MODE=record pytest tests/test_recognition_eval.py -q -s -m live --arms=A0f,A5` against both corpora — no further code change needed (confirmed via the safe `A0f` credential-skip dry run in Task 1).

## Next Phase Readiness

- The driver, bug fixes, and full DeepSeek-only measurement are committed and reproducible from the committed cassettes at zero further cost.
- SC1 remains **blocked, not failed** — the concrete next step (frontier key → `--arms=A0f,A5` → apply the F3 decision rule → re-run the permutation sub-sweep on whichever arm then wins → recompute the final ship-gate/claim-threshold verdict) is spelled out in `35-EVAL-REPORT.md`'s Task 3 section.
- A genuine follow-up finding surfaced this session, out of this plan's scope: Tier 0 (`cg_topology.classify`) currently abstains on every scoped candidate in both available corpora — contributes nothing measurable, extending 35-14's documented Tier-0 rule R4 defect. Worth a dedicated Tier-0 rule-coverage plan.
- Six deferrals now travel with the phase (five carried + the new A0f/A5 sweep), recorded in both `35-UAT.md`'s Gaps section and `STATE.md`'s deferred-items table so `/gsd-verify-work 35` re-surfaces all of them.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-27*

## Self-Check: PASSED

All 9 checked files found on disk (`live_sweep.py`, `arms.py`, `report.py`, `test_recognition_eval.py`,
`35-EVAL-REPORT.md`, `35-UAT.md`, `STATE.md`, and two representative cassette files under
`cassettes/A0/` and `cassettes/A4/`). All 6 task commit hashes (`dbaf635`, `0075631`, `f4d7f54`,
`da17fd8`, `398fa19`, `c820e64`) found in `git log`. Full suite re-confirmed green immediately before
writing this summary: `docker compose exec -T data-service python -m pytest tests/ -q -m "not live"`
→ 474 passed, 1 skipped, exit 0.
