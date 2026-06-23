using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Deterministic ID generation for the v3.0 DesignState hierarchy. Relocated from
/// DesignStateComponent.ComputeStateId (Grasshopper-coupled, #if GRASSHOPPER_SDK)
/// into DG.Core so it is pure logic, testable without a GH SDK reference.
/// </summary>
public static class DesignStateIdGenerator
{
    private const string DefStatePrefix = "DS_";
    private const string ObjectStatePrefix = "OS_";
    private const string ObjectInstancePrefix = "OI_";

    /// <summary>
    /// IdRef = DefState.StateId, reused (not separately hashed) — wired into DESIGN STATE
    /// component output in Phase 9 per CMPST-08.
    /// </summary>
    public const string IdRefPrefix = "IDR_";

    /// <summary>
    /// Produces a 16-character hex StateId, DS_-prefixed, deterministic over the sorted
    /// parameter ID + value pairs. Identical parameter sets always produce the same StateId.
    /// </summary>
    public static string ComputeDefStateId(IEnumerable<DesignStateParameter> parameters)
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

        return DefStatePrefix + HashToHex16(sb.ToString());
    }

    /// <summary>
    /// Produces an OS_-prefixed StateId: OS_&lt;SHA256(projectId + objectInstanceId + variableName)&gt;.
    /// Cross-rule (no rule-scoping input) per CMPST-07 — Object variables are shared across rules.
    /// </summary>
    public static string ComputeObjectStateId(string projectId, string objectInstanceId, string variableName)
    {
        var input = $"{projectId}|{objectInstanceId}|{variableName}";
        return ObjectStatePrefix + HashToHex16(input);
    }

    /// <summary>
    /// Produces an OI_-prefixed InstanceId for ObjectInstance, the cross-rule identity anchor.
    /// The seed parameter lets the caller supply a stable disambiguator (e.g. the user-supplied
    /// ObjectRef string); the actual call site is wired in Phase 9.
    /// </summary>
    public static string ComputeObjectInstanceId(string projectId, string variableName, string seed)
    {
        var input = $"{projectId}|{variableName}|{seed}";
        return ObjectInstancePrefix + HashToHex16(input);
    }

    private static string HashToHex16(string input)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(hash)[..16];
    }
}
