#if GRASSHOPPER_SDK
using System.Drawing;
using System.Globalization;
using DG.Core.Parsing;
using DG.Grasshopper.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Undo;
using Grasshopper.Kernel.Undo.Actions;

namespace DG.Grasshopper.Components;

/// <summary>
/// DG ENTITY TAG -- wraps the current manual canvas selection into a convention-named,
/// convention-colored <see cref="GH_Group"/> for a chosen <see cref="EntityTagKind"/>
/// (Proc/Pat/Var/Const/Emg/IntF). Auto-increments the Pattern index, nests inside an
/// enclosing Pattern group automatically (native nesting -- CanvasContextExtractor's
/// NestedGroupIds contract), updates membership on re-tag (same nickname) instead of
/// creating a duplicate group, and is undoable via an explicit <see cref="GH_UndoRecord"/>
/// (RESEARCH.md Perplexity Verification Addendum &#167;2 -- <see cref="GH_Document"/> has no
/// single-call "record this add" helper in the official API; the explicit record + action
/// composition below is the verified path). Second half of manual tagging (TAGC-02) and the
/// ground-truth round-trip (TAGC-03).
/// </summary>
public sealed class EntityTagComponent : GH_Component
{
    private bool _lastTagInput = true; // true prevents first-solve auto-fire
    private string _lastGroupName = string.Empty;
    private int _lastMemberCount;
    private string _status = "Idle";
    private string? _lastError; // deferred-mutation failure, re-emitted post-expire (WR-03)

    public EntityTagComponent()
        : base(
            "DG ENTITY TAG",
            "DG ENTITY TAG",
            "Wraps the current canvas selection into a convention-named, convention-colored group for a chosen entity kind; auto-increments the Pattern index, nests inside an enclosing Pattern automatically, undoable.",
            DgComponentCategory.Category,
            DgComponentCategory.GraphSubcategory)
    {
    }

    // Fresh GUID -- verified unused via repo-wide grep across Components/.
    public override Guid ComponentGuid => new("C1E7B4A9-3D82-4F65-8B0A-9E2D5C7F1A64");

