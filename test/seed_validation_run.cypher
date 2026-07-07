// Seed fixture: one schema-v4 validation run for UI smoke testing.
// Project "v8-ui-smoke" — additive test data, safe to delete:
//   MATCH (n {project:'v8-ui-smoke'}) DETACH DELETE n
//
// Creates: 1 ValidationRun + 8 ValidationEntity (ValidGraph),
// 1 Rule with SWRL (Metagraph) so the V2 Model Viewer rule panel resolves.

MERGE (r:Rule {Rule_Id: 'R_URB_HEIGHT_MAX_75_V', project: 'v8-ui-smoke'})
SET r.graph = 'Metagraph',
    r.RuleName = 'Max building height',
    r.RuleDescription = 'Maximum building height must not exceed 75 meters',
    r.SWRL = 'Building(?b) ^ hasHeight(?b, ?h) ^ swrlb:greaterThan(?h, 75) -> Violation(?b)',
    r.kind = 'SWRL rule';

MERGE (run:ValidationRun {runId: 'v8smoke-run-001', project: 'v8-ui-smoke'})
SET run.graph = 'ValidGraph',
    run.createdAt = '2026-07-07T12:00:00+00:00',
    run.ValidStatus = [false, true, true, false, true, true, false, true],
    run.SendStatus = true,
    run.rulesJson = '[{"ruleId":"R_URB_HEIGHT_MAX_75_V","ruleName":"Max building height","ruleDescription":"Maximum building height must not exceed 75 meters","passed":false}]',
    run.statePayloadJson = '{"version":"2","stateId":"DS_V8SMOKE01","capturedAtUtc":"2026-07-07T11:58:00Z","objStates":[{"stateId":"OS_A1"},{"stateId":"OS_A2"}],"paramStates":[{"stateId":"DS_P1"}],"propStates":[{"stateId":"PS_Q1"}]}';

WITH 1 AS _
UNWIND [
  ['building1', 'passed'], ['building2', 'failed'], ['building3', 'passed'],
  ['building4', 'failed'], ['building5', 'passed'], ['building6', 'passed'],
  ['building7', 'failed'], ['building8', 'passed']
] AS row
MERGE (ve:ValidationEntity {dgEntityId: row[0], runId: 'v8smoke-run-001', project: 'v8-ui-smoke'})
SET ve.graph = 'ValidGraph',
    ve.displayName = row[0],
    ve.status = row[1],
    ve.ruleId = 'R_URB_HEIGHT_MAX_75_V'
WITH ve
MATCH (run:ValidationRun {runId: 'v8smoke-run-001', project: 'v8-ui-smoke'})
MERGE (run)-[:HAS_ENTITY]->(ve);
