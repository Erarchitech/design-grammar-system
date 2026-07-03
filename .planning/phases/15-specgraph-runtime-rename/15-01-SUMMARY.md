---
phase: 15-specgraph-runtime-rename
plan: 01
status: complete
tasks_completed: 2
tasks_total: 3
task_manual_deferred: 1
deferred_task: "Task 3: Live seed -> migrate -> verify on dev Neo4j (SC#1 proof)"
date: 2026-07-03
---

## 15-01: KnowledgeGraph → SpecGraph DB Migration

### Completed Tasks

**Task 1: Write the seed script for migration proof** ✓
- Created `test/seed_knowledge_nodes.cypher` — dev-only seed script
- MERGEs: KnowledgeNote (with title+content), KnowledgeTag, KnowledgeSession, two KnowledgeClass hubs
- Includes TAGGED_WITH and INSTANCE_OF relationships
- Idempotent (MERGE-based), project:'phase15-smoke' isolation
- Header marks it dev-only with WARNING block
- Trailing commented count query for pre-migration baseline capture

**Task 2: Write the KnowledgeGraph→SpecGraph migration** ✓
- Created `migrations/2026-07-03_knowledge_to_spec_rename.cypher`
- Mirrors Phase 14 migration structure: PURPOSE, EXECUTION METHOD, DEV-DATABASES-ONLY WARNING block
- Five operations in order:
  1. Step 0 DRY-RUN (read-only counts grouped by label)
  2. Step 1: SET n.graph = 'SpecGraph' (WHERE-guarded)
  3. Step 2: Normalize KnowledgeClass hub name/label properties (KnowledgeNote→SpecNote, KnowledgeSession→SpecSession) BEFORE label rename
  4. Step 3: Manual SET/REMOVE for all four labels (no APOC, D-08)
  5. Step 4-5: DROP INDEX knowledge_note_search + CREATE FULLTEXT INDEX spec_note_search
- Full VERIFICATION block with EXPECT annotations (SC#1 proof queries)
- Every write step is idempotent (WHERE / IF EXISTS / IF NOT EXISTS)
- DEV DATABASES ONLY guard with identity-check query

**Task 3: Live seed → migrate → verify on dev Neo4j (SC#1 proof)** — DEFERRED
- This is a manual task requiring a running Neo4j instance
- Operator should: run seed → run migration (Step 0 dry-run first) → run VERIFICATION queries → paste counts below

### Manual Verification (Task 3 — to be completed by operator)

Run sequence on DEV Neo4j:
```bash
# 1. Seed
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f test/seed_knowledge_nodes.cypher

# 2. Migration (dry-run + execute)
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f migrations/2026-07-03_knowledge_to_spec_rename.cypher

# 3. Verification (run the VERIFICATION block queries)
```

Expected SC#1 results:
- `MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n)` → EXPECT 0
- `MATCH (n:KnowledgeNote|KnowledgeTag|KnowledgeSession|KnowledgeClass)` → each EXPECT 0
- `MATCH (n {graph:'SpecGraph'}) RETURN labels(n), count(*)` → shows Spec* labels
- `SHOW FULLTEXT INDEXES` → includes spec_note_search, NOT knowledge_note_search

### Key Files

| File | Status | Description |
|------|--------|-------------|
| `migrations/2026-07-03_knowledge_to_spec_rename.cypher` | NEW | Dated, idempotent, dev-guarded migration |
| `test/seed_knowledge_nodes.cypher` | NEW | Dev-only seed for SC#1 proof |

### Self-Check: PASSED

- Migration file: DEV-DATABASES-ONLY guard ✓, Step 0 dry-run ✓, all 4 rename operations ✓, VERIFICATION block ✓, idempotent ✓
- Seed file: KnowledgeNote+Tag+Session+Class ✓, TAGGED_WITH + INSTANCE_OF edges ✓, dev-only header ✓, count query ✓
- Hub-node name normalization (Step 2) runs BEFORE label rename (Step 3) — correct order
- Re-running is a no-op (all guards present)
