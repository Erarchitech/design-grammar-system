#if GRASSHOPPER_SDK
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Serialization;
using DG.Core.Services;
using DG.Core.Validation;
using CoreBindingRow = DG.Core.Models.BindingRow;
using CoreDesignState = DG.Core.Models.DesignState;
using CoreRule = DG.Core.Models.Rule;
using CoreRuleEvaluationResult = DG.Core.Models.RuleEvaluationResult;

namespace DG.Grasshopper.Validation;

internal static class ValidationPublishClient
{
    // Named per D-04's Artifacts table; used only in error-template text, never in a header.
    private const string ComponentName = "VALIDATOR";

    private static readonly HttpClient HttpClient = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public static ValidationPublishResponse Publish(
        IReadOnlyList<CoreRule> rules,
        IReadOnlyList<CoreRuleEvaluationResult> results,
        IReadOnlyList<CoreBindingRow> bindings,
        string dataServiceUrl,
        string? token,
        CoreDesignState? designState = null,
        List<bool>? validStatus = null)
    {
        var package = ValidationPublishPackageBuilder.Build(rules, results, bindings);
        var (statePayloadJson, stateWarning) = SerializeDesignState(designState);
        var request = BuildRequest(package, statePayloadJson);
        request.ValidStatus = validStatus;
        var endpoint = $"{NormalizeUrl(dataServiceUrl)}/validation/publish";

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = JsonContent.Create(request, options: JsonOptions),
        };

        // D-04/Correction 5: the token is required to publish. Bail out before any
        // network I/O when it's missing or malformed — the token itself never
        // enters an exception message (DataServiceRequestAuth doc-comment discipline).
        if (!DataServiceRequestAuth.TryApplyConnectorToken(httpRequest, token, out _))
        {
            throw new InvalidOperationException(ErrorMessageTemplates.PublishTokenMissing(ComponentName));
        }

        using var response = HttpClient.SendAsync(httpRequest).GetAwaiter().GetResult();
        var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        if (!response.IsSuccessStatusCode)
        {
            var outcome = DataServiceRequestAuth.ClassifyStatus(response.StatusCode);
            var message = outcome switch
            {
                PublishAuthOutcome.Rejected => ErrorMessageTemplates.PublishTokenRejected(ComponentName),
                PublishAuthOutcome.Forbidden => ErrorMessageTemplates.PublishProjectForbidden(ComponentName),
                _ => $"Validation publish failed ({(int)response.StatusCode}): {body}",
            };
            throw new InvalidOperationException(message);
        }

        var parsed = JsonSerializer.Deserialize<ValidationPublishResponse>(body, JsonOptions);
        if (parsed is null)
        {
            throw new InvalidOperationException("Validation publish failed: backend returned an empty response.");
        }

        if (!string.IsNullOrWhiteSpace(stateWarning))
        {
            parsed = new ValidationPublishResponse
            {
                Status = stateWarning,
                RunId = parsed.RunId,
                ModelViewerUrl = parsed.ModelViewerUrl,
                ValidationModelId = parsed.ValidationModelId,
                ValidationVersionId = parsed.ValidationVersionId,
                BaseVersionId = parsed.BaseVersionId,
                Shacl = parsed.Shacl,
            };
        }

        return parsed;
    }

    private static (string? Json, string? Warning) SerializeDesignState(CoreDesignState? designState)
    {
        if (designState is null)
        {
            return (null, null);
        }

        try
        {
            return (DesignStatePayloadV2Serializer.Serialize(designState), null);
        }
        catch (InvalidOperationException ex)
        {
            // Surface the validation error so the user can fix their DesignState wiring.
            return (null, $"DesignState not saved: {ex.Message}");
        }
    }

    private static ValidationPublishRequest BuildRequest(ValidationPublishPackage package, string? statePayloadJson)
    {
        var request = new ValidationPublishRequest
        {
            Project = package.Project,
            StatePayloadJson = statePayloadJson,
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
