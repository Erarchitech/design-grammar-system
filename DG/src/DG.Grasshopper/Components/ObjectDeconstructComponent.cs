#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using DG.Grasshopper;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class ObjectDeconstructComponent : GH_Component
{
    private string _latestObjectRef = string.Empty;
    private object? _latestGeometry;
    private string? _latestLabel;

    public ObjectDeconstructComponent()
        : base("OBJECT DECONSTRUCT", "OBJDECON",
            "Split an ObjState into Object reference, Geometry, and Label. Pure synchronous passthrough -- no refresh required.",
            DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("7E8C9D0A-1B2C-4D3E-8F4A-5B6C7D8E9F0A");

    protected override Bitmap Icon => DgIcons.ObjectDeconstruct24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("ObjState", "ObjState",
            "DG.ObjState -- from DESIGN STATE DECONSTRUCT or OBJECT STATE. Contains ObjectRef, Geometry, Label.", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("Object", "Object",
            "ObjectRef string from ObjState.ObjectRef.", GH_ParamAccess.item);
        pManager.AddGenericParameter("Geometry", "Geometry",
            "Geometry handle from ObjState.Geometry (in-process Rhino/GH reference).", GH_ParamAccess.item);
        pManager.AddTextParameter("Label", "Label",
            "Label string from ObjState.Label.", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? input = null;
        if (!da.GetData(0, ref input))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ObjectDeconstructInputMissing());
            SetEmptyOutputs(da, "No ObjState input.");
            return;
        }

        var objState = GhCastingHelpers.TryObjState(input);
        if (objState is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.ObjectDeconstructCastFailed());
            SetEmptyOutputs(da, "Invalid ObjState.");
            return;
        }

        _latestObjectRef = objState.ObjectRef;
        _latestGeometry = objState.Geometry;
        _latestLabel = objState.Label;

        da.SetData(0, objState.ObjectRef);
        da.SetData(1, objState.Geometry);
        da.SetData(2, objState.Label);

        Message = objState.ObjectRef;
    }

    private void SetEmptyOutputs(IGH_DataAccess da, string status)
    {
        _latestObjectRef = string.Empty;
        _latestGeometry = null;
        _latestLabel = null;

        da.SetData(0, string.Empty);
        da.SetData(1, null);
        da.SetData(2, string.Empty);

        AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, status);
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ObjectDeconstructComponent
{
}
#endif
