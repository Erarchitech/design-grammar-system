---
phase: 15-specgraph-runtime-rename
plan: 03
subsystem: n8n-workflows
tags: [rename, n8n, knowledge-to-spec, propagation]
status: complete
requires: [15-01, 15-02]
provides: [spec-ingest.json, spec-query.json, spec-update.json]
affects: [n8n/workflows/, sc#4-cleanup]
tech-stack:
  added: []
  patterns: [n8n-rename-connections-lockstep, git-mv]
key-files:
  created:
    - n8n/workflows/spec-ingest.json
    - n8n/workflows/spec-query.json
    - n8n/workflows/spec-update.json
  modified: []
  deleted:
    - n8n/workflows/knowledge-ingest.json
    - n8n/workflows/knowledge-query.json
    - n8n/workflows/knowledge-update.json
    - n8n/workflows/_active-graph-query.json
    - n8n/workflows/_all-workflows-export.json
decisions:
  - "Webhook paths preserved (dg/knowledge-ingest, dg/knowledge-query, dg/knowledge-update) — SPEC-02 URL compatibility"
metrics:
  duration: 4m
  completed_date: 2026-07-03
  tasks_completed: 4
  total_tasks: 4
---

# Phase 15 Plan 03: n8n Knowledge Workflow Rename

**One-liner:** Renamed three canonical n8n knowledge workflows (ingest/query/update) to spec-* with updated internal names, node display names, and inline Cypher labels, plus deleted two stale export snapshots -- all webhook path values preserved for UI compatibility.

## Objective

Propagate the Spec* rename through the three canonical n8n knowledge workflows -- file names, workflow `name`, node display names (with their `connections` references), and inline Cypher labels -- while preserving the webhook `path` values the UI depends on. Delete the two non-canonical export snapshots that would otherwise carry stale Knowledge* references past this phase.

## Tasks Completed

| Task | Name | Commit | Key files |
|------|------|--------|-----------|
| 1 | knowledge-ingest.json -> spec-ingest.json | 867685b | spec-ingest.json, ~knowledge-ingest.json |
| 2 | knowledge-query.json -> spec-query.json | ffc134d | spec-query.json, ~knowledge-query.json |
| 3 | knowledge-update.json -> spec-update.json | 104785a | spec-update.json, ~knowledge-update.json |
| 4 | Delete export snapshots | (gitignored, rm on fs) | ~_active-graph-query.json, ~_all-workflows-export.json |

### Task 1: Rename knowledge-ingest.json -> spec-ingest.json

- `git mv n8n/workflows/knowledge-ingest.json n8n/workflows/spec-ingest.json`
- Top-level workflow name: `"Knowledge Ingest"` -> `"Spec Ingest"`
- Renamed node `"Write KnowledgeSession"` -> `"Write SpecSession"` with matching `connections` updates (L-1)
- Replaced inline Cypher labels: `KnowledgeNote`/`KnowledgeTag`/`KnowledgeClass`/`KnowledgeSession` -> `Spec*`
- Replaced graph literal `'KnowledgeGraph'` -> `'SpecGraph'` in functionCode and bodyParametersJson
- Updated code comments referencing `KnowledgeNote`/`KnowledgeTag` to avoid stale tokens
- Preserved webhook path `dg/knowledge-ingest` and webhookId

**Verification:** JSON valid, zero Knowledge* graph-layer tokens, connections integrity holds (all keys and values reference existing node names).

### Task 2: Rename knowledge-query.json -> spec-query.json

- `git mv n8n/workflows/knowledge-query.json n8n/workflows/spec-query.json`
- Top-level workflow name: `"Knowledge Query"` -> `"Spec Query"`
- Renamed node `"Write KnowledgeSession"` -> `"Write SpecSession"` with connections fix (L-1)
- Replaced graph literal `'KnowledgeGraph'` -> `'SpecGraph'` in functionCode parameters and bodyParametersJson
- Preserved webhook path `dg/knowledge-query` and webhookId
- Preserved fulltext index name `knowledge_note_search` (index name, not a label)

**Verification:** JSON valid, zero Knowledge* graph-layer tokens, connections integrity holds.

### Task 3: Rename knowledge-update.json -> spec-update.json

- `git mv n8n/workflows/knowledge-update.json n8n/workflows/spec-update.json`
- Top-level workflow name: `"knowledge-update"` -> `"spec-update"`
- Scanned all node names -- no Knowledge* tokens found (RESEARCH confirmed zero inline Cypher labels)
- Preserved webhook path `dg/knowledge-update` and webhookId
- Preserved data-service URL references unchanged (SPEC-02)

**Verification:** JSON valid, workflow name updated, zero Knowledge* graph-layer tokens, connections integrity holds.

### Task 4: Delete export snapshots

- Deleted `n8n/workflows/_active-graph-query.json` (gitignored, 27KB)
- Deleted `n8n/workflows/_all-workflows-export.json` (gitignored, 324KB)
- Both were non-canonical generated exports (D-05); canonical files are the source of truth

## Deviations from Plan

### Operational

**1. [Rule 2] Export files gitignored -- used `rm` instead of `git rm`**

- **Found during:** Task 4
- **Issue:** Both export files (`_active-graph-query.json`, `_all-workflows-export.json`) are listed in `.gitignore` and were not tracked by git. `git rm` failed with "did not match any files".
- **Fix:** Used `rm` to delete from filesystem. Since files were already gitignored, nothing to stage.
- **Files modified:** (deleted from filesystem only)
- **Result:** Identical outcome -- both files removed.

### Auto-fixed Issues

**None** -- plan executed as specified.

## Verification Results

```
Task 1: PASS (JSON valid, Knowledge*-clean, webhook path preserved, connections intact)
Task 2: PASS (JSON valid, Knowledge*-clean, webhook path preserved, connections intact)
Task 3: PASS (JSON valid, Knowledge*-clean, workflow name spec-update, connections intact)
Task 4: PASS (both export files deleted)
```

## Threat Surface

No new threat surface introduced. All three workflows preserve their webhook paths and webhookIds. The deleted export snapshots reduce stale reference drift.

## Success Criteria

SPEC-03 satisfied: the three canonical n8n knowledge workflows are renamed and operate on Spec* labels with intact node graphs and preserved webhook URLs; the two stale export snapshots are gone so they cannot re-introduce Knowledge* references (SC#4).

## Self-Check

```
FOUND: n8n/workflows/spec-ingest.json
FOUND: n8n/workflows/spec-query.json
FOUND: n8n/workflows/spec-update.json
MISSING: n8n/workflows/knowledge-ingest.json (deleted - expected)
MISSING: n8n/workflows/knowledge-query.json (deleted - expected)
MISSING: n8n/workflows/knowledge-update.json (deleted - expected)
MISSING: n8n/workflows/_active-graph-query.json (deleted - expected)
MISSING: n8n/workflows/_all-workflows-export.json (deleted - expected)
FOUND: 867685b (Task 1 commit)
FOUND: ffc134d (Task 2 commit)
FOUND: 104785a (Task 3 commit)
```

## Self-Check: PASSED
