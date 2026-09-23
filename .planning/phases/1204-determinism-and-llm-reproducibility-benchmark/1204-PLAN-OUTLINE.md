# Phase 1204 — Plan Outline (chunked, outline-only)

**Phase:** 1204-determinism-and-llm-reproducibility-benchmark
**Requirements:** ALGN12-15, ALGN12-16
**Gate:** reports deterministic and model-dependent results separately, with confidence/limitations.

## Plan Table

| Plan ID | Objective | Wave | Depends On | Requirements | Decisions (D-NN) | Files (create/modify) | Autonomous |
|---|---|---|---|---|---|---|---|
| 1204-01 | Deterministic projection-hash tracer: D-04 exclusion-list canonical hash over leg envelopes using `canonical_json.hash_canonical` (never `hash_scalar_tuple`), plus the negative control (mutated status/warning must change the hash; re-ordered rows must not) | 1 | — | ALGN12-15 | D-04 | C: `tools/de01/projection_hash.py`, `tools/de01/tests/test_repeat_runner.py` | Yes |
| 1204-02 | D-20 gateway provenance tracer: additive optional `served_model` / `response_id` / `system_fingerprint` fields on `GenerateResponse`, populated only from what each adapter actually returns (`.get` + `None` defaults), per-adapter tests, new `spec/API.md` subsection | 1 | — | ALGN12-16 | D-20 | M: `data-service/llm_gateway.py`, `data-service/tests/test_llm_gateway.py`, `spec/API.md` | Yes |
| 1204-03 | D-21 sample-indexed cassette key: ninth `sample_index` key part (default 0 = byte-identical to today's eight-part digest), flip-test rows and backward-compat assertion in `TestCassette` | 1 | — | ALGN12-15, ALGN12-16 | D-21 | M: `data-service/tests/recognition_eval/cassette.py`, `data-service/tests/test_recognition_eval.py` | Yes |
| 1204-04 | LLM sample classification + provenance guards: D-14 taxonomy module (valid / valid_after_retry / invalid+path violation code / abstained / truncated / refused / provider_error — verdict vocabulary never reused), D-15 first-attempt-vs-final + attempts distribution inputs, D-16 explicit-channel-only abstention (G6 excluded, rule-ingest = "not supported by output contract"), D-18 oracle-free (no expected-label comparison), D-19 extended provenance field tuple + void guard in `corpus.py`; harness-side only (D-23: no production/envelope change) | 1 | — | ALGN12-15, ALGN12-16 | D-14, D-15, D-16, D-18, D-19, D-23 | C: `data-service/tests/recognition_eval/outcome_taxonomy.py`, `data-service/tests/recognition_eval/test_outcome_taxonomy.py`, `data-service/tests/recognition_eval/test_provenance.py`; M: `data-service/tests/recognition_eval/corpus.py` | Yes |
| 1204-05 | Deterministic repeat runner: imports `legs.py` runners and `report.compare_legs` verbatim (D-01), pinned-replay variant (D-06), N=10 across ≥2 `docker compose restart` batches with container-id/start-time recording (D-05), `leg_role: evaluator\|relay` column (D-02), D-07 configuration pins, D-08 N/N gate + JSON/MD report emitter with its own schema | 2 | 1204-01 | ALGN12-15 | D-01, D-02, D-05, D-06, D-07, D-08 | C: `tools/de01/run_de01_repeat.py`, `tools/de01/report_schema_repeat.json`; M: `tools/de01/tests/test_repeat_runner.py` | Yes |
| 1204-06 | Normative `spec/REPRODUCIBILITY.md`: determinism classes, scope table (D-03 unmeasured rows; D-11 consult/input-gen rows), D-22 reproducibility classes, D-04 projection + exclusion list, D-19 field list, explicit non-claims; D-26 machine-checked LLM call-site fenced block + drift test (with induced-mismatch proof); `CLAUDE.md` governing-spec pointer | 2 | 1204-01 | ALGN12-15, ALGN12-16 | D-03, D-11, D-22, D-25, D-26 | C: `spec/REPRODUCIBILITY.md`, `tools/de01/tests/test_reproducibility_scope_drift.py`; M: `CLAUDE.md` | Yes |
| 1204-07 | LLM sampling driver + aggregation: `repeat_sweep.py` (k=10 per item per provider, min-5 rate floor, never pooled, adapter-resolve-once, rule-ingest with no `GenerationOptions` = "not sent — provider default" finding per D-10), D-12 freeze script for the five rendered rule-ingest prompts, D-17 per-item two-level normalization (raw bytes; declared level-2) with distinct-output count / modal-agreement rate / Wilson CI, D-21 regeneration check, LLM report emitter + own schema (D-24) | 2 | 1204-02, 1204-03, 1204-04 | ALGN12-15, ALGN12-16 | D-09, D-10, D-12, D-13, D-17, D-21, D-24 | C: `data-service/tests/recognition_eval/repeat_sweep.py`, `data-service/tests/recognition_eval/freeze_rule_ingest_prompts.py`, `data-service/tests/recognition_eval/report_schema_llm.json`; M: `data-service/tests/recognition_eval/report.py` | Yes |
| 1204-08 | LIVE deterministic half (human checkpoint, D-28): rebuild/verify images hold the code under test (stale-image guard), run `run_de01_repeat.py` against the compose stack across ≥2 process lifetimes, D-08 gate with `silent_disagreement_count = 0` every iteration, emit deterministic-report.{json,md} with full D-07 config pins and the required "N/N does not prove determinism" statement | 3 | 1204-05, 1204-06 | ALGN12-15, ALGN12-16 | D-05, D-07, D-08, D-24, D-28 | C: `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/deterministic-evidence/deterministic-report.{json,md}` | No (human checkpoint) |
| 1204-09 | LIVE LLM half (human checkpoint, D-28): freeze the five rule-ingest prompts against a seeded project via `/context/assemble` + the repo's "Build LLM Prompt" node logic (D-12), k=10 live sampling of recognition + rule-ingest per reachable provider (key entered only via the LLM settings panel), full D-19 provenance per sample, D-22 class per experiment, emit llm-repeatability-report.{json,md} with confidence intervals + limitations, D-27 gate (≥1 live provider at k≥5; no pass threshold) | 3 | 1204-06, 1204-07 | ALGN12-15, ALGN12-16 | D-12, D-13, D-22, D-24, D-27, D-28 | C: `fixtures/llm_repeatability/**` (rule_ingest_prompts/ + cassettes/ + MANIFEST), `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/llm-evidence/llm-repeatability-report.{json,md}` | No (human checkpoint) |

## D-06 pin-resolution approach (established fact, not re-investigated)

Established by the orchestrator: `data-service/app.py:685` `get_validation_run` matches
`(run:ValidationRun {graph, project}) WHERE run.runId = $runId`; the golden seed writes
`:Run {Run_Id:'RUN_GOLD_1200'}` — so `GET /validation/view/{project}/RUN_GOLD_1200` does **not**
resolve today.

**Chosen approach (most consistent with CONTEXT.md):** 1204-05's pinned-replay variant pins the
run id minted by iteration 1's data-service publish — a `:ValidationRun.runId` the route
demonstrably resolves (the data-service leg already reads back its own publish through this exact
route, `legs.py:230`). The pin is captured at iteration 1 and held fixed for all N replay reads;
the pinned run id is recorded in the report's D-07 configuration block. The `:Run{Run_Id}` vs
`:ValidationRun{runId}` label drift is reported as a finding (Correction 4 already documents it).
No production change (D-10 measure-as-shipped discipline), no frozen-fixture edit.

**One-way door?** No — the pin is recorded in the committed evidence (self-describing); switching
pin schemes later is a new experiment, not a re-interpretation of committed hashes. No
`checkpoint:decision` required. *(Flag: if a reviewer later wants the pinned id to be the golden
`RUN_GOLD_1200` itself, that would require a sibling `:ValidationRun` seed — a decision, not the
default.)*

## Decision coverage

- **D-01** → 1204-05 (runner imports `legs.py` leg functions and `report.compare_legs` verbatim; no reimplementation)
- **D-02** → 1204-05 (`leg_role: evaluator|relay` column in `report_schema_repeat.json` and every emitter row)
- **D-03** → 1204-06 (scope-table `unmeasured` rows: `cg_structure_checks`, HermiT, Tier-0 paths, SHACL non-golden, live GH/canvas)
- **D-04** → 1204-01 (projection hash, closed exclusion list, producer hashes recorded as-is, negative control)
- **D-05** → 1204-05 (N=10, ≥2 restart batches, container ids/start times, required N/N statement); executed by 1204-08
- **D-06** → 1204-05 (pinned replay; approach above)
- **D-07** → 1204-05 (config-pin collection in the emitter; stale-image check); executed by 1204-08
- **D-08** → 1204-05 (one-distinct-hash-per-leg gate + per-iteration `silent_disagreement_count = 0` + diverging-pair recording); enforced by 1204-08
- **D-09** → 1204-07 (recognition primary, rule-ingest secondary subjects)
- **D-10** → 1204-07 (rule-ingest sampled with no `GenerationOptions`; temperature recorded as "not sent — provider default" finding)
- **D-11** → 1204-06 (consult + input generation rows: model-dependent, unmeasured)
- **D-12** → 1204-07 (freeze script authored); capture executed by 1204-09
- **D-13** → 1204-07 (k=10, min-5 rate floor, per-provider stratification, availability recording); executed by 1204-09
- **D-14** → 1204-04 (taxonomy module; proposal vocabulary, verdict vocabulary never reused)
- **D-15** → 1204-04 (first-attempt vs final invalid rates + attempts-distribution inputs)
- **D-16** → 1204-04 (explicit-channel abstention; G6-autofill excluded; rule-ingest "not supported by output contract")
- **D-17** → 1204-07 (per-item two normalization levels, distinct outputs, modal-agreement rate, Wilson CI; no pooled score)
- **D-18** → 1204-04 (taxonomy is oracle-free — no expected-label input) + 1204-07 (report schema excludes accuracy fields)
- **D-19** → 1204-04 (extended `REQUIRED_PROVENANCE_FIELDS` + void guard)
- **D-20** → 1204-02 (additive gateway fields, tests, `spec/API.md` docs)
- **D-21** → 1204-03 (sample-index key, backward-compatible default) + 1204-07 (byte-for-byte regeneration check labelled "scoring-pipeline determinism")
- **D-22** → 1204-06 (class definitions in spec); per-experiment assignment in 1204-09
- **D-23** → 1204-04 (guard lives in the harness; verify `data-service/evidence_contract.py` + `spec/evidence-contract.schema.json` untouched) + 1204-06 (spec scopes provenance to the declared experiment)
- **D-24** → 1204-05 (deterministic report schema + emitter) + 1204-07 (LLM report schema + emitter); evidence files emitted by 1204-08/1204-09
- **D-25** → 1204-06 (spec contents incl. non-claims; `CLAUDE.md` pointer)
- **D-26** → 1204-06 (fenced call-site block + drift test incl. induced-mismatch proof)
- **D-27** → 1204-09 (complete-provenance report, ≥1 live provider at k≥5, CI + limitations, no pass threshold)
- **D-28** → 1204-08 + 1204-09 (checkpoint:human-verify tasks; provider keys only via LLM settings panel / `/llm/settings`)

All 28 decisions are trackable — no informational entries.

## Cross-plan seams

- `tools/de01/tests/test_repeat_runner.py` — created by **1204-01** (projection-hash + negative-control tests), extended by **1204-05** (runner tests). Serialized by wave (1 → 2).
- `data-service/tests/recognition_eval/corpus.py` — modified by **1204-04** only (D-19 field-tuple + guard extension).
- `data-service/tests/test_recognition_eval.py` — modified by **1204-03** only (sample-index flip/backward-compat tests).
- `data-service/tests/recognition_eval/report.py` — modified by **1204-07** only (D-17 aggregation + LLM emitter).
- `data-service/llm_gateway.py` — modified by **1204-02** only (additive D-20 fields; no other plan touches production LLM code — D-10/D-23).
- `CLAUDE.md` — modified by **1204-06** only (governing-spec pointer).
- Phase evidence: **1204-08** owns `deterministic-evidence/`; **1204-09** owns `llm-evidence/` — disjoint subdirectories.
- `fixtures/llm_repeatability/**` — populated only by **1204-09** (1204-07 authors the freeze script; the live capture writes the fixture tree).
- Frozen inputs, modified by **no** plan: `tools/de01/legs.py`, `tools/de01/report.py`, `data-service/canonical_json.py`, `fixtures/golden/*`, `data-service/fixtures/recognition_eval/cassettes/`, `spec/EVIDENCE-CONTRACT.md`, `spec/evidence-contract.schema.json`, `n8n/workflows/rules-to-metagraph.json` (read-only rendering source for D-12).

## OUTLINE COMPLETE
