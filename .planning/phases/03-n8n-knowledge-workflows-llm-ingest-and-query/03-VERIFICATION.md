---
phase: 03-n8n-knowledge-workflows-llm-ingest-and-query
verified: 2026-04-06T00:00:00Z
status: human_needed
score: 6/8 must-haves verified
gaps:
  - truth: "Submitting a natural language prompt to POST /knowledge/ingest/prompt causes Ollama to extract a title, tags, and content, and a KnowledgeNote node appears in Neo4j within the async polling round-trip"
    status: partial
    reason: "ROADMAP SC-1 specifies the endpoint path POST /knowledge/ingest/prompt. This data-service endpoint does not exist. The functional goal is achieved but via POST /n8n/webhook/dg/knowledge-ingest (direct n8n webhook, accessed through nginx /n8n/ proxy). The ROADMAP contract path was replaced by a different URL in planning (CONTEXT.md D-09), but ROADMAP.md was not updated."
    artifacts:
      - path: "data-service/app.py"
        issue: "No /knowledge/ingest/prompt endpoint exists — the path named in ROADMAP SC-1 is absent"
      - path: "n8n/workflows/knowledge-ingest.json"
        issue: "Implements the ingest workflow correctly at dg/knowledge-ingest, but this differs from the ROADMAP-specified path"
    missing:
      - "Either update ROADMAP.md SC-1 to reflect the actual path /n8n/webhook/dg/knowledge-ingest, OR add a /knowledge/ingest/prompt endpoint to data-service that proxies to the n8n webhook"
  - truth: "Submitting a natural language question to POST /knowledge/query returns a human-readable answer drawn from matching notes, plus the Cypher query used for the search"
    status: partial
    reason: "ROADMAP SC-2 specifies the endpoint path POST /knowledge/query. This data-service endpoint does not exist. The functional goal is achieved but via POST /n8n/webhook/dg/knowledge-query (direct n8n webhook). Same path drift as SC-1."
    artifacts:
      - path: "data-service/app.py"
        issue: "No /knowledge/query endpoint exists — the path named in ROADMAP SC-2 is absent"
      - path: "n8n/workflows/knowledge-query.json"
        issue: "Implements the query workflow correctly at dg/knowledge-query, but this differs from the ROADMAP-specified path"
    missing:
      - "Either update ROADMAP.md SC-2 to reflect the actual path /n8n/webhook/dg/knowledge-query, OR add a /knowledge/query endpoint to data-service that proxies to the n8n webhook"
human_verification:
  - test: "Import and activate both n8n workflow JSON files"
    expected: "Both workflows appear as active in n8n UI at http://localhost:5678 after import"
    why_human: "n8n workflow import requires a browser UI interaction — no CLI import available for this n8n version"
  - test: "Run python test/test_phase03_knowledge_llm.py after workflow activation"
    expected: "All 5 tests (SC-4, SC-1, SC-3, SC-2, SC-5) print PASS, script exits with code 0"
    why_human: "Integration test requires running Docker stack with Ollama + Neo4j + n8n live; cannot verify programmatically without services running"
  - test: "POST to http://localhost:8080/n8n/webhook/dg/knowledge-ingest with body {prompt_text: 'Minimum setback distance is 5m', project_name: 'manual-test'}, then poll /data-service/execution-result/latest/knowledge-ingest"
    expected: "Ack returns {status: 'accepted'} immediately; after 30-60s, execution-result returns {status: 'completed', payload: {noteId, title, tags}} with a sensible title and at least one tag"
    why_human: "End-to-end LLM call through Ollama — requires running stack; verifies D-02 fallback behavior in production"
  - test: "POST to http://localhost:8080/n8n/webhook/dg/knowledge-query with body {prompt_text: 'What is the setback distance?', project_name: 'manual-test'}, then poll /data-service/execution-result/latest/knowledge-query"
    expected: "Payload contains non-empty answer string and cypher containing 'knowledge_note_search'"
    why_human: "End-to-end query requires running Ollama + Neo4j with notes already inserted; verifies QRYK-01 and QRYK-02 live behavior"
---

# Phase 3: n8n Knowledge Workflows + LLM Ingest and Query Verification Report

