---
phase: quick-261028-vm9
plan: 01
status: complete
date: 2026-10-28
---

# Grasshopper CONNECTOR connects to a DG server

Built and tested offline. **Not exercised against a real Grasshopper/Rhino or a deployed server**: no live
sign-in, no canvas run, no rebuilt service image. See "Open" below.

## Delivered

- **Server:** `GET /connector-graph/{project}/{query_id}` (`data-service/connector_graph.py`, `app.py`). Policy
  `connector`, source `path`, viewer; another project answers 403 `PROJECT_FORBIDDEN`, an unknown query 404
  `GRAPH_QUERY_NOT_FOUND`, `evidence` without `?runId=` 422 `RUN_ID_REQUIRED`. Statements are fixed, read-only
  and take the project as a bound parameter only.
- **Spec:** `spec/SECURITY-BOUNDARY.md` (route-policy block, principal scope, a "Graph read over HTTPS" bullet),
  `spec/GRASSHOPPER.md` (CONNECTOR ports and server mode). Route-policy size pin 135 -> 136.
- **DG.Core:** `GraphQuerySession` (Bolt or HTTPS), `ConnectionInfo.GraphApiUrl/GraphApiToken`, the three
  repositories read through it, server-mode probe in `Neo4jConnectorService`, `NormalizeServerUrl` and
  `IsRemoteServer` in `DataServiceRequestAuth`.
- **CONNECTOR:** new optional input `Server` (index 5, appended so existing canvases keep their wiring) and output
  `Server` (index 8) to wire into the `DataServiceUrl` of VALIDATOR and COMPUTGRAPH PUBLISH. Server mode when the
  server hands out no Neo4j bundle or is not loopback. Plain http to a remote host is refused. Sign-out uses the
  server the session was minted on.

## Verified

- Python: 1208 passed (`test_connector_graph.py` 9 new, plus route inventory and the spec drift test).
- C#: 874 passed, 4 failed. The 4 are `DesignStateValidationFlowTests` (live Neo4j required, known baseline). 17
  new tests in `GraphApiReadTests` run the real HTTP path against a loopback `HttpListener`: Bearer header, escaped
  project and run id, row mapping of rules/atoms/ontology/runs/evidence, probe, token never in a message.
- `dotnet build DG/DG.sln -c Release`: 0 errors (net7.0, net9.0, net48 for DG.Core).

## Open

- The data-service image must be rebuilt and recreated for the route to exist on the stand/localhost
  (see `stale-docker-images-mask-code-state`). Until then CONNECTOR in server mode reports "The DG server has no
  /connector-graph route. Update the server."
- The plugin must be rebuilt and re-staged for the DeGram Connectors tab (`stage_connector_payloads.py`) before
  users get the `Server` input. Not done here.
- Live check on the stand: sign in with a non-admin account in a multi-user profile, `Server` = the stand's
  https address, then METAGRAPH, ONTOGRAPH and VALIDATION GRAPH read and VALIDATOR publishes.
- `Neo4jPredicateKindResolver` and `ValidationRunsQueryService` are unused by any component and still Bolt-only.
