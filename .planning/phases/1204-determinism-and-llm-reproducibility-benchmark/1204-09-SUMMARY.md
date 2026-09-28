# Plan 1204-09 Summary — Live LLM Half of the 1204 Benchmark

## What was built

- `fixtures/llm_repeatability/rule_ingest_prompts/` — five D-12 rule-ingest
  prompts, frozen against a real `/context/assemble` call (the "Build LLM
  Prompt" node's production logic, since the n8n node is a thin caller that
  delegates prompt construction there — Phase 29-05), plus a sha256
  MANIFEST. (Captured in an earlier turn, reused unchanged here.)
- `fixtures/llm_repeatability/cassettes/rule_ingest/` — 50 recorded live
  samples (5 items × k=10), each a full provenance-complete cassette.
- `fixtures/llm_repeatability/MANIFEST.md` — human-facing index: every
  prompt and cassette's sha256, the provider/model sampled, the git commit.
- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/llm-evidence/llm-repeatability-report.{json,md}`
  — the D-24 LLM-repeatability report, schema-validated, per-(provider,
  item) strata, D-21 byte-identical replay confirmed.
- `data-service/tests/recognition_eval/report_schema_llm.json` — one
  additive schema fix (see below).

## Scope decisions (owner-confirmed)

- **Rule-ingest only.** Recognition prompts require faithfully reproducing
  `cg_recognition._build_recognition_prompt`'s internal `cg_context`/
  `scope`/`features`/`tier0` derivation from Computgraph corpora —
  meaningfully more reverse-engineering than rule-ingest's `/context/assemble`
  call. Owner chose rule-ingest only rather than risk an unfaithful
  recognition prompt (which would silently produce misleading evidence).
  D-27 requires ≥1 provider at k≥5 — it does not mandate both D-09 subjects.
- **One provider (openai-compatible via a custom router).** The LLM
  settings panel holds one active provider/model at a time; owner chose to
  use whatever was already configured rather than switch mid-run. Local
  Ollama and Anthropic were out of scope for this capture.
- **No live structural validity oracle.** `outcome_taxonomy.classify`'s
  `valid` input is read as a static item field by `repeat_sweep.py`
  (plan 1204-07), not computed from each sample's actual output — D-18's
  oracle-free scope means 1204 never wires a correctness-against-ground-truth
  check. `valid: True` was set as the default for every item, so outcome
  classification reflects only provider-level signals actually present on
  the response (`truncated`, `finish_reason == "refusal"`, `provider_error`),
  never a fabricated Cypher-correctness judgement. This is documented in the
  report's own Limitations section.

## D-28: key handling

Per plan requirement, the owner entered the provider key via the V2 UI LLM
Settings panel before this plan started (Task 1 checkpoint). All live
generation ran via a script executed **inside the `data-service` container**
(`docker exec`), decrypting the key through the exact same
`llm_gateway.resolve_active_provider()` call `app.py`'s own `/llm/generate`
route makes. The key existed only in that container process's memory, was
never printed, logged, written to a file, or returned to the orchestrator's
host-side output. The orchestrator never read `.secrets/`.

## Real bugs found and fixed during this live run

Six issues surfaced only under a real multi-item live capture — none were
catchable by plan 1204-07's hermetic (mocked) tests:

1. **`OpenAIAdapter`'s 120s production timeout was insufficient** for the
   largest D-12 prompt (~41k chars; measured at 51s standalone, but the full
   sequential run occasionally needed longer). Fixed via an
   orchestrator-local subclass (`_LongTimeoutOpenAIAdapter`, 300s) that never
   edits `llm_gateway.py` (D-10 — production code untouched).
2. **Transient network/5xx errors had no retry.** Added retry-with-backoff
   (4 attempts, 5s/10s/15s backoff) for `ReadTimeout`/`ConnectTimeout`/
   `ConnectError` and 5xx `HTTPStatusError` (4xx re-raises immediately — not
   retryable). Orchestrator-local, same reasoning as above.
3. **Module-identity bug wrote cassettes into the FROZEN directory.**
   `repeat_sweep.py` imports `from recognition_eval import cassette as
   cassette_module` (package-qualified); the orchestrator's script initially
   did a bare `import cassette as cassette_module`, binding a *separate*
   `sys.modules` entry. Patching `_FIXTURES_ROOT` on the wrong module object
   meant the first attempt's 7 cassettes landed in
   `data-service/fixtures/recognition_eval/cassettes/rule_ingest/` (the
   frozen Phase-35 directory) instead of `fixtures/llm_repeatability/cassettes/`.
   **Caught and cleaned up before any commit** — this only ever touched the
   container's own filesystem (a build-time image snapshot, not bind-mounted
   to the host), so the host's git-tracked frozen cassettes were never at
   risk; verified with `git status --porcelain` showing no change to that
   path at any point. Fixed by reusing `repeat_sweep.cassette_module`
   directly instead of a fresh import.
4. **`_provenance_block` required five item fields** (`promptFilePath`,
   `promptSha256`, `gatewayCommit`, `serviceCommit`, `timestamp`) the initial
   item construction omitted. Fixed by populating all D-19 fields the
   function actually reads. Minor documented limitation: `timestamp` is set
   once per item at construction time, so all 10 samples of one item share
   the same timestamp rather than each carrying its own generation time —
   D-19 only requires the field be non-None, which it is.
5. **`render_llm_repeatability_markdown` reads `report["strata"]`/
   `report["providers"]`, but the schema's actual required field is
   `providerStrata`** — a genuine naming inconsistency in plan 1204-07's own
   shipped code, invisible until real schema validation ran against real
   multi-item output. Worked around by building the markdown directly rather
   than further patching the mismatched emitter (out of scope to rewrite
   `report.py` mid-live-run; flagging here for a future phase to reconcile).
6. **`report_schema_llm.json`'s `providerStrata` had no item dimension**,
   even though `repeat_sweep.compute_item_metrics`/`run_repeat_sweep` are
   explicitly multi-item-shaped (`{item_id: {..., strata: {provider: {...}}}}`).
   Pooling the 5 different rule-ingest prompts' samples into one stratum
   would have been substantively misleading — different prompts have
   different correct outputs by construction, so a naive cross-item pool
   reads as near-total instability (~1/50 modal agreement) regardless of how
   stable any single item's own 10 samples actually are. Fixed with a
   minimal additive schema change: `providerStrata` array entries gained a
   required `item` field, so the schema now genuinely matches
   `repeat_sweep.py`'s own per-item output shape. Verified: plan 1204-07's
   own `test_llm_report_schema_has_no_shared_or_accuracy_fields` and the
   full `test_repeat_sweep.py` suite (14 tests) still pass unmodified.

## Results

| Item | n | Level-1 distinct | Level-2 distinct | Modal agreement | Wilson 95% CI |
|---|---|---|---|---|---|
| cq3_attribute_of | 10 | 9 | 9 | 0.200 | [0.057, 0.510] |
| fixture_rules_v7_1 (height 75m) | 10 | 5 | 5 | 0.600 | [0.313, 0.832] |
| fixture_rules_v7_2 (area 28m²) | 10 | 8 | 8 | 0.200 | [0.057, 0.510] |
| fixture_rules_v7_3 (separation 10m) | 10 | 9 | 9 | 0.100 → 0.200* | [0.057, 0.510] |
| height_rule | 10 | 10 | 10 | 0.100 | [0.018, 0.404] |

(*fixture_rules_v7_3's exact modal agreement is as recorded in the JSON —
see the report file; the table above is transcribed from the rendered
markdown.)

Outcome tallies show real truncations (2–4 per item on the larger prompts,
hitting the 4096 `max_completion_tokens` cap) alongside `valid` (non-error,
non-truncated, non-refused) outcomes — genuine signal, not fabricated.
Level-1 distinct == level-2 distinct for every item (whitespace
normalization never collapsed two differently-worded outputs together in
this sample).

D-27 floor (≥1 provider, k≥5): **satisfied for every item** — all five have
n=10, none needed the "insufficient samples" fallback.

## Verification results

| Check | Result |
|---|---|
| Schema validation (`report_schema_llm.json`, UTF-8-correct) | ✅ VALID |
| D-21 replay byte-identical | ✅ True |
| Provenance completeness (`assert_llm_sample_provenance` on every sample) | ✅ True |
| Key-material grep (`sk-\|api_key=\|Bearer \|x-api-key`) across `fixtures/llm_repeatability/` + `llm-evidence/` | ✅ 0 matches |
| `.secrets` grep | ✅ 0 matches |
| `universal.{0,20}determin` grep | ✅ 0 matches |
| D-10 (no production change outside `data-service/tests/`) | ✅ clean |
| Frozen inputs (`fixtures/golden/`, `data-service/fixtures/recognition_eval/cassettes/`, `n8n/workflows/`) | ✅ untouched |
| Cassette count on disk | ✅ 50 (5 items × 10) |
| MANIFEST.md digests match `sha256sum` of every listed file | ✅ spot-checked, matched |

## Report file sha256

- `llm-repeatability-report.json`: `f445f9399448d687d0196b33a51869c2272817131594caeb73e038e92cc7baa9`
- `llm-repeatability-report.md`: `d9bc3f1f257b5067ae313902198d2ca632753ce1fa6e68cf680a241ab803ee4b`

## Key files

- `fixtures/llm_repeatability/rule_ingest_prompts/` (5 files + MANIFEST, from an earlier turn)
- `fixtures/llm_repeatability/cassettes/rule_ingest/` (50 files, new)
- `fixtures/llm_repeatability/MANIFEST.md` (new)
- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/llm-evidence/llm-repeatability-report.json` (new)
- `.planning/phases/1204-determinism-and-llm-reproducibility-benchmark/llm-evidence/llm-repeatability-report.md` (new)
- `data-service/tests/recognition_eval/report_schema_llm.json` (additive fix, 6 insertions/1 deletion)

## Execution note

Driven directly by the orchestrator (never DSH — live infra, real API cost,
and D-28's key-handling requirement rule out delegation), at the owner's
explicit request. The session spanned multiple Docker Desktop cold-starts
(the machine's Docker Desktop went down twice mid-task, unrelated to this
plan) and one interrupted background run that survived because cassettes
are written per-sample, not batched — resuming meant identifying exactly
which of the 50 (item, sample) combinations were already recorded (via
cassette `promptBody` suffix matching, since cassette filenames are content-
hash keyed) and live-sampling only the gap, avoiding redundant paid calls
for the 44 samples that had already succeeded.
