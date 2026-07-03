---
tags: [decision, phase-15, v7.0, migration, neo4j]
date: 2026-07-03
---

# SpecGraph migration matches ValidGraph rename pattern, adds full-text index recreation

## Context

Phase 15 renames the runtime `graph:'KnowledgeGraph'` property value and `Knowledge*` node labels to `SpecGraph`/`Spec*`, closing drift that existed since the [[sessions/2026-06-01 Ontology v6.0 restructure — Core band, SpecGraph, partonomy|Ontology v6.0 restructure]] (which renamed the ontology in May 2026 but never propagated the rename to the running database). [[sessions/2026-07-03 Phase 14 discuss - schema v4 propagation decisions|Phase 14]] set a precedent one layer over: [[decisions/ValidationGraph runtime renamed to ValidGraph per D-14|D-14 renamed the `ValidationGraph` literal to `ValidGraph`]] using a dated `.cypher` migration file with dry-run counts and a dev-only guard.

## Decision

Phase 15's migration reuses the D-14 pattern exactly, with one addition: full-text index lifecycle management.

1. **Single dated `.cypher` file** in `migrations/` — not a Python script, not split across files. Consistent with the one existing migration file in the repo.
2. **Manual `SET`/`REMOVE` for label rename**, not APOC — `MATCH (n:KnowledgeNote) SET n:SpecNote REMOVE n:KnowledgeNote`. Only 4 labels; APOC would be a dependency for no real benefit.
3. **Migration owns the full index transition**: `DROP INDEX knowledge_note_search IF EXISTS` + `CREATE FULLTEXT INDEX spec_note_search IF NOT EXISTS FOR (n:SpecNote) ON EACH [n.title, n.content]`. `data-service/app.py`'s `ensure_knowledge_indexes()` startup hook is updated in parallel to create `spec_note_search` for fresh databases — both paths are idempotent via `IF EXISTS`/`IF NOT EXISTS`, so execution order doesn't matter.
4. **Seed + migrate + verify** — same as the Phase 14 kind-migration: create test Knowledge* nodes on dev if none exist, run the migration, capture before/after counts as proof that `MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n)` returns 0.

## Rationale

- Consistency: two migrations in the repo now, same shape, same safety guarantees. A third migration author has an unambiguous template to follow.
- No APOC dependency keeps the migration portable across any Neo4j 5 instance — the project doesn't otherwise depend on APOC being installed.
- Splitting index management from data migration (considered and rejected) would create a race: if `app.py` restarts mid-migration, it could recreate `knowledge_note_search` after the migration dropped it. Keeping both idempotent and letting either run first avoids that.

## Related

- [[decisions/ValidationGraph runtime renamed to ValidGraph per D-14|D-14 — ValidationGraph runtime renamed to ValidGraph]] — the precedent this decision extends
- [[sessions/2026-06-01 Ontology v6.0 restructure — Core band, SpecGraph, partonomy|Ontology v6.0 restructure]] — where the ontology-side rename happened, creating the drift Phase 15 closes
- `.planning/phases/15-specgraph-runtime-rename/15-CONTEXT.md` — full decision record (D-01 through D-11)