**Phase Goal:** Create n8n webhook workflows for knowledge note ingest (NL→Ollama→Neo4j) and knowledge query (NL→full-text search→Ollama answer). Add session tracking endpoint.
**Verified:** 2026-04-06
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                         | Status      | Evidence                                                                                                                                           |
|----|-------------------------------------------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Submitting NL prompt to POST `/knowledge/ingest/prompt` creates a KnowledgeNote in Neo4j within the async polling round-trip | ✗ PARTIAL   | No `/knowledge/ingest/prompt` endpoint in data-service. Functional goal exists at `/n8n/webhook/dg/knowledge-ingest`. ROADMAP path not implemented. |
| 2  | Submitting NL question to POST `/knowledge/query` returns NL answer + Cypher from search                                     | ✗ PARTIAL   | No `/knowledge/query` endpoint in data-service. Functional goal exists at `/n8n/webhook/dg/knowledge-query`. ROADMAP path not implemented.          |
| 3  | Every insert-prompt and query operation automatically writes a KnowledgeSession node with mode, prompt, result, createdAt    | ✓ VERIFIED  | knowledge-ingest.json: Write KnowledgeSession MERGE with mode='insert'. knowledge-query.json: Write KnowledgeSession MERGE with mode='query'. Both parameterized.  |
| 4  | GET `/knowledge/sessions/{project}` returns all sessions in reverse-chronological order                                      | ✓ VERIFIED  | data-service/app.py line 1075: `list_knowledge_sessions` endpoint reads KnowledgeSession nodes via `read_many` with `ORDER BY s.createdAt DESC`.  |
| 5  | NL prompt produces KnowledgeNote with title, tags, and content via Ollama JSON extraction                                    | ✓ VERIFIED  | knowledge-ingest.json: Build Insert Prompt → Ollama Generate (format:json) → Parse LLM JSON (with fallback) → Build Cypher (MERGE KnowledgeNote + KnowledgeTag + TAGGED_WITH). |
| 6  | Malformed LLM JSON output is gracefully recovered — a note is always created                                                 | ✓ VERIFIED  | Parse LLM JSON node contains full try/catch with fallback: title = first 60 chars of prompt_text, content = prompt_text, tags = ['untagged'].      |
| 7  | Knowledge query uses deterministic full-text search Cypher, not LLM-generated Cypher                                        | ✓ VERIFIED  | knowledge-query.json: Build Full-Text Cypher node contains hardcoded `CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)` Cypher.  |
| 8  | The full Phase 3 integration test suite passes end-to-end                                                                    | ? UNCERTAIN | test/test_phase03_knowledge_llm.py exists with all 5 test functions and correct syntax. End-to-end execution requires running stack + human verification. |

**Score:** 6/8 truths verified (2 PARTIAL due to ROADMAP path mismatch; 1 UNCERTAIN pending human)

### Required Artifacts

| Artifact                                   | Expected                                                                          | Status      | Details                                                                                       |
|--------------------------------------------|-----------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------|
| `n8n/workflows/knowledge-ingest.json`      | n8n workflow: webhook → Ollama JSON extraction → Neo4j MERGE → session → result   | ✓ VERIFIED  | 11 nodes, valid JSON, name="Knowledge Ingest", active=true                                    |
| `data-service/app.py`                      | GET /knowledge/sessions/{project} endpoint                                        | ✓ VERIFIED  | `list_knowledge_sessions` at line 1075, reads KnowledgeSession nodes, returns correct shape   |
| `test/test_phase03_knowledge_llm.py`       | Integration test scaffold for all Phase 3 scenarios                               | ✓ VERIFIED  | 5 test functions (sc1–sc5), valid Python syntax, correct workflow keys, __main__ block        |
| `n8n/workflows/knowledge-query.json`       | n8n workflow: webhook → full-text search → Ollama answer → session → result       | ✓ VERIFIED  | 11 nodes, valid JSON, name="Knowledge Query", active=true                                     |

### Key Link Verification

