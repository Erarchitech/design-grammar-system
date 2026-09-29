---
phase: 1205-security-and-tenancy-release-gate
plan: "11"
subsystem: ui-v2 data layer
tags: [react, vite, apiFetch, csrf, session-cookie, d-06, d-08, workflow-relay]

requires:
  - phase: 1205-07
    provides: "dg_session cookie auth, /auth/* routes, X-DG-CSRF contract"
  - phase: 1205-10
    provides: "global deny-by-default, owner-bound GET /execution-result/{id}, removal of the latest-by-workflow route"
provides:
  - "ui-v2/src/lib/apiClient.js: getConfig, dataServiceBase, apiFetch, ApiError, AUTH_EXPIRED_EVENT, CSRF_HEADER"
  - "graphApi/modelApi/inputGenApi on named data-service endpoints (contract table of 1205-11); no Cypher executor, no credential, no n8n URL in ui-v2/src/lib"
  - "ingestRules/queryGraph through POST /workflows/{rules-ingest,graph-query}, polled by executionId only"
affects: [1205-12, 1205-13, 1205-14, 1205-15, 1205-18]

tech-stack:
  added: []
  patterns:
    - "One transport (apiFetch): credentials include, X-DG-CSRF: 1 on unsafe verbs, ApiError {status, code, hint}, dg-auth-expired window event on 401"
    - "passthrough option for callers that branch on body shape (reasoner consistency) rather than status"

key-files:
  created:
    - ui-v2/src/lib/apiClient.js
  modified:
    - ui-v2/src/lib/graphApi.js
    - ui-v2/src/lib/modelApi.js
    - ui-v2/src/lib/inputGenApi.js
    - ui-v2/src/lib/connectorsApi.js
    - ui-v2/src/lib/llmApi.js
    - ui-v2/src/lib/reasonerApi.js
    - ui-v2/src/screens/GraphScreen.jsx

key-decisions:
  - "getConfig returns exactly {dataServiceUrl, speckleBaseUrl}; every other window.GRAPH_CONFIG key (including legacy neo4j*/n8n*/speckleReadToken) is ignored"
  - "apiFetch gained two options beyond the plan's list: signal (AbortController forwarding for the reasoner run) and passthrough (never throws, resolves {ok,status,body}); runConsistencyCheck depends on both to keep its no-throw contract"
  - "ApiError also carries hint (supersedeRule callers and inputGenApi read err.hint / err.code)"
  - "fetchGraph and fetchRules return empty results without a request when project is empty: there is no unscoped graph any more"
  - "Polling retries transient errors until timeout (as before) but a 404 throws 'Execution not found or not permitted.' and 401/403 rethrow"

patterns-established:
  - "Named-endpoint client shape: build path from dataServiceBase() + encodeURIComponent'd segments, no client-built predicates"

requirements-completed: []  # ALGN12-17/18/19 span 1205-12/13/14/15/16/18; not closed by this plan alone

coverage:
  - id: D1
    description: "D-06: no generic Cypher executor, Neo4j HTTP path, Neo4j/n8n credential or Basic auth header in ui-v2/src/lib; nine former Cypher sites call named endpoints"
    requirement: "ALGN12-18"
    verification:
      - kind: other
        ref: "grep over ui-v2/src/lib for executeCypher, neo4jPassword, n8nWebhook, /n8n/, tx/commit, execution-result/latest, btoa( -- 0 matches each"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-08: UI never calls n8n; ingest/query go through the data-service relay and are polled only by executionId"
    requirement: "ALGN12-19"
    verification:
      - kind: other
        ref: "graphApi.js callWorkflow/pollExecution read; no latest fallback; build green"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-01: every data-service call goes through apiFetch (credentials include, X-DG-CSRF on unsafe methods, ApiError, dg-auth-expired on 401)"
    requirement: "ALGN12-17"
    verification:
      - kind: other
        ref: "grep -rn 'fetch(' ui-v2/src/lib outside apiClient.js -- 0 matches; apiClient.js has 1 credentials include and 1 X-DG-CSRF"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-12: runtime config read by the UI carries only dataServiceUrl and speckleBaseUrl"
    requirement: "ALGN12-18"
    verification:
      - kind: other
        ref: "apiClient.js getConfig returns two keys; no other code reads window.GRAPH_CONFIG"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live behaviour against the enforcing server (login, graph load, ingest relay)"
    requirement: "ALGN12-17"
    verification: []
    human_judgment: true
    note: "Deferred: server endpoints land in 1205-12/14, login screen in 1205-13, live smoke in 1205-18"

duration: ~12min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 11: Browser Data Layer on Named Endpoints Summary

**The V2 UI data layer now has one authenticated transport (`apiFetch`: session cookie, `X-DG-CSRF` on unsafe verbs, structured `ApiError`, `dg-auth-expired` on 401); the nine browser Cypher sites and both n8n webhooks are replaced by named data-service endpoints and the owner-bound workflow relay, and no graph or n8n credential remains in `ui-v2/src/lib`.**

## Accomplishments

