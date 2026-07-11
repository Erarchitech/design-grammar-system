# Roadmap: Design Grammar System

## Milestones

- 🔄 **v8.1 Platform Setup Regions** — Phases 810-816 (active; started 2026-07-11; first milestone on the vX.Y → X·100+Y·10 phase-numbering convention)
- ✅ **v8.0 Design Grammars V2 UI** — Phases 21-27 (shipped 2026-07-07; Phase 27 Speckle 3D Embed added post-ship, completed 2026-07-08) → [requirements](milestones/v8.0-REQUIREMENTS.md) | [roadmap](milestones/v8.0-ROADMAP.md) | [phases](milestones/v8.0-phases/)
- ⏸ **v9.0 AI Workflow Intelligence** — Phases 28-40 (paused; Phase 28 executed 2026-07-06; restructured 2026-07-08: GH canvas → Computgraph serialization pipeline elaborated into Phases 32-37; renumbered from milestone-local 1-13) → [requirements](milestones/v9.0-REQUIREMENTS.md) | [roadmap](milestones/v9.0-ROADMAP.md) | [phases](milestones/v9.0-phases/)
- 📋 **v10.0 Script Intelligence** — Phases 41-49 (planned 2026-07-08, isolated; activates after v9.0; renumbered from milestone-local 1-9) → [requirements](milestones/v10.0-REQUIREMENTS.md) | [roadmap](milestones/v10.0-ROADMAP.md)
- 📋 **v4.0 BOT Ontology Bridge** — Phases 1-4 (planned) → [requirements](milestones/v4.0-REQUIREMENTS.md) | [roadmap](milestones/v4.0-ROADMAP.md)
- ✅ **v7.0 Update of DG Addin for Grasshopper** — Phases 13-20 (shipped 2026-07-05) → [requirements](milestones/v7.0-REQUIREMENTS.md) | [roadmap](milestones/v7.0-ROADMAP.md) | [phases](milestones/v7.0-phases/)
- ⛔ **v3.0 Typed Variables and Composable Design State** — Superseded 2026-07-02 (Phase 7 shipped, carried into v7.0) → [archive](milestones/v3.0-ROADMAP.md)
- ✅ **v2.0 DG Plugin - Design State and Validation Runs** — Phases 1-6 (shipped 2026-05-10) → [archive](milestones/v2.0-ROADMAP.md)
- ✅ **v1.1 Project Knowledge Graph** — Phases 1-7 (shipped 2026-04-10) → [archive](milestones/v1.1-phases/)

## Milestone v8.1: Platform Setup Regions

**Goal:** Four new setup regions along the V2 landing ring — AI Engine, Connectors, Reasoner, DG API Documentation — each a real screen layer wired to backend services.

**Phase numbering:** 810–816 (convention: milestone vX.Y → phases from X·100+Y·10; max 10 per milestone).

### Phase Overview

| # | Phase | Goal | Requirements | Depends on |
|---|-------|------|--------------|------------|
| 810 | Ring Extension & Screen Shell | 7 callouts on the ring, 4 new navigable screen layers | RING-01..03 | — |
| 811 | AI Engine Screen | LLM provider/model/API-key setup over the existing gateway | AIENG-01..04 | 810 |
| 812 | Connector Credential Backend | data-service credential CRUD + heartbeat/status API | CONNB-01..04 | — |
| 813 | Connectors Screen | 14 connectors / 5 categories UI with credentials + status | CONN-01..04 | 810, 812 |
| 814 | Reasoner Screen | 1/1 | Complete    | 2026-07-11 |
| 815 | DG API Documentation | 1/1 | Complete | 2026-07-11 |
| 816 | Integration & Deployment | E2E credential→heartbeat→status flow, container cutover | INTG-01..02 | 811–815 |

### Phase 810: Ring Extension & Screen Shell

**Goal:** The landing ring shows all seven region callouts and each new callout flies into its own (initially skeletal) screen layer.

