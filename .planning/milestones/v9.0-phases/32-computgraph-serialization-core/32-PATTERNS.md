# Phase 32: Computgraph Serialization Core - Pattern Map

**Mapped:** 2026-07-12
**Files analyzed:** 8 (model group counted as 1 unit of 7 classes/enums + parser + serializer + extractor + fixture)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `DG/src/DG.Core/Models/Computgraph/CgObject.cs`, `CgAlgorithm.cs`, `CgProcedure.cs`, `CgPattern.cs`, `CgParameter.cs`, `CgInterface.cs`, `CgNode.cs`, `CgWire.cs` | model | transform (plain POCOs) | `DG/src/DG.Core/Models/ObjState.cs`, `DesignStateParameter.cs`, `ParamState.cs` | exact |
| `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` | utility (parser) | transform | `DG/src/DG.Core/Parsing/SwrlRuleParser.cs` | exact |
| `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs` | service (serializer) | transform (JSON in/out) | `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` | exact |
| `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` | component (GH extractor) | transform (GH_Document → POCOs) | `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` (structure/guards only — extractor is not a `GH_Component`, so treat as partial match) | role-match |
| `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` + accompanying xUnit test | test (fixture + round-trip test) | transform | `DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs` | exact |

## Pattern Assignments

### `DG/src/DG.Core/Models/Computgraph/*.cs` (model, transform)

**Analog:** `DG/src/DG.Core/Models/ObjState.cs`, `DG/src/DG.Core/Models/DesignStateParameter.cs`, `DG/src/DG.Core/Models/ParamState.cs`

**Namespace + shape convention** (`ObjState.cs` lines 1-21):
```csharp
namespace DG.Core.Models;

public class ObjState
{
    public string StateId { get; init; } = string.Empty;
    public string ObjectRef { get; init; } = string.Empty;
    public object? Geometry { get; init; }
    public string? Label { get; init; }
    public string? ClassIri { get; init; }
    public DateTimeOffset CapturedAtUtc { get; init; }
}
```
- Plain POCO, `init`-only auto-properties, non-nullable strings default to `string.Empty`, nullable reference types for optional fields, XML doc comments only where a property's semantics need clarification (see `ClassIri` comment).
- No GH dependency, no attributes — the model is decoupled from serialization (DTOs live separately, see Serializer pattern below). `Cg*` classes should follow the same style: `CgObject { Name, ClassIri? }`, `CgAlgorithm { Index, Name }`, etc.

**Enum convention** (`DesignStateParameter.cs` lines 3-8):
```csharp
namespace DG.Core.Models;

public enum DesignStateParameterType
{
    Number,
    Integer,
    Boolean,
}
```
- Use this exact pattern for `ParamKind` (`Variable, Constant, Emergent`), `ParamDataType` (`Float, Integer, Text, Boolean, Geometry`), `IfaceType` (`Input, Output`) — separate small top-level enum per concept, PascalCase members matching CONTEXT.md wording exactly (not the OWL individual names).

**Composite/collection-holder convention** (`ParamState.cs`, referenced from `DesignStatePayloadV2Serializer.cs` line 262 area) — a state that owns a list of typed children uses `List<T>` with default empty collection, e.g. `public List<DesignStateParameter> Parameters { get; init; } = new();`. Apply this for `CgProcedure.Patterns`, `.Parameters`, `.Interfaces` and `CgPattern.Patterns` (nested).

---

### `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` (utility, transform)

**Analog:** `DG/src/DG.Core/Parsing/SwrlRuleParser.cs` (full file read, 153 lines)

**Imports + static-class shape** (lines 1-12):
```csharp
using System.Globalization;
using System.Text.RegularExpressions;
using DG.Core.Models;

namespace DG.Core.Parsing;

public static class SwrlRuleParser
{
    private static readonly Regex AtomRegex = new(
        "^(?<predicate>[^\\(]+)\\((?<args>.*)\\)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);
```
- Parser is a `static class` with `static readonly Regex` fields (`Compiled | CultureInvariant`), not an instance/DI service. `CanvasAnnotationParser` should follow: one compiled regex per grammar rule (object/algorithm/procedure/pattern/variable/constant/emergent/interface), matching CONTEXT.md's grammar (§4 of RESEARCH.md).

