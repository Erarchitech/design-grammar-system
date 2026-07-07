using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Deterministic ID generation for the DG state model hierarchy.
/// Every state entity (ParamState, PropState, ObjState, DesignState) gets a content-addressed
/// StateId — identical inputs produce identical StateId, enabling dedup across validation runs
/// via MERGE by StateId+project.
/// </summary>
public static class DesignStateIdGenerator
{
    private const string ParamStatePrefix = "DS_";
    private const string ObjectStatePrefix = "OS_";
    private const string PropStatePrefix = "PS_";
    private const string DesignStatePrefix = "DS_";

    /// <summary>
    /// IdRef = ParamState.StateId, reused (not separately hashed) — wired into DESIGN STATE
    /// component output in Phase 9 per CMPST-08.
    /// </summary>
    public const string IdRefPrefix = "IDR_";

    /// <summary>
    /// Produces a 16-character hex StateId, DS_-prefixed, deterministic over the sorted
    /// parameter ID + value pairs. Identical parameter sets always produce the same StateId.
    /// </summary>
    public static string ComputeParamStateId(IEnumerable<DesignStateParameter> parameters)
    {
        var sb = new StringBuilder();

        foreach (var p in parameters.OrderBy(x => x.ParameterId, StringComparer.Ordinal))
        {
            sb.Append(p.ParameterId);
            sb.Append('=');
            sb.Append(p.Type switch
            {
                DesignStateParameterType.Boolean => p.BooleanValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
                DesignStateParameterType.Integer => p.IntegerValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
                DesignStateParameterType.Number => p.NumberValue?.ToString("R", CultureInfo.InvariantCulture) ?? "null",
                _ => "null",
            });
            sb.Append(';');
        }

        return ParamStatePrefix + HashToHex16(sb.ToString());
    }

    /// <summary>
    /// Produces an OS_-prefixed StateId: OS_&lt;SHA256(projectId + objectInstanceId + variableName)&gt;
    /// for the ObjState model. Cross-rule (no rule-scoping input) per CMPST-07 — Object variables
    /// are shared across rules.
    /// </summary>
    public static string ComputeObjectStateId(string projectId, string objectInstanceId, string variableName)
    {
        var input = $"{projectId}|{objectInstanceId}|{variableName}";
        return ObjectStatePrefix + HashToHex16(input);
    }

    /// <summary>
    /// Produces a PS_-prefixed StateId for PropState: PS_&lt;SHA256(ruleIri|dataPropertyIri|propValueLex[|objectRef])&gt;.
    /// Deterministic over the Rule IRI, DataProperty IRI, and the typed property value.
    /// When <paramref name="objectRef"/> is provided (per-object properties), it is folded into
    /// the hash so two objects sharing the same value get distinct StateIds (no MERGE collision).
    /// Same Rule + DataProperty + value (+ object) → same StateId across validation runs.
    /// </summary>
    public static string ComputePropStateId(
        string ruleIri,
        string dataPropertyIri,
        DesignStateParameter propValue,
        string? objectRef = null)
    {
        var lex = propValue.Type switch
        {
            DesignStateParameterType.Number => propValue.NumberValue?.ToString("R", CultureInfo.InvariantCulture) ?? "null",
            DesignStateParameterType.Integer => propValue.IntegerValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
            DesignStateParameterType.Boolean => propValue.BooleanValue?.ToString(CultureInfo.InvariantCulture) ?? "null",
            _ => "null",
        };

        var input = string.IsNullOrWhiteSpace(objectRef)
            ? $"{ruleIri}|{dataPropertyIri}|{lex}"
            : $"{ruleIri}|{dataPropertyIri}|{lex}|{objectRef}";
        return PropStatePrefix + HashToHex16(input);
    }

    /// <summary>
    /// Produces a DS_-prefixed aggregate StateId for DesignState: DS_&lt;SHA256(sorted member StateIds)&gt;.
    /// Deterministic over sorted member StateIds. Same member set → same StateId → dedup across
    /// validation runs via MERGE by StateId+project. The DS_ prefix is shared with ParamStatePrefix
    /// but the hash input domains differ (parameters vs. member StateId concatenation), so IDs from
    /// the two methods are distinct.
    /// </summary>
    public static string ComputeDesignStateId(IEnumerable<string> memberStateIds)
    {
        var sb = new StringBuilder();
        foreach (var id in memberStateIds.OrderBy(x => x, StringComparer.Ordinal))
        {
            sb.Append(id);
        }

        return DesignStatePrefix + HashToHex16(sb.ToString());
    }

    private static string HashToHex16(string input)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16];
    }
}
