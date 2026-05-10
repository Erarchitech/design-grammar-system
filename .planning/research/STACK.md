# Technology Stack

**Project:** Design Grammar System — v3.0 Typed Variables and Composable Design State
**Researched:** 2026-05-11
**Scope:** ONLY additions and pattern changes needed for v3.0. The existing validated stack (Neo4j 5, Neo4j.Driver 5.28.2, Ollama/llama3.1, n8n, FastAPI, React 18 CDN, Vite Model Viewer, Docker Compose) is not re-researched.

---

## Executive Finding

**No new NuGet packages, no new pip packages, no new Docker services are required for v3.0.**

All v3.0 features can be implemented entirely within the existing stack using:
- In-box .NET 7/9 APIs (`System.Security.Cryptography.SHA256`, `System.Collections.Generic`)
- Grasshopper SDK APIs already consumed in v2.0 (`GH_Structure<T>`, `GH_Path`, `IGH_VariableParameterComponent`)
- Neo4j 5 multi-label MERGE (already used for `Class`, `DatatypeProperty`, etc.)
- The existing `SwrlRuleParser` + `Atom.Type` field (extended in-place)

---

## Recommended Stack

### Core Framework — No Changes

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| DG.Core | net7.0 / net9.0 | Pure logic: models, parsing, validation | Unchanged |
| DG.Grasshopper | net7.0-windows | GH plugin with `#if GRASSHOPPER_SDK` guards | Unchanged |
| Neo4j.Driver | 5.28.2 (current) | Bolt driver for graph reads/writes | Keep at 5.28.2 — see note |
| data-service FastAPI | pinned in requirements.txt | Validation publish, run persistence | Unchanged |

**Neo4j.Driver version note:** 6.0.0 shipped 2026-01-07 and is a major version with breaking changes. It drops .NET Standard 2.1, requires .NET 8/9/10, renames transaction APIs (`ReadTransaction` → `ExecuteRead`), and removes `IDriver.CloseAsync()`. DG.Grasshopper targets `net7.0-windows`. Upgrading would require retargeting to net8.0-windows and rewriting session management code. This is not needed for any v3.0 feature. Keep 5.28.2. The latest 5.x patch is 5.28.4 (2025-12-05) — a minor bump with no breaking changes; bump is low-priority optional hygiene. **Verdict: stay on 5.28.2, do NOT upgrade to 6.0.0 in this milestone.**

### Pattern A: Neo4j Multi-Label for DesignState Hierarchy

**Decision: use multi-label nodes (`DesignState` + subtype label) with MERGE on a single key.**

The v3.0 schema introduces a `DesignState` parent class with two subclasses: `DefState` (parametric capture, exists in v2.0) and `ObjectState` (new: ObjectRef + GeoRef). The question is whether to model this as:

1. Multi-label: one node with labels `[:DesignState:DefState]` or `[:DesignState:ObjectState]`
2. Nesting: a `DesignState` parent node connected to a child `DefState`/`ObjectState` node by a relationship

**Recommendation: multi-label, single node.**

Rationale:
- The existing validation graph already uses `ValidationRun` nodes as single nodes, not parent+child. Multi-label follows the same pattern.
- Querying `MATCH (ds:DesignState)` catches all subtypes without traversal. This is exactly the access pattern needed by METAGRAPH's `DesignStates` output.
- The Neo4j official modeling guide cautions against hierarchical label sets beyond 4 labels per node. For this schema, nodes carry exactly 2 labels (`DesignState` + one subtype) — well within the performance-safe zone.
- `MERGE (ds:DefState {State_Id: $id})` uniquely matches the subtype. Adding the parent label is a `SET` operation on first create: `SET ds:DesignState`. This keeps the MERGE key clean.
- Separate nesting would require a new relationship type and a two-node lookup for every state read — unnecessary complexity given that the `DefState` and `ObjectState` data structures are small.

**Cypher MERGE pattern for multi-label hierarchy:**

```cypher
// DefState (existing concept, new node label + parent label)
MERGE (ds:DefState {State_Id: $stateId, project: $project})
SET ds:DesignState,                    // add parent label
    ds.graph       = 'ValidationGraph',
    ds.capturedAt  = $capturedAt,
    ds.parameters  = $parametersJson

// ObjectState (new)
MERGE (os:ObjectState {State_Id: $objectStateId, project: $project})
SET os:DesignState,
    os.graph       = 'ValidationGraph',
    os.objectRef   = $objectRef,
    os.geoRef      = $geoRef
```

