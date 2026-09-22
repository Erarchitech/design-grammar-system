using System.Text.Json;
using System.Text.Json.Serialization;
using DG.Core.Contracts;
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

    // D-13/Correction 2: RunsQuery above does not select run.evidenceEnvelopeJson at all --
    // this is the first C# projection of that property. The per-object verdict was never
    // missing an index, it was never read into C# in the first place. Scoped by both
    // $project and $runId (and graph:'ValidGraph'), matching the two existing queries'
    // scoping convention -- project isolation itself remains Phase 1205's scope.
    private const string EvidenceQuery = """
        MATCH (run:ValidationRun {graph:'ValidGraph', project:$project, runId:$runId})
        RETURN run.evidenceEnvelopeJson AS evidenceEnvelopeJson
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

                // Parse design state
                var state = TryParseDesignState(statePayloadJson);

                // D-14: the per-run inner list is honestly the per-RULE pass/fail sequence
                // ParseRulesJson already returns -- one boolean per rule evaluated for this
                // run, never a per-object list. The former construction here fabricated a
                // per-object-shaped list from a run-level AND over rules by repeating that
                // single boolean once per ObjState; this is a missing feature, not a mapping
                // bug (Correction 2), and GetPerObjectVerdictsAsync is the canonical
                // per-object read path (D-10).
                var statusList = (IReadOnlyList<bool>)results;

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

    internal static string GetEvidenceQueryForTesting() => EvidenceQuery;

    /// <summary>
    /// Reads a run's canonical per-object verdicts (D-10/D-13). Guards <paramref name="runId"/>
    /// explicitly rather than via <c>ArgumentException.ThrowIfNullOrWhiteSpace</c>, which is
    /// .NET 8+ only -- DG.Core multi-targets net7.0. Wrapped in the same degrade-not-abort
    /// pattern as the standalone-states read (see :112-131 above): an older graph shape, an
    /// unreachable property, or a missing run must yield an envelope-absent result, never an
    /// exception that would surface as a Grasshopper canvas failure.
    /// </summary>
    public async Task<PerObjectVerdictResult> GetPerObjectVerdictsAsync(
        ConnectionInfo connection, string runId, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(runId))
        {
            throw new ArgumentException("Run id must not be null or whitespace.", nameof(runId));
        }

        await using var driver = GraphDatabase.Driver(
            connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(
            options => options.WithDatabase(connection.Database));

        string? evidenceEnvelopeJson = null;

        try
        {
            var cursor = await session
                .RunAsync(EvidenceQuery, new { project = connection.Project, runId })
                .WaitAsync(QueryTimeout, cancellationToken);

            await cursor
                .ForEachAsync(record =>
                {
                    evidenceEnvelopeJson = record["evidenceEnvelopeJson"].As<string?>();
                })
                .WaitAsync(QueryTimeout, cancellationToken);
        }
        catch (Exception)
        {
            // Degrade, don't abort -- an older graph shape or an unreachable property yields
            // an envelope-absent result rather than propagating out of this method.
            evidenceEnvelopeJson = null;
        }

        return BuildPerObjectVerdicts(evidenceEnvelopeJson);
    }

    /// <summary>
    /// Pure deserialization+rollup function (D-13's testing seam, matching the
    /// TryParseDesignState/ParseRulesJson convention): null/whitespace/malformed input all
    /// degrade to an envelope-absent result rather than throwing (D-11).
    ///
    /// Two distinct cases, both explained here per CR-01 (<c>1202-REVIEW.md</c>) so a future
    /// reader does not have to infer either from the body:
    ///
    /// <list type="bullet">
    /// <item><description><b>Cross-rule case (intended, unchanged):</b> one object, several
    /// DISTINCT rules. Rows are grouped by ObjectId (ordinal) and rolled up via
    /// <see cref="StatusRollup.Rollup"/> -- the shipped worst-case-first precedence, never a
    /// locally-ordered or re-implemented one (D-12). Output is sorted by ObjectId ordinal,
    /// matching the envelope's own normative row order.</description></item>
    /// <item><description><b>Duplicate-identity case (detected, reported):</b> two or more rows
    /// share ONE <c>(ruleId, objectId)</c> pair. This is a producer-side contract violation
    /// against <c>spec/EVIDENCE-CONTRACT.md</c> §4's row-identity rule ("never merged, collided,
    /// or deduplicated on value equality alone"). Rather than letting <see cref="StatusRollup.Rollup"/>
    /// silently absorb the duplicate rows into the same worst-case rollup, this method first
    /// groups by the composite <c>(RuleId, ObjectId)</c> identity to detect any pair appearing on
    /// more than one row, and reports the finding via
    /// <see cref="PerObjectVerdict.HasDuplicateRuleObjectRows"/> and
    /// <see cref="PerObjectVerdictResult.CollidingRuleObjectPairs"/>. The affected object's
    /// <see cref="PerObjectVerdict.Status"/> is still the complete D-12 rollup over every
    /// contributing row, duplicates included -- a duplicate is flagged, not degraded and not
    /// thrown, because it is a well-formed envelope and <see cref="GetPerObjectVerdictsAsync"/> is
    /// on the Grasshopper canvas read path (D-11's degrade contract covers malformed input, not
    /// this).</description></item>
    /// </list>
    ///
    /// See <c>spec/EVIDENCE-CONTRACT.md</c> §5.1 for the human-readable contract. Note
    /// <c>tools/de01/report.py</c>'s <c>compare_legs</c> keeps all rows per pair for the same
    /// reason (never deduplicating) -- the two legs now agree on this boundary.
    /// </summary>
    internal static PerObjectVerdictResult BuildPerObjectVerdicts(string? evidenceEnvelopeJson)
    {
        if (string.IsNullOrWhiteSpace(evidenceEnvelopeJson))
        {
            return new PerObjectVerdictResult { EnvelopePresent = false, Verdicts = Array.Empty<PerObjectVerdict>() };
        }

        try
        {
            var envelope = JsonSerializer.Deserialize<EvidenceEnvelope>(evidenceEnvelopeJson);
            if (envelope is null)
            {
                return new PerObjectVerdictResult { EnvelopePresent = false, Verdicts = Array.Empty<PerObjectVerdict>() };
            }

            // Materialize once: both the (RuleId, ObjectId) collision detection below and the
            // ObjectId-level rollup that follows must read from the SAME row sequence, so the
            // duplicate-identity flag and the rolled-up status can never describe different row
            // sets (plan 1202-10 key_links).
            var rows = envelope.Rows.ToList();

            // Step 1: (RuleId, ObjectId) composite identity, ordinal on both components, per
            // spec/EVIDENCE-CONTRACT.md §4. Any pair appearing on more than one row is a
            // producer-side identity collision (CR-01).
            var collidingPairs = rows
                .GroupBy(row => (row.RuleId, row.ObjectId), PairOrdinalComparer.Instance)
                .Where(group => group.Count() > 1)
                .Select(group => new RuleObjectPair(group.Key.RuleId, group.Key.ObjectId))
                .OrderBy(pair => pair.RuleId, StringComparer.Ordinal)
                .ThenBy(pair => pair.ObjectId, StringComparer.Ordinal)
                .ToList();

            var collidingObjectIds = collidingPairs
                .Select(pair => pair.ObjectId)
                .ToHashSet(StringComparer.Ordinal);

            // Step 2: existing ObjectId-level grouping and StatusRollup.Rollup, over EVERY row
            // (duplicates included) -- the rolled-up status must not change as a result of this
            // fix. D-12 forbids a second precedence; StatusRollup.Rollup is called exactly as it
            // is today.
            var verdicts = rows
                .GroupBy(row => row.ObjectId, StringComparer.Ordinal)
                .Select(group => new PerObjectVerdict
                {
                    ObjectId = group.Key,
                    Status = StatusRollup.Rollup(group.Select(row => row.CanonicalStatus)),
                    Source = VerdictSource.EvidenceEnvelope,
                    HasDuplicateRuleObjectRows = collidingObjectIds.Contains(group.Key),
                })
                .OrderBy(v => v.ObjectId, StringComparer.Ordinal)
                .ToList();

            return new PerObjectVerdictResult
            {
                EnvelopePresent = true,
                Verdicts = verdicts,
                CollidingRuleObjectPairs = collidingPairs,
            };
        }
        catch (Exception)
        {
            // Malformed envelope JSON -- degrade rather than throw, mirroring
            // TryParseDesignState's degrade-not-crash posture.
            return new PerObjectVerdictResult { EnvelopePresent = false, Verdicts = Array.Empty<PerObjectVerdict>() };
        }
    }

    /// <summary>
    /// Ordinal equality/hashing over a <c>(string RuleId, string ObjectId)</c> tuple, used by
    /// <see cref="BuildPerObjectVerdicts"/>'s Step 1 grouping (CR-01). The default tuple
    /// <c>EqualityComparer</c> already uses each component's own <see cref="object.Equals(object)"/>
    /// (ordinal for <see cref="string"/>), but this explicit comparer makes the ordinal intent
    /// visible at the call site rather than relying on that implicit default.
    /// </summary>
    private sealed class PairOrdinalComparer : IEqualityComparer<(string RuleId, string ObjectId)>
    {
        public static readonly PairOrdinalComparer Instance = new();

        public bool Equals((string RuleId, string ObjectId) x, (string RuleId, string ObjectId) y) =>
            StringComparer.Ordinal.Equals(x.RuleId, y.RuleId) && StringComparer.Ordinal.Equals(x.ObjectId, y.ObjectId);

        public int GetHashCode((string RuleId, string ObjectId) obj) =>
            HashCode.Combine(
                StringComparer.Ordinal.GetHashCode(obj.RuleId),
                StringComparer.Ordinal.GetHashCode(obj.ObjectId));
    }

    internal static DesignState? TryParseDesignState(string? statePayloadJson)
    {
        if (string.IsNullOrWhiteSpace(statePayloadJson)) return null;

        try
        {
            using var doc = JsonDocument.Parse(statePayloadJson);
            var root = doc.RootElement;

            // D-07 bundled mandatory fix: check the version field explicitly
            // before any structural sniffing. A payload that declares a
            // version other than "2" (e.g. a future v3) must be rejected
            // outright rather than structurally sniffed and partially parsed
            // as v2. A payload with NO version key at all (v1's shape) falls
            // through unchanged to the structural sniff below and, failing
            // that, the v1 fallback -- v1 payloads carry no version key and
            // must keep parsing.
            if (root.ValueKind == JsonValueKind.Object
                && root.TryGetProperty("version", out var versionElement)
                && versionElement.ValueKind == JsonValueKind.String
                && versionElement.GetString() != "2")
            {
                return null;
            }

            // v2 payload has top-level stateKind or 3-part composition structure
            if (root.TryGetProperty("stateKind", out _) ||
                root.TryGetProperty("objStates", out _) ||
                root.ValueKind == JsonValueKind.Object &&
                root.EnumerateObject().Any(p => p.Name is "objStates" or "paramStates" or "propStates"))
            {
                // Declared exclusion (Phase 1202 plan 09, D-09, ALGN12-09): this inline reader is
                // the authoritative reader for accept-candidate-writer (flat numberValue/
                // integerValue/booleanValue shape) parameters[] payloads only. It silently
                // yields null typed values (NumberValue/IntegerValue/BooleanValue) on the
                // DesignStatePayloadV2Serializer's own condensed {type, value} shape, with no
                // exception, because System.Text.Json ignores unmatched properties by default.
                // Converging the two readers is deliberately NOT implemented — see spec/DATABASE.md
                // "Declared exclusion: `parameters[]` has two wire shapes and two readers" for the
                // full contract. Pinned by
                // TryParseDesignState_AndSerializerDeserialize_DivergeOnAcceptCandidateWriterEnvelope
                // and
                // TryParseDesignState_AndSerializerDeserialize_DivergeOnSerializerOwnConciseParameterShape
                // in DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs.
                //
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
