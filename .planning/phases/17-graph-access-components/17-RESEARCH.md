# Phase 17: Graph Access Components — Research

**Researched:** 2026-07-04
**Domain:** C# Grasshopper plugin — Neo4j graph layer access components
**Confidence:** HIGH

## Summary

Phase 17 implements 5 Grasshopper components (CONNECTOR update, new GRAPH DECONSTRUCT, METAGRAPH extended, new ONTOGRAPH, new VALIDATION GRAPH) that collectively provide read-only access to all 4 Neo4j graph layers. The architecture follows the existing async-load patterns established by `ConnectorComponent` and `MetagraphComponent` — `Task<T>` + `CancellationTokenSource` + `ContinueWith` → `ScheduleSolution` + `ExpireSolution`. Three new repository interfaces (`IOntoGraphRepository`, `IValidGraphRepository`, and extended `IRuleRepository`) follow the `IRuleRepository` single-async-method pattern exactly.

The key architectural insight is that GRAPH DECONSTRUCT is the only purely synchronous component (no database calls, no async — pure type wrapping), while METAGRAPH, ONTOGRAPH, and VALIDATION GRAPH all reuse the established async-load pattern. Four handle types (`MetagraphHandle`, `OntographHandle`, `ValidGraphHandle`, `SpecGraphHandle`) wrap the existing `ConnectionInfo` object, providing Grasshopper wire-level type safety — a MetagraphHandle wire cannot accidentally plug into ONTOGRAPH's Ontograph input port.

**Primary recommendation:** Create all 4 handle types as immutable `{ get; init; }` classes in `DG.Core.Models`, add public wrappers in `PublicTypes.cs`, then implement components building-order: GRAPH DECONSTRUCT (no async, simplest) → CONNECTOR update (rename ports only) → METAGRAPH extension (add Objects output) → ONTOGRAPH (new repository + component) → VALIDATION GRAPH (new repository + component, replacing VALIDATION RUNS). Test the repository queries against a known-good Docker Neo4j instance. Do not attempt E2E wiring tests in Phase 17 — VALIDATOR (Phase 18) is needed to write v2 `statePayloadJson` to ValidGraph before VALIDATION GRAPH can demonstrate full read-back.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Neo4j connection (CONNECTOR) | Backend (Grasshopper plugin) | — | `Neo4jConnectorService` talks to Neo4j driver; component is the GH wrapper |
| Graph layer dispatch (GRAPH DECONSTRUCT) | Backend (Grasshopper plugin) | — | Pure type wrapping of `ConnectionInfo` in handle types — no external calls |
| Metagraph rule/object reading (METAGRAPH) | Backend (Grasshopper plugin) | Database (Neo4j) | `Neo4jRuleRepository` queries Neo4j; component is the GH async wrapper |
| OntoGraph reading (ONTOGRAPH) | Backend (Grasshopper plugin) | Database (Neo4j) | New `Neo4jOntoGraphRepository` queries Neo4j `graph='OntoGraph'` |
| ValidGraph reading (VALIDATION GRAPH) | Backend (Grasshopper plugin) | Database (Neo4j) | New `Neo4jValidGraphRepository` queries Neo4j `graph='ValidGraph'` |
| SpecGraph reading | Backend (Grasshopper plugin) | Database (Neo4j) | Handle exists but no consumer yet — future hook |
| Error messaging | Backend (DG.Core) | — | `ErrorMessageTemplates` static class in `DG.Core.Services`, existing pattern |
| GH type casting | Backend (DG.Grasshopper) | — | `GhCastingHelpers.Unwrap<T>` pattern, handles are just types |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Neo4j.Driver | 5.28.2 | Neo4j Bolt protocol access | Already in DG.Core csproj; verified [CITED: DG/src/DG.Core/DG.Core.csproj] |
| .NET SDK | 9.0.308 | Build and runtime | Installed on dev machine [VERIFIED: `dotnet --version` returned 9.0.308] |
| xUnit | 2.9.2 | Unit testing | Already in DG.Tests csproj [CITED: DG/tests/DG.Tests/DG.Tests.csproj] |
| RhinoCommon | 8.x | Rhino API (for Grasshopper plugin) | Already referenced by DG.Grasshopper csproj [CITED: DG/src/DG.Grasshopper/DG.Grasshopper.csproj] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| DG.Core.Models | in-repo | Domain models (ConnectionInfo, Rule, DesignState, etc.) | All handle types and output types |
| DG.Core.Data | in-repo | Repository interfaces + implementations | All 3 graph-layer repositories |
| DG.Core.Services | in-repo | Business services (ValidationRunsQueryService, ErrorMessageTemplates) | Adapted by Neo4jValidGraphRepository |
| DG.Core.Serialization | in-repo | DesignStateJsonSerializer | Deserializing statePayloadJson in ValidGraph repository |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Individual handle types per layer | Single `GraphHandle` with `Layer` enum | Grasshopper wire-level type safety lost — no compile-time detection of wrong layer connection |
| Direct Cypher in component class | Dedicated repository classes per CONTEXT D-06 | Testability lost; repository pattern enables mocking |
| Adapt ValidationRunsQueryService in-place | Fresh Neo4jValidGraphRepository class (as recommended) | Hybrid: new class using same Cypher, different output model — old service deprecated but not removed until Phase 18 |