| From                               | To                                        | Via                                                  | Status      | Details                                                                                    |
|------------------------------------|-------------------------------------------|------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------|
| knowledge-ingest.json              | neo4j:7474/db/neo4j/tx/commit             | HTTP POST with parameterized Cypher                  | ✓ WIRED     | Execute Neo4j Cypher node: POST to `http://neo4j:7474/db/neo4j/tx/commit`, basicAuth confirmed |
| knowledge-ingest.json              | data-service:8000/execution-result        | HTTP POST, workflow key "knowledge-ingest"           | ✓ WIRED     | Post Execution Result node: workflow="knowledge-ingest" (hyphen per D-08)                  |
| data-service/app.py                | Neo4j KnowledgeSession nodes              | read_many Cypher with $project and $graph            | ✓ WIRED     | `MATCH (s:KnowledgeSession {project: $project, graph: $graph})` parameterized query        |
| knowledge-query.json               | neo4j full-text index knowledge_note_search | Deterministic Cypher in Build Full-Text Cypher node  | ✓ WIRED     | `CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)` in function node code |
| knowledge-query.json               | ollama:11434/api/generate                 | HTTP POST with top-5 results as answer context       | ✓ WIRED     | Ollama Generate Answer node calls `http://ollama:11434/api/generate`, no format:json (free text) |
| knowledge-query.json               | data-service:8000/execution-result        | HTTP POST, workflow key "knowledge-query"            | ✓ WIRED     | Post Execution Result node: workflow="knowledge-query", payload has `cypher` key (not cypherUsed) |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable        | Source                                    | Produces Real Data | Status       |
|-----------------------------------|----------------------|-------------------------------------------|--------------------|--------------|
| knowledge-ingest.json             | noteId, title, tags  | Ollama JSON extraction → Parse LLM JSON   | Yes (+ fallback)   | ✓ FLOWING    |
| knowledge-ingest.json             | KnowledgeNote node   | Build Cypher → Execute Neo4j Cypher       | Yes (parameterized MERGE) | ✓ FLOWING |
| knowledge-ingest.json             | KnowledgeSession node| Write KnowledgeSession → Neo4j MERGE      | Yes (inline expression, parameterized) | ✓ FLOWING |
| knowledge-query.json              | answer               | Neo4j FTS results → Build Answer Prompt → Ollama | Yes (real search) | ✓ FLOWING |
| knowledge-query.json              | cypher               | Hardcoded in Build Full-Text Cypher (saved as cypherUsed, exposed as cypher in payload) | Yes | ✓ FLOWING |
| data-service/app.py sessions ep   | sessions rows        | read_many → Neo4j KnowledgeSession MATCH  | Yes (live DB query) | ✓ FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED for live endpoints — requires running Docker stack (Ollama + Neo4j + n8n). Routed to human verification.

| Behavior                          | Command                                                               | Result  | Status  |
|-----------------------------------|-----------------------------------------------------------------------|---------|---------|
| knowledge-ingest.json valid JSON  | `python -c "import json; json.load(open('n8n/workflows/knowledge-ingest.json'))"` | Exit 0  | ✓ PASS  |
| knowledge-query.json valid JSON   | `python -c "import json; json.load(open('n8n/workflows/knowledge-query.json'))"`  | Exit 0  | ✓ PASS  |
| test scaffold syntax valid        | `python -c "import ast; ast.parse(open('test/test_phase03_knowledge_llm.py').read())"` | syntax ok | ✓ PASS |
| 11 nodes in each workflow         | Python node count check                                               | 11 each | ✓ PASS  |
| sessions endpoint code present    | grep for `list_knowledge_sessions` in app.py                          | Found at line 1075 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan   | Description                                                                  | Status         | Evidence                                                                                    |
|-------------|---------------|------------------------------------------------------------------------------|----------------|---------------------------------------------------------------------------------------------|
| INSK-01     | 03-01-PLAN.md | User can insert knowledge via NL prompt — LLM extracts title, tags, content  | ✓ SATISFIED    | knowledge-ingest.json implements NL→Ollama JSON→KnowledgeNote MERGE                        |
| INSK-04     | 03-01-PLAN.md | Each insert creates KnowledgeSession node with prompt, result, timestamp     | ✓ SATISFIED    | Write KnowledgeSession node in knowledge-ingest.json with mode='insert', parameterized MERGE |
| QRYK-01     | 03-02-PLAN.md | NL question returns NL answer drawn from knowledge graph via full-text search | ✓ SATISFIED    | knowledge-query.json: FTS → Ollama answer synthesis path fully wired                        |
| QRYK-02     | 03-02-PLAN.md | Cypher query used for search is displayed in result                          | ✓ SATISFIED    | `cypherUsed` captured in Build Full-Text Cypher, exposed as `cypher` in execution-result payload |
| QRYK-03     | 03-02-PLAN.md | Each query creates KnowledgeSession node                                     | ✓ SATISFIED    | Write KnowledgeSession node in knowledge-query.json with mode='query'                       |
| INFR-02     | 03-01-PLAN.md, 03-02-PLAN.md | Two new n8n workflows for knowledge-ingest and knowledge-query | ✓ SATISFIED    | knowledge-ingest.json and knowledge-query.json both exist as importable n8n workflows       |
| HSTY-01     | 03-01-PLAN.md | All knowledge interactions saved with prompt, result, date, mode             | ✓ SATISFIED    | Both workflows write KnowledgeSession with all 5 required fields; GET /knowledge/sessions/{project} endpoint live |

