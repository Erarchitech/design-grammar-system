#if GRASSHOPPER_SDK
using DG.Core.Models;
using DG.Core.Services;
using DG.Grasshopper;
using Grasshopper.Kernel;
using System.Drawing;

namespace DG.Grasshopper.Components;

public sealed class GraphDeconstructComponent : GH_Component
{
    public GraphDeconstructComponent()
        : base("GRAPH DECONSTRUCT", "DECONSTRUCT",
            "Split a Database handle into 4 graph layer handles.",
            DgComponentCategory.Category, DgComponentCategory.GraphSubcategory)
    {
    }

    public override Guid ComponentGuid => new("0958A0C1-8FDE-47D6-9C3C-7131F1449F94");

    protected override Bitmap Icon => DgIcons.GraphDeconstruct24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddGenericParameter("Database", "Database",
            "DG connection object from CONNECTOR", GH_ParamAccess.item);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddGenericParameter("Metagraph", "Metagraph",
            "Metagraph layer handle", GH_ParamAccess.item);
        pManager.AddGenericParameter("Ontograph", "Ontograph",
            "Ontograph layer handle", GH_ParamAccess.item);
        pManager.AddGenericParameter("ValidGraph", "ValidGraph",
            "ValidGraph layer handle", GH_ParamAccess.item);
        pManager.AddGenericParameter("SpecGraph", "SpecGraph",
            "SpecGraph layer handle", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        object? databaseInput = null;
        if (!da.GetData(0, ref databaseInput))
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ErrorMessageTemplates.GraphDeconstructNoInput());
            return;
        }

        var connection = GhCastingHelpers.Unwrap<ConnectionInfo>(databaseInput);
        if (connection is null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ErrorMessageTemplates.GraphDeconstructCastFailed());
            return;
        }

        da.SetData(0, new global::DG.MetagraphHandle { ConnectionInfo = connection });
        da.SetData(1, new global::DG.OntographHandle { ConnectionInfo = connection });
        da.SetData(2, new global::DG.ValidGraphHandle { ConnectionInfo = connection });
        da.SetData(3, new global::DG.SpecGraphHandle { ConnectionInfo = connection });
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class GraphDeconstructComponent
{
}
#endif
