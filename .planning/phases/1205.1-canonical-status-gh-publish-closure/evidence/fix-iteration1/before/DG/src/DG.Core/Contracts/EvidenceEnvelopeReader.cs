using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace DG.Core.Contracts;

/// <summary>Admitted projection, not a rewritten historical envelope. Missing rows stay absent in JSON.</summary>
public sealed record EvidenceEnvelopeReadResult(
    string ContractVersion, IReadOnlyList<EvidenceRow> Rows,
    IReadOnlyList<EvidenceRuleResult> RuleResults);

/// <summary>
/// Exact version dispatch and explicit shape guards on net7/net9. JsonSerializer alone
/// ignores unknown fields and supplies defaults: it is deliberately NOT our admission gate.
/// </summary>
public static class EvidenceEnvelopeReader
{
    private static readonly string[] RequiredEnvelope =
    {
        "contractVersion", "canonicalizationVersion", "project", "definitionId", "serviceName",
        "serviceVersion", "emittedAt", "stage", "canonicalStatus", "rows"
    };
    private static readonly HashSet<string> AllowedEnvelope = new(RequiredEnvelope.Concat(new[]
    {
        "dgId", "sourceRepresentation", "inputHash", "outputHash", "schemaVersion",
        "ontologyVersion", "ruleVersion", "shapeVersion", "provider", "model", "warnings"
    }), StringComparer.Ordinal);
    private static readonly string[] RequiredRow = { "ruleId", "objectId", "canonicalStatus" };
    private static readonly HashSet<string> AllowedRow = new(RequiredRow.Concat(new[]
        { "warnings", "inputHash", "outputHash", "detail" }), StringComparer.Ordinal);
    private static readonly string[] RequiredRule = { "ruleId", "canonicalStatus", "warnings" };
    private static readonly HashSet<string> AllowedRule = new(RequiredRule.Concat(new[] { "detail" }), StringComparer.Ordinal);
    private static readonly JsonSerializerOptions WireOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    public static bool TryRead(string? json, out EvidenceEnvelopeReadResult? result)
    {
        result = null;
        if (string.IsNullOrWhiteSpace(json)) return false;
        try
        {
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;
            if (!Version(root, out var version)) return false;
            if (version == EvidenceEnvelopeFactory.ContractVersionV2)
            {
                if (!FullShape(root, isV2: true)) return false;
                var envelope = JsonSerializer.Deserialize<EvidenceEnvelopeV2>(root.GetRawText())!;
                result = new(version, envelope.Rows, envelope.RuleResults);
            }
            else
            {
                // The historical exception does NOT deserialize a partial full DTO or
                // manufacture timestamps/summary verdicts. Only present rows are projected.
                if (root.TryGetProperty("ruleResults", out _) ||
                    !OptionalStatus(root) || !Rows(root, required: false)) return false;
                var rows = root.TryGetProperty("rows", out var array)
                    ? JsonSerializer.Deserialize<List<EvidenceRow>>(array.GetRawText())!
                    : new List<EvidenceRow>();
                result = new(version, rows, Array.Empty<EvidenceRuleResult>());
            }
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    /// <summary>Strict full admission, separate from the historical projection exception.</summary>
    public static bool IsStrictEnvelope(string json)
    {
        try
        {
            using var document = JsonDocument.Parse(json);
            return Version(document.RootElement, out var version) &&
                   FullShape(document.RootElement, version == EvidenceEnvelopeFactory.ContractVersionV2);
        }
        catch (JsonException) { return false; }
    }

    public static string Serialize(EvidenceEnvelopeV2 envelope)
    {
        var json = JsonSerializer.Serialize(envelope, WireOptions);
        if (!IsStrictEnvelope(json)) throw new ArgumentException("Invalid full v2 evidence envelope", nameof(envelope));
        // The full union admits old tokens, but this named writer must never emit one.
        if (envelope.ContractVersion != EvidenceEnvelopeFactory.ContractVersionV2)
            throw new ArgumentException("Expected exact v2 contractVersion", nameof(envelope));
        return json;
    }

    private static bool Version(JsonElement root, out string version)
    {
        version = string.Empty;
        if (root.ValueKind != JsonValueKind.Object ||
            !root.TryGetProperty("contractVersion", out var token) || token.ValueKind != JsonValueKind.String)
            return false;
        version = token.GetString()!;
        return version is "1" or EvidenceEnvelopeFactory.ContractVersion or EvidenceEnvelopeFactory.ContractVersionV2;
    }

    private static bool Fields(JsonElement value, IEnumerable<string> required, HashSet<string> allowed)
    {
        if (value.ValueKind != JsonValueKind.Object) return false;
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var field in value.EnumerateObject())
            if (!allowed.Contains(field.Name) || !seen.Add(field.Name)) return false;
        return required.All(seen.Contains);
    }

    private static bool FullShape(JsonElement root, bool isV2)
    {
        var allowed = new HashSet<string>(AllowedEnvelope, StringComparer.Ordinal);
        var required = RequiredEnvelope.AsEnumerable();
        if (isV2)
        {
            allowed.Add("ruleResults");
            required = required.Append("ruleResults");
        }
        if (!Fields(root, required, allowed) || !Rows(root, required: true) || !OptionalStatus(root)) return false;
        foreach (var field in root.EnumerateObject())
        {
            switch (field.Name)
            {
                case "rows": case "canonicalStatus": break;
                case "canonicalizationVersion":
                    if (field.Value.ValueKind != JsonValueKind.Number || !field.Value.TryGetInt32(out _)) return false;
                    break;
                case "sourceRepresentation":
                    if (field.Value.ValueKind is not (JsonValueKind.Object or JsonValueKind.Null)) return false;
                    break;
                case "warnings":
                    if (!Strings(field.Value)) return false;
                    break;
                case "ruleResults":
                    if (!RuleResults(field.Value)) return false;
                    break;
                default:
                    if (!StringField(field.Name, field.Value)) return false;
                    break;
            }
        }
        return true;
    }

    private static bool OptionalStatus(JsonElement value) =>
        !value.TryGetProperty("canonicalStatus", out var status) ||
        (status.ValueKind == JsonValueKind.String && EvidenceStatusNames.TryParseWireName(status.GetString(), out _));

    private static bool Rows(JsonElement root, bool required)
    {
        if (!root.TryGetProperty("rows", out var rows)) return !required;
        if (rows.ValueKind != JsonValueKind.Array) return false;
        return rows.EnumerateArray().All(row => Record(row, RequiredRow, AllowedRow));
    }

    private static bool RuleResults(JsonElement results)
    {
        if (results.ValueKind != JsonValueKind.Array) return false;
        string? previous = null;
        foreach (var rule in results.EnumerateArray())
        {
            if (!Record(rule, RequiredRule, AllowedRule)) return false;
            var id = rule.GetProperty("ruleId").GetString()!;
            // Strictly ascending also rejects duplicate rule identities, even if statuses differ.
            if (previous is not null && StringComparer.Ordinal.Compare(previous, id) >= 0) return false;
            previous = id;
        }
        return true;
    }

    private static bool Record(JsonElement record, string[] required, HashSet<string> allowed)
    {
        if (!Fields(record, required, allowed) || !OptionalStatus(record)) return false;
        foreach (var field in record.EnumerateObject())
        {
            if (field.Name == "canonicalStatus") continue;
            if (field.Name == "warnings")
            {
                if (!Strings(field.Value)) return false;
            }
            else if (!StringField(field.Name, field.Value)) return false;
        }
        return true;
    }

    private static bool Strings(JsonElement value) => value.ValueKind == JsonValueKind.Array &&
        value.EnumerateArray().All(item => item.ValueKind == JsonValueKind.String);

    private static bool StringField(string name, JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.String) return false;
        var text = value.GetString()!;
        return name switch
        {
            "inputHash" or "outputHash" => Regex.IsMatch(text, "\\A[0-9A-F]{64}\\z"),
            "dgId" => Regex.IsMatch(text, "\\Adg:[0-9A-F]{16}\\z"),
            _ => true // date-time format remains annotation, as in the existing JSON Schema validator.
        };
    }
}
