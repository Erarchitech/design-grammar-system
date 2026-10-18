#if GRASSHOPPER_SDK
using DG.Core.Mapping;
using DG.Core.Models;
using DG.Grasshopper.Components;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;
using Rhino;

namespace DG.Grasshopper.Mapping;

/// <summary>Result of reading one Grasshopper document for automatic mapping.</summary>
internal sealed class CanvasMappingRead
{
    public MappingSnapshot Snapshot { get; set; } = new();

    /// <summary>Element native ids in canvas order (stream, then branch/item order).</summary>
    public List<string> Order { get; } = new();

    public Dictionary<string, Rhino.Geometry.GeometryBase> Previews { get; } = new(StringComparer.Ordinal);

    /// <summary>Stream id (param instance guid "N") → the output parameter, for placement.</summary>
    public Dictionary<string, IGH_Param> StreamParams { get; } = new(StringComparer.Ordinal);

    /// <summary>Measure param guid "N" → the numeric output parameter, for placement.</summary>
    public Dictionary<string, IGH_Param> MeasureParams { get; } = new(StringComparer.Ordinal);

    /// <summary>Slider guid "N" → the slider, for placement.</summary>
    public Dictionary<string, GH_NumberSlider> Sliders { get; } = new(StringComparer.Ordinal);

    /// <summary>"source (n)" per stream, for the Mapping summary.</summary>
    public List<string> Streams { get; } = new();

    public List<string> Notes { get; } = new();

    public string DocumentKey { get; set; } = string.Empty;

    /// <summary>True when the definition already wires geometry into DG components (OBJECT STATE …).</summary>
    public bool HasDgWiring { get; set; }
}

/// <summary>
/// Reads the open definition for automatic mapping (Phase 1303, D-33..D-37). Read-only.
/// Element streams: the geometry the definition wires into DG components; a definition without
/// DG wiring (the case automatic placement is for) gives its terminal geometry and the geometry
/// its calculation components read, minus streams that only feed another candidate. Every
/// stream carries the canvas text around it. Measures: numeric outputs of calculation
/// components, matched to streams by branch paths and by agreement with the stream's own
/// geometry features. Named number sliders are DG parameter candidates.
/// </summary>
internal static class MappingCanvasReader
{
    public const int MaxElements = 5000;
    public const int MaxMeasures = 80;
    private const int AncestorDepth = 6;

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

        // 1. Streams.
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

        read.HasDgWiring = streams.Count > 0;
        if (!read.HasDgWiring)
        {
            foreach (var param in CandidateStreams(doc))
            {
                streams.Add((param, new List<string>()));
            }

            read.Notes.Add($"no geometry is wired into DG components; {streams.Count} candidate streams from terminal geometry and calculation inputs");
        }