**MERGE key discipline:** MERGE on the most specific label (`DefState`, `ObjectState`) with `State_Id` + `project`. The parent label `DesignState` is applied by SET, not part of the MERGE key. This prevents false matches across subtypes if IDs were ever to collide.

**Query pattern for METAGRAPH `DesignStates` output:**

```cypher
MATCH (ds:DesignState {project: $project, graph: 'ValidationGraph'})
RETURN ds.State_Id, labels(ds) AS subtypes, ds
```

`labels(ds)` returns `["DesignState", "DefState"]` or `["DesignState", "ObjectState"]` — the component can inspect the list to distinguish subtypes without a separate query.

### Pattern B: Unique ID Prefixes for New Node Classes

**Decision: extend the existing `R_…_V` and `KN_…` prefix convention with two new prefixes.**

Existing prefixes:
- `R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` — Rule nodes
- `{Rule_Id}_A{n}` / `{Rule_Id}_H{n}` — Atom nodes
- `KN_<PROJECT>_<SLUG>` — KnowledgeNote nodes (v1.1)

New prefixes for v3.0:

| Node Class | ID Prefix Format | Example |
|------------|-----------------|---------|
| `DefState` | `DS_<16-hex-hash>` | `DS_A3F7C2B1D4E89012` |
| `ObjectState` | `OS_<ruleId>_<varName>_<elementRefHash>` | `OS_R_URB_HEIGHT_MAX_75_V_x_A3F2` |
| `DesignState` | (parent — no direct ID, matched via subtype) | — |

**`DefState` ID generation (existing `ComputeStateId` pattern, keep as-is):**
The existing `DesignStateComponent` already computes `StateId` as `SHA256(sorted parameterId=value pairs)[..16]`. Rename the output prefix from bare hex to `DS_<hex>` for namespace clarity. This is a naming-only change — the hash algorithm does not change.

**`ObjectState` ID generation:**
An `ObjectState` represents a specific object variable binding across rules. Its identity comes from: the rule it belongs to, the variable name (Object variable), and the element reference (e.g. the Rhino/BIM element ID). Use:

```csharp
// In DG.Core, no new library needed
var raw = $"OS|{ruleId}|{variableName}|{elementDgEntityId}";
var hash = SHA256.HashData(Encoding.UTF8.GetBytes(raw));
var objectStateId = $"OS_{Convert.ToHexString(hash)[..8]}";
```

This is the same pattern as `ComputeStateId` in `DesignStateComponent` — `System.Security.Cryptography.SHA256` is already imported in `DG.Grasshopper`. No new library is needed.

**Cross-rule Element Id persistence:**
The v3.0 requirement is that Object variable identity persists across rules (same Element Id if the same physical element is referenced). The recommended approach:
- Element Ids stored on the `DesignState` node as a JSON-serialized list property `elementIds`
- The C# `ElementRef.DgEntityId` field (already in `DG.Core.Models.ElementRef`) is the stable identity anchor
- Regenerate `ObjectState` `State_Id` only when `DefState` changes (i.e., when the hash of the parametric capture changes), not on every solve
- **Do NOT use external UUID libraries.** The existing SHA256 truncation pattern from `DesignStateComponent` is sufficient and already tested. UUID v5 (name-based, SHA-1) is a valid alternative but adds no benefit over the current pattern for this use case.

### Pattern C: Grasshopper DataTree for Index-Matched Outputs

**Decision: use `GH_Structure<IGH_Goo>` with explicit path construction — same pattern as ClassificatorComponent's existing `Values` input tree.**

The v3.0 CLASSIFICATOR rework adds a `Values` output DataTree where each branch `{branch_index}` corresponds to a variable by position index. This mirrors the existing `Values` input already consumed in `SolveInstance`.

**Writing a branch-per-variable DataTree output:**

