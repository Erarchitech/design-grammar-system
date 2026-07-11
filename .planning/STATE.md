---
gsd_state_version: 1.0
milestone: v8.2
milestone_name: Connector Integration & Reasoning Engine
current_phase: 821
current_phase_name: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation
status: executing
stopped_at: Phase 822 context gathered
last_updated: "2026-07-11T21:03:13.066Z"
last_activity: 2026-07-11
last_activity_desc: Phase 820 complete, transitioned to Phase 821
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-11)

**Core value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required
**Current focus:** Phase 820 — Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping

## Current Position

Phase: 821 — dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation
Plan: Not started
Status: Executing Phase 820
Last activity: 2026-07-11 — Phase 820 complete, transitioned to Phase 821

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 36 (v7.0)
- Average duration: —
- Total execution time: —

## Accumulated Context

### Decisions

Established for v8.2 (roadmap, Phases 820–824):

- [Roadmap]: REAS-05 (dg-reasoner sidecar + OntoGraph/Metagraph RDF translation) delivered as one merged phase (821) rather than the two sub-phases research suggested — keeps traceability single-owner per requirement; Phase 821 still carries the harder OntoGraph-translation research flag internally
- [Roadmap]: Phase 823 (SHACL) depends on Phase 821 only, not Phase 822 (OWL reasoning) — SHACL shape authoring doesn't need the OWL TBox question resolved, per research's phase-ordering rationale
- [Roadmap]: Phase 824 (CONNECTOR) has no dependency on Phases 820–823 and can be planned/executed in parallel at any point — zero shared code path with the reasoning work

Established for v8.1 Phase 815 Plan 01:

- [Phase 815]: Content modules discovered via `import.meta.glob('./##-*.js', {eager: true})` with ##- prefix sorting; adding a new module file auto-registers a section with zero viewer-code changes
- [Phase 815]: Block types follow Revit-API reference structure: text, code, endpoint (signature+params+request+response), table, note (info/warning/tip). The endpoint block reuses the existing CodeBlock component for request/response examples.
- [Phase 815]: No new shared primitives — the docs viewer reuses Button, CodeBlock, and design tokens from the V2 system. State is kept entirely local to the screen.

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

- [Phase 19 Plan 01]: ErrorMessageTemplates extended with FormatStatus/FormatMessage moved from old ReinstateComponent into DG.Core so Plans 2/3 can access them without DG.Grasshopper dependency — pure static functions on ReinstatementResult, testable from DG.Tests
- [Phase 19 Plan 01]: Deconstruct warning templates use D-07 Warning-level tone with "is required"/"Could not unwrap" wording; reinstate templates describe Target wire setup in What+Where+How-to-fix structure
- [Phase 19 Plan 01]: Minimal PNG icon placeholders sufficient — DgIcons.Load fallback to new Bitmap(24,24) guarantees compilation regardless of artwork quality

- [Phase 19 Plan 03]: _lastApplyInput initialized to true (not default false) — prevents first-solve auto-fire while preserving rising-edge behavior
- [Phase 19 Plan 03]: Wire-traversal restricted to Input 1 (Target) only — no fallback to Input 0 per D-02
- [Phase 19 Plan 03]: Parameters output always returns ALL params from ParamState (D-05), StateStatus index-matched to Parameters (D-04)
- [Phase ?]: E2E checklist structured as dual-purpose artifact (development QA + release/installation verification)

Established for v8.0 (Phase 21):

