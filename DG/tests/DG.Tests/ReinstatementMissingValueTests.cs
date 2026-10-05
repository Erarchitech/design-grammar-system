using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

// A ParamState read back with a parameter whose typed value is absent (test
// v12-hexagonal-facade-01, finding F25: VALIDATION GRAPH delivered NumberValue = null) used to be
// validated as Applied; PARAMETER REINSTATE then wrote `NumberValue ?? 0.0` into the slider and
// silently produced a variant that never existed. A missing value must block, like the other
// per-parameter failures, so the atomic abort (D-06) keeps the canvas untouched.
public sealed class ReinstatementMissingValueTests
{
    private static ParamState Snapshot(params DesignStateParameter[] parameters)
    {
        var state = new ParamState { StateId = "DS_TEST" };
        foreach (var p in parameters)
            state.Parameters.Add(p);
        return state;
    }

    [Theory]
    [InlineData(DesignStateParameterType.Number)]
    [InlineData(DesignStateParameterType.Integer)]
    [InlineData(DesignStateParameterType.Boolean)]
    public void ParameterWithoutItsTypedValue_IsBlockedAndAbortsTheReinstate(DesignStateParameterType type)
    {
        var snapshot = Snapshot(
            new DesignStateParameter { ParameterId = "width", DisplayName = "width", Type = DesignStateParameterType.Number, NumberValue = 4400 },
            new DesignStateParameter { ParameterId = "empty", DisplayName = "empty", Type = type });
        var targets = new[]
        {
            new ResolvedTarget("width", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 1000, 12000),
            new ResolvedTarget("empty", TargetResolutionStatus.Resolved, type, null, null),
        };

        var result = new DesignStateReinstatementService().Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        var report = Assert.Single(result.Reports, r => r.ParameterId == "empty");
        Assert.Equal(ReinstatementStatus.MissingValue, report.Status);
    }

    [Fact]
    public void MissingValueMessage_TellsTheUserToRecaptureTheState()
    {
        var message = ErrorMessageTemplates.ReinstatementBlocked("width", ReinstatementStatus.MissingValue, "has no recorded value");

        Assert.Contains("width", message);
        Assert.Contains("Recapture the Design State", message);
    }
}
