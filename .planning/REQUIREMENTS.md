# Requirements: Design Grammar System v3.0 — Typed Variables and Composable Design State

**Defined:** 2026-05-11
**Core Value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.

## v3.0 Requirements

### Variable Typing

- [ ] **VTYP-01**: Variable type (Object vs Property) is inferred at read-time from SWRL atom structure — ClassAtom arg → Object, DataPropertyAtom arg-2 → Property
- [ ] **VTYP-02**: Object variables are cross-rule — same variable name maps to the same entity across all rules in a project
- [ ] **VTYP-03**: Property variables are rule-scoped — same name in different rules represents independent variables
- [ ] **VTYP-04**: User can see Object and Property variables per rule via RULE DECONSTRUCT outputs

### Composable State

- [ ] **CMPST-01**: User can create an ObjectState by wiring an Object variable reference and geometry elements to the OBJECT STATE component (ObjectRef + GeoRef inputs)
- [ ] **CMPST-02**: User can compose a DESIGN STATE from ObjectState and DefState inputs
- [ ] **CMPST-03**: DESIGN STATE outputs auto-generated IdRefs (element IDs) for Object instances that persist while DefState is unchanged
- [ ] **CMPST-04**: DESIGN STATE outputs GeoRefs matching the Object instances' geometry
- [ ] **CMPST-05**: IdRefs regenerate when DefState input changes (new parameter config = new element IDs)
- [ ] **CMPST-06**: ObjectInstance class exists as the cross-rule identity of a validated geometric element. ObjectInstance is 1:1 with ObjectState (its current binding snapshot). Both are cross-rule. ObjectInstance carries `OI_` ID prefix; ObjectState carries `OS_` ID prefix; DefState carries `DS_` ID prefix — all three IDs are distinct
- [ ] **CMPST-07**: ObjectState State_Id format is `OS_<SHA256(projectId + objectInstanceId + variableName)>` — cross-rule (no ruleId in hash) because ObjectVariables are cross-rule (VTYP-02)
- [ ] **CMPST-08**: IdRef represents the DesignState's auto-regenerated identifier. IdRef = DesignState ID, NOT ObjectState ID. IdRef regenerates whenever DefState changes (CMPST-05) and resolves to one or more ObjectInstance(s) for cross-run identity tracking (INTG-03)

### Component Contracts

- [ ] **CTRCT-01**: METAGRAPH loads Runs alongside rules and exposes Objects, DesignStates, Runs outputs
- [ ] **CTRCT-02**: RULE DECONSTRUCT exposes Objects, Properties, and Runs outputs; Variables and VariableName outputs are removed
- [ ] **CTRCT-03**: CLASSIFICATOR uses v3.0 input layout (full reset): Rule, Objects, Properties, PropValues, IdRefs, GeoRefs, DefState; outputs BoundVariables, MissingVariables, Status, DefState, Values, Variables
- [ ] **CTRCT-04**: CLASSIFICATOR Values output DataTree is index-matched with BoundVariables and Variables outputs
- [ ] **CTRCT-05**: RUN DECONSTRUCT (new GUID, replaces VALIDATION RUNS) — input ValidRun; outputs passing items, failing items, Run Id, Date created, State
- [ ] **CTRCT-06**: VARIABLE NAME component accepts Variable input and outputs its name
- [ ] **CTRCT-07**: VALIDATOR input State renamed to DefState
- [ ] **CTRCT-08**: OBJECT STATE component's ObjectRef input accepts a Variable of Object kind (a `dgm:ObjectVariable` reference from RULE DECONSTRUCT or VARIABLE NAME), not a raw string
- [ ] **CTRCT-09**: OBJECT STATE component's GeoRef input accepts a list of geometry element handles (Speckle objectId / Rhino GUID) matching the ObjectInstance — one ObjectState may carry multiple GeoRefs

### Schema & Data

