# Roadmap: Design Grammar System

## Milestones

- 🔄 **v8.0 Design Grammars V2 UI** — Phases 21-26 (active)
- ⏸ **v9.0 AI Workflow Intelligence** — Phases 1-8 (paused; Phase 01 executed 2026-07-06, parked) → [requirements](milestones/v9.0-REQUIREMENTS.md) | [roadmap](milestones/v9.0-ROADMAP.md) | [phases](milestones/v9.0-phases/)
- 📋 **v4.0 BOT Ontology Bridge** — Phases 1-4 (planned) → [requirements](milestones/v4.0-REQUIREMENTS.md) | [roadmap](milestones/v4.0-ROADMAP.md)
- ✅ **v7.0 Update of DG Addin for Grasshopper** — Phases 13-20 (shipped 2026-07-05) → [requirements](milestones/v7.0-REQUIREMENTS.md) | [roadmap](milestones/v7.0-ROADMAP.md) | [phases](milestones/v7.0-phases/)
- ⛔ **v3.0 Typed Variables and Composable Design State** — Superseded 2026-07-02 (Phase 7 shipped, carried into v7.0) → [archive](milestones/v3.0-ROADMAP.md)
- ✅ **v2.0 DG Plugin - Design State and Validation Runs** — Phases 1-6 (shipped 2026-05-10) → [archive](milestones/v2.0-ROADMAP.md)
- ✅ **v1.1 Project Knowledge Graph** — Phases 1-7 (shipped 2026-04-10) → [archive](milestones/v1.1-phases/)

## Phases

### v8.0 — Design Grammars V2 UI

Design source of truth: `design/v2/Design Grammars V2.dc.html` + `design/v2/_ds/` design system. Full replacement of the dark legacy SPA, wired to real backends (Neo4j proxy, n8n webhooks, data-service, Speckle).

- [ ] **Phase 21: Design System Foundation** — Light token set, type stack, and reusable primitives (frost, blueprint grid, callout, pill controls) as the shared base for all screens
- [ ] **Phase 22: Navigation Shell, Landing and Auth** — Layered screen architecture with transitions, particle-ring landing hero, region navigation, inline login/register with session state
- [ ] **Phase 23: Graph Viewer** — Canvas datascape from live Neo4j metagraph, node selection with divergence callouts, prompt bar wired to n8n ingest/query webhooks, session panel, search
- [ ] **Phase 24: Model Viewer** — Validation runs from data-service, run/instance modes, map canvas + minimap + zoom, orbit legend, rule SWRL panel
- [ ] **Phase 25: Projects and Scoping** — Project tile grid from live data; opening a project scopes Graph and Model viewer queries
- [ ] **Phase 26: Deployment Cutover and E2E Parity** — V2 UI ships as the design-grammars container at :8080; legacy workflows verified end-to-end against live Docker services

---

## Phase Details

### Phase 21: Design System Foundation

**Goal**: Every V2 screen builds on one shared, spec-faithful foundation — tokens, fonts, and primitives — so later phases compose instead of restyling
**Depends on**: Nothing (universal prerequisite for phases 22–26)
**Requirements**: DSYS-01, DSYS-02, DSYS-03
**Success Criteria** (what must be TRUE):

  1. A token stylesheet derived from `design/v2/_ds/tokens/` loads in the app; rendered surfaces use the canvas/sidebar/card three-tone stack and no chromatic colour other than Signal Red `#e7000b`
  2. Geist, Geist Mono, and Oswald render in their spec roles (body/headings, data values and code, uppercase annotation captions)
  3. Button/Input/frost-panel/blueprint-grid/divergence-callout primitives render consistent with the design-system recipes — 18px pill radius on interactive elements, 24px on cards, 1px hairline borders, 78% white + 14px backdrop blur on frost

### Phase 22: Navigation Shell, Landing and Auth

