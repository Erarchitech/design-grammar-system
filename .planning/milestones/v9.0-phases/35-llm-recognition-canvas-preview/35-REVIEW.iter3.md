---
phase: 35-llm-recognition-canvas-preview
reviewed: 2026-07-27T00:00:00Z
depth: standard
scope: incremental (wave 5 / plan 35-15, dbaf635^..HEAD)
files_reviewed: 4
files_reviewed_list:
  - data-service/tests/recognition_eval/live_sweep.py
  - data-service/tests/recognition_eval/arms.py
  - data-service/tests/recognition_eval/report.py
  - data-service/tests/test_recognition_eval.py
findings:
  critical: 3
  warning: 9
  info: 5
  total: 17
status: issues_found
---

# Phase 35 (wave 5 / 35-15): Code Review Report — iteration 3

**Reviewed:** 2026-07-27
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found
**Prior reviews:** `35-REVIEW.md` (iter1), `35-REVIEW.iter2.md` (iter2) — those cover the C# preview/accept path and the `/computgraph/recognize` endpoint. No finding below duplicates them; the eval harness was not in either prior scope.

## Summary

Wave 5 adds `live_sweep.py`, the first code path in this repo that resolves a **real decrypted API key** and makes **metered LLM calls**, plus additive `api_key_override` / `negotiated_mode_override` seams on `arms.run_arm()` and the matching `report.py` wiring.

**What holds up under adversarial checking:**

- **No secret is persisted or printed.** Cassettes carry only `{requestDigest, promptBody?, responseText, usage, finishReason, truncated, provider, model, recordedAt, cassetteVersion}`. I scanned all 17 committed cassettes for `sk-*`, `Bearer`, `x-api-key`, `Authorization` — zero hits. `promptBody` is present only because both corpora are genuinely `ip_class == "own"` (verified). Neither `live_sweep.py` nor `arms.py` logs, prints, or formats `api_key` into any message.
- **Replay hermeticity is intact today.** `RECOGNITION_EVAL_MODE` defaults to `replay` in all three readers (`cassette.py:146`, `live_sweep.py:288`, `test_recognition_eval.py:653`). Every non-live `CassetteAdapter` construction pins `mode=` explicitly, so exporting `RECOGNITION_EVAL_MODE=record` and running the bare suite still makes zero live calls. `resolve_real_negotiated_mode()` is genuinely network-free for the `openai`/`anthropic` labels actually in use (`_negotiate` branches on base_url/model prefix; only the `ollama` branch probes — see WR-07 for the latent hole). Bare `pytest tests/test_recognition_eval.py` → `41 passed, 1 skipped, 1 deselected`; the deselected item is the live test.
- **The `"test-api-key"` fix works where it is applied.** The literal is now only reachable when `api_key_override is None`, which no real-adapter call site does. Replay tests that legitimately depend on it are unaffected (`CassetteAdapter` in replay never touches the wrapped adapter).
- **Cost accounting reads real numbers.** `AnthropicAdapter` normalizes `input_tokens`/`output_tokens` into `prompt_tokens`/`completion_tokens`, so `estimate_usd_cost` is not silently zeroing the Anthropic arms. Retries are bounded (`recognize_structure(max_retries=2)` → ≤3 calls per run), so spend is finite.

**What does not hold up:** three defects that make the wave's headline artifacts wrong or unverifiable — a permutation generator that emits **identical** orderings for the two arms that have a single few-shot example (billing 3× for one measurement and presenting it as a 3-point sub-sweep), the *same* negotiated-mode bug that was fixed in `report.py` this wave but **left in place** in the end-to-end driver (verified: the documented `--arm=A4` command dies on a cassette miss), and a paid-run test whose only assertion is structurally incapable of failing.

---

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `few_shot_permutations()` returns duplicate orderings for A0/A0f — the documented `--permutations=3` command bills three identical calls and reports them as an example-order sub-sweep

**File:** `data-service/tests/recognition_eval/live_sweep.py:219-239` (consumed at `:348-356`)

