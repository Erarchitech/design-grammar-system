#if GRASSHOPPER_SDK
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using DG.Core.Models;
using DG.Core.Validation;
using CoreBindingRow = DG.Core.Models.BindingRow;
using CoreRule = DG.Core.Models.Rule;
using CoreRuleEvaluationResult = DG.Core.Models.RuleEvaluationResult;

namespace DG.Grasshopper.Validation;

internal static class ValidationPublishClient
{
    private static readonly HttpClient HttpClient = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public static ValidationPublishResponse Publish(
        IReadOnlyList<CoreRule> rules,
        IReadOnlyList<CoreRuleEvaluationResult> results,
        IReadOnlyList<CoreBindingRow> bindings,
        string dataServiceUrl)
    {
        var package = ValidationPublishPackageBuilder.Build(rules, results, bindings);
        var request = BuildRequest(package);
        var endpoint = $"{NormalizeUrl(dataServiceUrl)}/validation/publish";
        using var response = HttpClient.PostAsJsonAsync(endpoint, request, JsonOptions).GetAwaiter().GetResult();
        var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Validation publish failed ({(int)response.StatusCode}): {body}");
        }

        var parsed = JsonSerializer.Deserialize<ValidationPublishResponse>(body, JsonOptions);
        if (parsed is null)
        {
            throw new InvalidOperationException("Validation publish failed: backend returned an empty response.");
        }

        return parsed;
    }

    private static ValidationPublishRequest BuildRequest(ValidationPublishPackage package)
    {
        var request = new ValidationPublishRequest
        {
            Project = package.Project,
        };

        foreach (var rule in package.Rules)
        {
            request.Rules.Add(new ValidationPublishRulePayload
            {
                RuleId = rule.RuleId,
                RuleName = rule.RuleName,
                RuleDescription = rule.RuleDescription,
            });
        }

        foreach (var ruleResult in package.RuleResults)
        {
            var payload = new ValidationPublishRuleResultPayload
            {
                RuleId = ruleResult.RuleId,
                Passed = ruleResult.Passed,
            };
            payload.FailedEntityIds.AddRange(ruleResult.FailedEntityIds);
            payload.PassedEntityIds.AddRange(ruleResult.PassedEntityIds);
            request.RuleResults.Add(payload);
        }

        foreach (var entity in package.Entities)
        {
            var payload = new ValidationPublishEntityPayload
            {
                DgEntityId = entity.DgEntityId,
                DisplayName = entity.DisplayName,
                Geometry = ValidationGeometryPayloadSerializer.Serialize(entity.Geometry),
                OverallStatus = entity.OverallStatus,
            };
            payload.RuleIds.AddRange(entity.RuleIds);
            payload.FailedRuleIds.AddRange(entity.FailedRuleIds);
            payload.PassedRuleIds.AddRange(entity.PassedRuleIds);
            request.Entities.Add(payload);
        }

        return request;
    }

    private static string NormalizeUrl(string dataServiceUrl)
    {
        var normalized = string.IsNullOrWhiteSpace(dataServiceUrl)
            ? "http://localhost:8000"
            : dataServiceUrl.Trim();
        return normalized.TrimEnd('/');
    }
}
#else
namespace DG.Grasshopper.Validation;

internal static class ValidationPublishClient
{
}
#endif
