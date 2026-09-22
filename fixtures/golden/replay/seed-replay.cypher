// ============================================================================
// Seed: 1202 replay fixture — DE-01 live gap-1 closure (round-trippable payload)
// ============================================================================
//
// PURPOSE
//   Projects fixtures/golden/replay/mixed-verdicts.json into Neo4j under project
//   'DG-1202-REPLAY' so DE-01's persisted-replay leg has a REAL, round-trippable
//   Design State to re-derive a canonical status AND a canonical state hash from.
//   This closes VERIFICATION.md gap 1 (1202-08 plan): fixtures/golden/seed.cypher's
//   own :DesignState carries a stub statePayloadJson (bare stateId members, no
//   objectRef/capturedAtUtc — see that file's Step 6) that cannot round-trip
//   through DesignStatePayloadV2Serializer.Deserialize, so the retained DE-01
//   exit evidence always reported "Agreement: not_applicable". This file seeds
//   the SIBLING project 'DG-1202-REPLAY' with mixed-verdicts.json's full-member
//   statePayloadJson, which DOES round-trip.
//
//   This script NEVER writes to the frozen golden project (see
//   fixtures/golden/fixture.json / seed.cypher / MANIFEST.md's freeze policy,
//   project id 'DG-1200' + '-GOLDEN') — that project is untouched by this file.
//   Every clause below is scoped to project: 'DG-1202-REPLAY'.
//
// Phase 1203-02 note: the three obj_*.dgId literals below were re-derived to stay
// verbatim-identical with fixtures/golden/fixture.json's re-derived OBJ_GOLD_PASS/
// FAIL/EMPTY dgIds (D-09 length-prefix hash-input encoding). Pre-fix values were
// dg:57C65BE15E8E368B (pass), dg:729E143958721742 (fail), dg:0B23FFBDA52B73A6 (empty).
//
// EXECUTION METHOD
//   This script is for dev databases only. Run it as a single block in
//   Neo4j Browser (paste all + Ctrl+Enter). Each statement is separated
//   by a semicolon followed by a blank line — Neo4j Browser recognizes
//   this pattern as multi-statement input.
//
//   Alternatively:
//     cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/replay/seed-replay.cypher
//
//   Or via the running compose stack (matches this repo's project convention,
//   MSYS_NO_PATHCONV=1 needed on Git Bash for docker exec/cp path rewriting):
//     docker compose exec -T neo4j cypher-shell -u neo4j -p 12345678 -f /dev/stdin < fixtures/golden/replay/seed-replay.cypher
//
// WARNING — DEV DATABASES ONLY
// ============================================================================
//
// TEARDOWN (idempotent — run before re-seeding, or to remove the fixture entirely)
//   MATCH (n {project: 'DG-1202-REPLAY'}) DETACH DELETE n
//
// ============================================================================
//
// PARAMETERIZATION DISCIPLINE (T-1200-06, carried forward from seed.cypher)
//   This file is a static, checked-in, dev-only script with literal values —
//   matching fixtures/golden/seed.cypher's own precedent, not a parameterized
//   runtime query. ANY Python or C# code that *executes* this file — or that
//   reconstructs equivalent statements from fixture-derived values at runtime —
//   MUST pass those values as a parameter dict and MUST NEVER string-interpolate
//   them into query text. Copy the discipline already followed by every function
//   in data-service/dg_identity.py — do not improvise a weaker version here.
//
// ============================================================================

