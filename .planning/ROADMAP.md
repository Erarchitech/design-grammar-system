# Roadmap: Design Grammar System

## Milestones

- 📋 **v4.0 BOT Ontology Bridge** — Phases 1-4 (planned) → [requirements](milestones/v4.0-REQUIREMENTS.md) | [roadmap](milestones/v4.0-ROADMAP.md)
- 🔄 **v7.0 Update of DG Addin for Grasshopper** — Phases 13-20 (active)
- 📋 **v9.0 AI Workflow Intelligence** — Phases 1-8 (future, isolated; pending v7.0) → [requirements](milestones/v9.0-REQUIREMENTS.md) | [roadmap](milestones/v9.0-ROADMAP.md)
- ⛔ **v3.0 Typed Variables and Composable Design State** — Superseded 2026-07-02 (Phase 7 shipped, carried into v7.0) → [archive](milestones/v3.0-ROADMAP.md)
- ✅ **v2.0 DG Plugin - Design State and Validation Runs** — Phases 1-6 (shipped 2026-05-10) → [archive](milestones/v2.0-ROADMAP.md)
- ✅ **v1.1 Project Knowledge Graph** — Phases 1-7 (shipped 2026-04-10) → [archive](milestones/v1.1-phases/)

## Phases

### v7.0 — Update of DG Addin for Grasshopper

Component contract source of truth: `ontology/GH_DesignGrammars.pdf` (14 components; CLASSIFICATOR eliminated).

- [x] **Phase 13: Ontology V7 and Contract Investigation** — Critical investigation resolves PDF-internal conflicts; full V6→V7 rename to schema notation; V6→V7 recovery mapping; port↔IRI map for all 14 components (completed 2026-07-03)
- [ ] **Phase 14: Graph Schema v4 Propagation** — cypher_template v4, dataset_schema v4, n8n ingest+query prompts, NeoVis config, index.html, data-service Cypher, kind-migration script, training examples + test fixtures
- [x] **Phase 15: SpecGraph Runtime Rename** — KnowledgeGraph→SpecGraph migration across DB, data-service, n8n knowledge workflows, UI/NeoVis (completed 2026-07-03)
- [ ] **Phase 16: DG.Core State Models and State Components** — ObjState/ParamState/PropState/DesignState models + statePayloadJson v2; OBJECT STATE, PARAMETER STATE, PROPERTY STATE, DESIGN STATE components
- [x] **Phase 17: Graph Access Components** — CONNECTOR update, GRAPH DECONSTRUCT, METAGRAPH rework, ONTOGRAPH, VALIDATION GRAPH
- [ ] **Phase 18: Rules and Validator Rework** — RULE DECONSTRUCT partition, VALIDATOR new contract with DesignState-driven binding, CLASSIFICATOR deletion, publish/persistence extension, Model Viewer read-side adaptation (1/5 plans)
- [x] **Phase 19: Deconstruct and Reinstate Components** — DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, PARAMETER REINSTATE
- [ ] **Phase 20: E2E Validation and Docs** — Live Docker E2E chain, release notes for canvas breakage, port↔IRI mapping published, repo/AI docs to v4, DG_OBSIDIAN + graphify refresh

<details>
<summary>⛔ v3.0 Typed Variables and Composable Design State — SUPERSEDED 2026-07-02</summary>

Phase 7 (Schema Foundation) shipped 2026-06-23 — VariableKind + VariableTypeInferrer, DesignStateIdGenerator, Var merge-key fix, schema propagation v3.1 — all carried into v7.0. Phases 8–12 dropped: the component plan was replaced by the GH_DesignGrammars schema. See [archive](milestones/v3.0-ROADMAP.md).

</details>

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

### Phase 13: Ontology V7 and Contract Investigation

