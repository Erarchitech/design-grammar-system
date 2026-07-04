---
phase: 17-graph-access-components
reviewed: 2026-07-04T14:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - DG/src/DG.Core/Models/MetagraphHandle.cs
  - DG/src/DG.Core/Models/OntographHandle.cs
  - DG/src/DG.Core/Models/ValidGraphHandle.cs
  - DG/src/DG.Core/Models/SpecGraphHandle.cs
  - DG/src/DG.Core/Models/OntologyClass.cs
  - DG/src/DG.Core/Models/OntologyProperty.cs
  - DG/src/DG.Core/Data/IOntoGraphRepository.cs
  - DG/src/DG.Core/Data/IRuleRepository.cs
  - DG/src/DG.Core/Data/IValidGraphRepository.cs
  - DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs
  - DG/src/DG.Core/Data/Neo4jRuleRepository.cs
  - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
  - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
  - DG/src/DG.Grasshopper/Components/ConnectorComponent.cs
  - DG/src/DG.Grasshopper/Components/GraphDeconstructComponent.cs
  - DG/src/DG.Grasshopper/Components/MetagraphComponent.cs
  - DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs
  - DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs
  - DG/src/DG.Grasshopper/PublicTypes.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
findings:
  critical: 0
  warning: 7
  info: 6
  total: 13
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-07-04T14:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed 20 source files implementing Phase 17 graph access components: 4 layer handle types, CONNECTOR port renames, GRAPH DECONSTRUCT passthrough, METAGRAPH Objects extension, ONTOGRAPH repository/component, VALIDATION GRAPH repository/component replacing the old ValidationRunsComponent, ErrorMessageTemplates extensions, and PublicTypes/DgIcons registration.

The architecture is sound and the per-layer interface pattern is well-structured. The type chain from CONNECTOR -> GRAPH DECONSTRUCT -> individual reader components is type-safe via distinct handle types and the generic `GhCastingHelpers.Unwrap<T>` pattern.

**Key issues found:**
1. Two `SetEmptyOutputs` methods overwrite output 0 with a string after correctly setting empty lists (WARNING)
2. `Neo4jValidGraphRepository` per-ObjState status is flat (all elements == overallPass) instead of properly computed per-ObjState (WARNING)
3. ConnectorComponent exposes default password "12345678" in Grasshopper UI (WARNING)
4. Several INFO-level issues: redundant using directives, input port naming inconsistency between METAGRAPH ("Connection") and the rest ("Ontograph"/"ValidGraph"), and the `RunInfo` class not being sealed like `ValidGraphQueryResult`

## Warnings

### WR-01: SetEmptyOutputs overwrites output 0 with status string (OntoGraphComponent)

**File:** `DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs:202`
**Issue:** `SetEmptyOutputs` sets empty lists on all 3 outputs, then immediately overwrites output 0 with `da.SetData(0, status)` — a string value. This overwrites the correct empty `List<OntologyClass>` with a string. Called when input is not connected or handle is invalid. Downstream consumers reading output 0 ("Class") will receive a string instead of a list, causing a type mismatch.

**Fix:** Remove the spurious `da.SetData(0, status)` call. The status should be communicated only via `AddRuntimeMessage` and the `Message` property, not via overwriting a data output. Method should be:

```csharp
private void SetEmptyOutputs(IGH_DataAccess da, string status)
{
    da.SetDataList(0, new List<global::DG.OntologyClass>());
    da.SetDataList(1, new List<global::DG.OntologyProperty>());
    da.SetDataList(2, new List<global::DG.OntologyProperty>());
    // Note: removed da.SetData(0, status) — status is set via Message field above
}
```

### WR-02: SetEmptyOutputs overwrites output 0 with status string (ValidationGraphComponent)

**File:** `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs:202`
**Issue:** Identical pattern to WR-01. `da.SetData(0, status)` on line 202 overwrites the empty `List<RunInfo>` set on line 199 with a string. Affects error paths when ValidGraph input is missing or handle is invalid.

**Fix:** Same fix as WR-01 — remove the `da.SetData(0, status)` call.

```csharp
private static void SetEmptyOutputs(IGH_DataAccess da, string status)
{
    da.SetDataList(0, new List<global::DG.RunInfo>());
    da.SetDataList(1, new List<IReadOnlyList<bool>>());
    da.SetDataList(2, new List<global::DG.DesignState>());
    // Removed: da.SetData(0, status);
}
```