```csharp
// In ClassificatorComponent.SolveInstance — existing tree read pattern:
da.GetDataTree(1, out GH_Structure<IGH_Goo> valueTree);
// branch index == variable index (existing constraint, preserved in v3.0)

// Writing a Values output DataTree (new in v3.0):
var outputTree = new GH_Structure<IGH_Goo>();
for (var varIdx = 0; varIdx < variables.Count; varIdx++)
{
    var path = new GH_Path(varIdx);           // {varIdx}
    var variable = variables[varIdx];
    foreach (var row in boundRows)            // one item per binding row
    {
        var value = row.ValuesByVar.GetValueOrDefault(variable.Name);
        outputTree.Append(GH_Convert.ToGoo(value), path);
    }
}
da.SetDataTree(outputIdx, outputTree);
```

**Key rule — index invariant:** The branch index in `Values` output must match the index of the corresponding variable in the `Variables` output list. This is the same constraint already enforced on the `Values` input. No DataTree API changes are needed; `GH_Structure<IGH_Goo>` and `GH_Path` are already imported in `ClassificatorComponent.cs`.

**`da.SetDataTree` vs `da.SetData`:** Use `da.SetDataTree(paramIndex, tree)` for DataTree outputs (access mode must be `GH_ParamAccess.tree` in `RegisterOutputParams`). This is the standard GH pattern; no new API knowledge required.

**`Variables` output (parallel list):** The v3.0 CLASSIFICATOR `Variables` output is a flat `GH_ParamAccess.list` of `DG.Variable` objects — one per variable, in the same order as the `Values` tree branches. This list already exists implicitly (the `variables` collection used to index the tree); it just needs to be wired to an output parameter.

### Pattern D: Variable Type Inference in SwrlRuleParser

**Decision: extend `SwrlRuleParser` + `Variable` model in-place — no new parsing library.**

The existing `ResolveAtomType` method in `SwrlRuleParser.cs` already classifies atoms as `ClassAtom`, `DataPropertyAtom`, `ObjectPropertyAtom`, or `BuiltinAtom`. Variable type inference maps from atom classification to variable kind:

| Atom Type | Arg Position | Inferred Variable Kind |
|-----------|-------------|----------------------|
| `ClassAtom` | 1 | `Object` |
| `DataPropertyAtom` | 1 | `Object` |
| `DataPropertyAtom` | 2 | `Property` |
| `ObjectPropertyAtom` | 1 or 2 | `Object` |
| `BuiltinAtom` | any | `Property` (operand) |

**Implementation approach:**
1. Add `VariableKind` enum to `DG.Core.Models` with values `Object` and `Property`.
2. Add `VariableKind? Kind` property to `Variable` model (nullable — unknown until inferred).
3. In `PopulateVariables` (inside `Neo4jRuleRepository`) and in `SwrlRuleParser.Parse`, after collecting all variable names, walk body atoms and set `Kind` based on the table above.
4. Cross-rule Object identity: a `Var` node shared across rules has the same `?name`. The inference rule is: if ANY atom across all rules classifies `?x` as `ClassAtom` arg-1, `?x` is `Object`.

No changes to Cypher or Neo4j schema are needed for the inference itself — it is a client-side C# computation over already-loaded atom data.

### Pattern E: Reworked DesignState Component — IGH_VariableParameterComponent

**Decision: keep `IGH_VariableParameterComponent` pattern from v2.0, extend outputs only.**

The existing `DesignStateComponent` uses `IGH_VariableParameterComponent` for variable-count inputs. The v3.0 rework adds outputs `IdRefs`, `GeoRefs`, `DefState`. These are fixed outputs (not variable), so `RegisterOutputParams` is extended normally — no new GH API needed.

The `OBJECT STATE` (new component) takes fixed inputs `ObjectRef` (text/id) and `GeoRef` (geometry) and produces a single `ObjectState` output. It follows the same component structure as existing fixed-input components (e.g., `ConnectorComponent`). No `IGH_VariableParameterComponent` needed for `OBJECT STATE`.