**Public entry point + guard clauses** (lines 13-24):
```csharp
public static ParsedSwrlRule Parse(string swrlExpression)
{
    if (string.IsNullOrWhiteSpace(swrlExpression))
    {
        throw new ArgumentException("SWRL expression cannot be empty.", nameof(swrlExpression));
    }
    ...
```
- Single public `Parse(...)` method returning a result object holding a strongly-typed list; guard clauses at top throw `ArgumentException`/`FormatException` for hard-invalid input. **Key divergence for Computgraph:** CONTEXT.md decision #2 says "anything non-conforming → untagged set. The parser never guesses" — so `CanvasAnnotationParser` should NOT throw for unmatched names; it should route non-matches into an `Untagged` collection and only throw for truly malformed calling contract (e.g. null document). Mirror the SWRL parser's *return-a-result-object* shape, not its throw-on-mismatch behavior.

**Regex dispatch + private per-atom parse method** (lines 46-80, `ParseAtoms`):
```csharp
private static void ParseAtoms(string chain, AtomSide side, ICollection<Atom> target)
{
    var atomTexts = chain.Split('^', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
    var order = 1;
    foreach (var atomText in atomTexts)
    {
        var match = AtomRegex.Match(atomText);
        if (!match.Success) { throw new FormatException($"Invalid SWRL atom: {atomText}"); }
        var predicate = match.Groups["predicate"].Value.Trim();
        ...
```
- Iterate raw tokens (scribble text / group nickname), run through ordered regex candidates, build typed sub-objects with deterministic ids (`$"{side}_{order}"` — analogous to CONTEXT.md's `cg:<alg>:<kind>:<conventionName>` id scheme). Use `match.Groups["name"].Value.Trim()` extraction style throughout.

**Tolerant-variant handling precedent** — none exists verbatim in SwrlRuleParser (it throws on mismatch), so the `Emg|Emr` tolerance + warning-emission is a new pattern for this codebase. Model warnings as a `List<string>` field on the parser's result type, consistent with `cgContextJson v1`'s `warnings: string[]` (RESEARCH.md §5).

---

### `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs` (service, transform)

**Analog:** `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` (read lines 1-120 of ~500)

**Imports + JsonSerializerOptions convention** (lines 1-13):
```csharp
using System.Globalization;
using System.Text.Json;
using DG.Core.Models;

namespace DG.Core.Serialization;

public static class DesignStatePayloadV2Serializer
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };
```
- Static class, single shared `JsonSerializerOptions` (camelCase, not indented). `ComputgraphContextSerializer` should reuse this exact options block — CONTEXT.md explicitly says "same conventions as DesignStatePayloadV2Serializer".

**Serialize: domain model → DTO → JSON** (lines 15-42):
```csharp
public static string Serialize(DesignState designState)
{
    ArgumentNullException.ThrowIfNull(designState);
    ValidateDesignState(designState);

    var dto = new DesignStatePayloadV2Dto
    {
        Version = "2",
        StateId = designState.StateId,
        ...
        ObjStates = designState.ObjStates.OrderBy(o => o.StateId, StringComparer.Ordinal).Select(ToDto).ToList(),
        ...
    };
    return JsonSerializer.Serialize(dto, Options);
}
```
- Deterministic ordering (`OrderBy(..., StringComparer.Ordinal)`) before serializing collections — apply to `algorithms`, `procedures`, `patterns`, `parameters`, `interfaces`, `nodes`, `wires` for stable diffs/fixture comparisons. Domain objects are never serialized directly — always map to a private nested `*Dto` record/class first (`ToDto`/`FromDto` static private methods per entity, see lines 251-503 for the full DTO set). `ComputgraphContextSerializer` needs an analogous internal DTO tree mirroring the `cgContextJson v1` envelope (RESEARCH.md §5) with a top-level `schemaVersion: "cg-context-1"` field playing the same role as `Version = "2"`.

**Deserialize: JSON → DTO → domain model with version + shape guards** (lines 44-100):
```csharp
public static DesignState Deserialize(string json)
{
    if (string.IsNullOrWhiteSpace(json)) { throw new InvalidOperationException("Design state v2 payload must not be empty."); }
    DesignStatePayloadV2Dto? dto;
    try { dto = JsonSerializer.Deserialize<DesignStatePayloadV2Dto>(json, Options); }
    catch (JsonException ex) { throw new InvalidOperationException("Design state v2 payload is not valid JSON.", ex); }
    if (dto is null) { throw new InvalidOperationException("Design state v2 payload is empty."); }
    if (dto.Version != "2") { throw new InvalidOperationException($"Unsupported state payload version. Expected '2', got '{dto.Version ?? "null"}'."); }
    ...
    ValidateDeserialized(designState);
    return designState;
}
```
- Version-check-first pattern — `ComputgraphContextSerializer.Deserialize` must check `dto.SchemaVersion == "cg-context-1"` before anything else and throw `InvalidOperationException` with the same message shape, satisfying CONTEXT.md's "versioned contract... breaking changes require a version bump."
- Wrap `JsonException` in `InvalidOperationException`, never let raw `JsonException` escape.
- Separate `Validate*` private methods run both before serialize (`ValidateDesignState`) and after deserialize (`ValidateDeserialized`) — mirror this for required fields (`documentId`, `fileName`, entity ids).

**Error handling pattern** — `InvalidOperationException` for all serializer-level failures (empty payload, bad version, missing required field); `FormatException`/`ArgumentException` reserved for parser-level failures (see SwrlRuleParser). Keep this split consistent in the new files.

---

### `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` (GH extractor, transform)

**Analog:** `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` (partial — structural/guard patterns only; this analog is a `GH_Component`, the extractor is a plain traversal class, so treat this as a role-match not exact)

**Conditional compilation wrapper** (line 1, and repo-wide convention documented in `DG_OBSIDIAN/knowledge/patterns/Conditional compilation guards Grasshopper SDK availability.md`):
```csharp
#if GRASSHOPPER_SDK
using DG.Core.Models;
...
namespace DG.Grasshopper.Components;

public sealed class ValidatorComponent : GH_Component
{
    ...
}
#endif
```
- Every GH-dependent file starts with `#if GRASSHOPPER_SDK`, ends with matching `#endif`, and per CONTEXT.md constraint the `#else` branch needs an **empty stub** (this is stricter than `ValidatorComponent.cs`, which has no `#else` — confirm the stub requirement against the repo's `Conditional compilation guards Grasshopper SDK availability.md` note before implementing).

**Input reading + null/empty guards** (lines 45-76 of `ValidatorComponent.cs`):
```csharp
object? ruleInput = null;
if (!da.GetData(0, ref ruleInput))
{
    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Rule input is required.");
    return;
}
var rule = GhCastingHelpers.TryRule(ruleInput);
if (rule is null)
{
    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Could not cast Rule input.");
    return;
}
```
- `CanvasContextExtractor` traverses `GH_Document.Objects` directly (not `IGH_DataAccess`), so this exact snippet won't transfer verbatim, but the **guard-and-continue-with-warning** philosophy applies: missing/malformed scribbles or unparseable groups should not throw — collect into `untagged`/`warnings`, matching CONTEXT.md's "never guesses" rule. `GhCastingHelpers.cs` (same directory) is the pattern to follow for any GH-type → POCO casting helpers this extractor needs (e.g. casting `IGH_Param` sources to wire endpoints).

**Category/subcategory registration convention** (`ValidatorComponent.cs` line 16, `DgComponentCategory`): only relevant if the extractor is ever exposed as a component; if it stays a pure traversal class invoked by a thin component, this pattern is not needed — flag for planner to decide file boundary (traversal logic in `CanvasContextExtractor.cs` vs. a thin wrapping `GH_Component` in `Components/`).

---

### `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` + xUnit round-trip test (test, transform)

**Analog:** `DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs` (read lines 1-70 of file)

**Imports + test class shape** (lines 1-9):
```csharp
using System.Text.Json;
using DG.Core.Models;
using DG.Core.Serialization;
using DG.Core.Services;

namespace DG.Tests;

public sealed class DesignStatePayloadV2SerializerTests
{
```

**Round-trip test pattern** (lines 10-34):
```csharp
[Fact]
public void SerializeDeserialize_RoundTrip_ShouldPreserveAllThreeLists()
{
    var state = CreateDesignState();
    var json = DesignStatePayloadV2Serializer.Serialize(state);
    var roundTrip = DesignStatePayloadV2Serializer.Deserialize(json);

    Assert.Equal(state.StateId, roundTrip.StateId);
    Assert.Equal(state.ObjStates.Count, roundTrip.ObjStates.Count);
    ...
}
```
- Naming convention `MethodUnderTest_Scenario_ExpectedResult`. A private `CreateDesignState()` builder method constructs the fixture in-code (not loaded from a file in this analog) — but CONTEXT.md explicitly wants a **checked-in JSON fixture** (`Fixtures/frame-cg-context.json`), so the new test should additionally `File.ReadAllText` the fixture and assert `ComputgraphContextSerializer.Deserialize(fixtureJson)` produces the expected named entities (`dg:Object_Frame`, `dgc:Algorithm_1`, `Proc_11`, `Proc_12`, etc. per CONTEXT.md decision #5). Check whether a `Fixtures/` directory already exists under `DG/tests/DG.Tests/` (not observed in current listing — likely new) and how the `.csproj` copies fixture files to output (`DG.Tests.csproj` — check for `<None Include="Fixtures/**" CopyToOutputDirectory="PreserveNewest" />` style entries before adding the file).

**Typed-value assertion pattern** (lines 44-47): `Assert.Contains(collection, predicate)` for verifying specific typed entries survived round-trip — use this for asserting specific `CgParameter` entries (kind/dataType/domain) in the fixture-based test.

## Shared Patterns

### Namespace/DTO separation
**Source:** `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` (whole file structure)
**Apply to:** `ComputgraphContextSerializer.cs`
Domain models (`DG.Core.Models.Computgraph.*`) are never decorated with `[JsonPropertyName]` or serialization attributes — the serializer owns a private DTO tree and maps both directions. This keeps `Cg*` models GH-free and serializer-agnostic per CONTEXT.md decision #1 ("zero Grasshopper dependencies").

### Conditional compilation
**Source:** `DG_OBSIDIAN/knowledge/patterns/Conditional compilation guards Grasshopper SDK availability.md`, `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` line 1
**Apply to:** `CanvasContextExtractor.cs` only
`#if GRASSHOPPER_SDK ... #endif` wraps the entire file; per CONTEXT.md constraint, add an `#else` stub (check the Obsidian note for the exact stub shape used elsewhere in the repo before writing it — this may differ slightly from `ValidatorComponent.cs`, which has no visible `#else`).

### Deterministic ordering before serialization
**Source:** `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` lines 27-38
**Apply to:** `ComputgraphContextSerializer.cs` — order `algorithms` by index, `procedures`/`patterns`/`parameters`/`interfaces` by their `NN`/id, `nodes`/`wires` by instance/source GUID, so fixture JSON and test assertions are stable across runs.

### Error-handling split (parser throws vs. serializer wraps)
**Source:** `SwrlRuleParser.cs` (throws `FormatException`/`ArgumentException` for structurally invalid input) vs. `DesignStatePayloadV2Serializer.cs` (wraps everything in `InvalidOperationException`)
**Apply to:** Both new files — but note CONTEXT.md's explicit divergence: `CanvasAnnotationParser` must NOT throw for unrecognized annotation text (route to untagged + warning instead); it should only throw for null/malformed input at the API boundary (e.g., null `GH_Document`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `DG/src/DG.Core/Models/Computgraph/CgWire.cs` | model | graph-edge | No existing model represents a graph edge (wire) with source/target member+param references; nearest is `ConnectionInfo.cs` — worth a quick look during planning but not read in this pass; treat as a new shape, follow the general POCO convention above |
| `Untagged-set / warning-collection sub-pattern in CanvasAnnotationParser` | utility | transform | No existing parser in the codebase returns a "soft failure" bucket instead of throwing — this is a new pattern for DG.Core, design it fresh using `List<string>` for warnings and a dedicated `Untagged` collection type, consistent with `cgContextJson v1`'s schema (RESEARCH.md §5) |

## Metadata

**Analog search scope:** `DG/src/DG.Core/Models/`, `DG/src/DG.Core/Parsing/`, `DG/src/DG.Core/Serialization/`, `DG/src/DG.Grasshopper/Components/`, `DG/tests/DG.Tests/`
**Files scanned:** ~55 (directory listings) + 6 read in full/partial (ObjState.cs, DesignStateParameter.cs, SwrlRuleParser.cs, DesignStatePayloadV2Serializer.cs [partial], ValidatorComponent.cs [partial], DesignStatePayloadV2SerializerTests.cs [partial])
**Pattern extraction date:** 2026-07-12
