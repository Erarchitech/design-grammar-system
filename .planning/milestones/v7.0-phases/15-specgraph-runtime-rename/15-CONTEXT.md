# Phase 15: SpecGraph Runtime Rename - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Rename `KnowledgeGraph`→`SpecGraph` (graph property value) and `Knowledge*`→`Spec*` (node labels) across all runtime surfaces — DB migration, data-service, n8n knowledge workflows, UI/NeoVis. The goal is zero Knowledge* references remaining in runtime code, closing the pre-existing ontology↔runtime drift.

**In scope (SPEC-01..04):** DB migration with fulltext index recreation, `data-service/app.py` knowledge endpoints, 3 n8n knowledge workflows, `graph-viewer/config.template.js` + `index.html`, `spec_schema.cypher` (renamed from `knowledge_schema.cypher`), test files, and file renames.

**This is a propagation/rename phase, not a design phase.** The names are locked by Phase 13 (Ontology V7). Phase 14 established the propagation pattern (dated migration files, dry-run + dev-guard, before/after counts).

**Already locked upstream (do NOT re-open):**
- Names: `SpecGraph`, `SpecNote`, `SpecTag`, `SpecSession`, `SpecClass` — Phase 13 Ontology V7
- Endpoint URLs stay as `/knowledge/*` — SPEC-02, UI compatibility
- DB keeps existing labels except Knowledge*→Spec* — PROJECT.md (no wider label migration)
- Migration follows `migrations/` dated-file pattern with dry-run + dev-only guard — Phase 14 precedent
- Phase 14 D-14 already renamed a `graph` property value (`ValidationGraph`→`ValidGraph`) — same operation type, same safety pattern

</domain>

<decisions>
## Implementation Decisions

### File Renames (Area 1)
- **D-01:** Rename all 8 files with "knowledge" in their name to "spec": `knowledge_schema.cypher` → `spec_schema.cypher`, `n8n/workflows/knowledge-ingest.json` → `spec-ingest.json`, `n8n/workflows/knowledge-query.json` → `spec-query.json`, `n8n/workflows/knowledge-update.json` → `spec-update.json`, `test/test_knowledge_schema.py` → `test/test_spec_schema.py`, `test/test_knowledge_crud.py` → `test/test_spec_crud.py`, `test/test_phase03_knowledge_llm.py` → `test/test_spec_llm.py` (dropping phase number — D-03), and any other files with "knowledge" in the name that contain Knowledge* references.
- **D-02:** n8n internal workflow `name` field and node display names also switch to Spec* (e.g. "Write KnowledgeSession" → "Write SpecSession"). Consistent — no stale Knowledge* visible in the n8n UI or code.
- **D-03:** Drop the phase number from `test_phase03_knowledge_llm.py` → `test_spec_llm.py`. The phase number is misleading (test is updated in Phase 15, not Phase 03). Historical info lives in git blame.
- **D-04:** Delete `_add_backfill.py` — a one-off backfill script at the repo root with hardcoded Knowledge* Cypher. It was a historical utility; the proper migration script (SPEC-01) handles the rename correctly. If the backfill already ran, the file is dead code; if it hasn't, it would now contain wrong labels.

### n8n Export Handling (Area 2)
- **D-05:** Delete `n8n/workflows/_active-graph-query.json` and `n8n/workflows/_all-workflows-export.json`. These are generated export/backup files, not source-of-truth. They contain Knowledge* references that would become stale after Phase 15. The canonical files are `spec-ingest.json`, `spec-query.json`, `spec-update.json`, `rules-to-metagraph.json`, and `graph-query-mcp.json`.

### Migration Scope and Safety (Area 3)
- **D-06:** Single dated `.cypher` file in `migrations/` (e.g. `migrations/2026-07-03_knowledge_to_spec_rename.cypher`) — follows the Phase 14 pattern exactly (`migrations/2026-06-23_var_project_merge_key.cypher`). Handles all 4 operations: (1) rename `graph` property value, (2) rename node labels via manual SET/REMOVE, (3) drop `knowledge_note_search` fulltext index, (4) create `spec_note_search` fulltext index.
- **D-07:** Seed + migrate + verify — follows Phase 14 pattern. Create test Knowledge* nodes on the dev DB, run migration, verify zero nodes with `graph:'KnowledgeGraph'` remain and all Spec* labels exist. Before/after node counts captured as live proof of SC#1.
- **D-08:** Manual `SET n:SpecNote REMOVE n:KnowledgeNote` for label rename — no APOC dependency. Only 4 labels to rename (KnowledgeNote/Tag/Session/Class). Simple, transparent, debuggable, works on any Neo4j 5 instance.
- **D-09:** Migration handles the full index transition: `DROP INDEX knowledge_note_search IF EXISTS` + `CREATE FULLTEXT INDEX spec_note_search IF NOT EXISTS FOR (n:SpecNote) ON EACH [n.title, n.content]`. `app.py`'s `ensure_knowledge_indexes()` startup hook is updated to create `spec_note_search` (and drops the old index creation code). Both sides agree — the migration does the transition on existing DBs, `app.py` handles fresh DBs. `IF NOT EXISTS` / `IF EXISTS` makes both idempotent.

