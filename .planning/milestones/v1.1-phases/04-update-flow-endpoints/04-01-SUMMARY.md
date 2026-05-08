---
phase: 04-update-flow-endpoints
plan: "01"
subsystem: data-service
tags: [fastapi, endpoints, difflib, update-flow, pytest, neo4j]
dependency_graph:
  requires: []
  provides: [match-endpoint, propose-endpoint, confirm-endpoint, word_diff_html, call_n8n_sync, pytest-scaffold]
  affects: [data-service/app.py, docker-compose.yml]
tech_stack:
  added: [pytest]
  patterns: [optimistic-lock, word-level-diff, n8n-polling, parameterized-cypher]
key_files:
  created:
    - data-service/tests/__init__.py
    - data-service/tests/conftest.py
    - data-service/tests/test_update_flow.py
  modified:
    - data-service/app.py
    - data-service/requirements.txt
    - docker-compose.yml
decisions:
  - word_diff_html uses Python difflib SequenceMatcher (autojunk=False) for word-level granularity
  - call_n8n_sync polls EXECUTION_RESULTS in-memory dict with 120s timeout and 1.5s sleep
  - Confirm optimistic lock compares updatedAt strings — no DB-level lock needed at current scale
  - MAX_CONTENT_SIZE = 100KB enforced pre-write to prevent oversized Neo4j property writes
metrics:
  duration: ~25 minutes
  completed: "2026-04-06"
  tasks_completed: 2
  files_modified: 6
---

# Phase 4 Plan 01: Update-Flow Endpoints Summary

Three FastAPI endpoints (match, propose, confirm) + word_diff_html + call_n8n_sync + pytest scaffold with 11 passing tests for the three-step knowledge update flow.

## What Was Built

### Task 1: Docker-compose fix + pytest scaffold + difflib helper

- **docker-compose.yml**: Added `N8N_INTERNAL_URL: http://n8n:5678` to data-service environment; added `n8n` to data-service `depends_on`
- **data-service/requirements.txt**: Appended `pytest`
- **data-service/tests/**: Created `__init__.py`, `conftest.py`, `test_update_flow.py`
- **data-service/app.py**: Added `import time`, `import urllib.request`; added `N8N_INTERNAL_URL` constant, `word_diff_html()` function, `call_n8n_sync()` function

### Task 2: Match, Propose, and Confirm endpoints

- **Pydantic models**: `UpdateMatchRequest`, `UpdateProposeRequest`, `NoteConfirmItem`, `UpdateConfirmRequest`
- **POST /knowledge/update/match**: Full-text search on `knowledge_note_search` index, top 10 results, 400 on empty prompt
- **POST /knowledge/update/propose**: Per-note n8n webhook call via `call_n8n_sync`, word diff via `word_diff_html`, 404 on missing note
- **POST /knowledge/update/confirm**: Optimistic lock check (409 on stale updatedAt), 100KB content guard (413), writes updated content + KnowledgeSession node
- **Tests**: 5 endpoint contract tests added (11 total)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 5be1e59 | feat(04-01): add word_diff_html, call_n8n_sync helpers + pytest scaffold |
| 2 | 8784726 | feat(04-01): add match, propose, confirm update-flow endpoints |

## Verification Results

```
python -m pytest data-service/tests/test_update_flow.py -v
11 passed in 1.49s
```

```
grep -c "knowledge/update" data-service/app.py  → 3
grep "N8N_INTERNAL_URL" docker-compose.yml      → N8N_INTERNAL_URL: http://n8n:5678
grep "MAX_CONTENT_SIZE" data-service/app.py     → MAX_CONTENT_SIZE = 100 * 1024
```

## Deviations from Plan

None - plan executed exactly as written.

## Threat Mitigations Applied

All four `mitigate` dispositions from the plan's threat register were implemented:

| Threat | Mitigation Applied |
|--------|-------------------|
| T-04-01: Tampering via Cypher injection | All Cypher uses `$param` placeholders — no f-string interpolation |
| T-04-03: DoS via oversized content | `MAX_CONTENT_SIZE = 100KB` check before any Neo4j write (413 response) |
| T-04-04: TOCTOU race on confirm | `updatedAt` comparison before write; 409 on mismatch |

## Known Stubs

- **POST /knowledge/update/propose**: Depends on `dg/knowledge-update` n8n workflow (Plan 02) for real LLM results. Falls back to original content if LLM returns empty. Functional structure is complete; real LLM output awaits Plan 02.

## Self-Check: PASSED

Files exist:
- data-service/app.py - modified with 3 endpoints + helpers
- data-service/tests/test_update_flow.py - 11 tests
- docker-compose.yml - N8N_INTERNAL_URL present

Commits exist:
- 5be1e59 - confirmed
- 8784726 - confirmed
