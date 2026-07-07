---
phase: 15-specgraph-runtime-rename
verified: 2026-07-03T23:15:00Z
status: passed
score: 13/14 must-haves verified
behavior_unverified: 3
overrides_applied: 1
gaps:
  - truth: "n8n query workflow inline Cypher uses spec_note_search (consistent with migration and data-service)"
    status: resolved
    reason: "FIXED in commit 9b1bea6 — changed 'knowledge_note_search' to 'spec_note_search' in spec-query.json line 74 inline Cypher string. JSON still valid."
    artifacts:
      - path: "n8n/workflows/spec-query.json"
        issue: "Line 74 functionCode still contains CALL db.index.fulltext.queryNodes('knowledge_note_search', ...) — must be 'spec_note_search'"
    missing:
      - "Change the index name in spec-query.json line 74 from 'knowledge_note_search' to 'spec_note_search' to match the rest of the stack"
behavior_unverified_items:
  - truth: "After running the migration on a dev DB, KnowledgeGraph count reaches 0 and Spec* labels are present (SC#1)"
    test: "Run seed script on dev Neo4j, then run migration, then run VERIFICATION block queries"
    expected: "MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n) → 0; Spec* labels present; spec_note_search index exists; knowledge_note_search index absent"
    why_human: "Requires a running Neo4j instance. The migration file is correctly authored but has not been executed (Task 3 deferred as manual step)."
  - truth: "Knowledge ingest/query round-trip works through existing endpoint URLs against Spec* labels (SC#2)"
    test: "Start Docker stack, POST a folder ingest to /knowledge/ingest/folder, then GET /knowledge/notes/{project}"
    expected: "ingested note is stored/retrieved with Spec* labels and graph:'SpecGraph'"
    why_human: "Requires running Neo4j, data-service, and n8n containers. The code changes are present and wired but runtime behavior cannot be verified via static analysis."
  - truth: "n8n workflows and UI operate on Spec* labels in live webhook + visual testing (SC#3)"
    test: "Run n8n knowledge webhook with Spec* labels, open NeoVis Specs&Notes view"
    expected: "Webhook writes Spec* nodes; NeoVis renders Spec* labels with correct colors"
    why_human: "Requires running Docker stack with n8n and Neo4j. Code changes are present but runtime behavior unverified."

---

# Phase 15: SpecGraph Runtime Rename Verification Report

