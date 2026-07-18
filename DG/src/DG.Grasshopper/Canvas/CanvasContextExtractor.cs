#if GRASSHOPPER_SDK
using DG.Core.Models.Computgraph;
using DG.Core.Parsing;
using DG.Core.Serialization;
using Grasshopper.GUI.Base;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;

namespace DG.Grasshopper.Canvas;

/// <summary>
/// Traverses a live <see cref="GH_Document"/> into a GH-free <see cref="RawCanvas"/>
/// (nodes, wires, groups with nesting, scribbles, slider domains) and composes a
/// one-call <see cref="SerializeContext"/> seam that chains the DG.Core parser +
/// serializer into a cgContextJson v1 string -- the GH-dependent half of CGSR-03.
/// The traversal itself is PURE: it never classifies scribble/group text into typed
/// Computgraph entities (that stays in DG.Core's <see cref="CanvasAnnotationParser"/>,
/// per CONTEXT.md decision #4).
/// </summary>
public static class CanvasContextExtractor
{
    /// <summary>
    /// Traverses <paramref name="doc"/> into a raw, GH-free canvas snapshot. Guards
    /// null document (returns an empty shape) and every per-object cast/read
    /// (guard-and-continue, threat T-32-10) so a single malformed object cannot
    /// abort the traversal.
    /// </summary>
    public static RawCanvas ExtractRaw(GH_Document? doc, string project)
    {
        var capturedAt = DateTimeOffset.UtcNow.ToString("O");

        if (doc is null)
        {
            return new RawCanvas
            {
                Project = project,
                Definition = new CgDefinition
                {
                    DocumentId = string.Empty,
                    FileName = string.Empty,
                    CapturedAt = capturedAt,
                },
            };
        }

        var raw = new RawCanvas
        {
            Project = project,
            Definition = new CgDefinition
            {
                DocumentId = doc.DocumentID.ToString(),
                FileName = doc.DisplayName ?? string.Empty,
                CapturedAt = capturedAt,
            },
        };

        var groupsByGuid = new Dictionary<Guid, GH_Group>();

        foreach (var obj in doc.Objects)
        {
            switch (obj)
            {
                case GH_Group group:
                    groupsByGuid[group.InstanceGuid] = group;
                    break;
                case GH_Scribble scribble:
                    TryAddScribble(raw, scribble);
                    break;
                default:
                    TryAddNode(raw, obj);
                    break;
            }
        }

        foreach (var group in groupsByGuid.Values)
        {
            TryAddGroup(raw, group, groupsByGuid);
        }

        foreach (var obj in doc.Objects)
        {
            TryAddWires(raw, obj);
        }

        return raw;
    }

    /// <summary>
    /// One-call seam: extract -&gt; parse -&gt; serialize. This is the entry point
    /// Phase 33's DG CANVAS LISTENER (<c>get_canvas_context</c>) invokes; kept as a
    /// thin composition so all classification/serialization logic stays in DG.Core.
    /// </summary>
    public static string SerializeContext(GH_Document? doc, string project)
    {
        var raw = ExtractRaw(doc, project);
        var context = CanvasAnnotationParser.Parse(raw);
        return ComputgraphContextSerializer.Serialize(context);
    }

    private static void TryAddNode(RawCanvas raw, IGH_DocumentObject obj)
    {
        try
        {
            var pivot = obj.Attributes.Pivot;
            raw.Nodes.Add(new CgNode
            {
                InstanceId = obj.InstanceGuid.ToString(),
                ComponentGuid = obj.ComponentGuid.ToString(),
                Name = obj.Name ?? string.Empty,
                Nickname = obj.NickName ?? string.Empty,
                Position = new[] { (double)pivot.X, (double)pivot.Y },
                Slider = TryReadSliderDomain(obj),
                IsIntegerSlider = obj is GH_NumberSlider integerCandidate
                    && integerCandidate.Slider.Type == GH_SliderAccuracy.Integer,
            });
        }
        catch
        {
            // Guard-and-continue (T-32-10): a single malformed doc object cannot abort the traversal.
        }
    }

