---
phase: 05-ui-mode-restructuring-insert-and-query-panels
plan: 01
subsystem: graph-viewer
tags: [ui, sidebar, knowledge, tabs, polling]
dependency_graph:
  requires: [phase-03-knowledge-workflows]
  provides: [sidebar-tabs, knowledge-state, insert-knowledge-panel, knowledge-polling]
  affects: [graph-viewer/index.html]
tech_stack:
  added: []
  patterns: [tab-bar-conditional-rendering, knowledge-polling-wrapper, folder-ingest-sync, prompt-ingest-async]
key_files:
  created: []
  modified:
    - graph-viewer/index.html
decisions:
  - Tabs reuse existing .prompt-tab CSS — no new CSS classes needed
  - Knowledge dropdown uses same pattern as existing mode dropdown with separate ref
  - Polling wrapper is fully independent from existing DesignRules polling state
metrics:
  completed: 2026-04-07
---

# Phase 05 Plan 01: Sidebar Restructuring + Knowledge State + Insert Knowledge Panel Summary

Tabbed sidebar with DesignRules/Specs&Notes top-level tabs, knowledge mode dropdown, Insert Knowledge panel (From Folder + From Prompt), and knowledge-specific async polling wrapper — all using existing CSS classes and React.createElement patterns.

## Changes Made

### Task 1: State scaffold + top-level tabs + knowledge dropdown + conditional sidebar rendering + polling wrapper

- Added `KNOWLEDGE_OPTIONS` array with Insert Knowledge and Query Knowledge options
- Added 14 new state variables for knowledge UI (`activeTab`, `knowledgeMode`, `insertTab`, `folderPath`, `knowledgePromptText`, etc.)
- Added 4 new refs (`knowledgeModeDropdownRef`, `knowledgeStepRef`, `knowledgeStepStartedAtRef`, `knowledgePollRef`)
- Added knowledge step arrays (`knowledgeInsertSteps`, `knowledgeQuerySteps`)
- Added outside-click handler useEffect for knowledge mode dropdown
- Added knowledge polling helpers: `clearKnowledgePoll`, `setKnowledgeWorkflowStep`, `finalizeKnowledgeWorkflowStep`, `applyKnowledgeProgressUpdate`, `startKnowledgePollingLatest`
- Restructured sidebar return with `activeTab` conditional rendering
- DesignRules tab wraps all existing sidebar content unchanged
- Specs&Notes tab renders knowledge mode dropdown

### Task 2: Insert Knowledge panel — From Folder and From Prompt sub-tabs

- Added `submitFolderIngest` function — synchronous POST to `/data-service/knowledge/ingest/folder`
- Added `submitKnowledgeIngest` function — async POST to `/n8n/webhook/dg/knowledge-ingest` with polling
- From Folder sub-panel: text input, tooltip, Import Notes button
- From Prompt sub-panel: textarea, Insert Knowledge button, progress bar, step indicators
- Response textarea shared between both sub-modes
- Query Knowledge placeholder added for Plan 02

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1+2 | 6cecdde | feat(05-01): sidebar tab restructuring + knowledge state + Insert Knowledge panel |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
