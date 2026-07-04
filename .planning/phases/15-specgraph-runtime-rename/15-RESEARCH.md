---
phase: 15
slug: specgraph-runtime-rename
type: research
created: 2026-07-03
grounding: verified against live tree 2026-07-03
---

# Phase 15 — Research: SpecGraph Runtime Rename

> Grounding doc. Records the **actual current state** of every edit target (verified by
> grep/read on 2026-07-03), the scope boundaries that keep the rename from over-reaching,
> and the two execution landmines. Consumed by the planner + executor. This is a
> mechanical propagation phase — the *what* is locked in CONTEXT.md (D-01..D-11); this
> doc supplies the *precise where* so plans are grounded, not assumed.

---

## Current-State Map (verified counts)

Grep `KnowledgeGraph|KnowledgeNote|KnowledgeTag|KnowledgeSession|KnowledgeClass|KNOWLEDGE_GRAPH|ensure_knowledge_indexes|knowledge_note_search` over the runtime surfaces:

| File | Hits | Nature of edits | Plan |
|------|------|-----------------|------|
| `data-service/app.py` | 50 | `KNOWLEDGE_GRAPH` const (L42), `ensure_knowledge_indexes()` (L732) + body, ~40 CRUD Cypher label refs (L1155–1438) | 15-02 |
| `knowledge_schema.cypher` (repo root) | 14 | Canonical schema-reference doc: index name, 3 node blocks, graph-isolation notes | 15-02 |
| `n8n/workflows/knowledge-ingest.json` | 5 | Workflow `name`, "Write KnowledgeSession" node (+connections), inline Cypher | 15-03 |
| `n8n/workflows/knowledge-query.json` | 5 | Workflow `name`, "Write KnowledgeSession" node (+connections), inline Cypher | 15-03 |
| `n8n/workflows/knowledge-update.json` | 0 (labels) | File name + workflow `name` + node display names only — delegates writes to data-service | 15-03 |
| `graph-viewer/config.template.js` | 8 | 4 label keys (L27–30) + 4 visGroups (L54–57) | 15-04 |
| `graph-viewer/index.html` | 4 (in-scope) | `KnowledgeGraph` view key + Cypher: L1439, L1441, L1442, L2916 | 15-04 |
| `test/test_knowledge_schema.py` | 31 | file rename + content | 15-05 |
| `test/test_knowledge_crud.py` | 1 | file rename + content | 15-05 |
| `test/test_phase03_knowledge_llm.py` | 7 | file rename (drop phase#) + content | 15-05 |
| `test/test_phase04_update_flow.sh` | 3 | content edit (no rename — not a `knowledge_*` filename) | 15-05 |
| `data-service/tests/test_update_flow.py` | 2 | `KnowledgeSession` assertion (L108) | 15-02 |
| `_add_backfill.py` (repo root) | 9 | **DELETE** (D-04) | 15-05 |
| `n8n/workflows/_active-graph-query.json` | — | **DELETE** (D-05, confirmed present) | 15-03 |
| `n8n/workflows/_all-workflows-export.json` | — | **DELETE** (D-05, confirmed present) | 15-03 |

Docs (Claude's-discretion — recommend doing now to avoid immediate drift): `spec/DATABASE.md` (13), `CLAUDE.md` (1) → 15-05.

### app.py precise targets (verified line numbers)
- `L42  KNOWLEDGE_GRAPH = "KnowledgeGraph"` → `SPEC_GRAPH = "SpecGraph"`
- `L732 def ensure_knowledge_indexes():` → `def ensure_spec_indexes():` (+ update the startup call site — grep for the invocation)
- `L736 CREATE FULLTEXT INDEX knowledge_note_search … FOR (n:KnowledgeNote)` → `spec_note_search … (n:SpecNote)`
- `L741–758` hub-node MERGEs: `KnowledgeClass`/`KnowledgeNote`/`KnowledgeSession` → `Spec*`
- `L1155–1438` CRUD: `KnowledgeNote`/`KnowledgeTag`/`KnowledgeSession`/`KnowledgeClass` labels + `KNOWLEDGE_GRAPH` refs → `Spec*` / `SPEC_GRAPH`
- `L1344 queryNodes('knowledge_note_search', …)` → `'spec_note_search'`

---

## Scope Boundaries (what NOT to touch)

The rename is targeted at the graph-layer identifiers. Three categories are deliberately **out of scope** because they are URL-facing (SPEC-02 compatibility) or unrelated UI naming, and because SC#4's grep (`KnowledgeGraph|KnowledgeNote|KnowledgeTag|KnowledgeSession|KnowledgeClass`, case-insensitive) does **not** match them:

1. **UI notes-panel React state** in `index.html` — `knowledgeMode`, `setKnowledgeMode`, `knowledgePromptText`, `knowledgeResponseText`, `startKnowledgePolling*`, etc. (~80 lowercase `knowledge*` identifiers). These are the insert/query/update *notes-panel* state, not the graph layer. Only the 4 `KnowledgeGraph` view-key/Cypher lines change (D-11).
2. **User-facing button labels** — "Insert Knowledge", "Query Knowledge", "Update Knowledge", the "Specs&Notes" tab (D-10). No text change.
3. **URL-facing identifiers (preserve for UI/data-service compatibility, SPEC-02):**
   - app.py route paths `/knowledge/*` (lowercase — stay)
   - n8n webhook `path` fields `dg/knowledge-*` (stay — the UI + nginx proxy call these)
   - the UI's lowercase workflow polling keys `"knowledge-ingest"`, `"knowledge-query"` in index.html (stay)

**Rationale check:** SC#4 grep is `-i` (case-insensitive) but requires the letters `knowledgegraph`/`knowledgenote`/`knowledgetag`/`knowledgesession`/`knowledgeclass` to be adjacent. `/knowledge/notes`, `knowledgeMode`, `dg/knowledge-ingest`, and `"Insert Knowledge"` contain none of those substrings → they will not trip the gate. Verified by inspection.

---

## knowledge-update.json — active vs. deprecated (CONTEXT open question, RESOLVED)

`knowledge-update.json` is `"active": false` in its JSON, but it is a **legitimate source-of-truth workflow**, not a deprecated artifact:
- Has a webhook node (`path: dg/knowledge-update`, `webhookId: dg-knowledge-update`) and 8 nodes total.
- Wired to the UI update panel (index.html `submitUpdateFlow`/`resetUpdateState`, the `knowledge-update` polling key).
- Contains **zero** `Knowledge*` capital-label references (0 grep hits) — it delegates all Neo4j writes to data-service `/knowledge/update/*` endpoints, so there is no inline Cypher to rewrite.

**Decision:** rename + internal-name edit like the others (D-01/D-02), do **not** delete. `"active": false` is just its current n8n import state, not a signal it's dead. Its content needs only the file rename, `name: "knowledge-update"` → `"spec-update"`, and node display-name updates (if any node name contains a Knowledge* token) — plus **preserve** the webhook `path`.

---

## Execution Landmines

### L-1: n8n node renames must update `connections` in lockstep
In n8n workflow JSON, the `connections` object references nodes **by their `name` string**. `knowledge-ingest.json` / `knowledge-query.json` both have a node `"name": "Write KnowledgeSession"` (L168) that is *also* referenced in `connections` (L283 `"node": "Write KnowledgeSession"`, L290 `"Write KnowledgeSession": {…}`). Renaming the node definition to "Write SpecSession" **without** updating both `connections` references produces a workflow that imports but has a broken/orphaned edge. Every node-name change must be applied to the node definition AND all `connections` keys/values. Acceptance must assert the JSON still parses **and** no dangling connection name remains.

"Write KnowledgeSession" contains `KnowledgeSession` → it *is* caught by SC#4, so the rename is mandatory, not optional.

### L-2: `.claude/worktrees/` shadow copies pollute a naive repo-root grep
Three stale agent worktrees under `.claude/worktrees/agent-*/` contain full copies of `knowledge_schema.cypher`, the n8n workflows, and the test files. A naive `grep -ri … .` from repo root will report dozens of Knowledge* hits there. **The SC#4 acceptance grep must be scoped to the real runtime surfaces** — `data-service/ n8n/workflows/ graph-viewer/ spec_schema.cypher` (and the renamed `test/` files) — and must exclude `.claude/`, `.planning/`, `DG_OBSIDIAN/`, and `migrations/`. The migration script legitimately contains Knowledge* tokens (its MATCH/REMOVE clauses) and lives in `migrations/`, so scoping to runtime dirs excludes it automatically.

---

## Reusable Pattern: Phase 14 ValidGraph migration

`migrations/2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher` SECTION B is the exact template for SPEC-01 — it renames a `graph` property VALUE (`ValidationGraph`→`ValidGraph`) across ~1169 live nodes with:
- a header block (PURPOSE / EXECUTION METHOD / WARNING — DEV DATABASES ONLY),
- Step 0 DRY-RUN counts (`MATCH (n {graph:'…'}) RETURN labels(n), count(*)`),
- an idempotent `SET` (re-run = no-op via `WHERE` guard),
- read-only VERIFICATION queries with `-- EXPECT: 0` annotations.

The SpecGraph migration adds label renames (Phase 14 didn't rename labels — it only moved a property value), so SPEC-01 also needs the `SET n:SpecNote REMOVE n:KnowledgeNote` idiom (D-08, manual, no APOC) for the 4 labels, plus the fulltext index DROP+CREATE (D-09).

Phase 14 PLAN frontmatter shape (`must_haves.{truths,artifacts,key_links,prohibitions}`, `security`, tasks with `<read_first>`/`<action>`/`<verify><automated>`/`<acceptance_criteria>`) is the plan template.

---

## Validation Architecture

The phase is verified by **live database proof** (SC#1/SC#2/SC#3) plus a **static grep gate** (SC#4). No new unit-test framework is introduced; validation reuses the existing seed→migrate→verify Cypher pattern (Phase 14) and the repo's `test/` scripts.

### Validation dimensions
1. **Migration correctness (SC#1)** — seed test `Knowledge*` nodes on the dev DB, run the migration, assert `MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n)` = 0 and former nodes now carry `Spec*` labels + `graph:'SpecGraph'`. Before/after counts captured as live proof (self-contained in 15-01: a seed `.cypher` + the migration + verification queries).
2. **Index transition (SC#1)** — after migration, `SHOW INDEXES` lists `spec_note_search` and not `knowledge_note_search`; a fulltext query against `spec_note_search` returns seeded notes.
3. **Endpoint round-trip (SC#2)** — with data-service on Spec* labels, folder-ingest → note-list → note-retrieval works through the **unchanged** `/knowledge/*` URLs (manual/live check; the update-flow assertion in `data-service/tests/test_update_flow.py` becomes `SpecSession`).
4. **n8n + UI on Spec* (SC#3)** — live webhook test of `dg/knowledge-ingest` + `dg/knowledge-query` writes/reads Spec* nodes; NeoVis "Specs&Notes" view renders Spec* labels with preserved colors (manual/visual).
5. **Static acceptance gate (SC#4)** — `grep -ri "KnowledgeGraph\|KnowledgeNote\|KnowledgeTag\|KnowledgeSession\|KnowledgeClass"` over `data-service/ n8n/workflows/ graph-viewer/ spec_schema.cypher` returns nothing. This is the automated, deterministic gate every plan runs on its own files before completion, and 15-05 runs phase-wide as the last task.

### Sampling
- **Per plan:** run the SC#4-scoped grep over that plan's files before marking complete; assert edited JSON/Python still parses.
- **Phase end (15-05, wave 2):** phase-wide SC#4 grep = 0; migration seed→verify counts captured; live webhook + NeoVis visual check.

### Manual-only (documented, no automation)
- Live webhook round-trip (SC#2/SC#3) and NeoVis visual check require a running Docker stack + Neo4j; captured as manual verification steps, not CI assertions.

---

## Open items handed to the planner
- Migration filename: `migrations/2026-07-03_knowledge_to_spec_rename.cypher` (follows dated convention; date is planning date — executor may adjust to run date).
- Docs (`spec/DATABASE.md`, `CLAUDE.md`): **do now** in 15-05 (they reference Knowledge* and would be immediately wrong for Phases 16–19). Flagged E2E-03/Phase-20 in CONTEXT but the drift cost of deferring is real.
