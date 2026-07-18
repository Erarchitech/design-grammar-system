---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: — AI Workflow Intelligence
current_phase: 32.1
current_phase_name: DG ID
status: verifying
stopped_at: Completed 32-02-PLAN.md (CanvasAnnotationParser + 15-fact unit matrix, both tasks committed)
last_updated: "2026-07-18T13:19:39.521Z"
last_activity: 2026-07-18
last_activity_desc: Phase 32 complete, transitioned to Phase 32.1
progress:
  total_phases: 14
  completed_phases: 2
  total_plans: 23
  completed_plans: 17
  percent: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-11)

**Core value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required
**Current focus:** Phase 32 — computgraph-serialization-core

## Current Position

Phase: 32.1 — Cross-Platform Identity and Mapping (DG ID)
Plan: 06 (cross-platform-identity-and-mapping-dg-id) — completed
Status: Phase complete — ready for verification
Last activity: 2026-07-18 — Plan 06 completed: ObjState DgId wiring + ObjStateDgIdTests (round-trip, backward-compat, minting parity); 290/290 tests green

## Deferred Items

Deferred at v8.2 milestone close on 2026-07-12 (override closeout); **2 of 3 closed on 2026-07-13** (gap-closure session):

| Category | Item | Status | Resume |
|----------|------|--------|--------|
| verification | Phase 822 (OWL 2 DL + Reasoner wiring) | **closed 2026-07-13 — passed** | All 3 frontend UAT scenarios executed live and passed (real kill-on-timeout → Inconclusive; Inconsistent verdict with human labels; Run/Cancel/Consistent click-through) — see archived 822-UAT.md; 822-VERIFICATION.md now `status: passed` |
| verification | Phase 823 (SHACL Validation Layer) | **closed 2026-07-13 — passed** | Retroactive 823-VERIFICATION.md written (4/4 truths; fresh in-container suites dg-reasoner 39/39 + data-service 168/168, DG 234/234; live /shacl/validate round-trip) |
| verification | Phase 824 (CONNECTOR Credential) | human_needed | /gsd-verify-work 824 — 3 in-Rhino UAT checks (live Grasshopper + data-service); the ONLY remaining v8.2 verification item |

