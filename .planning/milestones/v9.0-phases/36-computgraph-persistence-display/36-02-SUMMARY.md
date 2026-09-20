---
phase: 36-computgraph-persistence-display
plan: 02
subsystem: grasshopper-plugin
tags: computgraph, gh-component, http-client, publish
requires: []
provides:
  - DG COMPUTGRAPH PUBLISH Grasshopper component (CGPD-05)
  - ComputgraphPublishClient static HTTP client mirroring ValidationPublishClient pattern
  - ComputgraphPublishRequest/Response DTOs
affects: "Phase 36-04 (ui-v2 Computgraph layer display), Phase 37 (SVAL structural validation)"

tech-stack:
  added: []
  patterns:
    - "Rising-edge boolean trigger for publish (StructureConfirmComponent _lastApply idiom)"
    - "Static HttpClient POST to data-service (ValidationPublishClient precedent)"
    - "#if GRASSHOPPER_SDK / #else stub convention for cross-TFM compilation"
    - "Read-before-write re-extraction chain: ExtractRaw -> Parse -> AssignDgIds -> Serialize"

key-files:
  created:
    - DG/src/DG.Grasshopper/Validation/ComputgraphPublishContract.cs
    - DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs
    - DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs
    - DG/src/DG.Grasshopper/Properties/ComputgraphPublish24.png
  modified:
    - DG/src/DG.Grasshopper/DgIcons.cs

key-decisions:
  - "Separate ComputgraphPublishComponent (not an addition to StructureConfirmComponent) to preserve StructureConfirmComponent's zero-network invariant"
  - "Re-extract fresh canvas on each rising-edge publish (never cache CgContext across solves) — T-36-A3 tampering mitigation"
  - "ComputgraphPublishRequest uses JsonElement for CgContext to avoid schema coupling between client and server"

patterns-established:
  - "Rising-edge Publish trigger: _lastApply=true prevents first-solve auto-fire"
  - "Read-before-write re-extraction chain at solve time"
  - "NormalizeUrl + status-check/throw + empty-body guard on all GH data-service clients"

requirements-completed: [CGPD-05]

coverage:
  - id: D1
    description: "DG COMPUTGRAPH PUBLISH Grasshopper component with rising-edge Publish trigger, re-extraction chain, and HTTP publish to /computgraph/publish"
    requirement: CGPD-05
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release success (0 errors both TFMs)"
        status: pass
      - kind: other
        ref: "GUID uniqueness: grep -ri E2D4A9F1-3C68-4B72-9A05-6D1E8F2C7B30 DG/ returns exactly 1 hit"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-07-19
status: complete
---

# Phase 36 Plan 02: DG COMPUTGRAPH PUBLISH component Summary

**Scalable-pattern-composition add: DG COMPUTGRAPH PUBLISH Grasshopper component with rising-edge trigger, re-extraction chain (ExtractRaw -> Parse -> AssignDgIds -> Serialize), and static HttpClient POST to /computgraph/publish — all #if GRASSHOPPER_SDK-guarded, net7.0/net9.0 cross-TFM build clean (206 lines added)**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-19
- **Completed:** 2026-07-19
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ComputgraphPublishContract.cs with `ComputgraphPublishRequest` (Project, JsonElement CgContext) and `ComputgraphPublishResponse` (Status, StaleEntityIds), both `#if GRASSHOPPER_SDK`-guarded
- ComputgraphPublishClient.cs with static HttpClient, camelCase JSON, NormalizeUrl (defaults to http://localhost:8000), status-check/throw error handling, matching ValidationPublishClient exactly
- ComputgraphPublishComponent.cs: DG COMPUTGRAPH PUBLISH with Project/DataServiceUrl/Publish inputs, Status/StaleEntityIds outputs, rising-edge `_lastApply` trigger, and full re-extraction chain: CanvasContextExtractor -> CanvasAnnotationParser -> CgContextDgIdAssigner -> ComputgraphContextSerializer -> ComputgraphPublishClient.Publish
- DgIcons.cs updated with `ComputgraphPublish24` accessor + ComputgraphPublish24.png placeholder
- Build succeeds on both TFMs (net7.0-windows with GRASSHOPPER_SDK, net9.0 with stubs)

## Task Commits

Each task was committed atomically:

1. **Task 1: ComputgraphPublishContract.cs + ComputgraphPublishClient.cs** - `244b5fc` (feat)
2. **Task 2: ComputgraphPublishComponent.cs + DgIcons entry + icon placeholder** - `91a1587` (feat)

## Files Created/Modified

### Created
- `DG/src/DG.Grasshopper/Validation/ComputgraphPublishContract.cs` - Request/response DTOs (ComputgraphPublishRequest, ComputgraphPublishResponse)
- `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs` - Static HttpClient POST to /computgraph/publish
- `DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs` - DG COMPUTGRAPH PUBLISH GH component with rising-edge trigger
- `DG/src/DG.Grasshopper/Properties/ComputgraphPublish24.png` - Icon placeholder (copy of StructureConfirm24.png)

### Modified
- `DG/src/DG.Grasshopper/DgIcons.cs` - Added `ComputgraphPublish24` icon accessor

## Decisions Made
- **Separate component, not StructureConfirmComponent extension:** The plan specified a separate ComputgraphPublishComponent rather than adding a network call to StructureConfirmComponent, preserving that component's grep-enforced zero-network invariant (Phase 35 locked test coverage).
- **Re-extract fresh on each rising edge (T-36-A3 mitigation):** The SolveInstance always re-extracts from the live canvas document inside the rising-edge branch, never caching a CgContext across solves — matching Phase 35's read-before-write discipline.
- **JsonElement for CgContext:** The request DTO uses `System.Text.Json.JsonElement` (parsed from the serialized string by the client) to avoid schema coupling between the client DTO and the server contract.
- **Icon placeholder:** Copied StructureConfirm24.png as placeholder (follows WR-07 precedent from Phases 34/35 — avoids pink-X missing-icon fallback; replace with bespoke artwork when available).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both tasks compiled clean on first build.

## User Setup Required

None - no external service configuration required. The DataServiceUrl input defaults to "http://localhost:8000" matching the repo's standard data-service endpoint.

## Next Phase Readiness
- DG COMPUTGRAPH PUBLISH component is ready for live-Rhino UAT and Phase 36-04 ui-v2 Computgraph layer display wiring
- The publish path reaches `/computgraph/publish` via ComputgraphPublishClient — no Neo4j driver in the plugin process
- Phase 36-03 (computgraph_publish.py server-side) is the backend counterpart this component POSTs to

## Self-Check

**PASSED** — All verification criteria verified:
- `dotnet build DG/DG.sln -c Release` succeeds (0 errors, 0 warnings, both TFMs)
- GUID `E2D4A9F1-3C68-4B72-9A05-6D1E8F2C7B30` appears exactly once across `DG/`
- All 5 planned files exist and are committed
- Both DTOs are `#if GRASSHOPPER_SDK`-guarded with `#else` stubs
- Request DTO has camelCase keys: `project`, `cgContext`
- Response DTO has `status`, `staleEntityIds`
- `ComputgraphPublishClient.Publish` POSTs to path ending `/computgraph/publish`
- Component uses `_lastApply` rising-edge idiom and re-extraction chain

---
*Phase: 36-computgraph-persistence-display*
*Completed: 2026-07-19*
