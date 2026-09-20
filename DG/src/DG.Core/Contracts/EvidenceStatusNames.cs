using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace DG.Core.Contracts;

/// <summary>
/// The single C#-side wire-form mapping for <see cref="EvidenceStatus"/> (spec/EVIDENCE-CONTRACT.md
/// section 1, D-02). No other file in this codebase may hardcode a second copy of these eight
/// snake_case literals. The mapping is written as an explicit per-member switch, not a generic
/// PascalCase-to-snake_case transformation, so the wire forms are greppable and a renamed enum
/// member produces a compile error (via the throwing <c>default</c> arm surfacing at test time)
/// rather than a silently changed wire string.
/// </summary>
public static class EvidenceStatusNames
{
    /// <summary>
    /// The eight snake_case wire forms, in <see cref="EvidenceStatus"/> declaration order, for test
    /// assertion against <c>spec/evidence-contract.schema.json</c>'s <c>$defs.CanonicalStatus.enum</c>.
    /// </summary>
    public static readonly IReadOnlyList<string> AllWireNames = new[]
    {
        ToWireName(EvidenceStatus.Passed),
        ToWireName(EvidenceStatus.Failed),
        ToWireName(EvidenceStatus.Unknown),
        ToWireName(EvidenceStatus.NotEvaluated),
        ToWireName(EvidenceStatus.NoPopulation),
        ToWireName(EvidenceStatus.Unsupported),
        ToWireName(EvidenceStatus.Indeterminate),
        ToWireName(EvidenceStatus.Error),
    };

    /// <summary>
    /// Maps an <see cref="EvidenceStatus"/> member to its snake_case wire form. The <c>default</c>
    /// arm throws naming the offending value, so adding a ninth enum member without updating this
    /// switch fails loudly instead of silently falling through.
    /// </summary>
    public static string ToWireName(EvidenceStatus status)
    {
        return status switch
        {
            EvidenceStatus.Passed => "passed",
            EvidenceStatus.Failed => "failed",
            EvidenceStatus.Unknown => "unknown",
            EvidenceStatus.NotEvaluated => "not_evaluated",
            EvidenceStatus.NoPopulation => "no_population",
            EvidenceStatus.Unsupported => "unsupported",
            EvidenceStatus.Indeterminate => "indeterminate",
            EvidenceStatus.Error => "error",
            _ => throw new ArgumentOutOfRangeException(nameof(status), status, $"EvidenceStatusNames.ToWireName: unmapped EvidenceStatus member '{status}'. Add an explicit switch arm — this mapping must never fall back to a generic transformation."),
        };
    }

    /// <summary>
    /// Attempts to parse a snake_case wire form back into its <see cref="EvidenceStatus"/> member.
    /// Returns <c>false</c> for any string not in the frozen eight-member vocabulary, rather than
    /// defaulting to the enum's zero member.
    /// </summary>
    public static bool TryParseWireName(string? wireName, out EvidenceStatus status)
    {
        switch (wireName)
        {
            case "passed":
                status = EvidenceStatus.Passed;
                return true;
            case "failed":
                status = EvidenceStatus.Failed;
                return true;
            case "unknown":
                status = EvidenceStatus.Unknown;
                return true;
            case "not_evaluated":
                status = EvidenceStatus.NotEvaluated;
                return true;
            case "no_population":
                status = EvidenceStatus.NoPopulation;
                return true;
            case "unsupported":
                status = EvidenceStatus.Unsupported;
                return true;
            case "indeterminate":
                status = EvidenceStatus.Indeterminate;
                return true;
            case "error":
                status = EvidenceStatus.Error;
                return true;
            default:
                status = default;
                return false;
        }
    }
}

/// <summary>
/// Serializes <see cref="EvidenceStatus"/> to/from its snake_case wire form. This is genuinely new
/// infrastructure in this codebase: per 1200-PATTERNS.md's "No Analog Found" finding, zero other
/// enums in <c>DG.Core</c> use <see cref="JsonStringEnumConverter"/>, a naming policy, or any custom
/// converter — every other enum here serializes as its default PascalCase name (or as an int).
/// This converter exists solely because the evidence contract's wire form is snake_case
/// (spec/EVIDENCE-CONTRACT.md); it must not be generalized to any other enum in this codebase
/// without an explicit decision, since that would be a much broader behavior change than this
/// plan's scope.
/// </summary>
public sealed class EvidenceStatusJsonConverter : JsonConverter<EvidenceStatus>
{
    public override EvidenceStatus Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var raw = reader.GetString();
        if (!EvidenceStatusNames.TryParseWireName(raw, out var status))
        {
            throw new JsonException($"EvidenceStatusJsonConverter: unrecognized EvidenceStatus wire value '{raw}'. Expected one of: {string.Join(", ", EvidenceStatusNames.AllWireNames)}.");
        }

        return status;
    }

    public override void Write(Utf8JsonWriter writer, EvidenceStatus value, JsonSerializerOptions options)
    {
        writer.WriteStringValue(EvidenceStatusNames.ToWireName(value));
    }
}