**Orphaned requirements check:** No requirements mapped to Phase 3 in REQUIREMENTS.md traceability table beyond the 7 listed above.

### Anti-Patterns Found

| File                                | Line/Location           | Pattern                                                    | Severity    | Impact                                                       |
|-------------------------------------|-------------------------|------------------------------------------------------------|-------------|--------------------------------------------------------------|
| test/test_phase03_knowledge_llm.py  | cleanup() function      | `pass` block for KnowledgeSession cleanup — sessions NOT deleted after test run | Info | Test sessions accumulate in Neo4j on repeated runs; does not affect correctness but inflates session counts |
| n8n/workflows/knowledge-query.json  | Write KnowledgeSession  | `$items('Build Full-Text Cypher')[0].json` cross-node reference inside inline expression | Warning | If node name changes, the reference breaks silently in n8n — no compile-time check |

No blockers found. No TODO/FIXME/placeholder comments. No empty implementations. All handlers have real logic.

### Human Verification Required

#### 1. Import and Activate n8n Workflows

**Test:** Open n8n at http://localhost:5678, import `n8n/workflows/knowledge-ingest.json`, toggle active. Import `n8n/workflows/knowledge-query.json`, toggle active.
**Expected:** Both workflows appear in n8n workflow list as active with green indicator. No import errors.
**Why human:** n8n workflow import requires browser UI — no CLI import command available in this stack version.

#### 2. End-to-End Integration Test Suite

**Test:** With both workflows active, run: `python test/test_phase03_knowledge_llm.py`
**Expected:** Output shows all 5 tests PASS (SC-4, SC-1, SC-3, SC-2, SC-5), script exits with code 0.
**Why human:** Integration test requires running Ollama + Neo4j + n8n + data-service. Full LLM inference through Ollama cannot be verified without the live Docker stack.

#### 3. Live Ingest Spot-Check

**Test:** POST to `http://localhost:8080/n8n/webhook/dg/knowledge-ingest` with body `{"prompt_text": "Minimum setback distance from property boundary must be at least 5 meters for buildings over 20m tall", "project_name": "manual-test"}`. Wait 30-60 seconds. Then: `curl http://localhost:8080/data-service/execution-result/latest/knowledge-ingest`
**Expected:** Ack returns `{"status": "accepted"}` immediately. After polling, execution-result payload contains a sensible title (mentioning setback or boundary) and at least one meaningful tag (not just 'untagged').
**Why human:** Verifies D-02 (LLM always extracts meaningful data) and T-3-01/T-3-02 security mitigations in a live run.

#### 4. Live Query Spot-Check

**Test:** (Requires ingest spot-check above to have run.) POST to `http://localhost:8080/n8n/webhook/dg/knowledge-query` with body `{"prompt_text": "What is the setback distance requirement?", "project_name": "manual-test"}`. Wait 30-60 seconds. Then: `curl http://localhost:8080/data-service/execution-result/latest/knowledge-query`
**Expected:** Payload contains `answer` mentioning "5 meters" and `cypher` containing `knowledge_note_search`.
**Why human:** Verifies QRYK-01 (answer drawn from real notes) and QRYK-02 (deterministic cypher exposed) in a live run with real Ollama inference.

### Gaps Summary

**Two PARTIAL gaps from ROADMAP path mismatch (SC-1 and SC-2):**

ROADMAP.md Phase 3 success criteria specify `POST /knowledge/ingest/prompt` and `POST /knowledge/query` as the entry-point endpoints. Neither path exists in `data-service/app.py`. The actual implementation exposes the same functional capability through n8n webhook paths (`/n8n/webhook/dg/knowledge-ingest` and `/n8n/webhook/dg/knowledge-query`) per CONTEXT.md decision D-09. The test scaffold (`test_phase03_knowledge_llm.py`) correctly targets the n8n webhook paths.

This is a ROADMAP documentation drift rather than a functional gap — the capability exists. Resolution options:
1. Update ROADMAP.md SC-1 and SC-2 to reflect the actual n8n webhook paths (lowest cost)
2. Add thin proxy endpoints `/knowledge/ingest/prompt` and `/knowledge/query` to data-service that forward to the n8n webhooks (higher cost, changes public API surface)

The choice between these options determines whether this is a 10-minute ROADMAP edit or a new implementation task. The `/gsd-plan-phase --gaps` structured output above captures this for the planner.

---

_Verified: 2026-04-06_
_Verifier: Claude (gsd-verifier)_
