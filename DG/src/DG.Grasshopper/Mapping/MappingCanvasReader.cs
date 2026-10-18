#if GRASSHOPPER_SDK
using DG.Core.Mapping;
using DG.Core.Models;
using DG.Grasshopper.Components;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Rhino;

namespace DG.Grasshopper.Mapping;

/// <summary>Result of reading one Grasshopper document for automatic mapping.</summary>
internal sealed class CanvasMappingRead
{
    public MappingSnapshot Snapshot { get; set; } = new();

    /// <summary>Element native ids in canvas order (stream, then branch/item order).</summary>
    public List<string> Order { get; } = new();

    public Dictionary<string, Rhino.Geometry.GeometryBase> Previews { get; } = new(StringComparer.Ordinal);

    /// <summary>"source (n)" per stream, for the Mapping summary.</summary>
    public List<string> Streams { get; } = new();

    public List<string> Notes { get; } = new();

    public string DocumentKey { get; set; } = string.Empty;
}

/// <summary>
/// Reads the open definition for automatic mapping (Phase 1303, owner amendment 2026-10-18).
/// No mapping component and no wiring: the element streams are the geometry sources the
/// definition already connects to DG components (OBJECT STATE and the like); a definition
/// without DG wiring falls back to its visible terminal geometry. Every stream carries the
/// canvas text around it (group names, scribbles, component names and nicknames, the class an
/// OBJECT STATE already names). Named number sliders become parameters. Read-only.
/// </summary>
internal static class MappingCanvasReader
{
    public const int MaxElements = 5000;

