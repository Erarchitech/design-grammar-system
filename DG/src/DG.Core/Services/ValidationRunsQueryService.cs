using DG.Core.Models;
using DG.Core.Serialization;
using Neo4j.Driver;

namespace DG.Core.Services;

/// <summary>
/// Queries ValidationRun nodes from Neo4j with optional rule and state filters.
/// Produces a deterministic output schema for downstream reinstatement and UI grouping.
/// </summary>
public sealed class ValidationRunsQueryService
{
    private static readonly TimeSpan QueryTimeout = TimeSpan.FromSeconds(20);

    private const string ValidationGraph = "ValidationGraph";

    private const string RunsQuery = """
        MATCH (run:ValidationRun {graph:$graph, project:$project})
        WHERE $ruleId IS NULL OR run.rulesJson CONTAINS $ruleId
        RETURN
            run.runId AS runId,
            coalesce(run.project, $project) AS project,
            run.createdAt AS createdAt,
            coalesce(run.rulesJson, '[]') AS rulesJson,
            run.statePayloadJson AS statePayloadJson
        ORDER BY run.createdAt DESC, run.runId ASC
        """;

    /// <summary>
    /// Returns all validation runs for the specified project, optionally filtered by rule ID or state ID.
    /// </summary>
    /// <param name="connection">Active Neo4j connection.</param>
    /// <param name="ruleId">Optional Rule_Id to filter runs. Only runs referencing this rule are returned.</param>
    /// <param name="stateId">Optional StateId to filter runs. Only runs whose attached state has this StateId are returned.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>Ordered, deterministic list of query results.</returns>
    public async Task<IReadOnlyList<ValidationRunQueryResult>> QueryAsync(
        ConnectionInfo connection,
        string? ruleId = null,
        string? stateId = null,
        CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(
            connection.Uri,
            AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));

        var rawResults = await LoadRunsAsync(session, connection.Project, ruleId, cancellationToken);

        var results = new List<ValidationRunQueryResult>(rawResults.Count);
        foreach (var raw in rawResults)
        {
            var result = BuildResult(raw);
            if (result is null)
            {
                continue;
            }

            // Apply state filter when requested.
            if (!string.IsNullOrWhiteSpace(stateId))
            {
                if (result.State is null || !string.Equals(result.State.StateId, stateId, StringComparison.Ordinal))
                {
                    continue;
                }
            }

            results.Add(result);
        }

        return results;
    }

    private static async Task<IReadOnlyList<RawRunRow>> LoadRunsAsync(
        IAsyncSession session,
        string project,
        string? ruleId,
        CancellationToken cancellationToken)
    {
        var cursor = await session
            .RunAsync(RunsQuery, new { graph = ValidationGraph, project, ruleId = (object?)ruleId })
            .WaitAsync(QueryTimeout, cancellationToken);

        var rows = new List<RawRunRow>();
        await cursor
            .ForEachAsync(record =>
            {
                rows.Add(new RawRunRow(
                    RunId: record["runId"].As<string?>() ?? string.Empty,
                    Project: record["project"].As<string?>() ?? project,
                    CreatedAt: record["createdAt"].As<string?>(),
                    RulesJson: record["rulesJson"].As<string?>() ?? "[]",
                    StatePayloadJson: record["statePayloadJson"].As<string?>()));
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        return rows;
    }

    private static ValidationRunQueryResult? BuildResult(RawRunRow raw)
    {
        if (string.IsNullOrWhiteSpace(raw.RunId))
        {
            return null;
        }

        var capturedAt = ParseTimestamp(raw.CreatedAt);
        var (ruleIds, results) = ParseRulesJson(raw.RulesJson);
        var (state, statePayloadJson) = ParseState(raw.StatePayloadJson);

        return new ValidationRunQueryResult
        {
            RunId = raw.RunId,
            Project = raw.Project,
            CapturedAtUtc = capturedAt,
            RuleIds = ruleIds,
            Results = results,
            State = state,
            StatePayloadJson = statePayloadJson,
        };
    }

    private static DateTimeOffset ParseTimestamp(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return DateTimeOffset.MinValue;
        }

        return DateTimeOffset.TryParse(
            raw,
            System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.RoundtripKind,
            out var parsed)
            ? parsed.ToUniversalTime()
            : DateTimeOffset.MinValue;
    }

    private static (IReadOnlyList<string> ruleIds, IReadOnlyList<string> results) ParseRulesJson(string rulesJson)
    {
        if (string.IsNullOrWhiteSpace(rulesJson) || rulesJson == "[]")
        {
            return (Array.Empty<string>(), Array.Empty<string>());
        }

        try
        {
            using var document = System.Text.Json.JsonDocument.Parse(rulesJson);
            var root = document.RootElement;
            if (root.ValueKind != System.Text.Json.JsonValueKind.Array)
            {
                return (Array.Empty<string>(), Array.Empty<string>());
            }

            var ruleIds = new List<string>();
            var results = new List<string>();

            foreach (var item in root.EnumerateArray())
            {
                var ruleId = item.TryGetProperty("ruleId", out var rid) ? rid.GetString() : null;
                if (string.IsNullOrWhiteSpace(ruleId))
                {
                    continue;
                }

                ruleIds.Add(ruleId);

                var passed = item.TryGetProperty("passed", out var passedProp) && passedProp.GetBoolean();
                results.Add($"{ruleId}:{(passed ? "true" : "false")}");
            }

            // Deterministic ordering by ruleId.
            var sortedRuleIds = ruleIds.OrderBy(id => id, StringComparer.Ordinal).ToList();
            var sortedResults = results.OrderBy(r => r, StringComparer.Ordinal).ToList();

            return (sortedRuleIds, sortedResults);
        }
        catch (System.Text.Json.JsonException)
        {
            return (Array.Empty<string>(), Array.Empty<string>());
        }
    }

    private static (DesignStateSnapshot? state, string? statePayloadJson) ParseState(string? statePayloadJson)
    {
        if (string.IsNullOrWhiteSpace(statePayloadJson))
        {
            return (null, null);
        }

        try
        {
            var snapshot = DesignStateJsonSerializer.Deserialize(statePayloadJson);
            return (snapshot, statePayloadJson);
        }
        catch (InvalidOperationException)
        {
            // Malformed state payload — surface null, don't crash.
            return (null, statePayloadJson);
        }
    }

    private sealed record RawRunRow(
        string RunId,
        string Project,
        string? CreatedAt,
        string RulesJson,
        string? StatePayloadJson);
}
