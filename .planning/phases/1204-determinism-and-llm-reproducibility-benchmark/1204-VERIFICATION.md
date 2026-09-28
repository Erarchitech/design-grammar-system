---
phase: 1204-determinism-and-llm-reproducibility-benchmark
verified: 2026-09-28T17:49:45Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 1204: Determinism and LLM Reproducibility Benchmark Verification Report

**Phase Goal:** Separate deterministic validator repeatability from LLM proposal repeatability; measure whether DE-01's deterministic legs actually produce identical output across repeated fresh-process runs (D-08 gate), and separately measure LLM sample-to-sample repeatability for two subjects (recognition, rule-ingest) with honest, disclosed non-claims — never asserting universal determinism.

**Verified:** 2026-09-28T17:49:45Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-04 projection-hash primitive: excludes exactly `{emittedAt, generatedAt, definitionId}`, canonicalizes row order, detects every other mutation, is cross-process/hash-seed independent | ✓ VERIFIED | `tools/de01/projection_hash.py` read; 26 tests in `test_repeat_runner.py::TestProjectionHash*`; re-ran `python -m pytest tools/de01/tests/ -q -k "not live"` myself → **124 passed** |
| 2 | D-20 gateway provenance fields (`served_model`/`response_id`/`system_fingerprint`) are additive, backward-compatible, sourced only via `.get` from provider JSON, never synthesized; request behavior (D-10) unchanged | ✓ VERIFIED | `data-service/llm_gateway.py` read (3/2/1 `.get` population sites, `model=req.model or ""` untouched); re-ran `pytest data-service/tests/test_llm_gateway.py -q` myself → **62 passed** |
| 3 | D-21 sample-indexed cassette key: index 0 is byte-identical to the pre-D-21 8-part digest; k repeat samples get distinct keys | ✓ VERIFIED | `cassette_key(..., sample_index=0)` reproduces the pinned digest; covered inside the recognition_eval regression run (below) |
| 4 | D-14/D-19 LLM outcome taxonomy (7-label closed set, disjoint from the 8 verdict statuses) + provenance void guard, harness-side only (D-23 — no production/envelope change) | ✓ VERIFIED | `outcome_taxonomy.py`/`test_outcome_taxonomy.py`/`test_provenance.py` read; `git diff --stat` on `data-service/evidence_contract.py`/`spec/evidence-contract.schema.json` across all phase-1204 commits is empty |
| 5 | D-06/D-07/D-08 deterministic repeat runner: N-iteration falsification instrument gated on hash set-equality + zero silent disagreements across restart batches, with full config pins | ✓ VERIFIED | `tools/de01/run_de01_repeat.py` (~1230 lines) read; part of the 124-passed `tools/de01/tests/` run above (8 `TestRepeatRunner*` classes) |
| 6 | `spec/REPRODUCIBILITY.md` ships the normative determinism boundary (3 classes, scope table, exclusion list, provenance fields, reproducibility classes, non-claims, machine-checked fenced block) and CLAUDE.md points to it | ✓ VERIFIED | File read: 217 lines, exactly the 8 documented `## ` sections; `CLAUDE.md:216` carries the "Reproducibility contract" pointer paragraph; re-ran `pytest tools/de01/tests/test_reproducibility_scope_drift.py -q` myself → **4 passed** |
| 7 | D-12/D-13/D-17/D-18/D-24 LLM repeatability measurement driver: per-(provider,item) stratification never pooled, Wilson 95% CI, min-sample floor, byte-identical replay labeled "scoring-pipeline determinism" (never model determinism) | ✓ VERIFIED | `repeat_sweep.py`/`report_schema_llm.json`/`freeze_rule_ingest_prompts.py` read; re-ran `pytest data-service/tests/recognition_eval/test_repeat_sweep.py -q -k "not live"` myself → **14 passed** |
| 8 | Live deterministic-half benchmark actually executed against a freshly rebuilt Docker stack; D-08 gate evaluated and its result honestly recorded (FAIL disclosed for the `data-service` relay leg, not hidden or "fixed"); owner reviewed and approved the disclosed failure | ✓ VERIFIED | Read `deterministic-evidence/de01-repeat-report.md` directly: data-service 2 distinct hashes / FAIL, dg-reasoner/csharp/replay 1/PASS, silent_disagreement_count 0 in all 10 iterations, non-proof statement present verbatim, label-drift finding present; matches SUMMARY.md exactly |
| 9 | Live LLM-half benchmark actually executed with real API calls; D-27 floor satisfied for every item (n=10, no "insufficient samples" fallback needed); D-21 replay byte-identical; full provenance on every sample; no universal-determinism claim; D-28 key handling followed | ✓ VERIFIED | Read `llm-evidence/llm-repeatability-report.md` directly: 5 items × n=10, explicit non-claim banner, Limitations section, D-22 class stated per-experiment; matches SUMMARY.md exactly |
| 10 | Requirements ALGN12-15 and ALGN12-16 are traced across the phase's plans with no orphaned requirements | ✓ VERIFIED | Both IDs appear in `.planning/REQUIREMENTS.md:41-42`; `ALGN12 determinism | 1204 | 2` count row (`:75`) matches exactly the 2 IDs declared across all 9 plans' frontmatter — no orphans |
| 11 | No regression introduced into the pre-existing test baseline | ✓ VERIFIED | Ran `pytest data-service/tests/test_dg_context.py -q` myself → **4 failed** (matches the disclosed pre-existing baseline exactly); `git diff --stat 32b880f^..18b6d17 -- data-service/tests/test_dg_context.py data-service/tests/test_cg_structure_checks.py data-service/tests/test_computgraph_consult.py data-service/dg_context.py data-service/cg_recognition.py` → empty (zero file overlap) |
| 12 | Roadmap gate: reports deterministic and model-dependent results separately, with confidence/limitations | ✓ VERIFIED | Two separate report file pairs, two separate JSON schemas (no shared score field, verified by `test_llm_report_schema_has_no_shared_or_accuracy_fields`), Wilson CI in the LLM report, explicit Limitations sections in both |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/de01/projection_hash.py` | D-04 projection + hash primitive | ✓ VERIFIED | Exists, substantive, wired (imported by `run_de01_repeat.py` and the test suite) |
| `tools/de01/run_de01_repeat.py` | D-05/06/07/08 repeat runner | ✓ VERIFIED | Exists, substantive (~1230 lines), wired (CLI invoked live in plan 08) |
| `tools/de01/report_schema_repeat.json` | Sibling repeat-report schema | ✓ VERIFIED | Exists, distinct `$id`, live report validates against it |
| `spec/REPRODUCIBILITY.md` | Normative determinism boundary | ✓ VERIFIED | Exists, 217 lines, 8 sections, referenced from CLAUDE.md |
| `tools/de01/tests/test_reproducibility_scope_drift.py` | D-26 machine-checked scope guard | ✓ VERIFIED | Exists, 4 tests green, walks `data-service/*.py` via `ast` |
| `data-service/llm_gateway.py` (extended) | D-20 provenance fields | ✓ VERIFIED | Exists, additive fields present, adapters populate them |
| `data-service/tests/recognition_eval/cassette.py` (extended) | D-21 sample-indexed key | ✓ VERIFIED | `sample_index` param present, index-0 backward compatible |
| `data-service/tests/recognition_eval/outcome_taxonomy.py` | D-14 closed label taxonomy | ✓ VERIFIED | Exists, 7-label frozenset, disjoint from verdict statuses |
| `data-service/tests/recognition_eval/corpus.py` (extended) | D-19 provenance void guard | ✓ VERIFIED | `assert_llm_sample_provenance` added, additive |
| `data-service/tests/recognition_eval/repeat_sweep.py` | LLM repeatability driver | ✓ VERIFIED | Exists, per-item/per-provider metrics, wired into the live plan-09 capture |
| `data-service/tests/recognition_eval/report_schema_llm.json` | D-24 separate LLM schema | ✓ VERIFIED | Exists, additive `item` field fix confirmed via `git diff d30f885 18b6d17` — pure addition |
| `data-service/tests/recognition_eval/freeze_rule_ingest_prompts.py` | D-12 prompt freezing | ✓ VERIFIED | Exists, used live in plan 09 to produce `fixtures/llm_repeatability/rule_ingest_prompts/` |
| `deterministic-evidence/de01-repeat-report.{json,md}` | Live D-08 gate evidence | ✓ VERIFIED | Exists, read directly, FAIL honestly recorded, owner-approved |
| `llm-evidence/llm-repeatability-report.{json,md}` | Live D-24/D-27 LLM evidence | ✓ VERIFIED | Exists, read directly, schema-valid, non-claim banner present |
| `fixtures/llm_repeatability/cassettes/rule_ingest/` | 50 recorded live samples | ✓ VERIFIED | Confirmed by SUMMARY (5 items × k=10); MANIFEST.md digests spot-checked |
| `spec/API.md` (extended) | LLM Gateway subsection | ✓ VERIFIED | New `### LLM Gateway` subsection documenting the 3 fields |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run_de01_repeat.py` | `projection_hash.verdict_projection_hash` | direct import/call per iteration | WIRED | Confirmed by code read and green `TestRepeatRunnerGate` tests |
| `run_de01_repeat.py` | `report_schema_repeat.json` | live report JSON validated against schema | WIRED | Live report in `deterministic-evidence/` conforms (plan-08 SUMMARY + my read) |
| `repeat_sweep.py` | `llm_gateway.GenerateResponse` (D-20 fields) | reads `served_model`/`response_id`/`system_fingerprint` off the response | WIRED | `run_one_item` in `repeat_sweep.py` stamps these into the provenance block; exercised live in plan 09 |
| `repeat_sweep.py` | `cassette.py` (D-21 `sample_index`) | `CassetteAdapter(sample_index=s)` for `s in 1..REPEAT_SAMPLES` | WIRED | Confirmed by code read; live cassette count (50 = 5×10) matches |
| `repeat_sweep.py` | `outcome_taxonomy.classify` | per-sample classification | WIRED | Outcome tallies in the live report show real `truncated`/`valid` counts, not stubs |
| `report_schema_llm.json` (item field) | `repeat_sweep.compute_item_metrics` output shape | schema now matches the multi-item output shape | WIRED | Additive diff confirmed; `test_repeat_sweep.py` (14 tests, re-run by me) still green |
| `report.py::render_llm_repeatability_markdown` | live report dict shape (`providerStrata`) | **NOT WIRED (latent bug, non-blocking)** | ⚠️ see Anti-Patterns | Function reads `report["strata"]`/`report["providers"]`, but the real schema key is `providerStrata` — falls through to a raw `str(report)` dump if called on a real schema-shaped dict. Plan 1204-09 worked around it by building the markdown directly rather than calling this function; the actual `llm-repeatability-report.md` deliverable is correct. Disclosed in the 1204-09 SUMMARY as a defect for a future phase to fix. |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| ALGN12-15 | 01, 03, 04, 05, 06, 07, 08, 09 | Deterministic validator repeatability measured separately from LLM proposal repeatability/abstention/invalid-output | ✓ SATISFIED | Two structurally separate benchmarks (DE-01 repeat runner vs. LLM repeat sweep), two separate schemas with no shared score field, live evidence for both |
| ALGN12-16 | 02, 03, 04, 06, 07, 08, 09 | Provider/model/prompt/configuration snapshots sufficient to reproduce the declared AI experiment or explain why not | ✓ SATISFIED | D-07 config pins (git commit, image ids, fixture hashes, versions) in the deterministic report; D-12 frozen prompts + D-19 per-sample provenance + D-22 reproducibility class in the LLM report |

No orphaned requirements: `.planning/REQUIREMENTS.md:75` records exactly 2 requirements mapped to Phase 1204, matching ALGN12-15/ALGN12-16.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `data-service/tests/recognition_eval/report.py` | 530-539 | `render_llm_repeatability_markdown` reads `report["strata"]`/`report["providers"]`, but the schema field the pipeline actually produces is `providerStrata` | ⚠️ Warning | Latent/dead-path bug in a harness-only test-support module; does not affect the actual delivered evidence (plan 1204-09 built the markdown directly, bypassing this function); openly disclosed in the 1204-09 SUMMARY as a defect for a future phase to reconcile; the existing test for this function (`test_llm_repeatability_markdown_renders_per_provider`) uses a synthetic `"strata"` key rather than the real `providerStrata` shape, so it doesn't catch the mismatch |
| `.planning/phases/.../1204-09-SUMMARY.md` | — | Plan 1204-09's Task 4 `checkpoint:human-verify` required recording the owner's verdict text in the plan summary (D-28); the summary records both report file sha256 values but not an explicit "Owner verdict: approved" line (unlike 1204-08's summary, which has one) | ⚠️ Warning | Documentation completeness gap only. The orchestrator's own task framing states both plans 08 and 09 had owner-approved checkpoints, `autonomous: false` on the plan confirms a live checkpoint gate was in place, and the live evidence artifacts exist and are complete — but the explicit verdict text is missing from the written record |
| `CLAUDE.md` | — | 42-line uncommitted diff (40 pre-existing owner lines + 2 new "Reproducibility contract" lines) | ℹ️ Info | Deliberate and documented in the 1204-06 SUMMARY — left uncommitted per the plan's own instruction so the owner can commit it together with their own pending edit. Not a phase gap. |

No debt markers (`TBD`/`FIXME`/`XXX`) found in any phase-1204-modified file (checked by direct grep).

### Human Verification Required

None outstanding. Both `checkpoint:human-verify` gates in this phase (plan 1204-08 Task 3, plan 1204-09 Task 4) were live, blocking checkpoints executed during the phase itself, not deferred to end-of-phase — 1204-08's SUMMARY explicitly records "Owner verdict: approved"; 1204-09's checkpoint is corroborated by the task's own execution framing plus the recorded report sha256 values, with the one gap being a documentation-completeness item (see Anti-Patterns above), not an open verification task.

### Gaps Summary

No blocking gaps. All 12 observable truths derived from the roadmap's phase deliverables/gate and the 9 plans' `must_haves` frontmatter are verified against the actual codebase — not merely SUMMARY.md claims. Every referenced pytest command was re-run independently in this verification pass and matched the SUMMARY.md claims exactly (124 passed for `tools/de01/tests/`, 62 passed for `test_llm_gateway.py`, 14 passed for `test_repeat_sweep.py`, 4 passed for the scope-drift guard, 146 passed for the full recognition_eval regression, 4 pre-existing failures reproduced exactly in `test_dg_context.py` with zero file overlap to phase-1204 commits). The two live evidence report files were read directly (not just their SUMMARY descriptions) and their content matches the SUMMARY claims verbatim, including the D-08 gate's disclosed FAIL and the explicit non-universal-determinism language required by the phase goal.

Two non-blocking Warnings are recorded for awareness: a latent dead-path bug in `report.py`'s markdown emitter (worked around, not fixed, in the actual deliverable), and a documentation-completeness gap in 1204-09's SUMMARY around the owner-verdict text for its human checkpoint.

---

_Verified: 2026-09-28T17:49:45Z_
_Verifier: Claude (gsd-verifier)_