    public static CanvasMappingRead Read(GH_Document doc)
    {
        var read = new CanvasMappingRead { DocumentKey = DocumentKey(doc) };
        var rhino = RhinoDoc.ActiveDoc;
        var tol = rhino?.ModelAbsoluteTolerance ?? 0.001;
        var k = rhino is null ? 1.0 : RhinoMath.UnitScale(rhino.ModelUnitSystem, UnitSystem.Meters);

        var groups = doc.Objects.OfType<GH_Group>()
            .Select(g => new CanvasGroupInfo(g.InstanceGuid, g.NickName ?? string.Empty, g.ObjectIDs.ToList()))
            .ToList();
        var scribbles = doc.Objects.OfType<GH_Scribble>()
            .Select(s => new CanvasScribbleInfo(s.InstanceGuid, s.Text ?? string.Empty, s.Attributes.Bounds.X + s.Attributes.Bounds.Width / 2f, s.Attributes.Bounds.Y + s.Attributes.Bounds.Height / 2f))
            .ToList();
        var groupNames = MappingCanvasText.GroupNamesByObject(groups);

        List<string> CanvasText(IGH_DocumentObject top)
        {
            groupNames.TryGetValue(top.InstanceGuid, out var inGroups);
            var b = top.Attributes.Bounds;
            var notes = MappingCanvasText.ScribblesFor(top.InstanceGuid, new CanvasBounds(b.X, b.Y, b.Width, b.Height), scribbles, groups);
            return MappingCanvasText.Merge(inGroups ?? new List<string>(), notes);
        }

        var levels = FindLevels(doc);
        var geometry = new MappingGeometry(tol, k, levels);

        // 1. Streams: geometry wired into DG components, else visible terminal geometry.
        var streams = new List<(IGH_Param Param, List<string> Hints)>();
        var seen = new Dictionary<Guid, int>();
        foreach (var dg in doc.Objects.OfType<IGH_Component>().Where(IsDg))
        {
            var classHint = dg is ObjectStateComponent ? ObjectStateClass(dg) : null;
            foreach (var input in dg.Params.Input)
            {
                foreach (var source in input.Sources)
                {
                    if (IsDg(Top(source)) || !HasGeometry(source))
                    {
                        continue;
                    }

                    var hint = classHint is not null && input.Name == "Geometry" ? $"{dg.NickName}: {classHint}" : null;
                    if (seen.TryGetValue(source.InstanceGuid, out var at))
                    {
                        if (hint is not null)
                        {
                            streams[at].Hints.Add(hint);
                        }

                        continue;
                    }

                    seen[source.InstanceGuid] = streams.Count;
                    streams.Add((source, hint is null ? new List<string>() : new List<string> { hint }));
                }
            }
        }

        if (streams.Count == 0)
        {
            read.Notes.Add("no geometry is wired into DG components; reading visible terminal geometry");
            foreach (var param in AllOutputParams(doc))
            {
                if (param.Recipients.Count == 0 && IsVisible(param) && !IsDg(Top(param)) && HasGeometry(param))
                {
                    streams.Add((param, new List<string>()));
                }
            }
        }

        // 2. Elements.
        var elements = new List<MappingElement>();
        foreach (var (param, hints) in streams)
        {
            var top = Top(param);
            var source = SourceLabel(param, top);
            var names = MappingCanvasText.Merge(hints, CanvasText(top), ComponentNames(param, top));
            var key = param.InstanceGuid.ToString("N")[..8];
            var data = param.VolatileData;
            var count = 0;
            var perBranch = data.PathCount > 1;
            for (var b = 0; b < data.PathCount && elements.Count < MaxElements; b++)
            {
                var path = data.get_Path(b);
                var branch = data.get_Branch(path);
                if (branch is null || branch.Count == 0)
                {
                    continue;
                }

                var batches = perBranch
                    ? new List<(int Index, List<object> Items)> { (0, branch.Cast<object>().ToList()) }
                    : branch.Cast<object>().Select((o, i) => (i, new List<object> { o })).ToList();
                foreach (var (index, items) in batches)
                {
                    if (elements.Count >= MaxElements)
                    {
                        read.Notes.Add($"stopped at {MaxElements} elements");
                        break;
                    }

                    if (!geometry.TryDescribe(items, out var described, out var error))
                    {
                        if (read.Notes.Count < 20)
                        {
                            read.Notes.Add($"{source} {path}: {error}");
                        }

                        continue;
                    }

                    var nativeId = $"gh:{read.DocumentKey}:{key}:{path}:{index}";
                    elements.Add(new MappingElement
                    {
                        NativeId = nativeId,
                        Source = source,
                        Names = names,
                        Geometry = described.Geometry,
                        Properties = described.Properties,
                    });
                    read.Order.Add(nativeId);
                    if (described.Preview is not null)
                    {
                        read.Previews[nativeId] = described.Preview;
                    }

                    count++;
                }
            }

            if (count > 0)
            {
                read.Streams.Add($"{source} ({count})");
            }
        }

        // 3. Parameters: named number sliders with the canvas text around them.
        var parameters = new List<MappingParameter>();
        foreach (var slider in doc.Objects.OfType<GH_NumberSlider>())
        {
            var name = MappingCanvasText.Clean(slider.NickName);
            if (MappingCanvasText.IsDefaultNickname(name, slider.Name, "Number Slider"))
            {
                continue;
            }

            parameters.Add(new MappingParameter
            {
                NativeId = $"gh:{read.DocumentKey}:slider:{slider.InstanceGuid:N}",
                Name = name,
                Names = CanvasText(slider),
                Value = (double)slider.CurrentValue,
                Min = (double)slider.Slider.Minimum,
                Max = (double)slider.Slider.Maximum,
            });
        }

        read.Snapshot = new MappingSnapshot { Elements = elements, Parameters = parameters };
        return read;
    }

    public static bool IsDg(IGH_DocumentObject? obj) =>
        obj?.GetType().Namespace?.StartsWith("DG.Grasshopper", StringComparison.Ordinal) == true;

    private static IGH_DocumentObject Top(IGH_Param param) => param.Attributes?.GetTopLevel?.DocObject ?? param;

    private static bool HasGeometry(IGH_Param param)
    {
        foreach (var goo in param.VolatileData.AllData(true))
        {
            if (MappingGeometry.IsGeometry(goo))
            {
                return true;
            }
        }

        return false;
    }

