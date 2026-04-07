---
phase: 04-update-flow-endpoints
verified: 2026-04-07T00:00:00Z
status: human_needed
score: 4/4 roadmap success criteria verified
deferred:
  - truth: "Matching nodes are isolated in the graph view; user selects one or several nodes"
    addressed_in: "Phase 6"
    evidence: "Phase 6 goal: 'Architects can execute the full three-step update flow in the browser — describe what to change, see matching nodes highlighted, review red-highlighted diff, and confirm the edit'. Phase 6 SC-1: 'In Update Knowledge mode, submitting a prompt shows a selectable list of candidate note titles'"
  - truth: "User clicks Edit; LLM proposes edits to selected notes with changes highlighted in red"
    addressed_in: "Phase 6"
    evidence: "Phase 6 SC-2: 'After selecting one or more nodes and clicking Edit, the panel renders the LLM-proposed changes with deletions shown in red strikethrough and additions in red bold — no confirmed write has occurred yet'"
  - truth: "User reviews proposed changes in an inline text editor (textarea + diff panel with red-highlighted changes)"
    addressed_in: "Phase 6"
    evidence: "Phase 6 SC-3: 'The diff panel sits adjacent to an editable textarea containing the proposed text; the user can modify the textarea before confirming'. Phase 6 requirement: UIST-04"
human_verification:
  - test: "Import knowledge-update.json into n8n, activate the workflow, then call POST /knowledge/update/propose with a valid noteId and prompt; verify diffHtml in the response contains diff-ins and diff-del spans reflecting the LLM output"
    expected: "Response body contains diffs[0].diffHtml with at least one <span class=\"diff-ins\"> or <span class=\"diff-del\"> span; diffs[0].proposedContent is non-empty and differs from originalContent"
    why_human: "Requires n8n running with the workflow imported and activated, Ollama running with llama3.1, and a KnowledgeNote node in Neo4j — end-to-end LLM path cannot be exercised without live Docker services"
  - test: "Call POST /knowledge/update/match with a natural language prompt against a running data-service with notes in Neo4j; verify the full-text search index (knowledge_note_search) is used and results are ranked"
    expected: "Response contains candidates array with noteId, title, and score fields; results are ordered by score DESC"
    why_human: "Requires the full-text index knowledge_note_search to exist in Neo4j (created in Phase 1); unit tests mock read_many and cannot verify actual index query routing"
---

# Phase 4: Update Flow Endpoints Verification Report

**Phase Goal:** The three-step update backend is live — an architect can describe what to change, receive a list of matching notes, get a diff-annotated proposed edit, and confirm the write — with no LLM output silently overwriting Neo4j
**Verified:** 2026-04-07
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST `/knowledge/update/match` returns candidate list of KnowledgeNote IDs and titles ranked by full-text relevance | VERIFIED | `knowledge_update_match` in app.py line 1167 — uses `CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)` with `ORDER BY score DESC LIMIT 10`; unit test `test_match_returns_candidates` passes |
| 2 | POST `/knowledge/update/propose` returns diff-annotated content per note with additions and deletions marked as HTML spans | VERIFIED | `knowledge_update_propose` in app.py line 1181 calls `word_diff_html` which produces `<span class="diff-del">` and `<span class="diff-ins">` spans; 4 unit tests cover insertion/deletion/replacement/no-change cases |
| 3 | POST `/knowledge/update/confirm` writes new text to Neo4j and returns affected node IDs; original not overwritten until this call succeeds | VERIFIED | `knowledge_update_confirm` in app.py line 1216 — reads current `updatedAt`, compares, returns 409 on mismatch before any write; only calls `write_query` after lock check passes; `test_confirm_writes_and_creates_session` and `test_confirm_409_on_stale_updatedAt` both pass |
| 4 | Each confirmed update creates a KnowledgeSession node recording the prompt and affected nodes | VERIFIED | Confirm endpoint calls `write_query` with `MERGE (s:KnowledgeSession ...)` setting `mode='update'`, `prompt`, `result` (JSON of affectedNoteIds); `test_confirm_writes_and_creates_session` asserts `KnowledgeSession` appears in second write_query call |

**Score:** 4/4 roadmap success criteria verified

### Deferred Items

