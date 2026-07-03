// ============================================================================
// Seed: 14-03 DesignState seeding — Wave 0 precondition for SCHM-13
// ============================================================================
//
// PURPOSE
//   Inserts a realistic mix of pre-v4 DesignState nodes into the dev
//   database so the 14-06 kind-migration script (D-09/D-10) has real data
//   to exercise rename, layer-move, and orphan-delete against.
//
// EXECUTION METHOD
//   This script is for dev databases only. Run it as a single block in
//   Neo4j Browser (paste all + Ctrl+Enter). Each statement is separated
//   by a semicolon followed by a blank line — Neo4j Browser recognizes
//   this pattern as multi-statement input.
//
//   Alternatively: cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f test/seed_designstates.cypher
//
// WARNING — DEV DATABASES ONLY
// ============================================================================

// Step 1: Create Run nodes
MERGE (r1:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke', graph: 'Metagraph'})
  SET r1.SendStatus = false, r1.ValidStatus = []
;

MERGE (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke', graph: 'Metagraph'})
  SET r2.SendStatus = false, r2.ValidStatus = []
;

// Step 2: DefState nodes (pre-v4 kind → ParamState after migration)
MERGE (ds1:DesignState {StateId: 'DS_seed_defstate_01', project: 'phase14-smoke'})
  SET ds1.kind = 'DefState', ds1.graph = 'Metagraph', ds1.createdAt = datetime('2026-07-03T00:00:00Z')
WITH ds1
MATCH (r1:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke'})
MERGE (r1)-[:VALIDATES]->(ds1)
;

MERGE (ds2:DesignState {StateId: 'DS_seed_defstate_02', project: 'phase14-smoke'})
  SET ds2.kind = 'DefState', ds2.graph = 'Metagraph', ds2.createdAt = datetime('2026-07-03T00:00:01Z')
WITH ds2
MATCH (r1:Run {Run_Id: 'seed-run-01', project: 'phase14-smoke'})
MERGE (r1)-[:VALIDATES]->(ds2)
;

MERGE (ds3:DesignState {StateId: 'DS_seed_defstate_03', project: 'phase14-smoke'})
  SET ds3.kind = 'DefState', ds3.graph = 'Metagraph', ds3.createdAt = datetime('2026-07-03T00:00:02Z')
WITH ds3
MATCH (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke'})
MERGE (r2)-[:VALIDATES]->(ds3)
;

// Step 3: ObjectState nodes (pre-v4 kind → ObjState after migration)
MERGE (os1:DesignState {StateId: 'OS_seed_objstate_01', project: 'phase14-smoke'})
  SET os1.kind = 'ObjectState', os1.graph = 'Metagraph', os1.createdAt = datetime('2026-07-03T00:00:03Z')
WITH os1
MATCH (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke'})
MERGE (r2)-[:VALIDATES]->(os1)
;

MERGE (os2:DesignState {StateId: 'OS_seed_objstate_02', project: 'phase14-smoke'})
  SET os2.kind = 'ObjectState', os2.graph = 'Metagraph', os2.createdAt = datetime('2026-07-03T00:00:04Z')
WITH os2
MATCH (r2:Run {Run_Id: 'seed-run-02', project: 'phase14-smoke'})
MERGE (r2)-[:VALIDATES]->(os2)
;

// Step 4: Orphaned DesignState (no Run link — migration should DELETE)
MERGE (orphan:DesignState {StateId: 'DS_seed_orphan_01', project: 'phase14-smoke'})
  SET orphan.kind = 'DefState', orphan.graph = 'Metagraph', orphan.createdAt = datetime('2026-07-03T00:00:05Z')
;

// ============================================================================
// VERIFICATION (run after seeding):
//   MATCH (ds:DesignState {project:'phase14-smoke'}) RETURN ds.kind, count(*) — expect DefState:4, ObjectState:2
//   MATCH (ds:DesignState {project:'phase14-smoke'}) WHERE NOT (ds)<-[:VALIDATES]-(:Run) RETURN count(ds) — expect 1
// ============================================================================