**Issue:** The three "fixed orderings" are `as-authored`, `reversed`, and `rotate-by-len//2`. For a list of length 1 all three collapse to the same list; for length 2, `reversed` and `rotate` are identical. Arm A0/A0f resolve their few-shot content from the **pre-35-08** fixture, whose payload is a single `{description,input,expected}` object — `resolve_arm_artifacts` wraps it as `examples = [payload]`, i.e. **length 1**. Verified against the real artifacts:

```
A0 few-shot examples count: 1   -> A0 perms distinct: 1 of 3
A3 few-shot examples count: 5   -> A3 perms distinct: 3 of 3
```

Consequences on the command this module's own docstring (`live_sweep.py:5-7`) tells the operator to run — `--arms=A0,A0f,A1,A2,A3,A4,A5 --permutations=3`:

1. **Money:** 3 identical live requests per (A0 × corpus) and per (A0f × corpus) — 12 fully redundant metered calls (×2–3 more with retries), on the *most expensive* arm too (A0f is `claude-sonnet-5`).
2. **Cassettes:** identical prompts ⇒ identical `cassette_key` ⇒ the same file is written and overwritten 3×; the run *looks* like it produced 3 recordings and produced 1.
3. **Measurement validity (the worst part):** `perm_rows` gets 3 rows with `permutation_index` 0/1/2 carrying byte-identical M1. Anything reading those rows — including a thesis appendix — reads "M1 is stable across example orderings" from a sub-sweep that never varied the order. That is a fabricated stability claim, from a harness whose stated purpose is refusing exactly this kind of silent degradation.

There is no distinctness check, no warning, and no named skip.

**Fix:**
```python
def few_shot_permutations(examples, n=3):
    candidates = [list(examples)]
    if len(examples) >= 2:
        candidates.append(list(reversed(examples)))
    if len(examples) >= 3:
        k = len(examples) // 2
        candidates.append(list(examples[k:]) + list(examples[:k]))

    # Never return two orderings that are the same list: a duplicate would be
    # billed as a separate call, collide on the cassette key, and be reported
    # as an independent ordering.
    seen, perms = set(), []
    for cand in candidates:
        fp = json.dumps(cand, sort_keys=True)
        if fp not in seen:
            seen.add(fp)
            perms.append(cand)
    return perms[:n]
```
and in `run_live_sweep`, when `len(perms) < permutations`, record a named reason on the outcome (e.g. `detail="only 1 distinct ordering available (few-shot list has 1 example)"`) instead of silently running fewer/duplicate orderings. Any per-ordering numbers already published for A0/A0f from a `--permutations>1` run must be withdrawn or re-labelled as a single ordering.

---

### CR-02: `TestEndToEndDriver` still hardcodes `json_schema_strict` — the documented CI command for arm A4 fails with a cassette miss against the cassette this very wave recorded

**File:** `data-service/tests/test_recognition_eval.py:590-599` (specifically `:593`)

**Issue:** This wave's fix commit (`0075631`) corrected the naive negotiated-mode assumption in `report.py:236-248` (now `arms_module.resolve_real_negotiated_mode(arm)` + `negotiated_mode_override=`) but left the byte-identical bug in the end-to-end driver:

```python
negotiated_mode="json_schema_strict" if arm.structured_output else "none",
...
outcome = arms_module.run_arm(arm, corpus, adapter)   # no negotiated_mode_override
```

`negotiated_mode` is one of the eight cassette-key inputs. A4's real negotiated mode is `json_object` (verified: `resolve_real_negotiated_mode(ARMS["A4"]) == "json_object"`), so the driver computes a key that no recording can ever match. Reproduced:

```
$ python -m pytest tests/test_recognition_eval.py::TestEndToEndDriver -q \
      --corpus=urbanblock_slice --arm=A4
E  CassetteMissError: cassette miss for arm='A4' key=abd6a4bd... 1 failed
```
while the fixed path scores the same combo fine (`report.run_report_sweep(['urbanblock_slice'],['A4'])` → `scored 1 skipped 0`). Arms A0–A3/A5 pass through unnoticed only because `structured_output` is False for all of them, so the placeholder happens to equal the real mode — A4 is the only arm this harness exists to distinguish, and it is the only one the driver cannot replay.

