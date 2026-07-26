---
tags: [phase-35, wave-4, eval-harness, cassette, ablation-arms, sc1-gate]
date: 2026-07-27
model: claude-opus-5, then claude-haiku-4-5-20251001
status: complete
---

# Phase 35 Wave 4 Execution — Eval Harness Driver

## Summary

Executed plan 35-13 of phase 35 (Wave 4 of 5). **Plan complete, all tests passing (474 passed, 1 skipped).** Phase 35 now 15/16 complete; only Wave 5 (35-15: ablation sweep) remains.

## What Was Delivered

**Plan 35-13: Eval harness driver** — the runner that turns the frozen corpora (Corpus A from 35-11, Corpus B from 35-14) and the two-tier orchestrator (from 35-12) into a measurable result.

### Four new files, 4 atomic commits

1. **`data-service/tests/recognition_eval/cassette.py`** (230 lines) — keyed LLM record/replay
   - Replay mode is the default (no live calls during test runs)
   - A replay miss raises `CassetteMissError` with both the key and the refresh command
   - This prevents silent fallthrough to live calls and keeps test runs fast and deterministic

2. **`data-service/tests/recognition_eval/arms.py`** (339 lines) — A0–A5 ablation arm definitions
   - `run_arm()` patches `cg_recognition`'s existing module-level seams (get_adapter, negotiate_structured_output, resolve_active_provider, load_persisted_llm_settings, build_recognition_system_prompt, _load_frame_fewshot, cg_topology.classify)
   - Uses save/restore via `try/finally`, not pytest fixtures — the same function drives both the test suite and `report.py`'s standalone CLI sweep
   - Arms cover the spectrum: A0 (no LLM, Tier 0 only), A0f (A0 + Frame as few-shot), A1–A5 (full stack with different settings)

3. **`data-service/tests/recognition_eval/report.py`** (422 lines) — markdown + JSON emitter
   - Produces both `.md` and `.json` outputs, both committed to version control for diffability
   - Standalone CLI (`python -m tests.recognition_eval.report --out /tmp/eval-report.md`)
   - Reports on (corpus × arm) combinations with provenance tracking and E0 evidence flags

4. **`data-service/tests/test_recognition_eval.py`** (711 lines) + `conftest.py`
   - `--corpus`, `--arm`, `--arms`, `--sc1-gate`, `--permutations` pytest options registered
   - `eval` and `live` markers; default behavior deselects live-marked tests
   - SC1 gate as a single conjunctive assertion naming every failing conjunct (not abbreviated)
   - A0 validity check states "harness is wrong, not the model" on non-failure
   - Incomplete provenance rows raise an error (full traceability required)
   - E0 rows for frame_ablated stamped `evidence:false` with T0 gates inapplicable (ablation corpus is synthetic)

## Test Results

**Full suite:** 474 passed, 1 skipped, 3 warnings (FastAPI deprecation warnings re: `on_event`), ~18s runtime

The one skip is the end-to-end driver test (gated behind `--corpus`/`--arm`), which correctly waits for cassettes that don't exist until 35-15 records them. The conjunctive gate logic itself (SC1 assertions, A0 validity) is unit-tested today with synthetic numbers, so failing-conjunct behavior is proven now rather than deferred.

## Deviations & Notes

**Rule 3 violation (blocking): Dockerfile change bundled into a feature commit**
- The `data-service` container lacked a `git` binary, which `arms.py`'s repo-root resolution needed
- The executor added `RUN apt-get install git` to `data-service/Dockerfile` and rebuilt the container
- This change landed inside commit `8705924` (the arms.py commit) rather than as an atomic follow-up commit
- The code itself is correct; the bundling breaks the one-task-one-commit rule

**Windows/Git-Bash path translation gotcha (documented in SUMMARY)**
- Manual verification of the report CLI encountered a surprising path-rewrite issue on Windows Git Bash
- `MSYS_NO_PATHCONV=1` was needed to prevent Git Bash from translating `/tmp/eval-report.md` into a Windows host path before it reached the container
- Not a code issue; documented in the SUMMARY for future sessions

## Capability Gates (Post-Merge)

All gates passed:
- **schema-drift** (blocking) — `block: false` — no drift detected
- **codebase-drift** (advisory) — `block: false`, skipped (`git-diff-failed`, treated as recoverable)
- **ui.safety-gate** (blocking) — `block: false` — no UI files changed in this wave (Python-only)

## Next: Wave 5

Plan 35-15 is autonomous: false (checkpoint plan — requires user authorization to proceed).

**What it does:** Runs the ablation sweep against the frozen corpora (Corpus A from 35-11, Corpus B from 35-14), records the first cassettes, produces the SC1 measurement, and closes out 35-UAT.md.

**Ready when:** A live LLM provider key is available for the record pass.

**Command:**
```bash
RECOGNITION_EVAL_MODE=record python -m pytest tests/test_recognition_eval.py -m live --arms=A0,A0f,A1,A2,A3,A4,A5 --permutations=3
```

Then: `/gsd-execute-phase 35 --wave 5`

## Session Notes

- Model: claude-opus-5 (orchestrator), sonnet (executor), then haiku-4-5-20251001 for session close
- Runtime: ~1h10m for executor + wave close
- Use-worktrees: false (sequential execution on main tree)
- Branch: master
- No interactive checkpoints; plan was autonomous

## Files Committed This Session

This session created:
- `.planning/phases/35-llm-recognition-canvas-preview/35-13-SUMMARY.md` (new file, created by executor)

The executor's commits are already on master:
- `0ae528b` test(35-13): cassette.py
- `8705924` feat(35-13): arms.py
- `2cafc11` test(35-13): test_recognition_eval.py
- `918c9ab` feat(35-13): report.py
- `6b9e154` docs(35-13): SUMMARY.md

No additional changes needed for this session.
