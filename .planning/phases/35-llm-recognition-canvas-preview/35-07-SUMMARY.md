---
phase: 35-llm-recognition-canvas-preview
plan: 07
subsystem: api
tags: [llm-gateway, structured-output, anthropic, openai, ollama, truncation, reproducibility]

requires:
  - phase: 28-cloud-llm-connector
    provides: llm_gateway.py provider adapters behind one POST /llm/generate contract
  - phase: 35-llm-recognition-canvas-preview
    provides: cg_schemas.to_strict_json_schema() output (passed in as a plain dict)
provides:
  - GenerationOptions — internal-only temperature / max_tokens / output_schema
  - Per-provider output-cap spelling (Anthropic max_tokens, OpenAI max_completion_tokens, Ollama num_predict)
  - GenerateResponse.truncated + finish_reason from each provider's own stop reason
  - negotiate_structured_output() — capability detection, never assumption
affects: [35-10, 35-12, 35-13, 35-14]

tech-stack:
  added: []
  patterns:
    - "Internal-only options object kept OFF the public request body, so cost-DoS and provider pass-through stay unreachable from the HTTP surface"
    - "Capability DETECTION over assumption: probe or classify by provider family + base_url, degrade to none on unknown"

key-files:
  created: []
  modified:
    - data-service/llm_gateway.py
    - data-service/tests/test_llm_gateway.py

key-decisions:
  - "GenerationOptions is deliberately NOT on GenerateRequest, which IS the public POST /llm/generate body — max_tokens: 1000000 would be a cost-DoS and a raw output_schema an unvalidated provider pass-through. A test pins GenerateRequest's field set"
  - "OpenAI uses max_completion_tokens: max_tokens is deprecated and REJECTED by o-series and GPT-5.x, so the old body would have 400'd against those models"
  - "OpenAI refusals surface as finish_reason='refusal' so the caller raises a distinct violation instead of a misleading bad_json"
  - "negotiate_structured_output(): anthropic recent family and openai-on-api.openai.com => json_schema_strict; any other openai base_url (DeepSeek/Groq/Together/Azure) => json_object; ollama probed via /api/version; unknown => none. An unreachable Ollama degrades rather than raising"
  - "The negotiated mode is logged on every call — without it an eval result is uninterpretable"
  - "llm_gateway does not import cg_schemas: schema_for() takes an already-emitted dict, keeping the dependency arrow recognition -> gateway"

patterns-established:
  - "Backward-compatibility pin: with options omitted every adapter reproduces its prior body exactly, asserted by test rather than assumed"

requirements-completed: [RCGN-01]

coverage:
  - id: D1
    description: "GenerationOptions (temperature / max_tokens / output_schema) threaded as adapter.generate(req, api_key, options=...), kept off the public GenerateRequest body"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py — GenerateRequest field-set pin + options plumbing cases"
        status: pass
    human_judgment: false
  - id: D2
    description: "Per-provider output-cap spelling replaces the hardcoded 4096 cap that directly caused UAT F1"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py — per-provider body assertions (max_tokens / max_completion_tokens / num_predict)"
        status: pass
    human_judgment: false
  - id: D3
    description: "GenerateResponse.truncated + finish_reason derived from each provider's own stop reason; OpenAI refusals distinguished as finish_reason='refusal'"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py — truncation and refusal cases"
        status: pass
    human_judgment: false
  - id: D4
    description: "negotiate_structured_output() detects capability per provider/base_url and degrades to none on unknown; unreachable Ollama degrades rather than raising"
    requirement: RCGN-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py — negotiation matrix incl. unreachable-Ollama path"
        status: pass
    human_judgment: false
  - id: D5
    description: "Backward compatibility: with options omitted every adapter reproduces its prior body exactly, so /llm/generate, the n8n workflows and dg_context.generate_validated_cypher are unaffected"
    verification:
      - kind: unit
        ref: "in-container pytest — test_llm_gateway 50 passed; full suite 301 passed (was 281)"
        status: pass
    human_judgment: false

duration: unrecorded
completed: 2026-07-26
status: complete
---

# Phase 35-07: Gateway Generation Controls Summary

**The gateway now takes an internal-only `GenerationOptions`, spells the output cap correctly per provider, reports truncation and refusals, and negotiates structured-output capability instead of assuming it — with the public `/llm/generate` body unchanged.**

## Performance

- **Tasks:** all tasks executed
- **Files modified:** 2
- **Commits:** 1

## Accomplishments

- **Removed the direct cause of UAT F1.** The hardcoded 4096 output cap is gone, replaced by per-provider spelling: Anthropic `max_tokens`, OpenAI `max_completion_tokens`, Ollama `num_predict`.
- **Fixed a latent 400 against modern OpenAI models.** `max_tokens` is deprecated and *rejected* by o-series and GPT-5.x — the old body would have failed against them outright.
- **Made truncation observable.** `GenerateResponse.truncated` + `finish_reason` come from each provider's own stop reason. OpenAI refusals surface as `finish_reason='refusal'` so the caller raises a distinct violation instead of a misleading `bad_json`.
- **Closed defect D6 (uncontrolled temperature)** — a reproducibility defect first. Temperature is now pinned through `GenerationOptions`.
- **Capability detection, not assumption.** `negotiate_structured_output()` classifies Anthropic recent family and OpenAI-on-`api.openai.com` as `json_schema_strict`; any other OpenAI `base_url` (DeepSeek/Groq/Together/Azure) as `json_object`; probes Ollama via `/api/version`; and degrades anything unknown to `none`. An unreachable Ollama degrades rather than raising. The negotiated mode is logged on every call — without that, an eval result is uninterpretable.

## Task Commits

1. **Options, token spelling, truncation, negotiation** — `7a4d641` (feat)

## Files Created/Modified

- `data-service/llm_gateway.py` (+281/-…) — `GenerationOptions`, per-provider caps, `truncated`/`finish_reason`, `negotiate_structured_output()`, `schema_for()`
- `data-service/tests/test_llm_gateway.py` (+181) — 20 new tests

## Decisions Made

- **`GenerationOptions` stays off `GenerateRequest`.** That model *is* the public `POST /llm/generate` body: `max_tokens: 1000000` would be a cost-DoS and a raw `output_schema` an unvalidated provider pass-through. A test pins `GenerateRequest`'s field set so the boundary cannot erode.
- **`llm_gateway` does not import `cg_schemas`.** `schema_for()` takes an already-emitted dict, keeping the dependency arrow recognition → gateway.
- **Backward compatibility is asserted, not assumed.** With `options` omitted, every adapter reproduces its prior body exactly (4096 cap, no temperature key, no `response_format`), so `/llm/generate`, the n8n workflows and `dg_context.generate_validated_cypher` are unaffected. Timeouts unchanged.

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- 35-10's `output_token_budget()` has a gateway that will honour the budget it computes.
- 35-12 can drive strict-mode decoding and read `truncated` to raise a real violation.
- 35-13/35-14 can log the negotiated mode alongside each eval figure, which is what makes the figure interpretable.

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*
*Summary reconstructed from commit 7a4d641 during Wave 1 close-out (2026-07-26).*
