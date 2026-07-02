# Requirements: Design Grammar System — Milestone v7.0

**Defined:** 2026-07-02
**Core Value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.
**Milestone goal:** Rebuild the DG Grasshopper addin around the ontology-aligned component schema (`ontology/GH_DesignGrammars.pdf`), rename Ontology V6→V7 to fully match the schema, and propagate the revised graph schema across every interconnected artifact.

Source of truth for the component contract: `ontology/GH_DesignGrammars.pdf` (14 components; CLASSIFICATOR eliminated). Prior milestone v3.0 superseded — Phase 7 foundation (VariableKind, VariableTypeInferrer, DesignStateIdGenerator, Var merge-key fix) carries forward. Archived v3.0 requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` (SCHM numbering continues from there).

## v7.0 Requirements

### Ontology V7 (ONTO)

- [ ] **ONTO-01**: `apply_v7_rename.py` transforms `DesignGrammar-V6.owl` into `DesignGrammar-V7.owl` with all schema-notation renames applied (layer hubs `Ontograph`/`Validgraph`/`Computgraph`, `ObjProperty`, `DataProperty`, `Run`, `ObjState`, `ReStatus`), following the `apply_v6_*.py` script pattern
- [ ] **ONTO-02**: `V6-to-V7-mapping.md` lists every renamed IRI (old → new) as a recovery-only guard for existing publications
- [ ] **ONTO-03**: V7 models the state trio as DesignState subclasses — `ParamState` (renamed from DefState), new `PropState` (Rule + DataProperty + PropValue, building on existing `propValue`/`propValueOf`), `ObjState` (renamed from ObjectState)
- [ ] **ONTO-04**: V7 adds rule-level `SWRL`, `RuleName`, `RuleDescription` datatype properties (renaming ruleTitle/ruleText) and Validgraph `SendStatus`/`ValidStatus` (Boolean); the investigation note resolves ALL flagged conflicts: (a) PDF-internal ValidStatus-Boolean vs Status-text (proposed: `Run.ValidStatus` Boolean overall pass + `Run.Status` text enum); (b) DesignState storage layer — `cypher_template.txt` stores DesignState with `graph='Metagraph'` while the PDF's VALIDATION GRAPH reads DesignState from the ValidGraph handle (and the PDF itself says "New Design State can only pass to Metagraph through Validator"); (c) ontology version-marker policy — V6 owl carries both `versionInfo 6.1` and a stale `rdfs:comment "Schema version: v3"`
- [ ] **ONTO-05**: V7 extension facades (standards / BOT / Topologic) and `catalog-v001-V7.xml` regenerated; `DesignGrammar-V7.md` documentation regenerated; ontology passes consistency check
- [ ] **ONTO-06**: A component-port ↔ ontology-IRI mapping is documented for all 14 components (successor of GH-mapping)

### Graph Schema Propagation (SCHM — continues v3.0 numbering, which ended at SCHM-06)

- [ ] **SCHM-07**: `cypher_template.txt` v4 — DesignState `kind` ∈ {ObjState, ParamState, PropState}; Run properties (ValidStatus Boolean, SendStatus Boolean, Status text); rule-level SWRL property
- [ ] **SCHM-08**: `training/dataset_schema.json` v4 mirrors the same schema
- [ ] **SCHM-09**: n8n `rules-to-metagraph.json` prompts (Build LLM Prompt, Prepare Graph Payload, Parse LLM Output) emit the v4 schema
- [ ] **SCHM-10**: n8n `graph-query-mcp.json` Build Cypher Prompt describes the v4 schema
- [ ] **SCHM-11**: NeoVis `config.template.js` (labels/relationships/visGroups incl. three state kinds; reconcile the duplicate DatatypeProperty/DataProperty label entries) and `index.html` hardcoded Cypher updated
- [ ] **SCHM-12**: data-service `app.py` Cypher aligned with v4 (ValidationRun carries ValidStatus/SendStatus)
- [ ] **SCHM-13**: A migration script (following `migrations/` pattern) renames existing DesignState `kind` values (DefState→ParamState, ObjectState→ObjState) and applies the Phase-13 layer-placement decision on dev databases
- [ ] **SCHM-14**: `training/updated_cypher_reference_examples_v3.cypher` gets a v4 successor and `test/` fixtures referencing v3 state kinds are updated — no runtime or LLM few-shot artifact still teaches the old schema

### SpecGraph Runtime Rename (SPEC)

- [ ] **SPEC-01**: A migration script renames `graph:'KnowledgeGraph'`→`'SpecGraph'` and `Knowledge*`→`Spec*` node labels (incl. fulltext index recreation) on a live Neo4j database
- [ ] **SPEC-02**: data-service knowledge endpoints operate on `Spec*` labels (endpoint URLs preserved for UI compatibility)
- [ ] **SPEC-03**: n8n `knowledge-*.json` workflows operate on `Spec*` labels
- [ ] **SPEC-04**: UI knowledge view and NeoVis config render `Spec*` labels

### DG.Core State Models (CORE)

- [ ] **CORE-01**: `ObjState` model (Object reference, GeoRef, Label) replaces the ObjectState scaffolding
- [ ] **CORE-02**: `ParamState` model (typed Number/Integer/Boolean parameters, deterministic StateId) adapted from DesignStateSnapshot
- [ ] **CORE-03**: `PropState` model (Rule reference, DataProperty reference, PropValue)
- [ ] **CORE-04**: `DesignState` composition model aggregates many ObjState/ParamState/PropState with per-class ID prefixes via DesignStateIdGenerator
- [ ] **CORE-05**: `statePayloadJson` v2 serializes the 3-part composition with lossless round-trip (unit-tested)

### Graph Access Components (GHGA)

- [ ] **GHGA-01**: CONNECTOR outputs a `Database` handle (renamed from Connection); inputs aligned to Neo4jURI/Neo4jUser/Neo4jPassword/Project (keeps db-name + Connect inputs)
- [ ] **GHGA-02**: GRAPH DECONSTRUCT splits Database into Metagraph / Ontograph / ValidGraph / SpecGraph layer handles
- [ ] **GHGA-03**: METAGRAPH accepts the Metagraph handle and outputs Rules + Objects (index-matched lists)
- [ ] **GHGA-04**: ONTOGRAPH outputs Class / ObjProperties / DataProperties lists read from the OntoGraph layer
- [ ] **GHGA-05**: VALIDATION GRAPH (replaces VALIDATION RUNS, new GUID) outputs Run / Status / DesignState lists read from the ValidGraph layer

### State Components (GHST)

- [ ] **GHST-01**: OBJECT STATE composes Object + Geometry + Label into ObjState
- [ ] **GHST-02**: PARAMETER STATE captures a Parameters list into ParamState (variable-input pattern and deterministic StateId preserved from v2.0 DESIGN STATE)
- [ ] **GHST-03**: PROPERTY STATE composes Rule + DataProperty + PropValue into PropState
- [ ] **GHST-04**: DESIGN STATE composes many ObjState + ParamState + PropState into DesignState (index-matched list contract)
- [ ] **GHST-05**: DESIGN STATE DECONSTRUCT splits DesignState into ObjState / ParamState / PropState
- [ ] **GHST-06**: OBJECT DECONSTRUCT splits ObjState into Object / Geometry / Label
- [ ] **GHST-07**: PARAMETER REINSTATE (reworked REINSTATE) applies ParamState on a rising-edge Reinstate trigger and outputs Parameters + StateStatus (7-value ReStatus reporting preserved)

### Rules & Validation (GHVL)

- [ ] **GHVL-01**: RULE DECONSTRUCT partitions rule variables into Objects + DataProperties outputs via VariableTypeInferrer (Variables/VariableName outputs removed; Rule/SWRL/RuleName/RuleDescription kept)
- [ ] **GHVL-02**: CLASSIFICATOR component is removed from the plugin
- [ ] **GHVL-03**: VALIDATOR implements the new contract — inputs Rule, DesignState, SendValid, Run; outputs ValidStatus, RuleName, RuleDescription, SendStatus — keeping non-overlapping extras (DataServiceUrl input; Report, FailingBindings, ValidationRunId, ModelViewerUrl outputs)
- [ ] **GHVL-04**: VALIDATOR binds variables from the composed DesignState (ObjState → Object variables, PropState → Property values), replacing the CLASSIFICATOR/VariableBinder path
- [ ] **GHVL-05**: The publish path persists a Run with ValidStatus/SendStatus and the 3-part state payload; VALIDATION GRAPH reads it back intact
- [ ] **GHVL-06**: The Model Viewer keeps working against v7.0 data — data-service `_project_state_summary` and the `/validation/runs` projection are adapted to statePayloadJson v2, and `useValidationRunsGrouping` (group-by-State via `state.stateId`) plus ValidationRunsStrip render correctly for runs with 3-part states

### End-to-End & Docs (E2E)

- [ ] **E2E-01**: Full live chain on Docker completes without errors: rule ingest → METAGRAPH → RULE DECONSTRUCT → OBJECT/PARAMETER/PROPERTY STATE → DESIGN STATE → VALIDATOR → publish → VALIDATION GRAPH read-back → PARAMETER REINSTATE
- [ ] **E2E-02**: Release notes document canvas breakage and re-wiring for every changed component; port↔IRI mapping doc published
- [ ] **E2E-03**: Repo/AI-assistant docs updated to schema v4 and the v7.0 component set: `CLAUDE.md` (Graph Schema section + Schema Change Propagation list), `.github/copilot-instructions.md` (currently mandates "v3 as source of truth"), `spec/DATABASE.md`, `README.md`
- [ ] **E2E-04**: DG_OBSIDIAN reflects v7.0: the "Graph schema v3 is the canonical data model" atlas note superseded/updated, stale component notes annotated, and the graphify knowledge graph regenerated via `scripts/refresh_graphify.sh` so community notes (e.g. CLASSIFICATOR Component, ValidationRunsComponent, v3.0-phase notes) no longer describe deleted/renamed code as current

## Future Requirements

<!-- Deferred to later milestones. -->

- v4.0 BOT Ontology Bridge (planned milestone — BOT anchor nodes + ALIGNED_TO edges; facade regenerated for V7 in this milestone keeps it compatible)
- Cross-rule Element-Id persistence on DesignState nodes (v3.0 CMPST idea — re-evaluate once ObjState identity is live)
- Computgraph runtime layer (ontology models Algorithm/Procedure/Pattern — no runtime consumer yet; only `Computgraph.Parameter` is referenced by PARAMETER REINSTATE)

## Out of Scope

<!-- Explicit exclusions with reasoning. -->

| Feature | Reason |
|---------|--------|
| VARIABLE NAME and RUN DECONSTRUCT components | v3.0 plan artifacts; not present in the GH_DesignGrammars schema |
| Neo4j label renames beyond Knowledge*→Spec* (ValidationRun→Run, DatatypeProperty→DataProperty in DB) | Ontology↔DB mapping documented instead; migration cost outweighs benefit |
| CLASSIFICATOR backward compatibility / migration shim | Component eliminated by design; release notes cover re-wiring |
| Arbitrary geometry serialization in ParamState | Number/Integer/Boolean limit stands (v2.0 decision) |
| LLM fine-tuning for the v4 schema | Prompt-constrained approach continues |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ONTO-01 … ONTO-06 | Phase 13: Ontology V7 and Contract Investigation | Pending |
| SCHM-07 … SCHM-14 | Phase 14: Graph Schema v4 Propagation | Pending |
| SPEC-01 … SPEC-04 | Phase 15: SpecGraph Runtime Rename | Pending |
| CORE-01 … CORE-05 | Phase 16: DG.Core State Models and State Components | Pending |
| GHST-01 … GHST-04 | Phase 16: DG.Core State Models and State Components | Pending |
| GHGA-01 … GHGA-05 | Phase 17: Graph Access Components | Pending |
| GHVL-01 … GHVL-06 | Phase 18: Rules and Validator Rework | Pending |
| GHST-05 … GHST-07 | Phase 19: Deconstruct and Reinstate Components | Pending |
| E2E-01 … E2E-04 | Phase 20: E2E Validation and Docs | Pending |

**Coverage:** 39/39 requirements mapped to exactly one phase — no orphans.
*Amended 2026-07-02 after full-codebase audit: +SCHM-13/14 (kind migration, training/test fixtures), +GHVL-06 (Model Viewer read-side), +E2E-03/04 (repo/AI docs, DG_OBSIDIAN+graphify refresh); ONTO-04 scope extended with DesignState layer-placement and version-marker conflicts.*

---
*39 requirements across 8 categories. On completion they move to PROJECT.md Validated.*
