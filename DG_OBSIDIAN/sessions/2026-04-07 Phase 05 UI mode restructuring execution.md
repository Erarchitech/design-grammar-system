---
tags: [session, v1.1, phase-05, ui, execution]
date: 2026-04-07
---

# Session: 2026-04-07 — Phase 05 UI Mode Restructuring Execution

## Goal

Execute Phase 05 plans: restructure GraphViewerPage sidebar into DesignRules / Specs&Notes tabs, wire Insert Knowledge and Query Knowledge panels to live endpoints, auto-switch NeoVis to KnowledgeGraph view.

## What Was Done

### Plan 05-01 (Wave 1): Sidebar Restructuring + Insert Knowledge
- Added `KNOWLEDGE_OPTIONS` array with Insert Knowledge / Query Knowledge
- Added 14 new state variables and 4 refs for knowledge UI
- Added `knowledgeInsertSteps` / `knowledgeQuerySteps` step arrays
- Added knowledge polling wrappers: `clearKnowledgePoll`, `setKnowledgeWorkflowStep`, `startKnowledgePollingLatest`, `startKnowledgePollingResult`
- Restructured sidebar with `activeTab` conditional rendering (DesignRules / Specs&Notes tabs reusing `.prompt-tab` CSS)
- Knowledge mode dropdown (replicates existing mode dropdown pattern)
- Insert Knowledge panel: "From Folder" (path input + `submitFolderIngest`) and "From Prompt" (textarea + `submitKnowledgeIngest`)
- Commit: `6cecdde`

### Plan 05-02 (Wave 2): Query Knowledge + Fixes
- Added `requestKnowledge` function posting to `/n8n/webhook/dg/knowledge-query`
- Full Query Knowledge panel: prompt textarea, submit button, progress bar, step indicators, Response textarea, Workflow Cypher textarea
- Commit: `cffd714`

### Bug Fix: Stale polling result
- Root cause: `startKnowledgePollingLatest` returned the previous completed result immediately
- Fix: Added `startKnowledgePollingResult` (execution-ID-based), parse webhook response for `executionId`, timestamp guard in latest polling
- Commit: `fdd7cb0`

### Bug Fix: Wrong field names in webhook requests
- Root cause: UI sent `{ prompt, project }` but n8n expects `{ prompt_text, project_name }` — empty prompt caused LLM to regurgitate few-shot example
- Fix: Changed both `submitKnowledgeIngest` and `requestKnowledge` to send `prompt_text` / `project_name`
- Commit: `3908cae`

### Feature: KnowledgeGraph NeoVis auto-switch
- Added `KnowledgeGraph` branch to `buildCypher` showing KnowledgeNote/Tag/Session nodes
- Added `useEffect` on `activeTab` to auto-switch graph view
- Added labels and vis groups for KnowledgeNote (teal), KnowledgeTag (yellow), KnowledgeSession (purple) in `config.template.js`
- Added TAGGED_WITH and HAS_SESSION relationship captions
- Commit: `934721d`

## Decisions Made

- NeoVis auto-switches view based on active sidebar tab (DesignRules → MetaGraph/OntoGraph, Specs&Notes → KnowledgeGraph)
- Knowledge webhook field names: `prompt_text` / `project_name` (not `prompt` / `project`) to match n8n workflow expectations
- Execution-ID polling preferred over latest-polling when webhook returns `executionId`
- KnowledgeNote=teal (#4ecdc4), KnowledgeTag=yellow (#ffe66d), KnowledgeSession=purple (#a78bfa)

## Issues Encountered

- **Stale polling**: `/execution-result/latest/{workflow}` returned previous result. Fixed with execution-ID routing + timestamp guard.
- **Field name mismatch**: `prompt` vs `prompt_text` — n8n Set Input Defaults used `$json.body.prompt_text` which resolved to empty string. LLM saw only the few-shot example and output that title.
- **Disconnected graph nodes**: KnowledgeNote and KnowledgeSession nodes appear disconnected in NeoVis because they lack a parent class hub node. User wants visual grouping via hub nodes (deferred to next session).

## Next Steps

- Add parent class hub nodes to KnowledgeGraph NeoVis query (central "KnowledgeNote" and "KnowledgeSession" class nodes connecting all instances)
- Complete Phase 05 verification checkpoint
- Create 05-02-SUMMARY.md
- Proceed to Phase 06 (UI Update Panel + Inline Diff Editor)

## Related Notes

- [[Knowledge workflows use hybrid search-then-summarize for queries]]
- [[Async polling pattern for n8n workflow execution tracking]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[UI is a single-file React 18 SPA with no build step]]
