# Plan 1204-07 Summary — LLM Repeatability Measurement Driver

## What was built

The measurement instrument that wires 1204-02/03/04's primitives (provenance
fields, per-sample cassette keys, outcome taxonomy) into a runnable k-sample
sweep with a structurally-unpoolable report.

- `data-service/tests/recognition_eval/repeat_sweep.py` (new)
  - `REPEAT_SAMPLES = 10`, `MIN_SAMPLE_FLOOR = 5`, `SUBJECT_RECOGNITION`,
    `SUBJECT_RULE_INGEST` constants.
  - `resolve_adapter_once(provider, model)` — one adapter instance per
    provider, resolved once.
  - `run_one_item(item, provider, model, adapter)` — drives `sample_index`
    over `1..REPEAT_SAMPLES` (never 0) via `CassetteAdapter(sample_index=s)`,
    classifies each sample through `outcome_taxonomy.classify`, and stamps
    the `LLM_SAMPLE_PROVENANCE_FIELDS` block validated by
    `assert_llm_sample_provenance`, reading `served_model`/`response_id`/
    `system_fingerprint` from the 1204-02 `GenerateResponse` fields.
  - `run_repeat_sweep(items, providers)` — resolve-once-per-provider driver.
  - `normalize_level2(subject, raw_output)` (D-17) — canonical JSON of parsed
    recognition blocks for `SUBJECT_RECOGNITION`, whitespace-normalized
    Cypher for `SUBJECT_RULE_INGEST`.
  - `compute_item_metrics(item, records)` (D-13/D-17) — one stratum per
    provider, never pooled; distinct-output counts at both levels;
    modal-agreement rate; Wilson 95% CI via `scoring.wilson_interval` with
    an **integer** successes count; any cell with n < `MIN_SAMPLE_FLOOR`
    renders the string `"insufficient samples"` instead of a number.
  - `record_temperature(subject, ...)` (D-10) — `"not sent — provider
    default"` for rule-ingest (no `GenerationOptions` sent); as-sent sampling
    params for recognition.

- `data-service/tests/recognition_eval/report_schema_llm.json` (new) — its
  own draft 2020-12 schema, `additionalProperties: false`, no field name
  shared with the deterministic DE-01 schema (`tools/de01/report_schema.json`)
  and no accuracy/expected-label field (D-18/D-24). One genuine field
  collision found and fixed during verification: both schemas originally used
  `generatedAt` — renamed to `llmReportGeneratedAt` in this schema so the
  "no shared field, by construction" claim the schema's own docstring makes
  is actually true.

- `data-service/tests/recognition_eval/report.py` (extended, additive only)
  — `render_llm_repeatability_json` / `render_llm_repeatability_markdown`
  (new functions, existing `render_markdown`/`render_json`/`main` untouched),
  `MaxSamplesExceededError` + `enforce_max_samples()` (D-21 cost-runaway
  guard, exercised hermetically), `generate_llm_report_bytes()` (D-21 replay
  regeneration from committed cassettes, labeled `"scoring-pipeline
  determinism"` — never model determinism).

- `data-service/tests/recognition_eval/freeze_rule_ingest_prompts.py` (new)
  — `RULE_INGEST_SOURCES`: the five D-12 inputs (height rule from
  `fixtures/golden/fixture.json`; the three rules from
  `test/fixture_rules_v7.txt`, each named and hashed separately; the
  attribute-of source from `fixtures/golden/cq3-attribute-of/seed-cq3.cypher`).
  `render_rule_ingest_prompt()` delegates to an injectable renderer (no n8n
  import, no network — proven by an AST-based import check, not a
  fragile substring ban). `freeze_rule_ingest_prompts()` writes each
  rendered prompt plus a sha256 `MANIFEST`, using `write_bytes` (not
  `write_text`) so the hashed content and the on-disk bytes never diverge
  across platform newline conventions.

## Key files

