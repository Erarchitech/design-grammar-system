---
tags: [session, v12.0, phase-1204]
date: 2026-09-28
---

# Session: 2026-09-28 — Phase 1204 execution complete: Determinism and LLM Reproducibility Benchmark

## Goal

Execute all 9 plans of Phase 1204 (v12.0 Theory–Implementation Alignment): separate deterministic-validator repeatability (DE-01 legs, D-08 gate) from LLM proposal repeatability (recognition/rule-ingest, honest non-claims), per `/gsd-execute-phase 1204` with an explicit user directive to use DSH (DeepSeek Harness) flash workers for wave 1–2 subtasks.

## What Was Done

**Wave 1** (plans 01–04, DSH deepseek-v4-flash, independently re-verified by the orchestrator after every dispatch): projection-hash primitive (D-04 exclusion list), gateway provenance tracer (D-20 `served_model`/`response_id`/`system_fingerprint`), sample-indexed cassette key (D-21), LLM sample outcome taxonomy (D-14/D-18 oracle-free). Commits `32b880f`, `afb106b`, `5552b35`, `bc75d6f`.

**Wave 2** (plans 05–07, DSH): deterministic repeat runner (D-06/D-07/D-08), `spec/REPRODUCIBILITY.md` + machine-checked drift guard (D-25/D-26), LLM repeatability measurement driver + D-12 freeze script. Commits `d804814`, `485b2c1`, `d30f885`. CLAUDE.md's additive "Reproducibility contract" pointer paragraph was written directly by the orchestrator (not DSH) and deliberately left uncommitted for the owner, given a pre-existing uncommitted DSH-delegation section in that file.

**Wave 3** (plans 08–09, live infrastructure + human checkpoints, run directly by the orchestrator — never DSH, given live Docker restarts, real LLM API cost, and D-28's key-handling rule):
- **1204-08**: live deterministic benchmark against the freshly rebuilt Docker stack. **D-08 gate genuinely FAILED** — `data-service` (relay leg) produced 2 distinct projection hashes across 10 iterations, diverging only at iteration 6 (right after the mid-run restart) and reverting for iterations 7–10. Recorded verbatim, not fixed, per D-08's explicit prohibition on tuning the exclusion list to clear a divergence. Owner reviewed and approved. Commit `c19f5b1`.
- **1204-09**: live LLM sampling, k=10 across all 5 D-12 rule-ingest prompts (50 real calls) against the configured OpenAI-compatible provider (custom router). Owner explicitly scoped this to rule-ingest only (recognition prompts would need faithfully reproducing `cg_recognition`'s internal Computgraph-derived context, judged too high-risk to approximate). D-27 floor (≥1 provider, k≥5) satisfied for every item at n=10. Modal agreement 0.1–0.6 — genuine disclosed instability. Commits `18b6d17`, `00c4e50`.

**Phase close-out**: full regression suite confirmed clean against the known pre-existing Neo4j-dependent baseline (4 failures + 25 errors, zero file overlap with any phase-1204 change). `gsd-verifier` agent: 12/12 must-haves passed, no tampering found. `phase.complete` ran, STATE/ROADMAP/REQUIREMENTS updated. Commit `3a1d7bf`.

## Decisions Made

- DSH flash workers for waves 1–2, with the orchestrator independently re-running every acceptance command rather than trusting worker self-reports (see [[dsh-planning-worker-patterns]] and the new decision below).
- Wave 3 (live infra + secrets) executed directly by the orchestrator, never delegated — see [[knowledge/decisions/Live-infrastructure GSD plans run by the orchestrator directly, never DSH|decision]].
- 1204-09 scoped to rule-ingest only, recognition deferred — see [[knowledge/decisions/1204-09 scoped to rule-ingest only, recognition prompt construction deferred|decision]].

## Issues Encountered

Roughly a dozen real bugs surfaced only under live execution (DSH hermetic tests never exercised these paths) — all found, fixed, and documented per-plan in the corresponding `*-SUMMARY.md`. The two most broadly reusable are captured as standalone debugging notes:
- [[knowledge/debugging/Python module-identity mismatch silently defeats a monkeypatch|Python module-identity mismatch silently defeats a monkeypatch]] — a bare `import cassette` vs. the codebase's own `from recognition_eval import cassette` created two separate `sys.modules` entries; patching `_FIXTURES_ROOT` on the wrong one briefly wrote live cassettes into a FROZEN directory (caught before commit, host repo never touched).
- [[knowledge/debugging/D-24 report schema had no item dimension, risking misleading pooled metrics|D-24 report schema had no item dimension, risking misleading pooled metrics]] — `report_schema_llm.json`'s `providerStrata` (shipped by an earlier plan) had no way to represent multiple items; naively pooling 5 different rule-ingest prompts' samples into one stratum would have produced a near-zero "modal agreement" figure that looked like total instability but was actually a measurement artifact.

Other fixes (documented in-plan, not broken out separately): `run_leg_replay_pinned` crashed on any real HTTP response (`evidence_contract.validate_envelope` expects a pydantic model, not a dict — plan 1204-08 preflight, fixed in `2615ae1`); insufficient production adapter timeout for a 41k-char prompt (worked around locally, `llm_gateway.py` never edited); no retry for transient network/5xx errors (added, orchestrator-local); five missing D-19 provenance item fields; a `report.py` markdown-emitter field-name mismatch against its own schema (worked around, flagged for a future phase).

## Next Steps

- Next phase per roadmap: **1205 — Security and Tenancy Release Gate**.
- `report.py`'s `render_llm_repeatability_markdown` field-name mismatch (`strata`/`providers` vs. the schema's `providerStrata`) is a known, disclosed defect — worth a small fix in a future phase touching `data-service/tests/recognition_eval/report.py`.
- CLAUDE.md still carries an uncommitted "Reproducibility contract" pointer paragraph (from 1204-06) alongside the owner's own pending DSH-delegation section — the owner should commit both together when ready.

## Related Notes

- [[knowledge/decisions/Live-infrastructure GSD plans run by the orchestrator directly, never DSH|Decision: live-infra plans stay with the orchestrator]]
- [[knowledge/decisions/1204-09 scoped to rule-ingest only, recognition prompt construction deferred|Decision: 1204-09 rule-ingest-only scope]]
- [[knowledge/debugging/Python module-identity mismatch silently defeats a monkeypatch|Debugging: module-identity mismatch defeats monkeypatch]]
- [[knowledge/debugging/D-24 report schema had no item dimension, risking misleading pooled metrics|Debugging: D-24 schema item-dimension gap]]
- [[dsh-planning-worker-patterns]] (prior session's DSH reliability notes — held throughout this phase: ~50% TRANSPORT failure rate, always resumable, worker self-reports not trusted)
