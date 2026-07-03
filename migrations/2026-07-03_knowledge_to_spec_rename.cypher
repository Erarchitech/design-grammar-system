// ============================================================================
// Migration: 2026-07-03_knowledge_to_spec_rename.cypher
// ============================================================================
//
// PURPOSE
//   Four-part database migration that brings a live dev Neo4j database from
//   the Knowledge* end-state to the Spec* end-state (SPEC-01):
//
//   (1) Rename the graph property VALUE on all nodes: KnowledgeGraph->SpecGraph
//   (2) Normalize KnowledgeClass hub-node name/label property VALUES:
//       KnowledgeNote->SpecNote, KnowledgeSession->SpecSession
//       (so migrated hubs match what data-service ensure_spec_indexes() writes
//       after its rename in 15-02 — no duplicate hub nodes)
//   (3) Rename four node LABELS (no APOC — manual SET/REMOVE per D-08):
//       KnowledgeNote->SpecNote, KnowledgeTag->SpecTag,
//       KnowledgeSession->SpecSession, KnowledgeClass->SpecClass
//   (4) Swap the fulltext index: DROP knowledge_note_search,
//       CREATE spec_note_search FOR (n:SpecNote) ON EACH [n.title, n.content]
//
//   Relationships (TAGGED_WITH, INSTANCE_OF) survive the label rename
//   automatically (Neo4j binds relationships to node identity, not labels).
//
// EXECUTION METHOD
//   This script is NOT invoked automatically by any application code. Run it
//   manually against the DEV Neo4j instance using one of:
//     - cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f migrations/2026-07-03_knowledge_to_spec_rename.cypher
//     - Neo4j Browser: paste and execute each step in order (dry-run first,
//       then migration, then verification).
//
//   Sequence:
//     1. Run Step 0 DRY-RUN — review counts before proceeding.
//     2. Run Steps 1-5 in order.
//     3. Run VERIFICATION queries — confirm zero KnowledgeGraph nodes remain.
//
// IDEMPOTENT
//   Every write step has a built-in guard (WHERE clause or IF EXISTS/IF NOT
//   EXISTS). Re-running the entire file against an already-migrated database
//   is a no-op: no statement produces an error.
// ============================================================================

// ============================================================================
// WARNING — DEV DATABASES ONLY (read before running)
// ============================================================================
//   Steps 1-3 are bulk-SET operations that rename the graph property value on
//   all KnowledgeGraph nodes and relabel four node types. Step 3 uses REMOVE
//   to strip old labels, which makes label queries against the old names
//   return zero results.
//
//   These operations are DESTRUCTIVE and must NEVER be run against a database
//   that is or might be a production instance. Verify the target database
//   identity before executing any write step:
//
//     MATCH (n) RETURN DISTINCT labels(n) AS labels, count(*) AS c ORDER BY c DESC
//     LIMIT 10;
//
//   — If you see real domain data (actual architectural projects, rule sets,
//     validation entities from production use), STOP. This is not a dev DB.
//
//   — If you see only test/sandbox data (e.g. project='test', project='phase15-smoke',
//     or data seeded by test/seed_knowledge_nodes.cypher), it is safe to proceed.
//
// ============================================================================

// ============================================================================
// Step 0: DRY-RUN — count what will be renamed
// ============================================================================
// Run these BEFORE any SET, REMOVE, or CREATE statement. Review the counts
// to confirm the operation matches expectations.

// 0a. Nodes at the old graph value — how many carry graph:'KnowledgeGraph'?
MATCH (n {graph: 'KnowledgeGraph'})
RETURN labels(n) AS label, count(*) AS c
ORDER BY label;

// 0b. Per-label breakdown of the four Knowledge* labels
MATCH (n:KnowledgeNote) RETURN count(n) AS knowledgeNotes;
MATCH (n:KnowledgeTag) RETURN count(n) AS knowledgeTags;
MATCH (n:KnowledgeSession) RETURN count(n) AS knowledgeSessions;
MATCH (n:KnowledgeClass) RETURN count(n) AS knowledgeClasses;

// 0c. KnowledgeClass hub-node name breakdown (before normalization)
MATCH (c:KnowledgeClass)
RETURN c.name AS hubName, count(*) AS c
ORDER BY hubName;

// 0d. Confirm the fulltext index exists (to verify DROP will remove it)
SHOW INDEXES YIELD name, type, entityType
WHERE name = 'knowledge_note_search';

// ============================================================================
// Step 1: Rename the layer property VALUE (KnowledgeGraph -> SpecGraph)
// ============================================================================
// Changes graph property on ALL nodes at graph:'KnowledgeGraph' to
// graph:'SpecGraph'. Node labels are untouched at this stage.
//
// Idempotent: after the first pass, WHERE n.graph='KnowledgeGraph' matches
// zero nodes and the SET is a no-op on re-run.
//
// === DEV DATABASES ONLY ===
// See the WARNING block at the top of this file for identification steps.
// ===========================

MATCH (n {graph: 'KnowledgeGraph'})
SET n.graph = 'SpecGraph';

// ============================================================================
// Step 2: Normalize KnowledgeClass hub-node property VALUES
//         (KnowledgeNote->SpecNote, KnowledgeSession->SpecSession)
// ============================================================================
// This MUST run BEFORE the label rename (Step 3) because we match on
// :KnowledgeClass — after Step 3 the label is :SpecClass.
//
// The data-service function ensure_spec_indexes() (15-02) will MERGE
// SpecClass hub nodes with name 'SpecNote'/'SpecSession'. Without this
// normalization, already-migrated hubs carry the old name values, so the
// MERGE creates duplicate hub nodes. This step prevents that by rewriting
// name/label on existing hubs before the label rename.
//
// Idempotent: after the first pass, WHERE c.name='KnowledgeNote' matches
// zero nodes and the SET is a no-op.
//
// === DEV DATABASES ONLY ===
// See the WARNING block at the top of this file for identification steps.
// ===========================

