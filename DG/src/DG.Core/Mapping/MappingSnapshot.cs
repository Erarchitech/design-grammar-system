using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace DG.Core.Mapping;

/// <summary>
/// One mappable element read from the canvas (Phase 1303, owner amendment 2026-10-18):
/// class-agnostic geometry features plus the canvas text around it. The engine treats
/// <see cref="Source"/> as the stream name and <see cref="Names"/> (group names, scribbles,
/// component nicknames, the class an OBJECT STATE names) as word evidence.
/// </summary>
public sealed class MappingElement
{
    public string NativeId { get; init; } = string.Empty;

    public string Source { get; init; } = string.Empty;

    /// <summary>Instance id of the output parameter the element comes from (its stream).</summary>
    public string Stream { get; init; } = string.Empty;

    public IReadOnlyList<string> Names { get; init; } = Array.Empty<string>();

    public IReadOnlyDictionary<string, object> Geometry { get; init; } = new Dictionary<string, object>();

    public IReadOnlyDictionary<string, object> Properties { get; init; } = new Dictionary<string, object>();
}

/// <summary>A named slider: proposed by DG as a datatype property by its name and canvas text.</summary>
public sealed class MappingParameter
{
    public string NativeId { get; init; } = string.Empty;

    public string Name { get; init; } = string.Empty;

    public IReadOnlyList<string> Names { get; init; } = Array.Empty<string>();

    public double? Value { get; init; }

    public double? Min { get; init; }

    public double? Max { get; init; }
}

/// <summary>A stream whose branches a calculation output follows, and how its values agree with the stream's own features.</summary>
public sealed class MappingMeasureStream
{
    public string Stream { get; init; } = string.Empty;

    public bool PathMatch { get; init; }

    public bool Constant { get; init; }

    /// <summary>Property name (hasAspectRatio …) → share of elements whose computed value equals the output value.</summary>
    public IReadOnlyDictionary<string, double> Agreement { get; init; } = new Dictionary<string, double>();
}

/// <summary>A numeric output of a calculation component (Area, a measure script): a DG property candidate (D-37).</summary>
public sealed class MappingMeasure
{
    public string NativeId { get; init; } = string.Empty;

    public string Name { get; init; } = string.Empty;

    public string Component { get; init; } = string.Empty;

    public IReadOnlyList<string> Names { get; init; } = Array.Empty<string>();

    public int Count { get; init; }

    public double? Min { get; init; }

    public double? Max { get; init; }

    public IReadOnlyList<MappingMeasureStream> Streams { get; init; } = Array.Empty<MappingMeasureStream>();
}

/// <summary>
/// What CONNECTOR sends to <c>POST /mapping/sessions</c>. Serialization is deterministic
/// (elements and parameters sorted by native id, keys sorted), so <see cref="Fingerprint"/>
/// changes only when the canvas content changes.
/// </summary>
public sealed class MappingSnapshot
{
    public IReadOnlyList<MappingElement> Elements { get; init; } = Array.Empty<MappingElement>();

    public IReadOnlyList<MappingParameter> Parameters { get; init; } = Array.Empty<MappingParameter>();

    public IReadOnlyList<MappingMeasure> Measures { get; init; } = Array.Empty<MappingMeasure>();

    public bool IsEmpty => Elements.Count == 0 && Parameters.Count == 0 && Measures.Count == 0;

    /// <param name="askLlm">Ask DG for one LLM proposal when the deterministic pass leaves questions (D-37).</param>
    public string ToRequestJson(string project, string label, bool askLlm = true)
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["project"] = project,
            ["platform"] = "grasshopper",
            ["label"] = label,
            ["elements"] = ElementsPayload(),
            ["parameters"] = ParametersPayload(),
            ["measures"] = MeasuresPayload(),
            ["context"] = new Dictionary<string, object> { ["llm"] = askLlm },
        };
        return JsonSerializer.Serialize(body);
    }

    /// <summary>16 hex chars of SHA-256 over elements, parameters and measures (label and project excluded).</summary>
    public string Fingerprint()
    {
        var json = JsonSerializer.Serialize(new object[] { ElementsPayload(), ParametersPayload(), MeasuresPayload() });
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(json));
        return Convert.ToHexString(hash, 0, 8);
    }

    private List<SortedDictionary<string, object?>> ElementsPayload() =>
        Elements
            .OrderBy(e => e.NativeId, StringComparer.Ordinal)
            .Select(e => new SortedDictionary<string, object?>(StringComparer.Ordinal)
            {
                ["nativeId"] = e.NativeId,
                ["platform"] = "grasshopper",
                ["source"] = e.Source,
                ["stream"] = e.Stream,
                ["names"] = e.Names.ToList(),
                ["geometry"] = Sorted(e.Geometry),
                ["properties"] = Sorted(e.Properties),
            })
            .ToList();

    private List<SortedDictionary<string, object?>> ParametersPayload() =>
        Parameters
            .OrderBy(p => p.NativeId, StringComparer.Ordinal)
            .Select(p => new SortedDictionary<string, object?>(StringComparer.Ordinal)
            {
                ["nativeId"] = p.NativeId,
                ["name"] = p.Name,
                ["names"] = p.Names.ToList(),
                ["kind"] = "number",
                ["value"] = p.Value,
                ["min"] = p.Min,
                ["max"] = p.Max,
            })
            .ToList();

    private List<SortedDictionary<string, object?>> MeasuresPayload() =>
        Measures
            .OrderBy(m => m.NativeId, StringComparer.Ordinal)
            .Select(m => new SortedDictionary<string, object?>(StringComparer.Ordinal)
            {
                ["nativeId"] = m.NativeId,
                ["name"] = m.Name,
                ["component"] = m.Component,
                ["names"] = m.Names.ToList(),
                ["count"] = m.Count,
                ["min"] = m.Min is { } min ? Math.Round(min, 6) : null,
                ["max"] = m.Max is { } max ? Math.Round(max, 6) : null,
                ["streams"] = m.Streams
                    .OrderBy(s => s.Stream, StringComparer.Ordinal)
                    .Select(s => new SortedDictionary<string, object?>(StringComparer.Ordinal)
                    {
                        ["stream"] = s.Stream,
                        ["pathMatch"] = s.PathMatch,
                        ["constant"] = s.Constant,
                        ["agreement"] = new SortedDictionary<string, double>(
                            s.Agreement.ToDictionary(kv => kv.Key, kv => Math.Round(kv.Value, 4)), StringComparer.Ordinal),
                    })
                    .ToList(),
            })
            .ToList();

    private static SortedDictionary<string, object> Sorted(IReadOnlyDictionary<string, object> source)
    {
        var sorted = new SortedDictionary<string, object>(StringComparer.Ordinal);
        foreach (var (key, value) in source)
        {
            sorted[key] = value is double d ? Math.Round(d, 6) : value;
        }

        return sorted;
    }

    /// <summary>Invariant-culture number text for summaries and logs.</summary>
    public static string Number(double value) => value.ToString("0.###", CultureInfo.InvariantCulture);
}