    protected override Bitmap Icon => DgIcons.EntityTag24;

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddTextParameter("Kind", "Kind", "Entity kind: Proc | Pat | Var | Const | Emg | IntF (wired from the auto-created value list)", GH_ParamAccess.item);
        pManager.AddTextParameter("Name", "Name", "Entity name (empty for Pat auto-index)", GH_ParamAccess.item);
        pManager[1].Optional = true;
        pManager.AddIntegerParameter("ProcIndex", "ProcIndex", "Full NN token, e.g. 11 = algorithm 1 procedure 1", GH_ParamAccess.item);
        pManager.AddBooleanParameter("Tag", "Tag", "Rising-edge trigger -- fires on false->true. Use a Button or Boolean Toggle.", GH_ParamAccess.item, false);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddTextParameter("GroupName", "GroupName", "Nickname of the tag group created/updated", GH_ParamAccess.item);
        pManager.AddIntegerParameter("MemberCount", "MemberCount", "Number of objects wrapped by the tag group", GH_ParamAccess.item);
        pManager.AddTextParameter("Status", "Status", "Create/update/warning status", GH_ParamAccess.item);
    }

    /// <summary>
    /// Auto-creates a six-item <see cref="GH_ValueList"/> wired to Kind on first placement
    /// (new SDK surface -- gated by this plan's checkpoint:human-verify). Deferred via
    /// <see cref="GH_Document.ScheduleSolution(int, GH_ScheduleDelegate)"/> since a document
    /// cannot be mutated synchronously from AddedToDocument either.
    /// </summary>
    public override void AddedToDocument(GH_Document document)
    {
        base.AddedToDocument(document);

        try
        {
            if (Params.Input.Count == 0 || Params.Input[0].Sources.Count > 0)
            {
                return;
            }

            var pivot = Attributes.Pivot;

            document.ScheduleSolution(1, d =>
            {
                try
                {
                    // Re-check inside the delegate (WR-02): AddedToDocument also fires
                    // during file open, where wire topology may not be restored yet when
                    // the outer guard ran -- by ScheduleSolution time restoration is
                    // complete, so this is the authoritative "already wired" check.
                    if (Params.Input.Count == 0 || Params.Input[0].Sources.Count > 0)
                    {
                        return;
                    }

                    var valueList = new GH_ValueList();
                    valueList.CreateAttributes();
                    valueList.NickName = "Kind";
                    valueList.ListItems.Clear();
                    valueList.ListItems.Add(new GH_ValueListItem("Proc", "\"Proc\""));
                    valueList.ListItems.Add(new GH_ValueListItem("Pat", "\"Pat\""));
                    valueList.ListItems.Add(new GH_ValueListItem("Var", "\"Var\""));
                    valueList.ListItems.Add(new GH_ValueListItem("Const", "\"Const\""));
                    valueList.ListItems.Add(new GH_ValueListItem("Emg", "\"Emg\""));
                    valueList.ListItems.Add(new GH_ValueListItem("IntF", "\"IntF\""));
                    valueList.Attributes.Pivot = new PointF(pivot.X - 220f, pivot.Y - 10f);

                    d.AddObject(valueList, false);
                    Params.Input[0].AddSource(valueList);
                    global::Grasshopper.Instances.InvalidateCanvas();
                }
                catch
                {
                    // Guard: value-list auto-wiring is a UX convenience, never fatal.
                }
            });
        }
        catch
        {
            // AddedToDocument must never throw.
        }
    }

    protected override void SolveInstance(IGH_DataAccess da)
    {
        var kindText = string.Empty;
        da.GetData(0, ref kindText);

        var name = string.Empty;
        da.GetData(1, ref name);

        var procIndex = 0;
        da.GetData(2, ref procIndex);

        var tagInput = false;
        da.GetData(3, ref tagInput);

        // Rising-edge detection: _lastTagInput starts true so first solve with Tag=true
        // does NOT auto-fire (mirrors ParameterReinstateComponent's _lastApplyInput).
        var isRisingEdge = tagInput && !_lastTagInput;
        _lastTagInput = tagInput;

        if (!isRisingEdge)
        {
            // WR-03: the scheduled mutation ends with ExpireSolution, whose re-solve wipes
            // runtime messages added inside the delegate -- so a deferred failure is carried
            // in _lastError and re-emitted here on the post-expire pass.
            if (_lastError is not null)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, _lastError);
            }

            SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
            return;
        }

        _lastError = null; // new attempt -- stale deferred failure no longer applies

        var kind = MapKind(kindText);
        if (kind is null)
        {
            _status = "Warning: Kind must be one of Proc, Pat, Var, Const, Emg, IntF.";
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Warning,
                "What: Kind is missing or unrecognized. " +
                "Where: EntityTagComponent.SolveInstance. " +
                "How to fix: set Kind to one of Proc, Pat, Var, Const, Emg, IntF (wire from the auto-created value list).");
            SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
            return;
        }

        var doc = OnPingDocument();
        if (doc is null)
        {
            _status = "Warning: No active document.";
            SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
            return;
        }

        // Selection reading -- same shape as CanvasListenerComponent.ReadSelectedGuids,
        // kept as document objects so the group can wrap InstanceGuids directly.
        var selected = doc.Objects.Where(o => o.Attributes is { Selected: true }).ToList();
        if (selected.Count == 0)
        {
            _status = "Warning: No objects selected -- nothing tagged.";
            AddRuntimeMessage(
                GH_RuntimeMessageLevel.Warning,
                "What: No canvas objects are selected. " +
                "Where: EntityTagComponent.SolveInstance. " +
                "How to fix: select one or more objects on the canvas before pressing Tag.");
            SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
            return;
        }

        var selectedIds = selected.Select(o => o.InstanceGuid.ToString()).ToList();

        // Read-before-write: raw canvas groups drive next-free-index, cross-Proc conflict
        // detection, and nested-Pattern-host detection.
        var raw = CanvasContextExtractor.ExtractRaw(doc, string.Empty);

        // Guard rail (T-34-01 adjacent): a selection spanning two different existing
        // Proc groups is ambiguous unless the user is explicitly tagging a new Proc.
        if (kind != EntityTagKind.Proc)
        {
            var touchedProcGroups = raw.Groups
                .Where(g => g.Nickname.Contains(CanvasAnnotationGrammar.ProcedureInfix, StringComparison.Ordinal))
                .Where(g => g.MemberIds.Any(id => selectedIds.Contains(id)))
                .Select(g => g.Nickname)
                .Distinct(StringComparer.Ordinal)
                .ToList();

            if (touchedProcGroups.Count > 1)
            {
                _status = $"Warning: Selection spans multiple Procedure groups ({string.Join(", ", touchedProcGroups)}).";
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    $"What: The current selection touches {touchedProcGroups.Count} different Procedure groups " +
                    $"({string.Join(", ", touchedProcGroups)}). " +
                    "Where: EntityTagComponent.SolveInstance. " +
                    "How to fix: select objects that belong to a single Procedure group before tagging a non-Proc entity.");
                SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
                return;
            }
        }

        // Pattern index: re-tag detection first (CR-01) -- reuse the index of an existing
        // NN_Pat_* group whose member set equals the current selection so the update branch
        // in TagOrUpdateGroup fires instead of stacking a duplicate Pattern; otherwise
        // auto-increment to the next-free integer index under the given NN
        // (CanvasAnnotationNameFactory.ForEntity requires it for Pat).
        // WR-09: the equality is computed over NON-group members, symmetric on both sides --
        // a Pattern hosting a nested child group carries that child's InstanceGuid in
        // MemberIds (AttachToHost adds it), which would false-negative an identical-selection
        // re-tag and resurrect the CR-01 duplicate+nest. Filtering group guids from both the
        // group's members and the selection also tolerates a drag-selection that happens to
        // include the nested child group object itself.
        int? patternIndex = null;
        string? retagTargetNickname = null;
        if (kind == EntityTagKind.Pat)
        {
            var patPrefix = procIndex.ToString(CultureInfo.InvariantCulture) + CanvasAnnotationGrammar.PatternInfix;
            var groupGuids = doc.Objects.OfType<GH_Group>()
                .Select(g => g.InstanceGuid.ToString())
                .ToHashSet(StringComparer.Ordinal);
            var selectedCore = selectedIds.Where(id => !groupGuids.Contains(id)).ToList();
            var existingPat = raw.Groups.FirstOrDefault(g =>
            {
                if (!g.Nickname.StartsWith(patPrefix, StringComparison.Ordinal))
                {
                    return false;
                }

                var core = g.MemberIds.Where(id => !groupGuids.Contains(id)).ToList();
                return core.Count == selectedCore.Count && selectedCore.All(id => core.Contains(id));
            });

            if (existingPat is not null && TryExtractPatternIndex(existingPat.Nickname, patPrefix, out var reusedIndex))
            {
                patternIndex = reusedIndex;
                retagTargetNickname = existingPat.Nickname;
            }
            else
            {
                patternIndex = CanvasAnnotationNameFactory.NextFreePatternIndex(raw.Groups.Select(g => g.Nickname), procIndex);
            }
        }

        string nickname;
        try
        {
            // ForEntity validates Name (reserved tokens/whitespace/newline, T-34-04) and
            // ProcIndex range internally -- a single try/catch covers both guard rails.
            nickname = CanvasAnnotationNameFactory.ForEntity(kind.Value, procIndex, name ?? string.Empty, patternIndex);
        }
        catch (ArgumentException ex)
        {
            _status = $"Warning: {ex.Message}";
            AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ex.Message);
            SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
            return;
        }

        // Nesting detection: the selection is a (non-empty) subset of an existing
        // Pattern group's members -> native nesting (host group's ObjectIDs gains the new
        // group's InstanceGuid; CanvasContextExtractor.TryAddGroup picks it up as-is).
        // The re-tag target is excluded so a re-tagged Pattern is never treated as its
        // own host (CR-01).
        var hostGroupNickname = raw.Groups
            .Where(g => g.Nickname.Contains(CanvasAnnotationGrammar.PatternInfix, StringComparison.Ordinal))
            .Where(g => retagTargetNickname is null || !string.Equals(g.Nickname, retagTargetNickname, StringComparison.Ordinal))
            .Where(g => g.MemberIds.Count > 0 && selectedIds.All(id => g.MemberIds.Contains(id)))
            .OrderBy(g => g.MemberIds.Count)
            .Select(g => g.Nickname)
            .FirstOrDefault();

        var nested = hostGroupNickname is not null;
        var colour = CanvasAnnotationStyles.ForKind(kind.Value, nested);
        var memberCount = selected.Count;

        // Mutation deferred via ScheduleSolution -- the GH SDK forbids AddObject/group
        // mutation while a solution is in progress (RESEARCH.md Pitfall 1).
        doc.ScheduleSolution(1, currentDoc =>
        {
            try
            {
                TagOrUpdateGroup(currentDoc, nickname, colour, selected, hostGroupNickname, retagTargetNickname);
                global::Grasshopper.Instances.InvalidateCanvas();
                _lastError = null;
            }
            catch (Exception ex)
            {
                // WR-03: a message added here would be wiped by the ExpireSolution re-solve,
                // so the failure is carried in component state (_lastError/_status) and
                // re-emitted from SolveInstance on the post-expire pass.
                Message = "Tag failed";
                _lastError = $"Failed to create/update tag group: {ex.Message}";
                _status = $"Error: {_lastError}";
            }

            ExpireSolution(false);
        });

        _lastGroupName = nickname;
        _lastMemberCount = memberCount;
        _status = $"Tagged: {nickname} ({memberCount} member(s))";
        SetOutputs(da, _lastGroupName, _lastMemberCount, _status);
    }

    /// <summary>
    /// Read-before-write re-tag: an existing group with the same nickname has its
    /// membership/colour updated under a <see cref="GH_GenericObjectAction"/> (CONTEXT
    /// constraint -- same nickname updates, never duplicates). Otherwise CREATE a new
    /// <see cref="GH_Group"/> under a <see cref="GH_AddObjectAction"/> (RESEARCH.md
    /// Perplexity Verification Addendum &#167;2 -- only the group itself is a new document
    /// object; members already exist on the canvas).
    /// </summary>
    private static void TagOrUpdateGroup(
        GH_Document currentDoc,
        string nickname,
        Color colour,
        List<IGH_DocumentObject> selected,
        string? hostGroupNickname,
        string? retagTargetNickname)
    {
        // Re-tag lookup: a Pat re-tag may carry a changed trailing label, so the existing
        // group is found under its OLD nickname (retagTargetNickname) and renamed below
        // (CR-01); all other kinds update strictly by identical nickname.
        var lookupNickname = retagTargetNickname ?? nickname;
        var existingGroup = currentDoc.Objects.OfType<GH_Group>()
            .FirstOrDefault(g => string.Equals(g.NickName, lookupNickname, StringComparison.Ordinal));

        if (existingGroup is not null)
        {
            var updateRecord = new GH_UndoRecord("DG Tag Entity (update)");
            updateRecord.AddAction(new GH_GenericObjectAction(existingGroup));

            // Detach from stale hosts (WR-01): if the group was previously nested inside a
            // Pattern that no longer encloses the new selection, remove its guid from that
            // host so colour and structural nesting cannot disagree. Each touched host is
            // recorded in the same undo record BEFORE mutation.
            DetachFromStaleHosts(currentDoc, existingGroup.InstanceGuid, hostGroupNickname, updateRecord);

            // WR-08: rebuild membership through the group's own AddObject/RemoveObject API
            // instead of mutating the ObjectIDs collection directly -- Clear() bypasses the
            // SDK's removal bookkeeping and would be a silent no-op if ObjectIDs ever
            // returns a defensive copy (shrink-re-tag would then never remove members).
            // Child-group guids the equality predicate deliberately ignored (WR-09) must
            // survive the rebuild, or a matched re-tag silently destroys nesting (WR-10).
            var liveGroupGuids = currentDoc.Objects.OfType<GH_Group>()
                .Select(g => g.InstanceGuid).ToHashSet();
            var preservedChildIds = existingGroup.ObjectIDs
                .Where(id => liveGroupGuids.Contains(id) && id != existingGroup.InstanceGuid)
                .ToList();

            foreach (var id in existingGroup.ObjectIDs.ToList())
            {
                existingGroup.RemoveObject(id);
            }

            foreach (var obj in selected)
            {
                if (obj.InstanceGuid != existingGroup.InstanceGuid)
                {
                    existingGroup.AddObject(obj.InstanceGuid);
                }
            }

            foreach (var childId in preservedChildIds.Where(id => !existingGroup.ObjectIDs.Contains(id)))
            {
                existingGroup.AddObject(childId);
            }

            existingGroup.ExpireCaches();

            existingGroup.NickName = nickname;
            existingGroup.Colour = colour;
            AttachToHost(currentDoc, hostGroupNickname, existingGroup.InstanceGuid, updateRecord);

            currentDoc.UndoServer.PushUndoRecord(updateRecord);
            return;
        }

        var record = new GH_UndoRecord("DG Tag Entity");
        var group = new GH_Group();
        group.CreateAttributes();
        group.NickName = nickname;
        group.Colour = colour;

        foreach (var obj in selected)
        {
            group.AddObject(obj.InstanceGuid);
        }

        record.AddAction(new GH_AddObjectAction(group));
        currentDoc.AddObject(group, false);
        AttachToHost(currentDoc, hostGroupNickname, group.InstanceGuid, record);

        currentDoc.UndoServer.PushUndoRecord(record);
    }

    private static void AttachToHost(GH_Document currentDoc, string? hostGroupNickname, Guid childGuid, GH_UndoRecord record)
    {
        if (hostGroupNickname is null)
        {
            return;
        }

        var hostGroup = currentDoc.Objects.OfType<GH_Group>()
            .FirstOrDefault(g => string.Equals(g.NickName, hostGroupNickname, StringComparison.Ordinal));

        if (hostGroup is not null && !hostGroup.ObjectIDs.Contains(childGuid))
        {
            // Record the host BEFORE mutating it (WR-01): undoing the tag must also
            // restore the host Pattern's ObjectIDs, or the extractor would report a
            // phantom nested-group id after undo.
            record.AddAction(new GH_GenericObjectAction(hostGroup));
            hostGroup.AddObject(childGuid);
        }
    }

    /// <summary>
    /// Removes <paramref name="childGuid"/> from every Pattern group other than the newly
    /// detected host that still lists it as a member (WR-01 -- re-tag must detach from a
    /// stale host, not only attach to the new one). Each touched host is recorded in
    /// <paramref name="record"/> before mutation so the whole re-tag is atomically undoable.
    /// </summary>
    private static void DetachFromStaleHosts(GH_Document currentDoc, Guid childGuid, string? newHostNickname, GH_UndoRecord record)
    {
        var staleHosts = currentDoc.Objects.OfType<GH_Group>()
            .Where(g => g.NickName.Contains(CanvasAnnotationGrammar.PatternInfix, StringComparison.Ordinal))
            .Where(g => newHostNickname is null || !string.Equals(g.NickName, newHostNickname, StringComparison.Ordinal))
            .Where(g => g.ObjectIDs.Contains(childGuid))
            .ToList();

        foreach (var staleHost in staleHosts)
        {
            record.AddAction(new GH_GenericObjectAction(staleHost));
            staleHost.RemoveObject(childGuid);
        }
    }

    /// <summary>
    /// Extracts the integer idx token from an <c>NN_Pat_idx[ Label]</c> nickname -- the
    /// inverse of the slice <see cref="CanvasAnnotationNameFactory.NextFreePatternIndex"/>
    /// scans. Returns false for non-integer or non-positive idx tokens (they fall back to
    /// auto-increment).
    /// </summary>
    private static bool TryExtractPatternIndex(string nickname, string patPrefix, out int index)
    {
        index = 0;
        if (!nickname.StartsWith(patPrefix, StringComparison.Ordinal))
        {
            return false;
        }

        var remainder = nickname.Substring(patPrefix.Length);
        var spaceIdx = remainder.IndexOf(' ');
        var idxToken = spaceIdx >= 0 ? remainder.Substring(0, spaceIdx) : remainder;
        return int.TryParse(idxToken, NumberStyles.None, CultureInfo.InvariantCulture, out index) && index > 0;
    }

    private static EntityTagKind? MapKind(string? raw) => raw?.Trim() switch
    {
        "Proc" => EntityTagKind.Proc,
        "Pat" => EntityTagKind.Pat,
        "Var" => EntityTagKind.Var,
        "Const" => EntityTagKind.Const,
        "Emg" => EntityTagKind.Emg,
        "IntF" => EntityTagKind.IntF,
        _ => null,
    };

    private static void SetOutputs(IGH_DataAccess da, string groupName, int memberCount, string status)
    {
        da.SetData(0, groupName);
        da.SetData(1, memberCount);
        da.SetData(2, status);
    }
}
#else
namespace DG.Grasshopper.Components;

public sealed class EntityTagComponent
{
}
#endif
