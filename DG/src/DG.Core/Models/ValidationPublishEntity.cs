using DG.Core.Contracts;

namespace DG.Core.Models;

public sealed class ValidationPublishEntity
{
    public string DgEntityId { get; init; } = string.Empty;

    public string? DisplayName { get; set; }

    public object? Geometry { get; set; }

    public List<string> RuleIds { get; } = new();

    public List<string> FailedRuleIds { get; } = new();

    public List<string> PassedRuleIds { get; } = new();

    /// <summary>Authoritative per-rule outcomes, independent of the retained legacy lists.</summary>
    public Dictionary<string, EvidenceStatus> CanonicalStatuses { get; } = new(StringComparer.Ordinal);

    public Dictionary<string, List<string>> CanonicalWarnings { get; } = new(StringComparer.Ordinal);

    public Dictionary<string, string> CanonicalDetails { get; } = new(StringComparer.Ordinal);

    public string OverallStatus =>
        FailedRuleIds.Count > 0 ? "failed" : PassedRuleIds.Count > 0 ? "passed" : "unknown";
}