- [Phase 21]: V2 app lives at `ui-v2/` (Vite 5 + React 18, JSX/JS) — supersedes "no JSX build" for the retiring dark UI; single app hosts all four screen layers
- [Phase 21]: Fonts self-hosted — @fontsource latin woff2 vendored into `ui-v2/src/styles/tokens/fonts/`, no CDN at runtime
- [Phase 21]: Status tokens aligned to requirements over stale spec CSS — `--status-fail` = Signal Red (DSYS-01/MVIEW-03), pass = ink, base = mid-gray; reference spec files in design/v2 untouched
- [Phase 21]: No router library — layer-based navigation; dev-only specimen behind `#specimen` hash + DEV gate
- [Phase 22]: V2 auth reuses the legacy localStorage contract (`dg_users` salted SHA-256 + `dg_current_user`) — existing accounts survive cutover; full-name field split into legacy name/surname
- [Phase 22]: Engine-owned styling contract — canvas-engine-animated DOM carries classes only, never React style props (re-render safety); engine self-heals 0×0 mounts by re-measuring each frame
- [Phase 22]: Mockup dark-mode toggle dropped (out of scope per REQUIREMENTS); selected project persists at `dgv2_project`
- [Phase 23]: Datascape ring layers map 1:1 to live `graph` property values; node labels bucket into 3 orbits per layer; relationships → typed ring/cross edges
- [Phase 23]: V2 client reproduces the legacy post-ingest `tagProjectNodes` claim — the n8n workflows write to default-project (Set Input Defaults lacks `$json.body.project_name` fallback; repo JSONs patched) and the client claims nodes for the active project
- [Phase 23]: graph-query-mcp.json Build Cypher Prompt had a fatal quote-syntax error (from parked v9.0 rewiring) — fixed and re-imported; live n8n workflows have drifted ahead of repo JSONs (user edits, versionCounter 22)
- [Phase 24]: Model viewer map is deterministic synthetic iso massing from entity-id hashes (spec's stylised map; Speckle 3D deferred); rule SWRL resolved from metagraph Rule.SWRL, not data-service
- [Phase 24]: v2.0-era validation data carries graph:'ValidationGraph' (pre-v4) — invisible to data-service until migrations/2026-07-07_validationgraph_to_validgraph.cypher runs (NEEDS USER APPROVAL; auto-mode denied bulk mutation); v8-ui-smoke seed fixture covers UI verification meanwhile

Shipped from Phase 20 Plan 02:

- [Phase 20]: Release notes use per-component structure: old name -> new name, what broke, ASCII diagram, port mapping table, GUID changes — consistent layout across all 7 affected components
- [Phase 20]: copilot-instructions.md rewritten as full replacement (not patch) per D-10 — avoids v3 remnants in retained sections
- [Phase 20]: spec/DATABASE.md v3 migration notes preserved as historical section prefaced "v3->v4 migration (complete)" — keeps institutional knowledge
- [Phase ?]: Reasoner settings stored as plain JSON (no encryption needed)
- [Phase ?]: Registry structured with explicit status field for future integrated/non-placeholder reasoners

### Research Flags (carry into planning)

- Phase 820: OntoGraph axiom-scoping decision is genuinely open-ended (extend LLM ingestion vs. scope down vs. hybrid) — needs a prototype/spike against real project data, not just a literature read
- Phase 821: the OntoGraph half of the LPG→OWL translation has no standard shortcut (unlike Metagraph's SWRL-vocabulary mapping) — highest-risk piece for silent edge-property data loss (`ARG.pos`, `HAS_BODY/HAS_HEAD.order`); flag for `--research-phase`
- Phase 13: resolve PDF-internal ValidStatus(Boolean)-vs-Status(text) conflict AND the DesignState storage-layer conflict (cypher_template stores DesignState with graph='Metagraph' at line ~50; PDF's VALIDATION GRAPH reads DesignState from the ValidGraph handle) before locking the port↔IRI map
- Phase 18: read VariableBinder.BuildBindings (DG.Core.Classification) before writing PLAN — its logic is being redistributed to OBJECT STATE/PROPERTY STATE/VALIDATOR, not deleted wholesale
- Phase 18: read data-service `_project_state_summary` (app.py ~521) + `graph-viewer/model-viewer/src/useValidationRunsGrouping.js` before writing PLAN — Model Viewer groups runs by `state.stateId` from the statePayloadJson projection (GHVL-06)
- Phase 15: read ValidationRunPersistenceService.cs + data-service/app.py statePayloadJson path before drafting the SpecGraph migration (adjacent Cypher, avoid collateral breakage)

### Pending Todos

- **USER APPROVAL NEEDED**: run `migrations/2026-07-07_validationgraph_to_validgraph.cypher` — v2.0-era validation runs (project TestA, 20 runs/1148 entities) invisible to data-service until then (auto-mode denied the bulk mutation)
- **Reconcile n8n workflows**: live instance versions drifted ahead of `n8n/workflows/*.json` (user editor changes, versionCounter 22); repo JSONs carry the quote-syntax + project_name body-fallback fixes — export live → repo or re-import repo → live
- Optional cleanup: test rules ingested during v8.0 verification now live under project `v8-ui-smoke` (claimed from default-project); delete with `MATCH (n {project:'v8-ui-smoke'}) DETACH DELETE n` if unwanted
- Resume v9.0 AI Workflow Intelligence after v8.2 ships — Phase 28 (cloud-llm-connector, renumbered from 01 on 2026-07-08) executed and parked in .planning/milestones/v9.0-phases/28-cloud-llm-connector/; UAT item "E2E provider switch" still human-needed
- Formal `/gsd-complete-milestone` pass for v8.1 still pending (all 7 phases complete and verified 2026-07-11, not yet archived)

### Blockers/Concerns

- .NET SDK 10.0.109 is installed on this machine (per 2026-06-23 session note); `dotnet test` requires `DOTNET_ROLL_FORWARD=LatestMajor` (net9.0 runtime absent — only 7/8/10). Verify once before Phase 821+ C#/sidecar changes land
- Pending migration from v3.0 Phase 7 still applies: `migrations/2026-06-23_var_project_merge_key.cypher` has not been run against live Neo4j
- v8.2 Phase 820 spike outcome (OntoGraph axiom-scoping decision) gates Phases 821–823 — do not start sidecar/translation/SHACL implementation before Phase 820's Key Decision is recorded

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260711-gtz | Decrease the size of title in the landing page so it fits the ring | 2026-07-11 | c60f541 | [260711-gtz-decrease-the-size-of-title-in-the-landin](./quick/260711-gtz-decrease-the-size-of-title-in-the-landin/) |
| 260711-shf | Fold Session History panel on outside click | 2026-07-11 | 06c0dd1 | [260711-shf-fold-session-history-on-outside-click](./quick/260711-shf-fold-session-history-on-outside-click/) |
| 260711-i63 | Graph core thinking-sphere animation during Ingest/Query/Edit with node-emergence streams (Higgsfield loop video + procedural streams) | 2026-07-11 | d1e3483 | [260711-i63-add-graph-core-thinking-sphere-animation](./quick/260711-i63-add-graph-core-thinking-sphere-animation/) |
| Phase 814-reasoner-screen P814-01 | 9min | 3 tasks | 5 files |
| Phase 815-dg-api-documentation 815-01 | 8min | 3 tasks | 9 files |

## Session Continuity

Last session: 2026-07-11T21:03:13.053Z
Stopped at: Phase 822 context gathered
Resume file: .planning/phases/822-owl-2-dl-reasoning-integration-reasoner-screen-wiring/822-CONTEXT.md

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
| Phase 19 P01 | 12min | 2 tasks | 7 files |
| Phase 19-deconstruct-and-reinstate-components P02 | 3m | 2 tasks | 4 files |
| Phase 19-deconstruct-and-reinstate-components P03 | 8min | 2 tasks | 2 files |
| Phase 20-e2e-validation-and-docs P01 | 15min | 2 tasks | 4 files |
| Phase 20-e2e-validation-and-docs P02 | 25min | 3 tasks | 6 files |
| Phase 21-design-system-foundation P01 | 35min | 3 tasks | 46 files |
| Phase 22-navigation-shell-landing-auth P01 | 45min | 2 tasks | 9 files |
| Phase 23-graph-viewer P01 | 2.5h | 4 tasks | 7 files |
| Phase 24-model-viewer P01 | 1h | 2 tasks | 5 files |
| Phase 25-projects-and-scoping P01 | 25min | 1 task | 2 files |
| Phase 27-speckle-3d-embed P27-01 | ~18m | - tasks | - files |
