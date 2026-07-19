---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 07
subsystem: api
tags: [n8n, workflow, cypher, context-assembly, design-states]

# Dependency graph
requires:
  - phase: 29-06
    provides: "dg_context.assemble_context() emits a top-level existing_design_states key for graph_query requests (fetch_existing_design_states() + _summarize_state_payload())"
provides:
  - "n8n/workflows/graph-query-mcp.json -- Build Cypher Prompt node now forwards existing_design_states into the LLM Cypher-generation CONTEXT block, with a one-line guidance bullet pointing at (:ValidationRun {project:$project}) + run.statePayloadJson"
  - "Live n8n graph-query-mcp workflow re-synced (versionCounter 40->41), zero drift confirmed against repo JSON, active:true preserved"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "n8n live-instance sync reused the 29-05-established method verbatim: POST /rest/login (emailOrLdapLoginId + password, from docker compose exec n8n printenv, never .env), PATCH /rest/workflows/{id} with {name, nodes, connections, settings}, then an independent GET re-fetch diffing every node's parameters dict by name plus active:true"

key-files:
  created: []
  modified:
    - n8n/workflows/graph-query-mcp.json

key-decisions:
  - "PATCH body built from only {name, nodes, connections, settings} (not the full GET response envelope, which also carries read-only server fields like id/versionCounter/createdAt/updatedAt/tags) -- avoids accidentally round-tripping server-managed metadata back as a write"
  - "Guidance bullet phrased without an apostrophe (\"real per-project ValidationRun design-state snapshots\" instead of \"the project's real...\") to avoid escaping a single-quote inside the node's single-quoted JS string literal"

patterns-established: []

requirements-completed: [CTXA-01]

coverage:
  - id: D1
    description: "Build Cypher Prompt node forwards existing_design_states (from 29-06) into the CONTEXT block alongside existing_entities, plus a one-line guidance bullet"
    requirement: "CTXA-01"
    verification:
      - kind: other
        ref: "python -c json.load + assert 'existing_design_states' in Build Cypher Prompt functionCode + node-name/dangling-connection graph check -- OK forwarded, JSON valid, no dangling connections"
        status: pass
    human_judgment: false
  - id: D2
    description: "Live n8n graph-query-mcp workflow re-synced with zero drift against the repo JSON, active:true preserved"
    verification:
      - kind: manual_procedural
        ref: "POST /rest/login -> PATCH /rest/workflows/b2c3d4e5-f6a7-8901-bcde-f12345678901 (versionCounter 40->41) -> independent GET re-fetch diffing every node's parameters dict by name: missing_in_live=[], extra_in_live=[], param_diffs=[], active=True -- PARITY: PASS"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-19
status: complete
---

# Phase 29 Plan 07: Forward existing_design_states into n8n graph-query prompt Summary

**Build Cypher Prompt now serializes 29-06's live existing_design_states array into the LLM CONTEXT block, and the live n8n instance was re-synced with zero drift confirmed**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-19
- **Tasks:** 2 (both auto)
- **Files modified:** 1 (n8n/workflows/graph-query-mcp.json)

## Accomplishments

