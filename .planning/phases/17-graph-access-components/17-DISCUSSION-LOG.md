# Phase 17: Graph Access Components - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 17-graph-access-components
**Areas discussed:** Layer handle model, METAGRAPH Objects extraction, VALIDATION GRAPH output semantics, Repository layer design

---

## Layer Handle Model

| Option | Description | Selected |
|--------|-------------|----------|
| Individual types per layer | MetagraphHandle, OntographHandle, ValidGraphHandle, SpecGraphHandle — each wraps ConnectionInfo. Type-safe Grasshopper wires prevent miswiring. | ✓ |
| Single GraphLayerHandle + enum | One model class with GraphLayer enum discriminator. Less boilerplate but downstream components validate at runtime. | |
| Just pass ConnectionInfo through | Add GraphLayer string property to ConnectionInfo. Simplest but zero wire type safety. | |

**User's choice:** Individual types per layer (Recommended)
**Notes:** GRAPH DECONSTRUCT is the sole producer of handles; each layer-reader component accepts only its specific handle type. Grasshopper wires are type-safe.

---

## METAGRAPH Objects Extraction

| Option | Description | Selected |
|--------|-------------|----------|
| Query REFERS_TO→Class from Neo4j | New Cypher query: MATCH (r:Rule)-[:HAS_BODY\|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class). Deduplicate by Class IRI. Parallel-loadable with Rules. | ✓ |
| Infer from VariableTypeInferrer | After loading rules, run VariableTypeInferrer on each rule's variables, filter for VariableKind.Object. Reuses existing inference but ties to naming conventions. | |

**User's choice:** Query REFERS_TO→Class from Neo4j (Recommended)
**Notes:** Clean graph-structural approach. Objects = the set of Class nodes rules actually reference. No dependency on VariableTypeInferrer naming conventions.

---

## VALIDATION GRAPH Output Semantics

### Output Alignment

| Option | Description | Selected |
|--------|-------------|----------|
| Index-matched parallel lists | Run[i], Status[i], DesignState[i] all describe the same validation run. Follows METAGRAPH Rules/Objects pattern. | ✓ |
| Independent bags | Each output independent with no positional correspondence. Consumers cross-reference by ID. | |

**User's choice:** Index-matched parallel lists (Recommended)

### DesignState Deduplication

| Option | Description | Selected |
|--------|-------------|----------|
| Repeat per run | DesignState list has same length as Run list. Duplicates when runs share a DesignState. | |
| Deduplicate — only unique DesignStates | DesignState list contains only unique DesignStates by StateId, possibly shorter than Run list. | ✓ |

**User's choice:** Deduplicate — only unique DesignStates (Recommended)
**Notes:** Resolved tension with index-matching: Run↔Status are paired 1:1. DesignState is a separate deduplicated list, not forced to match Run length. Consumers join by StateId.

### Status Type

| Option | Description | Selected |
|--------|-------------|----------|
| IReadOnlyList\<bool\> per run | One bool per ObjState in the run's DesignState, index-matched to ObjState order. Overall pass = AND(all bools), derived at read time. | ✓ |
| Simple bool — overall pass only | Status[i] = single bool = AND(ValidStatus). Simpler but loses per-object granularity. | |
| Wrapper object | RunStatus { OverallPass, PerObject }. Most informative but requires new model type. | |

**User's choice:** IReadOnlyList\<bool\> per run (Recommended)
**Notes:** Matches Phase 14 D-01 contract. No wrapper type — the Boolean list IS the status.

---

## Repository Layer Design

| Option | Description | Selected |
|--------|-------------|----------|
| Per-layer repository + interface | IOntoGraphRepository + Neo4jOntoGraphRepository, IValidGraphRepository + Neo4jValidGraphRepository. Extend IRuleRepository with GetObjectsAsync. | ✓ |
| OntoGraph repository + extend existing ValidGraph service | IOntoGraphRepository for OntoGraph. Extend concrete ValidationRunsQueryService for ValidGraph — no new interface. | |
| Single unified IGraphQueryService | One interface with methods for all 3 layers. Single injectable service but mixes concerns across graph layers. | |

**User's choice:** Per-layer repository + interface (Recommended)
**Notes:** Each interface enables unit testing with mock repositories. Follows existing IRuleRepository pattern.

---

## Claude's Discretion

- CONNECTOR update details: exact nickname renames, whether Project is split into input+output
- GRAPH DECONSTRUCT implementation (pure passthrough, no DB calls)
- Exact model property names for handle types
- Whether ValidationRunsQueryService is adapted in-place or replaced by Neo4jValidGraphRepository
- DesignState output — handle both v1 (ParamState-only) and v2 (3-part) payloads gracefully
- Component icons for new components (GRAPH DECONSTRUCT, ONTOGRAPH, VALIDATION GRAPH)
- Error message wording per ErrorMessageTemplates pattern
- Whether GhCastingHelpers gets per-handle Try* methods or generic Unwrap\<T\> is sufficient
- Exact ordering of Run/Status/DesignState outputs

## Deferred Ideas

None — discussion stayed within phase scope.
