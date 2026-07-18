#if GRASSHOPPER_SDK
using System.Drawing;
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;
using DG.Grasshopper.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;

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
    private string? _lastError; // deferred-mutation failure, re-emitted on re-solve (WR-03)

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

        object? classInput = null;
        da.GetData(1, ref classInput);
        var ontologyClass = GhCastingHelpers.Unwrap<global::DG.OntologyClass>(classInput);

        var algorithmIndex = 1;
        da.GetData(2, ref algorithmIndex);

        if (string.IsNullOrWhiteSpace(objectName))
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Warning,
                "What: ObjectName is empty or whitespace. " +
                "Where: ObjectMarkerComponent.SolveInstance. " +
                "How to fix: supply a non-empty, non-whitespace ObjectName.");
            da.SetData(0, objectName);
            da.SetData(1, algorithmIndex);
            da.SetData(2, "Warning: ObjectName is required.");
            return;
        }

        if (algorithmIndex < 1 || algorithmIndex > 9)
        {
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Warning,
                "What: AlgorithmIndex is outside the valid single-digit range. " +
                "Where: ObjectMarkerComponent.SolveInstance. " +
                "How to fix: pass a value between 1 and 9.");
            da.SetData(0, objectName);
            da.SetData(1, algorithmIndex);
            da.SetData(2, "Warning: AlgorithmIndex must be 1-9.");
            return;
        }

        string objectScribbleText;
        string algorithmScribbleText;
        try
        {
            CanvasAnnotationNameFactory.ValidateName(objectName.Trim());
            objectScribbleText = CanvasAnnotationNameFactory.ForObjectScribble(objectName);
            algorithmScribbleText = CanvasAnnotationNameFactory.ForAlgorithmScribble(algorithmIndex);
        }
        catch (ArgumentException ex)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ex.Message);
            da.SetData(0, objectName);
            da.SetData(1, algorithmIndex);
            da.SetData(2, $"Warning: {ex.Message}");
            return;
        }

        var doc = OnPingDocument();
        var raw = CanvasContextExtractor.ExtractRaw(doc, string.Empty);
        var context = CanvasAnnotationParser.Parse(raw);

        var existingAlgorithm = context.Algorithms.FirstOrDefault(a => a.Index == algorithmIndex);
        if (context.Object is not null && existingAlgorithm is not null)
        {
            // REPORT mode -- idempotent read-before-write (TAGC-01): the canvas is
            // already annotated, so nothing is mutated.
            da.SetData(0, context.Object.Name);
            da.SetData(1, existingAlgorithm.Index);
            da.SetData(2, $"Read existing: OBJECT - {context.Object.Name} / {existingAlgorithm.Index}_ALGORITHM");
            return;
        }

        // CREATE mode -- document mutation is deferred via ScheduleSolution: the GH SDK
        // forbids AddObject while a solution is in progress (RESEARCH.md Pitfall 1/A3).
        var needsObjectScribble = context.Object is null;
        var needsAlgorithmScribble = existingAlgorithm is null;
        var classIri = ontologyClass?.Iri;

        // WR-03: a failure inside the previously scheduled mutation is carried in state --
        // re-emit it here so a re-solve (which wipes runtime messages) still shows it.
        if (_lastError is not null)
        {
            AddRuntimeMessage(GH_RuntimeMessageLevel.Error, _lastError);
        }

        doc?.ScheduleSolution(1, currentDoc =>
        {
            try
            {
                if (needsObjectScribble)
                {
                    AddScribble(currentDoc, objectScribbleText, new PointF(10f, 10f));
                }

                if (needsAlgorithmScribble)
                {
                    AddScribble(currentDoc, algorithmScribbleText, new PointF(10f, 60f));
                }

                if (!string.IsNullOrWhiteSpace(classIri))
                {
                    currentDoc.ValueTable.SetValue("dg.objectClassIri", classIri);
                }

                global::Grasshopper.Instances.InvalidateCanvas();
                _lastError = null;
            }
            catch (Exception ex)
            {
                // WR-03: state-tracked so SolveInstance can re-emit the failure after the
                // forced re-solve wipes this transient runtime message.
                Message = "Scribble creation failed";
                _lastError = $"Failed to create scribble(s): {ex.Message}";
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, _lastError);
            }

            ExpireSolution(false);
        });

        da.SetData(0, objectName);
        da.SetData(1, algorithmIndex);
        da.SetData(2, $"Created: OBJECT - {objectName} / {algorithmIndex}_ALGORITHM");
    }

    private static void AddScribble(GH_Document doc, string text, PointF pivot)
    {
        var scrib = new GH_Scribble();
        scrib.CreateAttributes();
        scrib.Text = text;
        scrib.Font = new Font("Microsoft Sans Serif", 30f, FontStyle.Regular);
        scrib.Attributes.Pivot = pivot;
        doc.AddObject(scrib, false);
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ObjectMarkerComponent
{
}
#endif
