// ============================================================================
// Seed: 1200 golden fixture — DE-01 persisted-replay leg
// ============================================================================
//
// PURPOSE
//   Projects the frozen cross-service golden fixture (fixtures/golden/fixture.json)
//   into Neo4j so DE-01's persisted-replay leg has real graph data to re-derive a
//   canonical status from. This is the only path from the checked-in fixture file
//   into the live graph (D-10) — there is no second, independently-authored
//   Neo4j-only fixture.
//
// Phase 1203-02 note: the three obj_*.dgId literals below were re-derived under
// the D-09 length-prefix hash-input encoding (see fixture.json's per-object _note
// and MANIFEST.md's Change-Reason Log, FIXTURE_VERSION 1.3.0). Pre-fix values were
// dg:57C65BE15E8E368B (pass), dg:729E143958721742 (fail), dg:0B23FFBDA52B73A6 (empty).
//
// EXECUTION METHOD
//   This script is for dev databases only. Run it as a single block in
//   Neo4j Browser (paste all + Ctrl+Enter). Each statement is separated
//   by a semicolon followed by a blank line — Neo4j Browser recognizes
//   this pattern as multi-statement input.
//
//   Alternatively:
//     cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/seed.cypher
//
// WARNING — DEV DATABASES ONLY
// ============================================================================
//
// TEARDOWN (idempotent — run before re-seeding, or to remove the fixture entirely)
//   MATCH (n {project: 'DG-1200-GOLDEN'}) DETACH DELETE n
//
// ============================================================================
//
// PARAMETERIZATION DISCIPLINE (T-1200-06)
//   This file is a static, checked-in, dev-only script with literal values —
//   matching the test/seed_designstates.cypher / test/seed_validation_run.cypher
//   precedent, not a parameterized runtime query. ANY Python or C# code that
//   *executes* this file — or that reconstructs equivalent statements from
//   fixture-derived values at runtime — MUST pass those values as a parameter
//   dict (session.run(query, {"key": value, ...})) and MUST NEVER string-
//   interpolate them into query text (f-string / % / .format / string
//   concatenation). This is the exact discipline already followed by every
//   function in data-service/dg_identity.py (e.g. mint_identity,
//   resolve_native_id, bind_representation) — copy it, do not improvise a
//   weaker version for this file's executor.
//
// ============================================================================

