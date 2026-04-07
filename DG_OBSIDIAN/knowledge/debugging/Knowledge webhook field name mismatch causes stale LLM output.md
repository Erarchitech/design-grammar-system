---
tags: [debugging, ui, polling, n8n]
date: 2026-04-07
---

# Knowledge webhook field name mismatch causes stale LLM output

## Symptom

Insert Knowledge "From Prompt" always returns "Created note: Maximum floor-to-floor height Zone A" regardless of user input.

## Root Cause

Two issues compounded:

1. **Field name mismatch**: The UI sent `{ prompt, project }` but both n8n workflows (`knowledge-ingest.json`, `knowledge-query.json`) expect `{ prompt_text, project_name }` in their "Set Input Defaults" node. The expression `$json.body.prompt_text || $json.prompt_text || ''` resolved to empty string.

2. **Empty prompt → few-shot regurgitation**: With an empty `promptText`, the LLM only saw the few-shot example (about "Maximum floor-to-floor height Zone A") and returned that example's title verbatim.

3. **Stale polling**: Even after fixing field names, `/execution-result/latest/{workflow}` returned the previous completed result before the new workflow ran. The data-service stores no timestamp on results, so there was no staleness detection.

## Fix

1. Changed UI to send `prompt_text` / `project_name` (commit `3908cae`)
2. Added `startKnowledgePollingResult` for execution-ID-based polling when webhook returns `executionId` (commit `fdd7cb0`)
3. Added timestamp guard (`requestedAt`) in `startKnowledgePollingLatest` to skip results completed before the request was sent

## Prevention

When adding new n8n webhooks, always check the "Set Input Defaults" node for expected field names and match them in the UI. The n8n convention is `prompt_text` / `project_name`, not `prompt` / `project`.

## Related

- [[Async polling pattern for n8n workflow execution tracking]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