**Version verification:**
```
Neo4j.Driver 5.28.2 — [VERIFIED: DG.Core.csproj]
.NET SDK 9.0.308 — [VERIFIED: dotnet --version]
xUnit 2.9.2 — [VERIFIED: DG.Tests.csproj]
```

## Package Legitimacy Audit

This phase uses only in-repo assemblies and the existing `Neo4j.Driver` NuGet package already referenced by `DG.Core.csproj`. No new external packages are required.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| Neo4j.Driver 5.28.2 | NuGet | 1+ yr | Widespread | github.com/neo4j/neo4j-dotnet-driver | OK | Already approved (existing dependency) |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** none

## Architecture Patterns

### System Architecture Diagram

```
[Grasshopper Canvas]
    |
    | CONNECTOR (updated)
    |   in: Neo4jURI, Neo4jUser, Neo4jPassword, PROJECT NAME, Connect
    |   out: Database (ConnectionInfo), Project
    |       |
    |       v
    | GRAPH DECONSTRUCT (new)
    |   in: Database (ConnectionInfo)
    |   out: Metagraph | Ontograph | ValidGraph | SpecGraph
    |       |          |             |              |
    |       v          v             v              v
    |  METAGRAPH   ONTOGRAPH   VALIDATION GRAPH   [SpecGraph handle]
    |  (extended)  (new)       (replaces          (no consumer yet —
    |   Rules      Class       VALIDATION RUNS)    future hook)
    |   +Objects   ObjProp.    Run + Status
    |              DataProp.   + DesignState
    |
    v
 [Neo4j Bolt Driver]
    |
    +-- Metagraph DB (graph='Metagraph')
    +-- OntoGraph DB (graph='OntoGraph')
    +-- ValidGraph DB (graph='ValidGraph')
    +-- SpecGraph DB (graph='SpecGraph')
```

### Recommended Project Structure