Items listed as Phase 4 requirements in REQUIREMENTS.md but addressed by later phases. The Phase 4 roadmap success criteria are all backend-only; the UI behaviors for UPDK-02/03/04 belong to Phase 6.

| # | Requirement | Item | Addressed In | Evidence |
|---|-------------|------|-------------|----------|
| 1 | UPDK-02 | Matching nodes are isolated in graph view; user selects one or several | Phase 6 | Phase 6 SC-1: "submitting a prompt shows a selectable list of candidate note titles" |
| 2 | UPDK-03 | User clicks Edit; LLM proposes edits highlighted in red | Phase 6 | Phase 6 SC-2: "panel renders the LLM-proposed changes with deletions in red strikethrough and additions in red bold" |
| 3 | UPDK-04 | User reviews proposed changes in inline text editor (textarea + diff panel) | Phase 6 | Phase 6 SC-3 + requirement UIST-04: "diff panel sits adjacent to an editable textarea" |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data-service/app.py` | match, propose, confirm endpoints + word_diff_html + call_n8n_sync | VERIFIED | All three endpoints at lines 1166, 1181, 1216; helpers at lines 50 and 74 |
| `data-service/tests/test_update_flow.py` | Unit tests for difflib logic and endpoint behavior | VERIFIED | 11 tests, all passing (2.47s run time confirmed) |
| `docker-compose.yml` | N8N_INTERNAL_URL env var for data-service | VERIFIED | Line 33: `N8N_INTERNAL_URL: http://n8n:5678`; `n8n` in data-service `depends_on` at line 40 |
| `n8n/workflows/knowledge-update.json` | n8n workflow for LLM-based note editing | VERIFIED | Valid JSON, 8 nodes, webhookId `dg-knowledge-update`, path `dg/knowledge-update` |
| `test/test_phase04_update_flow.sh` | End-to-end integration test script | VERIFIED | Bash syntax OK; covers all three endpoints plus 400 and 409 error cases with cleanup |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| data-service/app.py (match endpoint) | Neo4j knowledge_note_search index | `CALL db.index.fulltext.queryNodes` parameterized query | WIRED | Line 1171: exact string `fulltext.queryNodes('knowledge_note_search', $query)` |
| data-service/app.py (confirm endpoint) | Neo4j KnowledgeNote + KnowledgeSession | write_query with updatedAt comparison | WIRED | Line 1233: `if existing["updatedAt"] != item.updatedAt` raises 409; lines 1238 and 1246 call write_query for note update and session MERGE |
| data-service/app.py (propose endpoint) | n8n/workflows/knowledge-update.json (webhook) | `call_n8n_sync` POST to `/webhook/dg/knowledge-update` | WIRED | Line 1196-1199: `call_n8n_sync(webhook_path="dg/knowledge-update", body={...})` |
| n8n/workflows/knowledge-update.json (Post Execution Result) | data-service/app.py (execution-result endpoint) | HTTP POST to `/execution-result` with proposedText | WIRED | knowledge-update.json line 130-132: URL `http://data-service:8000/execution-result`, payload includes `proposedText` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `knowledge_update_match` | `rows` | `read_many(CALL db.index.fulltext.queryNodes(...))` | DB query present, parameterized with `$query`, `$project`, `$graph` | FLOWING |
| `knowledge_update_propose` | `note` | `read_single(MATCH (n:KnowledgeNote...))` + `call_n8n_sync` | DB query fetches real note; n8n/Ollama produces `proposedText` | FLOWING (live services needed for LLM segment — see human verification) |
| `knowledge_update_confirm` | `existing` | `read_single(MATCH (n:KnowledgeNote...))` for lock check | DB query present; write path uses `write_query` with parameterized Cypher | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| word_diff_html produces diff-del / diff-ins spans | `python -m pytest data-service/tests/test_update_flow.py -v` | 11 passed in 2.47s | PASS |
| match endpoint rejects empty prompt with 400 | `test_match_empty_prompt_returns_400` in test suite | PASSED | PASS |
| confirm endpoint returns 409 on stale updatedAt | `test_confirm_409_on_stale_updatedAt` in test suite | PASSED | PASS |
| confirm endpoint rejects content > 100KB with 413 | `test_confirm_rejects_oversized_content` in test suite | PASSED | PASS |
| knowledge-update.json is valid JSON with 8 nodes | `python -c "import json; json.load(open(...))"` | Valid, 8 nodes | PASS |
| test_phase04_update_flow.sh passes bash syntax check | `bash -n test/test_phase04_update_flow.sh` | Syntax OK | PASS |
| knowledge-update.json contains no Neo4j writes | grep for cypher/MATCH/CREATE/MERGE/neo4j | Zero matches | PASS |
| knowledge-update.json has no `format:json` (plain text mode) | grep for `"format"` | Zero matches | PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UPDK-01 | 04-01, 04-02 | User types update prompt; LLM identifies matching notes via full-text search | SATISFIED | `POST /knowledge/update/match` — full-text search on `knowledge_note_search`, LIMIT 10, ranked by score |
| UPDK-02 | 04-01, 04-02 | Matching nodes isolated in graph view; user selects | DEFERRED to Phase 6 | UI node selection not in Phase 4 scope; Phase 6 SC-1 covers this |
| UPDK-03 | 04-01, 04-02 | User clicks Edit; LLM proposes edits highlighted in red | DEFERRED to Phase 6 | Phase 6 SC-2 covers the Edit flow with red highlighting |
| UPDK-04 | 04-01, 04-02 | User reviews proposed changes in inline editor | DEFERRED to Phase 6 | Phase 6 SC-3 + UIST-04 covers the textarea + diff panel |
| UPDK-05 | 04-01, 04-02 | User clicks Confirm; changes saved; sidebar notification | SATISFIED (backend) | `POST /knowledge/update/confirm` writes note content; 409 on stale data; UI notification deferred to Phase 6 SC-4 |
| UPDK-06 | 04-01, 04-02 | Each update creates KnowledgeSession node | SATISFIED | Confirm endpoint calls `MERGE (s:KnowledgeSession ...)` with `mode='update'`, prompt, result |

