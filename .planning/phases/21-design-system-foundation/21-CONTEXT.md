# Phase 21: Design System Foundation - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Every V2 screen builds on one shared, spec-faithful foundation — the light token stylesheet, the Geist/Geist Mono/Oswald type stack, and the reusable component primitives — so phases 22–26 compose instead of restyling. This phase delivers the new V2 app scaffold, tokens, fonts, and the full component library with a specimen page proving them. No screens (landing/graph/model/projects) are built here — those are phases 22–25.

Requirements: DSYS-01 (light token set, achromatic + Signal Red), DSYS-02 (type stack in spec roles), DSYS-03 (primitives matching the design-system recipes).

</domain>

<decisions>
## Implementation Decisions

### App architecture & build
- **D-01:** The V2 UI is a **new Vite + React (JSX, JavaScript)** app. This supersedes the legacy "no JSX build for main UI" decision — that pattern retires with the dark UI. The _ds recipes are already JSX and drop in nearly verbatim.
- **D-02:** **One single V2 app** hosts all four screen layers (landing/graph/model/projects), matching the spec's single-page layered architecture with 520ms transitions. The existing `graph-viewer/model-viewer/` Vite app is NOT reused/reskinned — the V2 Model Viewer screen is rebuilt inside the new app; the old one retires at Phase 26 cutover.
- **D-03:** Plain **JavaScript (JSX)**, not TypeScript — consistent with model-viewer and the .jsx recipe files.
- **D-04:** _ds component recipes are **copied and adapted into the app's `src/components/`**. `design/v2/_ds/` stays untouched as the reference spec; the app owns its copies.

### Token & font delivery
- **D-05:** Copy the token CSS **preserving the 6-file split** (`tokens/{fonts,colors,typography,spacing,effects,base}.css` + `styles.css` entry) into the app's styles directory — keeps diffs against the _ds source easy.
- **D-06:** Fonts are **self-hosted** — Geist, Geist Mono, Oswald woff2 binaries vendored/served locally (no Google Fonts CDN at runtime). Replace the `@import url('https://fonts.googleapis.com/...')` in `tokens/fonts.css` with local `@font-face` rules. Fits the fully self-hosted Docker stack.
- **D-07:** **Oswald stays** as `--font-annotation` (the DIN-condensed substitute). Swappable later via the token + font files; no licensed-font procurement.

### Primitive scope & proof
- **D-08:** Port the **full ~23-component recipe set** from `_ds_manifest.json` (forms: Button/Checkbox/Input/SearchField/Select/Slider/Textarea; display: Avatar/Badge/Callout/Chip/CodeBlock/KVRow/StatBlock/Progress/PropertiesTable; surfaces: Collapsible/CollapsibleItem/Dialog/Panel/RunTile/Tabs/Tile) plus the `.dg-frost` and `.dg-blueprint` CSS primitives and the divergence callout. Phases 22–25 then purely compose.
- **D-09:** A **dev-only `/specimen` route** renders every component in all variants alongside token swatches (like the _ds guideline cards) — the phase's success criteria are verifiable in the browser without waiting for phase 22.

### Legacy coexistence
- **D-10:** The V2 app lives in a **new top-level directory** (sibling of `graph-viewer/`; planner picks the exact name, e.g. `graph-viewer-v2/` or `ui-v2/`). The legacy dark UI keeps serving :8080 untouched until Phase 26 cutover.
- **D-11:** During phases 21–25 the V2 app runs via the **Vite dev server only** against the live Docker backends (nginx proxy at :8080 for Neo4j/n8n/data-service). No new Docker container or compose changes until Phase 26.

### Claude's Discretion
- Exact new directory name (D-10), Vite proxy configuration details, font-file sourcing method (npm package such as `geist`, or downloaded woff2), icon loading approach (Lucide per the _ds readme — CDN vs inlined SVGs), and internal styles organization within components.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec (source of truth)
- `design/v2/Design Grammars V2.dc.html` — interactive mockup of all 4 screen layers + auth; the visual target
- `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/readme.md` — design-system philosophy, color/type/spacing/radii/animation rules, iconography, content voice
- `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/tokens/` — the 6 token CSS files (fonts, colors, typography, spacing, effects, base) to copy
- `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/styles.css` — global entry importing the token files
- `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/_ds_manifest.json` — full component inventory with source paths and token catalog
- `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/components/` — JSX recipes to copy & adapt (forms/, display/, surfaces/)

### Project planning
- `.planning/REQUIREMENTS.md` — DSYS-01..03 definitions and v8.0 scope boundaries
- `.planning/ROADMAP.md` — Phase 21 goal and success criteria

### Existing code (reference for conventions)
- `graph-viewer/model-viewer/vite.config.js` — existing Vite setup in the repo (proxy/dev conventions to mirror)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `design/v2/_ds/.../components/*.jsx` — ~23 ready JSX component recipes; the phase is adoption, not invention
- `graph-viewer/model-viewer/` — existing Vite + React app demonstrating repo conventions (JS, npm, dev-server-against-Docker workflow)

### Established Patterns
- Legacy "no JSX build" decision applied to the retiring dark UI — explicitly superseded for V2 (D-01)
- Repo is JavaScript-everywhere on the frontend; no TypeScript introduced
- Self-hosted-everything Docker stack (Speckle, Ollama local) — motivates self-hosted fonts (D-06)

### Integration Points
- Vite dev server proxies to the existing nginx at :8080 (`/neo4j/`, `/n8n/`, `/data-service/` routes) — no backend changes in v8.0
- Phase 26 will replace the `design-grammars` container content with the V2 build output

</code_context>

<specifics>
## Specific Ideas

- Achromatic discipline is the phase's soul: exactly one chromatic hue (Signal Red `#e7000b`), selection/failure/destructive only; failure vs passing distinguished by weight/fill, never hue
- Pill geometry is strict: 18px interactive, 24px cards, 10px nested, 6px small — "never other values"
- `.dg-frost` = 78% white + 14px backdrop blur + hairline; `.dg-blueprint` = faint 24px drafting grid
- Divergence callout (hexagon marker + hairline leader + Oswald condensed caption) is the signature annotation device
- Specimen page should mirror the _ds guideline cards' organization (Colors / Type / Foundations / Components groups)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 21-design-system-foundation*
*Context gathered: 2026-07-07*