**Goal**: The ontology and the GH component schema agree on every name — V7 is a full rename of V6 to schema notation plus the genuinely new concepts, with a recovery mapping and a per-port IRI contract locked for all downstream phases
**Depends on**: Nothing (universal prerequisite — locks naming for phases 14–20)
**Requirements**: ONTO-01, ONTO-02, ONTO-03, ONTO-04, ONTO-05, ONTO-06
**Success Criteria** (what must be TRUE):

  1. Running `python ontology/apply_v7_rename.py` produces `DesignGrammar-V7.owl` where the state trio exists as DesignState subclasses (ObjState, ParamState, PropState), rule-level SWRL/RuleName/RuleDescription datatype properties exist, and Validgraph carries SendStatus + ValidStatus (Boolean)
  2. `V6-to-V7-mapping.md` lists every renamed IRI old→new — spot-checking any V6 publication name finds its V7 successor
  3. The investigation note records the resolution of the PDF-internal ValidStatus(Boolean)-vs-Status(text) conflict, the DesignState storage-layer conflict (cypher_template stores DesignState in Metagraph; the PDF's VALIDATION GRAPH reads it from ValidGraph), the ontology version-marker policy (V6 owl carries both versionInfo 6.1 and a stale "Schema version: v3" comment), and the final state-kind names; every output port of the 14 schema components resolves to a V7 IRI in the port↔IRI map — zero unmapped references
  4. V7 extension facades (standards/BOT/Topologic), `catalog-v001-V7.xml`, and regenerated `DesignGrammar-V7.md` load/parse without errors

**Plans** (planned 2026-07-03 — 4 plans, 3 waves):

  - 13-01 — Conflict investigation + V6→V7 naming contract (`V7-INVESTIGATION.md`) — *wave 1* — ONTO-04
  - 13-02 — `apply_v7_rename.py` → `DesignGrammar-V7.owl` + `V6-to-V7-mapping.md` — *wave 2, depends 13-01* — ONTO-01/02/03/04
  - 13-03 — `port-iri-map-V7.md` for all 14 components — *wave 3, depends 13-02* — ONTO-06
  - 13-04 — V7 extension facades + `catalog-v001-V7.xml` + regenerated `DesignGrammar-V7.md` — *wave 3, depends 13-02* — ONTO-05

### Phase 14: Graph Schema v4 Propagation

**Goal**: Every artifact that hard-codes the Neo4j graph schema speaks v4 — three state kinds, Run validation properties, rule-level SWRL — so LLM ingest, querying, visualization, and the data-service agree before any component code changes
**Depends on**: Phase 13 (final names locked)
**Requirements**: SCHM-07, SCHM-08, SCHM-09, SCHM-10, SCHM-11, SCHM-12, SCHM-13, SCHM-14
**Success Criteria** (what must be TRUE):

  1. `cypher_template.txt` declares SCHEMA VERSION v4 with DesignState `kind` ∈ {ObjState, ParamState, PropState}, the Phase-13 layer placement, Run properties (ValidStatus, SendStatus — no stored Status text field; overall pass = AND(ValidStatus) derived at read time per D-01/D-02), and a rule-level SWRL property; `dataset_schema.json` mirrors it exactly
  2. A live rule ingest through the n8n webhook generates Cypher that validates against the v4 template (correct labels, kinds, and Run properties)
  3. The n8n graph-query prompt describes the v4 data model; a natural-language query about design states returns results using the new kind values
  4. NeoVis renders all three state kinds with distinct colors from `config.template.js` (duplicate DatatypeProperty/DataProperty entries reconciled); no `DefState`/`ObjectState` kind entries remain in any runtime artifact
  5. Running the kind-migration script on a dev database leaves zero nodes with `kind` in {DefState, ObjectState}; the v4 successor of `updated_cypher_reference_examples_v3.cypher` and updated `test/` fixtures contain no v3 state kinds

**Plans** (planned 2026-07-03 — 7 plans, 3 waves):

  - [x] 14-01-PLAN.md — v4 schema contract: `cypher_template.txt` + `dataset_schema.json` — *wave 1* — SCHM-07/08
  - [x] 14-02-PLAN.md — NeoVis `config.template.js` + `index.html` client Cypher — *wave 1* — SCHM-11
  - [x] 14-03-PLAN.md — C# read-side coalesce patch (D-06) + Wave 0 smoke/seed harness — *wave 1* — SCHM-09/10/13
  - [x] 14-04-PLAN.md — n8n ingest + query prompts v4 + live smoke — *wave 2, depends 14-01/14-03* — SCHM-09/10
  - [x] 14-05-PLAN.md — data-service `app.py` v4 + D-14 runtime-literal rename (app.py/C#/E2E) — *wave 1* — SCHM-12
  - [x] 14-06-PLAN.md — DesignState kind + ValidGraph-layer migration, executed on dev — *wave 3, depends 14-03/14-04/14-05* — SCHM-13
  - [x] 14-07-PLAN.md — v4 cypher reference + test fixtures + ROADMAP/REQUIREMENTS amendment — *wave 2, depends 14-01* — SCHM-14

### Phase 15: SpecGraph Runtime Rename

**Goal**: The runtime catches up with the ontology's KnowledgeGraph→SpecGraph rename — one migration, all surfaces, no orphaned Knowledge* references
**Depends on**: Phase 14 (same files touched — sequenced to avoid conflicts; logically independent)
**Requirements**: SPEC-01, SPEC-02, SPEC-03, SPEC-04
**Success Criteria** (what must be TRUE):

  1. After running the migration script on a live database, `MATCH (n {graph:'KnowledgeGraph'}) RETURN count(n)` returns 0 and former Knowledge* nodes carry Spec* labels with `graph:'SpecGraph'`
  2. Knowledge ingest and query round-trip works through the existing endpoint URLs against Spec* labels (folder ingest → note retrieval)
  3. n8n knowledge workflows and the UI knowledge view (NeoVis) operate on Spec* labels — live webhook test + visual check pass
  4. `grep -ri "KnowledgeGraph\|KnowledgeNote\|KnowledgeTag\|KnowledgeSession\|KnowledgeClass"` over runtime code (data-service, n8n workflows, graph-viewer) returns only migration-script and changelog references

**Plans**: 5/5 plans complete

**Wave 1** *(parallel — disjoint file sets, no inter-plan dependency)*

- [x] 15-01-PLAN.md — SpecGraph migration script (4 ops) + seed/migrate/verify — *wave 1* — SPEC-01
- [x] 15-02-PLAN.md — data-service app.py + spec_schema.cypher rename (routes preserved) — *wave 1* — SPEC-02
- [x] 15-03-PLAN.md — n8n workflows rename + inline Cypher + export deletion (webhooks preserved) — *wave 1* — SPEC-03
- [x] 15-04-PLAN.md — UI/NeoVis config keys + index.html SpecGraph view key — *wave 1* — SPEC-04

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 15-05-PLAN.md — test renames + _add_backfill delete + docs + phase-wide SC#4 gate — *wave 2, depends 15-01..15-04* — SPEC-01..04

**Cross-cutting constraints** *(appear in 2+ plans — keep consistent):*

- `SpecGraph` graph value + `SpecNote`/`SpecTag`/`SpecSession`/`SpecClass` labels + `spec_note_search` index must match 1:1 across 15-01 (DB), 15-02 (data-service), 15-03 (n8n), 15-04 (NeoVis)
- URL-facing identifiers preserved: `/knowledge/*` routes, `dg/knowledge-*` webhook paths, UI `knowledge-*` polling keys (SPEC-02)

### Phase 16: DG.Core State Models and State Components

**Goal**: Architects can capture all three state aspects on the canvas — object identity, parameters, and calculated property values — and compose them into a DesignState with a lossless serialized form
**Depends on**: Phase 13 (kind names); independent of 14–15 at code level
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, GHST-01, GHST-02, GHST-03, GHST-04
**Success Criteria** (what must be TRUE):

  1. `dotnet test` passes for ObjState/ParamState/PropState/DesignState models and the statePayloadJson v2 round-trip (serialize → deserialize → equal)
  2. OBJECT STATE wired with an Object variable, geometry, and a label produces an ObjState; PARAMETER STATE captures sliders/toggles into a ParamState with a deterministic StateId; PROPERTY STATE wired with Rule + DataProperty + PropValue produces a PropState
  3. DESIGN STATE composes multiple ObjState/ParamState/PropState inputs into a DesignState; index-mismatched list inputs produce an explicit component error, not silent misalignment
  4. The v3.0 DefState/ObjectState scaffolding classes are gone — no remaining references in DG.Core or DG.Grasshopper

**Plans**: 6/6 plans complete

**Wave 1** *(parallel — Plan 01 and Plan 02 are independent)*

- [x] 16-01-PLAN.md — Core state models (ObjState, ParamState, DesignState, PropState) + ParamState rename + scaffolding deletion — *wave 1* — CORE-01/02/03/04
- [x] 16-02-PLAN.md — DesignStateIdGenerator updates (rename ComputeDefStateId, add ComputePropStateId/ComputeDesignStateId, remove ComputeObjectInstanceId) — *wave 1* — CORE-01..04 (ID contract)

**Wave 2** *(parallel — Plan 03 and Plan 04 are independent)*

- [x] 16-03-PLAN.md — GH infrastructure: PublicTypes wrappers, GhCastingHelpers Try* helpers, ErrorMessageTemplates index-mismatch messages — *wave 2, depends 16-01* — GHST-01..04 (infrastructure)
- [x] 16-04-PLAN.md — v2 statePayloadJson serializer (DesignStatePayloadV2Serializer) with versioned envelope, no v1 fallback — *wave 2, depends 16-01* — CORE-05

**Wave 3** *(parallel — Plan 05 and Plan 06 are independent)*

- [x] 16-05-PLAN.md — PARAMETER STATE rename (new GUID, ParamState output) + OBJECT STATE component (index-mismatch guard) — *wave 3, depends 16-03* — GHST-01/02
- [x] 16-06-PLAN.md — PROPERTY STATE component (index-mismatch guard) + DESIGN STATE composition component (bag semantics, deterministic aggregated StateId) — *wave 3, depends 16-03* — GHST-03/04

### Phase 17: Graph Access Components

**Goal**: The canvas reads every graph layer through the CONNECTOR → GRAPH DECONSTRUCT chain — rules with typed objects from Metagraph, classes and properties from Ontograph, runs and design states from ValidGraph
**Depends on**: Phase 16 (VALIDATION GRAPH outputs DesignState objects); Phase 13 (handle/port names)
**Requirements**: GHGA-01, GHGA-02, GHGA-03, GHGA-04, GHGA-05
**Success Criteria** (what must be TRUE):

  1. CONNECTOR outputs a Database handle; GRAPH DECONSTRUCT splits it into Metagraph/Ontograph/ValidGraph/SpecGraph handles — wiring any handle into its reader component works without re-entering credentials
  2. METAGRAPH wired to a live project shows index-matched Rules and Objects outputs on the canvas
  3. ONTOGRAPH lists Class/ObjProperties/DataProperties from the live OntoGraph layer
  4. VALIDATION GRAPH lists Run/Status/DesignState from the live ValidGraph layer; the VALIDATION RUNS component no longer exists in the plugin

**Plans**: 4/4 plans complete

  - [x] 17-01-PLAN.md — Handle types, models, icons, CONNECTOR update, GRAPH DECONSTRUCT — *wave 1* — GHGA-01/02
  - [x] 17-02-PLAN.md — METAGRAPH extension (Objects output via REFERS_TO->Class query) — *wave 2, depends 17-01* — GHGA-03
  - [x] 17-03-PLAN.md — ONTOGRAPH (Class/ObjProperties/DataProperties from OntoGraph) — *wave 2, depends 17-01* — GHGA-04
  - [x] 17-04-PLAN.md — VALIDATION GRAPH (Run/Status/DesignState from ValidGraph, replaces VALIDATION RUNS) — *wave 2, depends 17-01* — GHGA-05

### Phase 18: Rules and Validator Rework

**Goal**: Validation flows entirely through the composed DesignState — RULE DECONSTRUCT partitions typed variables, VALIDATOR evaluates and publishes runs, and CLASSIFICATOR is gone
**Depends on**: Phase 16 (DesignState composition), Phase 17 (Rule flow via METAGRAPH)
**Requirements**: GHVL-01, GHVL-02, GHVL-03, GHVL-04, GHVL-05, GHVL-06
**Success Criteria** (what must be TRUE):

  1. RULE DECONSTRUCT wired to a rule shows Objects and DataProperties as separate outputs — each variable appears in exactly one output
  2. VALIDATOR wired with Rule + DesignState and Run=true outputs ValidStatus/RuleName/RuleDescription; with SendValid=true it publishes and returns SendStatus=true
  3. CLASSIFICATOR is absent from the built plugin; opening a v2.0 canvas shows a missing-component placeholder (release notes cover re-wiring)
  4. A published Run persists ValidStatus, SendStatus, and the 3-part state payload — confirmed by direct Neo4j query and read-back through VALIDATION GRAPH
  5. The Model Viewer lists and groups runs published with v2 payloads — group-by-State works via the adapted `_project_state_summary` projection, and pre-v7.0 runs with v1 payloads still render (read-side tolerance)

**Plans**: 5/5 plans complete
**Wave 1**

  - [x] 18-01-PLAN.md — DesignStateBindingService + ErrorMessageTemplates + tests — *wave 1* — GHVL-04
  - [x] 18-02-PLAN.md — RULE DECONSTRUCT extension (Objects/DataProperties outputs, VariableTypeInferrer partition) — *wave 1* — GHVL-01
  - [x] 18-03-PLAN.md — CLASSIFICATOR full purge (component, namespace, icon, tests) — *wave 1* — GHVL-02
  - [x] 18-04-PLAN.md — Model Viewer read-side (_project_state_summary v2, Python tests) — *wave 1* — GHVL-06

**Wave 2** *(blocked on Wave 1 completion)*

  - [x] 18-05-PLAN.md — VALIDATOR rework (new contract) + publish path extension — *wave 2, depends 18-01* — GHVL-03/05

### Phase 19: Deconstruct and Reinstate Components

**Goal**: Architects can take apart any stored DesignState back to its states, objects, and geometry, and re-apply captured parameters to the live canvas
**Depends on**: Phase 16 (state models), Phase 17 (VALIDATION GRAPH DesignState output); can run parallel to Phase 18
**Requirements**: GHST-05, GHST-06, GHST-07
**Success Criteria** (what must be TRUE):

  1. DESIGN STATE DECONSTRUCT splits a DesignState into ObjState/ParamState/PropState lists — composing them back through DESIGN STATE yields an equivalent state (round-trip)
  2. OBJECT DECONSTRUCT returns Object/Geometry/Label from an ObjState
  3. PARAMETER REINSTATE applies a ParamState to source sliders/toggles on a false→true Reinstate edge and outputs Parameters + StateStatus with the 7-value ReStatus reporting intact

**Plans**: 3/3 plans complete

- [x] 19-01-PLAN.md
- [x] 19-02-PLAN.md
- [x] 19-03-PLAN.md

**Wave 1** *(parallel — no dependencies)*

- [x] 19-01 — Infrastructure: ErrorMessageTemplates (deconstruct/reinstate templates + FormatStatus/FormatMessage), DgIcons (3 icon properties), 3 PNG files — *wave 1* — GHST-05/06/07 (shared infra) ✓

**Wave 2** *(parallel — both depend on 19-01)*

- 19-02 — DECONSTRUCT components: DESIGN STATE DECONSTRUCT (pure sync passthrough, DesignState -> ObjState/ParamState/PropState lists) + OBJECT DECONSTRUCT (pure sync passthrough, ObjState -> Object/Geometry/Label) — *wave 2, depends 19-01* — GHST-05/06 ✓
- 19-03 — PARAMETER REINSTATE: reworked REINSTATE (new GUID, required Target input, index-matched Parameters+StateStatus+Status, wire-traversal, rising-edge trigger, deferred write) — *wave 2, depends 19-01* — GHST-07 ✓

### Phase 20: E2E Validation and Docs

**Goal**: The full v7.0 pipeline runs end-to-end on live Docker with no data loss, and every breaking change is documented for canvas migration
**Depends on**: Phases 13–19
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04
**Success Criteria** (what must be TRUE):

  1. On live Docker: rule ingest → METAGRAPH → RULE DECONSTRUCT → OBJECT/PARAMETER/PROPERTY STATE → DESIGN STATE → VALIDATOR (publish) → VALIDATION GRAPH read-back → PARAMETER REINSTATE completes without errors in one canvas session
  2. Release notes document canvas breakage and re-wiring per component; the port↔IRI mapping doc is published
  3. `grep -ri "schema v3\|v3 schema"` over CLAUDE.md, .github/copilot-instructions.md, spec/, README.md returns no hits presenting v3 as current — all repo/AI-assistant docs teach schema v4 and the 14-component set
  4. DG_OBSIDIAN reflects v7.0: schema-v3 atlas note superseded, graphify regenerated via `scripts/refresh_graphify.sh` — no community note describes CLASSIFICATOR/VALIDATION RUNS or v3.0-phase plans as current work
  5. All 39 v7.0 requirements are checked off in REQUIREMENTS.md with traceability complete

**Plans**: 3/3 plans complete

Plans:

- [x] 20-01-PLAN.md — E2E Validation: create checklist + Docker automation, execute full chain, fix critical bugs inline — *wave 1* — E2E-01
- [x] 20-02-PLAN.md — Release Notes + Repo/AI Docs: re-wiring guide with ASCII diagrams, CLAUDE.md/copilot/DATABASE.md/README.md to v4, SC#3 grep gate — *wave 2, depends 20-01* — E2E-02/03
- [x] 20-03-PLAN.md — DG_OBSIDIAN + Graphify Refresh: archive stale notes, rewrite atlas to v4, regenerate graphify, finalize REQUIREMENTS.md — *wave 3, depends 20-02* — E2E-04

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 13. Ontology V7 and Contract Investigation | 4/4 | Complete    | 2026-07-03 |
| 14. Graph Schema v4 Propagation | 7/7 | Complete   | 2026-07-03 |
| 15. SpecGraph Runtime Rename | 5/5 | Complete    | 2026-07-03 |
| 16. DG.Core State Models and State Components | 6/6 | Complete   | 2026-07-04 |
| 17. Graph Access Components | 4/4 | Complete    | 2026-07-04 |
| 18. Rules and Validator Rework | 5/5 | Complete   | 2026-07-05 |
| 19. Deconstruct and Reinstate Components | 3/3 | Complete | 2026-07-05 |
| 20. E2E Validation and Docs | 3/3 | Complete   | 2026-07-05 |

---

*Roadmap updated: 2026-07-05 — Phase 19 complete (Plan 03 — PARAMETER REINSTATE component)*
*Roadmap updated: 2026-07-02 (audit amendment) — +5 requirements from full-codebase audit: kind-migration + training/test fixtures (Phase 14), Model Viewer read-side (Phase 18), repo/AI docs + DG_OBSIDIAN/graphify refresh (Phase 20); Phase 13 investigation scope extended with DesignState layer-placement and version-marker conflicts*
*Roadmap updated: 2026-07-02 — v7.0 phases 13-20 defined; v3.0 superseded (Phase 7 shipped, carried forward)*
*Roadmap updated: 2026-05-25 — v4.0 BOT Ontology Bridge added as planned milestone*
*v2.0 shipped: 2026-05-10*
