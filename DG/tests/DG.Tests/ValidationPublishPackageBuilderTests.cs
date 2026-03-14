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
}