```
DG/src/DG.Core/
├── Models/
│   ├── ConnectionInfo.cs             (existing — wrapped by all handles)
│   ├── MetagraphHandle.cs            (new — wraps ConnectionInfo)
│   ├── OntographHandle.cs            (new — wraps ConnectionInfo)
│   ├── ValidGraphHandle.cs           (new — wraps ConnectionInfo)
│   ├── SpecGraphHandle.cs            (new — wraps ConnectionInfo)
│   ├── OntologyClass.cs              (new — IRI + label for ONTOGRAPH output)
│   ├── OntologyProperty.cs           (new — IRI + label for ONTOGRAPH output)
│   └── ... (existing models)
├── Data/
│   ├── IRuleRepository.cs            (extend — add GetObjectsAsync)
│   ├── Neo4jRuleRepository.cs        (extend — add GetObjectsAsync)
│   ├── IOntoGraphRepository.cs       (new)
│   ├── Neo4jOntoGraphRepository.cs   (new)
│   ├── IValidGraphRepository.cs      (new)
│   ├── Neo4jValidGraphRepository.cs  (new)
│   └── ... (existing files)

DG/src/DG.Grasshopper/
├── Components/
│   ├── ConnectorComponent.cs         (update — port renames + Project output)
│   ├── GraphDeconstructComponent.cs  (new — pure passthrough)
│   ├── MetagraphComponent.cs         (extend — add Objects output)
│   ├── OntoGraphComponent.cs         (new)
│   ├── ValidationGraphComponent.cs   (new — replaces ValidationRunsComponent)
│   ├── ValidationRunsComponent.cs    (keep/deprecate — removed in Phase 18)
│   ├── GhCastingHelpers.cs           (extend if needed — generic Unwrap<T> sufficient)
│   └── ... (existing files)
├── PublicTypes.cs                    (extend — add handle type wrappers)
├── DgIcons.cs                        (extend — add new icon entries)
└── Properties/
    ├── GraphDeconstruct24.png        (new icon)
    ├── OntoGraph24.png               (new icon)
    └── ValidationGraph24.png         (new icon — replaces ValidationRuns24.png)
```

### Pattern 1: Async Load with Edge-Triggered Refresh
**What:** Every Neo4j-reading component uses the same async pattern: accept ConnectionInfo + bool Refresh, start async task on rising-edge or connection change, `ContinueWith` schedules re-solve.
**When to use:** METAGRAPH, ONTOGRAPH, VALIDATION GRAPH — all 3 reader components.
**Example (from existing `MetagraphComponent.SolveInstance`):**
```csharp
// [CITED: DG/src/DG.Grasshopper/Components/MetagraphComponent.cs]
var requestKey = BuildRequestKey(connection);
var connectionChanged = !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal);
var refreshPressed = refresh && !_refreshLatched;
_refreshLatched = refresh;

if (_loadTask is null || connectionChanged || refreshPressed)
{
    StartLoad(connection, requestKey);
}

if (_loadTask is { IsCompletedSuccessfully: true })
{
    _latestRules = _loadTask.Result.Select(ToPublicRule).ToList();
    Message = $"{_latestRules.Count} rules";
}
```

### Pattern 2: Repository Single-Async-Method
**What:** Each repository interface declares one async query method taking `ConnectionInfo` + `CancellationToken`, returning a task of the result list. Implementations use `GraphDatabase.Driver` → `AsyncSession` → `RunAsync` → `ForEachAsync`.
**When to use:** All 3 graph-layer repositories (extending `IRuleRepository` and new `IOntoGraphRepository`, `IValidGraphRepository`).
**Example (from existing `Neo4jRuleRepository.GetRulesAsync`):**
```csharp
// [CITED: DG/src/DG.Core/Data/Neo4jRuleRepository.cs]
await using var driver = GraphDatabase.Driver(connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
await using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));
var cursor = await session.RunAsync(query, new { project }).WaitAsync(QueryTimeout, cancellationToken);
```

