# Roadmap: Design Grammar System

## Milestones

- 🔄 **v3.0 Typed Variables and Composable Design State** — Phases 7-12 (active)
- ✅ **v2.0 DG Plugin - Design State and Validation Runs** — Phases 1-6 (shipped 2026-05-10) → [archive](milestones/v2.0-ROADMAP.md)
- ✅ **v1.1 Project Knowledge Graph** — Phases 1-7 (shipped 2026-04-10) → [archive](milestones/v1.1-phases/)

## Phases

### v3.0 — Typed Variables and Composable Design State

- [ ] **Phase 7: Schema Foundation** — Lock the data contracts: VariableKind enum, DesignState C# models, Var merge-key bug fix, schema propagation across all 6 surfaces
- [ ] **Phase 8: METAGRAPH Expansion and RULE DECONSTRUCT Rework** — METAGRAPH exposes Runs and typed variable outputs; RULE DECONSTRUCT reveals Objects/Properties partition; VARIABLE NAME component added
- [ ] **Phase 9: OBJECT STATE Component and DESIGN STATE Rework** — New OBJECT STATE component; DESIGN STATE reworked to accept ObjectState + DefState and output IdRefs/GeoRefs/DefState
- [ ] **Phase 10: CLASSIFICATOR Rework** — Full input reset (Rule, Objects, Properties, PropValues, IdRefs, GeoRefs, DefState); new Values/Variables outputs; VALIDATOR input renamed State→DefState
- [ ] **Phase 11: RUN DECONSTRUCT and statePayloadJson Extension** — RUN DECONSTRUCT replaces VALIDATION RUNS (new GUID); statePayloadJson extended with IdRefs list
- [ ] **Phase 12: E2E Validation and Schema Propagation Verification** — Live end-to-end flow confirmed; backward compat for rules-only workflow verified; live ingest test against updated n8n prompts

<details>
<summary>✅ v2.0 DG Plugin - Design State and Validation Runs (Phases 1-6) — SHIPPED 2026-05-10</summary>

- [x] Phase 1: Design State Contract and Serialization (1/1 plans) — 2026-04-30
- [x] Phase 2: Classificator State Input and Run Persistence (1/1 plans) — 2026-04-30
- [x] Phase 3: Validation Runs Retrieval Component (1/1 plans) — 2026-04-30
- [x] Phase 4: Reinstatement Component (2/2 plans) — 2026-05-07
- [x] Phase 5: Model Viewer Grouping by Rule and State (2/2 plans) — 2026-05-10
- [x] Phase 6: End-to-End Hardening and Verification (3/3 plans) — 2026-05-10

</details>

<details>
<summary>✅ v1.1 Project Knowledge Graph (Phases 1-7) — SHIPPED 2026-04-10</summary>

- [x] Phase 1: Neo4j Schema Foundation
- [x] Phase 2: data-service CRUD + Folder Ingest
- [x] Phase 3: n8n Knowledge Workflows + LLM Ingest and Query
- [x] Phase 4: Update Flow Endpoints
- [x] Phase 5: UI Mode Restructuring + Insert and Query Panels
- [x] Phase 6: UI Update Panel + Inline Diff Editor
- [x] Phase 7: UI Session History Panel + NeoVis Knowledge View

</details>

---

## Phase Details

### Phase 7: Schema Foundation
**Goal**: The data contracts for typed variables and composable DesignState are locked — VariableKind enum, DesignState/DefState/ObjectState C# models, DS_/OS_ ID prefixes, and schema propagation complete across all 6 surfaces; the latent v2.0 Var merge-key cross-project collision bug is eliminated
**Depends on**: Nothing (universal prerequisite for all v3.0 phases)
**Requirements**: SCHM-01, SCHM-02, SCHM-03, SCHM-04, VTYP-01, VTYP-02, VTYP-03
**Success Criteria** (what must be TRUE):
  1. A unit test for VariableTypeInferrer.Infer() passes for a variable appearing in both a ClassAtom and DataPropertyAtom — the result is Object (priority-chain rule holds)
  2. A Neo4j verification query `MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v)` returns 0 — no cross-project Var node collisions remain on the live database
  3. cypher_template.txt, dataset_schema.json, n8n workflow JSON prompts, config.template.js, C# models, and data-service/app.py all reference DS_ and OS_ ID prefixes and the single-label `:DesignState` + `kind` pattern consistently
  4. NeoVis renders DefState and ObjectState nodes with distinct colors using a single `:DesignState` label config entry — no label proliferation, no non-deterministic rendering
**Plans**: TBD

### Phase 8: METAGRAPH Expansion and RULE DECONSTRUCT Rework
**Goal**: METAGRAPH loads Runs alongside rules and partitions variables by kind into typed outputs; RULE DECONSTRUCT exposes Objects, Properties, and Runs per rule; VARIABLE NAME component lets users inspect variable names on the canvas
**Depends on**: Phase 7 (Variable.Kind must exist before typed outputs can be produced or consumed)
**Requirements**: CTRCT-01, CTRCT-02, CTRCT-06, VTYP-04
**Success Criteria** (what must be TRUE):
  1. METAGRAPH connected to a project with existing rules and runs shows non-empty Objects, Properties, and Runs outputs on the GH canvas
  2. RULE DECONSTRUCT wired to a rule shows Objects and Properties as separate outputs — each variable appears in exactly one output (no duplicates, no omissions)
  3. VARIABLE NAME wired to a Variable output from RULE DECONSTRUCT returns the variable's name as a plain string
