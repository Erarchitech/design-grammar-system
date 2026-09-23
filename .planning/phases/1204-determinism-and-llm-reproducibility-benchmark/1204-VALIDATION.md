---
phase: 1204
slug: determinism-and-llm-reproducibility-benchmark
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-23
---

# Phase 1204 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `1204-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`tools/de01/tests/`, `data-service/tests/`); xUnit (`DG/tests/DG.Tests/`) |
| **Config file** | none — tests are invoked by path (convention in `tools/de01/README.md`) |
| **Quick run command** | `python -m pytest tools/de01/tests/test_repeat_runner.py -x -q -k "not live"` |
| **Full suite command** | `python -m pytest tools/de01/tests/ -x -q && python -m pytest data-service/tests/recognition_eval/ data-service/tests/test_recognition_eval.py data-service/tests/test_llm_gateway.py -x -q && dotnet test DG/tests/DG.Tests/` |
| **Estimated runtime** | ~120 seconds (non-live); the live checkpoints are open-ended |

---

## Sampling Rate

- **After every task commit:** run the relevant `-k "not live"` unit subset for any task that touches `projection_hash.py`, the extended `cassette.py`, the outcome-taxonomy module, the provenance assertions, or the D-20 gateway fields.
- **After every plan wave:** run the full non-live suite command above.
- **Before `/gsd-verify-work`:** the full non-live suite must be green, and both live human checkpoints (D-28: the deterministic-half compose-stack run and the LLM-half live-provider sampling run) must have produced their reports.
- **Max feedback latency:** 120 seconds
- **Known env baseline:** four `DesignStateValidationFlowTests` (DG.Tests) and four `test_dg_context.py` tests fail when Neo4j is unreachable from the host. These failures come from the environment and are not regressions.

---

## Per-Task Verification Map

Task IDs are filled in by the planner and the executor. The rows below map requirements to the checks that sample them.

| Req / Decision | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|----------------|----------|------------|-----------------|-----------|-------------------|-------------|--------|
| ALGN12-15 (det.) | N=10 over ≥2 process lifetimes gives N/N identical projection hashes; a negative control detects a mutated status | — | N/A | unit | `python -m pytest tools/de01/tests/test_repeat_runner.py -x -q -k "not live"` | ❌ W0 | ⬜ pending |
| ALGN12-15 (det., live) | The live compose-stack run reaches `silent_disagreement_count = 0` and passes the D-08 N/N gate | — | N/A | human checkpoint | `python tools/de01/run_de01_repeat.py` | ❌ W0 | ⬜ pending |
| ALGN12-15 (LLM) | The outcome taxonomy classifies valid / valid_after_retry / invalid(+code) / abstained / truncated / refused / provider_error | — | N/A | unit | `python -m pytest data-service/tests/recognition_eval/test_outcome_taxonomy.py -x -q` | ❌ W0 | ⬜ pending |
| ALGN12-15 (LLM sampling) | k=10 samples per item use distinct sample-indexed cassette keys; modal agreement and the Wilson CI are computed correctly | T-provenance-leak | full prompt bodies are stored only for `ip_class == "own"` | unit + human checkpoint | `python -m pytest data-service/tests/test_recognition_eval.py -x -q -k "sample_index"` (cassette tests live in `TestCassette`, `test_recognition_eval.py:63`) | partial | ⬜ pending |
| ALGN12-16 | Every sample carries a complete D-19 provenance block; a sample missing any field is void | T-provenance-leak | no API key and no credentialed URL in the provenance | unit | `python -m pytest data-service/tests/recognition_eval/test_provenance.py -x -q` | ❌ W0 | ⬜ pending |
| ALGN12-16 (D-20) | The gateway fills served-model / response-id / fingerprint per adapter; a field the provider omits is `None` | T-provider-input | provider response JSON is read defensively with `.get` | unit | `python -m pytest data-service/tests/test_llm_gateway.py -x -q -k "served_model or response_id or fingerprint"` | partial | ⬜ pending |
| D-26 | The scope table in `spec/REPRODUCIBILITY.md` stays in sync with the LLM call sites in `data-service/` | — | N/A | unit (drift) | `python -m pytest tools/de01/tests/test_reproducibility_scope_drift.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/de01/projection_hash.py`: D-04 exclusion-list projection hash
- [ ] `tools/de01/run_de01_repeat.py` + `tools/de01/tests/test_repeat_runner.py`: N-iteration, multi-batch driver with the D-04 negative control
- [ ] `tools/de01/report_schema_repeat.json`: sibling schema for the repeat report (D-24)
- [ ] sample-index extension to `data-service/tests/recognition_eval/cassette.py` + `TestCassette` coverage in `data-service/tests/test_recognition_eval.py`
- [ ] `data-service/tests/recognition_eval/repeat_sweep.py`: k=10 sampling driver for recognition + rule-ingest
- [ ] `data-service/tests/recognition_eval/test_outcome_taxonomy.py`
- [ ] `data-service/tests/recognition_eval/test_provenance.py`: extend `corpus.py`'s `REQUIRED_PROVENANCE_FIELDS` / `assert_provenance` rather than duplicating it
- [ ] `fixtures/llm_repeatability/rule_ingest_prompts/`: five frozen, sha256-pinned rendered prompts (D-12)
- [ ] `spec/REPRODUCIBILITY.md` + its D-26 machine-checked fenced block + drift test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Deterministic-half live repeat run across ≥2 compose-stack process lifetimes | ALGN12-15 | needs the live compose stack and container restarts; stale images mask code state | rebuild the affected images, confirm the container holds the current code, then run `run_de01_repeat.py` and inspect the repeat report |
| LLM-half live-provider sampling (k=10) | ALGN12-15, ALGN12-16 | needs a live provider key, which is entered only through the LLM settings panel, and the sampling costs API money | configure the provider through the settings panel, run the repeat sweep in record mode, and confirm the report carries full provenance and a reproducibility class |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