    private static SliderDomain? TryReadSliderDomain(IGH_DocumentObject obj)
    {
        if (obj is not GH_NumberSlider slider)
        {
            return null;
        }

        try
        {
            var step = slider.Slider.Type == GH_SliderAccuracy.Integer
                ? 1.0
                : Math.Pow(10, -slider.Slider.DecimalPlaces);

            return new SliderDomain
            {
                Min = (double)slider.Slider.Minimum,
                Max = (double)slider.Slider.Maximum,
                Step = step,
            };
        }
        catch
        {
            // Guard-and-continue: a degenerate slider yields no domain rather than aborting the node.
            return null;
        }
    }

    private static void TryAddScribble(RawCanvas raw, GH_Scribble scribble)
    {
        try
        {
            var pivot = scribble.Attributes.Pivot;
            raw.Scribbles.Add(new RawScribble
            {
                Text = scribble.Text ?? string.Empty,
                Position = new[] { (double)pivot.X, (double)pivot.Y },
            });
        }
        catch
        {
            // Guard-and-continue.
        }
    }

    private static void TryAddGroup(RawCanvas raw, GH_Group group, IReadOnlyDictionary<Guid, GH_Group> groupsByGuid)
    {
        try
        {
            var memberIds = group.ObjectIDs.Select(id => id.ToString()).ToList();

            // Nesting (CONTEXT decision #4 / RESEARCH.md #4): a group id appearing inside
            // another group's ObjectIDs is a nested (child) group.
            var nestedGroupIds = new List<string>();
            foreach (var other in groupsByGuid.Values)
            {
                if (other.InstanceGuid == group.InstanceGuid)
                {
                    continue;
                }

                if (group.ObjectIDs.Contains(other.InstanceGuid))
                {
                    nestedGroupIds.Add(other.InstanceGuid.ToString());
                }
            }

            raw.Groups.Add(new RawGroup
            {
                Nickname = group.NickName ?? string.Empty,
                MemberIds = memberIds,
                NestedGroupIds = nestedGroupIds,
            });
        }
        catch
        {
            // Guard-and-continue: bounded pairwise scan (T-32-10), no unbounded recursion.
        }
    }

    private static void TryAddWires(RawCanvas raw, IGH_DocumentObject obj)
    {
        try
        {
            IEnumerable<IGH_Param>? inputParams = obj switch
            {
                IGH_Component component => component.Params.Input,
                IGH_Param param => new[] { param },
                _ => null,
            };

            if (inputParams is null)
            {
                return;
            }

            foreach (var param in inputParams)
            {
                foreach (var source in param.Sources)
                {
                    TryAddWire(raw, source, param);
                }
            }
        }
        catch
        {
            // Guard-and-continue.
        }
    }

    private static void TryAddWire(RawCanvas raw, IGH_Param source, IGH_Param param)
    {
        try
        {
            // Endpoints are param instance GUIDs -- stable under renames (CONTEXT "open for
            // planning" resolution). FromNode/ToNode resolve to the owning component (or the
            // param itself, for a floating param) via the top-level attributes' DocObject.
            var fromNode = source.Attributes.GetTopLevel.DocObject.InstanceGuid;
            var toNode = param.Attributes.GetTopLevel.DocObject.InstanceGuid;

            raw.Wires.Add(new CgWire
            {
                FromNode = fromNode.ToString(),
                FromParam = source.InstanceGuid.ToString(),
                ToNode = toNode.ToString(),
                ToParam = param.InstanceGuid.ToString(),
            });
        }
        catch
        {
            // Guard-and-continue: a single unreadable source cannot abort the wire scan.
        }
    }
}
#else
using DG.Core.Models.Computgraph;

namespace DG.Grasshopper.Canvas;

/// <summary>
/// Stub for builds without the Grasshopper SDK (GRASSHOPPER_SDK undefined) -- keeps
/// DG.Grasshopper compiling; the real GH_Document traversal lives in the #if branch.
/// </summary>
public static class CanvasContextExtractor
{
    public static RawCanvas ExtractRaw(object? doc, string project) =>
        throw new PlatformNotSupportedException(
            "CanvasContextExtractor requires the Grasshopper SDK (GRASSHOPPER_SDK).");

    public static string SerializeContext(object? doc, string project) =>
        throw new PlatformNotSupportedException(
            "CanvasContextExtractor requires the Grasshopper SDK (GRASSHOPPER_SDK).");
}
#endif
