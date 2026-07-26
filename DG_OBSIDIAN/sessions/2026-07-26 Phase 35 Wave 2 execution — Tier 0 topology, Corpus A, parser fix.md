---
date: 2026-07-26
tags: [phase-35, execution, wave-2, tier-0, corpus-a, parser-fix, concurrent-work]
links: [phases/35-llm-recognition-canvas-preview, decisions/Phase-35-recognition-quality-remediation]
---

# 2026-07-26 Phase 35 Wave 2 Execution — Tier 0 Topology, Corpus A, Parser Fix

## Session Summary

**Wave 1 bookkeeping + Wave 2 full execution.** Wave 1 (35-05..35-09) had production commits but no SUMMARY.md, blocking the Wave 2 gate. Reconstructed all five summaries from actual commits (e734e68). Executed Wave 2 in a shared working tree with another Claude Code session actively committing Phase 36 work in parallel — required hardened git staging to avoid cross-session contamination.

**Outcome:** 12/16 Phase 35 plans complete. Wave 2: all 3 plans (35-16, 35-10, 35-11) delivered, all tests green.

## Work Done

### Wave 1 Bookkeeping (e734e68)

Reconstructed SUMMARY.md for 35-05..35-09 strictly from commits:

- **35-05**: Frame fixture enrichment (members + wiring). Commits: `2ce1de3`, `1492514`, `932e304`. Three invariant guards pin what Wave 2 grades against.
- **35-06**: `cg_schemas.py` Pydantic v2 contract + strict-schema emitter. Commit: `5b9ac9d`. 25 tests.
- **35-07**: Gateway `GenerationOptions` / capability negotiation / per-provider token spelling / pinned temperature / `truncated`. Commit: `7a4d641`. 20 tests.
- **35-08**: System prompt `r35.4` + counterexample-shaped few-shot (inverted every harmful property). Commit: `ac1029f`. Addressed the core of SC1 root cause (fixture taught the failure).
- **35-09**: F4 undo fix + G12 accept-time publishability gate. Commits: `f2f518c`, `a82ab03`, `ae6d805`. 4 additional parser tests.

Coverage blocks routed two unproven items to human review:
- 35-08 D3: whether the new prompt actually lifts SC1 is unmeasured until 35-13/35-14 grade it.
- 35-09 D4: G12 per-entity blocking is unit-tested but UAT test 7 stays PENDING (needs live Rhino).

Updated ROADMAP: 9/16 summaries.

### Wave 2 Execution

