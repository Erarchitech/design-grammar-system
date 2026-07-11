# Requirements: Design Grammar System — Milestone v8.1 Platform Setup Regions

**Defined:** 2026-07-11
**Core Value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.
**Milestone goal:** Extend the V2 landing ring with four new region callouts — AI Engine, Connectors, Reasoner, DG API Documentation — each opening a real screen layer wired to backend services.

Archived v8.0 requirements: `.planning/milestones/v8.0-REQUIREMENTS.md`.

## v8.1 Requirements

Requirements for milestone v8.1. Each maps to roadmap phases 810–819.

### Ring Extension (RING)

- [ ] **RING-01**: User sees four new region callouts — AI Engine, Connectors, Reasoner, DG API Docs — placed along the particle ring together with the existing Graph Viewer / Model Viewer / Projects callouts
- [ ] **RING-02**: User can click each new callout to fly into its screen layer with the same transition grammar (520ms scale/opacity, fly-origin from the ring anchor) and back navigation as existing regions
- [ ] **RING-03**: Ring anchor layout distributes all seven callouts without overlap at common desktop viewport sizes

### AI Engine (AIENG)

- [ ] **AIENG-01**: User can select an LLM provider (Anthropic / OpenAI / Ollama) and a model for that provider from the AI Engine screen
- [ ] **AIENG-02**: User can manually input an API key, which is stored encrypted-at-rest via the existing data-service LLM gateway (`/llm/settings`)
- [ ] **AIENG-03**: User can see the currently active provider/model and key status (set / not set) without the key value ever being exposed back to the browser
- [ ] **AIENG-04**: User can test the configured connection and see success/failure feedback with an actionable error message

### Connector Backend (CONNB)

- [ ] **CONNB-01**: data-service exposes endpoints to create, list, and revoke connector credentials, scoped per connector type (14 connectors across 5 categories)
- [ ] **CONNB-02**: Credential tokens are generated server-side, displayed once for copying, and stored hashed/encrypted-at-rest (following the existing llm-settings storage pattern)
- [ ] **CONNB-03**: data-service exposes a token-authenticated heartbeat/ingest endpoint that connector components call from target software; each authenticated call updates that connector's status and last-connection timestamp
- [ ] **CONNB-04**: A status query endpoint returns per-connector activation state (never connected / active / stale) and the last-connection date

### Connectors Screen (CONN)

- [ ] **CONN-01**: User sees 14 connectors grouped in 5 categories — VPL Platforms (Grasshopper, Dynamo), BIM Authoring (Revit, Blender, Tekla, Archicad, Civil3D, Infraworks), BIM Coordination (Navisworks, Solibri), BCF Trackers (BIMCollab, BIMTrack), Visualization (Lumion, Twinmotion)
- [ ] **CONN-02**: User can create a credential for a connector and copy the token for pasting into the connector component within the target software
- [ ] **CONN-03**: User sees each connector's activation status and the date of its last connection (request or post to the Design Grammars platform)
- [ ] **CONN-04**: User can revoke a connector credential, after which the token no longer authenticates

### Reasoner (REAS)

- [ ] **REAS-01**: User can select a reasoner model for the Validation Graph from the Reasoner screen, with HermiT and Pellet offered as selectable entries
- [ ] **REAS-02**: The selected reasoner persists server-side (data-service settings store) and is shown as the active reasoner on revisit
- [ ] **REAS-03**: Placeholder reasoners are clearly marked as "integration pending" so users know selection does not yet change validation behavior

### DG API Documentation (APID)

- [ ] **APID-01**: User can browse DG API documentation in-app in a Revit-API-style structure (sections → classes/endpoints → members, with a navigable tree and detail pane)
- [ ] **APID-02**: Documentation covers the connector-facing API — credential authentication, heartbeat/status, and validation publish endpoints — with request/response examples
- [ ] **APID-03**: Documentation content is extendable: new pages/sections are added via structured content files without touching viewer code

### Integration (INTG)

- [ ] **INTG-01**: End-to-end: a credential created in the Connectors screen authenticates a simulated connector heartbeat, and the resulting status + last-connection date appear in the Connectors screen
- [ ] **INTG-02**: The rebuilt `design-grammars` container ships all four new regions while all v8.0 screens (Graph / Model / Projects, landing, auth) keep working

## Future Requirements

Deferred. Tracked but not in the v8.1 roadmap.

### Reasoner Integration

- **REAS-F01**: Selected reasoner actually drives Validation Graph inference (HermiT/Pellet or successor integrated as a real reasoning service)

### Connectors

- **CONN-F01**: Actual connector plugins for target software (Revit add-in, Dynamo package, etc.) — v8.1 only ships platform-side credentials + API
- **CONN-F02**: Per-credential usage analytics / request logs beyond last-connection date

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Building the connector plugins themselves (GH/Dynamo/Revit components) | v8.1 delivers the platform side: credentials, heartbeat API, docs. Plugins are separate deliverables |
| Real HermiT/Pellet reasoning integration | Placeholders only per milestone brief; real integration when reasoner architecture is elaborated |
| OAuth/token-exchange flows for connectors | Manual copy-paste credential model is the explicit v8.1 design |
| Auto-generated API docs from OpenAPI | Hand-authored structured content files; generation can come later without changing the viewer |
| Mobile layout for new screens | Desktop/web-first for architect workflows (project-wide) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RING-01 | Phase 810 | Pending |
| RING-02 | Phase 810 | Pending |
| RING-03 | Phase 810 | Pending |
| AIENG-01 | Phase 811 | Pending |
| AIENG-02 | Phase 811 | Pending |
| AIENG-03 | Phase 811 | Pending |
| AIENG-04 | Phase 811 | Pending |
| CONNB-01 | Phase 812 | Pending |
| CONNB-02 | Phase 812 | Pending |
| CONNB-03 | Phase 812 | Pending |
| CONNB-04 | Phase 812 | Pending |
| CONN-01 | Phase 813 | Pending |
| CONN-02 | Phase 813 | Pending |
| CONN-03 | Phase 813 | Pending |
| CONN-04 | Phase 813 | Pending |
| REAS-01 | Phase 814 | Pending |
| REAS-02 | Phase 814 | Pending |
| REAS-03 | Phase 814 | Pending |
| APID-01 | Phase 815 | Pending |
| APID-02 | Phase 815 | Pending |
| APID-03 | Phase 815 | Pending |
| INTG-01 | Phase 816 | Pending |
| INTG-02 | Phase 816 | Pending |

**Coverage:**
- v8.1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-11*
*Last updated: 2026-07-11 after roadmap creation*
