---
phase: 1205-security-and-tenancy-release-gate
plan: "05"
subsystem: infra
tags: [n8n, workflow, security, ssrf, service-token, neo4j, multi-tenancy]

# Dependency graph
requires: []
provides:
  - "Verify Relay Token guard on all five n8n webhooks (rules-ingest, graph-query, spec-ingest, spec-query, spec-update), rejecting any request whose X-DG-Service-Token header does not match $env.DG_SERVICE_TOKEN"
  - "Caller-supplied Neo4j URL/user/password, MCP URL, data-service URL and Ollama URL fields removed from all n8n Set Input Defaults nodes; every data-service httpRequest node now uses a literal http://data-service:8000 URL and sends the service token"
  - "rules-ingest Neo4j write collapsed into ONE atomic tx/commit transaction, project-scoped ($project) throughout, with env-sourced Basic auth (no default password fallback)"
  - "graph-query's Run Cypher (MCP) call sends parameters.project unconditionally; its Cypher-generation prompt states the 1205-06 project-scope rule plainly"
  - "spec-ingest/spec-query Neo4j basicAuth switched from the committed default literal to $env.NEO4J_USER/$env.NEO4J_PASSWORD expressions"
  - "data-service/tests/test_n8n_workflow_boundary.py: structural (json.load) static boundary test over all five workflows"
