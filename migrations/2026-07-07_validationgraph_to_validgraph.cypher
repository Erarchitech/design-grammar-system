// PENDING MIGRATION — requires user approval before running against live Neo4j.
//
// Why: all v2.0-era validation data (20 ValidationRun + 1148 ValidationEntity +
// 1 IntegrationConfig nodes, project "TestA") carries graph:'ValidationGraph',
// but schema v4 (training/dataset_schema.json, spec/DATABASE.md) and the current
// data-service (app.py VALIDATION_GRAPH = "ValidGraph") use graph:'ValidGraph'.
// Until this runs, /data-service/validation/* endpoints return zero runs for
// that legacy data — in the V2 UI and in the legacy Model Viewer alike.
//
// Discovered during v8.0 Phase 23/24 live verification (2026-07-07).
// Apply with:
//   curl -s -X POST http://localhost:8080/neo4j/db/neo4j/tx/commit \
//     -H "Content-Type: application/json" -u neo4j:12345678 \
//     -d '{"statements":[{"statement":"MATCH (n) WHERE n.graph = '\''ValidationGraph'\'' SET n.graph = '\''ValidGraph'\'' RETURN count(n)"}]}'

MATCH (n) WHERE n.graph = 'ValidationGraph'
SET n.graph = 'ValidGraph'
RETURN count(n) AS migrated;
