using System.Text.Json;
using System.Text.Json.Serialization;
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

    // Additive second read (Phase 38 plan 38-05, spec/DATABASE.md "Reading
    // standalone ParamStates" / finding F1): RunsQuery above matches only
    // (:ValidationRun) nodes, so a standalone, Run-less :DesignState written
    // by POST /computgraph/candidates/accept is otherwise invisible to the
    // VALIDATION GRAPH component. $project is the only bound parameter,
    // matching RunsQuery's own parameterization.
    private const string StandaloneStatesQuery = """
        MATCH (ds:DesignState {graph:'ValidGraph', project:$project, kind:'ParamState'})
        WHERE ds.statePayloadJson IS NOT NULL
        RETURN
            ds.StateId AS stateId,
            ds.statePayloadJson AS statePayloadJson,
            ds.acceptedAt AS acceptedAt
        ORDER BY ds.acceptedAt DESC, ds.StateId ASC
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

        // Additive second read on the SAME session, after the runs cursor is
        // fully consumed: standalone accepted ParamState DesignStates that
        // have no linked Run (Phase 38 plan 38-05, D-18/finding F1). Runs and
        // StatusList above are built from rawRuns ONLY and are untouched by
        // this block -- a standalone state has no run and contributes to
        // DesignStates alone. Wrapped so a failure (an older graph without
        // this shape, a missing property) degrades to the run-derived states
        // collected above rather than aborting the whole read (T-38-21): the
        // VALIDATION GRAPH component worked before this feature and must keep
        // working when this query cannot run.
        try
        {
            var standaloneCursor = await session
                .RunAsync(StandaloneStatesQuery, new { project = connection.Project })
                .WaitAsync(QueryTimeout, cancellationToken);

            await standaloneCursor
                .ForEachAsync(record =>
                {
                    var statePayloadJson = record["statePayloadJson"].As<string?>();
                    var state = TryParseDesignState(statePayloadJson);
                    if (state is not null) allStates.Add(state);
                })
                .WaitAsync(QueryTimeout, cancellationToken);
        }
        catch (Exception)
        {
            // Degrade, don't abort -- allStates already holds every
            // run-derived state collected above.
        }

        // Deduplicate DesignStates by StateId (D-04) -- standalone states
        // pass through the same seenIds filter as run-derived ones.
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

    internal static string GetStandaloneStatesQueryForTesting() => StandaloneStatesQuery;

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
                // v2 payload — deserialize as full DesignState. Two fixes
                // here (Rule 1, Phase 38 plan 38-05 Task 3), both required
                // for a ParamState carrying real parameters to round-trip
                // through this path at all:
                //   1. A JsonStringEnumConverter: DesignStateParameter.Type
                //      is a C# enum, and System.Text.Json's default enum
                //      handling only accepts an integer, never the
                //      lowercase string ("number"/"integer"/"boolean") a
                //      writer emits.
                //   2. A manual per-ParamState backfill of Parameters (see
                //      below): ParamState.Parameters is exposed via a
                //      getter-only Collection<T> (by design, so callers
                //      cannot replace the instance). System.Text.Json's
                //      default handling for a getter-only collection member
                //      SILENTLY SKIPS populating it instead of throwing --
                //      `JsonObjectCreationHandling.Populate` would fix this
                //      in one line, but that API is .NET 8+ only and
                //      DG.Core multi-targets net7.0 (the actual Grasshopper
                //      plugin runtime), so it is deliberately not used here.
                // Without both, this whole method silently returns a
                // DesignState with empty ParamStates[].Parameters, defeating
                // the very round-trip this plan exists to make reachable.
                var options = new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                    Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) },
                };
                var designState = JsonSerializer.Deserialize<DesignState>(statePayloadJson, options);
                if (designState is not null
                    && root.TryGetProperty("paramStates", out var paramStatesElement)
                    && paramStatesElement.ValueKind == JsonValueKind.Array)
                {
                    var rawParamStates = paramStatesElement.EnumerateArray().ToList();
                    for (var i = 0; i < designState.ParamStates.Count && i < rawParamStates.Count; i++)
                    {
                        if (!rawParamStates[i].TryGetProperty("parameters", out var parametersElement)
                            || parametersElement.ValueKind != JsonValueKind.Array)
                        {
                            continue;
                        }

                        foreach (var parameterElement in parametersElement.EnumerateArray())
                        {
                            var parameter = JsonSerializer.Deserialize<DesignStateParameter>(
                                parameterElement.GetRawText(), options);
                            if (parameter is not null)
                            {
                                designState.ParamStates[i].Parameters.Add(parameter);
                            }
                        }
                    }
                }

                return designState;
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
        catch (Exception)
        {
            // Malformed payload — return null rather than crash. Broadened
            // (WR-03) from `JsonException or InvalidOperationException`:
            // this try block also wraps the v1 fallback
            // (DesignStateJsonSerializer.Deserialize), and a malformed but
            // non-JSON-invalid v1 payload throwing any other exception type
            // must not propagate out of TryParseDesignState into
            // GetRunsAsync's ForEachAsync callback, where it would fail the
            // entire response for every run, not just the one bad payload.
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
