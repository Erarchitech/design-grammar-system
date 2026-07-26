using System.Text.Json;

namespace DG.Core.Parsing;

/// <summary>
/// LLM provenance recovered from a recognition marker: which provider/model authored the
/// proposal and how confident it was. Any field may be null -- a legacy marker records only
/// THAT a group was recognized, not by whom.
/// </summary>
public sealed record RecognitionProvenance(string? Provider, string? Model, double? Confidence);

/// <summary>
/// Read/write contract for the <c>dg.recognized.&lt;groupInstanceGuid&gt;</c> Grasshopper
/// document ValueTable marker -- the only channel that carries an accepted proposal's LLM
/// provenance from <c>DG STRUCTURE CONFIRM</c> (writer) through save/reopen to
/// <c>CanvasContextExtractor</c> (reader), and from there into the published Computgraph
/// subgraph's <c>provider</c>/<c>model</c>/<c>confidence</c> properties.
///
/// <para>
/// Phase 36 UAT F6: the marker used to be the literal string <c>"true"</c>, which discarded the
/// model identity and confidence score at confirm time -- so <c>computgraph_publish.py</c>, which
/// has always read those three fields, could only ever write nulls. The marker is now a compact
/// JSON object; <see cref="TryParse"/> still accepts the legacy <c>"true"</c> so canvases saved
/// before this change keep their <c>source: recognized</c> (with null provenance, exactly the
/// state they were saved in).
/// </para>
///
/// <para>
/// Lives in DG.Core (not DG.Grasshopper) so the format has one definition shared by writer and
/// reader, and so it is unit-testable without the Grasshopper SDK.
/// </para>
/// </summary>
public static class RecognitionMarker
{
    /// <summary>ValueTable key prefix -- the group's instance GUID is appended verbatim.</summary>
    public const string KeyPrefix = "dg.recognized.";

    /// <summary>
    /// The value <c>GH_ValueTable.GetValue</c> should be given as its default, and the value a
    /// never-recognized group reads back as. <see cref="TryParse"/> maps it to null.
    /// </summary>
    public const string Absent = "false";

    /// <summary>Legacy (pre-F6) marker value: recognized, provenance unknown.</summary>
    public const string LegacyRecognized = "true";

    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    /// <summary>ValueTable key for one group -- <c>dg.recognized.&lt;instanceGuid&gt;</c>.</summary>
    public static string Key(Guid groupInstanceGuid) => KeyPrefix + groupInstanceGuid;

    /// <summary>
    /// Renders the marker value written at accept time. Falls back to the legacy
    /// <see cref="LegacyRecognized"/> literal when there is no provenance to carry, so a marker
    /// never grows a JSON envelope around three nulls.
    /// </summary>
    public static string Serialize(string? provider, string? model, double? confidence)
    {
        var hasProvider = !string.IsNullOrWhiteSpace(provider);
        var hasModel = !string.IsNullOrWhiteSpace(model);

        if (!hasProvider && !hasModel && confidence is null)
        {
            return LegacyRecognized;
        }

        return JsonSerializer.Serialize(
            new MarkerDto
            {
                Provider = hasProvider ? provider!.Trim() : null,
                Model = hasModel ? model!.Trim() : null,
                Confidence = confidence,
            },
            Options);
    }

    /// <summary>
    /// Parses a marker value read back from the ValueTable.
    /// Returns null when the group is NOT recognized (absent key, <see cref="Absent"/>, blank, or
    /// an unreadable value -- never guess, mirroring CanvasAnnotationParser's contract); a
    /// <see cref="RecognitionProvenance"/> with all-null fields for the legacy
    /// <see cref="LegacyRecognized"/> literal; and the carried fields for a JSON marker.
    /// </summary>
    public static RecognitionProvenance? TryParse(string? rawValue)
    {
        var value = rawValue?.Trim();

        if (string.IsNullOrEmpty(value)
            || string.Equals(value, Absent, StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        if (string.Equals(value, LegacyRecognized, StringComparison.OrdinalIgnoreCase))
        {
            return new RecognitionProvenance(null, null, null);
        }

        if (value[0] != '{')
        {
            // Not the legacy literal and not a JSON object -- an unrelated key collision or a
            // corrupted value. Treat as not recognized rather than inventing provenance.
            return null;
        }

        try
        {
            var dto = JsonSerializer.Deserialize<MarkerDto>(value, Options);
            return dto is null
                ? null
                : new RecognitionProvenance(
                    string.IsNullOrWhiteSpace(dto.Provider) ? null : dto.Provider!.Trim(),
                    string.IsNullOrWhiteSpace(dto.Model) ? null : dto.Model!.Trim(),
                    dto.Confidence);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private sealed class MarkerDto
    {
        public string? Provider { get; init; }

        public string? Model { get; init; }

        public double? Confidence { get; init; }
    }
}
