---
phase: 35-llm-recognition-canvas-preview
reviewed: 2026-07-27T00:00:00Z
depth: standard
iteration: 4
scope: full phase (SUMMARY-derived, 41 source files)
files_reviewed: 41
files_reviewed_list:
  - DG/src/DG.Core/Models/Computgraph/RawCanvas.cs
  - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs
  - DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs
  - DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
  - DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs
  - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
  - DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
  - DG/tests/DG.Tests/CanvasAnnotationParserRecognizedSourceTests.cs
  - DG/tests/DG.Tests/CanvasAnnotationParserTests.cs
  - DG/tests/DG.Tests/Fixtures/frame-cg-context.json
  - DG/tests/DG.Tests/FrameAblatedCorpusEmitterTests.cs
  - DG/tests/DG.Tests/FrameFixtureTests.cs
  - data-service/app.py
  - data-service/cg_recognition.py
  - data-service/cg_schemas.py
  - data-service/cg_topology.py
  - data-service/fixtures/frame_recognition_fewshot.json
  - data-service/fixtures/recognition_eval/frame_ablated.context.json
  - data-service/fixtures/recognition_eval/frame_ablated.expected.json
  - data-service/fixtures/recognition_eval/urbanblock_slice.context.json
  - data-service/fixtures/recognition_eval/urbanblock_slice.expected.json
  - data-service/gh_bridge.py
  - data-service/llm_gateway.py
  - data-service/prompts/recognition_system.md
  - data-service/requirements.txt
  - data-service/tests/conftest.py
  - data-service/tests/recognition_eval/__init__.py
  - data-service/tests/recognition_eval/arms.py
  - data-service/tests/recognition_eval/cassette.py
  - data-service/tests/recognition_eval/corpus.py
  - data-service/tests/recognition_eval/live_sweep.py
  - data-service/tests/recognition_eval/report.py
  - data-service/tests/recognition_eval/scoring.py
  - data-service/tests/test_cg_recognition.py
  - data-service/tests/test_cg_schemas.py
  - data-service/tests/test_cg_topology.py
  - data-service/tests/test_gh_bridge.py
  - data-service/tests/test_llm_gateway.py
  - data-service/tests/test_recognition_eval.py
  - data-service/tests/test_recognition_scoring.py
findings:
  critical: 3
  warning: 9
  info: 5
  total: 17
status: issues_found
---

# Phase 35: Code Review Report — iteration 4

**Reviewed:** 2026-07-27
**Depth:** standard
**Files Reviewed:** 41 (full-phase SUMMARY-derived scope)
**Status:** issues_found
**Baseline at review time:** `pytest tests/test_recognition_eval.py tests/test_recognition_scoring.py -q` → **89 passed, 1 skipped, 1 deselected**

## Scope note — why this iteration exists

Iterations 1 and 2 (`35-REVIEW.iter2.md`) covered the C# preview/accept path and the
`/computgraph/recognize` endpoint at 15–18 files; their findings were fixed
(`35-REVIEW-FIX.md`, `35-REVIEW-FIX.iter2.md`). Iteration 3 (`35-REVIEW.iter3.md`) reviewed
**wave 5 only** (4 files) and reported 17 findings — **none of which were ever fixed**;
no `35-REVIEW-FIX.iter3.md` exists.

