# Phase 7: Schema Foundation - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase locks the data contracts every later v3.0 phase depends on. It delivers: the `VariableKind` enum and read-time inference logic (`VariableTypeInferrer`), the `DesignState`/`DefState`/`ObjectState` C# model hierarchy with `DS_`/`OS_` ID prefixes, the `Var` node merge-key fix (adding `project` to the MERGE key) plus a one-time data migration, and schema propagation across all 6 surfaces (C# models, `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompts, `config.template.js`, `data-service/app.py`). No Grasshopper component behavior changes ship in this phase — METAGRAPH, RULE DECONSTRUCT, CLASSIFICATOR, DESIGN STATE, and RUN DECONSTRUCT rework all happen in later phases and consume what this phase locks down.

</domain>

<decisions>
## Implementation Decisions

### DesignState Neo4j Hierarchy
*Locked in PROJECT.md Key Decisions; research SUMMARY.md Disagreement 1*
- Single `:DesignState` label with a `kind` property (`'DefState' | 'ObjectState'`) — NOT multi-label nodes
- Mirrors the existing `Rule.kind` pattern the LLM prompts already use; deterministic NeoVis rendering; lower propagation surface
- No concrete parent `DesignState` node — the shared label is the parent concept (Disagreement 3 resolution); the `DGST_` prefix from early drafts is unused
- Only two ID prefixes exist for this hierarchy: `DS_` (DefState) and `OS_` (ObjectState)

### ID Formats
*Locked in REQUIREMENTS.md CMPST-06/07; research Disagreement 2*
- `DefState.StateId`: existing SHA256-based `DS_<hash>` format (unchanged from v2.0)
- `ObjectState.StateId`: `OS_<SHA256(projectId + objectInstanceId + variableName)>` — cross-rule, no `ruleId` in the hash, because Object variables are cross-rule (VTYP-02)
- `ObjectInstance` (new class, `OI_` prefix) is the cross-rule identity anchor; `ObjectState` is its 1:1 current-binding snapshot
- `ObjectRef` (the user-supplied Rhino/Speckle GUID string) is distinct from both — it lives on the `dgv:objectRef` datatype property, never used directly as a node ID

### Var Merge Key Fix
*Locked — REQUIREMENTS.md SCHM-02; research PITFALLS.md P4*
- Fix: change `MERGE (v:Var {name: ...})` to `MERGE (v:Var {name: ..., project: ...})` in `cypher_template.txt` and `Neo4jRuleRepository`
- Migration: re-ingesting active rules re-creates `Var` nodes correctly under the fixed template; any remaining untagged nodes get swept (`coalesce(v.project, 'default-project')`) so the verification query (`MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v)` = 0) passes cleanly
- This is a Phase 7 prerequisite fix, not a deferred feature — confirmed in research Q5 (latent v2.0 bug, fixed before cross-rule identity is built on top of `Var`)

### Variable Type Inference
*Locked — research Resolved Findings; REQUIREMENTS.md VTYP-01*
- Read-time inference via a new `VariableTypeInferrer` class in `DG.Core.Parsing`, consumed from `Neo4jRuleRepository.PopulateVariables()` — NOT stored on `Var` nodes, NOT inferred in n8n
- Priority-chain rule: (1) pos-1 of any ClassAtom → Object; (2) else pos-2+ of any DataPropertyAtom → Property; (3) else Builtin-only → not exposed to canvas; (4) head-only variables classified by head predicate IRI
- Object wins when a variable appears in both a ClassAtom and a DataPropertyAtom (this is Phase 7's explicit success criterion #1)

### Enum Discriminator Modeling
*Locked — REQUIREMENTS.md SCHM-06*
- `variableKind`, `variableScope`, `kind` (DesignState), `status`, `parameterType` are modeled as OWL ObjectProperties pointing at NamedIndividuals in dedicated enum classes (`VariableKindValue`, `VariableScopeValue`, `DesignStateKindValue`, `ValidationStatusValue`, `DesignStateParameterTypeValue`)
- Mirrors the existing `DesignStateParameterTypeValue` pattern already in the ontology

### Claude's Discretion
- Exact NeoVis colors/styling for DefState vs ObjectState nodes within the single `:DesignState` config entry — any visually distinct pair is acceptable, no convention to match
- Whether the orphaned-Var-node migration sweep runs as a standalone Cypher script, a data-service endpoint, or a one-off `cypher-shell` command — no migration-script precedent exists yet in the repo, this is the first one
- Exact placement and signature of `VariableTypeInferrer` (static class, mirroring the `VariableBinder`/`SwrlRuleParser` static-utility convention already in `DG.Core`)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DesignStateSnapshot.cs`, `DesignStateParameter.cs` (`DG.Core.Models`) — existing v2.0 design-state models; `DefState` supersedes/extends this shape
- `SwrlRuleParser.cs`, `VariableBinder.cs` — static utility class pattern to follow for `VariableTypeInferrer`
- `System.Security.Cryptography.SHA256` already used in `DesignStateComponent` for `DS_` ID generation — extends directly to `OS_` IDs
- `Neo4jRuleRepository.cs` — `PopulateVariables()` is the existing read path where type inference plugs in

### Established Patterns
- Static utility classes with no instance state (`VariableBinder`, `SwrlRuleParser`)
- `init`-accessor immutable model properties; `Collection<T>` for list properties
- `Rule.kind`-style single-label-plus-property pattern already used elsewhere in the graph schema
- Schema changes always propagate across all 6 surfaces in the same change (established convention per CLAUDE.md and CONVENTIONS.md)

### Integration Points
- `cypher_template.txt` — Var MERGE pattern, new DS_/OS_ node shapes, schema version stamp
- `training/dataset_schema.json` — new node types + VariableKind field
- `n8n/workflows/*.json` — LLM system prompt ALLOWED node labels + GRAPH SCHEMA sections
- `graph-viewer/config.template.js` — NeoVis labels/visGroups for DesignState kind-based coloring
- `data-service/app.py` — statePayloadJson extension point (full extension lands in Phase 11, but the node/prefix vocabulary must agree starting here)

</code_context>

<specifics>
## Specific Ideas

No specific UI/UX requirements — this is a backend schema/data-contract phase. All specifics are captured as locked decisions above, sourced from PROJECT.md Key Decisions, REQUIREMENTS.md (SCHM-01..06, VTYP-01..03), and `.planning/research/SUMMARY.md` (Open Questions Q1-Q5, all resolved during roadmap creation on 2026-05-11/14).

</specifics>

<deferred>
## Deferred Ideas

- Component behavior changes (METAGRAPH, RULE DECONSTRUCT, DESIGN STATE, CLASSIFICATOR, RUN DECONSTRUCT) are explicitly out of scope for Phase 7 and tracked in Phases 8-11 per ROADMAP.md.
- **Vendor-neutral rename propagation** (`speckleProjectId` → `externalProjectId`): the DG_OBSIDIAN v6.1 ontology session (2026-06-01) renamed this property in the ontology files but left runtime propagation (the same 6 surfaces this phase touches: `cypher_template.txt`, `dataset_schema.json`, n8n prompts, `config.template.js`, `data-service/app.py`/`speckle_validation.py`) as a "separate follow-up pending confirmation." User explicitly decided (2026-06-23) to keep this OUT of v3.0 — Phase 7 stays scoped strictly to REQUIREMENTS.md VTYP/SCHM items. Do not bundle this rename into Phase 7's schema propagation work.

</deferred>
