// ============================================================================
// Seed: 14-03 DesignState seeding — Wave 0 precondition for SCHM-13
// ============================================================================
//
// PURPOSE
//   Inserts a realistic mix of pre-v4 DesignState nodes into the dev
//   database so the 14-06 kind-migration script (D-09/D-10) has real data
//   to exercise rename, layer-move, and orphan-delete against. The dev DB
//   currently holds ZERO DesignState nodes (confirmed live during Phase 14
//   research) — without this seed, the migration would run against empty
//   data and prove only syntactic correctness, not behavioral correctness
//   (see 14-RESEARCH.md Pitfall 5).
//
// EXECUTION METHOD
//   This script is for dev databases only. Run it manually against the dev
//   Neo4j instance using one of:
//     - cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f test/seed_designstates.cypher
//     - Neo4j Browser: paste and execute the statements below (one at a time)
//
// WARNING — DEV DATABASES ONLY
//   This script creates fake Run and DesignState nodes under project
//   'phase14-smoke'. Do NOT run against a database that contains real
//   project data with the same project name.
// ============================================================================

// ---------------------------------------------------------------------------
// Step 1: Seed DefState-kind DesignState nodes (2-3, Run-linked)
// ---------------------------------------------------------------------------
// These simulate the v3 parameter-kind value that the migration renames
// to ParamState.

MERGE (:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke', graph: 'Metagraph'})
  SET Run.SendStatus = false, Run.ValidStatus = [];

MERGE (:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke', graph: 'Metagraph'})
  SET Run.SendStatus = false, Run.ValidStatus = [];

// DefState #1 — linked to seed-run-01
MERGE (ds1:DesignState {StateId: 'DS_seed_defstate_01', project: 'phase14-smoke'})
  SET ds1.kind = 'DefState', ds1.graph = 'Metagraph',
      ds1.createdAt = datetime('2026-07-03T00:00:00Z');
WITH ds1
MATCH (r1:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke'})
MERGE (r1)-[:VALIDATES]->(ds1);

// DefState #2 — linked to seed-run-01 (same Run, multiple DesignState nodes)
MERGE (ds2:DesignState {StateId: 'DS_seed_defstate_02', project: 'phase14-smoke'})
  SET ds2.kind = 'DefState', ds2.graph = 'Metagraph',
      ds2.createdAt = datetime('2026-07-03T00:00:01Z');
WITH ds2
MATCH (r1:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke'})
MERGE (r1)-[:VALIDATES]->(ds2);

// DefState #3 — linked to seed-run-02
MERGE (ds3:DesignState {StateId: 'DS_seed_defstate_03', project: 'phase14-smoke'})
  SET ds3.kind = 'DefState', ds3.graph = 'Metagraph',
      ds3.createdAt = datetime('2026-07-03T00:00:02Z');
WITH ds3
MATCH (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke'})
MERGE (r2)-[:VALIDATES]->(ds3);

// ---------------------------------------------------------------------------
// Step 2: Seed ObjectState-kind DesignState nodes (1-2, Run-linked)
// ---------------------------------------------------------------------------
// These simulate the v3 object-kind value that the migration renames to
// ObjState.

// ObjectState #1 — linked to seed-run-02
MERGE (os1:DesignState {StateId: 'OS_seed_objstate_01', project: 'phase14-smoke'})
  SET os1.kind = 'ObjectState', os1.graph = 'Metagraph',
      os1.createdAt = datetime('2026-07-03T00:00:03Z');
WITH os1
MATCH (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke'})
MERGE (r2)-[:VALIDATES]->(os1);

// ObjectState #2 — linked to seed-run-02
MERGE (os2:DesignState {StateId: 'OS_seed_objstate_02', project: 'phase14-smoke'})
  SET os2.kind = 'ObjectState', os2.graph = 'Metagraph',
      os2.createdAt = datetime('2026-07-03T00:00:04Z');
WITH os2
MATCH (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke'})
MERGE (r2)-[:VALIDATES]->(os2);

// ---------------------------------------------------------------------------
// Step 3: Seed orphaned DesignState (NO incoming Run link)
// ---------------------------------------------------------------------------
// This node has no (:Run)-->(:DesignState) path and should be DELETED by
// the kind-migration script's orphan-delete step (D-10). Without this seed,
// the DELETE path would never be exercised.

MERGE (orphan:DesignState {StateId: 'DS_seed_orphan_01', project: 'phase14-smoke'})
  SET orphan.kind = 'DefState', orphan.graph = 'Metagraph',
      orphan.createdAt = datetime('2026-07-03T00:00:05Z');

// ============================================================================
// VERIFICATION QUERIES (read-only, run after seeding above)
// ============================================================================
//
// Total seeded DesignState nodes:
//   MATCH (ds:DesignState {project:'phase14-smoke'}) RETURN count(ds) AS total
//   -- expect 6
//
// Run-linked DesignState nodes:
//   MATCH (r:Run {project:'phase14-smoke'})-[:VALIDATES]->(ds:DesignState)
//   RETURN count(ds) AS linked
//   -- expect 5
//
// Orphaned DesignState nodes (no Run link):
//   MATCH (ds:DesignState {project:'phase14-smoke'})
//   WHERE NOT (ds)<-[:VALIDATES]-(:Run)
//   RETURN count(ds) AS orphans
//   -- expect 1
//
// Kind breakdown:
//   MATCH (ds:DesignState {project:'phase14-smoke'})
//   RETURN ds.kind AS kind, count(*) AS c
//   ORDER BY kind
//   -- expect DefState: 4, ObjectState: 2
//
// After running the kind-migration script:
//   MATCH (ds:DesignState {project:'phase14-smoke'})
//   RETURN ds.kind AS kind, count(*) AS c
//   ORDER BY kind
//   -- expect ParamState: 3 (DefState renames to ParamState, but orphan was deleted)
//   -- expect ObjState: 2 (ObjectState renames to ObjState, both still linked)
