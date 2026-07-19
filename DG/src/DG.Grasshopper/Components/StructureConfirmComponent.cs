#if GRASSHOPPER_SDK
using System.Drawing;
using DG.Core.Parsing;
using DG.Grasshopper.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Undo;
using Grasshopper.Kernel.Undo.Actions;

namespace DG.Grasshopper.Components;

/// <summary>
/// DG STRUCTURE CONFIRM -- the on-canvas confirmation gate for LLM-suggested structure
/// proposals (RCGN-03). Lists pending proposals from the shared <see cref="PreviewRegistry"/>
/// and, on a rising-edge <c>Apply</c>, accepts (converts a preview <see cref="GH_Group"/> into
/// a permanent convention group with a re-derived name/color and the
/// <c>dg.recognized.&lt;guid&gt;</c> ValueTable marker) or rejects (removes the group cleanly)
/// selected proposals. Partial accept is supported: any proposal id in neither the Accept nor
/// Reject list stays pending in the registry. Never persists to Neo4j -- confirmed structure
/// only ever reaches the graph via Phase 36's publish path.
/// </summary>
public sealed class StructureConfirmComponent : GH_Component
{
    private bool _lastApply = true; // true prevents first-solve auto-fire (ParameterReinstate precedent)
    private string _status = "Idle";

    public StructureConfirmComponent()
        : base(
            "DG STRUCTURE CONFIRM",
            "DG STRUCTURE CONFIRM",
            "Lists pending LLM structure proposals and, on Apply, accepts (preview -> permanent convention group + source:recognized) or rejects (clean removal) selected proposals; partial accept supported.",
            DgComponentCategory.Category,
            DgComponentCategory.ActionsSubcategory)
    {
    }

    // Fresh GUID -- verified unused via repo-wide grep across Components/.
    public override Guid ComponentGuid => new("A4C1F7E2-9B36-4D58-8E21-7F0A5C3B9D14");

    protected override Bitmap Icon => DgIcons.StructureConfirm24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddTextParameter("Accept", "Accept", "Proposal ids to accept (or * for all)", GH_ParamAccess.list);
        pManager[0].Optional = true;
        pManager.AddTextParameter("Reject", "Reject", "Proposal ids to reject", GH_ParamAccess.list);
        pManager[1].Optional = true;
        pManager.AddBooleanParameter("Apply", "Apply", "Rising-edge trigger: apply the Accept/Reject selection once", GH_ParamAccess.item, false);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("Pending", "Pending", "Pending proposals: name, kind, confidence, member count", GH_ParamAccess.list);
        pManager.AddTextParameter("Status", "Status", "Confirm status", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        // Task 2 (35-04) replaces this stub body with the real Accept/Reject/Apply logic.
        // For now: always refresh Pending from the shared registry and report Idle.
        var pendingText = DescribePending();
        da.SetDataList(0, pendingText);
        da.SetData(1, _status);
    }

    /// <summary>
    /// Renders every <see cref="PreviewRegistry.Pending"/> entry as "name, kind, confidence,
    /// member count" (must_haves truth #1) -- member count is a live read of the on-canvas
    /// preview <see cref="GH_Group"/>'s <c>ObjectIDs.Count</c>, matching
    /// <c>CanvasListenerComponent.HandleGetPreviewStatus</c>'s precedent rather than storing a
    /// redundant count.
    /// </summary>
    private List<string> DescribePending()
    {
        var doc = OnPingDocument();

        return PreviewRegistry.Pending
            .Select(e =>
            {
                var memberCount = doc?.Objects.OfType<GH_Group>()
                    .FirstOrDefault(g => g.InstanceGuid == e.GroupGuid)?.ObjectIDs.Count ?? 0;
                var confidencePercent = (e.Confidence * 100d).ToString("F0");
                return $"{e.ProposalId}: {e.SuggestedName} ({e.Kind}, {confidencePercent}%, {memberCount} member(s))";
            })
            .ToList();
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class StructureConfirmComponent
{
}
#endif
