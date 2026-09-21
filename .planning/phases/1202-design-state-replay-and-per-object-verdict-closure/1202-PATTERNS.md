# Phase 1202: Design State Replay and Per-Object Verdict Closure - Pattern Map

**Mapped:** 2026-09-21
**Files analyzed:** 10 (modified; zero net-new files — this phase extends existing types per RESEARCH.md's "Don't Hand-Roll" section)
**Analogs found:** 10 / 10 (all in-file — this is a pure-consolidation phase; every "analog" is the surrounding code in the same file the change lands in)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `DG/src/DG.Core/Data/IValidGraphRepository.cs` | model/interface (repository contract) | CRUD (read) | itself — `GetRunsAsync` signature (existing method) | exact (additive sibling method) |
| `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` | service (Neo4j repository) | CRUD (read) | itself — `RunsQuery` + `GetRunsAsync` + `TryParseDesignState` | exact (extend query, add method, delete fabrication) |
| `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` | utility (DTO serializer) | transform | itself — `ObjStateDto`/`ToDto`/`FromDto`/`Deserialize` version check | exact |
| `DG/src/DG.Core/Models/ObjState.cs` | model | — | itself — `ClassIri` property already exists (doc-comment names it normative; only DTO lags) | exact |
| `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` | service (ID/hash generator) | transform | itself — `ComputeParamStateId`/`ComputePropStateId`/`ComputeDesignStateId`/`HashToHex16` (sibling static methods, same file) | exact (new `canonicalStateHash` computation follows `HashToHex16` calling convention, OR extends `CanonicalJsonWriter` per D-02 — see Shared Patterns) |
| `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` | component (Grasshopper) | transform | `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` (D-04 target: delete private `ComputeObjStateId`, call generator instead) | role-match (component → service call-site convergence) |
| `data-service/app.py` (`publish_validation_result`, `:571-607`) | controller/service (FastAPI handler + Cypher write) | CRUD (write, MERGE+SET) | itself — sibling `MERGE...SET` blocks at `:2136-2137` (`evidenceEnvelopeJson`) and `:2244-2245` (`shaclReportJson`), which are already single-property `SET`s on the same node | exact (pattern for splitting `ON CREATE SET` vs `SET`) |
| `data-service/app.py` (`get_validation_entity_sets`, `:846-870`) | service (per-object rollup) | transform | `data-service/evidence_contract.py:87-96` (`_ROLLUP_PRECEDENCE`) | exact (D-12: replace failed-wins with ordered-precedence lookup) |
| `tools/de01/legs.py` (`run_leg_replay`, `~:747`) | test/tooling (DE-01 leg runner) | request-response | `tools/de01/report.py:69-78` (`_rows_by_pair`) and `:81` `compare_legs` | role-match (extend leg output; mirror comparison idiom for new hash dimension) |
| `fixtures/golden/` sibling fixture (D-17, new file, name TBD by planner) | test fixture (JSON) | batch/fixture | `fixtures/golden/parser/` (1201 D-16 precedent) and `fixtures/golden/canonical-vectors.json` (1200-06/09 precedent) | exact precedent (sibling-path-not-frozen-file pattern) |

## Pattern Assignments

### `DG/src/DG.Core/Data/IValidGraphRepository.cs` (interface, CRUD-read) — D-13

**Analog:** itself, existing `GetRunsAsync` signature (lines 21-25)

**Core pattern to copy** (additive interface method, matching existing async/CancellationToken convention):
```csharp
public interface IValidGraphRepository
{
    Task<ValidGraphQueryResult> GetRunsAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default);

    // D-13 additive method — same signature shape, new return type.
    // Planner has discretion on name/signature; e.g.:
    Task<IReadOnlyList<PerObjectVerdict>> GetPerObjectVerdictsAsync(
        ConnectionInfo connection, string runId, CancellationToken cancellationToken = default);
}
```
**DTO pattern to copy** — `RunInfo`/`ValidGraphQueryResult` (lines 5-19) show the project's plain-init-property DTO convention (`IReadOnlyList<T>` with `Array.Empty<T>()` default, not `List<T>`):
```csharp
public sealed class ValidGraphQueryResult
{
    public IReadOnlyList<RunInfo> Runs { get; init; } = Array.Empty<RunInfo>();
    public IReadOnlyList<IReadOnlyList<bool>> StatusList { get; init; } = Array.Empty<IReadOnlyList<bool>>();
    public IReadOnlyList<DesignState> DesignStates { get; init; } = Array.Empty<DesignState>();
}
```
Follow this exact shape for any new `PerObjectVerdict`/`PerObjectVerdictResult` DTO: `init`-only properties, `IReadOnlyList<T>` with `Array.Empty<T>()` default.

---

### `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` (service, CRUD-read) — D-13/D-14/D-09/D-07

**Analog:** itself — `RunsQuery` (13-22), `GetRunsAsync` (40-151), `TryParseDesignState` (157-249)

**Cypher query pattern to copy** (raw string const, `MATCH...RETURN...ORDER BY`, all reads scoped by `graph:'ValidGraph'` + `$project`):
```csharp
private const string RunsQuery = """
    MATCH (run:ValidationRun {graph:'ValidGraph', project:$project})
    RETURN
        run.runId AS runId,
        coalesce(run.project, $project) AS project,
        run.createdAt AS createdAt,
        coalesce(run.rulesJson, '[]') AS rulesJson,
        run.statePayloadJson AS statePayloadJson
    ORDER BY run.createdAt DESC, run.runId ASC
    """;
```
**D-13's new query must add `evidenceEnvelopeJson` to the projection** — it is currently absent (per RESEARCH.md Pitfall 4, this is the root cause, not an index bug). Mirror `StandaloneStatesQuery`'s pattern (lines 30-38) for a second, additive, independently-degrading query on the same session:
```csharp
// Additive — wrap execution in try/catch, degrade rather than abort (see below)
private const string EvidenceQuery = """
    MATCH (run:ValidationRun {graph:'ValidGraph', project:$project, runId:$runId})
    RETURN run.evidenceEnvelopeJson AS evidenceEnvelopeJson
    """;
```

**Degrade-not-abort pattern to copy verbatim** (lines 112-131 — try/catch around a second cursor read on the same session, comment explains why):
```csharp
try
{
    var standaloneCursor = await session
        .RunAsync(StandaloneStatesQuery, new { project = connection.Project })
        .WaitAsync(QueryTimeout, cancellationToken);

    await standaloneCursor
        .ForEachAsync(record => { /* ... */ })
        .WaitAsync(QueryTimeout, cancellationToken);
}
catch (Exception)
{
    // Degrade, don't abort -- allStates already holds every
    // run-derived state collected above.
}
```
Apply this same shape to the new D-13 per-object query and to D-09's reader convergence — `TryParseDesignState`'s existing broad `catch (Exception)` (lines 237-248) must be preserved around any call-through to `DesignStatePayloadV2Serializer.Deserialize` (which throws, unlike this method's current internal parse).

**Deserialization pattern for `EvidenceEnvelope` (D-13's per-object read)** — no new type needed, per RESEARCH.md Pattern 2:
```csharp
var options = new JsonSerializerOptions(); // EvidenceEnvelope already carries JsonPropertyName + converters
var envelope = JsonSerializer.Deserialize<EvidenceEnvelope>(evidenceEnvelopeJson, options);
// envelope.Rows[i].ObjectId, envelope.Rows[i].CanonicalStatus directly usable
```

**Fabrication to delete (D-14)** — lines 73-75, remove entirely along with the `overallPass`/`objStateCount`-derived `statusList` construction:
```csharp
// DELETE — this is a missing feature, not a mapping bug (Correction 2)
var statusList = objStateCount > 0
    ? Enumerable.Repeat(overallPass, objStateCount).ToList()
    : new List<bool> { overallPass };
```

**Version-check pattern to add (D-07)** — `TryParseDesignState`'s v2-detection (lines 167-170) currently sniffs structure only; add an explicit `version` field check before the structural sniff, mirroring the serializer's own strict check (`DesignStatePayloadV2Serializer.cs:66-69`, shown below).

**Reader convergence (D-09)** — per RESEARCH.md Pitfall 2, the fix is likely: delete the inline `JsonSerializer.Deserialize<DesignState>` + manual `Parameters` backfill loop (lines 194-223) entirely, replace the v2 branch with a call to `DesignStatePayloadV2Serializer.Deserialize(statePayloadJson)`, wrapped in the existing broad `catch (Exception)` since the serializer throws on invalid input where this method currently returns `null`.

---

### `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` (utility, transform) — D-05/D-07/D-08

**Analog:** itself — `ObjStateDto` (472-483), `ToDto`/`FromDto`, `Deserialize`'s version check (66-69), the StateId sort (28/32/36)

**DTO member-addition pattern to copy** — `ObjStateDto` is a plain `sealed class` with nullable `init`-only string properties, no attributes (camelCase comes from the shared `JsonSerializerOptions.PropertyNamingPolicy`, line 11):
```csharp
private sealed class ObjStateDto
{
    public string? StateId { get; init; }
    public string? ObjectRef { get; init; }
    public string? Label { get; init; }
    public string? CapturedAtUtc { get; init; }
    public string? DgId { get; init; }
    // D-05 addition — optional-additive member, absence means "not recorded":
    public string? ClassIri { get; init; }
}
```
Add the matching field to `ToDto`/`FromDto` mapping functions (which live at lines 251-353 in this file) following the exact same null-coalescing style already used for `Label`/`DgId`.

**Existing strict version-check to mirror in `Neo4jValidGraphRepository.TryParseDesignState` (D-07 bundled fix)** — copy this exact fail-closed style:
```csharp
if (dto.Version != "2")
{
    throw new InvalidOperationException($"Unsupported state payload version. Expected '2', got '{dto.Version ?? "null"}'.");
}
```

**Canonical StateId sort already implemented (D-08 — no new code needed here, just confirmed as the contract)**:
```csharp
ObjStates = designState.ObjStates
    .OrderBy(o => o.StateId, StringComparer.Ordinal)
    .Select(ToDto)
    .ToList(),
```

---

### `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` (service, transform) — D-01/D-02/D-04

**Analog:** itself — sibling static `Compute*Id` methods and `HashToHex16` (all in this file)

**Existing hashing convention to follow for ANY new hash-producing function** (private helper, SHA-256 → 16-hex, called from every public `Compute*` method):
```csharp
private static string HashToHex16(string input)
{
    var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
    return Convert.ToHexString(hash)[..16];
}
```
**D-02 explicitly forbids adding a new hasher here for `canonicalStateHash`** — that must call `CanonicalJsonWriter.HashCanonical(JsonNode?)` instead (see Shared Patterns below). This file's existing methods are the pattern for **ID minting** (D-04's `ComputeObjectStateId` convergence target), not for the state-content hash.

**D-04 signature note (see RESEARCH.md Pitfall 1)** — `ComputeObjectStateId(string projectId, string objectInstanceId, string variableName)` (lines 57-61) has no natural 1:1 mapping onto `ObjectStateComponent`'s `(objectRef, label)` inputs. Planner must resolve via a documented mapping or an additive overload, following this file's existing doc-comment convention (see lines 52-56, 63-69, 90-96 for the style: one XML-doc paragraph stating the exact hash input formula and prefix).

---

### `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` (Grasshopper component, transform) — D-04

**Analog:** `DG/src/DG.Core/Services/DesignStateIdGenerator.cs`

**Code to delete** (lines 190-196 — the private duplicate D-04 removes):
```csharp
private static string ComputeObjStateId(string objectRef, string? label)
{
    var input = $"{objectRef}|{label ?? ""}";
    var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
    var hex = Convert.ToHexString(hash)[..16];
    return $"OS_{hex}";
}
```
Replace call sites with `DesignStateIdGenerator.ComputeObjectStateId(...)` (or the new additive overload, per the Pitfall-1 resolution above). Note: `#if GRASSHOPPER_SDK` conditional compilation guards this whole file (see the `#else`/empty-class fallback at lines 198-204) — any edit must stay inside the guarded block.

---

### `data-service/app.py` publish path (`:571-607`) (service/controller, CRUD-write) — D-15

**Analog:** itself — sibling single-property `SET` blocks at `:2136-2137` and `:2244-2245`, which already demonstrate the MERGE-then-independently-SET pattern this phase generalizes

**Current unconditional `SET` mixing immutable+mutable (the pattern to split)**:
```python
write_query(
    """
    MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
    SET
        run.speckleProjectId = $speckleProjectId,
        ...
        run.rulesJson = $rulesJson,
        run.statePayloadJson = $statePayloadJson,
        run.status = 'completed',
        run.ValidStatus = $validStatus,
        run.SendStatus = true,
        run.createdAt = $createdAt
    """,
    { ... },
)
```
**Existing sibling-SET precedent to follow for splitting into ON CREATE SET (immutable) vs SET (mutable)** — the codebase already writes to this same node independently at different times:
```python
# app.py:2136-2137 — independent single-property SET on the same MERGE key
MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
SET run.evidenceEnvelopeJson = $evidenceEnvelopeJson
```
D-15's fix: split the `:571-588` block into `ON CREATE SET` for `statePayloadJson`, `rulesJson`, `createdAt` (immutable snapshot) and plain `SET` for `status`, `ValidStatus`, `SendStatus` (mutable), using standard Cypher `ON CREATE SET ... SET ...` syntax on the same `MERGE`.

---

### `data-service/app.py` (`get_validation_entity_sets`, `:846-870`) (service, transform) — D-12

**Analog:** `data-service/evidence_contract.py:87-96` (`_ROLLUP_PRECEDENCE`)

**Current failed-wins dedup to replace**:
```python
if status == "failed":
    if dg_entity_id not in seen_failed:
        seen_failed[dg_entity_id] = entry
    seen_passed.pop(dg_entity_id, None)
elif status == "passed" and dg_entity_id not in seen_failed and dg_entity_id not in seen_passed:
    seen_passed[dg_entity_id] = entry
```
**Precedence table to import and use instead (never retype, per "Don't Hand-Roll")**:
```python
# Source: data-service/evidence_contract.py:87-96
_ROLLUP_PRECEDENCE: tuple[CanonicalStatus, ...] = (
    CanonicalStatus.ERROR,
    CanonicalStatus.FAILED,
    CanonicalStatus.INDETERMINATE,
    CanonicalStatus.UNSUPPORTED,
    CanonicalStatus.UNKNOWN,
    CanonicalStatus.NOT_EVALUATED,
    CanonicalStatus.NO_POPULATION,
    CanonicalStatus.PASSED,
)
```
D-12 requires this legacy function to be reconciled toward the shipped table (note: per D-10, this whole function is demoted to non-authoritative — D-13's C# envelope read is canonical; this Python fix is about not shipping two disagreeing precedences, not about restoring authority to `ValidationEntity`).

---

### `tools/de01/legs.py` (`run_leg_replay`, `~:747`) (tooling, request-response) — D-16

**Analog:** `tools/de01/report.py:69-149` (`_rows_by_pair`, `compare_legs`)

**Existing "typed absence, never silently skipped" idiom to mirror for the new state-hash comparison dimension**:
```python
# Source: tools/de01/report.py:108-149
for rule_id, object_id in ordered_pairs:
    per_leg: dict[str, dict[str, Any]] = {}
    statuses_seen: set[str] = set()
    for leg_name, pairs in per_leg_pairs.items():
        leg_rows = pairs.get((rule_id, object_id))
        if not leg_rows:
            per_leg[leg_name] = {"present": False}
            continue
        # ... never silently omits a leg from the comparison
```
D-16's new state-hash comparison should follow this same shape: report `{"present": False}` for any leg that doesn't produce a `canonicalStateHash` (per Open Question #2, legs not touching Design State, e.g. `data-service`/`dg-reasoner`, may legitimately report absence rather than being force-fit).

---

## Shared Patterns

### Canonical hashing (D-02) — mandatory reuse, no new hasher
**Source:** `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:98` (`HashCanonical`) and `data-service/canonical_json.py:180` (`hash_canonical`)
**Apply to:** the new `canonicalStateHash` computation wherever it lands (D-02 forbids inventing a second canonicalization)
```csharp
// Source: DG/tools/DG.De01Harness/Program.cs:284 — existing precedent, identical call shape to follow
var stateHashInput = BuildCanonicalDesignStateProjection(designState); // new function, D-02 discretion
var canonicalStateHash = CanonicalJsonWriter.HashCanonical(stateHashInput);
```
The `CanonicalizationVersion` constant (`CanonicalJsonWriter.cs:40`) must not be bumped by this phase unless the six normalization rules themselves change — D-02's projection is new *input*, not a new *rule*.

### Per-object verdict source (D-10/D-13) — `EvidenceEnvelope.Rows`
**Source:** `DG/src/DG.Core/Contracts/EvidenceEnvelope.cs:15-38` (`EvidenceRow`), `:78-79` (`Rows`)
**Apply to:** any new C# per-object read path — no new DTO/reader type needed, `JsonSerializer.Deserialize<EvidenceEnvelope>` is sufficient (Pattern 2, confirmed by direct inspection: every property already carries `[JsonPropertyName]`).

### Additive-not-breaking (project house style)
**Source:** Phase 823 `shaclReportJson`, Phase 38 nullable `reinstateParameterId`, this phase's own D-03/D-07/D-13
**Apply to:** `ObjStateDto.ClassIri` (D-05), `IValidGraphRepository`'s new method (D-13) — old callers/payloads keep working, absence means "not recorded, never an error."

### Degrade-not-abort around a second Cypher read on the same session
**Source:** `Neo4jValidGraphRepository.cs:112-131` (the `StandaloneStatesQuery` try/catch)
**Apply to:** D-13's new evidence-envelope query, added on the same session as `RunsQuery` without risking the whole `GetRunsAsync` response.

### Rollup precedence — single source of truth
**Source:** `DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs:25-35` (C#), `data-service/evidence_contract.py:87-96` (Python)
**Apply to:** D-12's Python reconciliation — import/reference, never retype a third table.

## No Analog Found

None — every file this phase touches already exists and has an immediately-adjacent in-file pattern to extend (this is a pure-consolidation phase per RESEARCH.md: "zero new packages, zero new frameworks, zero new services"). The one genuinely new artifact — the D-17 sibling fixture file — has a direct structural precedent (`fixtures/golden/parser/`, `fixtures/golden/canonical-vectors.json`) rather than a code analog, listed in the classification table above.

## Metadata

**Analog search scope:** `DG/src/DG.Core/{Data,Serialization,Models,Services,Contracts}`, `DG/src/DG.Grasshopper/Components`, `data-service/{app.py,evidence_contract.py,canonical_json.py}`, `tools/de01/{legs.py,report.py}`, `fixtures/golden/`
**Files scanned:** 10 target files read in full or by targeted section (all confirmed against CONTEXT.md's `<canonical_refs>` line numbers, cross-verified 2026-09-21)
**Pattern extraction date:** 2026-09-21