### UI Label and View Naming (Area 4)
- **D-10:** Keep the user-facing sidebar tab label "Specs&Notes" — it's already Spec*-aligned and users recognize it. No UI text change needed.
- **D-11:** Internal view key `"KnowledgeGraph"` → `"SpecGraph"` in `index.html` (`buildCypher` function + the call site at line ~2916). Cypher queries switch from `graph:'KnowledgeGraph'` → `graph:'SpecGraph'`. NeoVis labels and visGroups in `config.template.js` — 4 Knowledge* entries renamed to Spec* (`KnowledgeNote`→`SpecNote`, `KnowledgeTag`→`SpecTag`, `KnowledgeSession`→`SpecSession`, `KnowledgeClass`→`SpecClass`). Colors preserved — teal, yellow, purple, pink stay the same.

### Claude's Discretion
- Exact filename for the migration `.cypher` file (follow the `YYYY-MM-DD_descriptive_slug.cypher` convention from Phase 14).
- Whether to update `spec/DATABASE.md` and `CLAUDE.md` Graph Schema section in this phase or defer to Phase 20 (E2E-03 covers repo/AI doc updates). Recommend doing it now — the docs reference Knowledge* labels and would be stale/immediately wrong.
- Whether `data-service/tests/test_update_flow.py` (which asserts `"KnowledgeSession" in written_queries`) should be renamed. It's in `data-service/tests/`, not `test/` — different test suite but same rename obligation.
- Exact handling of `n8n/workflows/knowledge-update.json` — need to verify this is genuinely an active workflow (it's referenced in Obsidian session notes as an 8-node workflow). If it's active, rename + content-edit like the others. If it's deprecated, delete.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-13 locked contract (the source of every Spec* name)
- `ontology/port-iri-map-V7.md` — SpecGraph is a named graph layer; `dgs:` namespace. **MUST read.**
- `ontology/V7-INVESTIGATION.md` — conflict resolutions; final names for all layers.
- `.planning/milestones/v7.0-phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` — D-01..D-11 that flow into this phase (SpecGraph layer naming).

### Phase-14 propagation pattern (the HOW to propagate)
- `.planning/milestones/v7.0-phases/14-graph-schema-v4-propagation/14-CONTEXT.md` — D-14 (ValidGraph runtime-literal rename — same operation type: rename a `graph` property value across DB, app.py, C#, E2E tests). Also: D-08/D-09/D-10 (migration safety pattern: dry-run, dev-guard, before/after counts, seed+verify). **MUST read.**

### Artifacts to rename (the edit targets)
- `knowledge_schema.cypher` → `spec_schema.cypher` — canonical schema reference (D-01)
- `n8n/workflows/knowledge-ingest.json` → `spec-ingest.json` — knowledge ingest workflow (SPEC-03)
- `n8n/workflows/knowledge-query.json` → `spec-query.json` — knowledge query workflow (SPEC-03)
- `n8n/workflows/knowledge-update.json` → `spec-update.json` — knowledge update workflow (SPEC-03)
- `data-service/app.py` — `KNOWLEDGE_GRAPH` constant (line 42), `ensure_knowledge_indexes()` (line ~733), 20+ Cypher queries with Knowledge* labels (SPEC-02)
- `graph-viewer/config.template.js` — 4 labels + 4 visGroups (SPEC-04, D-11)
- `graph-viewer/index.html` — `buildCypher("KnowledgeGraph")` + view key + Cypher query (SPEC-04, D-11)
- `test/test_knowledge_schema.py` → `test/test_spec_schema.py` (D-01)
- `test/test_knowledge_crud.py` → `test/test_spec_crud.py` (D-01)
- `test/test_phase03_knowledge_llm.py` → `test/test_spec_llm.py` (D-01, D-03)
- `data-service/tests/test_update_flow.py` — `KnowledgeSession` assertion (line 108)
- `_add_backfill.py` → DELETE (D-04)
- `n8n/workflows/_active-graph-query.json` → DELETE (D-05)
- `n8n/workflows/_all-workflows-export.json` → DELETE (D-05)

### Migration pattern reference
- `migrations/2026-06-23_var_project_merge_key.cypher` — the dated `.cypher` file pattern to follow (D-06)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — SPEC-01..04
- `.planning/ROADMAP.md` — Phase 15 goal + 4 success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 14 D-14 migration pattern** — already renamed a `graph` property value (`ValidationGraph`→`ValidGraph`) across `data-service/app.py`, `DG/src/DG.Core/Services/ValidationRunsQueryService.cs`, `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs`, and 1169 live nodes. Same operation type, same safety pattern. The Phase 14 plan structure is directly reusable.
- **`migrations/` file convention** — one existing dated `.cypher` file (`2026-06-23_var_project_merge_key.cypher`); the SpecGraph migration follows the same convention (dated filename, self-contained Cypher, dry-run counts at top).
- **`app.py` constant pattern** — `KNOWLEDGE_GRAPH = "KnowledgeGraph"` (line 42) mirrors `VALIDATION_GRAPH = "ValidationGraph"` (line 41). Phase 14 D-14 already renamed the latter to `"ValidGraph"` — same rename operation.

### Established Patterns
- **Layer-tagging via `graph=` property** on every node (`OntoGraph`/`Metagraph`/`ValidGraph`/`SpecGraph`) — the KnowledgeGraph→SpecGraph rename operates on this property.
- **Neo4j keeps existing labels; ontology↔DB naming is documented, not enforced** (PROJECT.md) — but Knowledge*→Spec* IS the one label rename that IS in scope (the exception that proves the rule).
- **NeoVis labels/visGroups** in `config.template.js` — label keys match DB node labels exactly; visGroups keys match either labels (direct mapping) or kind values (for DesignState). Knowledge* nodes use direct label mapping — the rename is a straightforward key rename, no group-by logic to change.
- **n8n workflow structure** — each workflow JSON has a top-level `name` field, `nodes[]` with `name` fields, and inline Cypher strings. The rename touches all three consistently.

### Integration Points
- Phase 17 (GRAPH DECONSTRUCT) outputs a `SpecGraph` handle — the runtime rename makes this handle name match what the DB actually stores.
- `app.py`'s `ensure_knowledge_indexes()` startup hook — must be updated to create `spec_note_search` instead. Migration handles existing DBs; app.py handles fresh DBs.
- The UI sidebar "Specs&Notes" tab already uses user-facing Spec* naming — this phase makes the code match the UI.

</code_context>

<specifics>
## Specific Ideas

- **The rename is mechanical, not creative.** Every Knowledge* string literal becomes Spec* — no exceptions in runtime code. The only judgment calls are about which files to touch (D-01..D-05) and the migration approach (D-06..D-09).
- **Follow Phase 14's structure exactly.** The planner can reuse Phase 14's plan architecture: one plan for the migration script + seed/verify, one plan for data-service, one plan for n8n workflows, one plan for UI/NeoVis, one plan for tests + file renames + cleanup. The Phase 14 CONTEXT.md decisions (D-01..D-14) are the template.
- **SC#4 is the acceptance gate.** A final `grep -ri "KnowledgeGraph\|KnowledgeNote\|KnowledgeTag\|KnowledgeSession\|KnowledgeClass"` over runtime code (data-service, n8n workflows, graph-viewer) must return only migration-script and changelog references. Run this BEFORE committing each plan to catch misses early.

</specifics>

<deferred>
## Deferred Ideas

- **`spec/DATABASE.md` update** — The KnowledgeGraph section needs to become SpecGraph. This is technically E2E-03 (Phase 20) scope, but updating it now prevents docs from being wrong for Phases 16–19. Planner's call: do it here or flag for Phase 20.
- **`CLAUDE.md` Graph Schema section** — currently says "v3" and doesn't list SpecGraph as a layer. Same as above — Phase 20 scope but updating now prevents drift.
- **n8n workflow file `knowledge-update.json`** — referenced in Obsidian session notes as an 8-node workflow. The researcher should verify whether this is genuinely active (has a webhook route, is imported in n8n) or deprecated. If deprecated, delete instead of rename.
- No out-of-scope capabilities surfaced — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-specgraph-runtime-rename*
*Context gathered: 2026-07-03*
