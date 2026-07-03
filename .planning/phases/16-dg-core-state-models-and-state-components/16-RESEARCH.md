# Phase 16: DG.Core State Models and State Components — Research

**Researched:** 2026-07-04
**Domain:** C# pure-logic state models (DG.Core) + Grasshopper capture/compose components (DG.Grasshopper)
**Confidence:** HIGH

## Summary

Phase 16 adds four pure-logic C# models in DG.Core (`ObjState`, `ParamState`, `PropState`, `DesignState`) with a deterministic ID generator, a versioned v2 serializer (`statePayloadJson`), and four Grasshopper components that capture and compose these states on the canvas. Existing v3.0 scaffolding (`DefState`, `ObjectState`, `ObjectInstance`) is deleted — confirmed zero call sites across all non-documentation files. The v2.0 `DesignStateComponent` (dynamic-parameter capture) is renamed to `PARAMETER STATE` with a new GUID, and its core capture logic carries forward unchanged. The v1 `DesignStateJsonSerializer` is either replaced or reworked into the v2 versioned-envelope serializer (Claude's discretion per CONTEXT.md).

**Primary recommendation:** Four new `DG.Core.Models` files (ObjState, ParamState, PropState, DesignState), one reworked `DG.Core.Serialization` serializer (v2 versioned envelope), five `DesignStateIdGenerator` method additions/renames, one component rename (DesignStateComponent -> ParameterStateComponent, new GUID), three new GH components (ObjectStateComponent, PropertyStateComponent, DesignStateComponent), new PublicTypes wrappers for all four state types, three model deletions. All within existing codebase patterns — no new infrastructure.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- D-01: DESIGN STATE is an aggregate — all wired ObjStates + ParamStates + PropStates fold into one DesignState snapshot
- D-02: The three DESIGN STATE inputs are independent bags — no cross-index alignment
- D-03: Index-mismatch guard lives in the parallel-list leaf components (OBJECT STATE, PROPERTY STATE), not in DESIGN STATE
- D-04: DesignState.StateId = deterministic hash over sorted member StateIds (SHA-256 -> 16-char hex, DS_-prefixed)
- D-05: statePayloadJson v2 versioned envelope: {version, stateId, capturedAtUtc, objStates[], paramStates[], propStates[]}
- D-06: Clean break — no v1 deserialization fallback
- D-07: New/reworked serializer class in DG.Core.Serialization
- D-08: PropValue = typed Number/Integer/Boolean scalar (same type system as DesignStateParameter)
- D-09: Rule and DataProperty stored as plain string references (IRIs)
- D-10: PropState is rule-scoped — one Rule + one DataProperty + one value per PropState
- D-11: PropState.StateId = PS_ + SHA-256(Rule IRI + DataProperty IRI + PropValue)
- D-12: Delete DefState.cs, ObjectState.cs, ObjectInstance.cs — zero call sites confirmed
- D-13: Rename DESIGN STATE -> PARAMETER STATE (new GUID)
- D-14: Rename DesignStateSnapshot -> ParamState model (same fields)
- D-15: DesignStateIdGenerator adapted: ComputeDefStateId -> ComputeParamStateId, add ComputePropStateId, remove ComputeObjectInstanceId

### Claude's Discretion
- Exact per-entity serialized field mapping within the v2 envelope (field names, ordering)
- Whether v2 serializer is a new `DesignStatePayloadSerializer` class or a rework of existing `DesignStateJsonSerializer`
- Error message wording for index-mismatch guards (follow ErrorMessageTemplates What+Where+How-to-fix pattern)
- Whether `OI_` prefix is removed with ObjectInstance deletion or kept as reserved
- Internal list ordering within the DesignState model (preserve wiring order vs sorted)

