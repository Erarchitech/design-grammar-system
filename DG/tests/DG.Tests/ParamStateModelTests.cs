using DG.Core.Models;

namespace DG.Tests;

public sealed class ParamStateModelTests
{
    [Fact]
    public void ParamState_ShouldSetProperties_ThroughInitOnlySetters()
    {
        var now = DateTimeOffset.UtcNow;
        var paramState = new ParamState
        {
            StateId = "PS_test456",
            CapturedAtUtc = now,
        };

        Assert.Equal("PS_test456", paramState.StateId);
        Assert.Equal(now, paramState.CapturedAtUtc);
    }

    [Fact]
    public void ParamState_ShouldHaveEmptyStateIdByDefault()
    {
        var paramState = new ParamState();

        Assert.Equal("", paramState.StateId);
    }

    [Fact]
    public void ParamState_ShouldAcceptParameters()
    {
        var paramState = new ParamState
        {
            StateId = "PS_params",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "Height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        });

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "Floors",
            DisplayName = "Floors",
            Type = DesignStateParameterType.Integer,
            IntegerValue = 12,
        });

        Assert.Equal(2, paramState.Parameters.Count);
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "Height");
        Assert.Contains(paramState.Parameters, p => p.ParameterId == "Floors");
    }

    [Fact]
    public void ParamState_ShouldPreserveDesignStateSnapshotContract()
    {
        // ParamState replaces DesignStateSnapshot with identical field set:
        // StateId (string), CapturedAtUtc (DateTimeOffset), Parameters (Collection<DesignStateParameter>)
        var paramState = new ParamState
        {
            StateId = "contract-test",
            CapturedAtUtc = DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"),
        };

        paramState.Parameters.Add(new DesignStateParameter
        {
            ParameterId = "width",
            DisplayName = "Width",
            Type = DesignStateParameterType.Number,
            NumberValue = 42.0,
        });

        // Verify all three original fields are present
        Assert.Equal("contract-test", paramState.StateId);
        Assert.Equal(DateTimeOffset.Parse("2026-04-30T10:00:00.0000000Z"), paramState.CapturedAtUtc);
        Assert.Single(paramState.Parameters);
    }

    [Fact]
    public void ParamState_ShouldHaveEmptyParametersByDefault()
    {
        var paramState = new ParamState
        {
            StateId = "PS_empty",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        Assert.Empty(paramState.Parameters);
    }
}
