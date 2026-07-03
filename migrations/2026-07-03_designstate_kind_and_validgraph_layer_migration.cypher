// ============================================================================
// Migration: 2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher
// ============================================================================
//
// PURPOSE
//   Two independent database migrations that together bring the live dev Neo4j
//   to the v4 / ValidGraph end-state. Both are destructive (one deletes nodes,
//   one bulk-SETs a property on ~1169 existing nodes). Each carries its own
//   dry-run count and dev-database-only guard.
//
//   SECTION A — DesignState kind rename + layer move + orphan delete (D-09/D-10,
//                SCHM-13). Renames kind values from pre-v4 (DefState/ObjectState)
//                to v4 (ParamState/ObjState), moves Run-linked DesignStates to
//                graph='ValidGraph', and DELETES orphan DesignState nodes that
//                have no linked Run (enforcing the no-orphan invariant).
//
//   SECTION B — ValidationGraph->ValidGraph layer-value consolidation (D-14.1).
//                The shipped runtime used graph='ValidationGraph' (1169 live nodes:
//                ValidationEntity, ValidationRun, IntegrationConfig), but D-14
//                resolved to rename this to 'ValidGraph' — the single canonical
//                layer value matching Phase-13 D-01 wording. This section renames
//                only the graph property VALUE, not any node label.
//
// EXECUTION METHOD
//   This script is NOT invoked automatically by any application code. Run it
//   manually against the DEV Neo4j instance using one of:
//     - cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f migrations/2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher
//     - Neo4j Browser: paste each section's executable statement(s) and execute
//       them in order (dry-run first, then migration, then verification).
//
//   Sequence:
//     1. Run SECTION A Step 0 dry-run — review counts before proceeding.
//     2. Run SECTION A Steps 1-2 — kind rename + layer move + orphan delete.
//     3. Run SECTION B Step 0 dry-run — review ~1169 count before proceeding.
//     4. Run SECTION B Step 1 — layer-value SET.
//     5. Run VERIFICATION queries — confirm zero old-kind / old-layer nodes remain.
//
// ============================================================================
// WARNING — DEV DATABASES ONLY (read before running)
// ============================================================================
//   SECTION A Step 2 DELETES DesignState nodes (orphans with no linked Run).
//   SECTION B Step 1 bulk-SETs the graph property on ~1169 live nodes.
//
//   Both operations are DESTRUCTIVE and must NEVER be run against a database
//   that is or might be a production instance. Verify the target database
//   identity before executing any write step:
//
//     MATCH (n) RETURN DISTINCT labels(n) AS labels, count(*) AS c ORDER BY c DESC
//     LIMIT 10;
//
//   — If you see real domain data (actual architectural projects, rule sets,
//     validation entities from production use), STOP. This is not a dev DB.
//
//   — If you see only test/sandbox data (e.g. project='test', project='phase14-smoke',
//     or data seeded by test/seed_designstates.cypher), it is safe to proceed.
//
// ============================================================================

// ============================================================================
// SECTION A — DesignState kind + layer migration (SCHM-13, D-09/D-10)
// ============================================================================

// ---------------------------------------------------------------------------
// Step 0: DRY-RUN — count what will be renamed, moved, and deleted
// ---------------------------------------------------------------------------
// Run these BEFORE any SET or DELETE statement. Review the counts to confirm
// the operation matches expectations.

// 0a. Kind breakdown — how many DesignState nodes per current kind value?
MATCH (ds:DesignState)
RETURN ds.kind AS currentKind, count(*) AS count
ORDER BY currentKind;

// 0b. Orphan count — how many DesignState nodes will be DELETED?
MATCH (ds:DesignState) WHERE NOT (ds)<-[:VALIDATES]-(:Run)
RETURN count(ds) AS orphansToDelete;

// 0c. DesignState nodes that ARE Run-linked (will be moved to ValidGraph)
MATCH (r:Run)-[:VALIDATES]->(ds:DesignState)
RETURN count(ds) AS runLinkedDesignStates;

// ---------------------------------------------------------------------------
// Step 1: Rename kind values + move Run-linked DesignStates to ValidGraph
// ---------------------------------------------------------------------------
// Renames DefState→ParamState and ObjectState→ObjState on ALL DesignState
// nodes. Also moves Run-linked DesignStates from their current graph value
// (typically 'Metagraph') to graph='ValidGraph' (D-09 + D-14 consistency).
//
// Orphan nodes (those without a Run link) also get their kind renamed here
// so that after Step 2's deletion, zero nodes carry the old kind values.
// This is safe-to-re-run idempotently: after the first pass, WHERE ds.kind
// matches zero nodes and the SET is a no-op.

