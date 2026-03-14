namespace DG.Core.Models;

public sealed class ValidationPublishPackage
{
    public string Project { get; init; } = "default-project";

    public List<ValidationPublishRule> Rules { get; } = new();

    public List<ValidationPublishRuleResult> RuleResults { get; } = new();

    public List<ValidationPublishEntity> Entities { get; } = new();
}
