# Research Summary: v3.0 Typed Variables and Composable Design State

**Project:** Design Grammar System — v3.0 Typed Variables and Composable Design State
**Domain:** Parametric architectural compliance checking — SWRL/OWL rule system, Grasshopper plugin, Neo4j metagraph
**Researched:** 2026-05-11
**Confidence:** HIGH (all four researchers grounded findings in direct codebase inspection)

---

## Open Questions — Answer Before Writing Requirements

These five questions have architectural consequences. Requirements should not be drafted until they are resolved, because each affects data contracts that cascade across all phases.

**Q1 — DesignState hierarchy strategy in Neo4j (CRITICAL)**

Two researchers split on this. STACK.md recommends multi-label nodes (`:DesignState:DefState`, `:DesignState:ObjectState`). ARCHITECTURE.md recommends single label `DesignState` with `kind` property (`DefState` | `ObjectState`), citing the established `Rule.kind` pattern and NeoVis rendering instability with multi-label nodes. See the Disagreements section for full tradeoff analysis. **Which pattern do you want?**

**Q2 — ObjectRef stable identity mechanism (CRITICAL)**

FEATURES.md insists the user must supply a semantic string ID (e.g. Rhino GUID from the model) because geometry-hash IDs break whenever geometry changes during design exploration. STACK.md and ARCHITECTURE.md both assume this too. The anti-feature automatic geometry-hash-based ID generation is explicitly rejected by all three researchers. **Confirm: ObjectRef is a user-supplied string, not auto-computed. Do users need a UI affordance (panel label, tooltip) to understand what to wire there, or is documentation sufficient?**

**Q3 — VALIDATION RUNS rename migration strategy (HIGH)**

PITFALLS.md flags two options for the VALIDATION RUNS to RUN DECONSTRUCT rename: (a) new ComponentGuid, accept canvas breakage, document re-wire steps; (b) keep old Guid, add one-release migration shim that shows "re-wire required" instead of null outputs. Option (b) is the safer user experience but requires writing a shim. **Which approach do you want?**

**Q4 — CLASSIFICATOR input ordering strategy (HIGH)**

PITFALLS.md documents that adding inputs between existing indices 0 to 3 causes silent wire misrouting in saved v2.0 canvases. The safe approach (append all new inputs after index 3) conflicts with the documentation-friendly ordering shown in PROJECT.md. **Do you require backward-wire-safe index ordering (append-only), or is a clean break acceptable with a migration warning in Read()?**

**Q5 — Var node merge key fix scope (CRITICAL, v2.0 bug)**

Pitfall P4 exposes a latent v2.0 bug: MERGE on Var nodes uses only name as the merge key, meaning variables with the same name across projects silently share a single Var node. This must be fixed before v3.0 cross-rule identity is built on top of it. The fix requires a Cypher template change, a data migration on existing Var nodes, and an n8n workflow update. **Confirm this lands in Phase 1 as a prerequisite (not a v3.0 feature), and that you accept the schema migration risk on existing Var nodes.**

---

## Executive Summary

v3.0 restructures the DG Grasshopper plugin around two new data concepts: typed variables (Object vs Property, inferred from SWRL atom structure) and a composable DesignState hierarchy (DefState for parametric capture plus ObjectState for element identity plus their parent class). These changes touch every component in the GH canvas pipeline — METAGRAPH, RULE DECONSTRUCT, DESIGN STATE, CLASSIFICATOR, VALIDATOR publish path, and the new OBJECT STATE and VARIABLE NAME components — plus six schema-propagation surfaces outside the plugin. The research confirms that no new NuGet packages, pip packages, or Docker services are required. All v3.0 features are achievable with the existing stack by extending in-place.

The core architectural finding is that variable type is derived data: it is 100% computable at read time in Neo4jRuleRepository.PopulateVariables() from the atom structure already stored in Neo4j. Writing it to Neo4j or inferring it in n8n would be redundant and error-prone. Similarly, cross-rule Object variable identity should be anchored to a user-supplied semantic string (the ObjectRef), not to a computed geometry hash — geometry hashes break on every design change, which is exactly when cross-run identity matters most. The DESIGN STATE component caches IdRefs keyed by DefState content hash to avoid re-scanning geometry on every solve.