Secondary damage: the provenance block returned by `run_arm` also stamps `negotiatedMode: "json_schema_strict"` on this path, so any consumer of that row would record a mode that was never sent.

**Fix:** make the driver use the same single source of truth as `report.py`:
```python
negotiated_mode = arms_module.resolve_real_negotiated_mode(arm)
adapter = cassette_module.CassetteAdapter(
    arm_id, None, negotiated_mode=negotiated_mode,
    prompt_version=cg_recognition.PROMPT_VERSION,
    ip_class=corpus.ip_class, mode="replay",
)
outcome = arms_module.run_arm(arm, corpus, adapter,
                              negotiated_mode_override=negotiated_mode)
```
Then delete the `"json_schema_strict" if arm.structured_output else "none"` default in `arms.run_arm` (`arms.py:388`) entirely, or make it raise — leaving a known-wrong default in the code is what let this bug survive its own fix commit.

---

### CR-03: The only paid test in the suite asserts nothing — a record run that recorded zero cassettes reports PASS

**File:** `data-service/tests/test_recognition_eval.py:640-693` (assertion at `:686-693`); interacts with `:29`

**Issue:** The single assertion is

```python
allowed_statuses = {"recorded", "skipped_credentials", "skipped_invalid",
                    "skipped_corpus_load_failed"}
unexpected = [o for o in result.outcomes if o.status not in allowed_statuses]
assert not unexpected, unexpected
```

`ArmCorpusOutcome.status` is assigned at exactly four sites in `live_sweep.py` (`:317`, `:327`, `:335`, `:400`) with exactly those four string literals. The predicate is therefore a tautology: **this assertion cannot fail for any input, any credential state, any provider outcome.** A sweep in which every single (arm × corpus) combo was skipped for credentials exits green, having spent nothing and recorded nothing, indistinguishable in CI from a successful record.

That failure mode is not hypothetical here: `test_recognition_eval.py:29` runs `os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")` at import. An operator who runs the documented record command without exporting the *real* master secret gets a fake one injected, every `resolve_active_provider` decrypt returns `("ollama", None, None)`, every arm raises `LiveCredentialError`, and the test passes. The results are only visible as `print()` output, which pytest captures and discards on a passing test — so the operator sees a green dot and no data.

This also contradicts the class's own comment ("so a bare `-m live` pass without the env var set does not silently do nothing while looking like it ran") — that is precisely what it does when credentials are missing.

**Fix:**
```python
recorded = [o for o in result.outcomes if o.status == "recorded"]
skipped_creds = [o for o in result.outcomes if o.status == "skipped_credentials"]
assert recorded, (
    "record sweep produced ZERO recordings -- nothing was measured. "
    f"credential skips: {[(o.arm_id, o.detail) for o in skipped_creds]}"
)
assert len(recorded) + len(skipped_creds) == len(result.outcomes), result.outcomes
```
and either drop the `setdefault("LLM_MASTER_SECRET", ...)` on the record path, or have `resolve_live_adapter_and_key` refuse to run when the master secret is literally `"test-master-secret"` so a misconfigured record run fails loudly instead of skipping.

---

## Warnings

### WR-01: `run_live_sweep` has no per-combo exception isolation — one provider error aborts the whole paid sweep and discards the entire cost/token record

**File:** `data-service/tests/recognition_eval/live_sweep.py:331-401`

**Issue:** Only `LiveCredentialError` is caught (`:333`). Everything else propagates out of `run_live_sweep`: an `httpx.HTTPStatusError` from a 429/500/model-not-found (`raise_for_status()` in both adapters), a `ProvenanceError` from the un-guarded `assert_provenance` at `:382`, a `RuntimeError` from `resolve_arm_artifacts`'s git subprocess at `:350`, a `json.JSONDecodeError` on a malformed blob. Because `LiveSweepResult` is only constructed at `:403`, the accumulated `costs` list — the entire "actual cost and total token usage" record the plan asked for — is destroyed along with the frame, after the money has already been spent. Loop order (`for corpus: for arm:`) makes this worse: a failure on the 2nd arm of the 1st corpus loses the 2nd corpus entirely.