- `data-service/tests/recognition_eval/repeat_sweep.py` (new)
- `data-service/tests/recognition_eval/report_schema_llm.json` (new)
- `data-service/tests/recognition_eval/test_repeat_sweep.py` (new)
- `data-service/tests/recognition_eval/report.py` (extended)
- `data-service/tests/recognition_eval/freeze_rule_ingest_prompts.py` (new)
- `data-service/tests/recognition_eval/test_freeze_rule_ingest_prompts.py` (new)

## Verification results

| Command | Result |
|---|---|
| `pytest test_repeat_sweep.py -k "not live"` | ✅ 14 passed |
| `pytest test_freeze_rule_ingest_prompts.py` | ✅ 4 passed |
| `pytest test_recognition_eval.py recognition_eval/ -k "not live"` (full regression) | ✅ 146 passed, 1 skipped, 12 deselected |
| `git status --porcelain -- data-service/` | ✅ only `data-service/tests/` paths (plus one unrelated pre-existing untracked file) |
| Frozen-input git status | ✅ empty |
| Key-material grep | ⚠️ 1 match — see note |

### Four real bugs found and fixed during orchestrator verification (not by the worker)

The DSH worker died before reaching its own verification step on every one of
6 dispatch attempts; all defects below were caught by the orchestrator's
independent test runs, not self-reported:

1. **Wrong schema path in a test** (`test_llm_report_schema_has_no_shared_or_accuracy_fields`):
   assumed the deterministic schema lived beside `report_schema_llm.json`;
   it's actually `tools/de01/report_schema.json`. Fixed the path
   (`parents[2]`, verified against actual directory depth) — this test now
   correctly proves the no-shared-field property.
2. **Genuine field collision**: both schemas independently used `generatedAt`
   as a top-level property name, violating the LLM schema's own docstring
   claim of zero shared fields "by construction". Renamed to
   `llmReportGeneratedAt` in `report_schema_llm.json`.
3. **Rule-parsing bug in `freeze_rule_ingest_prompts.py`**: the original
   blank-line block splitter merged all three `fixture_rules_v7.txt` rules
   into one block (they're separated by newlines, not blank lines, while the
   file's comment banner is blank-line-separated from them) — produced 4
   sources instead of the required 5. Rewrote the parser to drop comment
   lines and treat each remaining non-blank line as one rule; now correctly
   yields 3 named rule entries.
4. **Cross-platform hash-mismatch bug**: `write_manifest`/`freeze_rule_ingest_prompts`
   hashed the pre-write Python string but wrote files via `write_text`, which
   performs newline translation (`\n` → `\r\n`) on Windows — the on-disk bytes
   didn't match the hashed content whenever a prompt contained a newline.
   Switched both writes to `write_bytes` on the UTF-8-encoded string, so the
   hashed bytes and the written bytes are identical by construction.
5. **Over-reaching, fragile test assertion**: `test_freeze_is_renderer_injectable`
   banned the literal substring `"rules-to-metagraph"` from the freeze
   script's own source, which trips on the module's legitimate docstring
   explaining where the real (1204-09) renderer logic lives — not an actual
   import. Replaced with an AST-based check for actual `import` statements of
   `requests`/`httpx`/`urllib`/`n8n`-prefixed modules, which is what the plan
   actually requires (no n8n import, no network).

### Note on the key-material grep (1 match, expected 0)

`repeat_sweep.py:339`: `cassettes.generate(request, item.get("api_key"), options)`
— this is the `api_key` **parameter name** in the pinned
`generate(self, req, api_key, options=None)` signature (plan 1204-03), a dict
key lookup on a test item, not a literal credential. Same benign
false-positive class documented in plans 1204-02/04/05/06.

## Execution note

Built via DSH `deepseek-v4-flash` workers across 6 dispatch attempts (largest
plan in the phase alongside 1204-05, 4 tasks): 2 died before any write (one
flagged a since-confirmed-false fixture-path concern), 1 completed Tasks 1-2
fully (8 tests green), 2 more died deep in re-reading without writing new
content, and a final attempt completed the rest of Task 3 and all of Task 4.
The orchestrator's independent verification pass found and fixed the five
defects listed above — none were caught or reported by the worker itself,
underscoring why every plan in this phase was independently re-verified
rather than trusting worker self-reports.