The largest risk in v3.0 is not technical complexity — it is backward compatibility. The component rework changes input/output counts and indices on CLASSIFICATOR (4 to 8+ inputs), RULE DECONSTRUCT (6 to 4 outputs), and renames VALIDATION RUNS to RUN DECONSTRUCT. Existing .gh canvas files will have misrouted wires if migration guards are not applied. A latent v2.0 bug (P4: Var nodes share across projects via name-only merge key) must be patched in Phase 1 before any cross-rule identity feature is built on top of it, or the cross-rule identity mechanism will be built on a broken foundation. Schema propagation across all six surfaces (C# models, cypher_template.txt, dataset_schema.json, n8n workflow prompts, config.template.js, data-service Cypher) must be treated as a first-class deliverable in Phase 1, not a follow-up.

---

## Resolved Findings

The following areas had researcher agreement and can be treated as decided.

### Stack — No New Dependencies

**Confidence: HIGH** (verified against NuGet, pip, Rhino developer docs, direct codebase read)

All v3.0 features are implemented within the existing stack. Neo4j.Driver stays at 5.28.2 — 6.0.0 drops .NET 7 support and renames transaction APIs; upgrading breaks net7.0-windows with no v3.0 benefit. System.Security.Cryptography.SHA256 is already imported in DesignStateComponent and extends to ObjectState IDs with OS_ prefix. GH_Structure<IGH_Goo> with GH_Path is the existing DataTree pattern for the new Values output on CLASSIFICATOR. SwrlRuleParser is extended in-place; variable kind inference is extracted to a dedicated VariableTypeInferrer class in DG.Core.Parsing.

### Variable Type Inference — Read-Time, Not Write-Time

**Confidence: HIGH** (all three researchers agreed; grounded in SWRL W3C semantics and direct codebase read)

Variable kind (Object vs Property) is inferred at read time in Neo4jRuleRepository.PopulateVariables() from the atom structure already in Neo4j — not stored on Var nodes, not computed in n8n, not declared by the user. The inference rule is a strict priority chain: (1) variable at pos-1 of any ClassAtom in body or head is Object; (2) else at pos-2+ of any DataPropertyAtom is Property; (3) else only in BuiltinAtom args is Builtin-bound and not exposed to the GH canvas; (4) head-atom-only variables classified by head predicate IRI. Inference is extracted to a dedicated VariableTypeInferrer class so it can be unit-tested for each category independently, including the critical case where a variable appears in both ClassAtom and DataPropertyAtom (correct answer: Object wins).

### Cross-Rule Object Identity — User-Supplied ObjectRef

**Confidence: HIGH** (FEATURES.md, ARCHITECTURE.md, and STACK.md all agree; confirmed against Speckle applicationId pattern)

The ObjectRef is a user-supplied stable string (e.g. Rhino object GUID, panel-labeled string). Automatic geometry-hash-based ID generation is explicitly rejected — geometry regenerates on every GH solve, so content-hash IDs break precisely when cross-run history matters most. This mirrors Speckle's applicationId (stable, user/source-supplied) vs id (content-hash, changes with geometry) distinction. DESIGN STATE component caches (lastDefStateId, cachedIdRefs). IdRefs re-scan only when DefState.StateId changes.

### METAGRAPH as Single Neo4j Consumer

**Confidence: HIGH** (both ARCHITECTURE.md and FEATURES.md agreed; follows existing ScheduleSolution pattern)

METAGRAPH runs two concurrent async tasks (GetRulesAsync plus ValidationRunsQueryService.QueryAsync) via Task.WhenAll, then fires ScheduleSolution. All downstream components operate purely on pre-loaded data. ValidationRunsQueryService is reused as-is with ruleId: null, stateId: null for the all-runs load. Objects and Properties outputs are derived by partitioning loaded rules' variables by Kind — no second DB query.

### Phase 1 Must Fix the Var Merge Key (P4 — Latent v2.0 Bug)

**Confidence: HIGH** (PITFALLS.md grounded in direct read of cypher_template.txt showing name-only MERGE)

The existing MERGE pattern for Var nodes does not include project in the merge key. Variables with the same name across projects share a single Var node — a silent project isolation violation. v3.0 cross-rule identity is built on Var node identity. If this bug is not fixed first, the cross-rule identity mechanism inherits cross-project contamination. Fix requires: cypher_template.txt update, data migration script for existing Var nodes, n8n workflow JSON update, Neo4jRuleRepository AtomsQuery update. This is a Phase 1 prerequisite, not a v3.0 feature.

### Schema Propagation — Six Surfaces, All Mandatory

**Confidence: HIGH** (FEATURES.md SP-01..SP-06, cross-validated by PITFALLS.md P3/P9/P10)

Every schema change must propagate to all six surfaces in the same phase: (1) DG.Core.Models with new VariableKind enum, Variable.Kind, and DesignState/DefState/ObjectState C# models; (2) cypher_template.txt with new node shapes, ID prefix conventions, MERGE patterns, and schema version stamp; (3) training/dataset_schema.json with new node types and VariableKind field; (4) n8n/workflows JSON files with updated LLM system prompt ALLOWED node labels and GRAPH SCHEMA sections; (5) graph-viewer/config.template.js with NeoVis labels and visGroups for new node classes; (6) data-service/app.py with extended statePayloadJson to include idRefs list.

### EnsureOutputLayout Migration Guard — Apply to All Reworked Components

**Confidence: HIGH** (pattern already exists in RuleDeconstructComponent; PITFALLS.md P6/P7/P8 document the risks)

All components with changed output/input counts must apply the existing EnsureOutputLayout migration guard pattern. New inputs must be appended after existing indices (not inserted between them) unless an explicit Read(GH_IReader) migration shim detects and adapts the old layout. This is the difference between silent wrong results and a clear migration message.

### Unchanged Components

CONNECTOR, VALIDATOR (inputs), REINSTATE, Speckle stack, Ollama, n8n ingest logic (Cypher template documentation only), Model Viewer — all unchanged. ValidationPublishClient is a minor extension (adds idRefs to statePayloadJson).

---

## Disagreements — Presented with Tradeoffs

### Disagreement 1: Neo4j DesignState Hierarchy Strategy

This is the most consequential unresolved disagreement. It affects cypher_template.txt, config.template.js, METAGRAPH query patterns, and every piece of Cypher that reads or writes DesignState nodes.

**Option A: Multi-Label** (STACK.md recommendation)

Nodes carry two labels: :DesignState:DefState or :DesignState:ObjectState. MERGE on the subtype label; parent label added via SET.

Advantages: MATCH (d:DesignState) returns all subtypes without property filter; MERGE key is unambiguous (subtype label).

Disadvantages: LLM must learn compound label MERGE pattern not in any existing DG template; NeoVis renders by first label and label order in Neo4j 5 is non-deterministic across minor versions (PITFALLS.md P3); no existing pattern in the codebase uses multi-label nodes; higher propagation surface (three config.template.js entries vs one).

**Option B: Single Label + kind Property** (ARCHITECTURE.md recommendation)

All nodes carry label :DesignState with kind: 'DefState' | 'ObjectState' property. Mirrors the established Rule.kind pattern.

Advantages: One NeoVis config entry with deterministic rendering; single canonical MATCH pattern; mirrors Rule.kind so LLM already knows this pattern from existing Cypher templates; lower propagation surface.

Disadvantages: Cannot subtype-query with MATCH (d:DefState) — must always filter by kind property; nodes indistinguishable by label alone in Cypher.

**Recommendation: Option B (single label + kind).** Rationale: mirrors established Rule.kind pattern the LLM already knows; deterministic NeoVis rendering; lower propagation surface; lower risk of LLM Cypher template drift. The cost (no subtype-only Cypher query) is acceptable because all DesignState queries in this system filter by project and specific kind anyway.

The roadmapper must record the user's choice as a Key Decision in PROJECT.md before phase planning begins.

---

### Disagreement 2: ObjectRef ID Generation — Researcher Framing Mismatch

This was not a true disagreement on the mechanism but a framing inconsistency that could confuse requirements.

FEATURES.md clearly states the ObjectRef is user-supplied. STACK.md describes an OS_<ruleId>_<varName>_<elementRefHash> ID for the ObjectState node — which is different from the ObjectRef (the stable element identity string the user supplies). ARCHITECTURE.md proposes OS_<elementId>_<ruleId> for the node ID.

Resolution: these are two distinct IDs that must not be conflated:

- ObjectRef: user-supplied (e.g. Rhino GUID), stable element identity across rules and sessions, user-defined string.
- ObjectState.State_Id: generated by the DG plugin via SHA256 truncation, serves as the Neo4j node unique identifier, format OS_<hash8> consistent with DS_<hash16> for DefState.

The ObjectState.State_Id is computed from SHA256(ruleId + varName + objectRef) so it is deterministic given stable inputs. There is no geometry-hash in either ID. Requirements should define both IDs explicitly to prevent confusion during implementation.

---

### Disagreement 3: DesignState Parent — Concrete Node or Virtual Class

STACK.md's pattern implies a concrete DesignState parent node exists in Neo4j with DGST_ prefix aggregating DefState and ObjectState sub-nodes. ARCHITECTURE.md states the parent class has no concrete instances — there are only DefState and ObjectState instances.

Resolution (aligned with Option B in Disagreement 1): With single-label plus kind property, the parent concept is implicit in the label DesignState. All nodes are DesignState nodes via the shared label, distinguished by kind. No separate parent node is needed. The DGST_ prefix from FEATURES.md is therefore unused — only DS_ (DefState) and OS_ (ObjectState) prefixes exist.

If Option A (multi-label) is chosen instead, a concrete parent DesignState node with DGST_ prefix makes sense as the aggregation root. The roadmapper should capture this implication based on the user's Q1 answer.

---

## Roadmap Implications

### Suggested Phase Structure (6 phases)

The phase ordering is driven by three hard dependency chains: (1) Variable.Kind must exist before any component can produce or consume typed outputs; (2) the Var merge key bug (P4) must be fixed before cross-rule identity is built; (3) schema propagation must be complete before end-to-end validation can be tested.

---

**Phase 1 — Schema Foundation and Bug Fix**

Rationale: Everything else depends on Variable.Kind being available and the Var merge key being safe. No downstream component can be built until these data contracts are locked. This phase has no upstream dependencies.

Delivers: VariableKind enum and Variable.Kind property in DG.Core.Models; VariableTypeInferrer class with unit tests for all 4 atom categories; PopulateVariables() extended with kind inference; DesignState/DefState/ObjectState C# models and ID prefix constants; Var node merge key fix (name plus project) with data migration script; schema propagation across all six surfaces for new node classes and VariableKind; NeoVis config.template.js entries for new node labels; cypher_template.txt schema version stamp.

Must avoid: P1 (type inference false positives), P4 (cross-project Var collision), P3 (NeoVis label proliferation), P9 (n8n prompt desync).

Research flag: Standard patterns — no further research needed.

---

**Phase 2 — METAGRAPH Expansion and RULE DECONSTRUCT Rework**

Rationale: METAGRAPH must expose Runs before RUN DECONSTRUCT can consume them. RULE DECONSTRUCT must expose Objects/Properties before CLASSIFICATOR rework is meaningful. Both depend only on Phase 1. Independent of Phase 3.

Delivers: METAGRAPH concurrent Task.WhenAll(GetRulesAsync, QueryRunsAsync) with new outputs Objects, Properties, DesignStates, Runs; RULE DECONSTRUCT Objects, Properties, Runs outputs with Variables deprecated (not removed) at last index; VARIABLE NAME new trivial component; EnsureOutputLayout applied with deprecated Variables output preserved.

Must avoid: P6 (VALIDATION RUNS rename canvas break), P8 (RULE DECONSTRUCT Variables removal). Parallel with: Phase 3. Research flag: Standard patterns.

---

**Phase 3 — OBJECT STATE Component and DESIGN STATE Rework**

Rationale: Produces the IdRefs/GeoRefs contract that CLASSIFICATOR needs. Depends only on Phase 1 (C# models). Independent of Phase 2.

Delivers: ObjectStateComponent (new) with ObjectRef plus GeoRef inputs emitting DG.ObjectState; DesignStateComponent rework with inputs changing to ObjectState[] plus DefState and outputs becoming IdRefs, GeoRefs, DefState with cache logic; DG.ObjectState public GH-wirable type; unit tests for cache invalidation.

Must avoid: P5 (stale IdRefs when DefState changes). Parallel with: Phase 2. Research flag: Standard patterns.

---

**Phase 4 — CLASSIFICATOR Rework**

Rationale: Depends on Phase 1 (Variable.Kind), Phase 2 (typed Objects/Properties from RULE DECONSTRUCT), and Phase 3 (IdRefs/GeoRefs from DESIGN STATE). All three must be done before CLASSIFICATOR can be fully reworked.

Delivers: CLASSIFICATOR new inputs Rule, Objects, Properties, PropValues, IdRefs, GeoRefs, DefState; rename ElementRefs to GeoRefs and State to DefState output; new outputs Values (DataTree) and Variables (full bound list); binding logic updated to use Objects-to-IdRefs mapping; EnsureOutputLayout with Read() migration detection for v2.0 canvas files; component message showing N objects bound, M properties bound.

Must avoid: P7 (CLASSIFICATOR input index shift).

Research flag: Needs /gsd-research-phase before PLAN — read VariableBinder.BuildBindings before drafting this phase.

---

**Phase 5 — RUN DECONSTRUCT and statePayloadJson Extension**

Rationale: Depends on Phase 2 (Runs from METAGRAPH) and Phase 3/4 (extended DesignState shape for statePayloadJson). Partial implementation possible after Phase 2.

Delivers: ValidationRunsComponent to RunDeconstructComponent migration (strategy per Q3 decision) with outputs passing items, failing items, RunId, DateCreated, State; DesignStateSnapshot.cs gains IdRefs list; data-service/app.py extends statePayloadJson deserialization; ValidationPublishClient serializes IdRefs into statePayloadJson.

Must avoid: P6 (VALIDATION RUNS rename canvas breakage).

Research flag: Needs /gsd-research-phase before PLAN — read ValidationRunPersistenceService.cs and app.py serialization path; also requires Q3 decision from user.

---

**Phase 6 — End-to-End Validation and Schema Propagation Verification**

Rationale: Document-level propagation can be drafted in parallel with Phases 3-5 but must be verified end-to-end after all code phases complete.

Delivers: Live ingest test confirming LLM generates Cypher with new node labels; training dataset audit with dataset_schema.json examples passing validation script; schema version stamp verified between cypher_template.txt and n8n workflow Function node; REINSTATE component smoke test with new statePayloadJson shape; E2E canvas test confirming OBJECT STATE to DESIGN STATE to CLASSIFICATOR to VALIDATOR to run persistence to RUN DECONSTRUCT reads correctly.

Must avoid: P9 (n8n prompt desync), P10 (dataset obsolescence).

Research flag: Needs live system test — cannot be verified without a running Docker environment.

---

### Phase Ordering Rationale

Phase 1 is a universal prerequisite — Variable.Kind and the Var merge key fix are both blocking for all downstream work. Phases 2 and 3 are parallel — METAGRAPH/RULE DECONSTRUCT expansion does not share state with OBJECT STATE/DESIGN STATE rework. Phase 4 (CLASSIFICATOR) is the synchronization point — it depends on both Phase 2 output types and Phase 3 geometry contracts. Phase 5 (RUN DECONSTRUCT) is partially parallel with Phase 4 but must wait for statePayloadJson shape to be final. Phase 6 is the verification gate — no phase is done until the end-to-end data flow is confirmed live.

The v2.0 retrospective (see .planning/REQUIREMENTS.md Phase 3.1 gap closure) shows that plan-level completeness does not imply implementation completeness. Every phase should include an explicit broken-chain check: wire METAGRAPH to RULE DECONSTRUCT to CLASSIFICATOR to VALIDATOR to RUN DECONSTRUCT and confirm data flows end-to-end, not just that each component compiles.

---

### Research Flags

Phases needing deeper research during planning:
- Phase 4 (CLASSIFICATOR rework): The binding logic change is the most complex algorithmic change in v3.0. Read VariableBinder.BuildBindings in detail before the PLAN is written.
- Phase 5 (statePayloadJson extension): The data-service/app.py _project_state_summary() function and ValidationRunPersistenceService.cs serialize path should be read before the PLAN is written — the v2.0 gap closure showed this was the source of a silent data loss bug.

Phases with standard patterns (skip research-phase):
- Phase 1: VariableTypeInferrer — straightforward enum plus inference logic with clear test cases.
- Phase 2: METAGRAPH expansion — Task.WhenAll plus ScheduleSolution pattern is established.
- Phase 3: OBJECT STATE and DESIGN STATE — new fixed-input component plus cache pattern.
- Phase 6: Schema propagation verification — checklist-driven, no new code.

---

## Pitfall Index — Top 5 Risks

| # | Pitfall | Target Phase | Prevention |
|---|---------|-------------|------------|
| P4 | Cross-project Var node collision (latent v2.0 bug) | Phase 1 prerequisite | MERGE Var on (name, project); migration script; verify MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v) = 0 |
| P1 | Variable type inference false positives (variable in both ClassAtom and DataPropertyAtom) | Phase 1 | VariableTypeInferrer with priority chain; unit tests for every category including multi-atom-type case |
| P7 | CLASSIFICATOR input index shift silently misroutes v2.0 canvas wires | Phase 4 | Append-only new inputs OR Read() migration detection with explicit error message; verify by loading v2.0 canvas |
| P6 | VALIDATION RUNS to RUN DECONSTRUCT rename breaks existing canvases | Phase 5 | Decide migration strategy (Q3) before writing the component; document re-wire steps in release notes |
| P9 | n8n prompt desync after schema change — LLM generates Cypher with old node labels | Phase 1 and every schema-touching phase | Schema version stamp in both cypher_template.txt and n8n workflow JSON; live ingest test after every schema change |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; all recommendations grounded in direct NuGet/pip registry checks and codebase read |
| Features | HIGH | Grounded in SWRL W3C semantics, Speckle docs, and direct v2.0 component code read |
| Architecture | HIGH | All integration points traced to specific files and methods in the codebase |
| Pitfalls | HIGH | P4 confirmed via direct read of cypher_template.txt; P7 confirmed via direct read of ClassificatorComponent input indices; all pitfalls grounded in concrete code evidence |

**Overall confidence: HIGH**

### Gaps to Address During Planning

- VariableBinder.BuildBindings rework scope: exact change to binding construction needs a detailed code read before Phase 4 PLAN is written. Flag for /gsd-research-phase before Phase 4.
- statePayloadJson extension risk: Phase 5 touches the same code path that caused the v2.0 gap-closure bug. Read ValidationRunPersistenceService.cs and app.py serialization path before Phase 5 PLAN. Flag for /gsd-research-phase before Phase 5.
- Migration strategy decision (Q3): VALIDATION RUNS component migration path must be decided by the user before Phase 5 PLAN is written.
- DesignState hierarchy strategy (Q1): must be resolved before Phase 1 PLAN is written. The Key Decision must be recorded in PROJECT.md.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: DG.Core/Models/Variable.cs, DG.Core/Data/Neo4jRuleRepository.cs, DG.Core/Parsing/SwrlRuleParser.cs, DG.Core/Services/ValidationRunsQueryService.cs, all 7 GH component files, data-service/app.py, cypher_template.txt, training/dataset_schema.json, graph-viewer/config.template.js
- SWRL W3C Submission (https://www.w3.org/submissions/SWRL/) — i-variable/d-variable distinction, rule-local scoping
- SWRL Language FAQ protegeproject/swrlapi (https://github.com/protegeproject/swrlapi/wiki/SWRLLanguageFAQ) — ClassAtom/DataPropertyAtom argument semantics
- NuGet Gallery Neo4j.Driver (https://www.nuget.org/packages/Neo4j.Driver) — 5.28.4 latest 5.x; 6.0.0 breaking changes confirmed
- Neo4j .NET Driver Upgrade Guide (https://neo4j.com/docs/dotnet-manual/current/upgrade/) — 6.0.0 requires .NET 8 minimum
- Rhino Developer Docs IGH_DataAccess.GetDataTree — GH_Structure vs DataTree SDK guidance
- Speckle Core Concepts applicationId pattern (https://docs.speckle.systems/developers/data-schema/concepts) — stable vs content-hash identity

### Secondary (MEDIUM confidence)

- Neo4j Developer Blog Graph Modeling Labels — multi-label hierarchy guidance, 4-label performance threshold
- Neo4j Community Create multiple labels — community validation of multi-label subtype pattern
- Grasshopper/McNeel community forums — GUID persistence/loss behavior on regeneration

### Primary Internal (HIGH confidence)

- .planning/REQUIREMENTS.md — v2.0 Phase 3.1 gap closure retrospective (broken chain pattern)
- DG_OBSIDIAN/atlas/Graph schema v3 is the canonical data model.md — schema propagation checklist
- DG_OBSIDIAN/knowledge/decisions/SWRL parsing is bespoke regex not vendor OWL library.md — parser limitation scope

---

*Research completed: 2026-05-11*
*Ready for roadmap: yes — pending resolution of Q1 and Q3 by user*