---
tags: [session, bug-fix, debugging]
date: 2026-08-17
---

# Session: 2026-08-17 — Rules Ingest Silent-Failure Fix + LLM Provider-Test Defect

## Goal

Debug and fix the rules-ingest bug where ingesting a new rule ("minimum area of swimming pool is 45 m2") reported success in the session history but wrote zero nodes to Neo4j. A secondary defect in LLM provider testing was also discovered and fixed.

## What Was Done

### Bug 1: Rules-Ingest Silent-Failure (Three Stacked Defects)

**Root Causes Identified:**
1. `validate_cypher()` accepted `MERGE (x [Label] {...})` — square brackets where a `:Label` belongs. Neo4j rejected with `Neo.ClientError.Statement.SyntaxError`, rolled back the entire transaction, but the workflow reported success because HTTP 200 is returned even on statement failure inside `errors[]`.
2. Greedy relationship extraction read `swrlb:greaterThan` from inside a quoted SWRL body, so corrective-feedback retry named a relationship the Cypher never contained.
3. `Build Response` hardcoded `status: "ok"` based on a MERGE count from the *text*, not from Neo4j's response; `errors[]` was never inspected.

**Fixes Deployed:**
- `data-service/dg_context.py`: Added `_MALFORMED_NODE_PATTERN` regex to detect and reject bracket pseudo-labels with violation code `malformed_node_pattern`. Added `_strip_quoted()` to exclude quoted strings from relationship extraction.
- `n8n/workflows/rules-to-metagraph.json`: `Build Response` now inspects Neo4j's `errors[]` and returns `status: "error"` with the error message when present. `Execute LLM Cypher` and `Annotate Graph Props` both contribute. Also: `Prepare Graph Payload` now strips `;` statement separators outside quoted strings (single chained query instead of splitting, since variable scope doesn't survive across statements).
- `ui-v2/src/lib/graphApi.js`: `pollExecution()` now surfaces `data?.message` in the failure throw instead of a bare "Workflow failed."

**Verification:**
- 732 Python tests pass (data-service suite).
- Deployed and re-tested: rule "minimum ceiling height of sauna is 2.1 m" now writes proper nodes (R_SAUNA_HASHEIGHTM_MIN_2.1_V with HAS_BODY/HAS_HEAD structure, 1126 → 1134 node count). Graph Viewer query returns them through nginx proxy.

### Bug 2: LLM Provider Test Always Used Saved Provider

**Root Cause:**
`POST /llm/settings/test` only read persisted settings. Selecting "Anthropic" in the AI Engine panel still tested your saved DeepSeek key and reported success — every provider appeared to connect.

**Fixes Deployed:**
- `data-service/llm_gateway.py`: Added `TestConnectionPayload` request model to carry the panel's current provider/model/apiKey/baseUrl selection.
- `data-service/app.py`: `test_llm_settings()` now accepts optional payload. If a provider is named that differs from the saved one and no key is provided for it, returns an actionable error instead of borrowing the saved provider's key. Ollama is exempt (it runs locally, takes no key).
- `ui-v2/src/lib/llmApi.js`: `testConnection()` now sends the current selection (provider, model, apiKey, baseUrl) in the request body.
- `ui-v2/src/screens/AiEngineScreen.jsx`: `handleTest()` builds a selection object before calling `testConnection(selection)`. Test Connection button also enabled when an unsaved key is typed.

**Verification:**
- 736 Python tests pass (full data-service suite including 54 llm_gateway tests).
- Deployed and tested:
  - `{"provider":"openai"}` → success (saved provider)
  - `{"provider":"anthropic","model":"claude-sonnet-5"}` → error "No API key configured for anthropic"
  - `{"provider":"ollama"}` → error "Provider returned HTTP 404" (Ollama offline, but test is honest — not reporting false success)

### Deep Finding: n8n 2.x Draft vs. Published Versions

The three-month workflow drift (Phase-29 refactor drafted 2026-07-12 but last published 2026-07-05) happened because **n8n 2.x executes the *published* workflow, not the draft in the database**. Reading `workflow_entity.nodes` or `n8n export:workflow` looks correct but production webhooks still use the old pipeline. The previously published version is backed up in the scratchpad as `n8n-published-backup-rules-ingest.json` for safety.

## Decisions Made

- Malformed node pattern (bracket pseudo-labels) is a validation defect, not a parse defect → feeds the existing corrective-feedback retry loop (max 3 attempts).
- Ollama provider test exempted from API-key requirement since it's local; exemption scoped to *explicit* ollama requests (preserves "No API key configured" contract for unconfigured gateways).
- n8n workflows deployed to production require three steps: `import` (updates draft), `publish:workflow` (ships to prod), `restart n8n` (activates). Import alone is not sufficient.

## Issues Encountered

- PowerShell here-string syntax (`@'...'@`) leaked into git commit message during initial commit (fixed with amend).
- Greedy regex in relationship extraction was a latent issue exposed by the swimming pool example (SWRL body with embedded `:greaterThan` looked like a real relationship type).

## Next Steps

- Browser UI verification: hard-refresh and click through AI Engine panel + Graph Viewer (no browser tool available in this session, so API/proxy layer verified only).
- Monitor live ingests for any additional edge cases in the malformed-node detection or Neo4j error surfacing.
- Consider adding a lint/validation step to the deploy pipeline to catch similar silent-success patterns in future n8n workflows.

## Related Notes

- [[n8n-draft-vs-published-versions|n8n runs the published version, not the draft]]
- [[neo4j-http-tx-200-with-errors|Neo4j tx/commit returns 200 with errors[]]]
- [[feedback-deploy-and-verify-live|Deploy and verify live, not just commit]]
- [[LLM Cypher output needs bracket nesting validation|existing debugging note — now resolved]]

## Commits

- `107969f` — fix(ingest): stop rule ingestion silently writing zero nodes
- `7fe9e20` — fix(llm): test the selected provider, not whatever is persisted

## Files Modified

- `data-service/dg_context.py` — validator improvements (bracket detection, quote-aware extraction)
- `data-service/tests/test_dg_context.py` — 4 new validator tests
- `data-service/llm_gateway.py` — `TestConnectionPayload` model
- `data-service/app.py` — provider-aware test endpoint
- `data-service/tests/test_llm_gateway.py` — 4 new provider-test cases
- `n8n/workflows/rules-to-metagraph.json` — error surfacing, semicolon stripping
- `ui-v2/src/lib/graphApi.js` — error message surfacing
- `ui-v2/src/lib/llmApi.js` — send current selection
- `ui-v2/src/screens/AiEngineScreen.jsx` — build selection, enable button on unsaved key

## Model

claude-opus-5

## Date

2026-08-17

## Files Changed

8

## Results

- **Bug 1 (ingest):** Zero-node silent-failure fixed. Rules now ingest and write proper nodes with correct structure.
- **Bug 2 (provider test):** Every provider no longer reports success. Anthropic/Ollama without keys fail honestly.
- **Deployed & verified end-to-end:** Both containers rebuilt, n8n re-imported/re-published/restarted, live tests passed.