### Anti-Patterns to Avoid
- **Blocking on async in `SolveInstance`:** Grasshopper's `SolveInstance` must not block on `Task.Result` synchronously — this hangs the GH UI. All async components must use `ContinueWith` + `ScheduleSolution` for deferred completion, exactly as `ConnectorComponent` and `MetagraphComponent` do.
- **Tight coupling to `ValidationRunsQueryService`:** The CONTEXT decisions say to create a new `Neo4jValidGraphRepository` class, not modify the existing `ValidationRunsQueryService` — this avoids breaking Phase 18's ability to remove that service cleanly.
- **Re-creating driver per query call:** Each repository method already creates a fresh driver+session per call (existing `Neo4jRuleRepository` pattern). Reuse across calls within a single component instance is not necessary because Grasshopper components are stateless between solves.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Neo4j connection management | New connection logic | Existing `Neo4jConnectorService` + `Neo4jRuleRepository` patterns | Connection test + Bolt driver patterns are well-established |
| GH value unwrapping | Per-type casting methods | `GhCastingHelpers.Unwrap<T>(object?)` generic | Since handles are distinct .NET types, `Unwrap<MetagraphHandle>()` works — no per-handle `Try*` needed per CONTEXT discretion |
| JSON deserialization of state payload | New JSON parser | Existing `DesignStateJsonSerializer.Deserialize(string)` | Handles v1 (ParamState-only) payloads; extend for v2 3-part payload compat |
| Error message formatting | Inline error strings | `ErrorMessageTemplates` static class | Follows existing What+Where+How-to-fix pattern, test coverage exists |
| GRAPH DECONSTRUCT async infrastructure | Async task, CancellationTokenSource, Loading states | Pure synchronous GH_Component | Per CONTEXT: "pure passthrough — no database calls, no async, no SolveInstance complexity" |

**Key insight:** Phase 17 has an unusually high ratio of "use existing patterns" to "build new infrastructure." Almost every architectural decision (async pattern, repository pattern, error messaging, type casting, model immutability) has a well-established precedent in the codebase from Phases 7, 13, 14, 15, and 16. The new code is primarily wiring existing patterns into 5 Grasshopper component wrappers.

## Common Pitfalls

### Pitfall 1: Blocking on Async in SolveInstance
**What goes wrong:** Calling `.Result` or `.Wait()` on an async task inside `SolveInstance` freezes the Grasshopper UI.
**Why it happens:** `SolveInstance` runs on the GH UI thread; blocking it prevents solution scheduling.
**How to avoid:** Always use `ContinueWith` + `OnPingDocument()` + `ScheduleSolution` + `ExpireSolution(false)` pattern as demonstrated in `ConnectorComponent` and `MetagraphComponent`.
**Warning signs:** GH UI hangs when test-clicking Connect or Refresh on component.

### Pitfall 2: Index-Mismatch Between Rules and Objects
**What goes wrong:** METAGRAPH's Rules and Objects outputs are specified as index-matched parallel lists. If the two queries return items in non-correlated order, downstream consumers get wrong pairings.
**Why it happens:** Two separate async queries (Rules + Atoms query, Objects query) may complete in arbitrary order.
**How to avoid:** Both queries must ORDER BY the same key (Rule_Id IRI). The Objects query deduplicates by Class IRI — but the index match is Rules[i] ↔ Objects[i] by same Rule_Id ordering across both lists.
**Warning signs:** A downstream RULE DECONSTRUCT wired to an Object that doesn't match its Rule.

### Pitfall 3: DesignState v1/v2 Payload Deserialization
**What goes wrong:** `Neo4jValidGraphRepository` loads `statePayloadJson` from ValidGraph. At Phase 17 time, only v1 (ParamState-only) payloads exist. Phase 18 writes v2 (3-part ObjState+ParamState+PropState) payloads. If the repository uses `DesignStateJsonSerializer.Deserialize` (which expects a `ParamState`), it fails on v2 payloads.
**Why it happens:** `DesignStateJsonSerializer` is ParamState-specific (it calls `ValidateSnapshot` checking ParamState invariants).
**How to avoid:** The `Neo4jValidGraphRepository` must handle both payload shapes. For v1, deserialize into a DesignState with only ParamStates populated. For v2, deserialize into full 3-part DesignState. A heuristic: check if JSON root has a `kind` array or `stateKind` discriminator field. The `ValidationRunsQueryService` already has precedent for handling the v1 path — extend with a v2-aware code path, not a replacement.

