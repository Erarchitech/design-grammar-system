using System;
using System.Collections.Generic;
using System.Linq;
using DG.Core.Contracts;

namespace DG.Tests;

public sealed class StatusRollupTests
{
    [Fact]
    public void Precedence_ExposesEightStatusesInShippedOrder()
    {
        var expected = new[]
        {
            EvidenceStatus.Error,
            EvidenceStatus.Failed,
            EvidenceStatus.Indeterminate,
            EvidenceStatus.Unsupported,
            EvidenceStatus.Unknown,
            EvidenceStatus.NotEvaluated,
            EvidenceStatus.NoPopulation,
            EvidenceStatus.Passed,
        };

        Assert.Equal(expected, StatusRollup.Precedence);
    }

    [Fact]
    public void Rollup_OverPassedAndUnsupported_ReturnsUnsupported()
    {
        var result = StatusRollup.Rollup(new[] { EvidenceStatus.Passed, EvidenceStatus.Unsupported });

        Assert.Equal(EvidenceStatus.Unsupported, result);
    }

    [Fact]
    public void Rollup_OverFailedAndUnsupported_ReturnsFailed()
    {
        // Failed outranks Unsupported in the shipped order — this is the shipped semantics,
        // adopted verbatim (not something this phase is free to redesign).
        var result = StatusRollup.Rollup(new[] { EvidenceStatus.Failed, EvidenceStatus.Unsupported });

        Assert.Equal(EvidenceStatus.Failed, result);
    }

    [Fact]
    public void Rollup_OverEmptyInput_ReturnsNotEvaluated()
    {
        var result = StatusRollup.Rollup(Array.Empty<EvidenceStatus>());

        Assert.Equal(EvidenceStatus.NotEvaluated, result);
    }

    [Fact]
    public void Precedence_ContainsEveryEvidenceStatusMemberExactlyOnce()
    {
        var allMembers = Enum.GetValues<EvidenceStatus>().ToHashSet();
        var precedenceSet = StatusRollup.Precedence.ToHashSet();

        Assert.Equal(allMembers, precedenceSet);
        Assert.Equal(StatusRollup.Precedence.Count, precedenceSet.Count);
    }

    [Fact]
    public void Build_RollupPrecedence_MatchesStatusRollupForMixedRows()
    {
        var rows = new List<EvidenceRow>
        {
            new() { ObjectId = "OBJ_A", RuleId = "R_1", CanonicalStatus = EvidenceStatus.Passed },
            new() { ObjectId = "OBJ_B", RuleId = "R_2", CanonicalStatus = EvidenceStatus.Unsupported },
            new() { ObjectId = "OBJ_C", RuleId = "R_3", CanonicalStatus = EvidenceStatus.NoPopulation },
        };

        var envelope = EvidenceEnvelopeFactory.Build(
            project: "default-project",
            definitionId: "def-1",
            serviceName: "DG.Tests",
            serviceVersion: "0.0.0",
            stage: "validation",
            rows: rows);

        var expected = StatusRollup.Rollup(rows.Select(r => r.CanonicalStatus));

        Assert.Equal(expected, envelope.CanonicalStatus);
        Assert.Equal(EvidenceStatus.Unsupported, envelope.CanonicalStatus);
    }
}
