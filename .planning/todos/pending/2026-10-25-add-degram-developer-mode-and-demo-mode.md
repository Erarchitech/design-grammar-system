---
created: 2026-10-25T20:27:35.210Z
title: Add DeGram Developer Mode and Demo Mode
area: planning
priority: high
phase: 1301
related_phase: 1309
status: captured
files:
  - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DUAL-MODE.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
  - spec/degram/WORKSPACE.md
  - apps/degram/apps/desktop/
  - apps/degram/degram_variant/
---

## Problem

Owner request, 2026-10-25: adapt DeGram for two explicitly named operating modes as soon as possible, and integrate the work into GSD rather than defer it to a future milestone:

- **Developer Mode** — continued development and internal testing against DG on localhost.
- **Demo Mode** — testing against the DG stand hosted on the Contabo server.

Local development must remain usable after the stand becomes available. Replacing a global DG URL is not sufficient: authentication, active project/company, web content, agent context and native bridge operations must not accidentally cross environments. The existing deployed stand does not prove that the DeGram client supports switching targets.

## Solution

Delivery owner: **Phase 1301** (client configuration, UI and environment isolation), with hosted integration/acceptance coordinated with **Phase 1309 / HOST-05**. New additive requirements **DGMODE-01..04** are outside the original 51 MVP IDs; no existing requirement is reassigned or marked complete.

Planning brief and acceptance matrix: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DUAL-MODE.md`. Schedule this as the next bounded DeGram client follow-up, without waiting for all remaining 1302–1307 work or full HOST-04 recovery closure. Applicable security, client runtime isolation and per-operation authorization gates remain in force.

Implementation breakdown to turn into executable plans:

1. Component: explicit mode/target configuration, persistent selection, compatible migration of the current localhost installation and environment-scoped runtime state.
2. Component: visible mode/target selector and indicator, safe switch lifecycle across embedded DG, authentication, agent relay/tools and local CAD bridges; focused offline and A→B→A integration tests.
3. Framework: exact published component/gitlink integration, test guide, separately authorized build/install and localhost + Contabo live acceptance. Do not claim live success from mocks or a successful build.

No deployment, paid inference, data migration, CAD/graph mutation, component commit or fork push is authorized by this capture. Keep tokens and keys out of planning files. Developer Mode is not an authorization bypass; Demo Mode is not a mock/offline mode.