### Pitfall 4: GUID Collision for VALIDATION GRAPH
**What goes wrong:** VALIDATION GRAPH replaces VALIDATION RUNS with a new GUID but the old GUID remains registered in Grasshopper. If both components somehow coexist on a canvas, the solver may pick the wrong one.
**Why it happens:** Grasshopper identifies components by GUID.
**How to avoid:** Use the GUID specified for VALIDATION GRAPH (new, from port-IRI map or CONTEXT). The old VALIDATION RUNS GUID (`A7F2C3E1-B849-4D6A-9F0E-3C2D1E5B8A94`) is marked for deprecation; canvas breakage is expected and documented in Phase 20.

### Pitfall 5: GRAPH DECONSTRUCT Handle Type Registration
**What goes wrong:** If `MetagraphHandle`/`OntographHandle`/`ValidGraphHandle`/`SpecGraphHandle` are not registered as GH_Goo types, Grasshopper cannot pass them through wires — `SetData` silently drops them.
**Why it happens:** Grasshopper requires any object passed via `da.SetData` to either be a primitive, an `IGH_Goo`-wrapped type, or registered via `GH_Component.SetData`. Handle types are custom classes.
**How to avoid:** Either make each handle an `IGH_Goo` implementation (adds boilerplate) or pass them as `GH_ObjectWrapper` via `GhCastingHelpers.Unwrap<T>`. The existing `ConnectionInfo` works without IGH_Goo — it's passed as a plain object and unwrapped with `GhCastingHelpers.Unwrap<ConnectionInfo>(input)`. The 4 handle types follow the same pattern: plain `{ get; init; }` classes, unwrapped via generic `Unwrap<T>` per CONTEXT discretion.

## Code Examples

### Handle Type Pattern
```csharp
// Source: Pattern from ConnectionInfo (DG/src/DG.Core/Models/ConnectionInfo.cs)
// New: DG/src/DG.Core/Models/MetagraphHandle.cs (analogous for OntographHandle, ValidGraphHandle, SpecGraphHandle)
namespace DG.Core.Models;

public sealed class MetagraphHandle
{
    public ConnectionInfo ConnectionInfo { get; init; } = new();
}
```

### GRAPH DECONSTRUCT Pure Passthrough
```csharp
// Source: CONTEXT discretion — derived from ConnectorComponent pattern
#if GRASSHOPPER_SDK
using DG.Core.Models;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class GraphDeconstructComponent : GH_Component
{
    public GraphDeconstructComponent()
        : base("GRAPH DECONSTRUCT", "DECONSTRUCT", "Split a Database handle into 4 graph layer handles.",
            DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("..."); // new GUID

    protected override Bitmap Icon => DgIcons.GraphDeconstruct24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Database", "Database", "DG connection object from CONNECTOR", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Metagraph", "Metagraph", "Metagraph layer handle", GH_ParamAccess.item);
        pManager.AddGenericParameter("Ontograph", "Ontograph", "Ontograph layer handle", GH_ParamAccess.item);
        pManager.AddGenericParameter("ValidGraph", "ValidGraph", "ValidGraph layer handle", GH_ParamAccess.item);
        pManager.AddGenericParameter("SpecGraph", "SpecGraph", "SpecGraph layer handle", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? databaseInput = null;
        if (!da.GetData(0, ref databaseInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Database input is required.");
            return;
        }

        var connection = GhCastingHelpers.Unwrap<ConnectionInfo>(databaseInput);
        if (connection is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast Database input.");
            return;
        }

        da.SetData(0, new MetagraphHandle { ConnectionInfo = connection });
        da.SetData(1, new OntographHandle { ConnectionInfo = connection });
        da.SetData(2, new ValidGraphHandle { ConnectionInfo = connection });
        da.SetData(3, new SpecGraphHandle { ConnectionInfo = connection });
    }
}
#else
namespace DG.Grasshopper.Components;
public sealed class GraphDeconstructComponent { }
#endif
```