// ---- Step 1: Rule ----
MERGE (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1200-GOLDEN'})
  SET rule.graph = 'Metagraph',
      rule.kind = 'Constraint',
      rule.RuleName = 'Golden fixture max building height',
      rule.RuleDescription = 'Maximum building height must not exceed 75 meters',
      rule.SWRL = 'Building(?b) ^ hasHeight(?b, ?h) ^ swrlb:greaterThan(?h, 75) -> Violation(?b)'
;

// ---- Step 2: Atoms (all four types, including ObjectPropertyAtom) ----
MERGE (a1:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A1', project: 'DG-1200-GOLDEN'})
  SET a1.graph = 'Metagraph', a1.type = 'ClassAtom', a1.SWRL_label = 'Building(?b)'
;

MERGE (a2:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A2', project: 'DG-1200-GOLDEN'})
  SET a2.graph = 'Metagraph', a2.type = 'DataPropertyAtom', a2.SWRL_label = 'hasHeight(?b, ?h)'
;

MERGE (a3:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A3', project: 'DG-1200-GOLDEN'})
  SET a3.graph = 'Metagraph', a3.type = 'BuiltinAtom', a3.SWRL_label = 'swrlb:greaterThan(?h, 75)'
;

// ObjectPropertyAtom is seeded at the data level like the other three; the C# leg's
// SwrlRuleParser.ResolveAtomType has no branch for it until Phase 1201 ALGN12-05 --
// see fixtures/golden/MANIFEST.md "Expected non-results by design".
MERGE (a4:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A4', project: 'DG-1200-GOLDEN'})
  SET a4.graph = 'Metagraph', a4.type = 'ObjectPropertyAtom', a4.SWRL_label = 'belongsToDistrict(?b, ?d)'
;

// ---- Step 3: Var and Literal nodes ----
MERGE (var_b:Var {name: '?b', project: 'DG-1200-GOLDEN'})
  SET var_b.graph = 'Metagraph'
;

MERGE (var_h:Var {name: '?h', project: 'DG-1200-GOLDEN'})
  SET var_h.graph = 'Metagraph'
;

MERGE (var_d:Var {name: '?d', project: 'DG-1200-GOLDEN'})
  SET var_d.graph = 'Metagraph'
;

MERGE (lit_75:Literal {lex: '75', project: 'DG-1200-GOLDEN'})
  SET lit_75.graph = 'Metagraph', lit_75.datatype = 'xsd:decimal'
;

// ---- Step 4: HAS_BODY / ARG relationships (body atoms fire on violation, per convention) ----
MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1200-GOLDEN'})
MATCH (a1:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A1', project: 'DG-1200-GOLDEN'})
MERGE (rule)-[:HAS_BODY {order: 1}]->(a1)
;

MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1200-GOLDEN'})
MATCH (a2:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A2', project: 'DG-1200-GOLDEN'})
MERGE (rule)-[:HAS_BODY {order: 2}]->(a2)
;

MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1200-GOLDEN'})
MATCH (a3:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A3', project: 'DG-1200-GOLDEN'})
MERGE (rule)-[:HAS_BODY {order: 3}]->(a3)
;

MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1200-GOLDEN'})
MATCH (a4:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A4', project: 'DG-1200-GOLDEN'})
MERGE (rule)-[:HAS_BODY {order: 4}]->(a4)
;

MATCH (a1:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A1', project: 'DG-1200-GOLDEN'})
MATCH (var_b:Var {name: '?b', project: 'DG-1200-GOLDEN'})
MERGE (a1)-[:ARG {pos: 1}]->(var_b)
;

MATCH (a2:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A2', project: 'DG-1200-GOLDEN'})
MATCH (var_b:Var {name: '?b', project: 'DG-1200-GOLDEN'})
MATCH (var_h:Var {name: '?h', project: 'DG-1200-GOLDEN'})
MERGE (a2)-[:ARG {pos: 1}]->(var_b)
MERGE (a2)-[:ARG {pos: 2}]->(var_h)
;

MATCH (a3:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A3', project: 'DG-1200-GOLDEN'})
MATCH (var_h:Var {name: '?h', project: 'DG-1200-GOLDEN'})
MATCH (lit_75:Literal {lex: '75', project: 'DG-1200-GOLDEN'})
MERGE (a3)-[:ARG {pos: 1}]->(var_h)
MERGE (a3)-[:ARG {pos: 2}]->(lit_75)
;

MATCH (a4:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A4', project: 'DG-1200-GOLDEN'})
MATCH (var_b:Var {name: '?b', project: 'DG-1200-GOLDEN'})
MATCH (var_d:Var {name: '?d', project: 'DG-1200-GOLDEN'})
MERGE (a4)-[:ARG {pos: 1}]->(var_b)
MERGE (a4)-[:ARG {pos: 2}]->(var_d)
;

// ---- Step 5: Objects (dgId, cgId, definitionId, REFERS_TO class) ----
MERGE (obj_pass:Object {cgId: 'cg:1:obj:01_Pass', definitionId: 'def-golden-01', project: 'DG-1200-GOLDEN'})
  SET obj_pass.graph = 'Computgraph',
      obj_pass.dgId = 'dg:3D5D98A2E0E663A8',
      obj_pass.objectName = 'Golden Building Pass',
      obj_pass.objectId = 'OBJ_GOLD_PASS',
      obj_pass.classIri = 'ex:Building',
      obj_pass.hasHeight = 42.0
;

MERGE (obj_fail:Object {cgId: 'cg:1:obj:02_Fail', definitionId: 'def-golden-01', project: 'DG-1200-GOLDEN'})
  SET obj_fail.graph = 'Computgraph',
      obj_fail.dgId = 'dg:6607D4A051F356F2',
      obj_fail.objectName = 'Golden Building Fail',
      obj_fail.objectId = 'OBJ_GOLD_FAIL',
      obj_fail.classIri = 'ex:Building',
      obj_fail.hasHeight = 88.5
;

// OBJ_GOLD_EMPTY is deliberately class ex:Site (not ex:Building) so the rule's
// ClassAtom never matches -- zero bindings, expected status no_population.
MERGE (obj_empty:Object {cgId: 'cg:1:obj:03_Empty', definitionId: 'def-golden-01', project: 'DG-1200-GOLDEN'})
  SET obj_empty.graph = 'Computgraph',
      obj_empty.dgId = 'dg:2602FCC98B32C2A2',
      obj_empty.objectName = 'Golden Non-Building Object',
      obj_empty.objectId = 'OBJ_GOLD_EMPTY',
      obj_empty.classIri = 'ex:Site'
;

MERGE (cls_building:Class {iri: 'ex:Building', project: 'DG-1200-GOLDEN'})
  SET cls_building.graph = 'OntoGraph', cls_building.label = 'Building'
;

MATCH (obj_pass:Object {cgId: 'cg:1:obj:01_Pass', definitionId: 'def-golden-01', project: 'DG-1200-GOLDEN'})
MATCH (cls_building:Class {iri: 'ex:Building', project: 'DG-1200-GOLDEN'})
MERGE (obj_pass)-[:REFERS_TO]->(cls_building)
;

MATCH (obj_fail:Object {cgId: 'cg:1:obj:02_Fail', definitionId: 'def-golden-01', project: 'DG-1200-GOLDEN'})
MATCH (cls_building:Class {iri: 'ex:Building', project: 'DG-1200-GOLDEN'})
MERGE (obj_fail)-[:REFERS_TO]->(cls_building)
;

// ---- Step 6: DesignState composition (all three kinds via HAS_STATE) ----
MERGE (ds:DesignState {StateId: 'DS_GOLDEN_FIXTURE_01', project: 'DG-1200-GOLDEN'})
  SET ds.graph = 'ValidGraph',
      ds.kind = 'DesignState',
      ds.statePayloadJson = '{"version":"2","stateId":"DS_GOLDEN_FIXTURE_01","capturedAtUtc":"2026-09-20T00:00:00Z","objStates":[{"stateId":"OS_GOLDEN_01"}],"paramStates":[{"stateId":"DS_GOLDEN_01"}],"propStates":[{"stateId":"PS_GOLDEN_01"}]}'
;

MERGE (os:DesignState {StateId: 'OS_GOLDEN_01', project: 'DG-1200-GOLDEN'})
  SET os.graph = 'ValidGraph', os.kind = 'ObjState', os.geometryRef = 'speckle:golden-fixture-box-01'
;

MERGE (paramState:DesignState {StateId: 'DS_GOLDEN_01', project: 'DG-1200-GOLDEN'})
  SET paramState.graph = 'ValidGraph', paramState.kind = 'ParamState'
;

MERGE (ps:DesignState {StateId: 'PS_GOLDEN_01', project: 'DG-1200-GOLDEN'})
  SET ps.graph = 'ValidGraph', ps.kind = 'PropState', ps.ruleId = 'R_GOLD_HEIGHT_MAX_75_V'
;

MATCH (ds:DesignState {StateId: 'DS_GOLDEN_FIXTURE_01', project: 'DG-1200-GOLDEN'})
MATCH (os:DesignState {StateId: 'OS_GOLDEN_01', project: 'DG-1200-GOLDEN'})
MATCH (paramState:DesignState {StateId: 'DS_GOLDEN_01', project: 'DG-1200-GOLDEN'})
MATCH (ps:DesignState {StateId: 'PS_GOLDEN_01', project: 'DG-1200-GOLDEN'})
MERGE (ds)-[:HAS_STATE]->(os)
MERGE (ds)-[:HAS_STATE]->(paramState)
MERGE (ds)-[:HAS_STATE]->(ps)
;

// ---- Step 7: Run node for the replay leg ----
// evidenceEnvelopeJson is deliberately left unset -- the DE-01 replay leg writes it;
// its absence must read as "not recorded" per D-08, never as an error.
// NOTE (spec/DATABASE.md label drift): the manual VALIDATOR path and this convention
// use :Run with Run_Id; auto-validation code separately writes :ValidationRun with
// runId. This seed follows the :Run/Run_Id convention deliberately -- the drift is a
// known, pre-existing, disclosed issue and is not fixed here.
MERGE (run:Run {Run_Id: 'RUN_GOLD_1200', project: 'DG-1200-GOLDEN'})
  SET run.graph = 'ValidGraph',
      run.ValidStatus = [true, false],
      run.SendStatus = false
;

// ============================================================================
// VERIFICATION (run after seeding):
//   MATCH (n {project:'DG-1200-GOLDEN'}) RETURN count(n) -- expect > 0
//   MATCH (n {project:'DG-1200-GOLDEN'}) RETURN count(n) -- after teardown, expect 0
// ============================================================================
