---
tags: [decision, DeGram, v13.0, phase-1301, relay, llm, security]
date: 2026-10-06
status: implemented and deployed (framework c5966d4); D-24 in 1301-CONTEXT.md
---

# DeGram relay takes its model and key from the Web UI LLM settings

## Context

D-16 (plan 08) gave the DeGram relay its own operator config `degram-llm.json`, written by admin `PUT /degram/admin/llm-config`. The owner had already entered a key and model in the DG Web UI LLM settings and expected DeGram to use them; the relay was therefore unconfigured.

## Decision (owner, 2026-10-06, D-24, amends D-16)

The relay has no config of its own. Endpoint, model and system key come from `llm-settings.json` (admin `PUT /llm/settings`), read per call. Only provider type `openai` (OpenAI or an OpenAI-compatible `baseUrl`, https or localhost http; default `https://api.openai.com/v1`) is runnable; any other provider, a missing model/key, an unsafe URL or an undecryptable key leaves it unconfigured (503 `RELAY_NOT_CONFIGURED`). No fallback. `GET /degram/admin/llm-config` shows the effective config, `source: "llm-settings"`, and a `reason`, never the key. Provenance `requestedProvider` is the base URL host.

## Consequences

- `degram-llm.json` and `PUT /degram/admin/llm-config` removed; route table 96 → 95; SECURITY-BOUNDARY, API and OPERATIONAL-OUTCOMES updated.
- Changing the Web UI LLM settings changes DeGram's upstream at once (and the rule-ingest/n8n gateway with it).
- On 2026-10-06 the live relay reads the owner's own setting (`router.genproagent.ru/v1`, model `gena-mid`).

Related: [[knowledge/decisions/DeGram connects through a user-bound pairing connector in the Connectors tab]], [[sessions/2026-10-06 Phase 1301 audit-fix, DeGram identity and isolation beside open Hermes]].
