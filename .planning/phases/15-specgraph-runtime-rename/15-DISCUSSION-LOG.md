# Phase 15: SpecGraph Runtime Rename - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 15-specgraph-runtime-rename
**Areas discussed:** File renames, n8n export handling, Migration scope and safety, UI label and view naming

---

## File Renames

### Q1: Should files with 'knowledge' in name be renamed?

| Option | Description | Selected |
|--------|-------------|----------|
| Rename all 8 (recommended) | `knowledge_schema.cypher` → `spec_schema.cypher`, all n8n workflows, all test files. Cleanest — no file with 'knowledge' in name still contains Spec* content. | ✓ |
| Rename source files only | Rename .cypher, .json, .py in n8n/ and root. Keep test filenames. | |
| Content-only, no renames | Edit all content to Spec* but keep filenames. Minimal diff but confusing. | |

**User's choice:** Rename all 8
**Notes:** Content rename is mandatory per SC#4. File renames prevent the confusion of opening `knowledge_schema.cypher` and finding only Spec* content.

### Q2: Should n8n internal names also switch to Spec*?

| Option | Description | Selected |
|--------|-------------|----------|
| Rename everything (recommended) | File names, workflow `name`, and all node display names → Spec* | ✓ |
| Rename files + content only | Internal names stay as-is for n8n editor familiarity | |
| Files + workflow name only | Workflow name changes, node names stay | |

**User's choice:** Rename everything
**Notes:** Consistent approach — no stale Knowledge* visible anywhere in the n8n UI or code.

### Q3: test_phase03_knowledge_llm.py — preserve phase number?

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve phase number | `test_phase03_spec_llm.py` — keeps historical traceability | |
| Drop phase number (recommended) | `test_spec_llm.py` — simpler, phase number is misleading | ✓ |
| Rename to match current phase | `test_phase15_spec_llm.py` — inconsistent convention | |

**User's choice:** Drop phase number
**Notes:** The phase number is misleading since the test is being updated in Phase 15. Git blame preserves history.

### Q4: _add_backfill.py — rename or handle differently?

| Option | Description | Selected |
|--------|-------------|----------|
| Rename to _spec_backfill.py | Keep it renamed but it's a historical one-off | |
| Delete it (recommended) | One-off backfill; the migration script replaces its purpose | ✓ |
| Leave as-is, content-only | Content to Spec* but confusing filename | |

**User's choice:** Delete it
**Notes:** If the backfill already ran, the file is dead code. If it hasn't, it would now contain wrong labels. The proper migration handles the rename.

---

## n8n Export Handling

### Q1: How to handle _active-graph-query.json and _all-workflows-export.json?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete both (recommended) | Generated exports, not source-of-truth. Will be stale after Phase 15. | ✓ |
| Edit both in-place | Replace Knowledge* → Spec* in exports too. Large files, mechanical edits. | |
| Leave both as-is | Don't touch. SC#4 would flag them — needs explicit exclusion. | |

**User's choice:** Delete both
**Notes:** These are generated snapshots. The canonical files are the source-of-truth. Phase 14 didn't edit them for the same reason.

---

## Migration Scope and Safety

### Q1: Single .cypher file or Python script?

| Option | Description | Selected |
|--------|-------------|----------|
| Single .cypher file (recommended) | Follows Phase 14 pattern. All 4 operations in one file with dry-run counts. | ✓ |
| Python migration script | More flexible but inconsistent with Phase 14 convention. | |
| Two files: .cypher + Python | Split data migration (Cypher) from index management (Python). | |

**User's choice:** Single .cypher file
**Notes:** Follows the `migrations/` dated-file convention from Phase 14. Dry-run counts at top via commented-out MATCH queries.

### Q2: Seed test data before migration?

| Option | Description | Selected |
|--------|-------------|----------|
| Seed + migrate + verify (recommended) | Create test nodes, run migration, before/after counts as proof | ✓ |
| Migration script only, no seed | Trust the Cypher is correct. Faster but no live proof. | |
| Conditional: seed if DB is empty | Check first, seed only if needed. | |

**User's choice:** Seed + migrate + verify
**Notes:** Follows Phase 14 pattern exactly. The seed script is part of the plan deliverable.

### Q3: APOC or manual SET/REMOVE for label rename?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual SET/REMOVE (recommended) | `SET n:SpecNote REMOVE n:KnowledgeNote`. No APOC dependency. | ✓ |
| APOC procedure | `CALL apoc.refactor.rename.label(...)`. Cleaner but requires plugin. | |
| Both with APOC preference | Try APOC first, fall back to manual. More complex. | |

**User's choice:** Manual SET/REMOVE
**Notes:** Only 4 labels to rename. Simple, transparent, works on any Neo4j 5 instance.

### Q4: Migration or app.py handle index transition?

| Option | Description | Selected |
|--------|-------------|----------|
| Migration handles everything (recommended) | Migration drops old + creates new index. app.py updated for fresh DBs. | ✓ |
| Migration = data only, app.py = indexes | Simpler migration but app.py becomes responsible for cleanup. | |
| Index handled in both places | Belt and suspenders — both try to create/drop (idempotent via IF EXISTS). | |

**User's choice:** Migration handles everything
**Notes:** Migration does the transition on existing DBs. app.py's `ensure_knowledge_indexes()` is updated to create `spec_note_search` — handles fresh DBs. Both sides agree.

---

## UI Label and View Naming

### Q1: Change the UI tab label from 'Specs&Notes'?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 'Specs&Notes' (recommended) | Already Spec*-aligned, users recognize it. Purely internal rename. | ✓ |
| Rename tab to 'SpecGraph' | Matches internal view key but less user-friendly. | |
| Rename tab to 'Knowledge Base' | Keeps Knowledge* branding — defeats the purpose of Phase 15. | |

**User's choice:** Keep 'Specs&Notes'
**Notes:** The user-facing tab is already Spec*-aligned. This phase makes the code match.

---

## Claude's Discretion

- Exact filename for the migration `.cypher` file
- Whether to update `spec/DATABASE.md` and `CLAUDE.md` now vs. Phase 20
- Whether `data-service/tests/test_update_flow.py` should be renamed
- Whether `n8n/workflows/knowledge-update.json` is active or deprecated

## Deferred Ideas

- `spec/DATABASE.md` KnowledgeGraph section → SpecGraph (E2E-03, Phase 20 — or do now)
- `CLAUDE.md` Graph Schema section update (E2E-03, Phase 20 — or do now)
- Verify `knowledge-update.json` is genuinely an active workflow (research flag for planner)
