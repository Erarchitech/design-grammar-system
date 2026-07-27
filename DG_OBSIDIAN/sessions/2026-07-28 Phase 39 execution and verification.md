---
session_type: phase_execution
phase: 39
phase_name: DesignState Auto-Validation Investigation
status: complete
model: claude-opus-5 (primary), claude-haiku-4-5-20251001 (final)
date: 2026-07-28
execution_time_minutes: 360
waves_executed: 5/5
verification_status: passed
---

# Phase 39 Execution Session — 2026-07-28

## Session Summary

Executed all 5 plans of Phase 39 (DesignState Auto-Validation Investigation) sequentially across ~6 hours, with one blocking human-verify checkpoint at Wave 4 requiring operator confirmation. Verification passed 26/26 must-haves. Phase marked complete; DSAV-01/02/03 met.

## What This Phase Delivered

A **prototyped, evidence-based answer** to "can validation run automatically when a DesignState is captured?" 

- **Wave 1 (39-01)**: `data-service/dsav_watcher.py` — the auto-validation state machine (capture → coalesce → validate → complete/fail) as a standalone, importable module with in-memory guardrails
- **Wave 2 (39-02)**: Wired the watcher into the running service — `POST /designstate/capture` endpoint, FastAPI lifespan-managed daemon, best-effort auto-publish adapter. Fixed two plan-text bugs: a silently-killed startup hook and an auto-publish arity mismatch
- **Wave 3 (39-03)**: Live-Docker evidence driver measuring SC1 and SC2 — **2.679 s capture→run latency**, **8→1 debounce collapse**, **3 runs/min throughput**, all 8 Cypher constants executed, D-08 retry ladder terminal failure observed. Evidence artifact produced with zero estimates
- **Wave 4 (39-04)**: Single Speckle publish-enabled run, human-verified in Speckle viewer. One real version (`2ab708e884`) minted and confirmed. Plus operator-authorized scope extension: added `live` marker to `test_dsav_live_loop.py` so routine suite runs no longer scrub phase evidence
- **Wave 5 (39-05)**: DSAV-01 investigation note comparing trigger architectures (GH-side, data-service watcher, Neo4j event-driven) with measured latency/publish-flood/Speckle-noise analysis. DSAV-03 ADR filed to `DG_OBSIDIAN/knowledge/decisions/` scoping full implementation to a follow-up milestone

## Key Findings

**F-39-01 (Open Design Question):** Auto-runs are SHACL-validated BEFORE their own `ValidStatus` is written. At validation time, the run node has no `ValidStatus`, which trips the shapes graph's own `RunStatusShape_valid`. That finding's `focusLabel` is the `runId`, which matches no objState, so P-02's conservative unmapped fallback flips **every** ObjState to false. Measured: `conforms: false`, `ValidStatus: [false, false]`. Verdicts are structurally sound but NOT discriminating — a real design question for Phase 40+ (DSAV-03 ADR), not something Phase 39 resolved.

**F-39-02:** The rate limiter, not the debounce window, is what caps sustained throughput. Saturated projects accumulate `captured` rows (no data loss, but visible to existing readers).

## Checkpoints & Operator Input

Wave 4 included a `checkpoint:human-verify` blocking gate. The executor correctly halted without self-approval and surfaced the Speckle viewer URL for human confirmation. Operator (you) opened `http://localhost:8090/projects/44088eefc6/models/a6d1e0c5da@2ab708e884` and confirmed version existed with matching timestamp. Also approved adding the `live` marker to `test_dsav_live_loop.py` as an operator-authorized scope extension — that marker prevents routine suite runs from accidentally collecting and scrubbing the phase evidence.

## Deviations & Fixes

**Wave 1:** `COALESCE_QUERY` extended to return `statePayloadJson` (plan's minimum `RETURN` spec was underspecified)
**Wave 2:** Removed `@app.on_event("startup")` and moved `ensure_spec_indexes()` into the lifespan to avoid silently killing a shipped startup hook; fixed auto-publish arity mismatch (`poll_once` calls `publish_fn(project, kept_run_id)`, plan specified three required params)
**Wave 3:** Replaced the plan's literal "capture every second" with a 4-captures-then-8s-idle cycle so the debounce window re-arms AND lapses; drained the rate-limiter window between scenarios
**Wave 4:** Preflight deviation — instead of probing for a Speckle `IntegrationConfig` specific to the synthetic `p39-autoval` project (which would have recorded false-negative `blocked`), verified the write token, found a real existing `provider:'Speckle'` row, proved its project and base model readable, then pointed `p39-autoval` at that same real Speckle project. T-39-12 rationale applied
**Wave 5:** Corrected plan's cross-reference from D-823-03 to D-823-02 for the degrade-never-raise policy; declined to propagate the ~1.5 s latency figure from 39-03-SUMMARY.md into comparison tables (it cannot be reconciled with the 2.679 s artifact measurement)

## Post-Execution State

- **ROADMAP:** Phase 39 marked complete (5/5 plans, verification passed)
- **STATE.md:** Updated with phase 39 completion
- **REQUIREMENTS.md:** DSAV-01/02/03 marked complete
- **PROJECT.md:** Evolved to reflect Phase 39 completion and F-39-01 open issue; two warnings documented
- **VERIFICATION.md:** Created (39 must-haves verified, zero overrides)
- Verifier live re-ran the suite (6 passed in 194.82 s) and queried Speckle GraphQL directly to confirm the published version exists
- Environment clean: 0 `provider:'AutoValidation'` rows, `publishEnabled` off, all temporary test rows scrubbed
- No new git stashes created; pre-existing 8 stashes unchanged

## Non-Blocking Warnings (for Phase 40+)

**W-39-A:** `spec/DATABASE.md:108` still documents only `Run_Id`/`ValidStatus`/`SendStatus`/`statePayloadJson`/`shaclReportJson`. The phase's six new `:ValidationRun` properties and the `captured→completed|superseded|failed` state machine are live in the running service but not documented. Schema Change Propagation list names this file explicitly — recommend closing before Phase 40.

**W-39-B:** Stale ~1.5 s latency decomposition at `39-03-SUMMARY.md:132`. Uncorrected in place but honestly recorded in both deliverables and not used in Phase 39 comparisons. Verifier's fresh run added evidence (4.399 s) the note was right to reject it.

## Commits This Session

- `690ec11` — docs(phase-39): evolve PROJECT.md after phase completion

All other commits (tracking, verification, phase metadata) were made by the execution phase workflow or subagents.

## Changes to the Vault

- Created `DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md` (DSAV-03 ADR)
- Updated `DG_OBSIDIAN/00-home/index.md` with one insertion (link to the new ADR)
- This session note is being filed to `DG_OBSIDIAN/sessions/`

Next: Phase 40 (E2E Validation and Docs) can be discussed via `/gsd-discuss-phase 40`.