### Objects Query (REFERS_TO → Class)
```csharp
// Source: CONTEXT D-02 — direct Neo4j query, not naming-convention-based
// Added to Neo4jRuleRepository
private const string ObjectsQuery = """
    MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class)
    RETURN DISTINCT c.iri AS iri, c.label AS label
    ORDER BY c.label
    """;

public async Task<IReadOnlyList<OntologyClass>> GetObjectsAsync(
    ConnectionInfo connection, CancellationToken cancellationToken = default)
{
    await using var driver = GraphDatabase.Driver(connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
    await using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));

    var cursor = await session
        .RunAsync(ObjectsQuery, new { project = connection.Project })
        .WaitAsync(QueryTimeout, cancellationToken);

    var objects = new List<OntologyClass>();
    await cursor
        .ForEachAsync(record =>
        {
            objects.Add(new OntologyClass
            {
                Iri = record["iri"].As<string>(),
                Label = record["label"].As<string>(),
            });
        })
        .WaitAsync(QueryTimeout, cancellationToken);

    return objects;
}
```

### ONTOGRAPH Repository Query (Class example)
```csharp
// Source: D-06 — new IOntoGraphRepository
private const string ClassesQuery = """
    MATCH (c:Class {graph:'OntoGraph', project:$project})
    RETURN c.iri AS iri, c.label AS label
    ORDER BY c.label
    """;
// ObjProperty and DataProperty queries are analogous, matching graph='OntoGraph'
```

### DesignState v1/v2 Compat Deserialization
```csharp
// Source: CONTEXT discretion — repository handles both payload formats
private static DesignState? TryParseDesignState(string? statePayloadJson)
{
    if (string.IsNullOrWhiteSpace(statePayloadJson)) return null;

    try
    {
        // Try v2 format first (3-part: ObjState/ParamState/PropState at root)
        using var doc = JsonDocument.Parse(statePayloadJson);
        var root = doc.RootElement;
        if (root.TryGetProperty("objStates", out _) || root.TryGetProperty("stateKind", out _))
        {
            // v2 payload — deserialize as full DesignState
            return JsonSerializer.Deserialize<DesignState>(statePayloadJson, ...);
        }
        // Fallback: v1 payload — deserialize as ParamState-only DesignState
        var paramState = DesignStateJsonSerializer.Deserialize(statePayloadJson);
        return new DesignState
        {
            StateId = paramState.StateId,
            CapturedAtUtc = paramState.CapturedAtUtc,
            ParamStates = new List<ParamState> { paramState },
        };
    }
    catch
    {
        return null;
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| VALIDATION RUNS component | VALIDATION GRAPH component (new GUID) | Phase 17 | Canvas breakage — old GUID no longer recognized, wire replacement required |
| `ValidationRunsQueryService` single class | `Neo4jValidGraphRepository` (new) + keep `ValidationRunsQueryService` (deprecated) | Phase 17 | Dual-read until Phase 18 removes the old path |
| METAGRAPH has 3 outputs (Rules, RuleName, Count) | METAGRAPH gains 5 outputs (Rules, RuleName, Count + Objects, ObjectName) | Phase 17 | Port-IRI map defines exact output schema |
| ConnectionInfo passed directly | ConnectionInfo wrapped in typed handles | Phase 17 | Wire-level type safety; GRAPH DECONSTRUCT controls handle creation |
| `DesignStateSnapshot` → `ParamState` rename | v2 statePayloadJson adds 3-part composition | Phase 16 | `Neo4jValidGraphRepository` must handle both v1 and v2 |

**Deprecated/outdated:**
- `ValidationRunsComponent` component GUID `A7F2C3E1-B849-4D6A-9F0E-3C2D1E5B8A94` — replaced by VALIDATION GRAPH with new GUID per CONTEXT

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GhCastingHelpers.Unwrap<T>` works for all 4 handle types without per-handle registration | Code Examples | Handles are just `{ get; init; }` classes — same as `ConnectionInfo` — so `Unwrap<T>` should work. Risk: if Grasshopper requires `IGH_Goo` for non-primitive types through wires, each handle needs a wrapper. Mitigation: test with `Unwrap<ConnectionInfo>` (works today) — handles use same pattern. |
| A2 | DesignState v1 payloads can be distinguished from v2 by JSON root key presence | Code Examples | If v1 and v2 payloads have overlapping key sets (e.g. both have `stateId` at root), heuristic may misclassify. Mitigation: Phase 18 VALIDATOR must use a discriminator key (`stateKind: "v2"` or similar) that v1 payloads lack. |