### WR-03: Per-ObjState status is flat (all elements == overallPass)

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:56-58`
**Issue:** The per-ObjState status list is built with `Enumerable.Repeat(overallPass, objStateCount)`. This gives every ObjState the same pass/fail value (the AND of all rule results). Per D-05, `Status[i]` should be a per-ObjState boolean list with one element per ObjState, where each element reflects that ObjState's individual validation result. A run with 3 ObjStates currently gets `[true, true, true]` or `[false, false, false]` instead of potentially `[true, false, true]`.

This is rooted in the data model — the current `rulesJson` stores per-rule results, not per-ObjState results. The status derivation will need per-ObjState data from Phase 18 (VALIDATOR) to be correct. As-is, the status output is misleading: it claims to be per-ObjState but provides no individualization.

**Fix:** Either (a) add per-ObjState result tracking in the rulesJson/statePayloadJson schema and use it here, or (b) document that status is currently a single overall boolean and change the output type to `IReadOnlyList<bool>` (1:1 with Runs). If keeping the per-ObjState shape, align the data model so each ObjState maps to specific rule results, then compute:

```csharp
// Placeholder: once per-ObjState data exists in rulesJson, compute individually
// For now, compute overall AND and document the limitation
```

### WR-04: ConnectorComponent exposes default password in Grasshopper UI

**File:** `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs:20,39`
**Issue:** The default password "12345678" is hardcoded as the default value for the Neo4jPassword input parameter. This value is visible to any user who inspects the component in Grasshopper or hovers over the input port. While these are defaults that get overridden by user input, shipping default credentials (especially a weak password like "12345678") in the component metadata exposes the target Neo4j instance's default credentials to anyone who sees the component.

Additionally, lines 15-23 store the same defaults in the `_latestConnection` field.

**Fix:** Change the default password to an empty string, requiring the user to explicitly provide credentials:

```csharp
pManager.AddTextParameter("Neo4jPassword", "Password", "Neo4j password", GH_ParamAccess.item, "");
```

And update the `_latestConnection` default:
```csharp
Password = string.Empty,
```

At minimum, if the password is empty, the connection attempt should produce a clear error.

### WR-05: Single-error reporting masks parallel task failures (OntoGraphComponent)

**File:** `DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs:125-128`
**Issue:** When one or more of the three parallel load tasks (`_classesTask`, `_objPropertiesTask`, `_dataPropertiesTask`) faults, the error coalescing uses `??` chaining and reports only the *first* fault found. If `_classesTask` faults with "connection refused" and `_objPropertiesTask` faults with "timeout", users only see "connection refused". They have no way to know the other tasks also failed, which could mask secondary issues like a schema mismatch in a specific query.

**Fix:** Collect all fault exceptions and join them:

```csharp
var errors = new List<string>();
if (_classesTask?.IsFaulted == true)
    errors.Add(_classesTask.Exception?.GetBaseException().Message ?? "Unknown class error");
if (_objPropertiesTask?.IsFaulted == true)
    errors.Add(_objPropertiesTask.Exception?.GetBaseException().Message ?? "Unknown obj prop error");
if (_dataPropertiesTask?.IsFaulted == true)
    errors.Add(_dataPropertiesTask.Exception?.GetBaseException().Message ?? "Unknown data prop error");
var error = errors.Count > 0 ? string.Join("; ", errors) : "Failed to load OntoGraph data.";
```

### WR-06: StatusList data from repository is shared by reference, not copied

**File:** `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs:107`
**Issue:** `result.StatusList.ToList()` creates a shallow copy of the outer list, but each inner `IReadOnlyList<bool>` is a shared reference to the same list in the repository's result object. If the repository's `ValidGraphQueryResult` were ever reused or its inner lists mutated (unlikely but possible), the component's cached data could change unexpectedly. Since the repository creates `new List<bool>` per run, mutation in user code is the risk.

**Fix:** Deep-copy the status lists to fully isolate the component's data:

```csharp
_latestStatusData = result.StatusList
    .Select(inner => (IReadOnlyList<bool>)inner.ToList())
    .ToList();
```

### WR-07: MetagraphComponent input port "Connection" inconsistent with layer-naming convention

**File:** `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs:34`
**Issue:** The METAGRAPH component registers its first input as "Connection", while ONTOGRAPH uses "Ontograph" and VALIDATION GRAPH uses "ValidGraph". The GRAPH DECONSTRUCT outputs are named "Metagraph", "Ontograph", "ValidGraph", "SpecGraph". Users wiring from GRAPH DECONSTRUCT's "Metagraph" output to METAGRAPH's "Connection" input experience a naming mismatch that the other two components don't have. This is cosmetic but causes confusion — especially since the visual wiring in Grasshopper relies on port names for user guidance.

**Fix:** Rename the input port to "Metagraph" for consistency:

```csharp
pManager.AddGenericParameter("Metagraph", "Metagraph",
    "Metagraph layer handle from GRAPH DECONSTRUCT", GH_ParamAccess.item);