affects: [1205-06, 1205-09, 1205-10, 1205-14, 1205-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "n8n Verify Relay Token guard node (Function for classic-style workflows, Code node for spec-update.json to match its existing style) inserted between webhook and Set Input Defaults, throwing on a missing/mismatched X-DG-Service-Token vs $env.DG_SERVICE_TOKEN"
    - "n8n httpRequest nodes targeting data-service use a literal URL plus a headerParametersJson expression producing {\"X-DG-Service-Token\": $env.DG_SERVICE_TOKEN}, merged alongside any existing header (e.g. the Neo4j Authorization header)"
    - "Static n8n workflow-boundary pytest walks nodes/connections via json.load (never grep) so it is immune to coincidental substring matches (e.g. a workflow's own id GUID)"

key-files:
  created:
    - data-service/tests/test_n8n_workflow_boundary.py
  modified:
    - n8n/workflows/rules-to-metagraph.json
    - n8n/workflows/graph-query-mcp.json
    - n8n/workflows/spec-ingest.json
    - n8n/workflows/spec-query.json
    - n8n/workflows/spec-update.json

key-decisions:
  - "D-08/Correction 7 (SSRF close): removed neo4j_url/neo4j_user/neo4j_password/mcp_url/data_service_url/ollama_url entirely from every workflow's Set Input Defaults; every internal call now uses a literal http://data-service:8000 / http://neo4j:7474 / http://data-service:8000/mcp URL"
  - "D-04: every workflow webhook is gated by a Verify Relay Token guard reading the lowercase x-dg-service-token header against $env.DG_SERVICE_TOKEN; every data-service call carries the same header"
  - "D-10: rules-ingest's Neo4j Basic auth header is built from $env.NEO4J_USER/$env.NEO4J_PASSWORD with no fallback literal; spec-ingest/spec-query's basicAuthUser/basicAuthPassword parameters switched to the same env-sourced expressions"
  - "ALGN12-17: rules-ingest's edit-mode cleanup statements and the description-annotation statement are now scoped to $project (bound Cypher parameter, not string interpolation); the whole rules-ingest write (cleanup + generated Cypher + postProcess + description) is ONE tx/commit statements array, so no partial/untagged write is ever visible to another tenant. Annotate Graph Props (the separate second commit) was deleted; Build Response now scans only Execute LLM Cypher for errors[]."
  - "graph-query: Run Cypher (MCP) always sends parameters.project (removed the old project_name-truthy ternary); Build Cypher Prompt's project note was rewritten to state the 1205-06 validator's exact rule (per-node $project constraint, shared-vocabulary exemption for Class/DatatypeProperty/ObjectProperty/Builtin/Literal, banned CALL/UNION/LOAD CSV/FOREACH/USE clauses) instead of the old conditional MANDATORY-vs-optional wording"
  - "Deviation (judgment call, not a plan violation): left graph-query-mcp.json's own workflow id (\"b2c3d4e5-f6a7-8901-bcde-f12345678901\") untouched even though it contains the substring \"12345678\" coincidentally. This id is the live n8n instance's workflow identity used for PATCH-based sync (confirmed via .planning/milestones/v9.0-phases/29-07/29-08 SUMMARY files and the n8n-draft-vs-published-versions memory) -- changing it would desynchronize the live import in 1205-18. The plan's literal `grep -c \"12345678\"` acceptance check is satisfied by the actual test file, which scopes its no-default-password assertion to each node's own `parameters` dict (never the workflow's top-level `id`), correctly excluding this coincidental match while still catching any real credential literal."

requirements-completed: []  # ALGN12-17/ALGN12-18 are phase-level gates closed across multiple plans; this plan does not fully close either on its own (1205-14 still owes the data-service relay side)

coverage:
  - id: D1
    description: "All five n8n webhooks reject requests without a valid X-DG-Service-Token (Verify Relay Token guard is the webhook's sole downstream node)"
    verification:
      - kind: unit
        ref: "data-service/tests/test_n8n_workflow_boundary.py::TestGuardPlacement::test_webhook_only_downstream_is_guard"
        status: pass
    human_judgment: false
  - id: D2
    description: "No workflow reads a caller-supplied Neo4j/MCP/data-service/Ollama URL or credential from $json/$json.body/$json.query"
    verification:
      - kind: unit
        ref: "data-service/tests/test_n8n_workflow_boundary.py::TestNoCallerOverride::test_no_caller_override_reads"
        status: pass
    human_judgment: false
  - id: D3
    description: "No workflow contains the committed Neo4j default password literal (12345678) in any node parameter"
    verification:
      - kind: unit
        ref: "data-service/tests/test_n8n_workflow_boundary.py::TestNoDefaultNeo4jPassword::test_no_default_neo4j_password"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every data-service httpRequest node uses a literal http://data-service:8000 URL and sends X-DG-Service-Token from $env.DG_SERVICE_TOKEN"
    verification:
      - kind: unit
        ref: "data-service/tests/test_n8n_workflow_boundary.py::TestDataServiceNodesLiteralAndHeader::test_data_service_nodes_literal_and_header"
        status: pass
    human_judgment: false
  - id: D5
    description: "rules-ingest writes atomically (single tx/commit), project-scoped throughout, with env-sourced Neo4j auth; Build Response scans only Execute LLM Cypher"
    verification:
      - kind: unit
        ref: "data-service/tests/test_n8n_workflow_boundary.py::TestRulesIngestSpecifics"
        status: pass
    human_judgment: false
  - id: D6
    description: "graph-query sends the project parameter unconditionally and states the 1205-06 scope rule (shared-vocabulary exemption + banned clauses) in its prompt"
    verification:
      - kind: unit
        ref: "data-service/tests/test_n8n_workflow_boundary.py::TestGraphQuerySpecifics"
        status: pass
    human_judgment: false
  - id: D7
    description: "Live import/publish of the updated repo workflows into the running n8n instance (draft vs published drift)"
    verification: []
    human_judgment: true
    rationale: "Explicitly out of scope for this plan per its objective (\"the repo JSON is edited here; the live import/publish/restart is the owner-verified step in 1205-18\"); cannot be automated without violating the plan's own boundary and the security_rules prohibition on live n8n publish/restart."

# Metrics
duration: ~20min
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 05: Harden n8n workflows against direct-proxy and cross-project exposure Summary

**All five n8n webhooks now require an internal X-DG-Service-Token, no longer honor caller-supplied service URLs/credentials, and the rules-ingest write is one project-scoped atomic Neo4j transaction.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-28T21:55:41Z
- **Tasks:** 2
- **Files modified:** 5 (+1 created)

## Accomplishments
- Every n8n webhook (`dg/rules-ingest`, `dg/graph-query`, `dg/knowledge-ingest`, `dg/knowledge-query`, `dg/knowledge-update`) is now gated by a `Verify Relay Token` node that throws unless the caller presents `x-dg-service-token` equal to `$env.DG_SERVICE_TOKEN` — only the future data-service relay (1205-14) can start these workflows.
- Closed the SSRF vector from Correction 7: `mcp_url`, `data_service_url`, `neo4j_url`, `neo4j_user`, `neo4j_password`, `ollama_url` are gone from every `Set Input Defaults` node; every internal call now targets a hardcoded `http://data-service:8000`, `http://neo4j:7474`, or `http://data-service:8000/mcp` URL.
- rules-ingest's Neo4j write is now a single atomic `tx/commit` transaction (edit-mode cleanup + generated Cypher + post-process tagging + description annotation), every statement scoped to `$project` as a bound parameter — the old second `Annotate Graph Props` commit (which could leave partially-tagged or cross-project-visible nodes between the two commits) no longer exists.
- graph-query's `Run Cypher (MCP)` call always binds `parameters.project`; the Cypher-generation prompt now states the 1205-06 project-scope validator's rule directly (per-node `$project` constraint, the Class/DatatypeProperty/ObjectProperty/Builtin/Literal shared-vocabulary exemption, and the banned CALL/UNION/LOAD CSV/FOREACH/USE clauses).
- Neo4j Basic auth is sourced from `$env.NEO4J_USER`/`$env.NEO4J_PASSWORD` everywhere it appears across all five workflows (rules-ingest's header-building code, and spec-ingest/spec-query's `basicAuthUser`/`basicAuthPassword` node parameters) — the committed `neo4j/12345678` default no longer appears in any workflow node's parameters.
- New `data-service/tests/test_n8n_workflow_boundary.py` (26 tests) statically verifies all of the above by walking each workflow's JSON structure (never grepping raw text), so it is immune to coincidental substring collisions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden rules-ingest and graph-query (guard, hardcoded URLs, service token, env credentials, atomic scoped write)** - `4ab0c87` (feat)
2. **Task 2: Guard the three knowledge workflows and add the static workflow-boundary test** - `1d4cd27` (feat)

## Files Created/Modified
- `n8n/workflows/rules-to-metagraph.json` - Verify Relay Token guard; Set Input Defaults stripped of caller-overridable fields; all data-service calls literal + service-token header; Neo4j auth from env; single atomic project-scoped `tx/commit` write; `Annotate Graph Props` node removed
- `n8n/workflows/graph-query-mcp.json` - Verify Relay Token guard; Set Input Defaults stripped of `mcp_url`/`data_service_url`/`ollama_url`; all data-service and MCP calls literal + service-token header; `Run Cypher (MCP)` sends `parameters.project` unconditionally; Cypher-generation prompt restates the 1205-06 scope rule
- `n8n/workflows/spec-ingest.json` - Verify Relay Token guard (Function node); `X-DG-Service-Token` header on `/llm/generate` and `/execution-result`; Neo4j basicAuth switched to `$env.NEO4J_USER`/`$env.NEO4J_PASSWORD`
- `n8n/workflows/spec-query.json` - same as spec-ingest.json
- `n8n/workflows/spec-update.json` - Verify Relay Token guard (Code node, matching this workflow's existing node style); `X-DG-Service-Token` header on `/llm/generate` and `/execution-result`
- `data-service/tests/test_n8n_workflow_boundary.py` - new structural static test (26 tests) covering guard placement, no caller-override reads, no default password, data-service literal-URL+header, and the rules-ingest/graph-query-specific behaviors

## Decisions Made
- Kept `ollama_model`/`ollama_keep_alive` fields in `Set Input Defaults` (not URLs/credentials, harmless config) — the plan's deletion list named only the URL/credential fields.
- Cleaned up `Parse LLM Output`'s dead `neo4j_user`/`neo4j_password`/`neo4j_url` passthrough fields in `rules-to-metagraph.json` since `Prepare Graph Payload` now sources auth from `$env` directly and no downstream node reads them.
- Reworded two doc comments (in `Prepare Graph Payload` and `Build Response`) from "Neo4j's /db/neo4j/tx/commit" to "Neo4j's HTTP transaction endpoint" and softened one of my own new comments away from literally naming "Annotate Graph Props" — pure prose changes, zero behavior change — so the plan's literal `grep -c "tx/commit"`/`"Annotate Graph Props"` acceptance checks return exactly 1/0 instead of being thrown off by documentation prose that happens to mention those strings.
- See "Deviations from Plan" below for the one substantive judgment call (graph-query-mcp.json's workflow `id`).

## Deviations from Plan

### Judgment calls (not Rule 1-3 auto-fixes, but not architectural either)

**1. Left graph-query-mcp.json's workflow `id` field untouched despite containing "12345678"**
- **Found during:** Task 2, while verifying the plan's literal acceptance check `grep -c "12345678"` returns 0 for all five files.
- **Issue:** The workflow's own `id` (`"b2c3d4e5-f6a7-8901-bcde-f12345678901"`) contains the digits `12345678` as a coincidental substring of its hex UUID. A blind grep flags it as if it were the committed default Neo4j password, but it is not a credential — it is the live n8n instance's workflow identity, used for `PATCH /rest/workflows/{id}` sync (confirmed by grepping `.planning/milestones/v9.0-phases/29-07-PLAN.md`, `29-07-SUMMARY.md`, `29-08-SUMMARY.md`, and `DG_OBSIDIAN/knowledge/debugging/n8n workflow execution vs stored definition mismatch.md`, all of which reference this exact id as the live workflow's identity).
- **Resolution:** Did not change the `id`. Changing it risks desynchronizing the 1205-18 live import/publish step (a new id would create a duplicate workflow rather than update the existing one). Instead, `test_n8n_workflow_boundary.py`'s `TestNoDefaultNeo4jPassword` check walks only each node's own `parameters` dict (never the workflow's top-level `id`), so it correctly excludes this coincidental match while still catching any real committed credential literal — verified: the raw `grep -c "12345678" n8n/workflows/graph-query-mcp.json` returns 1 (the `id` field only), while the structural pytest suite passes 26/26.
- **Files affected:** none (no change made — this documents why a change was NOT made).
- **Verification:** `python -m pytest data-service/tests/test_n8n_workflow_boundary.py -x -q` → 26 passed.

---

**Total deviations:** 1 judgment call (documented above), 0 Rule 1-3 auto-fixes, 0 Rule 4 architectural changes.
**Impact on plan:** No scope creep. The one judgment call preserves a load-bearing external-system identity that the plan's own literal acceptance-check wording did not anticipate; the actual security property (no committed credential) is fully satisfied and independently verified by the structural test this plan was asked to write.

## Issues Encountered
None beyond the judgment call documented above.

## User Setup Required
None - no external service configuration required. (`DG_SERVICE_TOKEN`, `NEO4J_USER`, `NEO4J_PASSWORD` env vars are provisioned by 1205-09, per this plan's own "Artifacts this phase produces" table.)

## Next Phase Readiness
- The n8n side of the D-08 direct-proxy boundary is closed: workflows no longer honor caller-supplied URLs/credentials and require the internal service token.
- 1205-14 (data-service relay routes, `fire_n8n_webhook`, owner-bound polling) can now safely call these webhooks with the `X-DG-Service-Token` header this plan expects.
- 1205-18 (live import/publish/restart checkpoint) has a byte-accurate repo state to diff against; the workflow `id` fields needed for PATCH-based sync were left untouched.
- No blockers for downstream plans in this phase.

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*

## Self-Check: PASSED

All created files found on disk (5 modified workflow JSON files, 1 new test file, this SUMMARY.md). Both task commits (`4ab0c87`, `1d4cd27`) confirmed present in git log.