This also contradicts the module docstring's own contract (`:26-29`, "it never crashes the whole sweep") — a claim only true for credential mismatches.

**Fix:** wrap the per-combo body in `except Exception as exc:` → `ArmCorpusOutcome(status="failed", detail=f"{type(exc).__name__}: {exc}")` (add `"failed"` to the status vocabulary and to CR-03's assertion), and emit the running cost total to stdout/a JSON sidecar after *every* combo so a crash never loses the accounting.

### WR-02: `estimate_usd_cost` silently returns `0.0` for an unpriced (provider, model) pair, and nothing counts the unpriced calls

**File:** `data-service/tests/recognition_eval/live_sweep.py:142-154`, printed at `test_recognition_eval.py:676-679`

**Issue:** `USD_PER_MTOK` has exactly two entries. Any other pair — a DeepSeek model rename, an OpenAI-compatible endpoint swap, an Anthropic response echoing a dated model id (`claude-sonnet-5-2026xxxx`) — yields `0.0` with no trace, and the headline `approx_usd_cost=...` under-reports by exactly the unpriced volume while still looking authoritative. It works today only because DeepSeek echoes `"deepseek-chat"` verbatim and `AnthropicAdapter` returns `req.model`. This is the same "silent drop" the rest of this harness (cassette misses, provenance refusal, `SkippedRow`) is built to refuse.

**Fix:** have `AttemptCost` carry `priced: bool`, and print `unpriced: N call(s), M tokens (no rate for <provider>/<model>)` alongside the total. Never let an unpriced call be indistinguishable from a free one.

### WR-03: Permutation count is silently capped at 3 and silently floored at 1

**File:** `data-service/tests/recognition_eval/live_sweep.py:239` (`perms[:n]`), `:349-353`

**Issue:** `--permutations=5` runs 3 (verified) with no message; `--permutations=0` or a negative value falls into the `else` branch and runs 1. `conftest.py` applies no bounds. The operator's requested sweep size is silently different from what was billed and reported.

**Fix:** validate at the entry point — `if permutations < 1: raise ValueError(...)`; if `permutations > len(distinct_orderings)`, record the shortfall as a named `detail` on the outcome instead of truncating silently.

### WR-04: Permutation recordings are unreachable by any replay path — the per-ordering numbers cannot be regenerated from committed state

**File:** `data-service/tests/recognition_eval/report.py:210-270`, `live_sweep.py:355-397`

**Issue:** `run_live_sweep` scores each permutation in-process and returns the rows; nothing persists them. `run_report_sweep` — the only replay-side scorer — has no `permutations` parameter and always replays the as-authored ordering, so the permutation cassettes that *are* committed (arm A3 has 6 of its 7 recordings from the sub-sweep) can never be re-scored by any code in the repo. The per-ordering M1 figures live only in pytest stdout and whatever was hand-copied into `35-EVAL-REPORT.md`. For a harness whose stated purpose is "the artifact that goes in the thesis appendix", the sub-sweep is the one result that is not reproducible from the committed record.

**Fix:** add `permutations: int = 1` to `run_report_sweep`, reuse `live_sweep.few_shot_permutations` + `few_shot_examples_override` on the replay path, and emit one `ScoredRow` per (corpus × arm × permutation) so `report.main()` regenerates the sub-sweep table from cassettes alone.

### WR-05: The new skip guard in `test_options_registered_with_expected_defaults` is incomplete — `pytest --permutations=3` still fails

**File:** `data-service/tests/test_recognition_eval.py:540-562`

**Issue:** The guard checks `corpus`/`arm`/`arms` but not `sc1_gate`/`permutations`, while lines `:561-562` assert the defaults of exactly those two. Reproduced:

```
$ python -m pytest tests/test_recognition_eval.py::TestConftestOptions -q --permutations=3
tests\test_recognition_eval.py:562: AssertionError   1 failed, 1 passed
```

Any session that overrides only `--permutations` or only `--sc1-gate` (both documented knobs) fails a test that has nothing to do with the run. The fix applied this wave addressed three of the five options.

**Fix:** guard on every option the test asserts, or better, assert against `parser` registration rather than session state:
```python
overridden = [o for o in ("corpus", "arm", "arms", "sc1_gate", "permutations")
              if request.config.getoption(o) != _REGISTERED_DEFAULTS[o]]
if overridden:
    pytest.skip(f"defaults overridden this session: {overridden}")
```

### WR-06: The `"test-api-key"` placeholder is still structurally reachable by a real adapter

**File:** `data-service/tests/recognition_eval/arms.py:389`; `cassette.py:181-193`

**Issue:** The fix made `live_sweep` pass `api_key_override`, but nothing *enforces* the pairing. `run_arm` will still patch `resolve_active_provider` to hand back the literal `"test-api-key"` to whatever adapter it was given, and `CassetteAdapter` in `record`/`live` mode will forward it verbatim to a real provider as `Authorization: Bearer test-api-key` / `x-api-key: test-api-key`. The only thing preventing a repeat of the bug fixed in `0075631` is that exactly one caller currently remembers the keyword. A second live caller (a per-arm re-record helper, a spot-check script) reintroduces it.

**Fix:** enforce it at the boundary that knows it is live —
```python
# cassette.py, record/live branch, before calling the wrapped adapter
if api_key in (None, "", "test-api-key"):
    raise CassetteWriteError(
        f"refusing to make a live call with placeholder/empty api_key "
        f"(arm={self.arm_id!r}): pass arms.run_arm(..., api_key_override=<real key>)."
    )
```
This fails closed on the real-call path and is a no-op for every replay test.

### WR-07: `resolve_real_negotiated_mode`'s silent provider fallback can put a live HTTP probe on the replay-only, no-secrets path

**File:** `data-service/tests/recognition_eval/arms.py:87`

**Issue:**
```python
real_tag, base_url = REAL_ADAPTER_MAP.get(arm.provider, (arm.provider, None))
```
An unknown provenance label is silently reused as a real adapter tag. `live_sweep.resolve_live_adapter_and_key` raises `LiveCredentialError` for the identical condition (`live_sweep.py:104-109`) — the two functions disagree on the same input. Concretely: add an arm with `provider="ollama"` (a stated project provider) and `report.run_report_sweep` — documented as the path that "must NEVER touch a secret" and must be `$0`/no-network — starts issuing `GET {base_url}/api/version` probes from `_negotiate`'s ollama branch, breaking replay hermeticity in the one function whose docstring guarantees it. The docstring's hermeticity claim is scoped to "every provider label in `REAL_ADAPTER_MAP`", but the code does not enforce that scope.

**Fix:** make the function honor its own precondition —
```python
if arm.provider not in REAL_ADAPTER_MAP:
    raise ValueError(
        f"arm {arm.id!r}: no REAL_ADAPTER_MAP entry for provider "
        f"{arm.provider!r}; refusing to guess (a wrong guess either "
        "mis-keys every cassette or puts a live probe on the replay path)."
    )
```

### WR-08: `LiveCredentialError` echoes the persisted `baseUrl` into stdout and CI logs

**File:** `data-service/tests/recognition_eval/live_sweep.py:119-127`; printed at `test_recognition_eval.py:673`

**Issue:** The message interpolates `persisted_base_url` verbatim, and the live test prints every `outcome.detail` unconditionally. The project's own LLM-gateway convention is to mask credentials before they reach a log (`llm_gateway.mask_key`, and `negotiate_structured_output`'s "Never log the key ... (LLMC-06)"). `baseUrl` is not a secret by design, but the OpenAI-compatible endpoints this map exists to support routinely carry the credential in the URL (gateway/proxy path segments, Azure `?api-key=`, self-hosted routers with an embedded token). A pasted CI log or a copied terminal transcript then contains it.

