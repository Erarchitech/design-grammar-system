#if GRASSHOPPER_SDK
using System.Drawing;
using DG.Core.Parsing;
using DG.Core.Serialization;
using DG.Core.Services;
using DG.Grasshopper.Canvas;
using DG.Grasshopper.Validation;
using Grasshopper.Kernel;

namespace DG.Grasshopper.Components;

/// <summary>
/// DG COMPUTGRAPH PUBLISH -- re-extracts the confirmed canvas structure, stamps dgIds,
/// serializes cgContextJson, and POSTs it to the DG data-service Computgraph layer
/// on a rising-edge Publish trigger. Mirrors StructureConfirmComponent's rising-edge
/// trigger pattern and ValidationPublishClient's HTTP publish shape.
/// </summary>
public sealed class ComputgraphPublishComponent : GH_Component
{
    private bool _lastApply = true; // true prevents first-solve auto-fire (StructureConfirmComponent precedent)
    private string _status = "Idle";
    private List<string> _staleEntityIds = new();

    public ComputgraphPublishComponent()
        : base(
            "DG COMPUTGRAPH PUBLISH",
            "DG COMPUTGRAPH PUBLISH",
            "Re-extracts the confirmed canvas structure and publishes it to the DG data-service Computgraph layer.",
            DgComponentCategory.Category,
            DgComponentCategory.ActionsSubcategory)
    {
    }

    // Fresh GUID -- verified unused via repo-wide grep across DG/.
    public override Guid ComponentGuid => new("E2D4A9F1-3C68-4B72-9A05-6D1E8F2C7B30");

    protected override Bitmap Icon => DgIcons.ComputgraphPublish24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddTextParameter("Project", "Project", "DG project name", GH_ParamAccess.item, "default-project");
        pManager.AddTextParameter("DataServiceUrl", "DataServiceUrl", "DG data-service base URL", GH_ParamAccess.item, "http://localhost:8000");
        pManager.AddBooleanParameter("Publish", "Publish", "Rising-edge trigger: re-extract canvas and publish to data-service once", GH_ParamAccess.item, false);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("Status", "Status", "Publish status (Idle / published / error message)", GH_ParamAccess.item);
        pManager.AddTextParameter("StaleEntityIds", "StaleEntityIds", "Entity ids present on the server but absent from the published payload (not auto-deleted)", GH_ParamAccess.list);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var project = "default-project";
        da.GetData(0, ref project);

        var dataServiceUrl = "http://localhost:8000";
        da.GetData(1, ref dataServiceUrl);

        var publishInput = false;
        da.GetData(2, ref publishInput);

        // Rising-edge detection: _lastApply starts true so first solve with Publish=true
        // does NOT auto-fire (mirrors StructureConfirmComponent's _lastApply pattern).
        var isRisingEdge = publishInput && !_lastApply;
        _lastApply = publishInput;

        if (isRisingEdge)
        {
            PublishCanvas(project, dataServiceUrl);
        }

        da.SetData(0, _status);
        da.SetDataList(1, _staleEntityIds);

        Message = _status;
    }

    /// <summary>
    /// Re-extracts the live canvas, stamps dgIds, serializes, and POSTs to the
    /// data-service. Read-before-write: never reuses a cached CgContext (T-36-A3).
    /// Everything inside this method runs on a single solve -- it is a pure read+HTTP
    /// path with no canvas mutation, so no ScheduleSolution is needed.
    /// </summary>
    private void PublishCanvas(string project, string dataServiceUrl)
    {
        try
        {
            var doc = OnPingDocument();
            if (doc is null)
            {
                _status = "What: No active Grasshopper document. " +
                          "Where: DG COMPUTGRAPH PUBLISH.PublishCanvas. " +
                          "How to fix: Open a Grasshopper definition before publishing.";
                _staleEntityIds = new List<string>();
                return;
            }

            // Read-before-write: re-extract fresh from the live canvas (T-36-A3).
            var raw = CanvasContextExtractor.ExtractRaw(doc, project);
            var context = CanvasAnnotationParser.Parse(raw);
            CgContextDgIdAssigner.AssignDgIds(context, project);
            var cgContextJson = ComputgraphContextSerializer.Serialize(context);

            var response = ComputgraphPublishClient.Publish(cgContextJson, project, dataServiceUrl);

            _status = string.IsNullOrWhiteSpace(response.Status) ? "published" : response.Status;
            _staleEntityIds = response.StaleEntityIds ?? new List<string>();
        }
        catch (InvalidOperationException ex)
        {
            _status = "What: Publishing the computgraph structure failed. " +
                      "Where: DG COMPUTGRAPH PUBLISH.PublishCanvas. " +
                      "How to fix: Ensure data-service is running and reachable at the configured DataServiceUrl, " +
                      "and verify the canvas has tagged entities (Object, Procedure, etc.). " +
                      $"Details: {ex.Message}";
            _staleEntityIds = new List<string>();
        }
        catch (Exception ex)
        {
            _status = "What: Unexpected error during computgraph publish. " +
                      "Where: DG COMPUTGRAPH PUBLISH.PublishCanvas. " +
                      "How to fix: Check the Grasshopper plugin log for details. " +
                      $"Details: {ex.Message}";
            _staleEntityIds = new List<string>();
        }
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class ComputgraphPublishComponent
{
}
#endif