**Concurrent session management:** Phase 36 F6 work (another Claude Code session) touched `data-service/cg_recognition.py`, `test_cg_recognition.py`, DG.Core/* files, `.planning/REQUIREMENTS.md`. Wave 2 targets (cg_topology.py, recognition_eval/*, frame_ablated.*) are disjoint new files.

**35-16: Order-independent pattern host resolution** (1ce96d6, c6eabee, 37c74fa)
- Fixed latent defect 35-05 flagged: host resolution by pattern-ness, not `groups[]` position.
- With transitive containment, a Procedure appearing earlier than the true parent pattern won `FirstOrDefault`, failed the `idByGroup` lookup, fell back to superset (found nothing), silently never created `PATTERN_HOST_TO`.
- Order-independence tested; Phase 32 nesting proof (`divideLine.Id == topChord.HostPatternId`) still passes.
- **Tests:** 406/406 DG.Tests pass.

**35-10: `cg_topology.py` Tier 0** (9906e0a, 53c1fa7, 29b2c4b, 7d50a43, c5b3752, 73348af)
- `scope_untagged()` (closes UAT F2 silent-widening), `extract_features()`, R1–R6 `classify()` with honest abstention, order-stable `merge()` (G13), `output_token_budget()`.
- 53 tests. Full suite: 407/407 in-container pytest.
- Abstention honest: R5 (fully isolated) + R6 (Procedure/Pattern grouping) abstain by design — not a gap.
- C#-parity critical: `widget_kind()` mirrors `ClassifyNodeKind` exactly; where Python/C# would disagree, Tier 0 abstains.

**35-11: Corpus A + stdlib scoring core** (0c2cef9, 0b0b0b7, 66ee77e, a700658)
- `frame_ablated`: mechanically emitted from the tagged Frame fixture via a golden-file test. 31 reference blocks, 3 `abstainExpected`, `tier0Evidence: false` stamped.
- `scoring.py`: `match_blocks()`, 14 SC1 metrics (Jaccard, Brier, ECE, Wilson). Zero net-new deps (no scipy/numpy).
- `corpus.py`: loader, provenance checks, freeze-protocol enforcement.
- 48 tests in `test_recognition_scoring.py`.

**Independent verification ran both suites myself** (not just self-check):
- `dotnet test ./DG/tests/` → **406/406 passed** (Neo4j up, so `DesignStateValidationFlowTests` ran for real)
- in-container `pytest tests/` → **407 passed**
- Fixture freeze: `frame-cg-context.json` last touched by `1492514` (35-05); no Wave 2 commit edited it.

### Contamination Note

Despite hardened staging rules, **35-11's final commit `a700658` swept in the other session's `.planning/REQUIREMENTS.md` edit** (CGPD-04/CGPD-05 flipped to `[x]`) under a `docs(35-11)` message — though the executor reported it had left the file alone. No data was lost; the content is true (that session's actual work state), now committed. Did not amend it: rewriting HEAD while that session is live is riskier, and reverting those lines would break their bookkeeping mid-run. The attribution should be fixed once the Phase 36 session completes or via a manual commit message amendment.

## Invariants Verified

- ✅ Fixture freeze intact (last edited 1492514 / 35-05)
- ✅ `tier0Evidence: false` stamped on Corpus A
- ✅ Zero scipy/numpy in cg_topology.py or scoring.py
- ✅ All artifacts on disk (8 files)
- ✅ All SUMMARY.md files exist, no FAILED markers
- ✅ Both test suites independently green (406 C# / 407 Python)

## State Update

**Phase 35:** 12/16 plans complete.
- ✅ Waves 1–2 done
- Remaining: Wave 3 (35-12: merge Tier 0 + Tier 1), Wave 4 (35-13: scoring harness), Waves 4–5 (35-14: Corpus B, 35-15: final metrics)

**Next:** `/gsd-execute-phase 35` for Wave 3. Note: 35-12 overlaps the other session's `cg_recognition.py`, so consider waiting until that session is idle.

## Decisions

1. **Hardened staging required for concurrent work on shared tree.** Never use `git add -A`, `--only`, `commit -a`, or stash. Stage by exact path; verify `git diff --cached --name-only` before each commit. The other session's hunks (CGPD-04/CGPD-05 checkboxes) did escape into `a700658` despite these rules, likely because the executor's final write to `.planning/REQUIREMENTS.md` via the state-update query picked up uncommitted changes in the working tree.

2. **Fixture freeze protocol works.** Phase 35-05 locked the Frame fixture; Wave 2 (35-10, 35-11) graded against it without editing it. Provenance and freeze integrity verified post-execution.

3. **Abstention is free, guessing is not.** R5 (fully isolated) and R6 (Procedure/Pattern) abstain by design; a Tier-0 error (confidence 1.0, removes from Tier 1 candidate list) is unchallengeable, so abstaining to avoid guessing is the right choice.

## Open Items

- F1 (truncation) — still live; Phase 35-13 harness will measure it.
- F3 (model quality on frontier LLM) — unproven; Corpus B (35-14) will establish the gap.
- F6 (provenance transport) — parallel Phase 36 session working on it.
- 35-UAT test 1 (cold whole-canvas on frontier model) — blocked on LLM access; Phase 35-13 will grade SC1 formally.
- REQUIREMENTS.md attribution drift — CGPD-04/CGPD-05 checkboxes belong to Phase 36 (F6), committed under Phase 35-11 message.

## Files Modified

Commits: e734e68 (bookkeeping), 1ce96d6–37c74fa (35-16), 9906e0a–73348af (35-10), 0c2cef9–a700658 (35-11).

SUMMARY.md files: 35-05, 35-06, 35-07, 35-08, 35-09, 35-16, 35-10, 35-11 (all created).

Test/artifact files created:
- `DG/tests/DG.Tests/FrameAblatedCorpusEmitterTests.cs` (35-11)
- `data-service/cg_topology.py` + `tests/test_cg_topology.py` (35-10)
- `data-service/tests/recognition_eval/` (35-11, 3 files)
- `data-service/fixtures/recognition_eval/` (35-11, 2 files)

## Related Sessions / Decisions

- [[sessions/2026-07-26 Phase 35 SC1 remediation — planning and Wave 1 execution|2026-07-26: Planning and Wave 1]]
- [[decisions/Phase 35 recognition quality remediation — hybrid Tier 0 Tier 1 architecture and pytest eval|AI-SPEC design]]
- [[debugging/Phase 35 latent parser bug — pattern host resolved by document order|Latent parser bug (35-16)]]
- [[sessions/2026-07-26 Phase 36 F6 fix — provenance transport chain for recognized entities|Parallel Phase 36 session]]