- **apiClient.js (Task 1):** `getConfig()` (two keys only), `dataServiceBase()`, `apiFetch`, `ApiError`, `AUTH_EXPIRED_EVENT`, `CSRF_HEADER`. `connectorsApi`, `llmApi`, `reasonerApi` rewritten on it, exported names and return shapes unchanged; `createCredential` always sends `project`.
- **graphApi.js (Task 2):** credential DEFAULTS block, `executeCypher`, `rowsOf` and `webhookHeaders` deleted. `getConfig` re-exported from apiClient for existing importers. `fetchGraph` -> GET `/graph/{project}`; `tagProjectNodes` -> POST `/graph/{project}/claim-untagged`; `updateNodeProp(project, neoId, key, value)` -> PUT `/graph/{project}/node/{id}/property`; `fetchRules` -> GET `/rules/{project}`; `fetchProjects` -> GET `/projects`. All `/rules/*` and `/design-rule-sessions*` calls moved to apiFetch with unchanged signatures. `ingestRules`/`queryGraph` POST to `/workflows/rules-ingest` and `/workflows/graph-query`, require `{status:"accepted", executionId}` and poll `/execution-result/{executionId}` only.
- **modelApi.js / inputGenApi.js:** `fetchRuleDetails` (allow404, null without project), `fetchEntityStatuses` and `fetchAcceptedCandidates` on the contract endpoints; the two local `getJson`/`postJson` helpers are thin apiFetch wrappers (postJson still appends the hint to the message and keeps `err.hint`).
- **GraphScreen.jsx:** the single `updateNodeProp` call site passes `project` first.

## Task Commits

1. **Task 1: apiClient.js and the three small clients on apiFetch** - `bd79790` (feat)
2. **Task 2: named endpoints and the relay** - `795b888` (feat)

## Verification

| Check | Result |
|---|---|
| `npm --prefix ui-v2 run build` (after each task) | green |
| `grep -c "fetch("` connectorsApi / llmApi / reasonerApi | 0 / 0 / 0 |
| `grep -rn "fetch("` over `ui-v2/src/lib` excluding apiClient.js | 0 matches |
| `credentials: "include"` / `X-DG-CSRF` in apiClient.js | 1 / 1 |
| `executeCypher`, `neo4jPassword`, `n8nWebhook`, `/n8n/`, `tx/commit`, `execution-result/latest`, `btoa(` over `ui-v2/src/lib` | 0 each |
| `grep -c "updateNodeProp(project" GraphScreen.jsx` | 1 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] apiFetch needed `signal` and `passthrough` options**
- **Found during:** Task 1
- **Issue:** `runConsistencyCheck` forwards an AbortController signal and must NOT throw on non-2xx (a 504 is ambiguous; callers branch on body shape). The plan's option list (`method, body, headers, allow404`) cannot express either.
- **Fix:** added `signal` and `passthrough` (resolves `{ok, status, body}`, still dispatches `dg-auth-expired` on 401). Behaviour of the existing screen is unchanged.
- **Files modified:** `ui-v2/src/lib/apiClient.js`, `ui-v2/src/lib/reasonerApi.js`
- **Commit:** `bd79790`

**2. [Rule 2 - Missing critical] ApiError carries `hint`**
- **Issue:** `supersedeRule` callers (GraphScreen `err.code`/`err.hint`) and inputGenApi depend on the hint; ApiError with only status/code would drop it.
- **Fix:** ApiError stores `hint` alongside `status` and `code`.
- **Commit:** `bd79790`

## Expected mid-phase breakage (recorded, no server stubbed)

- The live UI does not fully work until 1205-12 (named graph endpoints, /projects), 1205-13 (login screen consuming `dg-auth-expired`) and 1205-14 (`/workflows/*` relay) land; until then those calls 401/404 against the enforcing server. Live smoke is 1205-18.
- **`ui-v2/entrypoint.sh` still writes `neo4jUser`/`neo4jPassword`/`n8n*`/`speckleReadToken` into `config.js`.** The UI no longer reads them (getConfig ignores them), but they still ship in the served file. Not in this plan's `files_modified`; the bundle/config scan in 1205-15 must close it (delete the keys from entrypoint.sh and compose env).
- `GraphScreen.jsx:1026` and `ProjectsScreen.jsx:117` display `cfg.neo4jUri`; that key is no longer in getConfig, so both fall back to the literal default `bolt://neo4j:7687` (display only, harmless).

## Notes for downstream plans

- **1205-14:** `tagProjectNodes` is kept for parity, but per 1205-12 `claim-untagged` only moves `project IS NULL` nodes and never `default-project`. The relay must run the rules-ingest workflow under the caller's real project (the UI now sends `{project, rulesText}`); if the workflow still writes `default-project`, ingested nodes will not be claimed and will be invisible.
- **1205-13:** listen for `AUTH_EXPIRED_EVENT` (`"dg-auth-expired"`) exported from `ui-v2/src/lib/apiClient.js` to return to the login state.
- `fetchProjects()` now returns `[{project, nodes, role}]` (role is new; ProjectsScreen ignores it).
- Legacy `graph-viewer/` and `test/test_spec_llm.py` still reference the removed latest-poll route; out of scope (archived / 1205-16).

## Known Stubs

None.

## Threat Flags

None beyond the plan's register.

## Self-Check: PASSED

Created/modified files present on disk (apiClient.js, graphApi.js, modelApi.js, inputGenApi.js, connectorsApi.js, llmApi.js, reasonerApi.js, GraphScreen.jsx, this SUMMARY); commits `bd79790` and `795b888` in git log.
