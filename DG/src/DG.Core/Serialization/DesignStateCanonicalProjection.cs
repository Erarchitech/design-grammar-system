using System.Globalization;
using System.Text.Json.Nodes;
using DG.Core.Contracts;
using DG.Core.Models;

namespace DG.Core.Serialization;

/// <summary>
/// Canonical DesignState projection and content hash (Phase 1202, ALGN12-08/ALGN12-09, D-01/D-02).
///
/// This is the normative definition of what a DesignState's <c>canonicalStateHash</c> is computed
/// over. It is an *extension* of the Phase 1200 hasher, not a new hashing primitive:
/// <see cref="ComputeHash"/> builds a <see cref="JsonObject"/> from a <see cref="DesignState"/> and
/// feeds it straight into <see cref="CanonicalJsonWriter.HashCanonical"/> — the same function
/// already hardened by CR-01 (decimal scale) and WR-01 (negative zero) and already
/// cross-language-verified against <c>data-service/canonical_json.py</c>. No second
/// canonicalization is introduced here.
///
/// Projection shape (all keys always present; canonical-writer sorts object keys ordinally at
/// hash time regardless of authoring order below, so this order is documentation, not contract):
/// <list type="bullet">
/// <item><c>stateId</c> — the DesignState's StateId.</item>
/// <item><c>label</c> — the DesignState's Label, or JSON null when absent. Absent and
/// present-but-null are represented identically (JSON null), so the two cannot collide with a
/// third "omitted" state that doesn't exist in this schema.</item>
/// <item><c>capturedAtUtc</c> — ISO-8601 round-trip ("O", invariant culture, UTC) string, the same
/// rendering <see cref="DesignStatePayloadV2Serializer"/> already uses, so the two never
/// disagree.</item>
/// <item><c>members</c> — the ALGN12-09 membership manifest: a JSON array of
/// <c>{kind, stateId}</c> objects, one per ObjState/ParamState/PropState, sorted by kind then
/// StateId (<see cref="StringComparer.Ordinal"/>). Folding the manifest into the hashed
/// projection (rather than shipping it as a separate artifact) makes membership tamper-evident
/// for free — a manifest that can drift from the thing it manifests is worse than no manifest.</item>
/// <item><c>objStates</c> — array sorted by StateId ordinal. <b>Geometry is omitted by
/// construction</b> — this is the D-06 exclusion contract: geometry has no stable JSON form, is
/// referenced by <c>dgId</c> / Speckle <c>objectId</c> instead, and the direct consequence is that
/// replay cannot reconstruct a viewable state offline. That is the accepted cost, not an
/// oversight.</item>
/// <item><c>paramStates</c> — array sorted by StateId ordinal; each entry's <c>parameters</c> array
/// is sorted by ParameterId ordinal.</item>
/// <item><c>propStates</c> — array sorted by StateId ordinal. <b>PropState carries no
/// CapturedAtUtc on the model</b> (unlike DesignState/ObjState/ParamState) and this is a
/// deliberate exclusion, not an omission: PropState is value-scoped (rule IRI + property IRI +
/// value), not capture-scoped, so adding a capture time to it would make two identical property
/// assertions captured a second apart hash differently — which contradicts the content-hash
/// purpose.</item>
/// </list>
///
/// Numeric handling: <see cref="CanonicalJsonWriter"/> rule 2 throws on <see cref="double"/>/
/// <see cref="float"/>. Every <see cref="DesignStateParameter.NumberValue"/> is converted to
/// <see cref="decimal"/> before entering the projection. When the conversion would overflow or
/// the value is NaN/Infinity, this class throws a named <see cref="InvalidOperationException"/>
/// naming the parameter id — never coerces silently (fail-closed, V5 scoping).
///
/// Sorting throughout uses <see cref="StringComparer.Ordinal"/>, matching
/// <see cref="DesignStatePayloadV2Serializer.Serialize"/>'s existing comparator.
/// <see cref="CanonicalJsonWriter"/> itself only sorts JSON *object* keys, never array elements —
/// this class is responsible for ordering every array it builds.
/// </summary>
public static class DesignStateCanonicalProjection
{
    /// <summary>
    /// Builds the canonical JSON projection of <paramref name="designState"/> per this class's
    /// documented shape. Geometry is never read or written. Throws
    /// <see cref="InvalidOperationException"/> if a parameter's numeric value cannot be
    /// represented as <see cref="decimal"/> (NaN/Infinity/overflow).
    /// </summary>
    public static JsonObject Build(DesignState designState)
    {
        ArgumentNullException.ThrowIfNull(designState);

        var members = new JsonArray();
        foreach (var entry in BuildMembers(designState))
        {
            members.Add(entry);
        }

        return new JsonObject
        {
            ["stateId"] = designState.StateId,
            ["label"] = designState.Label,
            ["capturedAtUtc"] = FormatCapturedAt(designState.CapturedAtUtc),
            ["members"] = members,
            ["objStates"] = BuildObjStates(designState.ObjStates),
            ["paramStates"] = BuildParamStates(designState.ParamStates),
            ["propStates"] = BuildPropStates(designState.PropStates),
        };
    }

    /// <summary>
    /// Thin wrapper: <c>CanonicalJsonWriter.HashCanonical(Build(designState))</c>. This is the
    /// <c>canonicalStateHash</c> for <paramref name="designState"/>.
    /// </summary>
    public static string ComputeHash(DesignState designState)
    {
        return CanonicalJsonWriter.HashCanonical(Build(designState));
    }

