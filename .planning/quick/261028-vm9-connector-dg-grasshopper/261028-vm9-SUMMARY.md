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

## Deployment to localhost — 2026-10-28

- Backend: the running `data-service` was `dg-remember-backend:07dd8a9`, a thin layer over the mapping release
  image, so the repository's `app.py` (no mapping code) could not be copied in. The live `app.py` and
  `route_policy.py` were extracted from the container, only this task's hunks applied, and `connector_graph.py`
  added: `dg-connector-backend:vm9` (`FROM dg-remember-backend:07dd8a9`, three files). Recreated only
  `data-service` with the existing four Compose files plus `C:\Users\Admin\dgb-vm9\compose.connector.yml`; every
  other container id unchanged. Rollback: `dg-remember-backend:rollback-vm9` (= 07dd8a9).
- Plugin: the net48 Release build copied to `%APPDATA%\Grasshopper\Libraries\DG` (Rhino not running). Previous
  files backed up to `%LOCALAPPDATA%\DG\connector-backups\grasshopper\20261028T230549Z`. DG.gha, DG.Core.dll and
  DG.Grasshopper.dll are byte-identical to the build output and contain the new code.

## Live verification (localhost, real data)

- All eight read queries answer 200 for project `v12-hexagonal-facade-01` (13 rules, 93 atom rows, 8 classes,
  45 runs); `evidence` without a run id 422; another project 403; a revoked session 401; heartbeat 200.
- The real `DG.Core` client (not a mock) over `http://localhost:8000` with a temporary connector session: probe
  "Connected (DG server)", 13 rules with 54 atoms and 27 variables, 8 objects, 8 classes, 45 runs, 5 states,
  100 per-object verdicts for a run. The temporary sessions were revoked (204).
- `objProperties` and `dataProperties` return 0 rows. The statements use labels `ObjProperty`/`DataProperty`,
  while the schema names `ObjectProperty`/`DatatypeProperty`. This was already so in the Bolt repository and is
  copied unchanged; not fixed here.

## Open

- Not exercised in a running Grasshopper/Rhino: the Server input on the canvas, sign-in with a password, VALIDATOR
  publishing. The localhost stack runs the `local` profile, so the plugin still reads Bolt there; server mode is
  used for a non-loopback Server value or a `multi-user` server.
- The stand (`https://dg.173-249-46-99.nip.io`, `/opt/dg`) has not been updated: it needs the same three-file
  layer on its backend image. Without it CONNECTOR reports "The DG server has no /connector-graph route".
- The DeGram Connectors tab bundle still carries the previous plugin until `stage_connector_payloads.py` is run
  for the next DeGram build (owner's build step).
- `Neo4jPredicateKindResolver` and `ValidationRunsQueryService` are unused by any component and still Bolt-only.
