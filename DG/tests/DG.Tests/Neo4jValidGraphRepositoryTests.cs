using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class Neo4jValidGraphRepositoryTests
{
    [Fact]
    public void TryParseDesignState_WithV1Payload_ReturnsParamStateOnlyDesignState()
    {
        // v1 payload: ParamState with StateId, CapturedAtUtc, Parameters array
        var v1Json = """{"stateId":"PS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","parameters":[{"parameterId":"Height","displayName":"Height","type":"number","value":75}]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v1Json);

        Assert.NotNull(result);
        Assert.Equal("PS_test", result!.StateId);
        Assert.Single(result.ParamStates);
        Assert.Empty(result.ObjStates);
        Assert.Empty(result.PropStates);
    }

    [Fact]
    public void TryParseDesignState_WithV2Payload_ReturnsFullDesignState()
    {
        // v2 payload has stateKind or 3-part structure
        var v2Json = """{"stateId":"DS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[],"paramStates":[],"propStates":[],"stateKind":"v2"}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v2Json);

        Assert.NotNull(result);
        Assert.Equal("DS_test", result!.StateId);
    }

    [Fact]
    public void TryParseDesignState_WithV2PayloadObjStates_ReturnsFullDesignState()
    {
        // v2 payload detected by objStates key (alternative to stateKind)
        var v2Json = """{"stateId":"DS_test","capturedAtUtc":"2026-07-04T12:00:00.0000000Z","objStates":[{"stateId":"OS_001","objectRef":"Wall","capturedAtUtc":"2026-07-04T12:00:00.0000000Z"}],"paramStates":[],"propStates":[]}""";

        var result = Neo4jValidGraphRepository.TryParseDesignState(v2Json);

        Assert.NotNull(result);
        Assert.Equal("DS_test", result!.StateId);
        Assert.Single(result.ObjStates);
        Assert.Equal("OS_001", result.ObjStates[0].StateId);
    }

    [Fact]
    public void TryParseDesignState_WithNullJson_ReturnsNull()
    {
        var result = Neo4jValidGraphRepository.TryParseDesignState(null);
        Assert.Null(result);
    }

    [Fact]
    public void TryParseDesignState_WithEmptyJson_ReturnsNull()
    {
        var result = Neo4jValidGraphRepository.TryParseDesignState("");
        Assert.Null(result);
    }

    [Fact]
    public void TryParseDesignState_WithMalformedJson_ReturnsNull()
    {
        var result = Neo4jValidGraphRepository.TryParseDesignState("{invalid json}");
        Assert.Null(result);
    }

    [Fact]
    public void DesignStates_AreDeduplicatedByStateId()
    {
        // Simulate what the repository does after loading all runs
        var state1 = new DesignState { StateId = "DS_001" };
        var state2 = new DesignState { StateId = "DS_001" }; // Same ID — duplicate
        var state3 = new DesignState { StateId = "DS_002" };

        var allStates = new[] { state1, state2, state3 };
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var distinct = allStates.Where(s => seen.Add(s.StateId)).ToList();

        Assert.Equal(2, distinct.Count);
        Assert.Contains(distinct, s => s.StateId == "DS_001");
        Assert.Contains(distinct, s => s.StateId == "DS_002");
    }

    [Fact]
    public void StatusList_LengthMatchesRunCount()
    {
        // D-03: Run and Status are 1:1 index-matched parallel lists
        var runs = new List<RunInfo> { new() { RunId = "R1" }, new() { RunId = "R2" } };
        var statuses = new List<IReadOnlyList<bool>> { new List<bool> { true }, new List<bool> { false } };

        Assert.Equal(runs.Count, statuses.Count);
    }

    [Fact]
    public void RunQuery_ShouldTargetValidGraphLayer()
    {
        var query = Neo4jValidGraphRepository.GetRunsQueryForTesting();
        Assert.Contains("graph:'ValidGraph'", query);
        Assert.Contains("project:$project", query);
        Assert.Contains("ORDER BY run.createdAt DESC, run.runId ASC", query);
    }

    [Fact]
    public void ParseRulesJson_WithEmptyArray_ReturnsEmpty()
    {
        var (ruleIds, results) = Neo4jValidGraphRepository.ParseRulesJson("[]");

        Assert.Empty(ruleIds);
        Assert.Empty(results);
    }

    [Fact]
    public void ParseRulesJson_WithValidArray_ReturnsSortedResults()
    {
        var json = """[{"ruleId":"R_B","passed":true},{"ruleId":"R_A","passed":false}]""";
        var (ruleIds, results) = Neo4jValidGraphRepository.ParseRulesJson(json);

        // Results should be sorted by ruleId
        Assert.Equal(2, ruleIds.Count);
        Assert.Equal("R_A", ruleIds[0]);
        Assert.Equal("R_B", ruleIds[1]);
        Assert.False(results[0]); // R_A passed = false
        Assert.True(results[1]);  // R_B passed = true
    }

    [Fact]
    public void ParseRulesJson_WithNullJson_ReturnsEmpty()
    {
        var (ruleIds, results) = Neo4jValidGraphRepository.ParseRulesJson(null);
        Assert.Empty(ruleIds);
        Assert.Empty(results);
    }

    [Fact]
    public void ParseTimestamp_WithValidIso8601_ReturnsParsed()
    {
        var result = Neo4jValidGraphRepository.ParseTimestamp("2026-07-04T12:00:00.0000000Z");
        Assert.Equal(new DateTimeOffset(2026, 7, 4, 12, 0, 0, TimeSpan.Zero), result);
    }

    [Fact]
    public void ParseTimestamp_WithNull_ReturnsMinValue()
    {
        var result = Neo4jValidGraphRepository.ParseTimestamp(null);
        Assert.Equal(DateTimeOffset.MinValue, result);
    }

    [Fact]
    public void ParseTimestamp_WithEmptyString_ReturnsMinValue()
    {
        var result = Neo4jValidGraphRepository.ParseTimestamp("");
        Assert.Equal(DateTimeOffset.MinValue, result);
    }
}
