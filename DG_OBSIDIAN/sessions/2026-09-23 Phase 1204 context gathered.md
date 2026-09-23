# Session: Phase 1204 Context Gathered

**Date:** 2026-09-23
**Task:** `/gsd-discuss-phase 1204 обсуди все темы и прими все рекомендуемые решения самостоятельно`
**Model:** Claude Haiku 4.5
**Duration:** Continued from prior context window (summarized mid-session)

## Summary

Completed the discuss phase for Phase 1204 (Determinism and LLM Reproducibility Benchmark, v12.0) in auto mode. User explicitly requested that I discuss all six gray areas and auto-accept all recommended decisions without user confirmation.

## Work Done

1. **Phase 1204 CONTEXT.md created** (commit `73a32d5`)
   - 908 lines, 28 decisions (D-01 through D-28)
   - Six discussion areas auto-selected per user instruction
   - All recommendations accepted without intermediate user prompts
   - `<upstream_corrections>` section documents 11 disk-verified corrections to inherited assumptions

2. **Phase 1204 DISCUSSION-LOG.md created** (commit `73a32d5`)
   - 170 lines documenting alternatives considered per gray area
   - Preserved for audit trail; decisions live in CONTEXT.md
   - Notes reversibility and integration impacts for key decisions

3. **STATE.md updated** (commit `6365cb9`)
   - Recorded stopped_at as "Phase 1204 context gathered"
   - Set resume_file pointer to 1204-CONTEXT.md
   - Updated session timestamp

4. **Memory notes created**
   - `phase-1204-context-gathered.md` — headline decisions and load-bearing corrections
   - `de01-data-service-leg-is-a-relay.md` — critical fact about DE-01 leg classification
   - Updated MEMORY.md index with both

## Key Decisions

**Deterministic half (measuring validator repeatability):**
- Reuse DE-01 legs, split into evaluator (csharp, dg-reasoner) and relay (data-service, replay)
- Benchmark-computed projection hash with closed exclusion list (no producer changes)
- N = 10 iterations across ≥2 fresh process lifetimes (Python hash randomization invisible in warm loops)
- Single divergence fails the gate

**LLM half (measuring proposal stability):**
- Recognition (primary) + rule-ingest (secondary), both measured as shipped
- Own proposal-outcome taxonomy (valid / valid_after_retry / invalid / abstained / truncated / refused / provider_error)
- k = 10 samples per item per provider, Wilson CI per-item
- Reproducibility class per experiment (replayable / re-executable-pinned-weights / not-reproducible-provider-managed)

**Contract & artifacts:**
- New `spec/REPRODUCIBILITY.md` with machine-checked scope table of LLM call sites
- Two separate reports (deterministic + LLM), each with own schema
- Both live runs are human checkpoints; provider keys via LLM settings panel only

## Critical Upstream Corrections

From disk audit, 11 facts contradicted inherited prose:
1. data-service leg echoes fixture's `expectedOutcomes` — does not evaluate the rule
2. No leg emits `outputHash` — benchmark must compute it
3. data-service envelope's `definitionId = run_id` (varies per publish)
4. Replay leg reads newest run by default (input not fixed in loop)
5. Rule-ingest sends no temperature; runs at provider default
6. DeepSeek routes through OpenAIAdapter; provider identity is endpoint host
7. No harness takes k>1 samples; cassettes collide by request digest
8. `prompt_version` logged, never persisted
9. No envelope carries provider/model today
10. `spec/EVIDENCE-CONTRACT.md` §6 stale on scalar-tuple hashing
11. dg-reasoner reports serviceVersion "unknown"

These corrections drove decisions D-02 (evaluator/relay split), D-04 (benchmark-computed hash), D-05 (process lifetimes), D-09/D-10 (measure as shipped), and D-20 (gateway fields).

## Next Step

`/gsd-plan-phase 1204` — user has not invoked planning; context gathering is complete.

## Files Modified

- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/1204-CONTEXT.md` (created)
- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/1204-DISCUSSION-LOG.md` (created)
- `.planning/STATE.md` (updated)
- Memory index (updated)