**Fix:** print scheme+host only, e.g. `urlparse(persisted_base_url).hostname`, or run the value through a `mask_url` helper before interpolating. Apply to both the mismatch message and the test's `print`.

### WR-09: `live_sweep` reaches across a module boundary into `report._compute_scored_row`

**File:** `data-service/tests/recognition_eval/live_sweep.py:390`

**Issue:** The leading underscore marks it private; `live_sweep` is now a hard consumer of its exact `(corpus_obj, arm, outcome) -> ScoredRow` signature and of `ScoredRow`'s field set. Any refactor of `report.py`'s internals silently breaks the record path — which is only exercised by a paid, marker-gated test, so the break surfaces during a metered run.

**Fix:** rename to `compute_scored_row` (public) and state in its docstring that `live_sweep` depends on it, or lift it into `scoring.py` where both modules are already legitimate consumers.

---

## Info

### IN-01: `conftest.pytest_collection_modifyitems` re-enables live tests for *any* `-m` expression

**File:** `data-service/tests/conftest.py:65-66`

`if config.option.markexpr: return` means `pytest -m "not slow"` (or any unrelated selector) restores `live`-marked items to the session. Today this is harmless only because `TestLiveRecordSweep` is gated a second time on `--arms` and `RECOGNITION_EVAL_MODE`. Consider `-m "not slow and not live"`-style composition instead of an unconditional early return, so the money gate does not depend on every future live test remembering its own second gate.