MATCH (c:KnowledgeClass) WHERE c.name = 'KnowledgeNote'
SET c.name = 'SpecNote', c.label = 'SpecNote';

MATCH (c:KnowledgeClass) WHERE c.name = 'KnowledgeSession'
SET c.name = 'SpecSession', c.label = 'SpecSession';

// ============================================================================
// Step 3: Rename node LABELS via manual SET/REMOVE (no APOC per D-08)
//         KnowledgeNote->SpecNote, KnowledgeTag->SpecTag,
//         KnowledgeSession->SpecSession, KnowledgeClass->SpecClass
// ============================================================================
// Each statement is a separate MATCH+SET+REMOVE. After execution, the old
// Knowledge* label is removed and the new Spec* label is added.
//
// Relationships (TAGGED_WITH, INSTANCE_OF) survive automatically because
// Neo4j binds relationships to node identity, not labels.
//
// Idempotent: after the first pass, MATCH (n:KnowledgeX) returns zero nodes
// (the label was removed) and SET/REMOVE is a no-op.
//
// === DEV DATABASES ONLY ===
// See the WARNING block at the top of this file for identification steps.
// ===========================

MATCH (n:KnowledgeNote) SET n:SpecNote REMOVE n:KnowledgeNote;
MATCH (n:KnowledgeTag) SET n:SpecTag REMOVE n:KnowledgeTag;
MATCH (n:KnowledgeSession) SET n:SpecSession REMOVE n:KnowledgeSession;
MATCH (n:KnowledgeClass) SET n:SpecClass REMOVE n:KnowledgeClass;

// ============================================================================
// Step 4: DROP the old fulltext index
// ============================================================================
// Removes the index that was created for (n:KnowledgeNote). The replacement
// index for (n:SpecNote) is created in Step 5.
//
// Idempotent: IF EXISTS guards against error on re-run (index already
// dropped from the first pass).

DROP INDEX knowledge_note_search IF EXISTS;

// ============================================================================
// Step 5: CREATE the new fulltext index
// ============================================================================
// Fulltext index on (n:SpecNote) over title and content, matching what
// data-service ensure_spec_indexes() will write after its rename (15-02).
//
// Idempotent: IF NOT EXISTS guards against error on re-run.

CREATE FULLTEXT INDEX spec_note_search IF NOT EXISTS
FOR (n:SpecNote) ON EACH [n.title, n.content];

// ============================================================================
// VERIFICATION QUERIES (read-only, documentation — not auto-executed)
// ============================================================================
//
// Run these AFTER Steps 1-5 to confirm the expected end-state.
//
// --- graph property verification (Step 1) ---
//   MATCH (n {graph: 'KnowledgeGraph'})
//   RETURN count(n);
//   -- EXPECT: 0 (zero nodes carry the old KnowledgeGraph property value)
//
//   MATCH (n {graph: 'SpecGraph'})
//   RETURN count(n);
//   -- EXPECT: same as Step 0a dry-run total (all migrated nodes)
//
// --- hub-node name normalization verification (Step 2) ---
//   MATCH (c:SpecClass) WHERE c.name IN ['KnowledgeNote', 'KnowledgeSession']
//   RETURN count(c);
//   -- EXPECT: 0 (no hub nodes carry the old Knowledge* name values)
//
//   MATCH (c:SpecClass)
//   RETURN c.name AS hubName, count(*) AS c
//   ORDER BY hubName;
//   -- EXPECT: SpecNote, SpecSession only
//
// --- label rename verification (Step 3) ---
//   MATCH (n:KnowledgeNote) RETURN count(n);
//   -- EXPECT: 0 (no nodes carry the old KnowledgeNote label)
//
//   MATCH (n:KnowledgeTag) RETURN count(n);
//   -- EXPECT: 0
//
//   MATCH (n:KnowledgeSession) RETURN count(n);
//   -- EXPECT: 0
//
//   MATCH (n:KnowledgeClass) RETURN count(n);
//   -- EXPECT: 0
//
//   MATCH (n:SpecNote) RETURN count(n);
//   -- EXPECT: same as Step 0b KnowledgeNote count
//
//   MATCH (n:SpecTag) RETURN count(n);
//   -- EXPECT: same as Step 0b KnowledgeTag count
//
//   MATCH (n:SpecSession) RETURN count(n);
//   -- EXPECT: same as Step 0b KnowledgeSession count
//
//   MATCH (n:SpecClass) RETURN count(n);
//   -- EXPECT: same as Step 0b KnowledgeClass count
//
// --- fulltext index verification (Steps 4-5) ---
//   SHOW INDEXES YIELD name, type, entityType
//   WHERE name IN ['knowledge_note_search', 'spec_note_search'];
//   -- EXPECT: spec_note_search present, knowledge_note_search absent
//
// --- Combined end-state (SC#1 proof) ---
//   MATCH (n {graph: 'SpecGraph'})
//   RETURN labels(n) AS label, count(*) AS c
//   ORDER BY label;
//   -- EXPECT: only SpecNote, SpecTag, SpecSession, SpecClass labels (and any
//   -- other labels the nodes carried before migration, like the original
//   -- runtime labels that were not renamed — e.g. Run, ValidationEntity, etc.)
