using System.Text.Json;
using DG.Core.Models;

namespace DG.Core.Validation;

public static class ValidationReportFormatter
{
    public static string ToReportLine(RuleEvaluationResult result)
    {
        var status = result.Passed ? "PASS" : "NO PASS";
        return $"{status} | {result.RuleName} | {result.RuleDescription} | {result.Message}";
    }

    public static IReadOnlyList<string> SerializeFailingBindings(RuleEvaluationResult result)
    {
        return result.FailingBindings
            .Select(binding => JsonSerializer.Serialize(binding.ValuesByVar))
            .ToList();
    }
}