The 3 in-Rhino acceptance checks for 824 (valid-token heartbeat → Auth OK; bad-token Error / service-down Warning with outputs still populating; internalised token scrubbed from a saved `.gh` + old canvas opens) are in `.planning/milestones/v8.2-phases/824-connector-credential-integration/824-UAT.md`. All automatable checks (build, 234 unit tests, source assertions) pass. Confirmed 2026-07-13: `dotnet test` runs clean on net9.0 without `DOTNET_ROLL_FORWARD` (the old "net9.0 runtime absent" blocker is stale — removed from Blockers). One intermittent order-dependent flake observed once in `DG.Tests.E2E.DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve` (passes in isolation and on re-run) — follow-up task flagged.

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
- [Phase 825 (CONNG-03 follow-up, 2026-07-13)]: CONNECTOR reduced to Token+Connect — the project-scoped token authenticated by data-service returns the project + host-facing Neo4j bundle (`NEO4J_PUBLIC_URI`, default `bolt://localhost:7687`); component derives the whole connection from it (ADR-825-6: auth gates the bolt attempt). **New CONNECTOR GUID `3F9B1C7E-6A24-4D53-8E10-9C2A5B7D40F1`** (was `24E78A17-…`) — backward compat intentionally broken (user-approved); old 8-input canvases show a missing-component placeholder. Token typeable live, scrubbed at .gh save via `NonPersistentStringParam` (replaces the 824 every-solve scrub). data-service 23/23 + build 0/0 + DG.Tests 236/236; in-Rhino UAT deferred (825-UAT.md). Also fixed a live UI bug: `ConnectorCard` never forwarded `onSetLabelInput` to `CredentialSection`, so the create-credential Label field was frozen ("field not active").

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
- [Phase ?]: [Phase 821 Plan 01]: openjdk-17-jre-headless unavailable on Debian trixie (python:3.11-slim base) - substituted openjdk-21-jre-headless per plan's documented fallback (proven in 820 spike, HermiT floor is Java 1.5+)
- [Phase ?]: [Phase 821 Plan 01]: dg-reasoner/requirements.txt pins starlette<1.0.0 + httpx - unpinned fastapi resolves starlette>=1.0 whose TestClient requires a new package (httpx2) instead of the already-vetted httpx used elsewhere in this repo
- [Phase ?]: [Phase 821 Plan 01]: n10s installed via custom neo4j/Dockerfile (neo4j:5.26 + wget-fetched neosemantics-5.26.0.jar), not NEO4J_PLUGINS auto-download, per RESEARCH.md flakiness warning (docker-neo4j#489)
- [Phase ?]: [Phase 821 Plan 02]: build_graph(session, project) duck-types neo4j.Session.run() without importing neo4j at module scope -- unit-testable via a fixture-backed FixtureSession with zero mocking
- [Phase ?]: [Phase 821 Plan 02]: owl:AllDifferent (UNA) deliberately deferred to Phase 823's ValidGraph ABox export per spec's explicit scope boundary -- not implemented in ontology_export.py
- [Phase 821]: [Phase 821 Plan 03]: reasoning.py functions accept an injectable session param (default None -> lazy module driver) so tests bypass live Neo4j entirely -- app.py opens one session per request and passes it through
- [Phase 821]: [Phase 821 Plan 03]: HermiT/Owlready2's sync_reasoner() runs inside a multiprocessing.Process joined with DG_REASONER_TIMEOUT_SECONDS, terminate() on expiry kills the java grandchild too (D-09) -- child reports results back via a Queue
- [Phase 821]: [Phase 821 Plan 03]: run_shacl validates the live per-project export (not the full hybrid TBox union) against an empty placeholder shapes graph -- real shapes deferred to Phase 823 (D-11)
- [Phase ?]: [Phase 821 Plan 04]: httpx.post(...) sync proxy with an explicit httpx.Timeout(connect=2.0, read=5.0, write=2.0, pool=2.0) -- matches app.py's prevailing sync-def style and llm_gateway.py's existing sync httpx.Client(timeout=...) pattern rather than introducing async
- [Phase ?]: [Phase 821 Plan 04]: dg-reasoner and data-service Docker images had to be rebuilt mid-plan -- both containers were still running Plan 01-era stub code, so live verification of Plans 02/03/04 code required an explicit docker compose build + up -d
- [Phase ?]: [Phase 822 Plan 01]: _local_name splits on last '#' first, then last '/', else returns IRI unchanged -- guarantees non-empty, non-http-prefixed fallback label
- [Phase ?]: [Phase 822 Plan 01]: Label resolution order is first non-empty owlready2 Class.label element, else _local_name(iri) fallback -- matches D-02
- [Phase ?]: [Phase 822 Plan 02]: Proxy read timeout expression is float(os.getenv('DG_REASONER_TIMEOUT_SECONDS','90'))+10 -- tracks sidecar's actual configured ceiling instead of a hardcoded literal, connect/write/pool stay 2.0s
- [Phase ?]: [Phase 822 Plan 02]: HermiT registry status flipped to 'integrated' per D-04; Pellet stays 'placeholder' -- Pellet integration explicitly out of phase scope
- [Phase ?]: [Phase 822 Plan 03]: runConsistencyCheck does not reuse getJson and does not throw on non-2xx -- returns {ok,status,body} so the caller branches on body shape (D-08/D-09)
- [Phase ?]: [Phase 822 Plan 03]: Run/Cancel controls and the result region are gated on r.status === 'integrated', not on card selection -- a user can run the check without re-selecting HermiT
- [Phase ?]: [Phase 822 Plan 03]: Each terminal verdict state renders its own re-run Run check button (Consistent/Inconsistent/Unknown/Cancelled); Error mirrors the existing loadError inline-Retry pattern instead
- [Phase ?]: [Phase 822 Plan 04]: Backend automated gate (dg-reasoner 19/19 incl. live HermiT round-trip, data-service 13/13, live curl) accepted as sufficient to close the phase; manual frontend UAT (Steps A-G) explicitly skipped per user decision rather than run partially
- [Phase 823]: [Phase 823 Plan 02] Sidecar {project, run_id?} contract extension pattern: add the field to the Pydantic model + the Python function signature + the route call simultaneously to avoid breaking the 821 backward-compat test
- [Phase 823 Plan 03]: publish_validation wraps _call_shacl_validate + _persist_shacl_report in one outer try/except (not just the proxy's internal catch-all) so a persistence-layer failure also degrades to shacl:{status:unavailable} instead of raising
- [Phase 823 Plan 03]: shaclReport parsing added only to the /validation/view/* route family (build_view_payload/get_validation_run), not list_validation_runs -- confirmed via ui-v2/src/lib/modelApi.js + ModelScreen.jsx that view is the selected-run-detail path
- [Phase ?]: [Phase 823 Plan 05] SHACL DTOs live in DG.Core.Validation (public), not DG.Grasshopper.Validation (internal) -- DG.Tests (net9.0) cannot ProjectReference DG.Grasshopper (net7.0-windows7.0, NU1201 TFM incompatibility confirmed via probe restore)
- [Phase ?]: [Phase 823 Plan 05] ValidatorComponent SHACL surfacing caps runtime message level at Warning/Remark, never Error, per D-15 -- Error stays reserved for the pre-existing publish-exception catch block
- [Phase 823]: [Phase 823 Plan 06] Task 3 checkpoint:human-verify closed via user 'approved' response with no code changes -- state selection keys strictly on shaclReport.results.length, never a conforms boolean
- [Phase ?]: [Phase 29 Plan 01]: Catalog resolves via DG_KNOWLEDGE_REPO_ROOT (Docker /mnt/repo mount) -- confirmed inside the running container, zero Dockerfile change needed
- [Phase ?]: [Phase 29 Plan 01]: existence_count models D-12's builtin atom pair as swrlb:greaterThanOrEqual + swrlb:lessThan against a project-keyed ?count Var
- [Phase ?]: [Phase 29 Plan 02]: SWRL_CONVENTIONS structured as four independently-addressable top-level keys (violation_inversion, atom_ordering, argument_rules, naming_quirks) rather than a single prose blob
- [Phase ?]: [Phase 29 Plan 02]: Computgraph catalog reuses ontology/export_to_markdown_v7.py's OWL-walking helpers via importlib.util.spec_from_file_location (mirrors ontology/make_docs_v7.py's own driver) instead of writing a second OWL parser
- [Phase ?]: [Phase 29 Plan 02]: RESEARCH.md Pitfall 4 (DOCTYPE entity block breaking ElementTree.parse) confirmed NOT to apply to DesignGrammar-V7.owl -- plain ET.parse() resolves the internal entity table natively, no custom resolver needed
- [Phase 29 Plan 03]: assemble_context() + /context/assemble + /context/debug live and complete (all 3 tasks); ContextAssembleRequest.type kept as plain str (not Pydantic Literal), validated by assemble_context()'s own ValueError dispatch so unknown types surface as CONTEXT_TYPE_INVALID 422 (not FastAPI's generic validation error)
- [Phase 29 Plan 03]: Task 3 checkpoint:human-verify closed via user "approved" response with no code changes -- the rule_edit Rule_Id-regenerate-on-numeric-change + old-atom MATCH-DELETE cleanup + ontology iri/SWRL_label-preserve convention (_RULE_EDIT_GUIDANCE, Pitfall 3 resolution) is locked as documented and frozen for Phase 31 RING-02's diff-preview design
- [Phase 29]: GenerateCypherRequest.type kept as plain str (not Literal), matching 29-03's ContextAssembleRequest ValueError-dispatch precedent
- [Phase 29]: Label extraction corrected to walk every :Label in a multi-label chain (n:LabelA:LabelB) -- the n8n JS precedent's greedy regex only captured the last label
- [Phase 29]: generate_validated_cypher() validates request_type upfront before touching the adapter -- fails fast on an unknown type without a live LLM call
- [Phase ?]: Task 1 (29-05) resolved as reimport-repo-first: live n8n rules-to-metagraph.json overwritten with repo content (Phase 28 LLM-gateway caller), reconciling drift (versionCounter 33->34)
- [Phase ?]: n8n prompt nodes (rules-to-metagraph.json, graph-query-mcp.json) reduced to thin callers of /context/assemble + /context/generate-cypher; both live workflows re-synced and verified byte-identical to repo
- [Phase ?]: [Phase 32 Plan 01]: CgObject.Source stays a plain string ("tagged"|"recognized"), not enum -- matches freeform envelope value, Phase 35 adds recognized
- [Phase ?]: [Phase 32 Plan 01]: SliderDomain and the three enums (ParamKind/ParamDataType/IfaceType) live alongside their owning entity file rather than separate files -- keeps file count at the plan's specified 10
- [Phase ?]: [Phase 32 Plan 01]: CgDefinition shared by both CgContext and RawCanvas (not duplicated) -- both envelopes carry identical documentId/fileName/capturedAt semantics
- [Phase ?]: [Phase 32 Plan 02]: CanvasAnnotationParser pattern-host resolution deferred until after immediate host ids are computed into a plain Dictionary, since CgPattern.HostPatternId is init-only
- [Phase ?]: [Phase 32 Plan 02]: CgInterface.IfaceType defaults to Input for all parsed interfaces -- the NN_IntF_NAME grammar carries no Input/Output marker; Phase 35 recognition refines it
- [Phase ?]: [Phase 32 Plan 03]: CgParameterDto.Kind (not ParamKind) so camelCase emits 'kind' matching cgContextJson v1 envelope verbatim (RESEARCH.md section 5)
- [Phase ?]: [Phase 32 Plan 03]: Warnings sorted StringComparer.Ordinal alongside every other collection per plan's explicit instruction, prioritizing determinism/idempotency over warning-message sequence
- [Phase 32-05]: Checked-in Frame RawCanvas fixture with descriptive-string node ids (not real GUID format) since nothing in the model/parser/serializer validates them as Guid — Readability over format realism for a hand-authored fixture; no downstream consumer parses these as System.Guid
- [Phase ?]: [Phase 32.1 Plan 01]: DgIdMintingService uses classic string.IsNullOrWhiteSpace guards, not net8+ ArgumentException.ThrowIfNullOrWhiteSpace, because DG.Core multi-targets net7.0
- [Phase ?]: [Phase 32.1 Plan 01]: Golden vector (p1|frame.gh|cg:1:proc:11_Proc) -> dg:BC8E62EE137E2B56 anchors cross-language parity for data-service compute_dg_id (Plan 03)
- [Phase ?]: dgId scheme documented: dg: + 16 hex SHA-256(project|definitionId|cgId), Revit binds UniqueId not ElementId, Representation/SharedProperty under graph:'Computgraph'
- [Phase ?]: Rename re-mints by default (member-GUID carry-forward escape hatch deferred); shared-property conflict policy is last-write-wins for MVP

### Research Flags (carry into planning)

- Phase 820: OntoGraph axiom-scoping decision is genuinely open-ended (extend LLM ingestion vs. scope down vs. hybrid) — needs a prototype/spike against real project data, not just a literature read
- Phase 821: the OntoGraph half of the LPG→OWL translation has no standard shortcut (unlike Metagraph's SWRL-vocabulary mapping) — highest-risk piece for silent edge-property data loss (`ARG.pos`, `HAS_BODY/HAS_HEAD.order`); flag for `--research-phase`
- Phase 13: resolve PDF-internal ValidStatus(Boolean)-vs-Status(text) conflict AND the DesignState storage-layer conflict (cypher_template stores DesignState with graph='Metagraph' at line ~50; PDF's VALIDATION GRAPH reads DesignState from the ValidGraph handle) before locking the port↔IRI map
- Phase 18: read VariableBinder.BuildBindings (DG.Core.Classification) before writing PLAN — its logic is being redistributed to OBJECT STATE/PROPERTY STATE/VALIDATOR, not deleted wholesale
- Phase 18: read data-service `_project_state_summary` (app.py ~521) + `graph-viewer/model-viewer/src/useValidationRunsGrouping.js` before writing PLAN — Model Viewer groups runs by `state.stateId` from the statePayloadJson projection (GHVL-06)
- Phase 15: read ValidationRunPersistenceService.cs + data-service/app.py statePayloadJson path before drafting the SpecGraph migration (adjacent Cypher, avoid collateral breakage)

### Pending Todos

- **USER APPROVAL NEEDED**: run `migrations/2026-07-07_validationgraph_to_validgraph.cypher` — v2.0-era validation runs (project TestA, 20 runs/1148 entities) invisible to data-service until then (auto-mode denied the bulk mutation)
- Optional cleanup: test rules ingested during v8.0 verification now live under project `v8-ui-smoke` (claimed from default-project); delete with `MATCH (n {project:'v8-ui-smoke'}) DETACH DELETE n` if unwanted — note: `v8-ui-smoke` is currently the reasoner/SHACL verification fixture (822/823 evidence runs use it), so keep it until an alternative fixture project exists
- Phase 28 UAT item "E2E provider switch" still human-needed (cloud-llm-connector, archived in .planning/milestones/v9.0-phases/28-cloud-llm-connector/)
- Phase 824's 3 in-Rhino UAT checks — the only remaining v8.2 verification item (see Deferred Items)
- Consider a phase (825–829 free block or v9.0 insert) for the reasoner value gap: post-ingest/edit consistency gate + taxonomy emission on ingest + staged-autonomy repair — analysis in `.planning/research/REASONER-VALUE-AND-AUTOREPAIR.md` (2026-07-13)
- ~~Reconcile n8n workflows~~ — RESOLVED in Phase 29-05 (2026-07-12): both live workflows overwritten with repo content and re-verified byte-identical
- ~~Formal `/gsd-complete-milestone` pass for v8.1~~ — RESOLVED 2026-07-13: MILESTONES.md entry written, retroactive VERIFICATION.md for 810–813, 813-01-SUMMARY, requirement checkboxes/traceability flipped, RETROSPECTIVE v8.1 section added

### Blockers/Concerns

- Pending migration from v3.0 Phase 7 still applies: `migrations/2026-06-23_var_project_merge_key.cypher` has not been run against live Neo4j
- ~~net9.0 runtime absent / `DOTNET_ROLL_FORWARD` required~~ — STALE, removed 2026-07-13: `dotnet test` runs clean on net9.0 (confirmed twice: 824 verification and the 2026-07-13 gap-closure 234/234 run)
- ~~Phase 820 spike gates 821–823~~ — RESOLVED: Phase 820's Key Decisions recorded (ADR-820-1/2); v8.2 shipped

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260711-gtz | Decrease the size of title in the landing page so it fits the ring | 2026-07-11 | c60f541 | [260711-gtz-decrease-the-size-of-title-in-the-landin](./quick/260711-gtz-decrease-the-size-of-title-in-the-landin/) |
| 260711-shf | Fold Session History panel on outside click | 2026-07-11 | 06c0dd1 | [260711-shf-fold-session-history-on-outside-click](./quick/260711-shf-fold-session-history-on-outside-click/) |
| 260711-i63 | Graph core thinking-sphere animation during Ingest/Query/Edit with node-emergence streams (Higgsfield loop video + procedural streams) | 2026-07-11 | d1e3483 | [260711-i63-add-graph-core-thinking-sphere-animation](./quick/260711-i63-add-graph-core-thinking-sphere-animation/) |
| Phase 814-reasoner-screen P814-01 | 9min | 3 tasks | 5 files |
| Phase 815-dg-api-documentation 815-01 | 8min | 3 tasks | 9 files |
| Phase 821 P01 | 40min | 2 tasks | 8 files |
| Phase 821 P02 | 25min | 2 tasks | 3 files |
| Phase 821 P03 | 30min | 3 tasks | 4 files |
| Phase 821 P04 | 7min | 2 tasks | 3 files |
| Phase 822 P01 | 15min | 2 tasks | 2 files |
| Phase 822 P02 | 12min | 3 tasks | 3 files |
| Phase 822 P03 | 35min | 3 tasks | 2 files |
| Phase 822 P04 | 45min | 2 tasks | 0 files |
| Phase 823 P02 | 15min | 3 tasks | 2 files |
| Phase 823 P03 | 20min | 2 tasks | 2 files |
| Phase 823 P05 | 35min | 3 tasks | 7 files |
| Phase 823-shacl-validation-layer P06 | 10min | 3 tasks | 4 files |
| Phase 29 P01 | 20min | 2 tasks | 3 files |
| Phase 29 P02 | 25min | 2 tasks | 2 files |
| Phase 29 P03 | 35min | 3 tasks | 3 files |
| Phase 29 P04 | 50min | 2 tasks | 3 files |
| Phase 29 P05 | 55min | 3 tasks | 3 files |
| Phase 32 P01 | 20min | 2 tasks | 11 files |
| Phase 32 P02 | 35min | 2 tasks | 2 files |
| Phase 32 P03 | 25min | 2 tasks | 2 files |
| Phase 32 P04 | 30min | 2 tasks | 1 files |
| Phase 32 P05 | 30min | 2 tasks | 3 files |
| Phase 32.1 P01 | 2min | 2 tasks | 3 files |
| Phase 32.1 P02 | 15m | 2 tasks | 2 files |

## Session Continuity

Last session: 2026-07-18T13:18:30.638Z
Stopped at: Completed 32-02-PLAN.md (CanvasAnnotationParser + 15-fact unit matrix, both tasks committed)
Resume file: None

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

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
