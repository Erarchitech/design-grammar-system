---
tags: [debugging, n8n, cypher, workflow, v8.0]
date: 2026-07-07
---

# n8n Workflows Had a Fatal Quote Bug and Silent Project-Scoping Failure

Discovered during v8.0 Phase 23 (Graph Viewer) live verification against the
full Docker stack. Both bugs predate v8.0 and also affected the legacy SPA.

## Bug 1 — `graph-query-mcp.json` hung forever

**Symptom:** every graph query (UI and curl alike) returned `{"status":"accepted","executionId":"..."}` and then never completed — polling `/data-service/execution-result/{id}` stayed `running` indefinitely.

**Root cause:** the "Build Cypher Prompt" Code node had unescaped `'...'` string literals nested inside a single-quoted JS string (introduced during the parked v9.0 rewiring). n8n logged `Unexpected string` on every execution and the node never ran.

**Fix:** re-quoted the offending lines with double quotes, re-imported the workflow (`docker cp` + `n8n import:workflow` + `update:workflow --active=true` + `docker restart n8n`), verified: query answered in ~5s.

## Bug 2 — ingested rules always landed in `default-project`

**Symptom:** rules ingested through the UI for a specific project scope showed up under `default-project` in Neo4j instead.

**Root cause:** both workflows' "Set Input Defaults" node reads `$json.project_name || $json.project || 'default-project'` — but webhook payloads arrive nested under `$json.body.*`, not top-level `$json.*`. Only `rules_text` had a `$json.body.rules_text` fallback; `project_name` did not, so it always fell through to the default.

**Fix (two layers, for robustness):**
1. Patched both workflow JSONs to add the `$json.body.project_name` fallback.
2. The V2 UI client (`ui-v2/src/lib/graphApi.js`) also reproduces the legacy SPA's post-ingest `tagProjectNodes()` claim (see [[Neo4j node tagging required after n8n ingestion]]) — so scoping works correctly **even if the live n8n instance still runs an unpatched workflow version**.

## Caveat — live n8n has drifted from the repo

The running n8n instance carries newer workflow versions (versionCounter 22,
extra "Fetch Existing Entities" / smart-edit nodes) than `n8n/workflows/*.json`
— edited directly in the n8n web editor at some point. CLI re-import did not
reliably confirm the repo version became authoritative. **Action needed:**
export the live workflows back into the repo, or re-import repo → live, so
the two stop diverging.

## Related

- [[Neo4j node tagging required after n8n ingestion]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- `migrations/2026-07-07_validationgraph_to_validgraph.cypher` — separate pending data migration found the same session (v2.0-era validation data tagged `ValidationGraph` instead of schema-v4 `ValidGraph`)