// ---- Step 1: Rule ----
MERGE (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1202-REPLAY'})
  SET rule.graph = 'Metagraph',
      rule.kind = 'Constraint',
      rule.RuleName = 'Golden fixture max building height',
      rule.RuleDescription = 'Maximum building height must not exceed 75 meters',
      rule.SWRL = 'Building(?b) ^ hasHeight(?b, ?h) ^ swrlb:greaterThan(?h, 75) -> Violation(?b)'
;

// ---- Step 2: Atoms (all four types, including ObjectPropertyAtom) ----
MERGE (a1:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A1', project: 'DG-1202-REPLAY'})
  SET a1.graph = 'Metagraph', a1.type = 'ClassAtom', a1.SWRL_label = 'Building(?b)'
;

MERGE (a2:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A2', project: 'DG-1202-REPLAY'})
  SET a2.graph = 'Metagraph', a2.type = 'DataPropertyAtom', a2.SWRL_label = 'hasHeight(?b, ?h)'
;

MERGE (a3:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A3', project: 'DG-1202-REPLAY'})
  SET a3.graph = 'Metagraph', a3.type = 'BuiltinAtom', a3.SWRL_label = 'swrlb:greaterThan(?h, 75)'
;

// ObjectPropertyAtom is seeded at the data level like the other three; the C# leg's
// SwrlRuleParser.ResolveAtomType has no branch for it until Phase 1201 ALGN12-05 --
// see fixtures/golden/MANIFEST.md "Expected non-results by design" (same note as
// fixtures/golden/seed.cypher's own Step 2).
MERGE (a4:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A4', project: 'DG-1202-REPLAY'})
  SET a4.graph = 'Metagraph', a4.type = 'ObjectPropertyAtom', a4.SWRL_label = 'belongsToDistrict(?b, ?d)'
;

// ---- Step 3: Var and Literal nodes ----
MERGE (var_b:Var {name: '?b', project: 'DG-1202-REPLAY'})
  SET var_b.graph = 'Metagraph'
;

MERGE (var_h:Var {name: '?h', project: 'DG-1202-REPLAY'})
  SET var_h.graph = 'Metagraph'
;

MERGE (var_d:Var {name: '?d', project: 'DG-1202-REPLAY'})
  SET var_d.graph = 'Metagraph'
;

MERGE (lit_75:Literal {lex: '75', project: 'DG-1202-REPLAY'})
  SET lit_75.graph = 'Metagraph', lit_75.datatype = 'xsd:decimal'
;

// ---- Step 4: HAS_BODY / ARG relationships (body atoms fire on violation, per convention) ----
MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1202-REPLAY'})
MATCH (a1:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A1', project: 'DG-1202-REPLAY'})
MERGE (rule)-[:HAS_BODY {order: 1}]->(a1)
;

MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1202-REPLAY'})
MATCH (a2:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A2', project: 'DG-1202-REPLAY'})
MERGE (rule)-[:HAS_BODY {order: 2}]->(a2)
;

MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1202-REPLAY'})
MATCH (a3:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A3', project: 'DG-1202-REPLAY'})
MERGE (rule)-[:HAS_BODY {order: 3}]->(a3)
;

MATCH (rule:Rule {Rule_Id: 'R_GOLD_HEIGHT_MAX_75_V', project: 'DG-1202-REPLAY'})
MATCH (a4:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A4', project: 'DG-1202-REPLAY'})
MERGE (rule)-[:HAS_BODY {order: 4}]->(a4)
;

MATCH (a1:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A1', project: 'DG-1202-REPLAY'})
MATCH (var_b:Var {name: '?b', project: 'DG-1202-REPLAY'})
MERGE (a1)-[:ARG {pos: 1}]->(var_b)
;

MATCH (a2:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A2', project: 'DG-1202-REPLAY'})
MATCH (var_b:Var {name: '?b', project: 'DG-1202-REPLAY'})
MATCH (var_h:Var {name: '?h', project: 'DG-1202-REPLAY'})
MERGE (a2)-[:ARG {pos: 1}]->(var_b)
MERGE (a2)-[:ARG {pos: 2}]->(var_h)
;

MATCH (a3:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A3', project: 'DG-1202-REPLAY'})
MATCH (var_h:Var {name: '?h', project: 'DG-1202-REPLAY'})
MATCH (lit_75:Literal {lex: '75', project: 'DG-1202-REPLAY'})
MERGE (a3)-[:ARG {pos: 1}]->(var_h)
MERGE (a3)-[:ARG {pos: 2}]->(lit_75)
;

MATCH (a4:Atom {Atom_Id: 'R_GOLD_HEIGHT_MAX_75_V_A4', project: 'DG-1202-REPLAY'})
MATCH (var_b:Var {name: '?b', project: 'DG-1202-REPLAY'})
MATCH (var_d:Var {name: '?d', project: 'DG-1202-REPLAY'})
MERGE (a4)-[:ARG {pos: 1}]->(var_b)
MERGE (a4)-[:ARG {pos: 2}]->(var_d)
;

// ---- Step 5: Objects (dgId, cgId, definitionId, REFERS_TO class) ----
MERGE (obj_pass:Object {cgId: 'cg:1:obj:01_Pass', definitionId: 'def-replay-1202-01', project: 'DG-1202-REPLAY'})
  SET obj_pass.graph = 'Computgraph',
      obj_pass.dgId = 'dg:3D5D98A2E0E663A8',
      obj_pass.objectName = 'Golden Building Pass',
      obj_pass.objectId = 'OBJ_GOLD_PASS',
      obj_pass.classIri = 'ex:Building',
      obj_pass.hasHeight = 42.0
;

MERGE (obj_fail:Object {cgId: 'cg:1:obj:02_Fail', definitionId: 'def-replay-1202-01', project: 'DG-1202-REPLAY'})
  SET obj_fail.graph = 'Computgraph',
      obj_fail.dgId = 'dg:6607D4A051F356F2',
      obj_fail.objectName = 'Golden Building Fail',
      obj_fail.objectId = 'OBJ_GOLD_FAIL',
      obj_fail.classIri = 'ex:Building',
      obj_fail.hasHeight = 88.5
;

// OBJ_GOLD_EMPTY is deliberately class ex:Site (not ex:Building) so the rule's
// ClassAtom never matches -- zero bindings, expected status no_population.
MERGE (obj_empty:Object {cgId: 'cg:1:obj:03_Empty', definitionId: 'def-replay-1202-01', project: 'DG-1202-REPLAY'})
  SET obj_empty.graph = 'Computgraph',
      obj_empty.dgId = 'dg:2602FCC98B32C2A2',
      obj_empty.objectName = 'Golden Non-Building Object',
      obj_empty.objectId = 'OBJ_GOLD_EMPTY',
      obj_empty.classIri = 'ex:Site'
;

MERGE (cls_building:Class {iri: 'ex:Building', project: 'DG-1202-REPLAY'})
  SET cls_building.graph = 'OntoGraph', cls_building.label = 'Building'
;

MATCH (obj_pass:Object {cgId: 'cg:1:obj:01_Pass', definitionId: 'def-replay-1202-01', project: 'DG-1202-REPLAY'})
MATCH (cls_building:Class {iri: 'ex:Building', project: 'DG-1202-REPLAY'})
MERGE (obj_pass)-[:REFERS_TO]->(cls_building)
;

MATCH (obj_fail:Object {cgId: 'cg:1:obj:02_Fail', definitionId: 'def-replay-1202-01', project: 'DG-1202-REPLAY'})
MATCH (cls_building:Class {iri: 'ex:Building', project: 'DG-1202-REPLAY'})
MERGE (obj_fail)-[:REFERS_TO]->(cls_building)
;

// ---- Step 6: DesignState composition — THE ROUND-TRIPPABLE PAYLOAD ----
// Unlike fixtures/golden/seed.cypher's stub (bare stateId members only), this
// statePayloadJson is copied VERBATIM from mixed-verdicts.json -- full
// objectRef/capturedAtUtc/classIri members on every ObjState, so
// DesignStatePayloadV2Serializer.Deserialize (C#) and the Python view path both
// round-trip it cleanly. This is the fix for gap 1: a live run against this seed
// can compute a real canonical state hash instead of failing to deserialize.
MERGE (ds:DesignState {StateId: 'DS_1202_MIXED_REPLAY_01', project: 'DG-1202-REPLAY'})
  SET ds.graph = 'ValidGraph',
      ds.kind = 'DesignState',
      ds.statePayloadJson = '{"version":"2","stateId":"DS_1202_MIXED_REPLAY_01","label":"1202 mixed pass/fail replay","capturedAtUtc":"2026-09-21T12:00:00.0000000Z","objStates":[{"stateId":"OS_1202_C_EMPTY","objectRef":"OBJ_GOLD_EMPTY","label":"Golden Non-Building Object","classIri":"ex:Site","capturedAtUtc":"2026-09-21T12:00:02.0000000Z"},{"stateId":"OS_1202_A_PASS","objectRef":"OBJ_GOLD_PASS","label":"Golden Building Pass","classIri":"ex:Building","capturedAtUtc":"2026-09-21T12:00:00.0000000Z"},{"stateId":"OS_1202_B_FAIL","objectRef":"OBJ_GOLD_FAIL","label":"Golden Building Fail","classIri":"ex:Building","capturedAtUtc":"2026-09-21T12:00:01.0000000Z"}],"paramStates":[{"stateId":"DS_1202_MIXED_PARAMS_01","capturedAtUtc":"2026-09-21T12:00:03.0000000Z","parameters":[{"parameterId":"HeightSlider","displayName":"Height Slider","type":"number","value":42.0}]}],"propStates":[{"stateId":"PS_1202_MIXED_HEIGHT_01","ruleIri":"R_GOLD_HEIGHT_MAX_75_V","dataPropertyIri":"ex:hasHeight","objectRef":"OBJ_GOLD_PASS","propValue":{"parameterId":"hasHeight","displayName":"Has Height","type":"number","value":42.0}}]}'
;

MERGE (os_empty:DesignState {StateId: 'OS_1202_C_EMPTY', project: 'DG-1202-REPLAY'})
  SET os_empty.graph = 'ValidGraph', os_empty.kind = 'ObjState', os_empty.objectRef = 'OBJ_GOLD_EMPTY'
;

MERGE (os_pass:DesignState {StateId: 'OS_1202_A_PASS', project: 'DG-1202-REPLAY'})
  SET os_pass.graph = 'ValidGraph', os_pass.kind = 'ObjState', os_pass.objectRef = 'OBJ_GOLD_PASS'
;

MERGE (os_fail:DesignState {StateId: 'OS_1202_B_FAIL', project: 'DG-1202-REPLAY'})
  SET os_fail.graph = 'ValidGraph', os_fail.kind = 'ObjState', os_fail.objectRef = 'OBJ_GOLD_FAIL'
;

MERGE (paramState:DesignState {StateId: 'DS_1202_MIXED_PARAMS_01', project: 'DG-1202-REPLAY'})
  SET paramState.graph = 'ValidGraph', paramState.kind = 'ParamState'
;

MERGE (ps:DesignState {StateId: 'PS_1202_MIXED_HEIGHT_01', project: 'DG-1202-REPLAY'})
  SET ps.graph = 'ValidGraph', ps.kind = 'PropState', ps.ruleId = 'R_GOLD_HEIGHT_MAX_75_V'
;

MATCH (ds:DesignState {StateId: 'DS_1202_MIXED_REPLAY_01', project: 'DG-1202-REPLAY'})
MATCH (os_empty:DesignState {StateId: 'OS_1202_C_EMPTY', project: 'DG-1202-REPLAY'})
MATCH (os_pass:DesignState {StateId: 'OS_1202_A_PASS', project: 'DG-1202-REPLAY'})
MATCH (os_fail:DesignState {StateId: 'OS_1202_B_FAIL', project: 'DG-1202-REPLAY'})
MATCH (paramState:DesignState {StateId: 'DS_1202_MIXED_PARAMS_01', project: 'DG-1202-REPLAY'})
MATCH (ps:DesignState {StateId: 'PS_1202_MIXED_HEIGHT_01', project: 'DG-1202-REPLAY'})
MERGE (ds)-[:HAS_STATE]->(os_empty)
MERGE (ds)-[:HAS_STATE]->(os_pass)
MERGE (ds)-[:HAS_STATE]->(os_fail)
MERGE (ds)-[:HAS_STATE]->(paramState)
MERGE (ds)-[:HAS_STATE]->(ps)
;

// ---- Step 7: Run node for the replay leg ----
// evidenceEnvelopeJson is set here (unlike seed.cypher's Step 7, which leaves it
// unset for the DE-01 replay leg to write) -- mixed-verdicts.json already carries
// a contract-valid envelope whose three rows produce exactly its own
// expectedPerObjectVerdicts, so seeding it directly gives the replay leg
// per-object rows without requiring a prior /validation/publish call.
// NOTE (spec/DATABASE.md label drift, same convention as seed.cypher's Step 7):
// the manual VALIDATOR path and this convention use :Run with Run_Id; auto-
// validation code separately writes :ValidationRun with runId. This seed follows
// the :Run/Run_Id convention deliberately -- the drift is a known, pre-existing,
// disclosed issue and is not fixed here.
MERGE (run:Run {Run_Id: 'RUN_1202_REPLAY', project: 'DG-1202-REPLAY'})
  SET run.graph = 'ValidGraph',
      run.ValidStatus = [true, false, false],
      run.SendStatus = false,
      run.evidenceEnvelopeJson = '{"contractVersion":"1","canonicalizationVersion":1,"project":"DG-1202-REPLAY","definitionId":"R_GOLD_HEIGHT_MAX_75_V","serviceName":"fixtures.golden.replay","serviceVersion":"1.0.0","emittedAt":"2026-09-21T12:00:04.0000000Z","stage":"validation.publish","canonicalStatus":"failed","rows":[{"ruleId":"R_GOLD_HEIGHT_MAX_75_V","objectId":"OBJ_GOLD_PASS","canonicalStatus":"passed"},{"ruleId":"R_GOLD_HEIGHT_MAX_75_V","objectId":"OBJ_GOLD_FAIL","canonicalStatus":"failed"},{"ruleId":"R_GOLD_HEIGHT_MAX_75_V","objectId":"OBJ_GOLD_EMPTY","canonicalStatus":"no_population"}]}'
;

// ============================================================================
// VERIFICATION (run after seeding):
//   MATCH (n {project:'DG-1202-REPLAY'}) RETURN count(n) -- expect > 0
//   MATCH (d:DesignState {StateId:'DS_1202_MIXED_REPLAY_01', project:'DG-1202-REPLAY'})
//     RETURN d.statePayloadJson IS NOT NULL AS hasPayload,
//            d.statePayloadJson CONTAINS 'capturedAtUtc' AS roundTrippable
//   -- both columns must be TRUE (this is the round-trip proof, unlike
//   -- seed.cypher's stub payload which fails this check by design)
//   MATCH (n {project:'DG-1202-REPLAY'}) DETACH DELETE n -- teardown, then re-run
//   the first query above -- expect 0
//
// This script never targets the frozen golden project -- confirm with the
// acceptance greps documented in the plan (project id spelled out there, not
// repeated here, so a grep for the frozen project's literal id against this
// file itself returns zero):
//   fixtures/golden/replay/seed-replay.cypher must contain zero occurrences of
//   the frozen golden project id, and at least 5 occurrences of 'DG-1202-REPLAY'.
// ============================================================================
