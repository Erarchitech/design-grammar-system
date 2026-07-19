---
status: testing
phase: 33-dg-canvas-bridge
source: [ROADMAP.md Phase 33 Success Criteria, 33-04-PLAN.md]
started: 2026-07-20T00:00:00Z
updated: 2026-07-20T00:00:00Z
---

## Current Test

number: 1
name: Live context pull returns cgContextJson v1
awaiting: live in-Rhino verification (plan 33-04 — never run)

## Tests

### 1. Live context pull returns cgContextJson v1 (SC1)
expected: With Rhino running, the Frame definition loaded, and DG CANVAS LISTENER On (port 8720), POST /computgraph/context/pull from inside the Docker network (project + definition scope) returns the live canvas as cgContextJson v1 — the same envelope the Phase 32 serializer produces. DEDUP: this happy path is transitively exercised by Phase 35 recognition (recognition can't pull canvas without the bridge); if Group 4 of v9.0-PIPELINE-UAT passes, SC1 is already proven — run standalone only when testing the bridge before Phase 35.
result: [pending]

### 2. MCP gh_get_context parity + tools/list (SC2)
expected: An MCP client calling gh_get_context via POST /mcp returns the same cgContextJson document as /computgraph/context/pull, and POST /mcp tools/list shows the four gh_* tools (gh_get_context, gh_get_selection, gh_preview_structure, gh_clear_preview). DEDUP: covered by Phase 35's recognition/preview flow which drives gh_preview_structure/gh_clear_preview through the same server — run standalone only when verifying the bridge in isolation.
result: [pending]

### 3. Bounded-timeout clean error when listener off / Rhino closed (SC3)
expected: With DG CANVAS LISTENER Off (or Rhino closed), POST /computgraph/context/pull returns a What+Where+How-to-fix structured error within the bounded timeout — it does NOT hang. Connection-refused and timeout both map to the same actionable error shape (gh_bridge.py GH_BRIDGE_HOST/PORT). UNIQUE robustness check — no happy-path pipeline run reaches it (Group 2 of v9.0-PIPELINE-UAT).
result: pass
verified: |
  2026-07-20 — With the listener toggled Off, POST /computgraph/context/pull returned
  HTTP 503 in 0.017s (not a hang) with body:
  {"detail":{"error":"Grasshopper bridge unreachable at host.docker.internal:8720:
  [Errno 111] Connection refused","hint":"Start Rhino and enable DG CANVAS LISTENER
  (port 8720).","code":"GH_BRIDGE_UNREACHABLE"}}
  Structured What (error)+Where (code)+How-to-fix (hint) shape confirmed.

### 4. UI-thread safety + socket lifecycle / no port leak (SC4)
expected: The listener never touches the GH canvas off the UI thread (canvas reads marshalled via RhinoApp.InvokeOnUiThread). Toggling the listener Off closes the socket cleanly, and repeated On/Off cycles (~5) do not leak the port — re-binding 8720 succeeds every time, no "address already in use". UNIQUE robustness check — not covered by any happy-path run (Group 2 of v9.0-PIPELINE-UAT).
result: pass
verified: |
  2026-07-20 — Listener cycled Off→On 5 times in Grasshopper with no bind errors on any
  cycle. Final re-check: POST /computgraph/context/pull returned HTTP 200 with a valid
  cgContextJson v1 envelope (schemaVersion: cg-context-1) for the loaded definition
  (RuleValidation-UrbanBlock_V7 — not the Frame fixture, object:null/algorithms:[],
  untagged node pool only; fine for this connectivity check, Frame definition needed
  for Group 4 recognition). Confirms clean rebind, no port leak.

## Summary

total: 4
passed: 2
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

- Phase 33 shipped code-complete (3/4 plans; 33-01/33-02/33-03 executed) with NO UAT file — plan 33-04 IS the live in-Rhino end-to-end verification and was never run. Tests 1-2 are transitively covered by the Phase 35 canvas-intelligence pipeline (Group 4 of .planning/phases/v9.0-PIPELINE-UAT.md); Tests 3-4 are unique bridge-robustness checks run standalone (Group 2).
