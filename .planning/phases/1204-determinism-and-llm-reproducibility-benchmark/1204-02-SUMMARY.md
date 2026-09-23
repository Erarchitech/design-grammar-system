# Plan 1204-02 Summary — D-20 Gateway Provenance Tracer

## What was built

Additive, response-only provenance fields on the LLM gateway so a provider alias
re-pointing behind a requested model id becomes observable (D-20), without ever
touching request behavior (D-10 measure-as-shipped).

- `data-service/llm_gateway.py`
  - `GenerateResponse` gains three additive optional fields, each `str | None = None`:
    `served_model`, `response_id`, `system_fingerprint`. Docstring records that
    `served_model` is provider-attested and may differ from `model` (the REQUESTED
    id, Correction 5 — never repointed).
  - `AnthropicAdapter.generate` populates `served_model=data.get("model")`,
    `response_id=data.get("id")` (no `system_fingerprint` — the Messages API has none).
  - `OpenAIAdapter.generate` populates all three via `.get`.
  - `OllamaAdapter.generate` populates `served_model=data.get("model")` only — no
    id/fingerprint/digest field invented for the `/api/generate` response, which
    carries none.
  - `model=req.model or ""` is untouched at all three return sites — the requested
    id keeps flowing unchanged.

- `data-service/tests/test_llm_gateway.py` — new class `TestGenerateProvenanceFields`
  appended (no existing class edited): per-adapter population tests (OpenAI x1,
  Anthropic x1, Ollama x1), per-adapter omission tests (all three return `None`
  when the provider response lacks the key), a default-construction/serialization
  test (`model_dump()` carries the three keys as `null`), and an end-to-end
  `/llm/generate` round-trip test with a mocked adapter proving additive-null
  backward compatibility.

- `spec/API.md` — new `### LLM Gateway` subsection inserted immediately before
  `### Identity`, inside the `## data-service` block: route table row for
  `POST /llm/generate`, request/response shape, and the response envelope example
  showing all eight fields including the three new ones.

## Key files

- `data-service/llm_gateway.py`
- `data-service/tests/test_llm_gateway.py`
- `spec/API.md`

## Verification results

Independently re-run by the orchestrator (not just the worker's self-report):

| Command | Result |
|---|---|
| `pytest test_llm_gateway.py -k "served_model or response_id or fingerprint"` | ✅ 8 passed |
| `pytest recognition_eval/ test_recognition_eval.py test_llm_gateway.py` | ✅ 114 passed, 1 skipped, 1 deselected |
| Key-material diff-grep | ⚠️ returns 1 — see note below |
| Taxonomy/determinism vocab diff-grep | ✅ 0 |
| Request-behavior diff-grep (temperature/max_tokens/etc.) | ✅ 0 |
| `served_model=data.get("model")` count | ✅ 3 |
| `response_id=data.get("id")` count | ✅ 2 |
| `system_fingerprint=data.get("system_fingerprint")` count | ✅ 1 |
| `app.py`/`cg_recognition.py`/`dg_context.py` diff | ✅ empty (D-10 untouched) |
| Frozen-input git status | ✅ empty |

**Note on the key-material grep (1 match, expected 0):** the single match is
`"apiKey": encrypt_value("sk-ant-test", "test-master-secret")` inside the new
`test_llm_generate_endpoint_serializes_served_model_response_id_fingerprint_additively`
test. This is a synthetic test fixture — the identical literal `"sk-ant-test"` paired
with `"test-master-secret"` already exists unmodified in the pre-existing
`TestGenerate.test_adapter_routing` (line 243, not part of this diff), which the
plan's own Task 3 action text instructed this test to mirror exactly
("patch app.get_adapter and app.load_persisted_llm_settings exactly like
TestGenerate.test_adapter_routing"). Not a credential leak — a coarse diff-scoped
grep matching a `sk-`-prefixed fake value that follows established test convention.
Judged a gate false-positive rather than a violation; flagged here for visibility
rather than silently passed.

## Execution note

Built via DSH `deepseek-v4-flash` workers. Four dispatch attempts: two died
immediately (TRANSPORT error, no writes), a third made partial progress
(`GenerateResponse` fields + all three adapter return sites) before dying, a
fourth resumed from that partial state and completed the test class + spec
section before also hitting a TRANSPORT error mid-verification. The orchestrator
verified all acceptance criteria independently and wrote this summary after the
final worker died before doing so itself.