### Deferred Ideas (OUT OF SCOPE)
- None for Phase 16.
- **Cross-phase notes (not scope changes):** Phase 18 owns ValidStatus population semantics, VariableBinder deletion, data-service v2 adaptation.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | ObjState model (Object reference, GeoRef, Label) replaces ObjectState scaffolding | ElementRef pattern exists (DgEntityId+Geometry+DisplayName). ObjState wraps ObjectRef + Geometry + Label from ElementRef. ID via ComputeObjectStateId (reuse existing, OS_ prefix unchanged). |
| CORE-02 | ParamState model (typed Number/Integer/Boolean parameters, deterministic StateId) adapted from DesignStateSnapshot | DesignStateSnapshot has exact shape: StateId+CapturedAtUtc+Collection<DesignStateParameter>. ParamState is a rename (D-14). ID via ComputeParamStateId (renamed from ComputeDefStateId). |
| CORE-03 | PropState model (Rule reference, DataProperty reference, PropValue) | New model. Rule/DataProperty = plain string IRIs (D-09). PropValue reuses DesignStateParameter's typed-nullable pattern (D-08). ID via new ComputePropStateId (D-11). |
| CORE-04 | DesignState composition model aggregates ObjState/ParamState/PropState with per-class ID prefixes | Aggregate with three internal lists. StateId = deterministic hash of sorted member StateIds (D-04). Uses DesignStateIdGenerator.ComputeDesignStateId (new method). |
| CORE-05 | statePayloadJson v2 serializes 3-part composition with lossless round-trip | v1 serializer pattern (DTO, camelCase, ISO 8601, validation) adapted to versioned envelope (D-05). New/resr class, no v1 fallback (D-06/D-07). |
| GHST-01 | OBJECT STATE composes Object+Geometry+Label into ObjState | Fixed-input GH component. GhCastingHelpers.TryElementRef pattern for unwrapping inputs. Output type: DG.ObjState via PublicTypes wrapper. |
| GHST-02 | PARAMETER STATE captures Parameters list into ParamState (variable-input, deterministic StateId) | Renames v2.0 DesignStateComponent. IGH_VariableParameterComponent kept. Same UnwrapScalar/BuildParameter/BuildSnapshot logic. New GUID, new output type DG.ParamState. |
| GHST-03 | PROPERTY STATE Compose Rule+DataProperty+PropValue into PropState | Fixed-input component. Rule input via GhCastingHelpers.TryRule. DataProperty as string. PropValue as typed scalar. Output: DG.PropState. Rule+DataProperty length guard per D-03. |
| GHST-04 | DESIGN STATE composes many ObjState+ParamState+PropState into DesignState | Fixed-list-input component (3 inputs, each list). No cross-length guard (D-03). Output: DG.DesignState via wrapper. StateId = aggregated hash (D-04). |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| State model definitions (ObjState, ParamState, PropState, DesignState) | DG.Core | — | Pure data contracts, no GH dependency. Multi-targets net7.0+net9.0. |
| Deterministic ID generation (SHA-256 hashing) | DG.Core | — | Pure logic, testable without GH SDK. Already established pattern in DesignStateIdGenerator. |
| State serialization (statePayloadJson v2) | DG.Core.Serialization | — | Pure logic (System.Text.Json). No GH dependency. |
| Grasshopper component parameters capture | DG.Grasshopper | DG.Core | GH-specific unwrapping (ScriptVariable), variable-parameter pattern. Consumes DG.Core models. |
| Cross-component type transport (PublicTypes) | DG.Grasshopper | DG.Core | Public wrappers inherit from Core models. GH data flow requires wirable types. |
| Index-mismatch guard (parallel-list validation) | DG.Grasshopper | — | Validation is component-level runtime message (GH_RuntimeMessageLevel.Error). No Core logic needed. |
| Error message templates | DG.Core.Services | — | Static What+Where+How-to-fix pattern. Extended with new messages for index-mismatch. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| .NET (multi-target) | net7.0;net9.0 | Project TFM | Existing DG.Core.csproj target. Matches Rhino 8 / GH SDK requirements. |
| System.Text.Json | Built-in | JSON serialization | Existing v1 serializer uses it. No dependency change needed. |
| System.Security.Cryptography.SHA256 | Built-in | Deterministic StateId hashing | Already used by DesignStateIdGenerator. No dependency change needed. |
| xUnit | 2.x | Unit testing | Existing test project pattern (DesignStateIdGeneratorTests, DesignStateJsonSerializerTests). |
| Grasshopper SDK | 8.x | GH component API | Conditional compilation (#if GRASSHOPPER_SDK). Referenced via NuGet or local GH install. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GhCastingHelpers | Internal static | Type unwrapping (Unwrap<T>, TryRule, TryElementRef) | All GH components that accept DG.Core type inputs |
| ErrorMessageTemplates | Internal static | Standardized error messages | All GH components for user-facing errors |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| System.Text.Json | Newtonsoft.Json | Existing v1 already uses System.Text.Json. Consistent. No need to add dependency. |
| Static DesignStateIdGenerator | Instance-based with DI | Static is simpler, testable, existing pattern. No DI container in Grasshopper context. |
| New serializer class | Rework existing DesignStateJsonSerializer | CONTEXT.md D-07 leaves both open (Claude's discretion). V1 flat DTO is fundamentally different from v2 versioned envelope. New class is cleaner separation. |

**Installation:**
No new NuGet packages. Existing project dependencies suffice.

**Version verification:**
- .NET SDK: `dotnet --version` >= 7.0
- xUnit: referenced via NuGet in `DG/tests/DG.Tests/DG.Tests.csproj`

## Package Legitimacy Audit

> **No external packages are introduced.** All code is within existing project boundaries (DG.Core, DG.Grasshopper, DG.Tests). No npm/PyPI/crates packages to audit.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious (SUS):** none

## Architecture Patterns

### System Architecture Diagram

```
                         Phase 16 Scope (C# Only)
    ┌─────────────────────────────────────────────────────────────────┐
    │                         DG.Core                                │
    │  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
    │  │ ObjState     │  │ ParamState      │  │ PropState        │  │
    │  │  - StateId   │  │  - StateId      │  │  - StateId      │  │
    │  │  - ObjectRef │  │  - CapturedAtUtc│  │  - RuleIri      │  │
    │  │  - Geometry  │  │  - Parameters   │  │  - DataPropIri  │  │
    │  │  - Label     │  │                  │  │  - PropValue    │  │
    │  └──────┬───────┘  └────────┬────────┘  └────────┬─────────┘  │
    │         │                   │                     │            │
    │         └───────────────────┼─────────────────────┘            │
    │                             ▼                                  │
    │                   ┌──────────────────┐                         │
    │                   │  DesignState     │                         │
    │                   │  - StateId (DS_) │                         │
    │                   │  - ObjStates[]   │                         │
    │                   │  - ParamStates[] │                         │
    │                   │  - PropStates[]  │                         │
    │                   └────────┬─────────┘                         │
    │                            │                                    │
    │                   ┌────────▼─────────┐                         │
    │                   │ DesignStateIdGen │                         │
    │                   │  ComputeParam..  │                         │
    │                   │  ComputeObject.. │                         │
    │                   │  ComputeProp..   │                         │
    │                   │  ComputeDesign.. │                         │
    │                   └──────────────────┘                         │
    │  ┌────────────────────────────────────────────┐                │
    │  │ DG.Core.Serialization                     │                │
    │  │  statePayloadJson v2 serializer            │                │
    │  │  {version, stateId, capturedAtUtc,         │                │
    │  │   objStates[], paramStates[], propStates[]}│                │
    │  └────────────────────────────────────────────┘                │
    └─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                       DG.Grasshopper                            │
    │  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐   │
    │  │ OBJECT STATE │  │PARAMETER STATE │  │ PROPERTY STATE   │   │
    │  │  in:Object   │  │ (IGH_Variable) │  │  in:Rule         │   │
    │  │  in:Geometry │  │  in:Parameters │  │  in:DataProperty │   │
    │  │  in:Label    │  │  out:ParamState│  │  in:PropValue    │   │
    │  │  out:ObjState│  └────────┬───────┘  │  out:PropState   │   │
    │  └──────┬───────┘           │           └────────┬─────────┘   │
    │         │                   │                     │            │
    │         └───────────────────┼─────────────────────┘            │
    │                             ▼                                  │
    │                    ┌──────────────────┐                        │
    │                    │  DESIGN STATE    │                        │
    │                    │  in:ObjState[]   │                        │
    │                    │  in:ParamState[] │                        │
    │                    │  in:PropState[]  │                        │
    │                    │  out:DesignState │                        │
    │                    └──────────────────┘                        │
    │                                                                 │
    │  ┌──────────────┐                                               │
    │  │ PublicTypes  │                                               │
    │  │ DG.ObjState  │  (wrapper over Core model)                   │
    │  │ DG.ParamState│                                               │
    │  │ DG.PropState │                                               │
    │  │ DG.DesignState│                                              │
    │  └──────────────┘                                               │
    └─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
DG/src/DG.Core/Models/
├── ObjState.cs                  # NEW — replaces ObjectState scaffolding
├── ParamState.cs                # Renamed from DesignStateSnapshot
├── PropState.cs                 # NEW
├── DesignState.cs               # NEW — aggregate composition
├── (delete) DefState.cs         # D-12
├── (delete) ObjectState.cs      # D-12
├── (delete) ObjectInstance.cs   # D-12
└── DesignStateSnapshot.cs       # Rename to ParamState.cs or delete after rename

DG/src/DG.Core/Services/
└── DesignStateIdGenerator.cs    # Modified — rename + add methods

DG/src/DG.Core/Serialization/
└── DesignStateJsonSerializer.cs # New v2 OR replace with DesignStatePayloadV2Serializer.cs

DG/src/DG.Grasshopper/Components/
├── (rename) DesignStateComponent.cs → ParameterStateComponent.cs  # D-13, new GUID
├── ObjectStateComponent.cs       # NEW — GHST-01
├── PropertyStateComponent.cs     # NEW — GHST-03
├── DesignStateComponent.cs       # NEW — GHST-04 (different from v2.0 DESIGN STATE)
└── GhCastingHelpers.cs           # Extend with new unwrappers

DG/src/DG.Grasshopper/Properties/
├── ObjectState24.png             # NEW icon
├── ParameterState24.png          # NEW icon (or reuse DesignState24.png with rename)
├── PropertyState24.png           # NEW icon
└── DesignState24.png             # Update or new icon

DG/src/DG.Grasshopper/PublicTypes.cs   # Extend with 4 new wrappers

DG/tests/DG.Tests/
├── DesignStateIdGeneratorTests.cs      # Update — rename ComputeDefStateId calls, add Prop/Design state tests
├── DesignStateJsonSerializerTests.cs   # Update — add v2 serializer tests
├── ObjStateModelTests.cs              # NEW
├── ParamStateModelTests.cs            # NEW
├── PropStateModelTests.cs             # NEW
└── DesignStateModelTests.cs           # NEW
```

### Pattern 1: Deterministic StateId via SHA-256

Every state entity gets a content-addressed ID — identical inputs produce identical StateId. This enables dedup across validation runs (MERGE by StateId+project).

```csharp
// Source: DG/src/DG.Core/Services/DesignStateIdGenerator.cs (existing pattern)
private static string HashToHex16(string input)
{
    var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
    return Convert.ToHexString(hash)[..16];
}
```

New methods needed:
- `ComputeParamStateId(IEnumerable<DesignStateParameter>)` — rename of existing `ComputeDefStateId`, same logic
- `ComputePropStateId(string ruleIri, string dataPropertyIri, string propValueLex)` — new: `$"{ruleIri}|{dataPropertyIri}|{propValueLex}"`, PS_ prefix
- `ComputeDesignStateId(IEnumerable<string> memberStateIds)` — new: sort + concatenate + hash, DS_ prefix

DesignState.StateId input: sorted OS_ + PS_ + DS_ member StateIds concatenated (D-04).

### Pattern 2: v1-to-v2 Serializer Evolution

The v1 serializer uses a flat `SnapshotDto` with `stateId`, `capturedAtUtc`, and `parameters[]`. The v2 envelope adds `version` discriminator and splits parameters into three typed arrays:

```csharp
// v2 envelope DTO pattern (extends v1 approach)
private sealed class DesignStatePayloadV2Dto
{
    public string Version { get; init; } = "2";
    public string? StateId { get; init; }
    public string? CapturedAtUtc { get; init; }
    public List<ObjStateDto>? ObjStates { get; init; }
    public List<ParamStateDto>? ParamStates { get; init; }
    public List<PropStateDto>? PropStates { get; init; }
}
```

Validation follows the same pattern: check required fields after deserialization, throw `InvalidOperationException` with descriptive messages.

### Pattern 3: GH Component with IGH_VariableParameterComponent (PARAMETER STATE)

The existing `DesignStateComponent` (renamed to PARAMETER STATE) demonstrates the dynamic-input pattern:

```csharp
// Source: DG/src/DG.Grasshopper/Components/DesignStateComponent.cs
public sealed class ParameterStateComponent : GH_Component, IGH_VariableParameterComponent
{
    // CanInsertParameter: only inputs
    // CanRemoveParameter: only inputs, keep >= 1
    // CreateParameter: new Param_GenericObject { Optional = true }
    // DestroyParameter: always true
    // VariableParameterMaintenance: no-op
    
    // SolveInstance iterates Params.Input, derives ParameterId from NickName,
    // unwraps scalars via UnwrapScalar, builds DesignStateParameter via BuildParameter,
    // creates ParamState with deterministic StateId
}
```

### Pattern 4: Fixed-Input Component with PublicType Wrapper

OBJECT STATE and PROPERTY STATE are fixed-input components. They output public wrappers defined in `PublicTypes.cs`:

```csharp
// Source: PublicTypes.cs (existing pattern)
public class ParamState : DG.Core.Models.ParamState { }
public class ObjState : DG.Core.Models.ObjState { }
public class PropState : DG.Core.Models.PropState { }
public class DesignState : DG.Core.Models.DesignState { }
```

Helps:
- `GhCastingHelpers.Unwrap<DG.ObjState>(input)` — pattern for reading from inputs
- `da.SetData(0, new DG.ObjState { ... })` — pattern for writing to outputs

### Anti-Patterns to Avoid

- **Adding GH SDK dependency to DG.Core models**: Models are pure logic. Keep `#if GRASSHOPPER_SDK` out of new model files. DesignStateIdGenerator is already in DG.Core — new ID methods go there.
- **Cross-index alignment in DESIGN STATE**: Per D-03, the three inputs are independent bags. Do not add validation that ObjState count == ParamState count.
- **v1 fallback in v2 serializer**: Per D-06, no fallback. v2 serializer only reads `version: "2"`.
- **Deleting VariableBinder**: Phase 18 owns this. Phase 16 must not touch ClassificatorComponent or VariableBinder.
- **Geometry serialization in StateId hash**: ObjectRef is user-supplied string (not geometry-hash). Geometry field on ElementRef is `object?` — do not include in hash computation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom JSON writer | System.Text.Json (built-in) | Existing v1 serializer uses it. Handles UTF-8, async, perf. |
| Hash-based identifiers | Custom hash algorithm | SHA256 (System.Security.Cryptography) | Built-in, already used, testable. Truncate to 16 hex chars. |
| Cross-component type unwrapping | Manual type casting with reflection | GhCastingHelpers.Unwrap<T>() | Existing pattern handles GH_ObjectWrapper nesting, public-vs-core type duality. |
| Error message formatting | Inline string construction | ErrorMessageTemplates static class | Existing What+Where+How-to-fix pattern. Extend, don't replace. |

**Key insight:** The domain is well-bounded — pure C# models with deterministic IDs and JSON serialization. Every pattern already exists in the codebase (DesignStateIdGenerator, DesignStateJsonSerializer, GhCastingHelpers, ErrorMessageTemplates). No new infrastructure or third-party packages needed.

## Runtime State Inventory

**SKIPPED** — Phase 16 is a pure code phase (models + GH components). No rename/refactor/migration of runtime state. The only deletion targets (DefState.cs, ObjectState.cs, ObjectInstance.cs) are source files with zero runtime data.

## Common Pitfalls

### Pitfall 1: Stale StateId When a Parameter Is Added
**What goes wrong:** The deterministic hash includes all parameters. Adding a parameter silently changes the StateId, which could surprise users expecting stable IDs.
**Why it happens:** The hash is a content hash. Identical content = same ID; different content (even adding one param) = different ID.
**How to avoid:** This is by design — the test `ComputeDefStateId_ShouldChange_WhenParameterIsAdded` already validates this behavior. Document that StateId changes when composition changes.
**Warning signs:** Test that adding a parameter DOES change the ID (existing test pattern).

### Pitfall 2: Geometry Reference Cannot Be Serialized/Deserialized
**What goes wrong:** The `Geometry` field on `ElementRef` is typed as `object?` and may contain a Rhino geometry reference that cannot be serialized by System.Text.Json.
**Why it happens:** Rhino/GH geometry is a complex in-process object, not a serializable primitive.
**How to avoid:** The geometry reference is an in-memory handle, not part of the serialized state payload. ObjState serialization includes only the `ObjectRef` string (DgEntityId/DisplayName) and `Label`. Geometry is not hashed or serialized (PROJECT.md: "ObjectRef is user-supplied string, not geometry-hash").
**Warning signs:** Attempting to serialize the `Geometry` field will throw `JsonException` or produce invalid JSON.

### Pitfall 3: Deterministic Hash Collision at Scale
**What goes wrong:** SHA-256 truncated to 16 hex chars (64 bits) has a birthday collision boundary at ~2^32 items (~4 billion). At current scale (hundreds of states) this is negligible.
**Why it happens:** Truncation reduces collision resistance.
**How to avoid:** Documented in PITFALLS.md P5. Accept the risk for current scale. If collision is observed in production, extend the hex length.
**Warning signs:** Not applicable at current volume. Monitor if project scales significantly.

### Pitfall 4: GUID Collision on Component Rename
**What goes wrong:** DESIGN STATE -> PARAMETER STATE gets a new GUID (D-13). Old canvases show a "missing component" placeholder. Users must re-wire.
**Why it happens:** v7.0 is a breaking-change milestone. Release notes at Phase 20 cover canvas re-wiring.
**How to avoid:** Documented. No backward-compat shim. Planner should ensure v7.0 release notes (Phase 20) describe the rename.
**Warning signs:** Old .gh files with the v2.0 DESIGN STATE GUID open with a missing-component placeholder.

## Code Examples

### ObjState Model
```csharp
// Source: Derived from ElementRef.cs + DesignStateSnapshot.cs patterns
// New file: DG/src/DG.Core/Models/ObjState.cs
namespace DG.Core.Models;

public class ObjState
{
    public string StateId { get; init; } = string.Empty;       // OS_ prefix
    public string ObjectRef { get; init; } = string.Empty;     // user-supplied identifier
    public object? Geometry { get; init; }                      // in-process handle, not serialized
    public string? Label { get; init; }                         // user-supplied display label
    public DateTimeOffset CapturedAtUtc { get; init; }
}
```

### PropState Model
```csharp
// Source: D-08/D-09/D-10/D-11 from CONTEXT.md
// New file: DG/src/DG.Core/Models/PropState.cs
namespace DG.Core.Models;

public class PropState
{
    public string StateId { get; init; } = string.Empty;        // PS_ prefix
    public string RuleIri { get; init; } = string.Empty;        // e.g. dgm:Rule_R_URB_HEIGHT_MAX_75_V
    public string DataPropertyIri { get; init; } = string.Empty; // e.g. dg:hasHeight
    public DesignStateParameter PropValue { get; init; }        // typed Number/Integer/Boolean
}
```

### DesignState Model
```csharp
// Source: D-01/D-02/D-04 from CONTEXT.md
// New file: DG/src/DG.Core/Models/DesignState.cs
namespace DG.Core.Models;

public class DesignState
{
    public string StateId { get; init; } = string.Empty;        // DS_ prefix (aggregate hash)
    public List<ObjState> ObjStates { get; init; } = new();
    public List<ParamState> ParamStates { get; init; } = new();
    public List<PropState> PropStates { get; init; } = new();
    public DateTimeOffset CapturedAtUtc { get; init; }
}
```

### DesignStateIdGenerator Additions
```csharp
// Source: Merged into DG/src/DG.Core/Services/DesignStateIdGenerator.cs
// Existing method renamed:
public static string ComputeParamStateId(IEnumerable<DesignStateParameter> parameters)
    => /* same logic as ComputeDefStateId, DS_ prefix */ ;

// New method for PropState (D-11):
public static string ComputePropStateId(string ruleIri, string dataPropertyIri, DesignStateParameter propValue)
{
    var lex = propValue.Type switch
    {
        DesignStateParameterType.Number => propValue.NumberValue?.ToString("R", CultureInfo.InvariantCulture) ?? "null",
        DesignStateParameterType.Integer => propValue.IntegerValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
        DesignStateParameterType.Boolean => propValue.BooleanValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
        _ => "null",
    };
    var input = $"{ruleIri}|{dataPropertyIri}|{lex}";
    return PropStatePrefix + HashToHex16(input);
}

// New method for DesignState aggregate (D-04):
public static string ComputeDesignStateId(IEnumerable<string> memberStateIds)
{
    var sb = new StringBuilder();
    foreach (var id in memberStateIds.OrderBy(x => x, StringComparer.Ordinal))
    {
        sb.Append(id);
    }
    return DesignStatePrefix + HashToHex16(sb.ToString());
}
```

### GhCastingHelpers Extensions
```csharp
// Source: Pattern from existing GhCastingHelpers.TryRule() and TryElementRef()
public static ObjState? TryObjState(object? input) => Unwrap<ObjState>(input) ?? Unwrap<global::DG.ObjState>(input);
public static ParamState? TryParamState(object? input) => Unwrap<ParamState>(input) ?? Unwrap<global::DG.ParamState>(input);
public static PropState? TryPropState(object? input) => Unwrap<PropState>(input) ?? Unwrap<global::DG.PropState>(input);
public static DesignState? TryDesignState(object? input) => Unwrap<DesignState>(input) ?? Unwrap<global::DG.DesignState>(input);
```

### Test Pattern for New Models
```csharp
// Source: Existing test patterns from DesignStateIdGeneratorTests.cs and DesignStateJsonSerializerTests.cs
[Fact]
public void PropState_ShouldGetDeterministicId_ForSameInputs()
{
    var iri1 = "dgm:Rule_R_URB_HEIGHT_MAX_75_V";
    var iri2 = "dg:hasHeight";
    var value = new DesignStateParameter
    {
        ParameterId = "height",
        DisplayName = "Height",
        Type = DesignStateParameterType.Number,
        NumberValue = 75.0,
    };

    var id1 = DesignStateIdGenerator.ComputePropStateId(iri1, iri2, value);
    var id2 = DesignStateIdGenerator.ComputePropStateId(iri1, iri2, value);

    Assert.Equal(id1, id2);
    Assert.StartsWith("PS_", id1);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DefState (v3.0 scaffolding) | ParamState + PropState | Phase 16 | Dual state kinds for parameters vs. calculated properties |
| DesignStateSnapshot (flat) | DesignState (3-part aggregate) | Phase 16 | Composition replaces flat snapshot |
| v1 statePayloadJson (flat DTO) | v2 statePayloadJson (versioned envelope) | Phase 16 | Explicit version discriminator, 3-part structure |
| DESIGN STATE (v2.0, dynamic-input) | PARAMETER STATE (renamed, same capture logic) | Phase 16 | Component name aligns with ontology; DESIGN STATE becomes composition component |
| ObjectState (v3.0 scaffolding, OI-OS chain) | ObjState (simplified: ObjectRef+Geometry+Label) | Phase 16 | Removed ObjectInstance concept. Simpler 3-field model. |

**Deprecated/outdated:**
- `DefState.cs` — delete (D-12). Replaced by `ParamState.cs`.
- `ObjectState.cs` — delete (D-12). Replaced by `ObjState.cs`.
- `ObjectInstance.cs` — delete (D-12). Concept eliminated; ObjState is self-contained.
- `DesignStateComponent.cs` (v2.0 GUID) — rename to ParameterStateComponent with new GUID (D-13).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DesignStateParameter's typed-nullable pattern (NumberValue?/IntegerValue?/BooleanValue?) can be reused as PropValue without wrapper class | Code Examples | Minimal — a simple `PropValue` wrapper would add one indirection layer |
| A2 | Geometry field on ElementRef (object?) should NOT be serialized in statePayloadJson | Code Examples / Pitfall 2 | If serialized, could produce invalid JSON for Rhino geometry types. Safer to exclude per PROJECT.md. |
| A3 | ObjState.ID uses existing ComputeObjectStateId (3-param signature) | Code Examples | If ObjState semantics differ from v3.0 ObjectState (no ObjectInstanceId), hash input must change. Per D-14, the ID contract carries forward unchanged. |
| A4 | OI_ prefix and ComputeObjectInstanceId should be removed (D-15) | Standard Stack | If any Phase 18 or other downstream code references OI_ prefix as a constant, removal would break compilation. Confirmed zero call sites in this research. |

## Open Questions

1. **Serializer class name: new vs rework?**
   - What we know: D-07 allows either a new class or rework of existing DesignStateJsonSerializer
   - What's unclear: The v1 DTO pattern (flat SnapshotDto) is fundamentally different from the v2 versioned envelope. A new class avoids conditional version branching in the serializer.
   - Recommendation: New class `DesignStatePayloadV2Serializer` in same namespace. Clean separation, no v1 baggage.

2. **Geometry field serialization in ObjState?**
   - What we know: PROJECT.md says ObjectRef is user-supplied string, not geometry-hash. Geometry is in-memory handle.
   - What's unclear: Should ObjState Geometry be serialized as a null placeholder or excluded from the DTO entirely?
   - Recommendation: Exclude from serialization DTO. Geometry is in-process handle meaningful only within the GH session. The `Label` field provides the user-facing identifier.

3. **Internal list ordering in DesignState model?**
   - What we know: Claude's discretion per CONTEXT.md.
   - What's unclear: Preserve wiring order from GH component, or sort deterministically by StateId?
   - Recommendation: Preserve wiring order within each list. The aggregate StateId is computed from sorted member IDs regardless of list order, so the StateId remains deterministic. Preserving wiring order is less surprising to users debugging canvas connections.

4. **OI_ prefix disposition?**
   - What we know: ObjectInstance is deleted. D-15 says remove ComputeObjectInstanceId. Claude's discretion whether prefix constant stays.
   - What's unclear: Could OI_ be needed in future?
   - Recommendation: Remove both ComputeObjectInstanceId method and OI_ prefix constant. They can be re-added if needed. Keeping dead constants creates confusion.

## Environment Availability

> **Step 2.6: SKIPPED** — Phase 16 is a pure C# code phase with no external tool dependencies beyond the existing .NET SDK and test runner. The project already builds and tests pass (v2.0 baseline). No new tools, services, or runtimes required.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | xUnit (net7.0) |
| Config file | DG/tests/DG.Tests/DG.Tests.csproj |
| Quick run command | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DG.Tests.DesignState"` |
| Full suite command | `dotnet test DG/tests/DG.Tests/` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-01 | ObjState model properties/constructor | unit | `dotnet test --filter "FullyQualifiedName~ObjState"` | NEW |
| CORE-02 | ParamState model (renamed DesignStateSnapshot) | unit | `dotnet test --filter "FullyQualifiedName~ParamState"` | NEW |
| CORE-03 | PropState model + ComputePropStateId deterministic | unit | `dotnet test --filter "FullyQualifiedName~PropState"` | NEW |
| CORE-04 | DesignState aggregate + ComputeDesignStateId | unit | `dotnet test --filter "FullyQualifiedName~DesignState"` | NEW |
| CORE-05 | statePayloadJson v2 round-trip (serialize->deserialize->equal) | unit | `dotnet test --filter "FullyQualifiedName~DesignStatePayloadSerializer"` | NEW |
| CORE-05 | v2 serializer rejects v1 payload (no fallback) | unit | same as above | NEW |
| D-11 | ComputePropStateId determinism and PS_ prefix | unit | `dotnet test --filter "FullyQualifiedName~DesignStateIdGenerator"` | UPDATE |
| D-04 | ComputeDesignStateId sorted-member hash | unit | same as above | UPDATE |

### Sampling Rate
- **Per task commit:** `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DG.Tests.DesignStateIdGenerator|DG.Tests.DesignStateJsonSerializer"` (ID + serializer)
- **Per wave merge:** `dotnet test DG/tests/DG.Tests/`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `DG/tests/DG.Tests/ObjStateModelTests.cs` — covers CORE-01
- [ ] `DG/tests/DG.Tests/ParamStateModelTests.cs` — covers CORE-02
- [ ] `DG/tests/DG.Tests/PropStateModelTests.cs` — covers CORE-03
- [ ] `DG/tests/DG.Tests/DesignStateModelTests.cs` — covers CORE-04
- [ ] `DG/tests/DG.Tests/DesignStatePayloadSerializerTests.cs` — covers CORE-05
- [ ] `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — update: add ComputeParamStateId (rename), ComputePropStateId, ComputeDesignStateId tests

*(No gaps for framework install — xUnit already configured in DG.Tests.csproj)*

## Security Domain

> Security enforcement is not applicable to Phase 16. The phase creates pure-logic C# models and Grasshopper UI components. No network access, no external input validation, no authentication, no persistence. Security assessment: `security_enforcement: false`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | Component-level type checking only (UnwrapScalar pattern). No injection risk in C# models. |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — SHA-256 hash assembly pattern, 3 existing methods, prefix constants
- [VERIFIED: codebase] `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs` — v1 DTO pattern, camelCase policy, validation
- [VERIFIED: codebase] `DG/src/DG.Core/Models/DesignStateParameter.cs` — typed nullable value fields
- [VERIFIED: codebase] `DG/src/DG.Core/Models/DesignStateSnapshot.cs` — flat 3-field model (StateId, CapturedAtUtc, Parameters)
- [VERIFIED: codebase] `DG/src/DG.Core/Models/ElementRef.cs` — DgEntityId, Geometry, DisplayName
- [VERIFIED: codebase] `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` — IGH_VariableParameterComponent pattern, UnwrapScalar/BuildParameter/BuildSnapshot
- [VERIFIED: codebase] `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — Unwrap<T>, TryRule, TryElementRef
- [VERIFIED: codebase] `DG/src/DG.Grasshopper/PublicTypes.cs` — public wrapper pattern (inherit Core model)
- [VERIFIED: codebase] `DG/src/DG.Grasshopper/DgComponentCategory.cs` — "DG" / "Design Grammars"
- [VERIFIED: codebase] `DG/src/DG.Grasshopper/DgIcons.cs` — icon loading pattern (embedded resources)
- [VERIFIED: codebase] `DG/src/DG.Core/Models/DefState.cs` — zero call sites (model def only)
- [VERIFIED: codebase] `DG/src/DG.Core/Models/ObjectState.cs` — zero call sites (model def only)
- [VERIFIED: codebase] `DG/src/DG.Core/Models/ObjectInstance.cs` — zero call sites (model def only)
- [VERIFIED: codebase] `DG/src/DG.Core/Classification/VariableBinder.cs` — 2 call sites, do NOT touch
- [VERIFIED: codebase] `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — What+Where+How-to-fix pattern
- [VERIFIED: codebase] `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — xUnit test patterns
- [VERIFIED: codebase] `DG/tests/DG.Tests/DesignStateJsonSerializerTests.cs` — round-trip test patterns
- [CITED: CONTEXT.md] D-01 through D-15 — locked decisions
- [CITED: port-iri-map-V7.md] Port-to-IRI contract for all 4 state components

### Secondary (MEDIUM confidence)
- [CITED: V7-INVESTIGATION.md] State-kind names, PS_ prefix decision, conflict resolutions
- [CITED: REQUIREMENTS.md] CORE-01..05, GHST-01..04
- [CITED: ROADMAP.md] Phase 16 goal, 4 success criteria

### Tertiary (LOW confidence)
- None — all research findings verified against codebase or CONTEXT.md

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library/pattern verified in existing codebase
- Architecture: HIGH — all patterns documented, verified call sites
- Pitfalls: HIGH — based on existing PITFALLS.md + codebase analysis

**Research date:** 2026-07-04
**Valid until:** 2026-08-04 (stable domain — C# models, SHA-256, System.Text.Json)

## RESEARCH COMPLETE

**Phase:** 16 — DG.Core State Models and State Components
**Confidence:** HIGH

### Key Findings
1. **Zero call sites confirmed** for DefState, ObjectState, ObjectInstance — deletion is safe (D-12).
2. **DesignStateIdGenerator pattern** is clean: SHA-256 -> 16-char hex. Add ComputeParamStateId, ComputePropStateId, ComputeDesignStateId; remove ComputeObjectInstanceId.
3. **DesignStateComponent v2.0** is the exact pattern for ParameterStateComponent — same IGH_VariableParameterComponent, UnwrapScalar, BuildParameter logic. Rename only.
4. **Serializer v2** needs a new versioned-envelope DTO. The v1 flat DTO is structurally incompatible. New class recommended.
5. **VariableBinder has 2 call sites** (ClassificatorComponent, VariableBinderTests) — Phase 18 owns deletion. Phase 16 must NOT touch.
6. **StateId.DS_ prefix** for DesignState is NOT the same as DS_ prefix for DefState/ParamState. The existing ComputeDefStateId uses DS_ for parameters. DesignState aggregate uses DS_ for the composition. Both DS_ but different hash inputs. This is correct per D-15 (ComputeDefStateId->ComputeParamStateId keeps same prefix) and D-04 (DesignState gets DS_ prefix too). The prefixes are disambiguated by hash input domain.
7. **DesignStateComponent.cs filename conflict:** The new DESIGN STATE component (GHST-04) creates a filename conflict with the v2.0 DesignStateComponent.cs being renamed to ParameterStateComponent.cs. The new composition component should be named `DesignStateCompositionComponent.cs` or similar to avoid filename collision.

### File Created
`C:\Users\Admin\source\repos\design-grammar-system\.planning\phases\16-dg-core-state-models-and-state-components\16-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All libraries verified in existing codebase |
| Architecture | HIGH | All patterns exist in codebase, decisions locked in CONTEXT.md |
| Pitfalls | HIGH | Based on existing PITFALLS.md + direct codebase analysis |

### Open Questions
1. Serializer class name: new `DesignStatePayloadV2Serializer` vs rework existing `DesignStateJsonSerializer`?
2. Geometry field serialization in ObjState DTO — exclude entirely or serialize as null?
3. Internal list ordering in DesignState model — preserve wiring order vs sort by StateId?
4. OI_ prefix constant — remove entirely or keep as reserved?

### Ready for Planning
Research complete. Planner can now create PLAN.md files. The recommended implementation ordering is:
1. Models (ObjState, ParamState, PropState, DesignState) + DesignStateIdGenerator updates + deletion of scaffolding
2. Serializer v2
3. PublicTypes wrappers + GhCastingHelpers extensions
4. ParameterStateComponent rename (rename file, new GUID, update output type)
5. New GH components (ObjectStateComponent, PropertyStateComponent, DesignStateCompositionComponent)
6. Tests for all new models, serializer, and ID generator methods
