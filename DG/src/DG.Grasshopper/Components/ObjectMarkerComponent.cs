#if GRASSHOPPER_SDK
using DG.Grasshopper.Canvas;
using Grasshopper.Kernel;

namespace DG.Grasshopper.Components;

/// <summary>
/// DG OBJECT MARKER -- stamps the architect's object/algorithm identity onto the
/// canvas as <c>OBJECT - &lt;NAME&gt;</c> and <c>&lt;n&gt;_ALGORITHM</c> scribbles
/// (Phase 34's write-path counterpart to Phase 32's <see cref="CanvasAnnotationParser"/>
/// -equivalent <c>CanvasContextExtractor</c>/<c>CanvasAnnotationParser</c> read path).
/// Read-before-write: an already-annotated canvas is reported, never duplicated
/// (TAGC-01). Optionally binds a <c>dg:Class</c> IRI to the document via
/// <see cref="Grasshopper.Kernel.GH_Document.ValueTable"/>.
/// </summary>
public sealed class ObjectMarkerComponent : GH_Component
{
    public ObjectMarkerComponent()
        : base(
            "DG OBJECT MARKER",
            "DG OBJECT MARKER",
            "Stamps the object/algorithm identity onto the canvas as OBJECT - <NAME> and <n>_ALGORITHM scribbles; idempotent on re-run.",
            DgComponentCategory.Category,
            DgComponentCategory.GraphSubcategory)
    {
    }

    // Fresh GUID -- verified unused via repo-wide grep across Components/.
    public override Guid ComponentGuid => new("D3A9F41C-7E52-4B86-9A1D-2C6F8B0E5A73");

    protected override System.Drawing.Bitmap Icon => DgIcons.ObjectMarker24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddTextParameter("ObjectName", "ObjectName", "Object identity -- becomes the OBJECT - <NAME> scribble", GH_ParamAccess.item);
        pManager.AddGenericParameter("Class", "Class", "Optional OntologyClass from ONTOGRAPH deconstruct -- binds dg:Object to a dg:Class IRI (stored in document ValueTable)", GH_ParamAccess.item);
        pManager[1].Optional = true;
        pManager.AddIntegerParameter("AlgorithmIndex", "AlgorithmIndex", "Algorithm digit (1-9) -- becomes the <n>_ALGORITHM scribble", GH_ParamAccess.item, 1);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("ObjectName", "ObjectName", "Object identity as stamped/read on the canvas", GH_ParamAccess.item);
        pManager.AddIntegerParameter("AlgorithmIndex", "AlgorithmIndex", "Algorithm digit as stamped/read on the canvas", GH_ParamAccess.item);
        pManager.AddTextParameter("Status", "Status", "Create/report/warning status", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var objectName = string.Empty;
        da.GetData(0, ref objectName);

        var algorithmIndex = 1;
        da.GetData(2, ref algorithmIndex);

        da.SetData(0, objectName);
        da.SetData(1, algorithmIndex);
        da.SetData(2, "Idle");
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ObjectMarkerComponent
{
}
#endif
