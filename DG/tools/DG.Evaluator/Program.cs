using System.Text.Json;
using DG.Core.Contracts;
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Serialization;
using DG.Core.Validation;

namespace DG.Evaluator;

/// <summary>
/// F-01 (2026-10-29): dg-evaluator. data-service posts the property values the DG Revit connector computed in Revit;
/// this service composes the Design State and judges every requested rule with DG.Core
/// (<see cref="CheckEvaluation"/>), and answers one /validation/publish body per rule, exactly as VALIDATOR would
/// send it, minus geometry (data-service attaches the connector's meshes per dgEntityId). Rules are read from Neo4j
/// with the repository VALIDATOR's RULE BY ID uses, so superseded rules stay excluded.
/// </summary>
public static class Program
{
    public static void Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);
        builder.Services.ConfigureHttpJsonOptions(o => o.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase);
        var app = builder.Build();

        app.MapGet("/health", () => Results.Ok(new { ok = true, service = "dg-evaluator" }));
        app.MapPost("/evaluate", async (EvaluateRequest request, CancellationToken ct) =>
        {
            if (string.IsNullOrWhiteSpace(request.Project) || string.IsNullOrWhiteSpace(request.ClassIri))
                return Results.BadRequest(new { code = "EVALUATE_INVALID", error = "project and classIri are required" });

            var connection = new DG.Core.Models.ConnectionInfo
            {
                Uri = Environment.GetEnvironmentVariable("NEO4J_URI") ?? "bolt://neo4j:7687",
                User = Environment.GetEnvironmentVariable("NEO4J_USER") ?? "neo4j",
                Password = Environment.GetEnvironmentVariable("NEO4J_PASSWORD") ?? string.Empty,
                Project = request.Project,
            };
            IReadOnlyList<Rule> rules;
            try
            {
                rules = await new Neo4jRuleRepository().GetRulesAsync(connection, ct);
            }
            catch (Exception ex)
            {
                return Results.Json(new { code = "EVALUATOR_RULES_UNAVAILABLE", error = $"Could not read the project rules: {ex.Message}" },
                    statusCode: 503);
            }

            return Results.Ok(Evaluate(request, rules));
        });

        app.Run();
    }

    public static EvaluateResponse Evaluate(EvaluateRequest request, IReadOnlyList<Rule> projectRules)
    {
        var state = CheckEvaluation.BuildDesignState(
            request.ClassIri,
            request.Objects.Select(o => new CheckObject { Ref = o.Ref, Label = o.Label }).ToList(),
            request.Values.Select(ToValue).ToList(),
            request.Label);

        string? statePayloadJson = null;
        string? stateWarning = null;
        try
        {
            statePayloadJson = DesignStatePayloadV2Serializer.Serialize(state);
        }
        catch (InvalidOperationException ex)
        {
            stateWarning = $"DesignState not saved: {ex.Message}";
        }

        var byId = projectRules.ToDictionary(r => r.Id, StringComparer.Ordinal);
        var response = new EvaluateResponse { StateId = state.StateId, StatePayloadJson = statePayloadJson, StateWarning = stateWarning };
        foreach (var ruleId in request.RuleIds.Distinct(StringComparer.Ordinal))
        {
            if (!byId.TryGetValue(ruleId, out var rule))
            {
                response.MissingRules.Add(ruleId);
                continue;
            }

            try
            {
                var outcome = CheckEvaluation.EvaluateRule(rule, state);
                var publish = ToPublishRequest(outcome.Package, statePayloadJson);
                publish.ValidStatus = outcome.ValidStatus;
                response.Runs.Add(new EvaluateRun
                {
                    RuleId = rule.Id,
                    RuleName = rule.Name,
                    Status = EvidenceStatusNames.ToWireName(outcome.Result.Status),
                    Report = ValidationReportFormatter.ToReportLine(outcome.Result),
                    Failing = outcome.FailingLines,
                    ValidStatusNames = outcome.ValidStatusNames,
                    Publish = publish,
                });
            }
            catch (InvalidOperationException ex)
            {
                response.Runs.Add(new EvaluateRun { RuleId = rule.Id, RuleName = rule.Name, Status = "error", Report = ex.Message });
            }
        }

        return response;
    }

    private static CheckValue ToValue(EvaluateValue value)
    {
        long? integer = null;
        double? number = null;
        if (value.Value is JsonElement { ValueKind: JsonValueKind.Number } element)
        {
            if (element.TryGetInt64(out var asLong) && !element.GetRawText().Contains('.') && !element.GetRawText().Contains('e')
                && !element.GetRawText().Contains('E'))
                integer = asLong;
            else
                number = element.GetDouble();
        }

        return new CheckValue { RuleId = value.RuleId, DataPropertyIri = value.DataPropertyIri, Ref = value.Ref, Integer = integer, Number = number };
    }

    // The same mapping ValidationPublishClient.BuildRequest applies in Grasshopper, without geometry.
    private static PublishRequest ToPublishRequest(ValidationPublishPackage package, string? statePayloadJson)
    {
        var request = new PublishRequest
        {
            Project = package.Project,
            EvidenceContractVersion = EvidenceEnvelopeFactory.ContractVersionV2,
            StatePayloadJson = statePayloadJson,
        };
        foreach (var rule in package.Rules)
            request.Rules.Add(new PublishRule { RuleId = rule.RuleId, RuleName = rule.RuleName, RuleDescription = rule.RuleDescription });
        foreach (var result in package.RuleResults)
        {
            var payload = new PublishRuleResult
            {
                RuleId = result.RuleId,
                Passed = result.Passed,
                CanonicalStatus = EvidenceStatusNames.ToWireName(result.Status),
                Detail = result.Detail,
            };
            payload.Warnings.AddRange(result.Warnings);
            payload.FailedEntityIds.AddRange(result.FailedEntityIds);
            payload.PassedEntityIds.AddRange(result.PassedEntityIds);
            request.RuleResults.Add(payload);
        }
        foreach (var entity in package.Entities)
        {
            var payload = new PublishEntity { DgEntityId = entity.DgEntityId, DisplayName = entity.DisplayName, OverallStatus = entity.OverallStatus };
            payload.RuleIds.AddRange(entity.RuleIds);
            payload.FailedRuleIds.AddRange(entity.FailedRuleIds);
            payload.PassedRuleIds.AddRange(entity.PassedRuleIds);
            foreach (var pair in entity.CanonicalStatuses)
                payload.CanonicalStatuses[pair.Key] = EvidenceStatusNames.ToWireName(pair.Value);
            foreach (var pair in entity.CanonicalWarnings)
                payload.CanonicalWarnings[pair.Key] = new List<string>(pair.Value);
            foreach (var pair in entity.CanonicalDetails)
                payload.CanonicalDetails[pair.Key] = pair.Value;
            request.Entities.Add(payload);
        }

        return request;
    }
}