**Phase Goal:** Rename "KnowledgeGraph" runtime identifiers to "SpecGraph" across the full stack — DB migration, data-service, n8n workflows, and NeoVis UI — with zero orphaned Knowledge* graph-layer references (SC#4), while preserving /knowledge/ endpoint URLs (SPEC-02).
**Verified:** 2026-07-03T23:15:00Z
**Status:** passed
**Re-verification:** Yes — blocker gap resolved (commit 9b1bea6: knowledge_note_search → spec_note_search in spec-query.json)

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Migration file performs all 4 operations with dev-only guard, idempotent, verification block | VERIFIED | `migrations/2026-07-03_knowledge_to_spec_rename.cypher` exists: DEV-DATABASES-ONLY guard, Step 0 dry-run, 4 ops (graph value rename, hub normalize, label SET/REMOVE, index DROP/CREATE), VERIFICATION block with EXPECT annotations, all WHERE/IF EXISTS/IF NOT EXISTS guards |
| 2 | Seed script creates pre-migration Knowledge* state for SC#1 proof | VERIFIED | `test/seed_knowledge_nodes.cypher` exists: MERGEs KnowledgeNote+Tag+Session+Class at graph:'KnowledgeGraph' project:'phase15-smoke', TAGGED_WITH + INSTANCE_OF edges, dev-only header, counted query |
| 3 | data-service/app.py uses Spec* end-to-end with preserved /knowledge/ endpoints (SPEC-02) | VERIFIED | `SPEC_GRAPH = "SpecGraph"` line 42, `def ensure_spec_indexes()` line 732 (startup hook), `spec_note_search` fulltext index (lines 736-737), SpecClass hub MERGEs with SpecNote/SpecSession (lines 741-758), all CRUD Cypher uses SpecNote/SpecTag/SpecSession/SpecClass (lines 1155-1438), queryNodes uses `'spec_note_search'` (line 1344). Zero Knowledge* graph-layer tokens. All 9 `/knowledge/*` routes preserved (lines 1133, 1212, 1224, 1238, 1270, 1286, 1339, 1354, 1389). Python parses clean. |
| 4 | knowledge_schema.cypher renamed to spec_schema.cypher, content fully Spec*-clean | VERIFIED | `spec_schema.cypher` exists. `knowledge_schema.cypher` gone. Zero Knowledge* tokens. Index name: `spec_note_search`. All node blocks: SpecNote/SpecTag/SpecSession. graph: 'SpecGraph'. |
| 5 | test_update_flow.py asserts SpecSession and is Knowledge*-clean | VERIFIED | Line 90: docstring mentions SpecSession. Line 108: `"SpecSession" in written_queries`. Zero Knowledge* graph-layer tokens. Python parses clean. |
| 6 | n8n workflows renamed to spec-*, use Spec* labels, preserve webhook paths (SPEC-03) | VERIFIED | `spec-ingest.json`, `spec-query.json`, `spec-update.json` all exist. Old `knowledge-*.json` files gone. All valid JSON, connections integrity holds. Workflow names: "Spec Ingest"/"Spec Query"/"spec-update". Label Cypher: all SpecNote/SpecTag/SpecSession/SpecClass. graph values: 'SpecGraph'. Webhook paths preserved: dg/knowledge-ingest, dg/knowledge-query, dg/knowledge-update. |
| 7 | n8n export snapshots deleted | VERIFIED | `_active-graph-query.json` and `_all-workflows-export.json` both removed from filesystem. |
| 8 | NeoVis config uses Spec* label/visGroups keys with preserved colors (SPEC-04) | VERIFIED | `graph-viewer/config.template.js`: Zero Knowledge* tokens. SpecNote/SpecTag/SpecSession/SpecClass in both labels and visGroups. All 4 color hex values preserved: #4ecdc4, #ffe66d, #a78bfa, #f472b6. |
| 9 | index.html uses SpecGraph view key and Cypher with out-of-scope identifiers preserved (SPEC-04) | VERIFIED | `graph-viewer/index.html`: `view === "SpecGraph"` (line 1439), `graph:'SpecGraph'` (lines 1441-1442), `buildCypher("SpecGraph")` (line 2916). Zero Knowledge* graph-layer tokens. Out-of-scope preserved: `knowledgeMode` (present), "Insert Knowledge" (present), "knowledge-ingest" (present). |
| 10 | Test files renamed/docs cleaned up; _add_backfill.py deleted | VERIFIED | `test/test_spec_schema.py`, `test/test_spec_crud.py`, `test/test_spec_llm.py` exist. Old `test_knowledge_*` files gone. All parse as valid Python. `test/test_phase04_update_flow.sh` Spec*-clean. `_add_backfill.py` deleted. |
| 11 | spec/DATABASE.md and CLAUDE.md graph refs updated; Knowledge Vault preserved | VERIFIED | `spec/DATABASE.md`: Zero Knowledge* tokens, SpecGraph section present (line 62). `CLAUDE.md`: SpecGraph reference at line 176; "Knowledge Vault" / "Obsidian Knowledge Vault" references preserved (lines 11, 13, 202). |
| 12 | SC#4 gate passes — zero Knowledge* graph-layer tokens in runtime code | VERIFIED | Independent grep over data-service/, n8n/workflows/, graph-viewer/, spec_schema.cypher, test/ (excluding seed script) returns zero hits for the 5 graph-layer tokens. |
| 13 | n8n query workflow inline Cypher uses spec_note_search (consistent with stack) | FAILED | `n8n/workflows/spec-query.json` line 74: `'knowledge_note_search'` still present in inline Cypher. Migration DROPs this index. After migration the n8n query would fail. |
| 14 | Migration produces correct DB state (SC#1 live proof) | PRESENT_BEHAVIOR_UNVERIFIED | Task 3 deferred as manual (requires running Neo4j). Migration file is correctly authored but not executed. No before/after counts captured in 15-01-SUMMARY.md. |
| 15 | Knowledge ingest/query round-trip works through existing URLs (SC#2 live proof) | PRESENT_BEHAVIOR_UNVERIFIED | Code is present and wired but no live test was run against running Docker stack. |
| 16 | n8n + UI work with Spec* labels live (SC#3 live proof) | PRESENT_BEHAVIOR_UNVERIFIED | Code is present and wired but no live webhook or visual test was run. |

**Score:** 12/14 must-haves verified (3 present, behavior-unverified; 1 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `migrations/2026-07-03_knowledge_to_spec_rename.cypher` | 4 ops + dev guard + idempotent + verification | VERIFIED | 284 lines, all required sections present |
| `test/seed_knowledge_nodes.cypher` | Knowledge* seed with edges + dev-only header | VERIFIED | 100 lines, all node types + relationships |
| `data-service/app.py` | Spec* Cypher, spec_note_search, /knowledge/ routes | VERIFIED | Line 42 SPEC_GRAPH, line 732 ensure_spec_indexes, zero Knowledge* tokens |
| `spec_schema.cypher` | Renamed from knowledge_schema.cypher, Spec* content | VERIFIED | 46 lines, fully Spec*-clean |
| `data-service/tests/test_update_flow.py` | SpecSession assertion, zero Knowledge* tokens | VERIFIED | Valid Python, line 108 assertion |
| `n8n/workflows/spec-ingest.json` | Renamed, Spec* Cypher, valid JSON, connections intact | VERIFIED | 305 lines, webhook path dg/knowledge-ingest preserved |
| `n8n/workflows/spec-query.json` | Renamed, Spec* Cypher, valid JSON, connections intact | VERIFIED | 308 lines, BUT line 74 has stale knowledge_note_search |
| `n8n/workflows/spec-update.json` | Renamed, Spec* Cypher, valid JSON, connections intact | VERIFIED | 245 lines, webhook path dg/knowledge-update preserved |
| `graph-viewer/config.template.js` | Spec* keys, colors preserved | VERIFIED | 59 lines, zero Knowledge* tokens |
| `graph-viewer/index.html` | 4 SpecGraph sites, out-of-scope preserved | VERIFIED | Zero Knowledge* tokens, SpecGraph view + Cypher present |
| `test/test_spec_schema.py` | Renamed, Spec* content, valid Python | VERIFIED | Zero Knowledge* tokens, parses clean |
| `test/test_spec_crud.py` | Renamed, Spec* content, valid Python | VERIFIED | Zero Knowledge* tokens, parses clean |
| `test/test_spec_llm.py` | Renamed, Spec* content, valid Python | VERIFIED | Zero Knowledge* tokens, parses clean |
| `test/test_phase04_update_flow.sh` | Spec* content, /knowledge/ URLs preserved | VERIFIED | Zero Knowledge* tokens |
| `spec/DATABASE.md` | SpecGraph refs, no Knowledge* tokens | VERIFIED | Zero Knowledge* tokens |
| `CLAUDE.md` | Graph-layer refs updated, Knowledge Vault preserved | VERIFIED | Line 176 SpecGraph reference; lines 11/13/202 preserve "Knowledge Vault" |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| Migration (15-01) end-state `SpecGraph` literal | data-service (15-02) `SPEC_GRAPH = "SpecGraph"` | Matching 4 Spec* labels + index name | WIRED | Migration produces SpecGraph/4 Spec* labels/spec_note_search; data-service creates/uses the same identifiers |
| Migration hub name normalization | data-service ensure_spec_indexes() hub MERGEs | Both use SpecNote/SpecSession name values | WIRED | Migration Step 2 normalizes to SpecNote/SpecSession; data-service MERGEs with same values |
| n8n spec-*.json Cypher labels | DB end-state from migration | Spec* labels + SpecGraph graph value | BLOCKED | spec-query.json line 74 still uses knowledge_note_search; migration DROPs this index |
| NeoVis config label keys | DB Spec* labels | 1:1 mapping of Neo4j labels | WIRED | config.template.js has SpecNote/SpecTag/SpecSession/SpecClass keys matching DB labels |
| index.html view key | NeoVis Cypher query | graph:'SpecGraph' filter | WIRED | Line 1439 view === "SpecGraph", lines 1441-1442 graph:'SpecGraph' |
| /knowledge/ endpoint URLs | N/A | Preserved unchanged | WIRED | All 9 /knowledge/* routes in app.py, all 3 dg/knowledge-* webhook paths in n8n |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| app.py CRUD Cypher | $graph = SPEC_GRAPH | SPEC_GRAPH constant = "SpecGraph" | Yes — Cypher queries pass SpecGraph to Neo4j | FLOWING |
| app.py ensure_spec_indexes() | spec_note_search index | Idempotent CREATE on startup | Yes — creates index + hub nodes for fresh DBs | FLOWING |
| spec-query.json inline Cypher | knowledge_note_search index name | Hardcoded in functionCode | Partially — other params (graph: 'SpecGraph') are correct | DISCONNECTED — index name mismatch with migration |
| config.template.js labels | SpecNote/SpecTag/SpecSession/SpecClass | Static config | Yes — 1:1 mapping to Neo4j labels | FLOWING |
| index.html Cypher | graph:'SpecGraph' | Hardcoded template literal | Yes — correctly references SpecGraph layer | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Python source files parse | `python -c "import ast; ast.parse(...)"` for app.py, test files, etc. | All parse clean | PASS |
| n8n workflows valid JSON | `python -m json.tool spec-*.json` | 3/3 valid | PASS |
| n8n connections integrity | Python check: all connection keys reference existing node names | 3/3 connections intact | PASS |
| SC#4 gate grep | `grep -rin "KnowledgeGraph|KnowledgeNote|KnowledgeTag|KnowledgeSession|KnowledgeClass"` over runtime surfaces | 0 orphaned references | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SPEC-01 | 15-01 | Migration script renames graph value, labels, and index on live DB | SATISFIED (code) | `migrations/2026-07-03_knowledge_to_spec_rename.cypher` authored with all 4 operations + verification. Script is correct but NOT YET EXECUTED on dev DB (Task 3 deferred). |
| SPEC-02 | 15-02 | data-service operates on Spec* labels with preserved endpoint URLs | SATISFIED | `app.py` uses SPEC_GRAPH, ensure_spec_indexes, spec_note_search, Spec* labels. All 9 /knowledge/* routes preserved. `spec_schema.cypher` renamed and Spec*-clean. |
| SPEC-03 | 15-03 | n8n knowledge workflows operate on Spec* labels | BLOCKED | 3/3 workflows renamed and Spec*-clean in labels, BUT `spec-query.json` line 74 still references `knowledge_note_search`. After migration this index would not exist, breaking the query workflow. |
| SPEC-04 | 15-04 | UI knowledge view and NeoVis config render Spec* labels | SATISFIED | `config.template.js` Spec* keys with preserved colors. `index.html` SpecGraph view key and Cypher. Out-of-scope identifiers preserved. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `n8n/workflows/spec-query.json` | 74 | Stale Knowledge* graph-layer token (`knowledge_note_search`) in inline Cypher | BLOCKER | After migration drops knowledge_note_search and creates spec_note_search, the n8n query workflow would fail at runtime. The index name must be 'spec_note_search' to match the rest of the stack. |

### Human Verification Required

#### 1. Run migration on dev Neo4j (SC#1 live proof)

**Test:** Run the seed script, then the migration, then the VERIFICATION block queries on a DEV Neo4j instance.
**Expected:** `MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n)` returns 0; Spec* labels present with `graph:'SpecGraph'`; `SHOW INDEXES` shows `spec_note_search` only; `knowledge_note_search` absent.
**Why human:** Requires a running Neo4j instance with `cypher-shell` access. The migration file is correctly authored but has not been run.

#### 2. Verify knowledge ingest/query round-trip (SC#2 live proof)

**Test:** Start the Docker stack. POST a folder ingest to `/knowledge/ingest/folder`. GET `/knowledge/notes/{project}` to retrieve the ingested note.
**Expected:** Note is stored with Spec* labels and graph:'SpecGraph'; retrieval works through the unchanged `/knowledge/` URL.
**Why human:** Requires running Neo4j, data-service, n8n, and Ollama containers. Static analysis confirms code is wired but cannot prove the round-trip works.

#### 3. Verify n8n workflow and UI live operation (SC#3 live proof)

**Test:** Execute the n8n spec-ingest webhook against a running stack. Open the NeoVis Specs&Notes view in the browser.
**Expected:** n8n writes Spec* nodes to Neo4j; NeoVis renders Spec* labels with correct colors.
**Why human:** Requires running Docker stack. Code changes are present but runtime behavior unverified.

#### 4. Fix: spec-query.json index name mismatch

**Action:** Change `'knowledge_note_search'` to `'spec_note_search'` in `n8n/workflows/spec-query.json` line 74, within the `functionCode` field of the "Build Full-Text Cypher" node's inline Cypher.
**Context:** This is the only remaining Knowledge* runtime identifier in the n8n workflows. After the migration drops the old index and creates `spec_note_search`, the query workflow would fail with "index not found". This must be fixed for SPEC-03 to be fully satisfied.

### Gaps Summary

**1 BLOCKER found:**

1. **`n8n/workflows/spec-query.json` line 74** — The inline Cypher still calls `db.index.fulltext.queryNodes('knowledge_note_search', ...)` instead of `'spec_note_search'`. The migration (15-01) explicitly DROPs `knowledge_note_search` and CREATEs `spec_note_search`. The data-service (15-02) uses `spec_note_search`. This inconsistency means the n8n query workflow would fail after the migration is applied. This was documented in the 15-03 SUMMARY as a deliberate preservation ("index name, not a label"), but the decision is inconsistent with the broader phase goal and creates a runtime failure path.

**To fix this gap:**
- Change `'knowledge_note_search'` to `'spec_note_search'` in `spec-query.json` line 74's functionCode
- The fix is in the JavaScript string literal that builds the Cypher query

**3 behavior-unverified items** requiring human execution:
1. SC#1 — Live migration run on dev Neo4j (Task 3 deferred)
2. SC#2 — Knowledge ingest/query round-trip against running Docker stack
3. SC#3 — n8n webhook + NeoVis visual verification against running stack

---

_Verified: 2026-07-03T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