    private static bool IsVisible(IGH_Param param)
    {
        var top = Top(param);
        if (top is IGH_ActiveObject active && active.Locked)
        {
            return false;
        }

        return top is not IGH_PreviewObject preview || !preview.Hidden;
    }

    private static IEnumerable<IGH_Param> AllOutputParams(GH_Document doc)
    {
        foreach (var obj in doc.Objects)
        {
            switch (obj)
            {
                case IGH_Component component:
                    foreach (var p in component.Params.Output)
                    {
                        yield return p;
                    }

                    break;
                case IGH_Param param:
                    yield return param;
                    break;
            }
        }
    }

    private static string SourceLabel(IGH_Param param, IGH_DocumentObject top)
    {
        if (ReferenceEquals(top, param))
        {
            var nick = MappingCanvasText.Clean(param.NickName);
            return nick.Length > 0 ? nick : param.Name;
        }

        var label = MappingCanvasText.Clean(top.NickName);
        if (label.Length == 0)
        {
            label = top.Name;
        }

        if (top is IGH_Component component && component.Params.Output.Count > 1)
        {
            label += "." + MappingCanvasText.Clean(param.NickName);
        }

        return label;
    }

    private static IEnumerable<string?> ComponentNames(IGH_Param param, IGH_DocumentObject top)
    {
        yield return top.Name;
        if (!MappingCanvasText.IsDefaultNickname(top.NickName, top.Name))
        {
            yield return top.NickName;
        }

        if (!ReferenceEquals(top, param) && !MappingCanvasText.IsDefaultNickname(param.NickName, param.Name))
        {
            yield return param.NickName;
        }
    }

    /// <summary>The class an OBJECT STATE already names on its Object input (the user's manual mapping).</summary>
    private static string? ObjectStateClass(IGH_Component objectState)
    {
        var input = objectState.Params.Input.FirstOrDefault(p => p.Name == "Object");
        if (input is null)
        {
            return null;
        }

        foreach (var goo in input.VolatileData.AllData(true))
        {
            if (MappingGeometry.Unwrap(goo) is OntologyClass cls)
            {
                return string.IsNullOrWhiteSpace(cls.Label) ? MappingSessionClient.LocalName(cls.Iri) : cls.Label;
            }
        }

        return null;
    }

    /// <summary>Level elevations (model units) from a parameter named LZ / level / уровни, for hasLevelOffsetM.</summary>
    private static List<double> FindLevels(GH_Document doc)
    {
        foreach (var param in doc.Objects.SelectMany(o => o is IGH_Component c ? c.Params.Input.Concat(c.Params.Output) : o is IGH_Param p ? new[] { p } : Enumerable.Empty<IGH_Param>()))
        {
            var nick = (param.NickName ?? string.Empty).Trim();
            var named = nick.Equals("LZ", StringComparison.OrdinalIgnoreCase)
                || nick.Contains("level", StringComparison.OrdinalIgnoreCase)
                || nick.Contains("уров", StringComparison.OrdinalIgnoreCase);
            if (!named)
            {
                continue;
            }

            var values = new List<double>();
            foreach (var goo in param.VolatileData.AllData(true))
            {
                if (MappingGeometry.Unwrap(goo) is { } v && double.TryParse(Convert.ToString(v, System.Globalization.CultureInfo.InvariantCulture), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var z))
                {
                    values.Add(z);
                }
            }

            if (values.Count > 0)
            {
                return values;
            }
        }

        return new List<double>();
    }

    private static string DocumentKey(GH_Document doc)
    {
        var path = doc.FilePath;
        var name = string.IsNullOrWhiteSpace(path) ? doc.DocumentID.ToString("N")[..8] : Path.GetFileNameWithoutExtension(path);
        var chars = name.Trim().ToLowerInvariant().Select(ch => char.IsLetterOrDigit(ch) || ch == '-' || ch == '_' ? ch : '-').ToArray();
        return new string(chars);
    }
}
#endif
