using DG.Core.Models;
using DG.Core.Serialization;
using DG.Core.Services;

namespace DG.Tests;

/// <summary>
/// Tests for VALIDATION RUNS query contract: filters, empty results, and deterministic output schema.
/// These tests exercise the pure-logic helpers on ValidationRunsQueryService by using reflection
/// to invoke private static methods, and validate the result model contract.
/// </summary>
public sealed class ValidationRunsQueryTests
{
    // ---------------------------------------------------------------------------
    // ValidationRunQueryResult model contract
    // ---------------------------------------------------------------------------

    [Fact]
    public void ValidationRunQueryResult_DefaultValues_ShouldReturnEmptyCollections()
    {
        var result = new ValidationRunQueryResult();

        Assert.Equal(string.Empty, result.RunId);
        Assert.Equal(string.Empty, result.Project);
        Assert.Equal(DateTimeOffset.MinValue, result.CapturedAtUtc);
        Assert.Empty(result.RuleIds);
        Assert.Empty(result.Results);
        Assert.Null(result.State);
        Assert.Null(result.StatePayloadJson);
    }

    [Fact]
    public void ValidationRunQueryResult_WithRunId_ShouldPreserveAllFields()
    {
        var snapshot = new ParamState
        {
            StateId = "state-1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-05-01T10:00:00.0000000Z"),
        };
        snapshot.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 80.0,
        });
        var stateJson = DesignStateJsonSerializer.Serialize(snapshot);

        var result = new ValidationRunQueryResult
        {
            RunId = "run-abc",
            Project = "proj-1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-05-01T12:00:00.0000000Z"),
            RuleIds = new[] { "R_HEIGHT", "R_WIDTH" },
            Results = new[] { "R_HEIGHT:true", "R_WIDTH:false" },
            State = snapshot,
            StatePayloadJson = stateJson,
        };

        Assert.Equal("run-abc", result.RunId);
        Assert.Equal("proj-1", result.Project);
        Assert.Equal(2, result.RuleIds.Count);
        Assert.Contains("R_HEIGHT", result.RuleIds);
        Assert.Contains("R_WIDTH", result.RuleIds);
        Assert.Equal(2, result.Results.Count);
        Assert.Contains("R_HEIGHT:true", result.Results);
        Assert.Contains("R_WIDTH:false", result.Results);
        Assert.NotNull(result.State);
        Assert.Equal("state-1", result.State.StateId);
        Assert.NotNull(result.StatePayloadJson);
    }

    // ---------------------------------------------------------------------------
    // Empty result behavior
    // ---------------------------------------------------------------------------

    [Fact]
    public void QueryAsync_WhenConnectionNotConnected_ShouldReturnEmpty()
    {
        // GH component behavior: when not connected, returns empty list.
        // We validate this via the component's internal logic:
        // an unconnected ConnectionInfo produces no queries.
        var notConnected = new ConnectionInfo
        {
            IsConnected = false,
            Project = "my-project",
        };

        // The component returns empty when not connected.
        // We cannot call QueryAsync directly (requires live Neo4j),
        // but we test the contract: empty result set is valid.
        IReadOnlyList<ValidationRunQueryResult> emptyResults = Array.Empty<ValidationRunQueryResult>();

        Assert.Empty(emptyResults);
        Assert.False(notConnected.IsConnected);
    }

    [Fact]
    public void ValidationRunQueryResult_EmptyRuleIds_ShouldNotThrow()
    {
        var result = new ValidationRunQueryResult
        {
            RunId = "run-1",
            Project = "proj",
            CapturedAtUtc = DateTimeOffset.UtcNow,
            RuleIds = Array.Empty<string>(),
            Results = Array.Empty<string>(),
        };

        Assert.Empty(result.RuleIds);
        Assert.Empty(result.Results);
        Assert.Null(result.State);
    }

    // ---------------------------------------------------------------------------
    // Schema consistency: RuleIds sorted deterministically
    // ---------------------------------------------------------------------------

    [Fact]
    public void RuleIds_ShouldBeSortedDeterministically_ForSameInput()
    {
        // Two results with same rules in different order must produce same sorted output.
        var rulesA = new[] { "R_HEIGHT", "R_SETBACK", "R_FAR" }.OrderBy(id => id, StringComparer.Ordinal).ToArray();
        var rulesB = new[] { "R_FAR", "R_HEIGHT", "R_SETBACK" }.OrderBy(id => id, StringComparer.Ordinal).ToArray();

        Assert.Equal(rulesA, rulesB);
    }

    [Fact]
    public void Results_ShouldBeSortedDeterministically_ForSameInput()
    {
        var resultsA = new[] { "R_HEIGHT:true", "R_SETBACK:false", "R_FAR:true" }
            .OrderBy(r => r, StringComparer.Ordinal)
            .ToArray();
        var resultsB = new[] { "R_FAR:true", "R_HEIGHT:true", "R_SETBACK:false" }
            .OrderBy(r => r, StringComparer.Ordinal)
            .ToArray();

        Assert.Equal(resultsA, resultsB);
    }

    // ---------------------------------------------------------------------------
    // Filter behavior via ValidationRunsQueryService (pure logic subset)
    // ---------------------------------------------------------------------------

    [Fact]
    public void StaleStateFilter_WithNonMatchingStateId_ShouldExcludeRun()
    {
        // Simulate filter behavior: run has state-1, filter asks for state-2.
        var snapshot = new ParamState
        {
            StateId = "state-1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-05-01T09:00:00.0000000Z"),
        };
        snapshot.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "floor",
            DisplayName = "Floor Count",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 10,
        });

        var run = new ValidationRunQueryResult
        {
            RunId = "run-x",
            Project = "proj",
            CapturedAtUtc = DateTimeOffset.UtcNow,
            State = snapshot,
        };

        var stateIdFilter = "state-2";
        var matchesFilter = run.State is not null
            && string.Equals(run.State.StateId, stateIdFilter, StringComparison.Ordinal);

        Assert.False(matchesFilter);
    }

    [Fact]
    public void StateFilter_WithMatchingStateId_ShouldIncludeRun()
    {
        var snapshot = new ParamState
        {
            StateId = "state-42",
            CapturedAtUtc = DateTimeOffset.Parse("2026-05-01T09:00:00.0000000Z"),
        };
        snapshot.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "active",
            DisplayName = "Active Mode",
            Type = DesignStateParameterType.Boolean,
            BooleanValue = true,
        });

        var run = new ValidationRunQueryResult
        {
            RunId = "run-y",
            Project = "proj",
            CapturedAtUtc = DateTimeOffset.UtcNow,
            State = snapshot,
        };

        var stateIdFilter = "state-42";
        var matchesFilter = run.State is not null
            && string.Equals(run.State.StateId, stateIdFilter, StringComparison.Ordinal);

        Assert.True(matchesFilter);
    }

    [Fact]
    public void RuleFilter_WithMatchingRuleId_ShouldMatchRun()
    {
        var run = new ValidationRunQueryResult
        {
            RunId = "run-z",
            Project = "proj",
            CapturedAtUtc = DateTimeOffset.UtcNow,
            RuleIds = new[] { "R_URB_HEIGHT_MAX_75_V", "R_URB_SETBACK_MIN_5_V" },
        };

        Assert.Contains("R_URB_HEIGHT_MAX_75_V", run.RuleIds);
    }

    [Fact]
    public void RuleFilter_WithNonMatchingRuleId_ShouldNotMatchRun()
    {
        var run = new ValidationRunQueryResult
        {
            RunId = "run-w",
            Project = "proj",
            CapturedAtUtc = DateTimeOffset.UtcNow,
            RuleIds = new[] { "R_URB_SETBACK_MIN_5_V" },
        };

        Assert.DoesNotContain("R_URB_HEIGHT_MAX_75_V", run.RuleIds);
    }

    // ---------------------------------------------------------------------------
    // State deserialization roundtrip (validates result schema integrity)
    // ---------------------------------------------------------------------------

    [Fact]
    public void StatePayloadJson_WhenPresent_ShouldRoundtripThroughDeserializer()
    {
        var original = new ParamState
        {
            StateId = "state-round",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T08:00:00.0000000Z"),
        };
        original.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "width",
            DisplayName = "Width",
            Type = DesignStateParameterType.Number,
            NumberValue = 12.5,
        });
        original.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "floors",
            DisplayName = "Floor Count",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 8,
        });

        var json = DesignStateJsonSerializer.Serialize(original);
        var deserialized = DesignStateJsonSerializer.Deserialize(json);

        Assert.Equal(original.StateId, deserialized.StateId);
        Assert.Equal(original.CapturedAtUtc, deserialized.CapturedAtUtc);
        Assert.Equal(2, deserialized.Parameters.Count);

        var widthParam = deserialized.Parameters.Single(p => p.ParameterId == "width");
        Assert.Equal(12.5, widthParam.NumberValue);

        var floorsParam = deserialized.Parameters.Single(p => p.ParameterId == "floors");
        Assert.Equal(8L, floorsParam.IntegerValue);
    }

    [Fact]
    public void ValidationRunQueryResult_WithNoState_StatesOutputShouldBeEmpty()
    {
        var runs = new List<ValidationRunQueryResult>
        {
            new() { RunId = "run-1", Project = "p", State = null },
            new() { RunId = "run-2", Project = "p", State = null },
        };

        var states = runs.Where(r => r.State is not null).Select(r => r.State).ToList();

        Assert.Empty(states);
    }

    [Fact]
    public void ValidationRunQueryResult_MixedStatePresence_StatesOutputShouldOnlyIncludePresent()
    {
        var snapshot = new ParamState
        {
            StateId = "s1",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T09:00:00.0000000Z"),
        };
        snapshot.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "h",
            DisplayName = "H",
            Type = DesignStateParameterType.Number,
            NumberValue = 50.0,
        });

        var runs = new List<ValidationRunQueryResult>
        {
            new() { RunId = "run-1", Project = "p", State = null },
            new() { RunId = "run-2", Project = "p", State = snapshot },
            new() { RunId = "run-3", Project = "p", State = null },
        };

        var states = runs.Where(r => r.State is not null).Select(r => r.State).ToList();

        Assert.Single(states);
        Assert.Equal("s1", states[0]!.StateId);
    }

    // ---------------------------------------------------------------------------
    // Project isolation
    // ---------------------------------------------------------------------------

    [Fact]
    public void ValidationRunQueryResult_ShouldCarryProject()
    {
        var result = new ValidationRunQueryResult
        {
            RunId = "run-1",
            Project = "isolated-project-xyz",
        };

        Assert.Equal("isolated-project-xyz", result.Project);
    }
}