### IN-02: DeepSeek cache-hit pricing is not modeled, so cost is systematically over-stated

**File:** `data-service/tests/recognition_eval/live_sweep.py:74-77`

The map uses DeepSeek's cache-**miss** input rate for every prompt token. The harness re-sends near-identical prompts across retries and permutations (recorded prompts run 5.2k–11.8k input tokens with a large shared prefix), and DeepSeek reports `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` in `usage`. The number is honestly labelled "approximate", but it is presented as the run's cost figure; splitting on the cache fields would make it real rather than an upper bound.

### IN-03: The plaintext key is re-derived once per (arm × corpus) combo

**File:** `data-service/tests/recognition_eval/live_sweep.py:331-332`

`resolve_live_adapter_and_key` re-reads the settings file and re-runs Fernet decryption for every combo (up to 14 for the documented sweep), holding a fresh plaintext copy each time. Resolving once per distinct provider and caching by `real_tag` narrows the plaintext's lifetime and copy count without changing behavior.

### IN-04: `run_arm`'s module-global monkeypatching is not parallel-safe

**File:** `data-service/tests/recognition_eval/arms.py:391-423`

Seven `cg_recognition`/`cg_topology` attributes are swapped and restored around each call. Under `pytest-xdist -n` (or any threaded driver) two concurrent arms corrupt each other's artifacts and could record a cassette under the wrong arm's prompt. `live_sweep.py:96-98` already alludes to "an unrelated, concurrently-running call" — worth an explicit module-level note that the harness is single-threaded by construction, or a re-entrancy guard.

### IN-05: `resolved_base_url` is dead for Anthropic, and the DeepSeek base_url match is exact-string

**File:** `data-service/tests/recognition_eval/live_sweep.py:117`, `:137-139`

`get_adapter("anthropic", base_url)` ignores `base_url` entirely (`llm_gateway.py:597-598`), so the value computed at `:137` and returned at `:139` is inert for anthropic arms and the caller discards it anyway (`_real_base_url`). Separately, `persisted_base_url != required_base_url` is an exact string comparison: a persisted `https://api.deepseek.com/v1/` (trailing slash) or `https://api.deepseek.com` skips every DeepSeek arm with a credentials error. It fails safe, but normalizing (strip trailing `/`, compare hostname + path) removes a confusing operator dead-end.

---

_Reviewed: 2026-07-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (incremental — wave 5 only, `dbaf635^..HEAD`)_
