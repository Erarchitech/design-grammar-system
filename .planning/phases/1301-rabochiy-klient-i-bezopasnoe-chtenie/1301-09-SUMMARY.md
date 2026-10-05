---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 09
subsystem: data-service-speckle-proxy
tags: [speckle, geometry-proxy, token-removal, d-21, route-policy, nginx, objectloader2, tdd]
requires: [1301-08]
provides:
  - "data-service/speckle_proxy.py: resolve_view_resources (server-side model/version to root-object resolution with the read token, returns DG-proxy URLs) and proxy_objects (bound-project object streaming, fixed upstream paths, hash-validated ids, named errors)"
  - "/validation/view payload: viewerResources (list of /data-service/speckle-proxy/{project}/objects/{speckleProjectId}/{objectId}) plus optional viewerResourcesError; readToken and speckleBaseUrl removed"
  - "Four proxy routes (member viewer + delegated, source path): GET objects/{spid}/{oid}, GET objects/{spid}/{oid}/single, POST api/getobjects/{spid}, POST api/v2/projects/{spid}/object-stream/"
  - "Error codes SPECKLE_PROJECT_FORBIDDEN (403), SPECKLE_PROJECT_UNBOUND (404), SPECKLE_UPSTREAM_ERROR (502), SPECKLE_OBJECT_ID_INVALID (422), SPECKLE_BODY_TOO_LARGE (413), SPECKLE_NOT_CONFIGURED (503)"
  - "ui-v2/src/lib/speckleProxy.js: parseViewerResource, speckleProxyFetch, createProxyObjectLoader; SpeckleViewport loads through a ProxySpeckleLoader with no token argument"
  - "nginx location /data-service/speckle-proxy/ (no buffering, 4m body, inherited security headers); SECURITY-BOUNDARY section 3.7; API.md proxy section"
affects: [1301-10, 1301-12, 1301-13, 1301-14]
tech-stack:
  added: ["@speckle/objectloader2 as a direct ui-v2 dependency (already installed at 2.31.14 as the viewer's own dependency; package.json + package-lock root entry only, no install)"]
  patterns:
    - "Module-level _transport_factory seam (same as degram_relay): tests inject httpx.MockTransport, production passes None; one MockTransport serves both the sync resolver and the async proxy"
    - "Subclass SpeckleLoader and override only initObjectLoader so the stock viewer pipeline is kept while the object loader targets the DG proxy with a cookie-credentialed fetch and no cache"
key-files:
  created:
    - data-service/speckle_proxy.py
    - data-service/tests/test_speckle_proxy.py
    - ui-v2/src/lib/speckleProxy.js
    - ui-v2/tests/speckle-proxy.test.mjs
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-09-SUMMARY.md
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_review_fix_1205.py
    - data-service/tests/test_evidence_versions.py
    - data-service/tests/test_static_proxy_boundary.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - ui-v2/src/components/speckle/SpeckleViewport.jsx
    - ui-v2/src/screens/ModelScreen.jsx
    - ui-v2/src/lib/modelApi.js
    - ui-v2/src/lib/apiClient.js
    - ui-v2/src/screens/apidocs/content/06-validation-publish-api.js
    - ui-v2/nginx.conf
    - ui-v2/package.json
    - ui-v2/package-lock.json
    - test/smoke_e2e.sh
key-decisions:
  - "The proxy routes follow what @speckle/objectloader2 2.31.14 actually requests (GET /objects/{p}/{o}/single and POST /api/v2/projects/{p}/object-stream/), not only the two shapes the plan named; the plan's two shapes (GET /objects/{p}/{o}, POST /api/getobjects/{p}) are kept as aliases served by the same handlers"
  - "viewerResources is a list of DG-origin URLs the server resolved; the browser does no Speckle GraphQL (UrlHelper.getResourceUrls is gone) and never sees the Speckle host"
  - "Resolution runs only for interactive callers (user, delegated); a connector or unknown caller gets []. A run whose speckleProjectId differs from the DG project's bound id resolves nothing (SPECKLE_PROJECT_FORBIDDEN) so the viewer never receives a URL the proxy would refuse"
  - "The browser loader runs with its IndexedDB cache off so project geometry does not outlive the DG session on the device"
  - "Upstream non-200 and transport errors all map to 502 SPECKLE_UPSTREAM_ERROR with a fixed message; the upstream body is never echoed and redirects are never followed"
