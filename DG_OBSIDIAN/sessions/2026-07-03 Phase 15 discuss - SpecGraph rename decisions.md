---
tags: [session, phase-15, v7.0, specgraph, discuss]
date: 2026-07-03
model: claude-sonnet-5
---

# 2026-07-03 — Phase 15 discussion: SpecGraph runtime rename decisions

## Context

Ran `/gsd-discuss-phase 15` (SpecGraph Runtime Rename). This phase closes the drift the [[sessions/2026-06-01 Ontology v6.0 restructure — Core band, SpecGraph, partonomy|Ontology v6.0 restructure]] created back in June: the ontology renamed `KnowledgeGraph`→`SpecGraph` months ago, but `data-service/app.py`, 3 n8n workflows, and NeoVis config still use the old `Knowledge*` labels. No design decisions were locked upstream to re-litigate — this is a mechanical propagation phase following the pattern [[sessions/2026-07-03 Phase 14 discuss - schema v4 propagation decisions|Phase 14]] established.

## What was done

1. Loaded PROJECT.md / REQUIREMENTS.md / STATE.md / ROADMAP.md, both Phase 13 and Phase 14 CONTEXT.md files, and the 7 codebase maps (STACK/ARCHITECTURE/INTEGRATIONS).
2. Grepped the full runtime for `Knowledge*` references — found 10 files needing content edits: `data-service/app.py` (20+ Cypher queries), 3 n8n workflow JSONs, `graph-viewer/config.template.js` + `index.html`, `knowledge_schema.cypher`, `_add_backfill.py`, and 4 test files. Also found 2 n8n export/backup files (`_active-graph-query.json`, `_all-workflows-export.json`) carrying the same stale references.
3. Presented 4 gray areas; user selected all four: File renames, n8n export handling, Migration scope and safety, UI label and view naming.
4. Wrote `15-CONTEXT.md` + `15-DISCUSSION-LOG.md` in `.planning/phases/15-specgraph-runtime-rename/`.

## Key decisions (user-confirmed)

- **Rename all 8 files with "knowledge" in the name** to "spec" — `knowledge_schema.cypher`→`spec_schema.cypher`, 3 n8n workflows, 3 test files. n8n internal workflow `name` fields and node display names ("Write KnowledgeSession") also switch to Spec* — no stale Knowledge* left visible anywhere, including the n8n editor UI.
- **Delete `_add_backfill.py`** — a one-off backfill utility superseded by the proper migration script — and **delete both n8n export files** (`_active-graph-query.json`, `_all-workflows-export.json`) since they're generated snapshots, not source-of-truth (same reasoning Phase 14 applied).
- **Migration reuses the D-14 pattern exactly**: single dated `.cypher` file, manual `SET`/`REMOVE` label rename (no APOC), seed+migrate+verify with before/after counts. New addition: the migration also owns full-text index recreation (`knowledge_note_search`→`spec_note_search`), with `data-service/app.py`'s startup hook updated to match — both idempotent so execution order doesn't matter. Full rationale: [[decisions/SpecGraph migration matches ValidGraph rename pattern with full index recreation|SpecGraph migration decision note]].
- **UI tab label "Specs&Notes" stays unchanged** — it was already Spec*-aligned before this phase even started. Only the internal NeoVis view key (`"KnowledgeGraph"`→`"SpecGraph"`) and the 4 label/visGroup entries in `config.template.js` change; colors preserved.

## Result

`.planning/phases/15-specgraph-runtime-rename/15-CONTEXT.md` + `15-DISCUSSION-LOG.md` written and committed (2 commits: context capture + STATE.md session record — `commit_docs: false` in this project's GSD config didn't block the workflow's own git calls this time; manual commit fallback used).

**Research flag for the planner:** verify `n8n/workflows/knowledge-update.json` is genuinely an active workflow (has a webhook route, imported in n8n) before renaming — Obsidian session notes describe it as an 8-node workflow but this wasn't re-verified live this session.

**Deferred:** whether `spec/DATABASE.md` and `CLAUDE.md`'s Graph Schema section get updated now or wait for Phase 20 (E2E-03) — left to the planner's judgment, noted in CONTEXT.md.

**Next:** `/gsd-plan-phase 15`.

## Graph connections

- [[sessions/2026-07-03 Phase 14 discuss - schema v4 propagation decisions|Prior session: Phase 14 discuss]] — the propagation pattern this session reuses
- [[decisions/SpecGraph migration matches ValidGraph rename pattern with full index recreation|SpecGraph migration matches ValidGraph rename pattern]] — the key decision this session
- [[decisions/ValidationGraph runtime renamed to ValidGraph per D-14|D-14 — ValidationGraph runtime renamed to ValidGraph]] — the precedent extended here
- [[sessions/2026-06-01 Ontology v6.0 restructure — Core band, SpecGraph, partonomy|Ontology v6.0 restructure]] — where the ontology-side rename happened, creating the drift this phase closes
- [[Graph schema v3 is the canonical data model]] — stale atlas note; still not updated for v4/v7.0 (tracked as ongoing gap)