MATCH (ds:DesignState) WHERE ds.kind = 'DefState'
SET ds.kind = 'ParamState';

MATCH (ds:DesignState) WHERE ds.kind = 'ObjectState'
SET ds.kind = 'ObjState';

MATCH (r:Run)-[:VALIDATES]->(ds:DesignState)
SET ds.graph = 'ValidGraph';

// ---------------------------------------------------------------------------
// Step 2: DELETE orphan DesignState nodes (destructive — dev databases only)
// ---------------------------------------------------------------------------
// Enforces the no-orphan invariant (Phase 13 D-05): any DesignState without
// a VALIDATES relationship from a Run is unreachable and must be removed.
//
// === DEV DATABASES ONLY ===
// This is a destructive DELETE. Confirm the target is the DEV database before
// running. See the WARNING block at the top of this file for identification
// steps. NEVER run against production data.
// ===========================

MATCH (ds:DesignState) WHERE NOT (ds)<-[:VALIDATES]-(:Run)
DETACH DELETE ds;

// ============================================================================
// SECTION B — ValidationGraph→ValidGraph layer-value consolidation (D-14.1)
// ============================================================================

// ---------------------------------------------------------------------------
// Step 0: DRY-RUN — count nodes currently carrying the old layer value
// ---------------------------------------------------------------------------
// Expected: ~1169 (ValidationEntity ×1148 + ValidationRun ×20 +
// IntegrationConfig ×1). Run this BEFORE the SET to confirm.

MATCH (n {graph: 'ValidationGraph'})
RETURN labels(n) AS label, count(*) AS count
ORDER BY count DESC;

MATCH (n {graph: 'ValidationGraph'})
RETURN count(n) AS nodesToMigrate;

// ---------------------------------------------------------------------------
// Step 1: Rename the layer property VALUE from 'ValidationGraph' to 'ValidGraph'
// ---------------------------------------------------------------------------
// D-14: rename the graph property VALUE on all existing nodes that carry the
// old runtime literal. Node labels stay unchanged (ValidationRun/ValidationEntity/
// IntegrationConfig keep their labels). Only the graph property value changes.
//
// Idempotent: after the first pass, WHERE n.graph='ValidationGraph' matches
// zero nodes and the SET is a no-op on re-run.
//
// === DEV DATABASES ONLY ===
// This bulk-SET touches ~1169 live nodes. Confirm the target is the DEV
// database before running. See the WARNING block at the top of this file
// for identification steps.
// ===========================

MATCH (n {graph: 'ValidationGraph'})
SET n.graph = 'ValidGraph';

// ============================================================================
// VERIFICATION QUERIES (read-only, documentation — not auto-executed)
// ============================================================================
//
// Run these AFTER the migration to confirm the expected end-state.
//
// --- DesignState kind verification (SECTION A) ---
//   MATCH (ds:DesignState) WHERE ds.kind IN ['DefState', 'ObjectState']
//   RETURN count(ds);
//   -- EXPECT: 0 (no DesignState nodes carry the old v3 kind values)
//
//   MATCH (ds:DesignState) WHERE NOT (ds)<-[:VALIDATES]-(:Run)
//   RETURN count(ds);
//   -- EXPECT: 0 (no orphan DesignState nodes remain)
//
//   MATCH (ds:DesignState)
//   RETURN ds.kind AS kind, count(*) AS c ORDER BY kind;
//   -- EXPECT: ParamState, ObjState only (no PropState unless seeded)
//   -- EXPECT: count matches the original Step 0a minus orphans deleted
//
// --- DesignState graph layer verification (SECTION A Step 1c) ---
//   MATCH (r:Run)-[:VALIDATES]->(ds:DesignState)
//   RETURN ds.graph AS graphLabel, count(*) AS c;
//   -- EXPECT: 'ValidGraph' for all Run-linked DesignState nodes
//
// --- Layer-value verification (SECTION B) ---
//   MATCH (n {graph: 'ValidationGraph'})
//   RETURN count(n);
//   -- EXPECT: 0 (zero nodes carry the old 'ValidationGraph' literal)
//
//   MATCH (n {graph: 'ValidGraph'})
//   RETURN count(n);
//   -- EXPECT: count of all nodes that were migrated (should match Section B
//   -- Step 0 dry-run total, which was ~1169)
//
// --- Combined: DesignState end-state (SC#5 proof) ---
//   MATCH (ds:DesignState)
//   RETURN ds.kind AS kind, ds.graph AS graph, count(*) AS c
//   ORDER BY kind, graph;
//   -- EXPECT: every DesignState is either ParamState+ValidGraph or
//   -- ObjState+ValidGraph; zero orphans; zero old-kind entries
//   -- (full SC#5 evidence: before/after counts captured at execution time)
