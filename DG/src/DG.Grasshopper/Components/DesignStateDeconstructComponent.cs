#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using DG.Grasshopper;
using Grasshopper.Kernel;
using System.Drawing;

using CoreObjState = DG.Core.Models.ObjState;
using CoreParamState = DG.Core.Models.ParamState;
using CorePropState = DG.Core.Models.PropState;
using CoreDesignState = DG.Core.Models.DesignState;

namespace DG.Grasshopper.Components;

public sealed class DesignStateDeconstructComponent : GH_Component
{
    private List<CoreObjState> _latestObjStates = new();
    private List<CoreParamState> _latestParamStates = new();
    private List<CorePropState> _latestPropStates = new();

    public DesignStateDeconstructComponent()
        : base("DESIGN STATE DECONSTRUCT", "DSGDECON",
            "Split a DesignState into ObjState, ParamState, and PropState lists. Pure synchronous passthrough -- no refresh required.",
            DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("6D7B8C9D-0E1F-4A2B-8C3D-4E5F6A7B8C9D");

    protected override Bitmap Icon => DgIcons.DesignStateDeconstruct24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("DesignState", "DesignState",
            "DG.DesignState -- aggregate state from DESIGN STATE or VALIDATION GRAPH.", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("ObjState", "ObjState",
            "List of ObjState objects. From DesignState.ObjStates.", GH_ParamAccess.list);
        pManager.AddGenericParameter("ParamState", "ParamState",
            "List of ParamState objects. From DesignState.ParamStates.", GH_ParamAccess.list);
        pManager.AddGenericParameter("PropState", "PropState",
            "List of PropState objects. From DesignState.PropStates.", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? input = null;
        if (!da.GetData(0, ref input))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.DesignStateDeconstructInputMissing());
            SetEmptyOutputs(da, "No DesignState input.");
            return;
        }

        var designState = GhCastingHelpers.TryDesignState(input);
        if (designState is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.DesignStateDeconstructCastFailed());
            SetEmptyOutputs(da, "Invalid DesignState.");
            return;
        }

        _latestObjStates = designState.ObjStates;
        _latestParamStates = designState.ParamStates;
        _latestPropStates = designState.PropStates;

        da.SetDataList(0, designState.ObjStates);
        da.SetDataList(1, designState.ParamStates);
        da.SetDataList(2, designState.PropStates);

        Message = $"{designState.ObjStates.Count}O/{designState.ParamStates.Count}P/{designState.PropStates.Count}Pr";
    }

    private void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        _latestObjStates = new List<CoreObjState>();
        _latestParamStates = new List<CoreParamState>();
        _latestPropStates = new List<CorePropState>();

        da.SetDataList(0, _latestObjStates);
        da.SetDataList(1, _latestParamStates);
        da.SetDataList(2, _latestPropStates);

        AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, status);
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class DesignStateDeconstructComponent
{
}
#endif