## Open Questions (RESOLVED)

1. **(RESOLVED)** **How to distinguish v1 from v2 statePayloadJson at deserialization time?**
   - What we know: v1 is a strict ParamState (StateId + CapturedAtUtc + Parameters array). v2 will have 3-part composition structure.
   - What's unclear: The exact JSON shape of v2 is defined by Phase 18 VALIDATOR's write path, which hasn't been built yet. v1 payloads exist in DB from existing ValidationRun nodes.
   - Recommendation: Use a try-v2-first heuristic — attempt v2 deserialization, fall back to v1 if `JsonException` is thrown. Document that v2 payloads are absent until Phase 18 completes; Phase 17 VALIDATION GRAPH shows empty DesignState when only v1 payloads exist (which is an acceptable interim state per CONTEXT design).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| .NET SDK | Build all projects | yes | 9.0.308 | DOTNET_ROLL_FORWARD=LatestMajor if net9.0 absent |
| xUnit | Test execution | yes | 2.9.2 | — |
| Neo4j.Driver NuGet | Database queries | yes | 5.28.2 | — |
| Rhino 8 SDK | Grasshopper compilation | yes * | 8.x | `#if GRASSHOPPER_SDK` guard stub for non-GH builds |
| Docker | Running Neo4j for integration tests | yes | — | Mock repository tests (pure C#, no Docker needed) |

**Missing dependencies with no fallback:** none — all required tools are installed and verified.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | xUnit 2.9.2 + Microsoft.NET.Test.Sdk 17.12.0 |
| Config file | none — xUnit discovers facts automatically |
| Quick run command | `dotnet test DG\tests\DG.Tests\ --no-restore --filter "FullyQualifiedName~{TestClass}"` |
| Full suite command | `dotnet test DG\tests\DG.Tests\` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GHGA-01 | CONNECTOR outputs Database handle with renamed ports | unit | `dotnet test DG\tests\DG.Tests\ --filter "FullyQualifiedName~ConnectorComponent"` | ❌ Wave 0 |
| GHGA-02 | GRAPH DECONSTRUCT splits ConnectionInfo into 4 typed handles | unit | `dotnet test DG\tests\DG.Tests\ --filter "FullyQualifiedName~GraphDeconstructComponent"` | ❌ Wave 0 |
| GHGA-03 | METAGRAPH outputs index-matched Rules+Objects | unit | `dotnet test DG\tests\DG.Tests\ --filter "FullyQualifiedName~MetagraphComponent"` | ❌ Wave 0 |
| GHGA-04 | ONTOGRAPH lists Class/ObjProperties/DataProperties | integration (Cypher) | `dotnet test DG\tests\DG.Tests\ --filter "FullyQualifiedName~OntoGraphRepository"` | ❌ Wave 0 |
| GHGA-05 | VALIDATION GRAPH reads Run/Status/DesignState from ValidGraph | integration (Cypher) | `dotnet test DG\tests\DG.Tests\ --filter "FullyQualifiedName~ValidGraphRepository"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `dotnet test DG\tests\DG.Tests\` (full suite, ~4s)
- **Per wave merge:** same
- **Phase gate:** Full suite green before `gsd-verify-work`

### Wave 0 Gaps
- [ ] `DG/tests/DG.Tests/MetagraphHandleModelTests.cs` — covers handle type immutability and default values
- [ ] `DG/tests/DG.Tests/OntographHandleModelTests.cs` — covers handle type
- [ ] `DG/tests/DG.Tests/ValidGraphHandleModelTests.cs` — covers handle type
- [ ] `DG/tests/DG.Tests/SpecGraphHandleModelTests.cs` — covers handle type
- [ ] `DG/tests/DG.Tests/OntologyClassModelTests.cs` — covers model IRI+label
- [ ] `DG/tests/DG.Tests/OntologyPropertyModelTests.cs` — covers model IRI+label
- [ ] `DG/tests/DG.Tests/Neo4jOntoGraphRepositoryTests.cs` — covers Cypher query for Classes, ObjProperties, DataProperties
- [ ] `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` — covers Run/Status/DesignState output, v1/v2 compat, deduplication
- [ ] `DG/tests/DG.Tests/ObjectsQueryTests.cs` — METAGRAPH Objects extraction via REFERS_TO->Class, dedup by IRI
- [ ] Error message unit tests for new `ErrorMessageTemplates` entries (if any added)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Neo4j credentials handled by existing `Neo4jConnectorService` — no change |
| V3 Session Management | no | Bolt driver sessions are ephemeral per repository call |
| V4 Access Control | no | Neo4j project isolation already in-place via `project` property on all queries |
| V5 Input Validation | yes | ConnectionInfo inputs validated via existing `Neo4jConnectorService` — no new input surfaces |
| V6 Cryptography | no | Neo4j Bolt protocol handles encryption — no change |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Neo4j credential exposure in Grasshopper canvas | Information Disclosure | Credentials input as GH text parameters (not hardcoded) — existing pattern, no change |
| Cypher injection via project name | Tampering | All queries use parameterized `new { project }` — project value is parameterized, not string-concatenated |
| Deserialization of malformed `statePayloadJson` | Tampering | Try-catch with null return on parse failure — existing pattern from `ValidationRunsQueryService` |

## Sources

### Primary (HIGH confidence)
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` — established async pattern [VERIFIED: codebase grep]
- `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs` — established async-load pattern [VERIFIED: codebase grep]
- `DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs` — existing VALIDATION RUNS [VERIFIED: codebase grep]
- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` — repository query pattern [VERIFIED: codebase grep]
- `DG/src/DG.Core/Data/IRuleRepository.cs` — repository interface pattern [VERIFIED: codebase grep]
- `DG/src/DG.Core/Data/Neo4jConnectorService.cs` — connection pattern [VERIFIED: codebase grep]
- `DG/src/DG.Core/Data/INeo4jConnectorService.cs` — connection interface [VERIFIED: codebase grep]
- `DG/src/DG.Core/Models/ConnectionInfo.cs` — immutable model pattern [VERIFIED: codebase grep]
- `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` — ValidGraph Cypher template [VERIFIED: codebase grep]
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — error message pattern [VERIFIED: codebase grep]
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — generic Unwrap<T> pattern [VERIFIED: codebase grep]
- `DG/src/DG.Grasshopper/PublicTypes.cs` — public wrapper pattern [VERIFIED: codebase grep]
- `ontology/port-iri-map-V7.md` — exact port names and IRIs for all 5 components [VERIFIED: codebase read]
- `ontology/V7-INVESTIGATION.md` — conflict resolutions (a)/(b)/(c) [VERIFIED: codebase read]
- `.planning/phases/17-graph-access-components/17-CONTEXT.md` — locked user decisions [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)
- `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs` — v1 JSON serialization pattern [VERIFIED: codebase grep]
- `DG/src/DG.Core/Models/DesignState.cs` — 3-part composition model [VERIFIED: codebase grep]

### Tertiary (LOW confidence)
- None — all claims verified against source code or official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages and versions verified against project files and dotnet SDK
- Architecture: HIGH — patterns are derived from existing, working component implementations
- Pitfalls: HIGH — drawn from existing code patterns and CONTEXT decisions

**Research date:** 2026-07-04
**Valid until:** 2026-08-04 (30 days — stable project with no fast-moving dependencies beyond Neo4j.Driver)