No orphaned requirements: all 6 Phase 4 requirement IDs appear in plan frontmatter. UPDK-02/03/04 are backend-supported (API exists) but UI surface deferred to Phase 6.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `data-service/app.py` | 1201-1202 | `if not proposed_text: proposed_text = note["content"]` — fallback to original when LLM returns empty | Info | Intentional design decision (documented in 04-01-SUMMARY.md "Known Stubs"); propose step falls back gracefully until n8n workflow is active. Does not affect correctness of confirm/write path. |

No blockers or warnings. The one info-level pattern is a documented intentional fallback, not a stub.

### Human Verification Required

#### 1. End-to-End Propose with Live LLM

**Test:** Start all Docker services (`docker compose up -d`). Import `n8n/workflows/knowledge-update.json` via n8n UI (Settings > Import Workflow) and activate it. Run the integration test script: `bash test/test_phase04_update_flow.sh`
**Expected:** Tests 1-5 all show PASS; Test 3 (propose) returns diffs with non-empty `diffHtml` containing diff-ins or diff-del spans; Test 4 (confirm) returns `affectedNoteIds` and `sessionId`; Test 5 (stale updatedAt) returns HTTP 409. Final line shows `0 failed`.
**Why human:** Requires running Docker stack with n8n, Ollama (llama3.1 model), Neo4j, and data-service all up and connected. The workflow must be manually imported and activated in the n8n UI. Cannot be verified without live services.

#### 2. Full-Text Index Query Routing Verification

**Test:** Ensure the Phase 1 schema (knowledge_note_search full-text index) is present. With the Docker stack running, call `POST http://localhost:8000/knowledge/update/match` with `{"prompt": "building height", "project": "<any project with notes>"}`.
**Expected:** Response contains `candidates` array with `noteId`, `title`, and `score` fields; results are ordered by relevance score descending.
**Why human:** Unit tests mock `read_many` — they do not verify that the Neo4j full-text index actually exists and responds correctly to the query. This requires Neo4j with the index created by Phase 1 and at least one KnowledgeNote in the project.

### Gaps Summary

No gaps. All four roadmap success criteria are fully implemented and verified. The only human verification items concern live-service behavior (n8n/Ollama end-to-end and Neo4j full-text index routing) that cannot be tested programmatically.

Requirements UPDK-02, UPDK-03, UPDK-04 are listed in Phase 4 plan frontmatter but are UI behaviors explicitly addressed in Phase 6 — they are deferred, not missing.

---

_Verified: 2026-04-07_
_Verifier: Claude (gsd-verifier)_
