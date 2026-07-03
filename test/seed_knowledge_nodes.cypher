// ============================================================================
// Seed: test/seed_knowledge_nodes.cypher
// ============================================================================
//
// PURPOSE
//   Seeds PRE-migration Knowledge* nodes on a DEV Neo4j database at
//   graph:'KnowledgeGraph', project:'phase15-smoke'. Used together with
//   migrations/2026-07-03_knowledge_to_spec_rename.cypher to prove SC#1:
//   before/after counts showing zero remaining KnowledgeGraph nodes after
//   migration.
//
//   Run this BEFORE the migration:
//     1. Seed:  cypher-shell ... -f test/seed_knowledge_nodes.cypher
//     2. Dry-run and migrate: cypher-shell ... -f migrations/2026-07-03_knowledge_to_spec_rename.cypher
//     3. Verify: run the VERIFICATION queries in the migration file
//
// EXECUTION METHOD
//   Run against the DEV Neo4j instance via cypher-shell or Neo4j Browser.
//   Do NOT run against a production database.
//
// WARNING
//   DEV DATABASE ONLY. This script writes test data that must not reach
//   a production instance. Verify the target database identity before
//   executing (see migration file header for identification steps).
//
// IDEMPOTENT
//   All nodes are MERGEd — safe to re-run.
// ============================================================================

// ---------------------------------------------------------------------------
// KnowledgeNote (carries title+content so the fulltext index can match)
// ---------------------------------------------------------------------------
MERGE (n:KnowledgeNote {noteId: 'seed-note-001', project: 'phase15-smoke', graph: 'KnowledgeGraph'})
SET n.title = 'Phase 15 Smoke Test Note',
    n.content = 'This note verifies the KnowledgeGraph -> SpecGraph migration at graph, label, and index level.',
    n.source = 'seed-script',
    n.createdAt = datetime('2026-07-03T00:00:00Z'),
    n.updatedAt = datetime('2026-07-03T00:00:00Z');

// ---------------------------------------------------------------------------
// KnowledgeTag
// ---------------------------------------------------------------------------
MERGE (t:KnowledgeTag {name: 'smoke-test', project: 'phase15-smoke', graph: 'KnowledgeGraph'});

// ---------------------------------------------------------------------------
// TAGGED_WITH relationship (KnowledgeNote -> KnowledgeTag)
// ---------------------------------------------------------------------------
MATCH (n:KnowledgeNote {noteId: 'seed-note-001', project: 'phase15-smoke'})
MATCH (t:KnowledgeTag {name: 'smoke-test', project: 'phase15-smoke'})
MERGE (n)-[:TAGGED_WITH]->(t);

// ---------------------------------------------------------------------------
// KnowledgeSession
// ---------------------------------------------------------------------------
MERGE (s:KnowledgeSession {sessionId: 'seed-session-001', project: 'phase15-smoke', graph: 'KnowledgeGraph'})
SET s.mode = 'insert',
    s.prompt = 'Seed migration test prompt for smoke testing the rename.',
    s.result = 'Expected: migration renames all Knowledge* labels and graph property to Spec*.',
    s.createdAt = datetime('2026-07-03T00:00:00Z');

// ---------------------------------------------------------------------------
// KnowledgeClass hub nodes (matching data-service ensure_knowledge_indexes keys)
// ---------------------------------------------------------------------------
MERGE (cNote:KnowledgeClass {name: 'KnowledgeNote', graph: 'KnowledgeGraph'})
SET cNote.label = 'KnowledgeNote';

MERGE (cSession:KnowledgeClass {name: 'KnowledgeSession', graph: 'KnowledgeGraph'})
SET cSession.label = 'KnowledgeSession';

// ---------------------------------------------------------------------------
// INSTANCE_OF edges (note -> hub, session -> hub)
// ---------------------------------------------------------------------------
MATCH (n:KnowledgeNote {noteId: 'seed-note-001', project: 'phase15-smoke'})
MATCH (cNote:KnowledgeClass {name: 'KnowledgeNote', graph: 'KnowledgeGraph'})
MERGE (n)-[:INSTANCE_OF]->(cNote);

MATCH (s:KnowledgeSession {sessionId: 'seed-session-001', project: 'phase15-smoke'})
MATCH (cSession:KnowledgeClass {name: 'KnowledgeSession', graph: 'KnowledgeGraph'})
MERGE (s)-[:INSTANCE_OF]->(cSession);

// ============================================================================
// Count query — run AFTER seeding, BEFORE migration, to capture baseline
// ============================================================================
// Run the following against Neo4j Browser or cypher-shell to capture the
// pre-migration state:
//
//   MATCH (n {graph: 'KnowledgeGraph', project: 'phase15-smoke'})
//   RETURN labels(n) AS label, count(*) AS c
//   ORDER BY label;
//
// Expected output:
//   ╒═════════════════╤═══╕
//   │ "KnowledgeClass"│ 2 │
//   │ "KnowledgeNote" │ 1 │
//   │ "KnowledgeSession"│1 │
//   │ "KnowledgeTag"  │ 1 │
//   └─────────────────┴───┘
//
// Then check the fulltext index exists:
//   SHOW INDEXES YIELD name, type, entityType;
//   -- EXPECT: knowledge_note_search listed
