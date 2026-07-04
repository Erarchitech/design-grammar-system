using System.Text.Json;
using DG.Core.Models;
using DG.Core.Serialization;
using Neo4j.Driver;

namespace DG.Core.Data;

public sealed class Neo4jValidGraphRepository : IValidGraphRepository
{
    private static readonly TimeSpan QueryTimeout = TimeSpan.FromSeconds(20);

    private const string RunsQuery = """
        MATCH (run:ValidationRun {graph:'ValidGraph', project:$project})
        RETURN
            run.runId AS runId,
            coalesce(run.project, $project) AS project,
            run.createdAt AS createdAt,
            coalesce(run.rulesJson, '[]') AS rulesJson,
            run.statePayloadJson AS statePayloadJson
        ORDER BY run.createdAt DESC, run.runId ASC
        """;

    public async Task<ValidGraphQueryResult> GetRunsAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(
            connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(
            options => options.WithDatabase(connection.Database));

        var cursor = await session
            .RunAsync(RunsQuery, new { project = connection.Project })
            .WaitAsync(QueryTimeout, cancellationToken);

        var rawRuns = new List<(RunInfo, IReadOnlyList<bool>, DesignState?)>();
        await cursor
            .ForEachAsync(record =>
            {
                var runId = record["runId"].As<string?>() ?? string.Empty;
                if (string.IsNullOrWhiteSpace(runId)) return;

                var project = record["project"].As<string?>() ?? connection.Project;
                var createdAt = ParseTimestamp(record["createdAt"].As<string?>());
                var rulesJson = record["rulesJson"].As<string?>() ?? "[]";
                var statePayloadJson = record["statePayloadJson"].As<string?>();

                // Parse rules and status
                var (ruleIds, results) = ParseRulesJson(rulesJson);
                var overallPass = results.All(r => r);

                // Parse design state
                var state = TryParseDesignState(statePayloadJson);
                var objStateCount = state?.ObjStates.Count ?? 0;

                // Build per-ObjState status list
                var statusList = objStateCount > 0
                    ? Enumerable.Repeat(overallPass, objStateCount).ToList()
                    : new List<bool> { overallPass };

                var runInfo = new RunInfo
                {
                    RunId = runId,
                    Project = project,
                    CapturedAtUtc = createdAt,
                    RuleIds = ruleIds,
                    StateId = state?.StateId,
                };

                rawRuns.Add((runInfo, statusList, state));
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        // Build Run/Status (parallel, index-matched)
        var runs = new List<RunInfo>(rawRuns.Count);
        var statuses = new List<IReadOnlyList<bool>>(rawRuns.Count);
        var allStates = new List<DesignState>(rawRuns.Count);

        foreach (var (runInfo, statusList, state) in rawRuns)
        {
            runs.Add(runInfo);
            statuses.Add(statusList);
            if (state is not null) allStates.Add(state);
        }

        // Deduplicate DesignStates by StateId (D-04)
        var distinctStates = new List<DesignState>();
        var seenIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var state in allStates)
        {
            if (seenIds.Add(state.StateId))
            {
                distinctStates.Add(state);
            }
        }

        return new ValidGraphQueryResult
        {
            Runs = runs,
            StatusList = statuses,
            DesignStates = distinctStates,
        };
    }

    internal static string GetRunsQueryForTesting() => RunsQuery;

    internal static DesignState? TryParseDesignState(string? statePayloadJson)
    {
        if (string.IsNullOrWhiteSpace(statePayloadJson)) return null;

        try
        {
            using var doc = JsonDocument.Parse(statePayloadJson);
            var root = doc.RootElement;

            // v2 payload has top-level stateKind or 3-part composition structure
            if (root.TryGetProperty("stateKind", out _) ||
                root.TryGetProperty("objStates", out _) ||
                root.ValueKind == JsonValueKind.Object &&
                root.EnumerateObject().Any(p => p.Name is "objStates" or "paramStates" or "propStates"))
            {
                // v2 payload — deserialize as full DesignState
                var options = new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                };
                return JsonSerializer.Deserialize<DesignState>(statePayloadJson, options);
            }

            // v1 payload — ParamState-only format
            var paramState = DesignStateJsonSerializer.Deserialize(statePayloadJson);
            return new DesignState
            {
                StateId = paramState.StateId,
                CapturedAtUtc = paramState.CapturedAtUtc,
                ParamStates = new List<ParamState> { paramState },
            };
        }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException)
        {
            // Malformed payload — return null rather than crash
            return null;
        }
    }

    internal static (IReadOnlyList<string> ruleIds, IReadOnlyList<bool> results) ParseRulesJson(string? rulesJson)
    {
        if (string.IsNullOrWhiteSpace(rulesJson) || rulesJson == "[]")
        {
            return (Array.Empty<string>(), Array.Empty<bool>());
        }

        try
        {
            using var document = JsonDocument.Parse(rulesJson);
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Array)
            {
                return (Array.Empty<string>(), Array.Empty<bool>());
            }

            var ruleIds = new List<string>();
            var results = new List<bool>();

            foreach (var item in root.EnumerateArray())
            {
                var ruleId = item.TryGetProperty("ruleId", out var rid) ? rid.GetString() : null;
                if (string.IsNullOrWhiteSpace(ruleId))
                {
                    continue;
                }

                ruleIds.Add(ruleId);

                var passed = item.TryGetProperty("passed", out var passedProp) && passedProp.GetBoolean();
                results.Add(passed);
            }

            // Deterministic ordering by ruleId
            var paired = ruleIds
                .Select((id, i) => (id, result: results[i]))
                .OrderBy(p => p.id, StringComparer.Ordinal)
                .ToList();

            return (paired.Select(p => p.id).ToList(), paired.Select(p => p.result).ToList());
        }
        catch (JsonException)
        {
            return (Array.Empty<string>(), Array.Empty<bool>());
        }
    }

    internal static DateTimeOffset ParseTimestamp(string? raw)
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
}