- [ ] **SCHM-01**: DesignState nodes use single label `:DesignState` with `kind` property (`DefState` | `ObjectState`)
- [ ] **SCHM-02**: Var nodes include `project` in MERGE key (fix cross-project collision bug)
- [ ] **SCHM-03**: New node classes use unique ID prefixes (DS_ for DefState, OS_ for ObjectState, OI_ for ObjectInstance, IDR_ for IdRef)
- [ ] **SCHM-04**: Schema changes propagate across all 6 surfaces (cypher_template, dataset_schema, n8n prompts, NeoVis config, C# models, data-service)
- [ ] **SCHM-05**: PropValue persists per `ValidationEntity` (NOT per `ObjectInstance`). Each ValidationEntity has one `propValue` (xsd:string lex form) and one `propValueOf` → `PropertyVariable` reference. Displayed in Model Viewer's passing/failing item list as one value per item per rule — preserves multi-rule, multi-property validation semantics
- [ ] **SCHM-06**: Enum-valued discriminator properties (`variableKind`, `variableScope`, `kind`, `status`, `parameterType`) are modeled as OWL ObjectProperties pointing at NamedIndividuals in dedicated enum classes (`VariableKindValue`, `VariableScopeValue`, `DesignStateKindValue`, `ValidationStatusValue`, `DesignStateParameterTypeValue`), mirroring the existing `DesignStateParameterTypeValue` pattern

### Integration

- [ ] **INTG-01**: E2E flow works: OBJECT STATE → DESIGN STATE → CLASSIFICATOR → VALIDATOR → RUN DECONSTRUCT
- [ ] **INTG-02**: Existing rule validation workflow continues when no ObjectState is provided (backward compat for rules-only flow)
- [ ] **INTG-03**: Validation run statePayloadJson includes IdRefs list for cross-run Object instance tracking

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-computed geometry-hash ObjectRef | Geometry regenerates on every solve; would break cross-run identity |
| Migration shim for v2.0 canvases | Full reset chosen — document re-wire in release notes |
| ObjectPropertyAtom variable inference | Only ClassAtom + DataPropertyAtom used in DG's bespoke SWRL parser subset |
| Visual diff of design states across runs | Not required for composable state foundation |
| Auto-detection of Object variables from geometry topology | Beyond v3.0 scope |

## Key Decisions (v3.0)

| Decision | Rationale |
|----------|-----------|
| Single label `:DesignState` + `kind` property | Mirrors `Rule.kind` pattern; deterministic NeoVis rendering; lower propagation surface |
| New GUID for RUN DECONSTRUCT | Clean break from VALIDATION RUNS; accept canvas breakage; document re-wire |
| CLASSIFICATOR full input reset (no compat) | Cleanest API for v3.0; existing v2.0 canvases require full re-wire |
| PropValues = renamed Values | Same DataTree structure, narrower semantic scope (Property variables only) |
| VALIDATOR input State → DefState | Consistency with CLASSIFICATOR output name |
| Var merge key includes `project` | Fixes latent v2.0 cross-project collision bug; prerequisite for cross-rule identity |
| ObjectInstance separate from ObjectState | ObjectInstance = stable cross-rule identity (OI_ prefix), ObjectState = binding snapshot (OS_ prefix). 1:1 cardinality. Survives geometry edits — ObjectState gets replaced, ObjectInstance does not |
| ObjectRef input wires Variable, not string | OBJECT STATE's ObjectRef port takes a `dgm:ObjectVariable` reference (from RULE DECONSTRUCT). The user-supplied stable string (Rhino/Speckle GUID) lives on `dgv:objectRef` datatype property of ObjectState. Two distinct concepts |
| IdRef ≠ ObjectState ID | IdRef is the DesignState's auto-generated ID (regenerates with DefState). ObjectState carries its own State_Id (OS_ prefix). Conflating the two would break cross-run identity tracking |
| PropValue on ValidationEntity (not ObjectInstance) | Multi-rule validation requires per-(Run, Rule, ObjectInstance) values. ValidationEntity is already that cell. Placing PropValue on ObjectInstance would force overwrites across rules and lose data |
| Enum discriminators as ObjectProperty + NamedIndividuals | Mirrors existing DesignStateParameterTypeValue pattern. Reasoner can validate value space; LLM has explicit vocabulary to reference |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VTYP-01 | Phase 7 | Pending |
| VTYP-02 | Phase 7 | Pending |
| VTYP-03 | Phase 7 | Pending |
| VTYP-04 | Phase 8 | Pending |
| CMPST-01 | Phase 9 | Pending |
| CMPST-02 | Phase 9 | Pending |
| CMPST-03 | Phase 9 | Pending |
| CMPST-04 | Phase 9 | Pending |
| CMPST-05 | Phase 9 | Pending |
| CMPST-06 | Phase 9 | Pending |
| CMPST-07 | Phase 9 | Pending |
| CMPST-08 | Phase 9 | Pending |
| CTRCT-01 | Phase 8 | Pending |
| CTRCT-02 | Phase 8 | Pending |
| CTRCT-03 | Phase 10 | Pending |
| CTRCT-04 | Phase 10 | Pending |
| CTRCT-05 | Phase 11 | Pending |
| CTRCT-06 | Phase 8 | Pending |
| CTRCT-07 | Phase 10 | Pending |
| CTRCT-08 | Phase 9 | Pending |
| CTRCT-09 | Phase 9 | Pending |
| SCHM-01 | Phase 7 | Pending |
| SCHM-02 | Phase 7 | Pending |
| SCHM-03 | Phase 7 | Pending |
| SCHM-04 | Phase 7 | Pending |
| SCHM-05 | Phase 11 | Pending |
| SCHM-06 | Phase 7 | Pending |
| INTG-01 | Phase 12 | Pending |
| INTG-02 | Phase 12 | Pending |
| INTG-03 | Phase 11 | Pending |

**Coverage:**
- v3.0 requirements: 30 total (23 original + 7 added in v3.1 ontology pass)
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-05-11*
*Last updated: 2026-05-14 — added CMPST-06..08, CTRCT-08..09, SCHM-05..06 from ontology audit (ObjectInstance/GeoRef/IdRef classes, PropValue on ValidationEntity, enum discriminators)*