**Plans**: TBD

### Phase 9: OBJECT STATE Component and DESIGN STATE Rework
**Goal**: Architects can compose parameterized element identity into a DesignState by wiring an Object variable reference and geometry into OBJECT STATE, then combining ObjectState + DefState in the reworked DESIGN STATE to obtain stable IdRefs and GeoRefs
**Depends on**: Phase 7 (DG.ObjectState and DG.DefState C# models)
**Requirements**: CMPST-01, CMPST-02, CMPST-03, CMPST-04, CMPST-05
**Success Criteria** (what must be TRUE):
  1. OBJECT STATE component wired with a panel string (ObjectRef) and a list of geometry elements produces a DG.ObjectState data item without errors
  2. DESIGN STATE wired with two ObjectState items and a DefState produces non-empty IdRefs and GeoRefs outputs and passes DefState through unchanged
  3. When the DefState input changes (e.g. a slider moves), DESIGN STATE outputs a different IdRefs set on the next solve — cache invalidation confirmed by a changed ID value
  4. When DefState is unchanged across two consecutive solves, DESIGN STATE outputs the same IdRefs — cache is preserved and no re-scan occurs
**Plans**: TBD

### Phase 10: CLASSIFICATOR Rework
**Goal**: CLASSIFICATOR accepts the full v3.0 component contract — typed Objects, Properties, PropValues, IdRefs, GeoRefs, DefState — binds variables to element identities, and produces index-matched BoundVariables / Values / Variables outputs; VALIDATOR input State is renamed to DefState
**Depends on**: Phase 7 (Variable.Kind), Phase 8 (typed Objects/Properties from RULE DECONSTRUCT), Phase 9 (IdRefs/GeoRefs from DESIGN STATE)
**Requirements**: CTRCT-03, CTRCT-04, CTRCT-07
**Success Criteria** (what must be TRUE):
  1. CLASSIFICATOR with all 7 v3.0 inputs wired shows a status message "N objects bound, M properties bound" and produces a non-empty BoundVariables output
  2. CLASSIFICATOR Values DataTree is index-matched with BoundVariables — for any branch index i, Values[i] and BoundVariables[i] describe the same variable
  3. VALIDATOR accepts a DefState input (renamed from State) without type error when wired from CLASSIFICATOR DefState output
  4. Opening a saved v2.0 canvas file in Grasshopper displays an explicit migration warning message rather than silently passing wrong data through misrouted wires
**Plans**: TBD
**Research flag**: Needs /gsd-research-phase before PLAN — read VariableBinder.BuildBindings in detail before drafting this phase

### Phase 11: RUN DECONSTRUCT and statePayloadJson Extension
**Goal**: RUN DECONSTRUCT (new GUID, replaces VALIDATION RUNS) provides a clean v3.0 run-reading contract with passing/failing item lists; statePayloadJson is extended to persist IdRefs in Neo4j for cross-run object identity tracking
**Depends on**: Phase 8 (Runs output from METAGRAPH), Phase 9/10 (extended DesignState shape for statePayloadJson)
**Requirements**: CTRCT-05, INTG-03
**Success Criteria** (what must be TRUE):
  1. RUN DECONSTRUCT wired to a ValidRun from METAGRAPH shows passing items, failing items, Run Id, Date created, and State outputs with correct data
  2. A validation run persisted using v3.0 CLASSIFICATOR has a statePayloadJson that includes a non-empty idRefs list when read back from Neo4j
  3. REINSTATE wired through the new RUN DECONSTRUCT path successfully reinstates slider parameters — the statePayloadJson shape change does not break the reinstatement path
**Plans**: TBD
**Research flag**: Needs /gsd-research-phase before PLAN — read ValidationRunPersistenceService.cs and data-service/app.py statePayloadJson serialization path before drafting this phase

### Phase 12: E2E Validation and Schema Propagation Verification
**Goal**: The full v3.0 pipeline runs end-to-end on a live Docker environment with no data loss; the rules-only backward-compat flow is confirmed; schema propagation is audited across all surfaces; live ingest confirms LLM generates Cypher with new node labels
**Depends on**: Phases 7–11 (all code phases complete)
**Requirements**: INTG-01, INTG-02
**Success Criteria** (what must be TRUE):
  1. A GH canvas wired OBJECT STATE → DESIGN STATE → CLASSIFICATOR → VALIDATOR completes a validation run; the run appears in RUN DECONSTRUCT output with correct passing/failing item lists and no errors in the chain
  2. A GH canvas wired CLASSIFICATOR → VALIDATOR (no ObjectState, rules-only flow) completes a validation run without errors — backward compat holds
  3. A live rule ingest through the n8n webhook generates Cypher using DS_/OS_ ID prefixes and the single-label `:DesignState` pattern — confirming the n8n prompt update is active
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 7. Schema Foundation | 0/? | Not started | - |
| 8. METAGRAPH Expansion and RULE DECONSTRUCT Rework | 0/? | Not started | - |
| 9. OBJECT STATE Component and DESIGN STATE Rework | 0/? | Not started | - |
| 10. CLASSIFICATOR Rework | 0/? | Not started | - |
| 11. RUN DECONSTRUCT and statePayloadJson Extension | 0/? | Not started | - |
| 12. E2E Validation and Schema Propagation Verification | 0/? | Not started | - |

---

*Roadmap updated: 2026-05-11 — v3.0 phases added*
*v2.0 shipped: 2026-05-10*