**Goal**: The app opens on the V2 landing experience — the user can move between all four screen layers and authenticate without leaving the landing
**Depends on**: Phase 21 (primitives, tokens)
**Requirements**: NAV-01, NAV-02, LAND-01, LAND-02, LAND-03, AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):

  1. Landing shows the particle-ring hero canvas with the materialising "DESIGN GRAMMARS." title; region callouts navigate to Graph Viewer / Model Viewer / Projects with the 520ms scale+opacity transition, and Back returns to landing
  2. A guest sees the Login/Register CTA; submitting valid credentials via the rising frost card signs the user in and the hero switches to the member state (name, red status dot, "System initiated" annotation, Sign out)
  3. Register mode collects full name + email + password via the same card's mode switch; auth errors render inline in Signal Red; Cancel returns to the hero
  4. Global chrome (screen title, mono connection subtitle) renders on every non-landing screen

### Phase 23: Graph Viewer

**Goal**: The datascape is real — the user browses, queries, and extends the live project metagraph from the V2 canvas
**Depends on**: Phase 22 (shell navigation, session state)
**Requirements**: GVIEW-01, GVIEW-02, GVIEW-03, GVIEW-04, GVIEW-05
**Success Criteria** (what must be TRUE):

  1. The canvas renders nodes/edges fetched from Neo4j (project-scoped, via the nginx proxy) as translucent ink arcs and achromatic dots with idle drift and divergence field per design defaults
  2. Clicking a node shows the red selection halo + divergence callout and populates the node-details panel with the node's live label chip and properties table
  3. Sending a rule from the persistent prompt bar calls the rules-ingest n8n webhook and the outcome appears under the prompt in the extended session panel; query mode does the same via the graph-query webhook
  4. Search finds live nodes via the search bar popover and centres the canvas on the chosen result

### Phase 24: Model Viewer

**Goal**: Validation results are browsable in the V2 skin — runs, failing/passing breakdowns, and per-instance inspection over the map canvas
**Depends on**: Phase 22 (shell); parallel-safe with Phase 23
**Requirements**: MVIEW-01, MVIEW-02, MVIEW-03, MVIEW-04
**Success Criteria** (what must be TRUE):

  1. The run list loads from data-service validation endpoints; selecting a run populates KV rows and failing/passing collapsible groups
  2. The map canvas colours failing entities Signal Red and passing/base entities ink/gray, with working minimap and zoom
  3. Instance mode shows hover and selection panels for individual geometry entities
  4. The rule panel displays the selected run's SWRL verbatim in mono; the orbit legend renders per spec

### Phase 25: Projects and Scoping

**Goal**: Projects are first-class — the user picks a project and every viewer works within it
**Depends on**: Phases 23–24 (viewers exist to be scoped)
**Requirements**: PROJ-01, PROJ-02
**Success Criteria** (what must be TRUE):

  1. The Projects screen lists real projects from the database as V2 tiles
  2. Opening a project scopes subsequent Graph Viewer and Model Viewer data to that project — verified by switching projects and observing different data

### Phase 26: Deployment Cutover and E2E Parity

**Goal**: V2 is the product UI — served by the design-grammars container with no workflow regressions against the legacy SPA
**Depends on**: Phases 21–25
**Requirements**: DEPL-01, DEPL-02
**Success Criteria** (what must be TRUE):

  1. `docker compose up` serves the V2 UI at :8080 through the existing nginx reverse-proxy routes
  2. The E2E parity checklist passes against live services: rule ingest, graph query, graph browse, validation run browsing, project scoping
  3. The legacy dark SPA is retired (removed or archived) with release notes

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 21. Design System Foundation | 0/? | Not started | — |
| 22. Navigation Shell, Landing and Auth | 0/? | Not started | — |
| 23. Graph Viewer | 0/? | Not started | — |
| 24. Model Viewer | 0/? | Not started | — |
| 25. Projects and Scoping | 0/? | Not started | — |
| 26. Deployment Cutover and E2E Parity | 0/? | Not started | — |

---

*Roadmap updated: 2026-07-07 — v8.0 Design Grammars V2 UI defined (phases 21-26, 25 requirements); v7.0 archived to milestones/*
*v7.0 shipped: 2026-07-05*
*v2.0 shipped: 2026-05-10*