metrics:
  duration: ~80 min
  completed: 2026-10-05
requirements-completed: []
requirements-partial: [DGCL-03, DGCL-05]  # DGCL-03: the token half (no Speckle credential in any browser path) is done; the isolated embedded DG web surface is plans 12/13. DGCL-05: proxy routes admit member viewer and the delegated principal only and logout/revoke stops object reads; the rest of the surface belongs to later plans
status: complete
---

# Phase 1301 Plan 09: Speckle geometry proxy Summary

The Speckle read token, one credential for the whole Speckle server, no longer exists in any browser path: `/validation/view` returns server-resolved DG-proxy object URLs instead, and the Model Viewer loads geometry through project-authorised `/data-service/speckle-proxy/` routes that serve only the Speckle project bound to the caller's DG project.

## What was built

**Task 1 (commit `4c2c96d`) tracer.** `speckle_proxy.py` does the model/version to root-object resolution the viewer's `UrlHelper` used to do in the browser, server side with the read token (`resolve_view_resources`, sync `httpx.Client`, GraphQL `project.model.version.referencedObject`), and rewrites each root object to `{prefix}/speckle-proxy/{project}/objects/{speckleProjectId}/{objectId}` (prefix `DG_DATA_SERVICE_PUBLIC_PREFIX`, default `/data-service`). `proxy_objects` streams the object endpoints with an async client. Check order, all before Speckle is contacted: no binding 404 `SPECKLE_PROJECT_UNBOUND`, requested Speckle project not equal to the bound one 403 `SPECKLE_PROJECT_FORBIDDEN`, object id not `^[0-9a-f]{32}$` or a bad body 422 `SPECKLE_OBJECT_ID_INVALID`, body over 4 MiB 413, read token unset 503 `SPECKLE_NOT_CONFIGURED`. Upstream paths are fixed templates, the caller's Cookie/Authorization/CSRF headers are never forwarded, redirects are not followed, any upstream failure is 502 `SPECKLE_UPSTREAM_ERROR` with a fixed message, and the stream is closed in a shielded `finally`. `build_view_payload` lost `readToken` and `speckleBaseUrl` and gained `viewerResources` (and `viewerResourcesError` when resolution fails). Four route-policy rows (`member`+`delegated`, path, viewer); table size 92 to 96. SECURITY-BOUNDARY gets a new section 3.7, four route-policy block rows, the browser trust-zone note and the delegated route scope; API.md gets the proxy section.

