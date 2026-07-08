---
phase: 27-speckle-3d-embed
status: Ready for planning
gathered: 2026-07-08
source: audit-fix F-02 (deferred from Phase 24)
---

# Phase 27: Speckle 3D Embed — Context

## Phase Boundary

Replace the synthetic SVG isometric boxes in `ModelScreen.jsx` (lines 20–57) with an embedded Speckle 3D viewer rendering real BIM geometry. The V2 Model Viewer currently renders deterministic hash-derived SVG boxes; real 3D geometry exists in Speckle and is viewable only through the legacy `graph-viewer/model-viewer/` app. This phase brings the real geometry into the V2 UI.

**In scope:**
- Embed Speckle 3D viewer in V2 ModelScreen (replacing or toggling SVG map)
- Validation color overlay on Speckle geometry (Signal Red = failing, ink/gray = passing)
- Entity selection/interaction in 3D (click entity → instance mode in sidebar)
- Fallback toggle (3D / SVG map) for degraded scenarios

**Out of scope:**
- Modifying the Speckle publish pipeline (already creates colored geometry)
- Changes to the legacy `graph-viewer/model-viewer/` app
- Grasshopper plugin changes
- Neo4j schema changes

<decisions>
## Implementation Decisions

### D-01: Integration Approach
**Locked.** Use `@speckle/viewer` npm package directly in the V2 React app (NOT iframe embedding of the legacy viewer). Rationale: native React integration enables event handling (entity click → instance mode), styling consistency with V2 design system, and avoids cross-origin iframe complexity. The `@speckle/viewer` package provides a `Viewer` class that accepts an HTML container element, auth token, and stream/object IDs.

### D-02: Viewer Lifecycle
**Locked.** The Speckle viewer instance is created when a validation run is selected and destroyed on run change / unmount. Viewer state (camera position, selection) resets per run. This matches the current SVG map behavior where `viewBox` resets on run change.

### D-03: Auth Token Flow
**Locked.** The Speckle viewer auth token is fetched from the data-service (new endpoint or existing integration config endpoint). The token is NOT stored in the UI codebase or env vars exposed to the browser. The data-service already manages Speckle tokens for publishing; it will serve a read-only token for the viewer.

### D-04: Geometry Color Mapping
**Locked.** The data-service publish pipeline already creates Speckle versions with per-entity colors (Signal Red for failing, ink/gray for passing). The viewer receives the Speckle version ID and renders geometry as-is — no client-side recoloring needed. Color mapping is consistent with the existing SVG scheme (fail = `#e7000b`, pass = ink/gray).

### D-05: Entity Selection → Instance Mode
**Locked.** Clicking a Speckle object in the 3D viewport triggers the same `pick(dgEntityId)` flow used by the SVG map. The Speckle viewer's object selection event provides the Speckle object ID, which maps to `dgEntityId` via the existing entity metadata. The Properties sidebar switches to instance mode showing per-rule pass/fail.

### D-06: Fallback Toggle
**Locked.** A "3D / Map" toggle in the toolbar switches between Speckle 3D and the existing SVG map. The SVG map is preserved as-is (not removed). Default: 3D when Speckle is available, map as fallback when Speckle viewer fails to initialize (e.g., missing token, network error).

<deferred>
### Claude's Discretion
- Exact React component structure for the Speckle viewer wrapper (`SpeckleViewport.jsx` vs inline in ModelScreen)
- npm dependency version (`@speckle/viewer` — use latest stable)
- Viewer configuration defaults (camera position, lighting, background color matching V2 blueprint aesthetic)
- Loading/error state UI treatment in the viewport area
- Mobile/responsive behavior of the 3D viewport
- Whether to persist camera state per design-state (stretch goal, not required)
</deferred>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### V2 UI — Model Viewer
- `ui-v2/src/screens/ModelScreen.jsx` — Current ModelScreen with SVG map (lines 20–57: hash/box functions; lines 238–301: zoom/pan/minimap; lines 468–528: SVG viewport)
- `ui-v2/src/lib/modelApi.js` — Data-service API client (fetchValidationRuns, fetchValidationView, fetchEntityStatuses)
- `ui-v2/src/components/index.js` — Available V2 design-system primitives
- `ui-v2/package.json` — Current dependencies (React 18, Vite 5)

### Speckle Pipeline
- `data-service/app.py` — Validation publish endpoint, Speckle integration config, `_auto_configure_integration()`
- `data-service/speckle_validation.py` — Speckle publishing logic (geometry coloring, version creation)
- `graph-viewer/model-viewer/` — Legacy Speckle 3D viewer (reference for viewer API usage and token flow)

### Design System
- `ui-v2/src/styles/tokens/` — V2 token files (colors, typography, spacing)
- `.planning/milestones/v8.0-phases/24-model-viewer/24-01-PLAN.md` — Original Model Viewer plan (deferred Speckle embed)
- `CLAUDE.md` — Project architecture and service map

### Docker / Deployment
- `docker-compose.yml` — Speckle service stack (speckle-server, speckle-frontend, speckle-db, etc.)
- `ui-v2/Dockerfile` — V2 UI build (node → nginx)
- `ui-v2/nginx.conf` — Reverse proxy routes
</canonical_refs>

<specifics>
## Specific Requirements

1. **3D Viewport renders real Speckle geometry** — No more synthetic boxes. The Speckle viewer shows actual BIM geometry (buildings, walls, volumes) from the published validation version.
2. **Validation colors on geometry** — Entities are colored: Signal Red (`#e7000b`) for failing, ink/gray for passing. This coloring is done server-side during Speckle publish (already implemented).
3. **Click-to-inspect** — Clicking a 3D object selects it and opens instance mode in the Properties sidebar, identical to the current SVG map behavior.
4. **3D/Map toggle** — Toolbar toggle switches between Speckle 3D and the existing SVG map.
5. **No regression** — Run browsing, design-state grouping, failing/passing lists, SWRL rule panel, minimap (map mode), zoom/pan (map mode), and all existing toolbar controls continue to work.
</specifics>

<deferred>
## Deferred Ideas

- Camera state persistence across runs/design-states (nice-to-have, not required)
- Measurement tools in 3D viewport
- Section planes / cutaway views
- Multi-run comparison overlay in 3D
- Mobile touch support for 3D viewport
</deferred>

---
*Phase: 27-speckle-3d-embed*
*Context gathered: 2026-07-08 via audit-fix F-02 escalation from Phase 24*
