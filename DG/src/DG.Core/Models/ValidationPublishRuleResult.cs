namespace DG.Core.Models;

public sealed class ValidationPublishRuleResult
{
    public string RuleId { get; init; } = string.Empty;

    public bool Passed { get; init; }

    public List<string> FailedEntityIds { get; } = new();

    public List<string> PassedEntityIds { get; } = new();
}