The `VARIABLE NAME` component takes a single `Variable` input and produces a text `Name` output. It is a pure pass-through deconstruct with no async behavior — the simplest possible GH component pattern.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Neo4j hierarchy | Multi-label (`DesignState` + subtype) | Parent node + child node with relationship | Adds traversal to every state read; breaks existing single-node pattern; no query benefit at this scale |
| Neo4j hierarchy | Multi-label | Separate label only (no parent) | Cannot query `MATCH (ds:DesignState)` across subtypes without `OR` logic; violates the METAGRAPH `DesignStates` output requirement |
| Driver version | Stay on 5.28.2 | Upgrade to 6.0.0 | 6.0.0 requires .NET 8+, drops .NET 7 support; breaks `net7.0-windows` target; renames transaction APIs; no v3.0 feature needs it |
| Element ID generation | SHA256 truncation (existing pattern) | UUID v5 library (e.g., UUIDNext) | New NuGet dependency for identical outcome; SHA256 already imported; same uniqueness guarantee |
| Variable inference | In-place `SwrlRuleParser` extension | Dedicated inference service | Cross-cutting pure logic; belongs in `DG.Core`; no HTTP boundary needed |
| DataTree mirroring | `GH_Structure<IGH_Goo>` with explicit `GH_Path` | `DataTree<T>` | GH SDK best practice is `GH_Structure` for SDK components; `DataTree` is for script components only |

---

## What NOT to Add

| Avoid | Why |
|-------|-----|
| Neo4j.Driver 6.0.0 | Breaking changes, requires .NET 8 minimum — not worth the migration cost for v3.0 |
| OWL/SWRL vendor libraries (e.g., OWLSharp, dotNetRDF) | Bespoke regex parser is a validated architectural decision; OWL libs add significant dependency weight and parse a superset DG does not need |
| Deterministic UUID NuGet packages (UUIDNext, DeterministicGuids) | SHA256 truncation with prefix is already established in `DesignStateComponent`; consistent and test-covered without new packages |
| Additional Neo4j indexes for v3.0 node types | Volume of `DefState`/`ObjectState` nodes is small at current scale; add range index on `capturedAt` only when query latency is observed |
| `System.Text.Json` source generators or custom serializers | Existing `DesignStateJsonSerializer` covers the serialization need; extend in-place |

---

## Version Compatibility Summary

| Component | Current Version | v3.0 Change | Conflict Risk |
|-----------|----------------|-------------|---------------|
| Neo4j.Driver (NuGet) | 5.28.2 | None (stay) | None |
| DG.Core target | net7.0 + net9.0 | None | None |
| DG.Grasshopper target | net7.0-windows | None | None |
| data-service neo4j (pip) | pinned via requirements.txt | None | None |
| specklepy | 3.2.4 | None | None |
| Grasshopper SDK (Rhino 8) | Runtime DLLs, no version lock | None | None |
| Neo4j server (docker) | neo4j:5 image | Multi-label MERGE is standard Neo4j 5 Cypher | None |

---

## Sources

- [NuGet Gallery — Neo4j.Driver](https://www.nuget.org/packages/Neo4j.Driver) — confirmed 5.28.4 is latest 5.x patch, 6.0.0 is latest stable; HIGH confidence
- [Neo4j .NET Driver Upgrade Guide](https://neo4j.com/docs/dotnet-manual/current/upgrade/) — 6.0.0 breaking changes: .NET 8 minimum, transaction API renames, CloseAsync removed; HIGH confidence
- [Graph Modeling: Labels — Neo4j Developer Blog](https://medium.com/neo4j/graph-modeling-labels-71775ff7d121) — multi-label hierarchy guidance, 4-label performance threshold; MEDIUM confidence (official Neo4j blog post)
- [Neo4j Community — Create multiple labels (hierarchical label)](https://community.neo4j.com/t/create-multiple-labels-hierarchical-label-relationship/16806) — community validation of multi-label subtype pattern; MEDIUM confidence
- [Rhino Developer Docs — IGH_DataAccess.GetDataTree](https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_Kernel_IGH_DataAccess_GetDataTree__1.htm) — DataTree vs GH_Structure SDK recommendation; HIGH confidence (official McNeel docs)
- [GitHub — DeterministicGuids](https://github.com/MarkCiliaVincenti/DeterministicGuids) — confirmed SHA256-based deterministic GUID is achievable without external library in .NET; LOW confidence (external lib, not needed)
- DG.Core source — `DesignStateComponent.ComputeStateId`, `SwrlRuleParser.ResolveAtomType`, `VariableBinder.BuildBindings`, `Neo4jRuleRepository.PopulateVariables` — read directly; HIGH confidence

---

*Stack research for: Design Grammar System v3.0 Typed Variables and Composable Design State*
*Researched: 2026-05-11*
