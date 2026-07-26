---
phase: 35-llm-recognition-canvas-preview
fixed_at: 2026-07-27T00:00:00Z
review_path: .planning/phases/35-llm-recognition-canvas-preview/35-REVIEW.md
iteration: 4
scope: Critical + Warning (Info deferred — no --all)
findings_in_scope: 12
fixed: 12
skipped: 0
deferred_info: 5
status: all_fixed
commits:
  - e61952f — CR-02, WR-07
  - 0e496b6 — CR-01, WR-01, WR-02, WR-03, WR-06, WR-08, WR-09
  - 0a46d63 — CR-03, WR-04, WR-05
tests_before: 89 passed, 1 skipped, 1 deselected
tests_after: 100 passed, 1 skipped, 1 deselected
---

# Phase 35: Code Review Fix Report — iteration 4

All 12 Critical + Warning findings from `35-REVIEW.md` (iteration 4, carried from the
never-fixed `35-REVIEW.iter3.md`) are fixed and verified. The 5 Info findings are deferred:
`--all` was not passed.

## Critical

### CR-01 — duplicate few-shot orderings billed and reported as a sub-sweep — **FIXED**

`few_shot_permutations` branched on the requested count `n`, not on `len(examples)`. For a
one-element list `reversed([x]) == [x]`, and `k = len(examples) // 2 or 1` made the rotation
`[x][1:] + [x][:1] == [x]` — three identical orderings. Arms A0/A0f resolve exactly such a
list from the pre-35-08 fixture.

Now branches on list length and drops duplicates by fingerprint before truncating to `n`.

```
before ->  A0: perms=3 distinct=1   A0f: perms=3 distinct=1   A3: 3/3   A4: 3/3
after  ->  A0: perms=1 distinct=1   A0f: perms=1 distinct=1   A3: 3/3   A4: 3/3
```

**No published result had to be withdrawn.** The review flagged that any per-ordering
A0/A0f numbers from a `--permutations>1` run would be a fabricated stability claim. Checked
`35-EVAL-REPORT.md`: the sub-sweep that actually ran was `--arms=A3 --permutations=3` — A3
has 5 few-shot examples, so its 3 orderings were genuinely distinct — and A0f never ran at
all (no Anthropic key configured). The defect was real on the *documented* full-arm command
line, but it never reached a published figure.

### CR-02 — driver hardcoded `json_schema_strict`, A4 unreplayable — **FIXED**

Fixed at the source rather than only at the call site. `run_arm`'s default for
`negotiated_mode` is now `resolve_real_negotiated_mode(arm)` — the same single source of
truth `report.py` already used — so a caller that forgets the override gets the *right* mode
instead of a known-wrong one. `TestEndToEndDriver` computes it explicitly and reuses it for
the `CassetteAdapter` key. The naive `"json_schema_strict" if arm.structured_output`
expression is gone from the codebase.

```
before -> pytest ...::TestEndToEndDriver --corpus=urbanblock_slice --arm=A4  ->  CassetteMissError, 1 failed
after  -> pytest ...::TestEndToEndDriver --corpus=urbanblock_slice --arm=A4  ->  1 passed
```

### CR-03 — the only paid test asserted nothing — **FIXED**

The sole assertion checked `status` against a set containing exactly the literals
`live_sweep.py` assigns, so it could not fail for any input. Replaced with assertions that
the run actually measured something: recordings exist, no combo failed after spending money,
and token usage was captured. `OUTCOME_STATUSES` is now exported from `live_sweep` so the
vocabulary check reads from one definition instead of a hand-copied literal set.

The root enabler is closed too: `run_live_sweep` refuses to start when `LLM_MASTER_SECRET`
is the `"test-master-secret"` placeholder this test module `setdefault()`s at import. A
misconfigured record run now fails *before* spending rather than skipping every arm and
exiting green.

```
LLM_MASTER_SECRET=test-master-secret run_live_sweep(...) -> LiveCredentialError (verified)
```

## Warnings

