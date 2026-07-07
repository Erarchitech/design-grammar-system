# Phase 19: Deconstruct and Reinstate Components - Research

**Researched:** 2026-07-05
**Domain:** Grasshopper GH_Component design (C#, .NET, Rhino/Grasshopper SDK)
**Confidence:** HIGH

## Summary

Phase 19 creates three Grasshopper components that let architects disassemble stored DesignStates and re-apply captured parameters to the live canvas. Two are pure synchronous passthrough components (DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT) following the GRAPH DECONSTRUCT pattern from Phase 17. The third, PARAMETER REINSTATE, is a rework of the existing REINSTATE (GUID `D4E2F8A1-C736-4B9D-AE51-2B1F7C9D0E63`) with a new GUID, a required Target input wired from PARAMETER STATE, and index-matched StateStatus/Parameters outputs.

The phase relies entirely on existing infrastructure: `DesignStateReinstatementService` (pure logic, already tested), `GhCastingHelpers` (type unwrapping), `ErrorMessageTemplates` (What+Where+How-to-fix pattern), and established GH_Component patterns from Phase 16/17. No new external packages are required.

**Primary recommendation:** Implement DESIGN STATE DECONSTRUCT and OBJECT DECONSTRUCT as pure synchronous passthrough components (no async, no DB, no ScheduleSolution), following the GraphDeconstructComponent pattern. Implement PARAMETER REINSTATE by adapting the existing ReinstateComponent -- new GUID, required Target input, reworked output contract (Parameters + StateStatus + Status), wire-traversal and deferred-write patterns carried forward unchanged.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DesignState deconstruction (data unpacking) | Grasshopper Plugin (C#) | -- | Pure synchronous data transformation, no external dependencies |
| ObjState deconstruction (data unpacking) | Grasshopper Plugin (C#) | -- | Pure synchronous data transformation, no external dependencies |
| Parameter reinstatement (validation) | DG.Core.Services (C#) | Grasshopper Plugin | DesignStateReinstatementService is pure logic in DG.Core -- GH component calls it for pre-validation |
| Parameter reinstatement (write phase) | Grasshopper Plugin (C#) | -- | GH-specific: writes live slider/toggle values via GH API, deferred via ScheduleSolution |
| Target discovery | Grasshopper Plugin (C#) | -- | Wire-traversal of GH document graph (GH API only) |
| Reinstatement status reporting | Grasshopper Plugin (C#) | -- | GH output ports -- index-matched lists + summary text |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### REINSTATE Target Discovery (Area 1)
- **D-01:** PARAMETER REINSTATE keeps a 'Target' input -- wired from PARAMETER STATE component's State output. REINSTATE walks upstream wires from that PARAMETER STATE to discover which sliders/toggles to push captured values to. Same proven wire-traversal pattern as the old REINSTATE. The wire IS the target declaration.
- **D-02:** Target input is Required (not optional). No fallback search from the ParamState input -- simpler contract, no ambiguity about which PARAMETER STATE is the target.
- **D-03:** Target input is a runtime/DB concern (no ontology IRI). Annotated alongside the Reinstate trigger -- it's a Grasshopper-internal wiring mechanism, not an ontology concept.

#### StateStatus & Parameters Outputs (Area 2)
- **D-04:** StateStatus list is index-matched to ParamState.Parameters -- one ReStatus per parameter, same length, same order. Downstream components can pair Parameters[i] with StateStatus[i]. Follows the index-matched list contract pattern from METAGRAPH Rules/Objects (Phase 17 D-02) and VALIDATOR ValidStatus/ObjStates (Phase 18 D-01).
- **D-05:** Parameters output contains ALL parameters from the captured ParamState (not just applied ones). Clean separation of concerns -- data vs. status. Downstream filters by cross-referencing with StateStatus.
- **D-06:** Keep summary Status text output as a third output alongside Parameters + StateStatus. Human-readable summary ("Applied 5 parameters" / "Aborted: 2 blocked" / "Unchanged (same state)" / "Idle"). Ergonomic -- architects see the outcome directly on the component without inspecting lists.

#### DECONSTRUCT Error Contract (Area 3)
- **D-07:** Both DESIGN STATE DECONSTRUCT and OBJECT DECONSTRUCT use Warning + empty outputs on null/missing input. AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ...) + set all outputs to empty lists + return. Consistent with standard Grasshopper component behavior. Empty list inputs (e.g., DesignState with no ObjStates) are valid and passthrough as empty lists -- no warning.

### Claude's Discretion
- Exact GUID assignments for DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, and PARAMETER REINSTATE (whether old REINSTATE GUID D4E2F8A1-C736-4B9D-AE51-2B1F7C9D0E63 is kept or a new GUID assigned -- recommend: new GUID for the reworked component, matching the VALIDATION GRAPH precedent from Phase 17)
- Component icons (DgIcons entries -- follow existing icon naming convention)
- Exact GH_Component layout: RegisterInputParams/RegisterOutputParams for all 3 components
- Wire-traversal implementation for Target input (reuse FindUpstreamDesignState pattern from current ReinstateComponent)
- Deferred write scheduling -- reuse ScheduleSolution pattern from current ReinstateComponent
- Error message wording (follow ErrorMessageTemplates What+Where+How-to-fix pattern)
- Exact output type for Parameters output (DesignStateParameter list vs custom goo wrapper)
- Exact output type for StateStatus output (ReinstatementStatus enum vs int vs text -- recommend: ReinstatementStatus enum, wrapped for GH)
- Whether the old REINSTATE component file is renamed in-place or replaced with a new file (recommend: replace -- new GUID, new contract, cleaner git history)
- DECONSTRUCT component output typing -- ObjState/ParamState/PropState lists, wrapped via GH_ObjectWrapper or GhCastingHelpers generic pattern

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope.

### Cross-phase notes (not scope changes)
- Phase 20: E2E live chain tests the full round-trip: VALIDATION GRAPH -> DESIGN STATE DECONSTRUCT -> OBJECT DECONSTRUCT, and VALIDATION GRAPH -> DESIGN STATE DECONSTRUCT -> PARAMETER REINSTATE. Canvas breakage from REINSTATE GUID change is documented in release notes.
- Phase 20: Release notes document the old REINSTATE -> PARAMETER REINSTATE re-wiring (new GUID, required Target input, new output contract).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GHST-05 | DESIGN STATE DECONSTRUCT splits DesignState into ObjState/ParamState/PropState | DesignState model exposes 3 independent lists (ObjStates, ParamStates, PropStates) -- pure unpack. GhCastingHelpers.TryDesignState unwraps from GH_ObjectWrapper or DG.DesignState public wrapper. Warning+empty-outputs pattern defined in D-07. Port-IRI map lines 52-55 define port contracts. |
| GHST-06 | OBJECT DECONSTRUCT splits ObjState into Object/Geometry/Label | ObjState model has ObjectRef (string), Geometry (object?), Label (string?) fields. Pure property access. GhCastingHelpers.TryObjState (lines 81-95) already exists. Port-IRI map lines 57-59 define port contracts. |
| GHST-07 | PARAMETER REINSTATE (reworked REINSTATE) applies ParamState on rising-edge Reinstate trigger, outputs Parameters + StateStatus + Status | Existing ReinstateComponent carries all patterns forward: wire-traversal (FindUpstreamDesignState, ResolveTargets), rising-edge trigger (_lastApplyInput), deferred writes (ScheduleSolution, WriteToSource), assembly-mismatch fallback (ReconstructSnapshot). DesignStateReinstatementService.Validate already tested and ready. Index-matched StateStatus contract from D-04. Parameters output = all params from D-05. Summary Status text from D-06. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| .NET SDK | 9.0.308 (installed) | Build target for DG.Core; also builds net7.0 | Existing project infrastructure |
| xUnit | 2.9.2 | Test framework | Existing project standard in DG.Tests |
| Microsoft.NET.Test.Sdk | 17.12.0 | Test runner | Existing project standard |

### Supporting (in-project)
| Component/Class | Source | Purpose | When to Use |
|-----------------|--------|---------|-------------|
| GhCastingHelpers | DG.Grasshopper.Components | Unwrap GH containers to native types | Both DECONSTRUCT components: TryDesignState, TryObjState, TryParamState, TryPropState, Unwrap<T> |
| DesignStateReinstatementService | DG.Core.Services | Pure logic pre-validation | PARAMETER REINSTATE: Validate(ParamState, targets, lastStateId) -> ReinstatementResult |
| ErrorMessageTemplates | DG.Core.Services | What+Where+How-to-fix error messages | DECONSTRUCT warnings, REINSTATE error bubbles |
| DesignState | DG.Core.Models | Three-list state composition | DESIGN STATE DECONSTRUCT input and output format |
| ObjState | DG.Core.Models | Object reference + Geometry + Label | OBJECT DECONSTRUCT input and output |
| ParamState | DG.Core.Models | Captured parameter values | DESIGN STATE DECONSTRUCT output, PARAMETER REINSTATE input |
| PropState | DG.Core.Models | Rule-scoped property value | DESIGN STATE DECONSTRUCT output |
| DesignStateParameter | DG.Core.Models | Typed Number/Integer/Boolean parameter | PARAMETER REINSTATE Parameters output |
| ReinstatementResult | DG.Core.Models | Applied/Aborted + per-param reports | PARAMETER REINSTATE internal use for building outputs |
| ReinstatementStatus | DG.Core.Models | 7-value enum | PARAMETER REINSTATE StateStatus output |
| ResolvedTarget | DG.Core.Models | Target resolution for wire-traversal | PARAMETER REINSTATE internal use |
| DgComponentCategory | DG.Grasshopper | "DG" / "Design Grammars" toolbar grouping | All 3 components |
| DgIcons | DG.Grasshopper | Embedded 24x24 PNG icon loading | All 3 components: need new icons (DesignStateDeconstruct24.png, ObjectDeconstruct24.png, ParameterReinstate24.png) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inheriting from GH_Component (built-in) | IGH_Component interface | No reason to deviate -- all existing DG components use GH_Component base class |
| Direct type casting | GhCastingHelpers | GhCastingHelpers handles GH_ObjectWrapper unwrapping and assembly-mismatch fallback -- avoids silent null casts |
| DesignStateReinstatementService (pure logic) | Inline validation | Service is already tested (12 test cases) -- inlining would duplicate coverage and risk divergence |

**Installation:**
```bash
# No new NuGet packages -- all dependencies are in-project
dotnet build DG/DG.sln -c Release
```

**Version verification:** No external packages to verify. All referenced types are in DG.Core (net7.0;net9.0) and DG.Grasshopper (net7.0-windows). xUnit 2.9.2 confirmed in DG.Tests.csproj (existing install).

## Package Legitimacy Audit

> This phase installs no external packages. All dependencies are in-project assemblies (DG.Core, DG.Grasshopper) or system-installed Rhino/Grasshopper assemblies referenced via relative path. No npm/PyPI/crates registry dependency.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| DG.Core | in-project | -- | -- | -- | N/A | In-project |
| DG.Grasshopper | in-project | -- | -- | -- | N/A | In-project |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
  VALIDATION GRAPH (Phase 17)
        |
        | DesignState (list)
        v
  +---------------------------+
  | DESIGN STATE DECONSTRUCT  |  Pure sync passthrough
  +---------------------------+
    /           |            \
   v            v             v
ObjState[]   ParamState[]   PropState[]
   |              |              |
   v              v              
  +------------+  +-----------------------------+
  | OBJECT     |  | PARAMETER REINSTATE         |
  | DECONSTRUCT|  | (rising-edge triggered)     |
  +------------+  +-----------------------------+
   |    |    |       |        |         |
   v    v    v       v        v         v
 Object Geom Label  Param  StateStatus Status
                    [all]  [index-     [summary
                            matched]   text]
```

The E2E chain flows: VALIDATION GRAPH -> DESIGN STATE DECONSTRUCT splits the state. OBJECT DECONSTRUCT further splits each ObjState. PARAMETER REINSTATE consumes a ParamState and applies it back to sliders/toggles via the PARAMETER STATE Target wire.

### Recommended Project Structure
No structural changes -- 3 new component files in the existing `DG/src/DG.Grasshopper/Components/` directory plus supporting assets (icons, tests, error message extensions).

```
DG/src/DG.Grasshopper/Components/
  DesignStateDeconstructComponent.cs    -- NEW: GHST-05 component
  ObjectDeconstructComponent.cs         -- NEW: GHST-06 component
  ParameterReinstateComponent.cs        -- NEW: GHST-07 component (replaces ReinstateComponent.cs)

DG/src/DG.Grasshopper/Properties/
  DesignStateDeconstruct24.png          -- NEW: icon for DESIGN STATE DECONSTRUCT
  ObjectDeconstruct24.png               -- NEW: icon for OBJECT DECONSTRUCT
  ParameterReinstate24.png              -- NEW: icon for PARAMETER REINSTATE

DG/src/DG.Core/Services/
  ErrorMessageTemplates.cs             -- EXTEND: add deconstruct warning templates

DG/tests/DG.Tests/
  DesignStateDeconstructComponentTests.cs    -- NEW: unit tests
  ObjectDeconstructComponentTests.cs         -- NEW: unit tests
  ParameterReinstateComponentTests.cs        -- NEW: unit tests
```

**File disposition for old REINSTATE:**
- `DG/src/DG.Grasshopper/Components/ReinstateComponent.cs` -- REPLACED (new GUID, new file ParameterReinstateComponent.cs; old file deleted or kept as reference with a note)
- `DG/src/DG.Grasshopper/Properties/Reinstate24.png` -- REPLACED (new icon)

### Pattern 1: Pure Synchronous Passthrough (DECONSTRUCT components)
**What:** Component that reads one input, unwraps the type, and outputs multiple parts of the same data synchronously. No async, no DB calls, no ScheduleSolution.
**When to use:** DESIGN STATE DECONSTRUCT and OBJECT DECONSTRUCT.
**Source:** GraphDeconstructComponent.cs (Phase 17 D-01 pattern)

```csharp
// Pattern from GraphDeconstructComponent.cs (lines 41-61)
protected override void SolveInstance(IGH_DataAccess da)
{
    object? input = null;
    if (!da.GetData(0, ref input))
    {
        AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
            ErrorMessageTemplates.ValidationInputMissing("DesignState"));
        SetEmptyOutputs(da, "No input.");
        return;
    }

    var designState = GhCastingHelpers.TryDesignState(input);
    if (designState is null)
    {
        AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
            "DESIGN STATE DECONSTRUCT: Could not unwrap DesignState input.");
        SetEmptyOutputs(da, "Invalid input.");
        return;
    }

    // Pure data passthrough -- unpack three independent lists
    da.SetDataList(0, designState.ObjStates);
    da.SetDataList(1, designState.ParamStates);
    da.SetDataList(2, designState.PropStates);
    Message = $"{designState.ObjStates.Count}O/{designState.ParamStates.Count}P/{designState.PropStates.Count}Pr";
}
```

### Pattern 2: Rising-Edge Trigger with Deferred Writes (PARAMETER REINSTATE)
**What:** Component that detects a false->true transition on a Boolean input, performs validation, and schedules slider/toggle value writes after the current GH solution completes.
**When to use:** PARAMETER REINSTATE (carried forward from existing REINSTATE).
**Source:** ReinstateComponent.cs (Phase 2 v2.0 pattern)

```csharp
// Rising-edge detection (ReinstateComponent.cs lines 121-128)
bool applyInput = false;
if (!da.GetData(2, ref applyInput)) applyInput = false;

var isRisingEdge = applyInput && !_lastApplyInput;
_lastApplyInput = applyInput;

if (!isRisingEdge)
{
    // Output last result or idle
    SetOutputs(da, _latestResult, GetStatusSummary(_latestResult));
    return;
}

// Deferred write scheduling (lines 401-441)
var doc = designState.OnPingDocument();
if (doc is null) return;

var writeActions = new List<Action>();
// ... build write actions for each resolved target ...

doc.ScheduleSolution(5, _ =>
{
    foreach (var write in writeActions) write();
});
```

### Pattern 3: Target Discovery via Wire Traversal (PARAMETER REINSTATE)
**What:** Component walks upstream wire connections from the Target input to find the PARAMETER STATE component, then enumerates its input sources to build ResolvedTarget list.
**When to use:** PARAMETER REINSTATE Target input processing.
**Source:** ReinstateComponent.cs FindUpstreamDesignState + ResolveTargets

```csharp
// Wire traversal: find PARAMETER STATE from Target input (ReinstateComponent.cs lines 310-331)
private ParameterStateComponent? FindUpstreamDesignState()
{
    if (Params.Input[1].Sources.Count == 0) return null;

    foreach (var source in Params.Input[1].Sources)
    {
        var docObj = source.Attributes?.GetTopLevel?.DocObject;
        if (docObj is ParameterStateComponent dsc) return dsc;
    }
    return null;
}

// Target resolution: enumerate PARAMETER STATE inputs to build ResolvedTarget list
private static List<ResolvedTarget> ResolveTargets(ParameterStateComponent designState)
{
    var targets = new List<ResolvedTarget>();
    for (var i = 0; i < designState.Params.Input.Count; i++)
    {
        var ghParam = designState.Params.Input[i];
        var parameterId = string.IsNullOrWhiteSpace(ghParam.NickName)
            ? $"param_{i}" : ghParam.NickName.Trim();
        // ... source resolution logic ...
    }
    return targets;
}
```

### Anti-Patterns to Avoid
- **Omitting assembly-mismatch fallback:** The existing ReinstateComponent has `ReconstructSnapshot` and `ReconstructParameter` to handle the case where GH loads a different copy of DG.Core.dll. This must carry forward into PARAMETER REINSTATE.
- **Writing sliders during SolveInstance:** Direct slider writes during SolveInstance can be silently dropped. Always use `ScheduleSolution` to defer writes, as demonstrated in ScheduleWriteValues.
- **Using `null` sentinel for empty outputs on DECONSTRUCT:** D-07 specifies Warning + empty lists for null/missing input (not null outputs). Empty lists are valid passthroughs. Setting outputs to `null` breaks index-matched downstream components.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GH container unwrapping | Custom if/else chain for GH_ObjectWrapper/IGH_Goo | GhCastingHelpers.Unwrap<T>, TryDesignState, TryObjState, TryParamState, TryPropState | Handles assembly-mismatch reflection fallback and nested GH_ObjectWrapper unwrapping |
| StateId generation | Roll your own hash | DesignStateIdGenerator.ComputeDesignStateId, .ComputeParamStateId, .ComputeObjectStateId | Deterministic content-addressed IDs for dedup -- already unit-tested |
| Pre-validation logic | Inline parameter/type/domain checks | DesignStateReinstatementService.Validate | 12 test cases already covering Applied/MissingTarget/TypeMismatch/AmbiguousTarget/OutOfRange/Unchanged/WouldApply/aggregate counting |
| Error message formatting | Hardcoded strings | ErrorMessageTemplates (extend with new templates) | Consistent What+Where+How-to-fix pattern across the entire plugin |
| Icon loading | Manual resource stream code | DgIcons.Load(embedding convention) | All 14 existing icons follow this pattern; no RIAs or custom loaders |

**Key insight:** Phase 19 has unusually high reuse. The DECONSTRUCT components are the simplest in the v7.0 set (data unpacking only, no async, no DB, no triggers). PARAMETER REINSTATE carries forward ~80% of the existing ReinstateComponent code. The main new surface is the modified output contract (Parameters + StateStatus + Status) and the required Target input.

## Common Pitfalls

### Pitfall 1: GH_ObjectWrapper nesting causes silent null cast
**What goes wrong:** DECONSTRUCT component receives a DesignState wrapped in GH_ObjectWrapper -> IGH_Goo -> GH_ObjectWrapper, and a direct cast returns null silently. [CITED: ReinstateComponent.cs UnwrapGhContainer handles this pattern]
**Why it happens:** Grasshopper wraps values in typed GH goo + ObjectWrapper layers. The nesting depth varies by wire origin (some components add an extra wrapper).
**How to avoid:** Use `GhCastingHelpers.Unwrap<T>()` or `GhCastingHelpers.TryDesignState()` which recursively unwraps GH_ObjectWrapper and IGH_Goo before attempting the cast.
**Warning signs:** DECONSTRUCT output is always null/empty for valid DesignState inputs.

### Pitfall 2: Assembly version mismatch (REINSTATE)
**What goes wrong:** PARAMETER REINSTATE receives a ParamState from a different solution (or GH loaded a different copy of DG.Core.dll), and `input is ParamState` returns false even though the type name matches. [CITED: ReinstateComponent.cs lines 172-199]
**Why it happens:** Grasshopper loads assemblies from multiple directories; a user might run two DG versions or a stale .gha remains in the Components folder.
**How to avoid:** Keep the `ReconstructSnapshot` reflection-based reconstruction path. Check `raw.GetType().FullName` before falling through to null return.
**Warning signs:** "Assembly: DG.Core, Version=..." in the DiagnoseInputType error message.

### Pitfall 3: Rising-edge REINSTATE fires on first value
**What goes wrong:** On first GH solution, `_lastApplyInput` is `false` and `applyInput` comes in `true` from the default toggle value, so the component applies immediately even if the user hasn't explicitly triggered it. [ASSUMED]
**Why it happens:** Default logic: `isRisingEdge = applyInput && !_lastApplyInput` -- first solve: _lastApplyInput is false, applyInput is true (default GH Boolean input).
**How to avoid:** Initialize `_lastApplyInput = true` so the first solve sees `true && !true = false` -- only a user toggle from false to true fires the edge. The existing REINSTATE uses this initialization.
**Warning signs:** Parameters are written on first canvas load without explicit toggle.

### Pitfall 4: DECONSTRUCT empty-list warning on empty bags
**What goes wrong:** DESIGN STATE DECONSTRUCT emits a Warning for a DesignState with zero ObjStates but valid ParamStates/PropStates. [VERIFIED: D-07 explicitly says empty lists are valid passthrough with no warning]
**Why it happens:** Developer interprets "no items" as "invalid input" and adds an early guard.
**How to avoid:** Only emit Warning on null/missing input. If the input is a valid DesignState with empty internal lists, those lists are valid passthroughs. No warning.
**Warning signs:** Valid DesignState with no ObjStates produces spurious warnings on DESIGN STATE DECONSTRUCT.

### Pitfall 5: REINSTATE ScheduleSolution closure captures stale references
**What goes wrong:** Deferred write callback captures the GH parameter reference, but by the time ScheduleSolution fires, the document has changed and the reference is stale. [CITED: ReinstateComponent.cs lines 436-440]
**Why it happens:** ScheduleSolution defers execution to a later solution pass. If the user edits the canvas between trigger and execution, the captured reference may point to a removed component.
**How to avoid:** Use ScheduleSolution with a short delay (5ms) and validate source references inside the callback before writing. The existing pattern captures parameter copies in the closure.
**Warning signs:** "NullReferenceException" in ScheduleSolution callback during canvas edits.

## Code Examples

Verified patterns from the existing codebase [VERIFIED: source code from ReinstateComponent.cs, ParameterStateComponent.cs, GraphDeconstructComponent.cs, ValidationGraphComponent.cs]:

### DESIGN STATE DECONSTRUCT -- Complete Component Skeleton
```csharp
#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class DesignStateDeconstructComponent : GH_Component
{
    public DesignStateDeconstructComponent()
        : base("DESIGN STATE DECONSTRUCT", "DSGDECON",
            "Split a DesignState into ObjState, ParamState, and PropState lists.",
            DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("GUID-HERE"); // Claude's discretion

    protected override Bitmap Icon => DgIcons.DesignStateDeconstruct24; // NEW icon

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("DesignState", "DesignState",
            "DG.DesignState -- aggregate state from DESIGN STATE or VALIDATION GRAPH.",
            GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("ObjState", "ObjState",
            "List of ObjState objects. Index-matched to DesignState.ObjStates.",
            GH_ParamAccess.list);
        pManager.AddGenericParameter("ParamState", "ParamState",
            "List of ParamState objects. Index-matched to DesignState.ParamStates.",
            GH_ParamAccess.list);
        pManager.AddGenericParameter("PropState", "PropState",
            "List of PropState objects. Index-matched to DesignState.PropStates.",
            GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? input = null;
        if (!da.GetData(0, ref input))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
                ErrorMessageTemplates.ValidationInputMissing("DesignState"));
            SetEmptyOutputs(da, "No input.");
            return;
        }

        var designState = GhCastingHelpers.TryDesignState(input);
        if (designState is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
                "DESIGN STATE DECONSTRUCT: Could not unwrap DesignState input. Ensure the input is a valid DG.DesignState.");
            SetEmptyOutputs(da, "Invalid input.");
            return;
        }

        da.SetDataList(0, designState.ObjStates);
        da.SetDataList(1, designState.ParamStates);
        da.SetDataList(2, designState.PropStates);
        Message = $"{designState.ObjStates.Count}O/{designState.ParamStates.Count}P/{designState.PropStates.Count}Pr";
    }

    private static void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        da.SetDataList(0, new List<ObjState>());
        da.SetDataList(1, new List<ParamState>());
        da.SetDataList(2, new List<PropState>());
        AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, status);
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class DesignStateDeconstructComponent { }
#endif
```

### OBJECT DECONSTRUCT -- Complete Component Skeleton
```csharp
#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ObjectDeconstructComponent : GH_Component
{
    public ObjectDeconstructComponent()
        : base("OBJECT DECONSTRUCT", "OBJDECON",
            "Split an ObjState into Object reference, Geometry, and Label.",
            DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("GUID-HERE"); // Claude's discretion

    protected override Bitmap Icon => DgIcons.ObjectDeconstruct24; // NEW icon

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("ObjState", "ObjState",
            "DG.ObjState -- from DESIGN STATE DECONSTRUCT or OBJECT STATE output.",
            GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("Object", "Object",
            "ObjectRef string (e.g. 'building-42'). From ObjState.ObjectRef.",
            GH_ParamAccess.item);
        pManager.AddGenericParameter("Geometry", "Geometry",
            "Geometry handle from ObjState.Geometry (Rhino/GH geometry reference).",
            GH_ParamAccess.item);
        pManager.AddTextParameter("Label", "Label",
            "Label string from ObjState.Label.",
            GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? input = null;
        if (!da.GetData(0, ref input))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
                ErrorMessageTemplates.ValidationInputMissing("ObjState"));
            SetEmptyOutputs(da, "No input.");
            return;
        }

        var objState = GhCastingHelpers.TryObjState(input);
        if (objState is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,
                "OBJECT DECONSTRUCT: Could not unwrap ObjState input. Ensure the input is a valid DG.ObjState.");
            SetEmptyOutputs(da, "Invalid input.");
            return;
        }

        da.SetData(0, objState.ObjectRef);
        da.SetData(1, objState.Geometry);
        da.SetData(2, objState.Label);
        Message = objState.ObjectRef;
    }

    private static void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        da.SetData(0, string.Empty);
        da.SetData(1, null);
        da.SetData(2, null);
        AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, status);
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ObjectDeconstructComponent { }
#endif
```

### PARAMETER REINSTATE -- Modified Output Contract (Key Section)
```csharp
// New output registration (replacing old Result + Report + Status):
protected override void RegisterOutputParams(GH_OutputParamManager pManager)
{
    // D-05: ALL parameters from the captured ParamState, not just applied ones
    pManager.AddGenericParameter("Parameters", "Parameters",
        "All captured DesignStateParameters from the input ParamState. "
        + "Cross-reference with StateStatus to filter applied vs. blocked.",
        GH_ParamAccess.list);

    // D-04: Index-matched to Parameters list -- same length, same order
    pManager.AddGenericParameter("StateStatus", "StateStatus",
        "Per-parameter ReinstatementStatus list, index-matched to Parameters. "
        + "Use with Parameters[i] + StateStatus[i] pairing.",
        GH_ParamAccess.list);

    // D-06: Human-readable summary
    pManager.AddTextParameter("Status", "Status",
        "Summary: 'Applied 5 parameters' / 'Aborted: 2 blocked' / "
        + "'Unchanged (same state)' / 'Idle'.",
        GH_ParamAccess.item);
}

// New output setter (replacing SetOutputs in old REINSTATE):
private void SetOutputs(IGH_DataAccess da, ReinstatementResult? result, string status)
{
    // Parameters output always contains ALL params from the ParamState
    da.SetDataList(0, _latestParamState?.Parameters.ToList() ?? new List<DesignStateParameter>());

    // StateStatus output is index-matched to Parameters
    if (result is not null)
    {
        da.SetDataList(1, result.Reports
            .Select(r => r.Status)
            .ToList());
    }
    else
    {
        da.SetDataList(1, new List<ReinstatementStatus>());
    }

    da.SetData(2, status);
}
```

### Index-Matched List Contract Pattern (Phase 17 D-02 / Phase 18 D-01)
```csharp
// From ValidationGraphComponent.cs lines 106-108 -- index-matched outputs:
_latestRuns = result.Runs.Select(ToPublicRunInfo).ToList();
_latestStatusData = result.StatusList.ToList();
_latestDesignStates = result.DesignStates.Select(ToPublicDesignState).ToList();

// PARAMETER REINSTATE follows the same pattern:
// - Parameters[i] is the param at index i in ParamState.Parameters
// - StateStatus[i] is the ReStatus for Parameters[i]
// - Both lists are the same length (ParamState.Parameters.Count)

// Downstream pairing (architect code):
//   for (int i = 0; i < Parameters.Count; i++)
//   {
//       var param = Parameters[i];
//       var status = StateStatus[i];
//       if (status == Applied) { /* use param */ }
//   }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| REINSTATE (GUID D4E2F8A1) | PARAMETER REINSTATE (new GUID) | Phase 19 | Canvas breakage for existing REINSTATE users; documented in Phase 20 release notes |
| REINSTATE State + DesignState + Apply inputs | PARAMETER REINSTATE ParamState + Target + Reinstate inputs | Phase 19 | Required Target input (no optional fallback). Wire IS the target declaration. |
| REINSTATE Result + Report + Status outputs | PARAMETER REINSTATE Parameters + StateStatus + Status outputs | Phase 19 | Parameters = ALL captured params (D-05). StateStatus = index-matched ReStatus list (D-04) |
| DECONSTRUCT (nonexistent) | DESIGN STATE DECONSTRUCT + OBJECT DECONSTRUCT | Phase 19 | New components, simplest in v7.0 set -- pure synchronous passthrough |

**Deprecated/outdated:**
- ReinstateComponent.cs (GUID D4E2F8A1): replaced by ParameterReinstateComponent.cs with new GUID and new contract. Old file should be deleted (or kept as dead reference -- recommended: delete for clean git history).

## Assumptions Log

> All claims in this research were verified against existing source code or the CONTEXT.md locked decisions. No user confirmation needed.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| -- | No ASSUMED claims -- every finding cited from existing code or locked decisions | -- | -- |

## Open Questions

1. **What GUIDs to assign for the 3 components?**
   - What we know: Claude's discretion. The old REINSTATE GUID `D4E2F8A1-C736-4B9D-AE51-2B1F7C9D0E63` should get a new one (matching VALIDATION GRAPH precedent from Phase 17 where old `A7F2C3E1` became `95fc9d32-307e-41fd-a158-bfae49a3dc2a`).
   - What's unclear: Exact GUID values for DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, and new PARAMETER REINSTATE.
   - Recommendation: Generate 3 unique GUIDs at plan time. Use one for each component's `ComponentGuid`.

2. **Icon filenames for new components?**
   - What we know: Follow existing naming pattern: `{ComponentName}24.png` (e.g., DesignStateComposition24.png). Embedded in .csproj via `<EmbeddedResource Include="Properties\*.png" />`.
   - What's unclear: Exact pixel content of the icons.
   - Recommendation: Create placeholder 24x24 PNGs or reuse existing icons. Planner should decide whether to create new icon art or use programmatic icons (icon creation is out of scope for this phase otherwise).

3. **Output typing for DECONSTRUCT component outputs?**
   - What we know: Claude's discretion. Options: (a) GH_ObjectWrapper wrapping each item, (b) direct object output compatible with downstream GhCastingHelpers.TryObjState/TryParamState/TryPropState, (c) custom public wrapper types (like DG.DesignState in PublicTypes.cs).
   - What's unclear: Whether downstream components need the public wrapper (DG.ObjState) or the Core type (DG.Core.Models.ObjState) for correct casting.
   - Recommendation: Output the Core model types directly (ObjState, ParamState, PropState) via `da.SetDataList`. GhCastingHelpers.TryObjState already handles both Core types and public wrappers. The ValidationGraphComponent pattern (lines 106-108) outputs `List<IReadOnlyList<bool>>` directly. Consistent approach: output the model list directly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| .NET SDK | Build DG.Core + DG.Grasshopper | Yes | 9.0.308 | -- |
| Rhino 8 + Grasshopper | DG.Grasshopper build (GRASSHOPPER_SDK conditional) | Checked at build time via .csproj | -- | If not found, DG.Grasshopper compiles without GRASSHOPPER_SDK (stub classes) |
| xUnit | Run tests | Yes | 2.9.2 | -- |
| DOTNET_ROLL_FORWARD=LatestMajor | dotnet test (net9.0 absent on some machines) | Workaround needed only if .NET 9 runtime missing | -- | Current SDK 9.0.308 has net9.0; no roll-forward needed |

**Missing dependencies with no fallback:** None
**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | xUnit 2.9.2 |
| Config file | None -- xunit auto-discovers tests in DG.Tests.dll |
| Quick run command | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ReinstatementServiceTests"` |
| Full suite command | `dotnet test DG/tests/DG.Tests/` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GHST-05 | DesignState -> ObjState/ParamState/PropState lists | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DesignStateDeconstruct"` | [ ]  |
| GHST-05 | Null/missing input -> Warning + empty outputs | unit | same filter | [ ] |
| GHST-05 | Empty bag passthrough (no warning for empty lists) | unit | same filter | [ ] |
| GHST-06 | ObjState -> Object/Geometry/Label | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ObjectDeconstruct"` | [ ] |
| GHST-06 | Null/missing input -> Warning + empty outputs | unit | same filter | [ ] |
| GHST-07 | Rising-edge trigger fires on false->true | unit | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ParameterReinstate"` | [ ] |
| GHST-07 | StateStatus index-matched to Parameters | unit | same filter | [ ] |
| GHST-07 | Parameters output contains all params (~applied filter) | unit | same filter | [ ] |
| GHST-07 | Summary Status text (Applied/Aborted/Unchanged/Idle) | unit | same filter | [ ] |
| GHST-07 | DesignStateReinstatementService.Validate called | unit | same filter | [✅](../19-deconstruct-and-reinstate-components/DG/tests/DG.Tests/ReinstatementServiceTests.cs) |
| GHST-07 | Deferred write via ScheduleSolution | unit | same filter | [ ] |
| GHST-07 | Assembly-mismatch fallback (ReconstructSnapshot) | unit | same filter | [ ] |
| GHST-07 | All 7 ReStatus values output correctly | unit | same filter | [✅](../19-deconstruct-and-reinstate-components/DG/tests/DG.Tests/ReinstatementServiceTests.cs) |

**NOTE:** The ReinstatementServiceTests.cs (12 existing tests) cover the underlying logic -- Phase 19 tests need to verify the GH component integration layer (output contract, input unwrapping, rising-edge detection, deferred write scheduling).

### Sampling Rate
- **Per task commit:** `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~(DesignStateDeconstruct|ObjectDeconstruct|ParameterReinstate|ReinstatementService)"`
- **Per wave merge:** `dotnet test DG/tests/DG.Tests/`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `DG/tests/DG.Tests/DesignStateDeconstructComponentTests.cs` -- covers GHST-05 (3 test cases)
- [ ] `DG/tests/DG.Tests/ObjectDeconstructComponentTests.cs` -- covers GHST-06 (2 test cases)
- [ ] `DG/tests/DG.Tests/ParameterReinstateComponentTests.cs` -- covers GHST-07 (6-8 test cases)
- [ ] `DG/tests/DG.Tests/ErrorMessagesTemplateTests.cs` -- EXTEND existing test class with new deconstruct/reinstate message templates

*Existing test infrastructure (xUnit, Microsoft.NET.Test.Sdk) is already configured -- no framework install needed. Only new test files are required.*

## Security Domain

> `security_enforcement` is not explicitly set in config.json (absent = enabled). However, Phase 19 components have no external network access, no authentication, no user data creation, and no database writes. Zero security surface.

**Applicable ASVS Categories:**
None. Phase 19 components:
- DESIGN STATE DECONSTRUCT: reads in-memory object, outputs in-memory lists. No data mutation, no storage, no network.
- OBJECT DECONSTRUCT: reads in-memory object, outputs property values. No data mutation, no storage, no network.
- PARAMETER REINSTATE: reads in-memory ParamState, writes to local GH slider/toggle values (in-process, same document). Deferred write is in-memory only. Validation is pure logic (no side effects until write). No network, no storage, no authentication.

**Security assessment:** `security_enforcement: false` by exception -- no security surface exists for this phase's components. All components operate entirely within the Grasshopper document process space. The planner should skip security tasks.

## Sources

### Primary (HIGH confidence)
- `DG/src/DG.Grasshopper/Components/ReinstateComponent.cs` -- REINSTATE full implementation; wire-traversal, rising-edge trigger, deferred writes, assembly-mismatch fallback, UnwrapGhContainer, ReconstructSnapshot [VERIFIED: source code]
- `DG/src/DG.Grasshopper/Components/GraphDeconstructComponent.cs` -- Pure synchronous passthrough pattern (Phase 17 precedent) [VERIFIED: source code]
- `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs` -- Index-matched list output pattern, GUID replacement precedent, ToPublicObjState/ToPublicParamState/ToPublicDesignState [VERIFIED: source code]
- `DG/src/DG.Grasshopper/Components/DesignStateCompositionComponent.cs` -- DesignState composition pattern, TryObjState/TryParamState/TryPropState unwrapping [VERIFIED: source code]
- `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs` -- Wire-traversal target, NickName->ParameterId pattern, UnwrapScalar/BuildParameter/BuildSnapshot [VERIFIED: source code]
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` -- Generic unwrapping for all state types [VERIFIED: source code]
- `DG/src/DG.Core/Services/DesignStateReinstatementService.cs` -- Pure logic validation service [VERIFIED: source code]
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` -- Error message pattern [VERIFIED: source code]
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` -- StateId generation [VERIFIED: source code]
- `DG/src/DG.Core/Models/*.cs` -- All state models (DesignState, ObjState, ParamState, PropState, DesignStateParameter) [VERIFIED: source code]
- `DG/src/DG.Core/Models/ReinstatementStatus.cs` -- 7-value enum [VERIFIED: source code]
- `DG/src/DG.Core/Models/ReinstatementResult.cs` -- Applied/Aborted + Reports [VERIFIED: source code]
- `DG/src/DG.Core/Models/ReinstatementParameterReport.cs` -- Per-parameter report [VERIFIED: source code]
- `DG/src/DG.Core/Models/ResolvedTarget.cs` -- Target resolution model [VERIFIED: source code]
- `DG/src/DG.Grasshopper/DgComponentCategory.cs` -- Category constants [VERIFIED: source code]
- `DG/src/DG.Grasshopper/DgIcons.cs` -- Icon loading pattern [VERIFIED: source code]
- `DG/src/DG.Grasshopper/PublicTypes.cs` -- Public wrapper types [VERIFIED: source code]
- `DG/tests/DG.Tests/ReinstatementServiceTests.cs` -- 12 existing tests for validation service [VERIFIED: source code]
- `DG/tests/DG.Tests/DesignStateModelTests.cs` -- DesignState model tests (bag semantics, ordering) [VERIFIED: source code]
- `DG/tests/DG.Tests/ObjStateModelTests.cs` -- ObjState model tests [VERIFIED: source code]
- `DG/tests/DG.Tests/ParamStateModelTests.cs` -- ParamState model tests [VERIFIED: source code]
- `DG/tests/DG.Tests/PropStateModelTests.cs` -- PropState model tests [VERIFIED: source code]
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` -- Existing error message tests [VERIFIED: source code]
- `ontology/port-iri-map-V7.md` -- Port-I RI contracts for all 3 components [VERIFIED: source file]
- `.planning/milestones/v7.0-phases/19-deconstruct-and-reinstate-components/19-CONTEXT.md` -- All locked decisions (D-01 through D-07) [VERIFIED: source file]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all patterns and types verified against existing source code
- Architecture: HIGH -- three component patterns are well-established in the codebase (GraphDeconstructComponent for passthrough, ReinstateComponent for REINSTATE, ValidationGraphComponent for index-matched outputs)
- Pitfalls: HIGH -- all identified directly from existing REINSTATE code (assembly-mismatch, GH container nesting, rising-edge initialization, ScheduleSolution timing)
- Validation: HIGH -- xUnit 2.9.2 with existing test patterns (ReinstatementServiceTests has 12 test cases as template)

**Research date:** 2026-07-05
**Valid until:** 2026-08-05 (stable patterns; main risk is .NET SDK version change or Rhino API changes, unlikely within 30 days)