    private static IEnumerable<JsonObject> BuildMembers(DesignState designState)
    {
        var entries = new List<(string Kind, string StateId)>();

        foreach (var objState in designState.ObjStates)
        {
            entries.Add(("objState", objState.StateId));
        }

        foreach (var paramState in designState.ParamStates)
        {
            entries.Add(("paramState", paramState.StateId));
        }

        foreach (var propState in designState.PropStates)
        {
            entries.Add(("propState", propState.StateId));
        }

        return entries
            .OrderBy(e => e.Kind, StringComparer.Ordinal)
            .ThenBy(e => e.StateId, StringComparer.Ordinal)
            .Select(e => new JsonObject
            {
                ["kind"] = e.Kind,
                ["stateId"] = e.StateId,
            });
    }

    private static JsonArray BuildObjStates(IEnumerable<ObjState> objStates)
    {
        var array = new JsonArray();

        foreach (var objState in objStates.OrderBy(o => o.StateId, StringComparer.Ordinal))
        {
            // Geometry is intentionally never read here (D-06). Do not add a Geometry key.
            array.Add(new JsonObject
            {
                ["stateId"] = objState.StateId,
                ["objectRef"] = objState.ObjectRef,
                ["label"] = objState.Label,
                ["classIri"] = objState.ClassIri,
                ["dgId"] = objState.DgId,
                ["capturedAtUtc"] = FormatCapturedAt(objState.CapturedAtUtc),
            });
        }

        return array;
    }

    private static JsonArray BuildParamStates(IEnumerable<ParamState> paramStates)
    {
        var array = new JsonArray();

        foreach (var paramState in paramStates.OrderBy(p => p.StateId, StringComparer.Ordinal))
        {
            var parameters = new JsonArray();
            foreach (var parameter in paramState.Parameters.OrderBy(p => p.ParameterId, StringComparer.Ordinal))
            {
                parameters.Add(BuildParameter(parameter));
            }

            array.Add(new JsonObject
            {
                ["stateId"] = paramState.StateId,
                ["capturedAtUtc"] = FormatCapturedAt(paramState.CapturedAtUtc),
                ["parameters"] = parameters,
            });
        }

        return array;
    }

    private static JsonArray BuildPropStates(IEnumerable<PropState> propStates)
    {
        var array = new JsonArray();

        foreach (var propState in propStates.OrderBy(p => p.StateId, StringComparer.Ordinal))
        {
            // PropState carries no CapturedAtUtc on the model -- deliberate exclusion (see class
            // doc-comment), not an omission. Do not add a capturedAtUtc key here.
            array.Add(new JsonObject
            {
                ["stateId"] = propState.StateId,
                ["ruleIri"] = propState.RuleIri,
                ["dataPropertyIri"] = propState.DataPropertyIri,
                ["objectRef"] = propState.ObjectRef,
                ["propValue"] = propState.PropValue is null ? null : BuildParameter(propState.PropValue),
            });
        }

        return array;
    }

    private static JsonObject BuildParameter(DesignStateParameter parameter)
    {
        return new JsonObject
        {
            ["parameterId"] = parameter.ParameterId,
            ["displayName"] = parameter.DisplayName,
            ["type"] = ParameterTypeWireForm(parameter.Type),
            ["value"] = BuildParameterValue(parameter),
        };
    }

    private static JsonNode? BuildParameterValue(DesignStateParameter parameter)
    {
        switch (parameter.Type)
        {
            case DesignStateParameterType.Number:
                return JsonValue.Create(ToCanonicalDecimal(parameter));
            case DesignStateParameterType.Integer:
                return parameter.IntegerValue is long integerValue
                    ? JsonValue.Create(integerValue)
                    : null;
            case DesignStateParameterType.Boolean:
                return parameter.BooleanValue is bool booleanValue
                    ? JsonValue.Create(booleanValue)
                    : null;
            default:
                throw new InvalidOperationException(
                    $"DesignStateCanonicalProjection: parameter '{parameter.ParameterId}' has an unsupported type '{parameter.Type}'.");
        }
    }

    private static decimal ToCanonicalDecimal(DesignStateParameter parameter)
    {
        if (parameter.NumberValue is not double numberValue)
        {
            throw new InvalidOperationException(
                $"DesignStateCanonicalProjection: parameter '{parameter.ParameterId}' is typed Number but carries no NumberValue.");
        }

        if (double.IsNaN(numberValue) || double.IsInfinity(numberValue))
        {
            throw new InvalidOperationException(
                $"DesignStateCanonicalProjection: parameter '{parameter.ParameterId}' has a non-finite NumberValue ({numberValue.ToString(CultureInfo.InvariantCulture)}) which cannot be represented in canonical form (CanonicalJsonWriter rule 6).");
        }

        try
        {
            return Convert.ToDecimal(numberValue, CultureInfo.InvariantCulture);
        }
        catch (OverflowException ex)
        {
            throw new InvalidOperationException(
                $"DesignStateCanonicalProjection: parameter '{parameter.ParameterId}' has a NumberValue that overflows decimal ({numberValue.ToString(CultureInfo.InvariantCulture)}).",
                ex);
        }
    }

    private static string ParameterTypeWireForm(DesignStateParameterType type)
    {
        return type switch
        {
            DesignStateParameterType.Number => "number",
            DesignStateParameterType.Integer => "integer",
            DesignStateParameterType.Boolean => "boolean",
            _ => throw new InvalidOperationException($"DesignStateCanonicalProjection: unsupported parameter type '{type}'."),
        };
    }

    private static string FormatCapturedAt(DateTimeOffset capturedAtUtc)
    {
        return capturedAtUtc.UtcDateTime.ToString("O", CultureInfo.InvariantCulture);
    }
}
