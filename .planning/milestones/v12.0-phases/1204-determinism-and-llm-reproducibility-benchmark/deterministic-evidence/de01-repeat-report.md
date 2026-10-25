# DE-01 Deterministic Repeat Benchmark Report

**D-08 gate verdict:** FAIL
**Iterations:** 10
**Batches:** 2
**Pinned replay run id (D-06):** b606720bb0f24d6faf95133369bc398c
**Projection version:** 1
**Generated:** 2026-09-24T01:17:15Z

Gate rule (D-08): passes iff every leg produced exactly one distinct projection hash across all N iterations AND `silent_disagreement_count == 0` in every iteration. Nothing is averaged; a single divergence fails.

## Per-leg projection stability

| Leg | Role | Iterations | Distinct hashes | Leg verdict |
|---|---|---|---|---|
| data-service | relay | 10 | 2 | FAIL |
| dg-reasoner | evaluator | 10 | 1 | PASS |
| csharp | evaluator | 10 | 1 | PASS |
| replay | relay | 10 | 1 | PASS |

Roles are `LEG_ROLES` (D-02): only `evaluator` legs (csharp, dg-reasoner) may carry a validator-determinism claim. `relay` legs (data-service, replay) echo or re-read persisted evidence, so the table above reports round-trip stability for them, never validator repeatability.

## Per-iteration silent disagreement counts

| Iteration | silent_disagreement_count |
|---|---|
| 1 | 0 |
| 2 | 0 |
| 3 | 0 |
| 4 | 0 |
| 5 | 0 |
| 6 | 0 |
| 7 | 0 |
| 8 | 0 |
| 9 | 0 |
| 10 | 0 |

## Diverging pairs (D-08 failure evidence)

- `{"hash_a": "B20E74EF8C7534AC40D4719A1B5E9277CEAE77E7BB3DF5006114A4B1E548BEEB", "hash_b": "19BF1B630B680326567DED0FD205E6D8FB1B79723605085C4576CFF8E695C26F", "iteration_a": 1, "iteration_b": 6, "leg": "data-service"}`

## Configuration pins (D-07)

- **git_commit:** 2615ae19b00f4a1160a5f62e81797156bc6c135b
- **git_dirty:** True
- **dotnet_sdk_version:** 10.0.301
- **build_configuration:** Release
- **contract_version:** 1.0.0
- **canonicalization_version:** 1
- **pinned_replay_run_id:** b606720bb0f24d6faf95133369bc398c
- **iterations:** 10
- **batches:** 2
- **fixture_version:** 1.3.0
- **image_ids:** `{"data-service": "1410e0f03ce2055d547d78108d215991ba90fb73fc75d3a02707471482d0dca8", "dg-reasoner": "dcd4ab1c232305809742f7776fabffc446afb86a3386c9edbe6c70cbefda3e38", "neo4j": "46abd0ec9de55d560c4054a4ab05ae500c8558cef73eaa8640f269ec415f2308"}`
- **fixture_sha256:** `{"fixtures/golden/fixture.json": "3cc9fe377f7c5bf12becc4624dcd95a341a90adc3be9514f4539d037fae65d40", "fixtures/golden/replay/mixed-verdicts.json": "56ab68a809262f35a3f9861e1e7d4272391701756e36e81d7706802204cefd81"}`
- **service_versions:** `{"csharp": "unknown", "data-service": "unknown", "dg-reasoner": "unknown", "replay": "unknown"}`
- **stale_image_check.checked:** False
- **stale_image_check.note:** The running image id(s) below were recorded from the live daemon, but whether each image actually contains the code under test was NOT verified by this run. docker compose reuses a previously built image when the compose file and Dockerfile inputs are unchanged, so a stale image can mask a source change: before treating an N/N result as evidence for THIS commit, rebuild (docker compose build) or confirm image ids match a build of git_commit. Recorded image ids: {'data-service': '1410e0f03ce2055d547d78108d215991ba90fb73fc75d3a02707471482d0dca8', 'dg-reasoner': 'dcd4ab1c232305809742f7776fabffc446afb86a3386c9edbe6c70cbefda3e38', 'neo4j': '46abd0ec9de55d560c4054a4ab05ae500c8558cef73eaa8640f269ec415f2308'}.

## Findings

- Run-identity label drift (1204-CONTEXT.md Correction 4): the golden seed writes :Run {Run_Id: 'RUN_GOLD_1200'} (legs.py:47), but data-service's GET /validation/view/{project}/{run_id} matches :ValidationRun {runId} (app.py:685) -- so the seeded literal does not resolve through the pinned route. The D-06 pin is therefore the run id minted by iteration 1's data-service publish (a :ValidationRun.runId the route demonstrably resolves), recorded in this report's config block. Recorded as a finding; not fixed here (D-10 measure as shipped, and this plan adds no production change).

## Non-proof statement (D-05)

N/N identical does not prove determinism; it fails to falsify it for this fixture, build and configuration.