public sealed class EvaluateRequest
{
    public string Project { get; init; } = string.Empty;
    public string ClassIri { get; init; } = string.Empty;
    public string? Label { get; init; }
    public List<string> RuleIds { get; init; } = new();
    public List<EvaluateObject> Objects { get; init; } = new();
    public List<EvaluateValue> Values { get; init; } = new();
}

public sealed class EvaluateObject
{
    public string Ref { get; init; } = string.Empty;
    public string? Label { get; init; }
}

public sealed class EvaluateValue
{
    public string RuleId { get; init; } = string.Empty;
    public string DataPropertyIri { get; init; } = string.Empty;
    public string Ref { get; init; } = string.Empty;
    public JsonElement? Value { get; init; }
}

public sealed class EvaluateResponse
{
    public string StateId { get; init; } = string.Empty;
    public string? StatePayloadJson { get; init; }
    public string? StateWarning { get; init; }
    public List<EvaluateRun> Runs { get; } = new();
    public List<string> MissingRules { get; } = new();
}

public sealed class EvaluateRun
{
    public string RuleId { get; init; } = string.Empty;
    public string RuleName { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public string Report { get; init; } = string.Empty;
    public List<string> Failing { get; init; } = new();
    public List<string> ValidStatusNames { get; init; } = new();
    public PublishRequest? Publish { get; init; }
}

public sealed class PublishRequest
{
    public string Project { get; init; } = string.Empty;
    public string? EvidenceContractVersion { get; init; }
    public string? StatePayloadJson { get; init; }
    public List<bool>? ValidStatus { get; set; }
    public List<PublishRule> Rules { get; } = new();
    public List<PublishRuleResult> RuleResults { get; } = new();
    public List<PublishEntity> Entities { get; } = new();
}

public sealed class PublishRule
{
    public string RuleId { get; init; } = string.Empty;
    public string RuleName { get; init; } = string.Empty;
    public string RuleDescription { get; init; } = string.Empty;
}

public sealed class PublishRuleResult
{
    public string RuleId { get; init; } = string.Empty;
    public bool Passed { get; init; }
    public string? CanonicalStatus { get; init; }
    public string? Detail { get; init; }
    public List<string> Warnings { get; } = new();
    public List<string> FailedEntityIds { get; } = new();
    public List<string> PassedEntityIds { get; } = new();
}

public sealed class PublishEntity
{
    public string DgEntityId { get; init; } = string.Empty;
    public string? DisplayName { get; init; }
    public string OverallStatus { get; init; } = "unknown";
    public List<string> RuleIds { get; } = new();
    public List<string> FailedRuleIds { get; } = new();
    public List<string> PassedRuleIds { get; } = new();
    public Dictionary<string, string> CanonicalStatuses { get; } = new(StringComparer.Ordinal);
    public Dictionary<string, List<string>> CanonicalWarnings { get; } = new(StringComparer.Ordinal);
    public Dictionary<string, string> CanonicalDetails { get; } = new(StringComparer.Ordinal);
}
