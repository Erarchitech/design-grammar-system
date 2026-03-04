namespace DG.Core.Models;

public sealed class RuleEvaluationResult
{
    public string RuleId { get; init; } = string.Empty;

    public string RuleName { get; init; } = string.Empty;

    public string RuleDescription { get; init; } = string.Empty;

    public bool Passed { get; init; }

    public string Message { get; init; } = string.Empty;

    public List<BindingRow> FailingBindings { get; } = new();
}
