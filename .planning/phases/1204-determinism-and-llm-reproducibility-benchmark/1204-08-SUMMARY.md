# Plan 1204-08 Summary — Live Deterministic Half of the 1204 Benchmark

## What was built

`.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/deterministic-evidence/de01-repeat-report.{json,md}` — the live DE-01 repeat-benchmark evidence pair, produced by running `tools/de01/run_de01_repeat.py` (plan 1204-05) against the freshly rebuilt Docker Compose stack across two process-lifetime batches.

## Preflight (Task 1)

- `python -m pytest tools/de01/tests/ -x -q -k "not live"` — 124 passed (green before the live run).
- `docker compose build --no-cache data-service` — clean build.
- `docker compose up -d data-service` — container recreated.
- Stale-image guard: `grep -c served_model /app/llm_gateway.py` inside the container → 5 (≥1, pass); running container image id (`sha256:5c62d4ab...`) matched the freshly built image id exactly.
- Golden fixture seed confirmed present (`:Run {Run_Id: 'RUN_GOLD_1200'}` resolves in Neo4j).
- `dotnet build DG/DG.sln -c Release` — clean build, 0 warnings, 0 errors (csharp leg harness current).

**One production bug found and fixed during this preflight** (not by this plan's own scope, but blocking any live run): `run_leg_replay_pinned` in `tools/de01/run_de01_repeat.py` (shipped by plan 1204-05) crashed on any real HTTP response — it called `evidence_contract.validate_envelope(envelope_dict)` on a plain dict, but that function expects an already-built pydantic model and calls `.model_dump()` on it. It also signals failure by raising, never by returning non-`None`, so the code's own `if validated is not None:` branch could never have worked either way. This was invisible to 1204-05's hermetic tests because they mocked the buggy call into a no-op. Fixed in a separate commit (`2615ae1`) to mirror `run_leg_replay`'s proven pattern exactly (validate via `legs._validated_leg_result`, re-stamp `stage`, re-attach `canonicalStateHash`) — not part of this plan's own artifact set, but required before any live run of 1204-05's own runner could proceed at all.

## Live run (Task 2)

```
python tools/de01/run_de01_repeat.py --iterations 10 --batches 2 \
  --out-dir .planning/phases/1204-determinism-and-llm-reproducibility-benchmark/deterministic-evidence \
  --services "data-service dg-reasoner"
```

- Exit completed; JSON validates against `tools/de01/report_schema_repeat.json`.
- One restart round recorded between batch 1 (iterations 1–5) and batch 2 (6–10), with distinct per-service container start timestamps for `data-service` and `dg-reasoner` (both recreated).
- D-07 config block complete: git commit, dirty flag, image ids (all three services), dotnet SDK 10.0.301/Release, fixture sha256 pins, contract version 1.0.0, canonicalization version 1, pinned replay run id (`b606720b...`, captured from iteration 1's data-service publish per D-06 — the `:Run` vs `:ValidationRun` label drift is recorded as a finding, not fixed), N=10, batches=2, and the stale-image-check note.

### D-08 gate result: **FAIL**

| Leg | Role | Distinct hashes | Verdict |
|---|---|---|---|
| data-service | relay | **2** | **FAIL** |
| dg-reasoner | evaluator | 1 | PASS |
| csharp | evaluator | 1 | PASS |
| replay | relay | 1 | PASS |

- `silent_disagreement_count == 0` in every one of the 10 iterations — no cross-leg comparison issue.
- The single diverging pair: `data-service` iteration 1 vs iteration 6 (hashes `B20E74EF...` vs `19BF1B63...`). Iterations 7–10 **revert** to the original iteration-1 hash — the divergence is isolated to the single iteration immediately following the batch restart, not a sustained post-restart state shift.
- Per D-08, no code, fixture, or exclusion-list change was made to clear this divergence. The finding is recorded verbatim in both report files, exactly as measured.
- Non-proof statement present verbatim in the .md: "N/N identical does not prove determinism; it fails to falsify it for this fixture, build and configuration."
- Label-drift finding present verbatim (see D-06 note above).

## Prohibition gates (all pass)

- `universal.{0,20}determin` grep on both report files: 0.
- Key-material grep (`api[_-]?key|bearer|credentialed|/settings`) on both report files: 0.
- `.secrets` grep on both report files: 0.
- `git status --porcelain -- tools/de01/legs.py tools/de01/report.py fixtures/golden/ data-service/app.py`: empty (no source/fixture drift from the run itself).

## Owner checkpoint (Task 3)

Presented to the owner: per-leg hash counts, silent-disagreement counts, `leg_role` mapping, D-07 config-pin completeness, the label-drift finding, the non-proof statement, and the restart evidence — plus the orchestrator's own read that the divergence pattern (isolated to iteration 6 only) suggests a transient blip at the restart boundary rather than a stable configuration shift, offered as context, not as an explanation that excuses or reclassifies the failure.

**Owner verdict: approved.** The D-08 gate failure is accepted as the recorded, disclosed finding — the benchmark's own purpose is to falsify a determinism claim it cannot support, and it did exactly that for the `data-service` relay leg on one of ten iterations.

**Report file sha256:**
- `de01-repeat-report.json`: `e33163c0e13d3717c1da143619b227c53bc78ef2e9a90f09ea41166158fd18ec`
- `de01-repeat-report.md`: `729a98a3ffb7ac71321aec95412cec501cd79d80a05ab15e20282f3eed961ad5`

## Key files

- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/deterministic-evidence/de01-repeat-report.json` (new)
- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/deterministic-evidence/de01-repeat-report.md` (new)

## Execution note

Run directly by the orchestrator (not via DSH) at the user's explicit request, given the live infrastructure (Docker restarts) and human-checkpoint nature of this plan. The `run_leg_replay_pinned` crash was diagnosed and fixed inline before the run could proceed; the D-08 gate failure itself was left untouched and reported as measured, per plan and per D-08's explicit prohibition on tuning the exclusion list or otherwise "fixing" a divergence.
