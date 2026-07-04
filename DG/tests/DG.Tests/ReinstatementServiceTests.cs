using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class ReinstatementServiceTests
{
    private readonly DesignStateReinstatementService _sut = new();

    [Fact]
    public void Validate_AllParametersValid_ShouldReturnApplied()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 50.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 });

        var targets = new[]
        {
            MakeTarget("height", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
            MakeTarget("floors", TargetResolutionStatus.Resolved, DesignStateParameterType.Integer, 1, 50),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.True(result.Applied);
        Assert.False(result.Aborted);
        Assert.Equal(2, result.AppliedCount);
        Assert.Equal(0, result.BlockedCount);
        Assert.Equal(0, result.UnchangedCount);
        Assert.All(result.Reports, r => Assert.Equal(ReinstatementStatus.Applied, r.Status));
    }

    [Fact]
    public void Validate_MissingTarget_ShouldAbortWithWouldApply()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 50.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 });

        var targets = new[]
        {
            MakeTarget("height", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
            MakeTarget("floors", TargetResolutionStatus.Missing, DesignStateParameterType.Integer),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        var heightReport = result.Reports.Single(r => r.ParameterId == "height");
        var floorsReport = result.Reports.Single(r => r.ParameterId == "floors");
        Assert.Equal(ReinstatementStatus.WouldApply, heightReport.Status);
        Assert.Equal(ReinstatementStatus.MissingTarget, floorsReport.Status);
    }

    [Fact]
    public void Validate_TypeMismatch_ShouldAbortWithWouldApply()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 50.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 });

        var targets = new[]
        {
            MakeTarget("height", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
            // Wrong type: Integer parameter but Number target
            MakeTarget("floors", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        var heightReport = result.Reports.Single(r => r.ParameterId == "height");
        var floorsReport = result.Reports.Single(r => r.ParameterId == "floors");
        Assert.Equal(ReinstatementStatus.WouldApply, heightReport.Status);
        Assert.Equal(ReinstatementStatus.TypeMismatch, floorsReport.Status);
    }

    [Fact]
    public void Validate_AmbiguousTarget_ShouldAbortWithWouldApply()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 50.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 });

        var targets = new[]
        {
            MakeTarget("height", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
            MakeTarget("floors", TargetResolutionStatus.Ambiguous, DesignStateParameterType.Integer),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        var heightReport = result.Reports.Single(r => r.ParameterId == "height");
        var floorsReport = result.Reports.Single(r => r.ParameterId == "floors");
        Assert.Equal(ReinstatementStatus.WouldApply, heightReport.Status);
        Assert.Equal(ReinstatementStatus.AmbiguousTarget, floorsReport.Status);
    }

    [Fact]
    public void Validate_OutOfRange_ShouldAbortWithWouldApply()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 95.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 });

        var targets = new[]
        {
            // Domain max is 75 but value is 95
            MakeTarget("height", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 75),
            MakeTarget("floors", TargetResolutionStatus.Resolved, DesignStateParameterType.Integer, 1, 50),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        var heightReport = result.Reports.Single(r => r.ParameterId == "height");
        var floorsReport = result.Reports.Single(r => r.ParameterId == "floors");
        Assert.Equal(ReinstatementStatus.OutOfRange, heightReport.Status);
        Assert.Equal(ReinstatementStatus.WouldApply, floorsReport.Status);
    }

    [Fact]
    public void Validate_StateIdGuard_ShouldReturnAllUnchanged()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 50.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 });

        var targets = new[]
        {
            MakeTarget("height", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
            MakeTarget("floors", TargetResolutionStatus.Resolved, DesignStateParameterType.Integer, 1, 50),
        };

        // Pass the same StateId as lastAppliedStateId
        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: snapshot.StateId);

        Assert.False(result.Applied);
        Assert.False(result.Aborted);
        Assert.Equal(0, result.AppliedCount);
        Assert.Equal(0, result.BlockedCount);
        Assert.Equal(2, result.UnchangedCount);
        Assert.All(result.Reports, r => Assert.Equal(ReinstatementStatus.Unchanged, r.Status));
    }

    [Fact]
    public void Validate_MultipleFailures_ShouldReportEachIndividually()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "height", DisplayName = "Height", Type = DesignStateParameterType.Number, NumberValue = 50.0 },
            new DesignStateParameter { ParameterId = "floors", DisplayName = "Floors", Type = DesignStateParameterType.Integer, IntegerValue = 10 },
            new DesignStateParameter { ParameterId = "hasPodium", DisplayName = "Has Podium", Type = DesignStateParameterType.Boolean, BooleanValue = true });

        var targets = new[]
        {
            MakeTarget("height", TargetResolutionStatus.Missing, DesignStateParameterType.Number),
            // Type mismatch: Integer param matched to Boolean target
            MakeTarget("floors", TargetResolutionStatus.Resolved, DesignStateParameterType.Boolean),
            MakeTarget("hasPodium", TargetResolutionStatus.Resolved, DesignStateParameterType.Boolean),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        var heightReport = result.Reports.Single(r => r.ParameterId == "height");
        var floorsReport = result.Reports.Single(r => r.ParameterId == "floors");
        var podiumReport = result.Reports.Single(r => r.ParameterId == "hasPodium");
        Assert.Equal(ReinstatementStatus.MissingTarget, heightReport.Status);
        Assert.Equal(ReinstatementStatus.TypeMismatch, floorsReport.Status);
        Assert.Equal(ReinstatementStatus.WouldApply, podiumReport.Status);
    }

    [Fact]
    public void Validate_BooleanWithNoDomainBounds_ShouldApply()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "hasPodium", DisplayName = "Has Podium", Type = DesignStateParameterType.Boolean, BooleanValue = true });

        var targets = new[]
        {
            // Boolean resolved with no domain bounds — should never be OutOfRange
            MakeTarget("hasPodium", TargetResolutionStatus.Resolved, DesignStateParameterType.Boolean),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.True(result.Applied);
        Assert.False(result.Aborted);
        Assert.Equal(1, result.AppliedCount);
        Assert.Equal(ReinstatementStatus.Applied, result.Reports[0].Status);
    }

    [Fact]
    public void Validate_AggregateCounts_ShouldMatchIndividualStatuses()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "a", DisplayName = "A", Type = DesignStateParameterType.Number, NumberValue = 10.0 },
            new DesignStateParameter { ParameterId = "b", DisplayName = "B", Type = DesignStateParameterType.Number, NumberValue = 20.0 },
            new DesignStateParameter { ParameterId = "c", DisplayName = "C", Type = DesignStateParameterType.Integer, IntegerValue = 5 });

        var targets = new[]
        {
            MakeTarget("a", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 100),
            // Out of range: value 20 > max 15
            MakeTarget("b", TargetResolutionStatus.Resolved, DesignStateParameterType.Number, 0, 15),
            MakeTarget("c", TargetResolutionStatus.Resolved, DesignStateParameterType.Integer, 0, 10),
        };

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.True(result.Aborted);
        // 1 blocked (OutOfRange), 2 WouldApply
        Assert.Equal(1, result.BlockedCount);
        Assert.Equal(0, result.AppliedCount);
        Assert.Equal(0, result.UnchangedCount);
        Assert.Equal(2, result.Reports.Count(r => r.Status == ReinstatementStatus.WouldApply));
    }

    [Fact]
    public void Validate_NoTargetInList_ShouldReportMissingTarget()
    {
        var snapshot = CreateSnapshot(
            new DesignStateParameter { ParameterId = "unknown", DisplayName = "Unknown", Type = DesignStateParameterType.Number, NumberValue = 5.0 });

        // Empty target list — parameter has no match
        var targets = Array.Empty<ResolvedTarget>();

        var result = _sut.Validate(snapshot, targets, lastAppliedStateId: null);

        Assert.False(result.Applied);
        Assert.True(result.Aborted);
        Assert.Equal(ReinstatementStatus.MissingTarget, result.Reports[0].Status);
        Assert.Contains("No resolved target", result.Reports[0].Detail);
    }

    private static ParamState CreateSnapshot(params DesignStateParameter[] parameters)
    {
        var snapshot = new ParamState
        {
            StateId = $"test-state-{string.Join("-", parameters.Select(p => p.ParameterId))}",
            CapturedAtUtc = new DateTimeOffset(2026, 1, 15, 10, 0, 0, TimeSpan.Zero),
        };

        foreach (var p in parameters)
        {
            snapshot.Parameters.Add(p);
        }

        return snapshot;
    }

    private static ResolvedTarget MakeTarget(
        string parameterId,
        TargetResolutionStatus resolution,
        DesignStateParameterType? type,
        double? min = null,
        double? max = null)
    {
        return new ResolvedTarget(parameterId, resolution, type, min, max);
    }
}
