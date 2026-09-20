using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Validation;

namespace DG.Tests;

public sealed class ValidationPublishPackageBuilderTests
{
    [Fact]
    public void Build_ShouldKeepPassAndFailEntitiesPerRuleAndPreferFail()
    {
        var sharedRef = new ElementRef
        {
            DgEntityId = "DG-1",
            DisplayName = "Building 1",
            Geometry = "mesh-data",
        };
        var secondRef = new ElementRef
        {
            DgEntityId = "DG-2",
            DisplayName = "Building 2",
        };
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var passingBinding = new BindingRow();
        passingBinding.ValuesByVar["?b"] = "B1";
        passingBinding.ElementRefsByVar["?b"] = sharedRef;

        var failingBinding = new BindingRow();
        failingBinding.ValuesByVar["?b"] = "B2";
        failingBinding.ElementRefsByVar["?b"] = sharedRef;
        failingBinding.ElementRefsByVar["?b2"] = secondRef;

        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = false,
        };
        result.FailingBindings.Add(failingBinding);

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { passingBinding, failingBinding });

        Assert.Equal("project-a", package.Project);
        Assert.Single(package.RuleResults);
        Assert.Equal(new[] { "DG-1", "DG-2" }, package.RuleResults[0].FailedEntityIds);
        Assert.Empty(package.RuleResults[0].PassedEntityIds);

        Assert.Equal(2, package.Entities.Count);
        var sharedEntity = Assert.Single(package.Entities, entity => entity.DgEntityId == "DG-1");
        Assert.Equal("failed", sharedEntity.OverallStatus);
        Assert.Equal("mesh-data", sharedEntity.Geometry);
        Assert.Equal(new[] { "R_HEIGHT" }, sharedEntity.RuleIds);
        Assert.Equal(new[] { "R_HEIGHT" }, sharedEntity.FailedRuleIds);
        Assert.Empty(sharedEntity.PassedRuleIds);
    }

    [Fact]
    public void Build_ShouldAllowBindingsWithoutElementRefs()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "B1";
        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = true,
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        Assert.Single(package.RuleResults);
        Assert.Empty(package.RuleResults[0].FailedEntityIds);
        Assert.Empty(package.RuleResults[0].PassedEntityIds);
        Assert.Empty(package.Entities);
    }

    [Fact]
    public void Build_ShouldUseBoundVariableValueAsFallbackEntityIdWhenElementRefIdIsMissing()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "building32";
        binding.ElementRefsByVar["?b"] = new ElementRef
        {
            Geometry = "mesh-data",
            DisplayName = "Building 32",
        };

        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = false,
        };
        result.FailingBindings.Add(binding);

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        Assert.Single(package.RuleResults);
        Assert.Equal(new[] { "building32" }, package.RuleResults[0].FailedEntityIds);
        Assert.Empty(package.RuleResults[0].PassedEntityIds);

        var entity = Assert.Single(package.Entities);
        Assert.Equal("building32", entity.DgEntityId);
        Assert.Equal("mesh-data", entity.Geometry);
        Assert.Equal(new[] { "R_HEIGHT" }, entity.RuleIds);
        Assert.Equal(new[] { "R_HEIGHT" }, entity.FailedRuleIds);
    }

    [Fact]
    public void Build_ShouldRejectMixedProjects()
    {
        var rules = new[]
        {
            new Rule { Id = "R1", Project = "project-a" },
            new Rule { Id = "R2", Project = "project-b" },
        };
        var results = new[]
        {
            new RuleEvaluationResult { RuleId = "R1", Passed = true },
            new RuleEvaluationResult { RuleId = "R2", Passed = true },
        };

        var ex = Assert.Throws<InvalidOperationException>(() =>
            ValidationPublishPackageBuilder.Build(rules, results, Array.Empty<BindingRow>()));

        Assert.Contains("single DG project", ex.Message);
    }

    // --- Phase 1201 plan 02: the publish boundary carries the evaluator's typed Status. ---

    [Fact]
    public void Build_ShouldPublishNotEvaluatedWhenNoResultExistsForRule()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };

        // No RuleEvaluationResult supplied for R_HEIGHT at all — the rule was in scope but never
        // evaluated (or produced no result).
        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            Array.Empty<RuleEvaluationResult>(),
            Array.Empty<BindingRow>());

        var ruleResult = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.NotEvaluated, ruleResult.Status);
        Assert.False(ruleResult.Passed);
    }

    [Fact]
    public void Build_ShouldCopyResultStatusVerbatimWhenResultExists()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "B1";
        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = true,
            Status = EvidenceStatus.Passed,
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        var ruleResult = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.Passed, ruleResult.Status);
        Assert.True(ruleResult.Passed);
    }

    [Fact]
    public void Build_ShouldPublishUnsupportedStatusRatherThanDisguisingItAsAViolation()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "B1";

        // An unsupported construct: Passed is false (non-authoritative, per the contract), but
        // Status is Unsupported, not Failed — the evaluator never called this a violation.
        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = false,
            Status = EvidenceStatus.Unsupported,
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        var ruleResult = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.Unsupported, ruleResult.Status);
        Assert.False(ruleResult.Passed);
        // Status is not recomputed from Passed — an Unsupported result must not silently read as
        // Failed just because Passed happens to be false.
        Assert.NotEqual(EvidenceStatus.Failed, ruleResult.Status);
    }
}