- **Task 1:** `n8n/workflows/graph-query-mcp.json`'s `Build Cypher Prompt` function node now adds `existing_design_states: context.existing_design_states` immediately after `existing_entities` in the `JSON.stringify({...})` CONTEXT block, plus one guidance bullet after the LIMIT-50 line telling the LLM that `existing_design_states` lists real per-project `ValidationRun` design-state snapshots and that design-state questions are answered by matching `(:ValidationRun {project:$project})` and reading `run.statePayloadJson`. No other node, the prompt framing, or the raw-Cypher-only instruction were touched.
- Verified via the plan's exact python one-liner: JSON parses, `existing_design_states` is present in the `Build Cypher Prompt` node's `functionCode`, and every connection target resolves to an existing node name (no dangling references).
- `git diff` on the file confirmed the change is a single-line diff (the `functionCode` string value) with no incidental whitespace/formatting drift elsewhere in the file.
- **Task 2:** n8n container confirmed running (`docker compose ps n8n`). Read the live container's actual `N8N_BASIC_AUTH_USER`/`N8N_BASIC_AUTH_PASSWORD` via `docker compose exec n8n printenv` (not `.env`). Authenticated via `POST /rest/login` (this n8n version's login body key is `emailOrLdapLoginId`, not `email` -- confirmed by a first 400 response asking for the missing field, then a 200 on retry). Pushed the repo JSON via `PATCH /rest/workflows/b2c3d4e5-f6a7-8901-bcde-f12345678901` with `{name, nodes, connections, settings}` -- `versionCounter` advanced 40->41, `active:true` preserved in the PATCH response itself. Independently re-fetched via `GET` and diffed every node's `parameters` dict by name against the repo JSON plus `active` state: `missing_in_live=[]`, `extra_in_live=[]`, `param_diffs=[]`, `active=True` -- zero drift confirmed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Forward existing_design_states in the Build Cypher Prompt node** - `270395e` (feat)
2. **Task 2: Re-sync the live n8n instance and verify zero drift** - no repo git commit (live-instance-only action via the n8n REST API, same precedent as 29-05's Task 1 -- the repo JSON pushed was already committed in Task 1, so there is nothing further to diff/commit in git)

**Plan metadata:** `commit_docs` is `false` in `.planning/config.json` for this project -- the final metadata commit (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md) is expected to skip via the SDK's `skipped_commit_docs_false` path.

## Files Created/Modified

- `n8n/workflows/graph-query-mcp.json` - `Build Cypher Prompt` node forwards `existing_design_states` into the CONTEXT block with a one-line ValidationRun/statePayloadJson guidance bullet

## Decisions Made

See `key-decisions` in frontmatter above:
- PATCH body scoped to `{name, nodes, connections, settings}` only, not the full GET envelope (avoids writing back server-managed fields)
- Guidance bullet phrasing avoids an apostrophe to sidestep escaping inside the node's single-quoted JS string literal

## Deviations from Plan

None - plan executed exactly as written. The `emailOrLdapLoginId` login-body-key discovery was a mechanical API-contract detail (first response told us the exact expected field name), not a deviation from the plan's instructions -- the plan specified the correct endpoint/method/credential-source, and 29-05's own precedent already used `POST /rest/login` without specifying its exact body shape.

## Issues Encountered

None blocking. The first `POST /rest/login` attempt used a plain `{"email": ..., "password": ...}` body and got a 400 (`invalid_type`, missing `emailOrLdapLoginId`) -- corrected on the next attempt using the field name the error response named explicitly. No retry loop needed.

## User Setup Required

None - no external service configuration required. The live n8n re-sync used the already-running `n8n` container's REST API and its existing `N8N_BASIC_AUTH_USER`/`PASSWORD` (read from the running container, not `.env`).

## Next Phase Readiness

- Phase 29's graph_query pipeline now delivers 29-06's live `existing_design_states` ground truth all the way to the LLM Cypher-generation prompt, closing the last forwarding gap between `/context/assemble`'s corrected schema/data and the n8n workflow that consumes it.
- Repo and live n8n `graph-query-mcp` workflow are in sync (versionCounter 41, `active:true`, zero parameter drift).
- **Not exercised in this session:** an actual live natural-language design-state graph query through the real webhook -> n8n -> data-service -> Neo4j -> LLM pipeline (requires a configured LLM provider and a live end-to-end run) -- this was already deferred to `/gsd-verify-work` per 29-05's and 29-06's own precedent (Success Criterion 4 / the UAT gap this plan closes structurally but does not itself re-verify end-to-end).
- No blockers.

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-19*

## Self-Check: PASSED

- FOUND: n8n/workflows/graph-query-mcp.json (existing_design_states present in Build Cypher Prompt node)
- FOUND: 270395e (Task 1 commit)
- CONFIRMED: JSON parses, zero dangling connection references
- CONFIRMED: live n8n workflow re-fetched independently -- zero parameter drift, active:true, versionCounter 41
