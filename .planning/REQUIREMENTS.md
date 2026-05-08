# Requirements: Design Grammar System v2.0 - DG Plugin Design State and Validation Runs

**Defined:** 2026-04-10
**Core Value:** Architects can save parameterized design states with each validation run and reliably reinstate those states in Grasshopper to compare alternatives quickly.

## v2.0 Requirements

### Design State Capture

- [x] **DGST-01**: Grasshopper provides a DESIGN STATE component that accepts Number, Integer, and Boolean inputs and serializes them into a reusable state object
- [x] **DGST-02**: Serialized design state includes stable parameter identifiers, display names, typed values, and capture timestamp
- [x] **DGST-03**: Design state payload can be attached to validation execution without breaking existing validation flow

### Classificator and Validation Persistence

- [x] **DGCL-01**: Classificator component accepts optional State input from DESIGN STATE
- [x] **DGCL-02**: Validation run persistence stores design state payload alongside run metadata in Neo4j
- [x] **DGCL-03**: Persisted validation run remains project-isolated and queryable by rule and state

### Validation Runs Retrieval

- [x] **DGRN-01**: VALIDATION RUNS component returns run list for selected project/stream
- [x] **DGRN-02**: VALIDATION RUNS supports optional Rule filter and optional State filter
- [x] **DGRN-03**: VALIDATION RUNS outputs Runs, Results, and States collections in a deterministic schema

### Reinstatement

- [x] **REIN-01**: REINSTATE component accepts States output and applies values back to matching Grasshopper parameters
- [x] **REIN-02**: Reinstatement is trigger-based (button/boolean) and does not auto-apply on wire change
- [x] **REIN-03**: Reinstatement reports per-parameter apply status (applied, missing target, type mismatch)

### Model Viewer Grouping

- [ ] **MVGP-01**: Validation Runs strip supports grouping by Rule
- [ ] **MVGP-02**: Validation Runs strip supports grouping by Design State
- [ ] **MVGP-03**: Grouping switch is user-selectable and preserves filter context

### Integration and Safety

- [x] **INTG-01**: End-to-end flow works: DESIGN STATE -> Classificator validation -> Neo4j persistence -> VALIDATION RUNS retrieval -> REINSTATE apply
- [x] **INTG-02**: Existing rule validation workflow continues to operate when no DESIGN STATE is provided
- [x] **INTG-03**: Serialization, persistence, and reinstatement errors are surfaced as actionable user-facing messages

## Out of Scope

| Feature | Reason |
|---------|--------|
| Arbitrary object/geometry serialization in DESIGN STATE | v2.0 is limited to Number, Integer, Boolean primitives for deterministic reinstatement |
| Full version history UI for state diffs | Not required for first usable reinstatement loop |
| Cross-project state sharing | Project isolation remains mandatory |
| Automatic periodic snapshotting | Explicit user capture keeps intent clear and payload sizes bounded |

## Traceability

| Requirement | Phase | Status | Notes |
|-------------|-------|--------|-------|
| DGST-01 | Phase 1 (+ retro Phase 3.1) | Validated | Data contracts in Phase 1; **DESIGN STATE GH component added retroactively in commit `b73e8d9`**. Live UAT 2026-05-05 confirmed canvas usage. |
| DGST-02 | Phase 1 | Validated | `DesignStateParameter` model has `ParameterId`, `DisplayName`, typed values, `CapturedAtUtc`. Live UAT confirmed serialization round-trip. |
| DGST-03 | Phase 2 (+ retro Phase 3.1) | Validated | Persistence chain wired end-to-end in commit `d856ca4`. Live UAT 2026-05-05 confirmed state attaches to runs without breaking legacy flow. |
| DGCL-01 | Phase 2 | Validated | Optional State input on Classificator (index 3); pass-through output added in `d856ca4`. Live UAT confirmed wiring works. |
| DGCL-02 | Phase 2 (+ retro Phase 3.1) | Validated | **Original Phase 2 only built helper methods — actual Neo4j write path added in `d856ca4`**. Live UAT 2026-05-05 confirmed `run.statePayloadJson` populated in Neo4j. |
| DGCL-03 | Phase 3 | Validated | Cypher uses `{project:$project}`; rule + state filters work. Live UAT confirmed filters correctly narrow result set. |
| DGRN-01 | Phase 3 | Validated | `ValidationRunsComponent` queries by project. Live UAT confirmed run list populates. |
| DGRN-02 | Phase 3 | Validated | Both Rule and State filters wired. Live UAT 2026-05-05 confirmed all three filter modes (unfiltered, rule, state) return correct subsets. |
| DGRN-03 | Phase 3 | Validated | Sorted via `StringComparer.Ordinal`; deterministic schema. Live UAT confirmed `States` output is non-empty for runs with attached state. |
| REIN-01 | Phase 4 | Validated | ReinstateComponent accepts State input, resolves targets via DesignStateComponent, writes values via ScheduleSolution. Manual UAT passed 2026-05-07. |
| REIN-02 | Phase 4 | Validated | Rising-edge trigger (false>true only). Boolean Apply input with default false. |
| REIN-03 | Phase 4 | Validated | Report output with per-parameter status lines. 7-value ReinstatementStatus enum covers Applied, MissingTarget, TypeMismatch, AmbiguousTarget, OutOfRange, Unchanged, WouldApply. |
| MVGP-01 | Phase 5 | Pending | |
| MVGP-02 | Phase 5 | Pending | |
| MVGP-03 | Phase 5 | Pending | |
| INTG-01 | Phase 6 | Code Complete | E2E test `HappyPath_StatePublishAndRetrieve` passes. Human UAT pending. |
| INTG-02 | Phase 2/3/6 | Validated | E2E `LegacyNoState_FlowStillWorks` passes. Full suite regression green (61 C# + 23 pytest). |
| INTG-03 | Phase 6 | Code Complete | ErrorMessageTemplateTests (12) + test_error_responses.py (3) + ReinstateFailureModes E2E pass. Human UAT pending. |

**Status legend:**
- `Code Complete` — implementation verified by code inspection + unit tests; live integration test still pending
- `Validated` — code complete + live test passed
- `Pending` — not yet implemented

**Coverage:**
- v2.0 requirements: 18 total
- Mapped to phases: 18
- Validated: 14 (DGST-01..03, DGCL-01..03, DGRN-01..03, REIN-01..03, INTG-02)
- Code complete: 2 (INTG-01, INTG-03)
- Pending: 3 (MVGP-01..03)
- Unmapped: 0

## Phase 3.1 — Gap Closure (retroactive)

After Phase 3 verifier passed and during human UAT, two upstream gaps from Phase 1 and Phase 2 were discovered:

1. **DGST-01 was not actually delivered** by Phase 1. Only data contracts existed; the DESIGN STATE GH component was missing from the task list.
2. **DGCL-02 was not actually delivered** by Phase 2. `ValidationRunPersistenceService` only had helper methods; no Neo4j write existed. The Classificator received state but never persisted it.

Both were closed in two commits without a formal gap-closure phase being scheduled:
- `b73e8d9` — `feat(03): add DESIGN STATE GH component for named parameter capture`
- `d856ca4` — `fix: wire design state through full persistence chain` (6 broken links: Classificator output, Validator input, ValidationPublishClient param, ValidationPublishContract field, data-service Pydantic field, data-service Cypher SET)

See `.planning/v2.0-GAP-CLOSURE.md` for the full retrospective.

---
*Requirements defined: 2026-04-10*
*Traceability updated: 2026-05-05 (post Phase 3 gap closure)*