        // 2. Elements, with per-stream keyed properties for measure matching.
        var elements = new List<MappingElement>();
        var keyed = new Dictionary<string, Dictionary<string, IReadOnlyDictionary<string, object>>>(StringComparer.Ordinal);
        foreach (var (param, hints) in streams)
        {
            var top = Top(param);
            var source = SourceLabel(param, top);
            var names = MappingCanvasText.Merge(hints, CanvasText(top), ComponentNames(param, top));
            var streamId = param.InstanceGuid.ToString("N");
            var data = param.VolatileData;
            var count = 0;
            var perBranch = data.PathCount > 1;
            var byKey = new Dictionary<string, IReadOnlyDictionary<string, object>>(StringComparer.Ordinal);
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

                    var nativeId = $"gh:{read.DocumentKey}:{streamId[..8]}:{path}:{index}";
                    elements.Add(new MappingElement
                    {
                        NativeId = nativeId,
                        Source = source,
                        Stream = streamId,
                        Names = names,
                        Geometry = described.Geometry,
                        Properties = described.Properties,
                    });
                    byKey[MappingMeasureMatcher.Key(path.ToString(), index)] = described.Properties;
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
                read.StreamParams[streamId] = param;
                keyed[streamId] = byKey;
            }
        }

        // 3. Measures: numeric outputs of calculation components.
        var measures = new List<MappingMeasure>();
        foreach (var component in doc.Objects.OfType<IGH_Component>())
        {
            if (IsDg(component) || !component.Params.Input.Any(i => i.Sources.Any(HasGeometry)))
            {
                continue;
            }

            foreach (var output in component.Params.Output)
            {
                if (measures.Count >= MaxMeasures)
                {
                    break;
                }

                var values = NumericValues(output);
                if (values.Count == 0)
                {
                    continue;
                }

                var matches = keyed
                    .Select(kv => MappingMeasureMatcher.Match(kv.Key, values, kv.Value))
                    .Where(m => m.PathMatch || m.Agreement.Count > 0)
                    .ToList();
                var guid = output.InstanceGuid.ToString("N");
                measures.Add(new MappingMeasure
                {
                    NativeId = $"gh:{read.DocumentKey}:measure:{guid}",
                    Name = MappingCanvasText.Clean(string.IsNullOrWhiteSpace(output.NickName) ? output.Name : output.NickName),
                    Component = MappingCanvasText.Clean(string.IsNullOrWhiteSpace(component.NickName) ? component.Name : component.NickName),
                    Names = MappingCanvasText.Merge(CanvasText(component), new[] { component.Name, output.Name, output.Description }),
                    Count = values.Count,
                    Min = values.Values.Min(),
                    Max = values.Values.Max(),
                    Streams = matches,
                });
                read.MeasureParams[guid] = output;
            }
        }

        // 4. Parameters: named number sliders with the canvas text around them.
        var parameters = new List<MappingParameter>();
        foreach (var slider in doc.Objects.OfType<GH_NumberSlider>())
        {
            var name = MappingCanvasText.Clean(slider.NickName);
            if (MappingCanvasText.IsDefaultNickname(name, slider.Name, "Number Slider"))
            {
                continue;
            }

            var guid = slider.InstanceGuid.ToString("N");
            parameters.Add(new MappingParameter
            {
                NativeId = $"gh:{read.DocumentKey}:slider:{guid}",
                Name = name,
                Names = CanvasText(slider),
                Value = (double)slider.CurrentValue,
                Min = (double)slider.Slider.Minimum,
                Max = (double)slider.Slider.Maximum,
            });
            read.Sliders[guid] = slider;
        }

        read.Snapshot = new MappingSnapshot { Elements = elements, Parameters = parameters, Measures = measures };
        return read;
    }

    public static bool IsDg(IGH_DocumentObject? obj) =>
        obj?.GetType().Namespace?.StartsWith("DG.Grasshopper", StringComparison.Ordinal) == true;

    public static IGH_DocumentObject Top(IGH_Param param) => param.Attributes?.GetTopLevel?.DocObject ?? param;

    /// <summary>Terminal geometry (named or visible) plus geometry read by calculation components, minus pure ancestors of other candidates.</summary>
    private static List<IGH_Param> CandidateStreams(GH_Document doc)
    {
        var candidates = new Dictionary<Guid, IGH_Param>();
        foreach (var param in AllOutputParams(doc))
        {
            var top = Top(param);
            if (IsDg(top) || top is GH_NumberSlider || !HasGeometry(param) || (top is IGH_ActiveObject active && active.Locked))
            {
                continue;
            }

            // Geometry outputs of calculation components (a measure script's violator preview) are diagnostics, not elements.
            if (top is IGH_Component owner && owner.Params.Output.Any(o => !ReferenceEquals(o, param) && NumericValues(o).Count > 0))
            {
                continue;
            }

            var named = !MappingCanvasText.IsDefaultNickname(top.NickName, top.Name)
                || (!ReferenceEquals(top, param) && !MappingCanvasText.IsDefaultNickname(param.NickName, param.Name));
            if (param.Recipients.Count == 0 && (named || IsVisible(param)))
            {
                candidates[param.InstanceGuid] = param;
            }
        }

        foreach (var component in doc.Objects.OfType<IGH_Component>())
        {
            if (IsDg(component) || !component.Params.Output.Any(o => NumericValues(o).Count > 0))
            {
                continue;
            }

            foreach (var input in component.Params.Input)
            {
                foreach (var source in input.Sources)
                {
                    if (!IsDg(Top(source)) && HasGeometry(source))
                    {
                        candidates[source.InstanceGuid] = source;
                    }
                }
            }
        }

        // A candidate that only feeds another candidate (raw HU → Join Curves → join HU) is dropped.
        var ancestors = new HashSet<Guid>();
        foreach (var param in candidates.Values)
        {
            foreach (var up in Upstream(param, AncestorDepth))
            {
                ancestors.Add(up);
            }
        }

        return candidates.Values
            .Where(p => !ancestors.Contains(p.InstanceGuid))
            .OrderBy(p => Top(p).Attributes.Pivot.Y)
            .ThenBy(p => Top(p).Attributes.Pivot.X)
            .ToList();
    }

    private static HashSet<Guid> Upstream(IGH_Param param, int depth)
    {
        var result = new HashSet<Guid>();
        var frontier = new List<IGH_Param> { param };
        for (var d = 0; d < depth && frontier.Count > 0; d++)
        {
            var next = new List<IGH_Param>();
            foreach (var p in frontier)
            {
                var sources = Top(p) is IGH_Component owner && !ReferenceEquals(owner, p) && owner.Params.Output.Contains(p)
                    ? owner.Params.Input.SelectMany(i => i.Sources)
                    : p.Sources;
                foreach (var s in sources)
                {
                    if (result.Add(s.InstanceGuid))
                    {
                        next.Add(s);
                    }
                }
            }

            frontier = next;
        }

        return result;
    }

    private static Dictionary<string, double> NumericValues(IGH_Param param)
    {
        var values = new Dictionary<string, double>(StringComparer.Ordinal);
        var data = param.VolatileData;
        for (var b = 0; b < data.PathCount; b++)
        {
            var path = data.get_Path(b);
            var branch = data.get_Branch(path);
            if (branch is null)
            {
                continue;
            }

            for (var i = 0; i < branch.Count; i++)
            {
                var raw = branch[i] switch
                {
                    GH_Number n => (double?)n.Value,
                    GH_Integer n => n.Value,
                    _ => null,
                };
                if (raw is null)
                {
                    return new Dictionary<string, double>(); // mixed or non-numeric output: not a measure
                }

                var index = data.PathCount > 1 && branch.Count == 1 ? 0 : i;
                values[MappingMeasureMatcher.Key(path.ToString(), index)] = raw.Value;
            }
        }

        return values;
    }

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
            var value = MappingGeometry.Unwrap(goo);
            if (value is OntologyClass cls)
            {
                return string.IsNullOrWhiteSpace(cls.Label) ? MappingSessionClient.LocalName(cls.Iri) : cls.Label;
            }

            if (MappingClassText.Parse(value as string) is { } iri)
            {
                return MappingSessionClient.LocalName(iri);
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
