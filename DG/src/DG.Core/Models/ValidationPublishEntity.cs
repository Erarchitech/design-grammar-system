namespace DG.Core.Models;

public sealed class ValidationPublishEntity
{
    public string DgEntityId { get; init; } = string.Empty;

    public string? DisplayName { get; set; }

    public object? Geometry { get; set; }

    public List<string> RuleIds { get; } = new();

    public List<string> FailedRuleIds { get; } = new();

    public List<string> PassedRuleIds { get; } = new();

    public string OverallStatus =>
        FailedRuleIds.Count > 0 ? "failed" : PassedRuleIds.Count > 0 ? "passed" : "unknown";
}
