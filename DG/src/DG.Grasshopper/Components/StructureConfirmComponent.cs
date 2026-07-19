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
        var acceptIds = new List<string>();
        da.GetDataList(0, acceptIds);

        var rejectIds = new List<string>();
        da.GetDataList(1, rejectIds);

        var applyInput = false;
        da.GetData(2, ref applyInput);

        // Rising-edge detection: _lastApply starts true so first solve with Apply=true does
        // NOT auto-fire (mirrors ParameterReinstateComponent's _lastApplyInput).
        var isRisingEdge = applyInput && !_lastApply;
        _lastApply = applyInput;

        if (isRisingEdge)
        {
            ApplySelection(acceptIds, rejectIds);
        }

        // Always refresh Pending from the shared registry, regardless of Apply.
        da.SetDataList(0, DescribePending());
        da.SetData(1, _status);
    }

    /// <summary>
    /// Resolves the Accept/Reject id sets (expanding a literal <c>*</c> Accept entry to every
    /// pending proposal id), warns and skips any id not currently pending, then defers the
    /// actual canvas mutation via <see cref="GH_Document.ScheduleSolution"/> -- the GH SDK
    /// forbids document mutation (AddObject/RemoveObject/group edits) while a solution is in
    /// progress (RESEARCH.md Pitfall 1, same discipline as EntityTagComponent/ObjectMarkerComponent).
    /// </summary>
    private void ApplySelection(IReadOnlyList<string> acceptIds, IReadOnlyList<string> rejectIds)
    {
        var pending = PreviewRegistry.Pending;
        var pendingIds = pending.Select(e => e.ProposalId).ToHashSet(StringComparer.Ordinal);

        var acceptAll = acceptIds.Any(id => string.Equals(id?.Trim(), "*", StringComparison.Ordinal));
        var acceptSet = acceptAll
            ? new HashSet<string>(pendingIds, StringComparer.Ordinal)
            : new HashSet<string>(
                acceptIds.Where(id => !string.IsNullOrWhiteSpace(id)).Select(id => id.Trim()),
                StringComparer.Ordinal);

        var rejectSet = new HashSet<string>(
            rejectIds.Where(id => !string.IsNullOrWhiteSpace(id)).Select(id => id.Trim()),
            StringComparer.Ordinal);

        // Unknown ids (not currently pending) get a Warning and are dropped from both sets so
        // the scheduled mutation never looks them up.
        foreach (var id in acceptSet.Concat(rejectSet).Distinct(StringComparer.Ordinal).ToList())
        {
            if (!pendingIds.Contains(id))
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    $"What: Proposal id '{id}' is not pending. " +
                    "Where: StructureConfirmComponent.SolveInstance. " +
                    "How to fix: check DG STRUCTURE CONFIRM's Pending output for valid ids before Accept/Reject.");
                acceptSet.Remove(id);
                rejectSet.Remove(id);
            }
        }

        var doc = OnPingDocument();
        if (doc is null)
        {
            _status = "Warning: No active document.";
            return;
        }

        try
        {
            doc.ScheduleSolution(1, currentDoc => ApplyToDocument(currentDoc, acceptSet, rejectSet));
        }
        catch (Exception ex)
        {
            // Never let a scheduling failure escape SolveInstance.
            _status = $"Error: Failed to schedule confirm mutation: {ex.Message}";
        }
    }

    /// <summary>
    /// Runs inside <see cref="GH_Document.ScheduleSolution"/> -- the actual document mutation.
    /// Accept: read-before-write re-derives the permanent nickname/colour from the LIVE canvas
    /// (never the possibly-stale LLM <c>suggestedName</c>, T-35-06) and writes the
    /// <c>dg.recognized.&lt;guid&gt;</c> ValueTable marker. Reject: removes the group. Both
    /// remove the proposal from <see cref="PreviewRegistry"/>; ids in neither set stay pending
    /// (partial accept). One <see cref="GH_UndoRecord"/> covers the whole Apply.
    /// </summary>
    private void ApplyToDocument(GH_Document currentDoc, HashSet<string> acceptIds, HashSet<string> rejectIds)
    {
        try
        {
            var record = new GH_UndoRecord("DG confirm structure");
            var accepted = 0;
            var rejected = 0;

            foreach (var id in acceptIds)
            {
                if (!PreviewRegistry.TryGet(id, out var entry))
                {
                    continue;
                }

                var group = currentDoc.Objects.OfType<GH_Group>()
                    .FirstOrDefault(g => g.InstanceGuid == entry.GroupGuid);
                if (group is null)
                {
                    // Preview group already gone from the canvas -- nothing to restyle, just
                    // drop the now-stale registry entry.
                    PreviewRegistry.Remove(id);
                    continue;
                }

                // Read-before-write (T-35-06): re-derive the permanent nickname from the LIVE
                // canvas, never the possibly-stale LLM suggestedName -- avoids a collision if
                // the architect tagged something between recognition and confirmation.
                var raw = CanvasContextExtractor.ExtractRaw(currentDoc, string.Empty);

                int? patternIndex = entry.Kind == EntityTagKind.Pat
                    ? CanvasAnnotationNameFactory.NextFreePatternIndex(raw.Groups.Select(g => g.Nickname), entry.ProcedureIndex)
                    : null;

                string nickname;
                try
                {
                    // CR-01: the LLM emits suggestedName as a FULL convention name
                    // ("11_IntF_ParSplitAt"); ForEntity expects the BARE trailing Name and
                    // would reject the reserved infix (and double-prefix the result), so
                    // strip the convention prefix before re-deriving the permanent name.
                    var bareName = CanvasAnnotationNameFactory.StripConventionPrefix(entry.Kind, entry.SuggestedName);
                    nickname = CanvasAnnotationNameFactory.ForEntity(entry.Kind, entry.ProcedureIndex, bareName, patternIndex);
                }
                catch (ArgumentException ex)
                {
                    AddRuntimeMessage(
                        GH_RuntimeMessageLevel.Warning,
                        $"What: Could not derive a convention name for proposal '{id}' ({ex.Message}). " +
                        "Where: StructureConfirmComponent.SolveInstance. " +
                        "How to fix: rename the proposal's suggested name or tag it manually with DG ENTITY TAG instead.");
                    continue;
                }

                record.AddAction(new GH_GenericObjectAction(group));

                var nested = entry.Kind == EntityTagKind.Pat && IsNestedInAnotherPattern(raw, group);

                group.NickName = nickname;
                group.Colour = CanvasAnnotationStyles.ForKind(entry.Kind, nested);
                group.ExpireCaches();

                currentDoc.ValueTable.SetValue($"dg.recognized.{group.InstanceGuid}", "true");

                PreviewRegistry.Remove(id);
                accepted++;
            }

            foreach (var id in rejectIds)
            {
                if (!PreviewRegistry.TryGet(id, out var entry))
                {
                    continue;
                }

                var group = currentDoc.Objects.OfType<GH_Group>()
                    .FirstOrDefault(g => g.InstanceGuid == entry.GroupGuid);
                if (group is not null)
                {
                    record.AddAction(new GH_GenericObjectAction(group));
                    currentDoc.RemoveObject(group, false);
                }

                PreviewRegistry.Remove(id);
                rejected++;
            }

            if (accepted > 0 || rejected > 0)
            {
                currentDoc.UndoServer.PushUndoRecord(record);
            }

            global::Grasshopper.Instances.InvalidateCanvas();
            _status = $"Accepted {accepted}, rejected {rejected}, {PreviewRegistry.Pending.Count} pending";
            ExpireSolution(false);
        }
        catch (Exception ex)
        {
            // Never throw out of the scheduled callback -- surface the failure in Status.
            _status = $"Error: {ex.Message}";
        }
    }

    /// <summary>
    /// True when <paramref name="group"/>'s members are a non-empty subset of another Pattern
    /// group's members (native nesting -- CanvasContextExtractor.NestedGroupIds contract),
    /// mirroring EntityTagComponent's host-group detection so an accepted nested Pattern gets
    /// the purple <see cref="CanvasAnnotationStyles.NestedPattern"/> variant instead of the
    /// plain orange Pattern colour.
    /// </summary>
    private static bool IsNestedInAnotherPattern(DG.Core.Models.Computgraph.RawCanvas raw, GH_Group group)
    {
        var memberIds = group.ObjectIDs.Select(id => id.ToString()).ToList();
        if (memberIds.Count == 0)
        {
            return false;
        }

        return raw.Groups
            .Where(g => g.Nickname.Contains(CanvasAnnotationGrammar.PatternInfix, StringComparison.Ordinal))
            .Where(g => !string.Equals(g.Nickname, group.NickName, StringComparison.Ordinal))
            .Any(g => g.MemberIds.Count > 0 && memberIds.All(id => g.MemberIds.Contains(id)));
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