This iteration widens back to the full phase scope (41 files) and **independently
re-verified every iteration-3 finding against current `HEAD`**. All 17 are still present.
No new defect was found in the files that iterations 1–3 never covered
(`scoring.py`, `corpus.py`, `cassette.py`, `cg_topology.py`, `cg_schemas.py`,
`llm_gateway.py`, `conftest.py`, the C# test files and the JSON fixtures) beyond the
`conftest.py` item already filed as IN-01.

The full defect analysis, reproduction transcripts and suggested patches live in
`35-REVIEW.iter3.md` and are **not duplicated here**. This document records the
re-verification evidence and the current line anchors, so the fixer works from
confirmed state rather than from a stale report.

## Re-verification evidence (run at review time, current HEAD)

```
A0:  examples=1  perms=3  distinct=1   real_negotiated=none         naive=none
A0f: examples=1  perms=3  distinct=1   real_negotiated=none         naive=none
A3:  examples=5  perms=3  distinct=3   real_negotiated=none         naive=none
A4:  examples=5  perms=3  distinct=3   real_negotiated=json_object  naive=json_schema_strict
```

- **CR-01 confirmed.** `few_shot_permutations` at `live_sweep.py:219-239` branches on `n`,
  not on `len(examples)`. For a 1-element list it appends `reversed(examples)` (identical)
  and, with `k = len(examples) // 2 or 1` → `k=1`, `examples[1:] + examples[:1]` (identical
  again). A0/A0f therefore yield **3 permutations, 1 distinct**.
- **CR-02 confirmed.** A4's real negotiated mode is `json_object`; the driver at
  `test_recognition_eval.py:593` still hardcodes `"json_schema_strict" if arm.structured_output`,
  and `:599` calls `run_arm` with no `negotiated_mode_override`. `negotiated_mode` is a
  cassette-key input, so A4 can never replay through the driver. `report.py:236-247`
  has the correct wiring — the driver is the un-fixed twin.
- **CR-03 confirmed.** `test_recognition_eval.py:686-693`. `ArmCorpusOutcome.status` is
  assigned at exactly four sites in `live_sweep.py` (`:317`, `:327`, `:335`, `:400`) with
  exactly the four literals in `allowed_statuses`. The assertion is a tautology.
- **WR-06 / WR-07 confirmed** at `arms.py:389` and `arms.py:87` respectively (verbatim as
  filed). **CR-02's secondary half** — the known-wrong `"json_schema_strict"` default — is
  live at `arms.py:388`.
- **WR-01, WR-02, WR-03, WR-08, WR-09 confirmed** at `live_sweep.py:331-401`, `:142-154`,
  `:239`, `:119-127`, `:390`.
- **WR-04 confirmed**: `run_report_sweep` (`report.py:210-213`) still takes no
  `permutations` parameter.
- **WR-05 confirmed**: the guard at `test_recognition_eval.py:548-552` checks
  `corpus`/`arm`/`arms` but the assertions at `:561-562` cover `sc1_gate`/`permutations`.
- **IN-01 confirmed** at `conftest.py:65-66`; **IN-02 – IN-05** confirmed at the filed
  `live_sweep.py` / `arms.py` anchors.

## Findings

Severity, titles and line anchors are carried from iteration 3 after re-verification.
Read `35-REVIEW.iter3.md` for the full analysis of each.

### Critical

| ID | File | Title |
|----|------|-------|
| CR-01 | `data-service/tests/recognition_eval/live_sweep.py:219-239` | `few_shot_permutations()` returns duplicate orderings for A0/A0f — the documented `--permutations=3` command bills three identical calls and reports them as an example-order sub-sweep |
| CR-02 | `data-service/tests/test_recognition_eval.py:590-599` | `TestEndToEndDriver` still hardcodes `json_schema_strict` — the documented CI command for arm A4 fails with a cassette miss |
| CR-03 | `data-service/tests/test_recognition_eval.py:640-693` | The only paid test in the suite asserts nothing — a record run that recorded zero cassettes reports PASS |

### Warnings

| ID | File | Title |
|----|------|-------|
| WR-01 | `live_sweep.py:331-401` | No per-combo exception isolation — one provider error aborts the whole paid sweep and discards the entire cost/token record |
| WR-02 | `live_sweep.py:142-154` | `estimate_usd_cost` silently returns `0.0` for an unpriced (provider, model) pair, and nothing counts the unpriced calls |
| WR-03 | `live_sweep.py:239` | Permutation count silently capped at 3 and silently floored at 1 |
| WR-04 | `report.py:210-270` | Permutation recordings are unreachable by any replay path — the per-ordering numbers cannot be regenerated from committed state |
| WR-05 | `test_recognition_eval.py:540-562` | The skip guard in `test_options_registered_with_expected_defaults` is incomplete — `pytest --permutations=3` still fails |
| WR-06 | `arms.py:389`; `cassette.py:181-193` | The `"test-api-key"` placeholder is still structurally reachable by a real adapter |
| WR-07 | `arms.py:87` | `resolve_real_negotiated_mode`'s silent provider fallback can put a live HTTP probe on the replay-only, no-secrets path |
| WR-08 | `live_sweep.py:119-127` | `LiveCredentialError` echoes the persisted `baseUrl` into stdout and CI logs |
| WR-09 | `live_sweep.py:390` | `live_sweep` reaches across a module boundary into `report._compute_scored_row` |

### Info

| ID | File | Title |
|----|------|-------|
| IN-01 | `conftest.py:65-66` | `pytest_collection_modifyitems` re-enables live tests for *any* `-m` expression |
| IN-02 | `live_sweep.py:74-77` | DeepSeek cache-hit pricing is not modeled, so cost is systematically over-stated |
| IN-03 | `live_sweep.py:331-332` | The plaintext key is re-derived once per (arm × corpus) combo |
| IN-04 | `arms.py:391-423` | `run_arm`'s module-global monkeypatching is not parallel-safe |
| IN-05 | `live_sweep.py:117`, `:137-139` | `resolved_base_url` is dead for Anthropic, and the DeepSeek base_url match is exact-string |

## What holds up

Re-confirmed this iteration, unchanged from iteration 3:

- **No secret is persisted or printed.** Cassettes carry no credential material; neither
  `live_sweep.py` nor `arms.py` logs or formats `api_key` into any message.
- **Replay hermeticity is intact today.** `RECOGNITION_EVAL_MODE` defaults to `replay` in
  all three readers; every non-live `CassetteAdapter` construction pins `mode=` explicitly.
- **Cost accounting reads real token counts** from the provider's own `usage` field.
- **`scoring.py` is clean** — the deterministic matcher's total ordering, the vacuous-case
  handling in every metric, and the Wilson/ECE/Brier arithmetic all check out; the
  greedy-vs-optimal gap is measured rather than assumed, and ties are logged.

---

_Reviewed: 2026-07-27_
_Reviewer: Claude (inline, gsd-code-review workflow)_
_Depth: standard (full phase scope; iteration-3 findings independently re-verified)_
