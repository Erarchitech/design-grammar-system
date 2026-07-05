---
gsd_state_version: 1.0
milestone: v7.0
milestone_name: — Update of DG Addin for Grasshopper
current_phase: 18
current_phase_name: rules-and-validator-rework
status: verifying
stopped_at: Phase 19 context gathered
last_updated: "2026-07-05T14:47:53.728Z"
last_activity: 2026-07-05
last_activity_desc: Phase 18 execution started
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 31
  completed_plans: 31
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-02)

**Core value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required
**Current focus:** Phase 18 — rules-and-validator-rework

## Current Position

Phase: 18 (rules-and-validator-rework) — EXECUTING
Plan: 5 of 5
Status: Phase complete — ready for verification
Last activity: 2026-07-05 — Phase 18 execution started

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v7.0)
- Average duration: —
- Total execution time: —

## Accumulated Context

### Decisions

Carried from v2.0:

- Single Neo4j DB with property isolation — ✓ Good
- No JSX build for main UI — ✓ Good
- SWRL bespoke regex parsing — ✓ Good
- ErrorMessageTemplates as static class in DG.Core.Services — ✓ Good
- Typed design state limited to Number/Integer/Boolean — ✓ Good
- Rising-edge trigger for reinstatement — ✓ Good

Shipped from v3.0 Phase 7 (carried into v7.0):

- Single `:DesignState` label + `kind` property (not multi-label) — mirrors Rule.kind pattern; kind enum revised for v7.0 to {ObjState, ParamState, PropState}
- Var merge key includes `project` — fixes latent v2.0 cross-project collision bug
- Variable type inferred at read-time via priority-chain (Object wins over Property) — VariableTypeInferrer in DG.Core.Parsing; drives v7.0 RULE DECONSTRUCT Objects/DataProperties partition
- DesignStateIdGenerator (DS_/OS_/OI_ prefixes) — id scheme extended in v7.0 for ObjState/ParamState/PropState

v3.0 decisions superseded by v7.0 (see PROJECT.md Key Decisions for replacements):

- ~~New GUID for RUN DECONSTRUCT~~ — component dropped; role taken by VALIDATION GRAPH
- ~~CLASSIFICATOR full input reset~~ — CLASSIFICATOR eliminated entirely (GHVL-02)
- ~~PropValues = renamed Values~~ — PROPERTY STATE owns value binding now
- ~~VALIDATOR input State → DefState~~ — VALIDATOR input is composed DesignState

Established for v7.0 (see PROJECT.md Key Decisions):

