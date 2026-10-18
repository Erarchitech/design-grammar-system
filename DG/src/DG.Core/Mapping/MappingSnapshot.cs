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

/// <summary>
/// What CONNECTOR sends to <c>POST /mapping/sessions</c>. Serialization is deterministic
/// (elements and parameters sorted by native id, keys sorted), so <see cref="Fingerprint"/>
/// changes only when the canvas content changes.
/// </summary>
public sealed class MappingSnapshot
{
    public IReadOnlyList<MappingElement> Elements { get; init; } = Array.Empty<MappingElement>();

    public IReadOnlyList<MappingParameter> Parameters { get; init; } = Array.Empty<MappingParameter>();

    public bool IsEmpty => Elements.Count == 0 && Parameters.Count == 0;

    public string ToRequestJson(string project, string label)
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["project"] = project,
            ["platform"] = "grasshopper",
            ["label"] = label,
            ["elements"] = ElementsPayload(),
            ["parameters"] = ParametersPayload(),
        };
        return JsonSerializer.Serialize(body);
    }

    /// <summary>16 hex chars of SHA-256 over the elements and parameters (label and project excluded).</summary>
    public string Fingerprint()
    {
        var json = JsonSerializer.Serialize(new object[] { ElementsPayload(), ParametersPayload() });
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