**Task 2 (commit `306b3a8`) viewer.** `speckleProxy.js` holds `parseViewerResource` (accepts only same-origin `.../speckle-proxy/{project}/objects/{spid}/{hash}`; refuses absolute and protocol-relative URLs, Speckle viewer URLs, dot segments, queries, fragments), `speckleProxyFetch` (credentialed same-origin fetch; strips Authorization/Cookie headers; CSRF marker on POST only; refuses any URL not under `/speckle-proxy/` before calling fetch) and `createProxyObjectLoader` (the real `ObjectLoader2` with the proxy prefix as server URL, no token, cache off). `SpeckleViewport` subclasses `SpeckleLoader` overriding only `initObjectLoader`, drops `UrlHelper`/`readToken`; `ModelScreen` consumes `viewerResources`; no visible UI change (the degraded synthetic-massing fallback triggers exactly when there are no resources, as it did with no token). nginx gets a streaming location for `/data-service/speckle-proxy/` (HTTP/1.1, `proxy_buffering off`, `proxy_read_timeout 90s` above the proxy's 60 s read limit, `client_max_body_size 4m`, no `add_header`, no Speckle upstream).

## TDD

RED observed before implementation: `test_speckle_proxy.py` stopped at collection with `ModuleNotFoundError: No module named 'speckle_proxy'`; the route-inventory table size, the six spec-block tests, three 1205 CR-01 tests and four evidence-wire tests failed after the routes and payload changed until the specs and tests were updated; `speckle-proxy.test.mjs` failed on the missing `speckleProxy.js` module, then four source/bundle-scan tests failed until the viewer was switched; six nginx boundary tests failed before the location existed. GREEN afterwards. Each task is one commit (tests plus implementation).

## Verification (host, Python 3.14.2, Node 20.20; no Docker, no live Speckle, no live DB)

- Task 1 gate: `test_speckle_proxy.py` (58) + route inventory + boundary spec + 1205 review fixes + evidence versions + static proxy boundary: **1140 passed, 1 skipped**.
- Neighbours (cross-project matrix, delegated token, degram relay and policy, config.js no secrets, compose boundary, GH publish wire, SHACL proxy, run immutability, auth tracer): **1303 passed**. `tools/security/tests` + `tools/de01/tests`: 223 passed, 1 failed (see below).
- Frontend: `node --test tests/speckle-proxy.test.mjs tests/api-security.test.mjs tests/auth-security.test.mjs` **191 passed, 0 failed** (27 new). `npm --prefix ui-v2 run build` **exit 0**. After the build the bundle-scan test runs (not skipped): no `readToken` anywhere in `dist`. `node ui-v2/tests/run-degram.mjs` (offline headless Chrome against a file bundle, no server): **22 passed, 0 failed**; its evidence file was a scratch label and was deleted.
- Full data-service suite `python -m pytest data-service/tests -q`: **4804 passed, 35 skipped, 8 deselected, 6 failed, 25 errors** (254 s). The 31 are the known environmental set, unchanged from plan 08: 25 errors in `test_cg_structure_checks.py` / `test_computgraph_consult.py` and 4 failures in `test_dg_context.py` (the `neo4j` hostname does not resolve from the host), 2 failures in `recognition_eval/test_repeat_sweep.py` (missing 1204 report). Passed count grew by 165 over plan 08's 4639 (new proxy tests plus the per-row route-inventory sweeps over four new rows).
- `tools/de01/tests/test_de01_runner.py::test_de01_runner_against_golden_fixture_has_zero_silent_disagreements` fails: the runner reaches `localhost:8000`/`8001` and the data-service, dg-reasoner and replay legs report `connection error: timed out`. Environmental (needs the live stack), not caused by this plan; the file also carries foreign uncommitted edits.

How "no token in any browser path" is proved: a recursive key scan of the `/validation/view` payload (no key containing `token`, no `speckleBaseUrl`, no read or write token value, no Speckle host) for the three view routes and for `build_view_payload` directly; a source check on `build_view_payload`; the Speckle read token never in any proxy response body or header or log line (caplog) including every error path; upstream requests carry only the server-held Bearer and none of the caller's headers; in the browser, a real `ObjectLoader2` driven against a fake fetch shows exactly the two proxy URL shapes, `credentials: include`, no Authorization/Cookie header, CSRF only on the POST, and a synthetic token placed in `window.GRAPH_CONFIG` never appears in any request; source scans of `SpeckleViewport.jsx`, `ModelScreen.jsx`, `modelApi.js`, every file under `ui-v2/src`, `gen-config.sh`/`entrypoint.sh` and the built `dist` bundle and `config.js`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in the plan's assumption A5] The installed loader does not use the paths the plan named.** `@speckle/objectloader2` 2.31.14 requests `GET {server}/objects/{project}/{object}/single` and `POST {server}/api/v2/projects/{project}/object-stream/` (confirmed by reading `serverDownloader.js` and by driving the real loader against a fake fetch), not `objects/{p}/{o}` and `api/getobjects/{p}`. A proxy with only the plan's two routes would have served nothing to the viewer. Fix: four routes (the loader's two plus the plan's two as aliases on the same handlers), four policy rows, all documented. Files: `app.py`, `route_policy.py`, `speckle_proxy.py`, `spec/*`. Commit `4c2c96d`.

**2. [Rule 1 - Bug] The stock `SpeckleLoader` cannot be pointed at a path prefix and always takes a token.** It keeps only the origin of its resource URL (so `/data-service/speckle-proxy/...` would be dropped) and falls back to `localStorage.AuthToken`. Fix: a `ProxySpeckleLoader` subclass overriding only `initObjectLoader`, backed by `createProxyObjectLoader` in a new `ui-v2/src/lib/speckleProxy.js` (a file the plan did not list; it keeps the loader logic importable and testable from node). Commit `306b3a8`.

**3. [Rule 3 - Blocking] `@speckle/objectloader2` must be imported directly.** It was only a transitive dependency; added to `ui-v2/package.json` and the root entry of `package-lock.json` (the lock already had the resolved package entry). No package install was run and nothing new was fetched.