```

## Info

### IN-01: Redundant `using DG.Core.Models` in handle type files

**Files:**
- `DG/src/DG.Core/Models/MetagraphHandle.cs:1`
- `DG/src/DG.Core/Models/OntographHandle.cs:1`
- `DG/src/DG.Core/Models/ValidGraphHandle.cs:1`
- `DG/src/DG.Core/Models/SpecGraphHandle.cs:1`

**Issue:** All four handle files include `using DG.Core.Models;` but are already in namespace `DG.Core.Models`. The using directive is redundant and adds unnecessary noise.

**Fix:** Remove the `using DG.Core.Models;` line from all four files.

### IN-02: `RunInfo` class not sealed unlike peer types

**File:** `DG/src/DG.Core/Data/IValidGraphRepository.cs:12`
**Issue:** `ValidGraphQueryResult` is declared `sealed` (line 5) but `RunInfo` is not (line 12). Both are returned from the repository and have no subclassing intent. Inconsistent sealing reduces design clarity.

**Fix:** Add `sealed` to `RunInfo`:

```csharp
public sealed class RunInfo
```

### IN-03: `ObjectsQuery` in Neo4jRuleRepository uses rule-level graph anchor but loose variable

**File:** `DG/src/DG.Core/Data/Neo4jRuleRepository.cs:58-62`
**Issue:** The `ObjectsQuery` anchors `r:Rule {graph:'Metagraph', project:$project}` but does not constrain `c:Class` to the same project. While `c:Class` nodes are in the OntoGraph layer and may not carry a `project` property (Class nodes are shared across projects per the schema), the query could return classes from other projects if Class nodes do have project properties. This depends on how OntoGraph nodes are tagged by n8n during ingestion. If n8n does set project on Class nodes, this query will miss them; if it doesn't, this query returns cross-project data.

**Fix:** Verify the OntoGraph ingestion behavior. If Class nodes carry `project`, add the constraint:
```cypher
MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class {project:$project})
```

### IN-04: ConnectorComponent heartbeat request key includes password in memory

**File:** `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs:159-162`
**Issue:** `BuildRequestKey` includes `request.Password` in the key string to detect credential changes. While this is functionally correct (password change triggers reconnection), it means the cleartext password lives as part of the key string in memory for the component's lifetime. The key is stored in `_activeRequestKey` and is used for string comparison on every solve. This is standard for password-in-key patterns but worth noting.

**Fix (optional):** Use a salted hash of the password in the request key instead of the cleartext value:
```csharp
private static string BuildRequestKey(ConnectionInfo request) =>
    $"{request.Uri}|{request.User}|{HashPassword(request.Password)}|{request.Database}|{request.Project}";
```

### IN-05: Neo4j driver created per method call (all three repositories)

**Files:**
- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs:66-67`
- `DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs:31-33` (and all 3 methods)
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:26-28`

**Issue:** Every repository method creates a new `GraphDatabase.Driver` instance. The Neo4j .NET driver maintains a connection pool per driver instance. Creating a driver per call means a new connection pool per query, which is wasteful. The METAGRAPH, ONTOGRAPH, and VALIDATION GRAPH components all fire 2-3 parallel queries, each creating its own driver.

This is the pre-existing pattern, so not introduced by Phase 17, but worth noting as it compounds with the parallel query pattern.

**Fix (pre-existing, optional):** Share a single `IDriver` instance per repository or use a driver factory that reuses drivers by connection string.

### IN-06: `CancelPendingConnection/Load/Query` empty catch blocks

**Files:**
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs:146-148`
- `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs:161-163`
- `DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs:181-183`
- `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs:166-168`

**Issue:** All four components use `catch { }` when cancelling CancellationTokenSource. While cancellation is best-effort and `CancellationTokenSource.Cancel()` is unlikely to throw, swallowing all exceptions without logging makes debugging harder if it does fail (e.g., ObjectDisposedException if the CTS was already disposed on another thread).

**Fix:** At minimum, log the exception (e.g., `System.Diagnostics.Debug.WriteLine`), or restructure to avoid the try/catch entirely:

```csharp
private void CancelPendingLoad()
{
    _loadCts?.Cancel();
    _loadCts?.Dispose();
    _loadCts = null;
    // ... reset fields
}
```

`CancellationTokenSource.Dispose()` and `Cancel()` are thread-safe in .NET; the try/catch is defensive but overly broad.

---

_Reviewed: 2026-07-04T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
