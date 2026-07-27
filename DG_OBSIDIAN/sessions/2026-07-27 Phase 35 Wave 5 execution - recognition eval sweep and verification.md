# Session: Phase 35 Wave 5 execution — recognition eval sweep and verification

**Date:** 2026-07-27  
**Model:** Claude Opus 5  
**Command:** `/gsd-execute-phase 35 --wave 5`  
**Duration:** ~3.5 hours  
**Commits:** 15 total (1 executor + 13 code-review/verification)

## What this session accomplished

Executed Phase 35 Wave 5 (plan 35-15: recognition ablation sweep, SC1 measurement, UAT closeout). Hit a real architectural gap in the upstream 35-13 harness (no live record path existed at all), escalated to user checkpoint with full rationale, received authorization to build the missing driver in-plan and run DeepSeek-only arms (A0–A4, no frontier key), and completed the sweep. Then ran code review and phase-goal verification.

## Critical findings

### Plan 35-15 execution

- **Blocker discovered:** 35-13's SUMMARY.md claimed `RECOGNITION_EVAL_MODE=record pytest ... -m live` was ready. It wasn't — no test ever marked `@pytest.mark.live` (marker only registered, never applied), and both `report.py` and `TestEndToEndDriver` hardcoded `CassetteAdapter(mode="replay", wrapped=None)`. Zero code path could record.
- **User decision:** Build the missing live record driver inside 35-15 as an in-plan deviation, run DeepSeek-only arms (no Anthropic/OpenAI key configured), defer A0f/A5 to a later frontier-key run.
- **Delivered:** `live_sweep.py` (new record-mode driver with real-provider resolution + decrypted-key resolution + per-attempt cost tracking), 2 live-call bugs found and fixed during the run, 17 cassettes recorded and committed (A0–A4 against both corpora).
- **Commits:** 7 atoms covering the deviation, the bugs, and the four task deliverables.

### Code review (iter3, wave-5 only)

**Status:** `issues_found` — 3 critical, 9 warning, 5 info. No overlap with iter1/iter2 (those covered the canvas preview/accept path).

**Criticals:**
- **CR-02:** A4's cassette unreplayable — driver hardcodes `json_schema_strict` but A4's real mode is `json_object`. Reproduced `CassetteMissError`. Undercuts Task 3's "replay reproducibility proof" *completeness* but didn't falsify published numbers (task-3 row came via `report.py`, which was fixed).
- **CR-01:** `few_shot_permutations()` emits duplicates for single-example arms (A0/A0f have 1 few-shot → 1 distinct of 3 orderings). **Correction:** verified A3 has 5 examples → 3 distinct orderings, so the stability claim for A3 is NOT fabricated. Real hazard attaches to A0, not to any published measurement.
- **CR-03:** The one live/paid test has a tautology assertion — cannot fail. Doesn't falsify this run (cassettes prove calls happened) but the instrument would report green on a zero-recording sweep.

**Security checks:** All 17 committed cassettes scanned for credential leaks — zero hits. Replay hermeticity intact; `RECOGNITION_EVAL_MODE` defaults to `replay`. The `"test-api-key"` fix works on the real-call path but is still structurally reachable per WR-06.

### Phase verification

**Status:** `gaps_found` — 7/12 must-haves verified

**Canvas half:** SC2, SC3, SC4 all verified in code. F4 re-preview undo crash is fixed and retested. This half achieved.

**Recognition half:** SC1 measured and **failed**. M1 = **0.031 vs. required 0.60** on Corpus B / A3. 1 of 32 blocks matched. Verifier reproduced the gate failure and regenerated metrics from committed cassettes — numbers are real.

**Gaps:**
1. SC1 not met (measured, not blocked on provider)
2. A0 harness-validity gate never passed (grammar_citation_rate requires > 0.0, got 0.000)
3. Three code-review Criticals unfixed
4. SC1 gap is unowned across phases 36–40

## Decisions made

1. **Approve building the live record driver in-plan** — 35-13 gap closure routed to 35-15 since 35-15 is the sole consumer
2. **DeepSeek-only sweep** — no Anthropic/OpenAI key configured, A0f/A5 deferred per plan's pre-registered fallback
3. **Scope the code review to wave-5 changes only** — prior reviews (iter1/iter2) already covered 35-01..14/16; wrote to iter3 path to preserve history

## State changes

- **Phase 35 remains pending** — not marked complete pending gap closure
- **REQUIREMENTS.md:76 (RCGN-01) still marked complete** — verifier flagged it as arguably wrong given M1=0.031; user's call to revert or caveat
- **Commit on ROADMAP:** will need to reflect SC1 status change to `blocked` when state advances

## Files created/modified

**Created:**
- `data-service/tests/recognition_eval/live_sweep.py` (new record-mode driver)
- `.planning/phases/35-llm-recognition-canvas-preview/35-REVIEW.iter3.md` (code review report, committed `9d8f9b4`)
- `.planning/phases/35-llm-recognition-canvas-preview/35-VERIFICATION.md` (phase verification, committed `f138ed4`)
- 17 cassette files under `data-service/fixtures/recognition_eval/cassettes/{A0,A1,A2,A3,A4}/`

**Modified:**
- `data-service/tests/recognition_eval/arms.py` (additive api_key_override/negotiated_mode_override params)
- `data-service/tests/recognition_eval/report.py` (touched for live wiring)
- `data-service/tests/test_recognition_eval.py` (new @pytest.mark.live test TestLiveRecordSweep)

**Commits (15):**
- 7 executor commits (35-15 plan execution)
- 1 code-review commit (35-REVIEW.iter3.md)
- 1 verification commit (35-VERIFICATION.md)
- 6 prior-session commits visible in the wave-5 diff base

## Known issues

1. **CR-02 unfixed** — A4 cassette mismatch on structured-output negotiation mode
2. **CR-03 unfixed** — Live test assertion is a tautology
3. **WR-04 unfixed** — Permutation cassettes unreachable by any replay path (run_report_sweep has no --permutations parameter)
4. **WR-06 unfixed** — "test-api-key" literal is still reachable by real adapter (should fail closed at CassetteAdapter boundary)
5. **A0 validity gate** — grammar_citation_rate = 0.000 on both corpora, should have halted all reporting per plan's own rule

## Next steps for user

```bash
/gsd-plan-phase 35 --gaps
```

Gap closure should cover:
- Three code-review Criticals
- A0 validity gate re-evaluation
- UAT test-1 status move to "recorded FAIL with conjunct named"
- Decision on frontier-key configuration to settle prompt-defect-vs-model-ceiling

## Session notes

- The executor's decision to halt at the 35-13 gap rather than fabricate was correct. Independently verifying orchestrator escalations prevented downstream acceptance of false claims about harness readiness.
- The M1=0.031 result is roughly 20x short of the 0.60 gate. This is a genuine miss, not a near-miss, and the "blocked on provider" framing should not obscure it.
- The three code-review Criticals are real. CR-01 was narrower than initially suspected (A3 does have multiple distinct orderings), but the permutation sub-sweep still has unreachable cassettes.
- Phase 35's canvas half succeeded cleanly; recognition half has a measured gap that requires follow-up before shipping.
