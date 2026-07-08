# Requirements: Design Grammar System — Milestone v8.0

**Defined:** 2026-07-07
**Core Value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.
**Milestone goal:** Replace the dark legacy web UI with the "Design Grammars V2" light clinical-blueprint interface, implemented as the real product UI wired to the existing Neo4j / n8n / data-service / Speckle backends.

**Design source of truth:** `design/v2/Design Grammars V2.dc.html` (interactive spec, 4 screen layers + auth) and `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/` (tokens, component recipes, readme). The mockup's embedded data is mock; v8.0 replaces it with live backend calls.

Archived v7.0 requirements: `.planning/milestones/v7.0-REQUIREMENTS.md`.

## v8.0 Requirements

### Design System Foundation (DSYS)

- [x] **DSYS-01**: UI renders with the V2 light token set (canvas `#f5f5f5` → sidebar `#fafafa` → card `#ffffff`, ink `#0a0a0a`, hairline `#e5e5e5`, ink-alpha steps) — all surfaces achromatic; Signal Red `#e7000b` appears only for selection, failure, and destructive affordances
- [x] **DSYS-02**: Typography stack loads and applies per spec — Geist (body/headings), Geist Mono (data values, ids, code), Oswald (uppercase annotation captions, +1.2px tracking)
- [x] **DSYS-03**: Reusable UI primitives match the design-system recipes — Button/Input pill geometry (18px interactive, 24px cards), `.dg-frost` panels (78% white + 14px backdrop blur + hairline), `.dg-blueprint` 24px drafting grid, divergence callout (hexagon marker + hairline leader + condensed caption)

### Landing (LAND)

- [x] **LAND-01**: User sees the particle-ring landing hero on load — canvas particle cloud with "DESIGN GRAMMARS. / Encode your design intent." title materialising from it
- [x] **LAND-02**: User can navigate to Graph Viewer, Model Viewer, or Projects via the region callout labels anchored to the particle ring
- [x] **LAND-03**: Landing reflects session state — guest sees Login/Register CTA; member sees name, red status dot, "System initiated" annotation, and Sign out

### Authentication (AUTH)

- [x] **AUTH-01**: User can log in (email + password) via the inline frost card that rises through the particles on the landing screen
- [x] **AUTH-02**: User can register (full name + email + password) via the same card's mode switch
- [x] **AUTH-03**: Auth errors render inline in Signal Red; user can cancel back to the hero at any point
- [x] **AUTH-04**: User can sign out from the landing member state

### Graph Viewer (GVIEW)

- [x] **GVIEW-01**: Canvas datascape renders the real project-scoped Neo4j metagraph as ink arcs and dots (translucent black edges, achromatic nodes), with idle drift and divergence field per design defaults
- [x] **GVIEW-02**: User can select a node — red dot + signal halo + divergence callout; node-details panel shows label chip and properties table
- [x] **GVIEW-03**: User can submit natural-language rules from the persistent prompt bar; the rules-ingest n8n webhook is called and the response appears under the prompt in the extended session panel
- [x] **GVIEW-04**: User can query the graph in natural language (mode select on prompt bar → graph-query n8n webhook) and read the answer in the session panel
- [x] **GVIEW-05**: User can search nodes via the search bar with results popover, and jump to a result on the canvas

### Model Viewer (MVIEW)

- [x] **MVIEW-01**: User can browse validation runs fetched from data-service — run mode sidebar with KV rows and failing/passing collapsible groups
- [x] **MVIEW-02**: User can inspect a geometry instance — instance mode with hover panel and selection panel
- [x] **MVIEW-03**: Map canvas with minimap and zoom renders the model layout with validation colouring — red for failing entities, ink/gray for passing/base
- [x] **MVIEW-04**: Orbit legend and rule panel (SWRL code block) display for the selected run

### Projects (PROJ)

- [x] **PROJ-01**: User sees the project tile grid backed by real project data (projects present in Neo4j)
- [x] **PROJ-02**: User can open a project, which scopes Graph Viewer and Model Viewer queries to that project

### Navigation Shell (NAV)

- [x] **NAV-01**: Four screen layers (landing / graph / model / projects) switch with the spec's 520ms scale+opacity transition; Back returns to landing
- [x] **NAV-02**: Global chrome (screen titles, connection annotation, mono subtitles) renders per design on every screen

### Deployment Cutover (DEPL)

- [x] **DEPL-01**: The V2 UI ships as the `design-grammars` container at :8080, replacing the dark legacy SPA
- [x] **DEPL-02**: End-to-end parity check passes — every workflow the legacy UI supported (rule ingest, graph query, graph browse, validation run browsing, project scoping) works in the V2 UI against live Docker services

### Model Viewer 3D Embed (MVIEW3D) — post-ship addendum, Phase 27 (2026-07-08)

<!-- Promoted from Future Requirements after v8.0 shipped; executed as Phase 27 -->

- [x] **MVIEW3D-01**: ModelScreen renders an interactive 3D viewport using the embedded Speckle viewer (replacing the synthetic SVG isometric boxes) — entity selection, zoom, pan, and orbit all work
- [x] **MVIEW3D-02**: Validation colouring is applied to Speckle geometry — Signal Red for failing entities, ink/gray for passing/base — matching the SVG map colour scheme
- [x] **MVIEW3D-03**: The SVG map remains available as a fallback toggle; run browsing, instance inspection, and the SWRL rule panel work unchanged in 3D mode

## Future Requirements

<!-- Valid but deferred beyond v8.0 -->

- Graphics settings toolbar (checkbox filters, colour swatches, opacity sliders, select-by-id) from the v1 Model Viewer — re-add after V2 map ships
- Per-run screenshot persistence UI in V2 skin

## Out of Scope

- OAuth/SSO — client-side auth per existing RegisterForm approach remains sufficient
- Mobile layout — desktop-first for architect workflows (spec is desktop-proportioned)
- Dark mode — V2 system is deliberately the light reskin; legacy dark UI retires
- Editing rules from the Graph Viewer node-details panel — read + add-property only per spec; full rule editing stays in the prompt workflow
- New backend endpoints — v8.0 consumes existing Neo4j proxy, n8n webhooks, and data-service routes only; backend changes belong to v9.0

## Traceability

| Requirement | Phase |
|-------------|-------|
| DSYS-01 | 21 |
| DSYS-02 | 21 |
| DSYS-03 | 21 |
| NAV-01 | 22 |
| NAV-02 | 22 |
| LAND-01 | 22 |
| LAND-02 | 22 |
| LAND-03 | 22 |
| AUTH-01 | 22 |
| AUTH-02 | 22 |
| AUTH-03 | 22 |
| AUTH-04 | 22 |
| GVIEW-01 | 23 |
| GVIEW-02 | 23 |
| GVIEW-03 | 23 |
| GVIEW-04 | 23 |
| GVIEW-05 | 23 |
| MVIEW-01 | 24 |
| MVIEW-02 | 24 |
| MVIEW-03 | 24 |
| MVIEW-04 | 24 |
| PROJ-01 | 25 |
| PROJ-02 | 25 |
| DEPL-01 | 26 |
| DEPL-02 | 26 |
| MVIEW3D-01 | 27 |
| MVIEW3D-02 | 27 |
| MVIEW3D-03 | 27 |

**Coverage:** 28/28 requirements mapped — 100% ✓

---
*28 requirements across 9 categories (MVIEW3D added post-ship with Phase 27, 2026-07-08)*
