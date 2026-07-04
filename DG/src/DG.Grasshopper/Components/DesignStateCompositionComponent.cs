#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using System.Drawing;
using CoreObjState = DG.Core.Models.ObjState;
using CoreParamState = DG.Core.Models.ParamState;
using CorePropState = DG.Core.Models.PropState;

namespace DG.Grasshopper.Components;

/// <summary>
/// DESIGN STATE composition component. Aggregates independent ObjState, ParamState,
/// and PropState lists into a single aggregate DesignState with a deterministic
/// content-addressed StateId.
///
/// Usage:
///   1. Drop DESIGN STATE on the canvas.
///   2. Wire OBJECT STATE component output → "ObjState" input.
///   3. Wire PARAMETER STATE component output → "ParamState" input.
///   4. Wire PROPERTY STATE component output → "PropState" input.
///   5. Wire the "DesignState" output to VALIDATOR.DesignState.
///
/// Inputs are independent bags (D-02) — no cross-index alignment enforced.
/// Output is a SINGLE DesignState, not a list (D-01).
/// Filename: DesignStateCompositionComponent.cs (avoids collision with renamed ParameterStateComponent per Research Finding 7).
/// </summary>
public sealed class DesignStateCompositionComponent : GH_Component
{
    public DesignStateCompositionComponent()
        : base(
            "DESIGN STATE",
            "DSGSTATE",
            "Compose all wired ObjState, ParamState, and PropState inputs into a single aggregate DesignState with a deterministic StateId.",
            DgComponentCategory.Category,
            DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("E7F2D8B1-6A3C-4F9E-8B0D-5C1A7E3F2D4B");

    protected override Bitmap Icon => DgIcons.DesignStateComposition24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "ObjState",
            "ObjState",
            "ObjState list from OBJECT STATE component.",
            GH_ParamAccess.list);
        pManager[0].Optional = true;

        pManager.AddGenericParameter(
            "ParamState",
            "ParamState",
            "ParamState list from PARAMETER STATE component.",
            GH_ParamAccess.list);
        pManager[1].Optional = true;

        pManager.AddGenericParameter(
            "PropState",
            "PropState",
            "PropState list from PROPERTY STATE component.",
            GH_ParamAccess.list);
        pManager[2].Optional = true;
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter(
            "DesignState",
            "DesignState",
            "DG.DesignState — a single aggregate state (NOT a list). Wire to VALIDATOR.DesignState input or downstream state consumers.",
            GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var objStateInputs = new List<object?>();
        var paramStateInputs = new List<object?>();
        var propStateInputs = new List<object?>();

        da.GetDataList(0, objStateInputs);
        da.GetDataList(1, paramStateInputs);
        da.GetDataList(2, propStateInputs);

        // Unwrap each input list
        var objStates = new List<CoreObjState>();
        foreach (var input in objStateInputs)
        {
            var unwrapped = GhCastingHelpers.TryObjState(input);
            if (unwrapped is not null)
                objStates.Add(unwrapped);
        }

        var paramStates = new List<CoreParamState>();
        foreach (var input in paramStateInputs)
        {
            var unwrapped = GhCastingHelpers.TryParamState(input);
            if (unwrapped is not null)
                paramStates.Add(unwrapped);
        }

        var propStates = new List<CorePropState>();
        foreach (var input in propStateInputs)
        {
            var unwrapped = GhCastingHelpers.TryPropState(input);
            if (unwrapped is not null)
                propStates.Add(unwrapped);
        }

        // Guard: at least one state must be present
        if (objStates.Count == 0 && paramStates.Count == 0 && propStates.Count == 0)
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Warning,
                ErrorMessageTemplates.DesignStateNoInputs());
            da.SetData(0, null);
            Message = "No inputs";
            return;
        }

        // Collect all member StateIds for aggregate hash (D-04)
        var memberStateIds = new List<string>();
        foreach (var os in objStates)
            memberStateIds.Add(os.StateId);
        foreach (var ps in paramStates)
            memberStateIds.Add(ps.StateId);
        foreach (var ps in propStates)
            memberStateIds.Add(ps.StateId);

        var designStateId = DesignStateIdGenerator.ComputeDesignStateId(memberStateIds);

        var designState = new DG.DesignState
        {
            StateId = designStateId,
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        // Preserve wiring order within each list (Claude's discretion per CONTEXT.md)
        foreach (var os in objStates)
            designState.ObjStates.Add(os);
        foreach (var ps in paramStates)
            designState.ParamStates.Add(ps);
        foreach (var ps in propStates)
            designState.PropStates.Add(ps);

        da.SetData(0, designState);
        Message = $"{objStates.Count}O/{paramStates.Count}P/{propStates.Count}Pr";
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class DesignStateCompositionComponent
{
}
#endif