| ID | Resolution |
|----|-----------|
| WR-01 | Per-combo `except Exception` isolation in `run_live_sweep`; a raising combo becomes a `"failed"` outcome and the accumulated cost/token record survives. Previously an httpx 429/500, a `ProvenanceError` or a git-subprocess `RuntimeError` escaped the loop and destroyed the whole accounting after the money was spent — and, given `for corpus: for arm:`, lost every remaining corpus. |
| WR-02 | `estimate_usd_cost_priced()` returns `(cost, priced)`; `AttemptCost.priced` carries it; `LiveSweepResult.cost_summary()` names the unpriced call count, token volume and `provider/model` pairs. An unpriced call can no longer read as a free one. |
| WR-03 | `permutations < 1` rejected at both entry points (`run_live_sweep`, `few_shot_permutations`). A shortfall against the distinct orderings available is recorded as a named `detail` on the outcome instead of silently running fewer. |
| WR-04 | `run_report_sweep(..., permutations=N)` emits one `ScoredRow` per (corpus × arm × ordering), with `--permutations` on `report.main()`. Verified: A3 × urbanblock_slice replays 3 rows from **4 distinct committed cassette keys**, 0 skipped, ordering 0 reproducing the as-authored row. The sub-sweep is now regenerable from committed state. |
| WR-05 | The skip guard covered 3 of the 5 options the test asserts. Both the guard and the assertions now read one `expected_defaults` table. Verified: `--permutations=3` and `--sc1-gate=0.75` each skip instead of failing. |
| WR-06 | `CassetteAdapter` refuses `None`/`""`/`"test-api-key"` on the record/live branch. Fails closed at the boundary that knows it is live, so a second live caller cannot reintroduce the 401 by forgetting `api_key_override`. No-op in replay. |
| WR-07 | `resolve_real_negotiated_mode` raises on a provider label absent from `REAL_ADAPTER_MAP` instead of silently reusing it as a real adapter tag. Closes the path where an `ollama` label would have put a live HTTP probe on `report.py`'s replay-only, no-secrets sweep, and makes it agree with `resolve_live_adapter_and_key` on the same input. |
| WR-08 | `mask_url()` reduces a base URL to `scheme://host` before interpolation, matching the project's `llm_gateway.mask_key` convention. Verified a credential-bearing path segment is stripped from the `LiveCredentialError` message. |
| WR-09 | `report._compute_scored_row` → public `compute_scored_row`, with a docstring naming `live_sweep` as a contract consumer. The private cross-module reach would have broken the record path on any internals refactor — surfacing mid-metered-run, since only a paid test exercises it. |

## Structural change

`few_shot_permutations` moved from `live_sweep.py` to `arms.py`, the module that owns
few-shot artifact resolution, so `report.py` can reuse the record path's exact generator on
the replay side. `live_sweep` already imports `report`, so importing the other direction
would have been a cycle. Re-exported from `live_sweep` — every existing caller and test is
unaffected.

## Deferred (Info — pass `--all` to include)

IN-01 (`conftest` re-enables live tests for any `-m` expression), IN-02 (DeepSeek cache-hit
pricing unmodeled), IN-03 (plaintext key re-derived per combo), IN-04 (`run_arm` monkeypatching
not parallel-safe), IN-05 (`resolved_base_url` inert for Anthropic; exact-string base_url match).

## Verification

New regression coverage — 11 tests added, all free and hermetic:

- `TestLiveSweepHelpers`: permutation distinctness across list lengths, as-authored ordering
  preserved, non-positive count rejected at both entry points, unpriced-call flagging,
  `cost_summary` naming the unpriced volume, URL masking, credential error not echoing a raw
  base URL, and the permutation sub-sweep replaying from committed cassettes.
- `TestArms::test_live_mode_refuses_the_placeholder_api_key`: the WR-06 refusal fires.

```
recognition eval suite   before: 89 passed, 1 skipped, 1 deselected
                          after: 100 passed, 1 skipped, 1 deselected

full data-service suite   after: 481 passed, 1 skipped, 1 deselected, 4 failed
```

The 4 failures are `tests/test_dg_context.py` and are the pre-existing environment baseline,
not regressions: the `neo4j` hostname only resolves inside the compose network, so they fail
identically from the host before and after these changes.

---

_Fixed: 2026-07-27_
_Fixer: Claude (inline, gsd-code-review --fix)_