- Full ontology rename V6→V7 to match GH_DesignGrammars.pdf schema notation, guarded by a V6→V7 IRI recovery-mapping file
- KnowledgeGraph→SpecGraph runtime rename is in scope (closes pre-existing ontology↔runtime drift)
- Component ports: update where overlapping with the new schema, keep where no overlap (e.g. VALIDATOR's DataServiceUrl/Report/ValidationRunId extras)
- DB keeps existing Neo4j labels except Knowledge*→Spec* — no wider label migration
- [Phase 13]: Conflict (a): Run.ValidStatus unified as Boolean list index-matched to ObjState, overall pass derived (AND) not stored
- [Phase 13]: Conflict (b): DesignState storage layer corrected to graph='ValidGraph' with no-orphan invariant enforced
- [Phase 13]: Conflict (c): owl:versionInfo='7.0' as single source of version truth, stale v3 comment resolved
- [Phase 13]: PropState assigned ID prefix PS_ (Claude's discretion, extends DS_/OS_ pattern) — locked in DesignGrammar-V7.owl — V7-INVESTIGATION.md left the exact PropState ID prefix unspecified
- [Phase 13]: owl:DatatypeProperty self-check assertion uses SRC+6 (not exact parity) to account for the 3 new datatype properties this plan adds (RuleDescription, SendStatus, ValidStatus) — Exact SRC parity is mathematically impossible when new same-typed properties are added; corrupted-form detection (owl:DataProperty/owl:ObjProperty must be zero) is the real collision-hazard safety property
- [Phase 13]: PARAMETER REINSTATE StateStatus and OBJECT DECONSTRUCT/OBJECT STATE Label ports map to the real resolvable OWL IRIs (dgv:ReStatusValue, dgv:objectRefName) rather than the PDF's display-name ontology paths — V7-INVESTIGATION.md rename table names ReStatus as the class rdfs:label, not the IRI; the actual IRI is ReStatusValue. Geometry.Label has no dedicated OWL property, so objectRefName (the user-supplied ObjectRef string per PROJECT.md) is used instead
- [Phase 13]: Runtime/DB-only ports (credentials, driver handles, Boolean triggers, VALIDATOR publish extras) are explicitly annotated with a placeholder and note in port-iri-map-V7.md rather than omitted — Keeps the zero-unmapped-references invariant literal (every row has a non-empty IRI-column cell) while documenting the ontology<->DB gap per PROJECT.md policy
- [Phase 13]: BOT/Topologic V7 extensions require only a version bump + prose ComputationGraph->Computgraph rename (dg:Topology anchor unchanged in V7)
- [Phase 13]: make_docs_v6.py does not actually generate DesignGrammar-V6.md (it generates ONTOLOGY-ALIGNMENT-V6.md/HIERARCHY-OPTIMIZATION-V6.md instead) — make_docs_v7.py implemented as a purpose-built importlib driver invoking export_to_markdown_v7.main()
- [Phase ?]: Rule properties renamed: text->SWRL, title->RuleName, added RuleDescription (optional) — PascalCase per D-05
- [Phase ?]: DesignState MERGE block (//2b) removed from emitted CYPHER TEMPLATE BLOCK per D-03
- [Phase ?]: DesignState/Run documented as document-only with graph='ValidGraph' (D-14), three kinds {ObjState,ParamState,PropState}
- [Phase ?]: Run has only ValidStatus (Boolean list) and SendStatus (single Boolean) — no Status text field per D-01
- [Phase 14-graph-schema-v4-propagation]: Description coalesce also extended to RuleDescription alongside D-06's two mandated lines — completes same backward-compat contract enabled by the n8n RuleDescription backfill
- [Phase 14]: ValidStatus added as best-effort per-entity Boolean list; full per-ObjState index-matched population deferred to Phase 18 (GHVL-05) — Schema presence only per SCHM-12; binding logic is Phase 18 work

Shipped from Phase 16 Plan 01:

- ParamState replaces DesignStateSnapshot as the canonical type — identical 3-field shape (StateId, CapturedAtUtc, Collection<DesignStateParameter>), pure rename per D-14
- DesignState composition uses independent bag semantics per D-02 — ObjStates/ParamStates/PropStates as three separate List<> with no cross-index alignment
- PropValue typed as DesignStateParameter? reusing the existing typed-nullable pattern (Number/Integer/Boolean) per D-08
- DesignState internal list ordering preserves wiring order (not sorted); aggregate StateId computed from sorted member IDs independently of list order
- All 17 DesignStateSnapshot references updated to ParamState across DG.Core, DG.Grasshopper, and DG.Tests — mechanical rename, no behavior change
- DefState, ObjectState, ObjectInstance deleted (zero remaining type references)
- ObjState/PropState/DesignState/ParamState all unsealed (downstream may need inheritance)
- Geometry field on ObjState typed as object? — in-process Rhino/GH handle, excluded from serialization
- [Phase 16]: ParamStatePrefix reuses DS_ literal; DesignStatePrefix also DS_ — different hash input domains disambiguate per Research Finding 6
- [Phase 16]: PropStatePrefix = PS_ per D-11
- [Phase 16]: OI_ prefix and ComputeObjectInstanceId removed entirely — zero call sites per D-15
- [Phase 16]: ComputeObjectStateId (OS_) and IdRefPrefix (IDR_) preserved unchanged — not in Phase 16 scope
- [Phase ?]: Handle types are unsealed to permit public wrapper inheritance in DG namespace
- [Phase ?]: All 4 handles wrap the SAME ConnectionInfo instance - no per-handle connection logic
- [Phase ?]: GRAPH DECONSTRUCT is pure synchronous passthrough with no async, no DB calls, no CancellationTokenSource
- [Phase ?]: CONNECTOR Project output is a string passthrough of the PROJECT NAME input (scopes downstream queries)
- [Phase ?]: ErrorMessageTemplates follow What+Where+How-to-fix pattern for graph-access error surfaces

Shipped from Phase 17 Plan 03:

- [Phase 17]: OntologyProperty unsealed in Core (matching OntologyClass pattern) to allow DG.Grasshopper public wrapper inheritance
- [Phase 17]: GUID F8C6A4B2-1E3D-4F5A-8C7B-9D0E1F2A3B4C assigned to OntoGraphComponent

Shipped from Phase 17 Plan 04:

- [Phase 17]: Neo4jValidGraphRepository is a new parallel class, not a modification of ValidationRunsQueryService (preserved for Phase 18 removal)
- [Phase 17]: v1/v2 payload heuristic checks root JSON for stateKind/objStates keys to detect v2; falls back to DesignStateJsonSerializer for v1
- [Phase 17]: Status constructed as per-ObjState Boolean list (overall AND of all rules per ObjState), single-element for v1
- [Phase 17]: GUID 95fc9d32-307e-41fd-a158-bfae49a3dc2a assigned to ValidationGraphComponent (replaces old A7F2C3E1)
- [Phase 17]: RunInfo unsealed in Core (matching DesignState/ParamState/ObjState/PropState pattern) for public wrapper inheritance
- [Phase 17]: Old VALIDATION RUNS GUID (A7F2C3E1) fully purged — zero remaining references
- [Phase 18]: Builtin-only variables excluded from binding rows (D-07)
- [Phase 18]: Property values apply to ALL existing rows (not per-ObjState), matching VALIDATOR evaluation contract
- [Phase ?]: CLASSIFICATOR fully purged per D-09 (GHVL-02)
- [Phase ?]: Return shape identical for v1 and v2: only {stateId, capturedAtUtc, parameterCount} - no stateKind field

### Research Flags (carry into planning)

- Phase 13: resolve PDF-internal ValidStatus(Boolean)-vs-Status(text) conflict AND the DesignState storage-layer conflict (cypher_template stores DesignState with graph='Metagraph' at line ~50; PDF's VALIDATION GRAPH reads DesignState from the ValidGraph handle) before locking the port↔IRI map
- Phase 18: read VariableBinder.BuildBindings (DG.Core.Classification) before writing PLAN — its logic is being redistributed to OBJECT STATE/PROPERTY STATE/VALIDATOR, not deleted wholesale
- Phase 18: read data-service `_project_state_summary` (app.py ~521) + `graph-viewer/model-viewer/src/useValidationRunsGrouping.js` before writing PLAN — Model Viewer groups runs by `state.stateId` from the statePayloadJson projection (GHVL-06)
- Phase 15: read ValidationRunPersistenceService.cs + data-service/app.py statePayloadJson path before drafting the SpecGraph migration (adjacent Cypher, avoid collateral breakage)

### Pending Todos

- Execute Phase 13: /gsd-execute-phase 13 (4 plans, 3 waves — 13-01 locks names, 13-02 builds the V7 owl, 13-03/13-04 map ports + regenerate the bundle)
- Phase 19 can run parallel to Phase 18 once Phase 16/17 land — Phases 16/17 now complete, ready for parallel execution

### Blockers/Concerns

- .NET SDK 10.0.109 is installed on this machine (per 2026-06-23 session note); `dotnet test` requires `DOTNET_ROLL_FORWARD=LatestMajor` (net9.0 runtime absent — only 7/8/10). Verify once before Phase 16+ state-model changes land
- Pending migration from v3.0 Phase 7 still applies: `migrations/2026-06-23_var_project_merge_key.cypher` has not been run against live Neo4j

## Session Continuity

Last session: 2026-07-05T14:47:53.712Z
Stopped at: Phase 19 context gathered
Resume file: .planning/phases/19-deconstruct-and-reinstate-components/19-CONTEXT.md

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| v3.0 Phase 07 P01 | 20m | 2 tasks | 3 files |
| v3.0 Phase 07 P02 | 25min | 2 tasks | 5 files |
| v3.0 Phase 07 P03 | 18min | 2 tasks | 5 files |
| v3.0 Phase 07 P04 | 12min | 2 tasks | 5 files |
| Phase 13 P01 | 15min | 2 tasks | 1 files |
| Phase 13 P02 | 20min | 3 tasks | 3 files |
| Phase 13 P03 | 25min | 2 tasks | 1 files |
| Phase 13 P04 | 25min | 4 tasks | 9 files |
| Phase 14 P01 | 3min | 2 tasks | 2 files |
| Phase 14-graph-schema-v4-propagation P03 | 12min | 3 tasks | 4 files |
| Phase 14-graph-schema-v4-propagation P05 | 18min | 2 tasks | 3 files |
| Phase 14-graph-schema-v4-propagation P07 | 8min | 3 tasks | 4 files |
| Phase 16 P01 | 10min | 3 tasks | 25 files |
| Phase 16 P02 | 15m | 2 tasks | 2 files |
| Phase 16-dg-core-state-models-and-state-components P03 | 8 | 3 tasks | 3 files |
| Phase 17-graph-access-components P01 | 12m | 3 tasks | 22 files |
| Phase 17 P02 | 6m | 3 tasks | 6 files |
| Phase 17 P03 | 4m27s | 3 tasks | 6 files |
| Phase 17 P04 | 4m30s | 4 tasks | 8 files |
| Phase 18-rules-and-validator-rework P01 | 9m | 4 tasks | 5 files |
| Phase 18-rules-and-validator-rework P02 | 8m | - tasks | - files |
| Phase 18-rules-and-validator-rework P03 | 3m | - tasks | - files |
| Phase 18 PP04 | 6m | 2 tasks | 2 files |
| Phase 18-rules-and-validator-rework P05 | 12min | 3 tasks | 5 files |
