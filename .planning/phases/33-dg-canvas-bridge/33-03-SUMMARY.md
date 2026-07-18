---
phase: 33-dg-canvas-bridge
plan: 03
subsystem: api
tags: [fastapi, socket, mcp, tcp-client, grasshopper-mcp]

# Dependency graph
requires:
  - phase: 33-01
    provides: "Locked wire contract — newline-terminated UTF-8 JSON request `{type, parameters}`, single-line JSON response envelope `{bridge:'dg', version:1, status, result|error}`, error codes UNKNOWN_COMMAND/BAD_REQUEST/HANDLER_ERROR"
provides:
  - "gh_bridge.py — raw-socket TCP client speaking the locked wire contract with bounded connect/read timeouts and structured-error mapping"
  - "POST /computgraph/context/pull — thin proxy stamping project onto the live cgContextJson document"
  - "4 new gh_* tools (gh_get_context, gh_get_selection, gh_preview_structure, gh_clear_preview) on the existing POST /mcp JSON-RPC server"
  - "docker-compose data-service wiring to reach the Windows-host DG CANVAS LISTENER via host.docker.internal"
affects: [33-04, 35-preview-and-selection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "gh_bridge.py: stdlib socket.create_connection + settimeout, MAX_RESPONSE_BYTES-bounded readline, lazy in-function import of _structured_error_response to break the app<->gh_bridge circular import"
    - "/mcp tools/list + tools/call extended in place (single MCP server, no new abstraction) — matches the existing neo4j_schema/neo4j_query dispatch chain verbatim"

key-files:
  created:
    - data-service/gh_bridge.py
    - data-service/tests/test_gh_bridge.py
    - data-service/tests/test_app_computgraph_pull.py
    - data-service/tests/test_mcp_gh_tools.py
  modified:
    - data-service/app.py
    - docker-compose.yml

key-decisions:
  - "Circular import resolved via lazy import: gh_bridge.py imports `_structured_error_response` from `app` inside `_call()`'s function body, not at module scope, since app.py imports gh_bridge at module scope (`import gh_bridge`) — importing app back at gh_bridge's own module-load time would deadlock the import graph."
  - "gh_bridge errors (HTTPException raised inside gh_bridge) propagate through both the REST endpoint and the /mcp tools/call branches unwrapped — never re-wrapped in a JSON-RPC error object — matching the existing neo4j_query precedent in the same file."
  - "readline() bounded via `readline(MAX_RESPONSE_BYTES)` (10 MiB) rather than an unbounded read, per T-33-06 (Tampering/DoS mitigation)."

requirements-completed: [BRDG-02, BRDG-03, BRDG-04]

coverage:
  - id: D1
    description: "gh_bridge.py TCP client maps refusal/timeout/OSError to a bounded 503 GH_BRIDGE_UNREACHABLE and an error envelope to a 502, returning the result payload on success"
    requirement: "BRDG-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_gh_bridge.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /computgraph/context/pull stamps project onto the live cgContextJson document and propagates bridge errors unchanged"
    requirement: "BRDG-02"
    verification:
      - kind: integration
        ref: "data-service/tests/test_app_computgraph_pull.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /mcp tools/list lists the 4 gh_* tools alongside neo4j_schema/neo4j_query; tools/call dispatches each through gh_bridge"
    requirement: "BRDG-03"
    verification:
      - kind: unit
        ref: "data-service/tests/test_mcp_gh_tools.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "docker-compose data-service service reaches the Windows-host listener via GH_BRIDGE_HOST/PORT env + extra_hosts host.docker.internal:host-gateway"
    requirement: "BRDG-02"
    verification:
      - kind: other
        ref: "docker compose config (manual invocation, confirms env + extra_hosts render correctly)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live end-to-end round-trip against a real Rhino/Grasshopper DG CANVAS LISTENER session — cannot be automated in this environment"
    verification: []
    human_judgment: true
    rationale: "Requires a live Rhino/Grasshopper process with the Plan 01/04 listener running on the Windows host; deferred to Plan 04's checkpoint:human-verify per 33-RESEARCH.md Environment Availability."

duration: 12min
completed: 2026-07-18
status: complete
---

# Phase 33 Plan 03: DG Canvas Bridge — data-service side (gh_bridge.py) Summary

**Raw-socket `gh_bridge.py` TCP client plus a REST proxy and 4 new MCP tools that let data-service pull the live Grasshopper canvas context, all wired through docker-compose's `host.docker.internal` host-gateway.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-18T20:10:00+03:00 (approx.)
- **Completed:** 2026-07-18T20:19:12+03:00
- **Tasks:** 2
- **Files modified:** 6 (2 created source, 3 created test, 2 modified)

## Accomplishments
- `gh_bridge.py` — a raw-socket TCP client (`socket.create_connection`) speaking the locked newline-terminated JSON wire contract, with `CONNECT_TIMEOUT_SECONDS=5.0`/`READ_TIMEOUT_SECONDS=30.0` and a `MAX_RESPONSE_BYTES`-bounded `readline()`; refusal/timeout/`OSError` map to a structured 503 `GH_BRIDGE_UNREACHABLE`, a listener error envelope maps to 502
- `POST /computgraph/context/pull` — thin proxy returning the live `cgContextJson` document with `project` stamped onto it
- 4 new `gh_*` tools (`gh_get_context`, `gh_get_selection`, `gh_preview_structure`, `gh_clear_preview`) added to the existing `POST /mcp` `tools/list`/`tools/call` dispatch chain, reusing the neo4j_query error-propagation precedent
- `docker-compose.yml` data-service block gets `GH_BRIDGE_HOST`/`GH_BRIDGE_PORT` env plus `extra_hosts: ["host.docker.internal:host-gateway"]`

## Task Commits

Each task followed the RED → GREEN TDD cycle with its own commits:

1. **Task 1: gh_bridge.py TCP client with bounded timeouts + structured errors**
   - `302d9a3` test(33-03): add failing tests for gh_bridge.py TCP client (RED)
   - `a7fa4ac` feat(33-03): implement gh_bridge.py TCP client with bounded timeouts (GREEN)
2. **Task 2: /computgraph/context/pull endpoint + 4 gh_* MCP tools + docker-compose wiring**
   - `7becc37` test(33-03): add failing tests for /computgraph/context/pull + gh_* MCP tools (RED)
   - `7327618` feat(33-03): implement /computgraph/context/pull + 4 gh_* MCP tools + compose wiring (GREEN)

**Plan metadata:** commit_docs is disabled for this project (`.planning/config.json` → `commit_docs: false` from init context) — no separate `docs(...)` metadata commit is created; STATE.md/ROADMAP.md/REQUIREMENTS.md updates are made without a final commit per the SDK's `skipped_commit_docs_false` contract.

## Files Created/Modified
- `data-service/gh_bridge.py` - TCP client: `_call`, `get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`, `get_preview_status`
- `data-service/tests/test_gh_bridge.py` - 10 tests covering success path, refusal/timeout/OSError→503, error-envelope→502, bounded-readline contract
- `data-service/app.py` - `import gh_bridge`; `ComputgraphContextPullRequest` + `POST /computgraph/context/pull`; 4 new `gh_*` tools/list entries + tools/call branches
- `data-service/tests/test_app_computgraph_pull.py` - 2 tests covering project-stamping and 503 propagation
- `data-service/tests/test_mcp_gh_tools.py` - 6 tests covering tools/list contents and tools/call dispatch for all 4 gh_* tools + error propagation
- `docker-compose.yml` - data-service `GH_BRIDGE_HOST`/`GH_BRIDGE_PORT` env + `extra_hosts` host-gateway entry

## Decisions Made
- Lazy in-function import of `_structured_error_response` inside `gh_bridge._call()` to resolve the `app.py` ↔ `gh_bridge.py` circular import (app.py imports gh_bridge at module scope; gh_bridge only needs `_structured_error_response` at call time, not import time).
- `readline(MAX_RESPONSE_BYTES)` with `MAX_RESPONSE_BYTES = 10 * 1024 * 1024` (10 MiB) as the bound for T-33-06 — generous enough for any realistic `cgContextJson` document, small enough to cap worst-case memory use from a malformed/never-terminating response.
- gh_bridge errors are never re-wrapped in a JSON-RPC error object inside `/mcp`'s `tools/call` — they propagate as the same `HTTPException`/`_structured_error_response` FastAPI already uses for `neo4j_query`, keeping one error vocabulary across the whole file (per 33-RESEARCH.md Anti-Patterns).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing environment quirk (not a deviation from this plan, out of scope per SCOPE BOUNDARY):** Running `python -m pytest data-service/tests/` directly on the Windows host (outside the Docker network) causes 4 unrelated failures in `test_dg_context.py` (`TestContextEndpoints`/`TestDeterminism`), because those tests exercise endpoints that open a live `neo4j.GraphDatabase.driver` session against the default `NEO4J_URI=bolt://neo4j:7687` — a Docker-internal hostname unresolvable from the host. Confirmed this is purely a host-vs-container DNS issue, not caused by this plan's changes: `NEO4J_URI=bolt://localhost:7687 python -m pytest data-service/tests/` yields **205 passed, 0 failed** (the full suite, including all 18 new tests from this plan). No code in `test_dg_context.py`/`dg_context.py` was touched. `docker compose config` also parses cleanly with the new `GH_BRIDGE_HOST`/`GH_BRIDGE_PORT`/`extra_hosts` entries.

## User Setup Required

None - no external service configuration required. The live end-to-end round-trip against a real Rhino/Grasshopper `DG CANVAS LISTENER` session (Plan 01/04's C# component) still needs a `checkpoint:human-verify` in Plan 04, since no Rhino session is available in this automated context.

## Next Phase Readiness

- `gh_bridge.py` is ready for Plan 04's live-Rhino end-to-end verification against the real `CanvasListenerComponent` (Plan 01).
- `POST /computgraph/context/pull` and the 4 `gh_*` MCP tools are fully green under `python -m pytest` with no Rhino/socket dependency (fake/monkeypatched), satisfying this plan's "Fully green in CI" success criterion.
- No blockers for Plan 04.

---
*Phase: 33-dg-canvas-bridge*
*Completed: 2026-07-18*
