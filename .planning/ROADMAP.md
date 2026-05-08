# Roadmap: Design Grammar System

## Milestones

- [ ] **v2.0 DG Plugin - Design State and Validation Runs** - Phases 1-6 (in progress)
- [x] **v1.1 Project Knowledge Graph** - Phases 1-7 (shipped 2026-04-10)

## Phases

### v2.0 DG Plugin - Design State and Validation Runs

- [x] Phase 1: Design State Contract and Serialization (completed 2026-04-30)
- [x] Phase 2: Classificator State Input and Run Persistence (completed 2026-04-30)
- [x] Phase 3: Validation Runs Retrieval Component (completed 2026-04-30)
- [x] Phase 4: Reinstatement Component (completed 2026-05-07)
- [ ] Phase 5: Model Viewer Grouping by Rule and State
- [ ] Phase 6: End-to-End Hardening and Verification

#### v2.0 Planning Details

**Phase 1**
- Requirements: DGST-01, DGST-02
- Plans: 01-01-PLAN.md

**Phase 2**
- Requirements: DGST-03, DGCL-01, DGCL-02
- Plans: 02-01-PLAN.md

**Phase 3**
- Requirements: DGCL-03, DGRN-01, DGRN-02, DGRN-03
- Plans: 03-01-PLAN.md

**Phase 4**
- Requirements: REIN-01, REIN-02, REIN-03
- Plans: 2 plans
  - [x] 04-01-PLAN.md � Core result models + validation service + tests
  - [x] 04-02-PLAN.md � GH ReinstateComponent with trigger and target resolution

**Phase 5**
- Requirements: MVGP-01, MVGP-02, MVGP-03
- Plans: 05-01-PLAN.md

**Phase 6**
- Requirements: INTG-01, INTG-02, INTG-03
- Plans: 3 plans
  - [x] 06-01-PLAN.md � C# error contracts + GH component hardening
  - [x] 06-02-PLAN.md � Data-service + model-viewer error hardening
  - [x] 06-03-PLAN.md � E2E integration tests + verification + UAT

### v1.1 Project Knowledge Graph (Shipped)

- [x] Phase 1: Neo4j Schema Foundation
- [x] Phase 2: data-service CRUD + Folder Ingest
- [x] Phase 3: n8n Knowledge Workflows + LLM Ingest and Query
- [x] Phase 4: Update Flow Endpoints
- [x] Phase 5: UI Mode Restructuring + Insert and Query Panels
- [x] Phase 6: UI Update Panel + Inline Diff Editor
- [x] Phase 7: UI Session History Panel + NeoVis Knowledge View

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Design State Contract and Serialization | v2.0 | 1/1 | Complete | 2026-04-30 |
| 2. Classificator State Input and Run Persistence | v2.0 | 1/1 | Complete   | 2026-04-30 |
| 3. Validation Runs Retrieval Component | v2.0 | 1/1 | Complete | 2026-04-30 |
| 4. Reinstatement Component | v2.0 | 2/2 | Complete | 2026-05-07 |
| 5. Model Viewer Grouping by Rule and State | v2.0 | 0/1 | Planned | - |
| 6. End-to-End Hardening and Verification | v2.0 | 0/3 | Planned | - |

---
*Roadmap updated: 2026-05-07*