**4. [Rule 1 - Bug] Existing tests and docs encoded the old contract.** `test_review_fix_1205.py::TestCr01SpeckleReadToken` (asserted `readToken` per principal kind) and `test_evidence_versions.py` (asserted `readToken is None`) were rewritten to the D-21 contract (no `readToken` key at all); the apidocs response sample and `test/smoke_e2e.sh` (greps `readToken`; documented unsupported legacy) were updated. `test_static_proxy_boundary.py` gained the new location in its allowlist plus six tests.

**5. [Rule 2 - fail-closed additions]** Resolution gated to interactive callers and to a run whose Speckle project equals the binding; a binding-lookup failure answers unbound (never open); IndexedDB cache off; `Cache-Control: private, no-store`; `X-DG-CSRF` carried on the loader's POST (a cookie session needs it); dot-segment, query and fragment rejection in `parseViewerResource`.

## Overlap with pre-existing uncommitted work

`data-service/auth.py`, `recognition_eval/*`, `test_auth_store.py`, `test_validation_run_immutability.py`, `spec/SWRL-SUBSET.md`, `tools/de01/tests/test_de01_runner.py`, `ui-v2/src/lib/auth.js`, `ui-v2/src/screens/ProjectsScreen.jsx`, `ui-v2/tests/{api-security,auth-security,run-panel,projects-panel}*`, `ui-v2/tests/evidence/*` and the `test/v12-hexagonal-facade-01/*` changes were present before this plan and were not touched or staged. Every file this plan edited was clean before the edit (checked with `git diff --stat`), so each commit contains only this plan's hunks and no index blob surgery was needed. `apps/degram` and `apps/revit-mcp` gitlinks were not touched; `ui-v2/dist` (regenerated by the build, ignored) was not committed.

## Known Stubs

None. `viewerResourcesError` is a real, named degraded-mode signal, not a placeholder.

## Unverified

- No browser run against a live stack: the real ObjectLoader2 is exercised in node against a fake fetch, and the offline `run-degram.mjs` bundle test passes, but the full `Viewer` + `ProxySpeckleLoader` + WebGL path (world tree construction from proxied geometry, `viewer.loadObject`) was not run in a browser, and the viewer package cannot be imported in node. The subclass relies on `initObjectLoader` being called from the stock `SpeckleLoader` constructor with `(resource, token, caching, resourceData, attributeMask, objectTypeMask)`, which is true of 2.31.14 (read in the minified bundle) and must be re-checked on a viewer upgrade. The owner's rebuild (`docker compose build --no-cache design-grammars` and `data-service`) plus a Model Viewer load is the live check.
- The real Speckle server was not contacted: that a self-hosted Speckle serves `/api/v2/projects/{id}/object-stream/` and `/objects/{p}/{o}/single` is inherited from the viewer's own requirement (the viewer already called these paths directly), not independently confirmed here. The legacy `/api/getobjects/{p}` wire shape (`{objects: "<json array string>"}`) is implemented from Speckle's documented format and covered only against a mock.
- nginx was not run (no binary or Docker here); the new location is checked by the static brace-aware parser only. Streaming large objects through nginx and the 90 s read timeout belong to the live deploy check.
- Geometry bytes are not size-capped on the response path (streamed, as the plan accepts for T-1301-09-04); a very large model holds one upstream connection per request until it completes or the 60 s inter-chunk read limit trips.

## Threat Flags

None beyond the plan's register. T-1301-09-01 (token removed) is covered by the payload, source, bundle and config scans and by the no-token-in-any-response tests; -02 (cross-project geometry) by the zero-upstream mismatch, unbound, non-member and foreign-delegated tests across all four routes; -03 (path traversal) by the strict id regex, fixed upstream templates and the dot-segment tests; -04 accepted as planned. New surface worth the verifier's attention: the proxy lets any project viewer read any object of the bound Speckle project, not only the run's models (a Speckle project is the isolation unit, enforced by the existing one-binding-per-non-default-project rule); the shared default Speckle project (`SPECKLE_PROJECT_ID`) is bound to several DG projects by design, so those projects can read each other's geometry through the proxy exactly as they could share the old token.

## Self-Check: PASSED

- FOUND: data-service/speckle_proxy.py, data-service/tests/test_speckle_proxy.py, ui-v2/src/lib/speckleProxy.js, ui-v2/tests/speckle-proxy.test.mjs
- FOUND commits: 4c2c96d (task 1), 306b3a8 (task 2)
