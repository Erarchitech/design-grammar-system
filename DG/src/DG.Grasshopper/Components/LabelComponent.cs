#if GRASSHOPPER_SDK
using DG.Core.Services;
using DG.Grasshopper;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class LabelComponent : GH_Component
{
    private string _latestName = string.Empty;

    public LabelComponent()
        : base("LABEL", "LABEL",
            "Show the name of a DG.Variable from the Graph.",
            DgComponentCategory.Category, DgComponentCategory.Subcategory)
    {
    }

    public override Guid ComponentGuid => new("A1B2C3D4-E5F6-7890-ABCD-EF1234567890");

    protected override Bitmap Icon => DgIcons.Label24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Var", "Var",
            "DG.Variable — a variable from the Metagraph.", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("Name", "Name",
            "The name of the variable (Variable.Name).", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? input = null;
        if (!da.GetData(0, ref input))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.LabelInputMissing());
            _latestName = string.Empty;
            da.SetData(0, _latestName);
            return;
        }

        var variable = GhCastingHelpers.TryVariable(input);
        if (variable is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ErrorMessageTemplates.LabelCastFailed());
            _latestName = string.Empty;
            da.SetData(0, _latestName);
            return;
        }

        _latestName = variable.Name ?? string.Empty;
        da.SetData(0, _latestName);
        Message = _latestName;
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class LabelComponent
{
}
#endif