**Requirements:** RING-01, RING-02, RING-03

**Success criteria:**

1. Landing shows AI Engine, Connectors, Reasoner, and DG API Docs callouts along the particle ring beside Graph Viewer / Model Viewer / Projects, without overlap at common desktop sizes
2. Clicking any new callout flies into its screen layer with the standard 520ms transition originating from its ring anchor
3. Each new screen has back navigation to the landing, matching existing screens
4. Existing three regions behave exactly as before (no regression in anchors, hero, auth)

### Phase 811: AI Engine Screen

**Goal:** Users configure the platform LLM (provider, model, API key) from the AI Engine region, backed by the existing data-service LLM gateway.

**Requirements:** AIENG-01, AIENG-02, AIENG-03, AIENG-04

**Success criteria:**

1. User selects provider (Anthropic / OpenAI / Ollama) and model; the choice persists via `/llm/settings`
2. User enters an API key that is stored encrypted-at-rest; the UI shows only set/not-set status, never the key
3. User runs a connection test and gets clear success/failure feedback
4. The Graph Viewer prompt console continues to work against the newly configured provider

### Phase 812: Connector Credential Backend

**Goal:** data-service can mint, list, and revoke connector credentials and track per-connector connection status via an authenticated heartbeat endpoint.

**Requirements:** CONNB-01, CONNB-02, CONNB-03, CONNB-04

**Success criteria:**

1. Credentials can be created/listed/revoked per connector type via REST; the 14-connector / 5-category registry is served by the API
2. Tokens are generated server-side, returned once, and stored hashed/encrypted (llm-settings storage pattern)
3. A token-authenticated heartbeat call updates the connector's status and last-connection timestamp; revoked/unknown tokens are rejected
4. Status endpoint reports never-connected / active / stale + last-connection date per connector; covered by pytest tests

### Phase 813: Connectors Screen

**Goal:** The Connectors region shows all connectors by category with credential creation, copy-once tokens, activation status, and last-connection dates.

**Requirements:** CONN-01, CONN-02, CONN-03, CONN-04

**Success criteria:**

1. All 14 connectors render grouped in the 5 categories from the milestone brief
2. User creates a credential and copies the token (shown once) for pasting into the target software's connector component
3. Each connector shows activation status and last-connection date from the status endpoint
4. User can revoke a credential and the UI reflects the deactivation

### Phase 814: Reasoner Screen

**Goal:** The Reasoner region lets users select the Validation Graph reasoner, with HermiT and Pellet as clearly-labeled placeholders.

**Requirements:** REAS-01, REAS-02, REAS-03

**Success criteria:**

1. User selects HermiT or Pellet from the Reasoner screen
2. Selection persists server-side and is shown as active on revisit
3. Placeholder entries carry an explicit "integration pending" annotation

### Phase 815: DG API Documentation

**Goal:** The DG API Docs region hosts a Revit-API-style documentation browser for connector developers, driven by extendable structured content.

**Requirements:** APID-01, APID-02, APID-03

**Success criteria:**

1. User navigates a tree (sections → endpoints/classes → members) with a detail pane, Revit-API-doc style
2. Connector-facing API is documented end-to-end: credential auth, heartbeat/status, validation publish — with request/response examples
3. Adding a new doc page requires only adding a structured content file (no viewer code change)

### Phase 816: Integration & Deployment

**Goal:** The full connector lifecycle works end-to-end and the rebuilt container ships all four regions without v8.0 regressions.

**Requirements:** INTG-01, INTG-02

**Success criteria:**

1. A credential created in the Connectors screen authenticates a simulated heartbeat (curl/script), and the status + last-connection date update in the UI
2. `docker compose build --no-cache design-grammars` ships all seven regions; Graph / Model / Projects / landing / auth still pass their v8.0 smoke checks

---
*Roadmap created: 2026-07-11 — milestone v8.1 Platform Setup Regions*
