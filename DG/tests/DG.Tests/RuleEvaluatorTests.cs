using DG.Core.Models;
using DG.Core.Validation;

namespace DG.Tests;

public sealed class RuleEvaluatorTests
{
    [Fact]
    public void EvaluateRule_ShouldFailWhenHeightExceedsLimit()
    {
        var evaluator = new RuleEvaluator();
        var rule = new Rule
        {
            Id = "R_URB_HEIGHT_MAX_75_V",
            Name = "Maximum Building Height",
            Description = "Maximum height is 75 m",
            Kind = "violation",
            Swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
            Text = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
            Project = "default-project",
            Graph = "Metagraph",
        };

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?b"] = "B1", ["?h"] = 70m } },
            new() { ValuesByVar = { ["?b"] = "B2", ["?h"] = 80m } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);
        Assert.False(result.Passed);
        Assert.Single(result.FailingBindings);
        Assert.Equal("B2", result.FailingBindings[0].ValuesByVar["?b"]);
    }

    [Fact]
    public void EvaluateRule_ShouldMatchBindingsWithoutQuestionMarkPrefix()
    {
        var evaluator = new RuleEvaluator();
        var rule = new Rule
        {
            Id = "R_URB_HEIGHT_MAX_75_V",
            Name = "Maximum Building Height",
            Description = "Maximum height is 75 m",
            Kind = "violation",
            Swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
            Text = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
            Project = "default-project",
            Graph = "Metagraph",
        };

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["b"] = "building1", ["h"] = 78m } },
            new() { ValuesByVar = { ["b"] = "building2", ["h"] = 60m } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);
        Assert.False(result.Passed);
        Assert.Single(result.FailingBindings);
        Assert.Equal("building1", result.FailingBindings[0].ValuesByVar["b"]);
    }

    [Fact]
    public void EvaluateRule_ShouldReturnFailingBindingsWhenVariableIsMissing()
    {
        var evaluator = new RuleEvaluator();
        var rule = new Rule
        {
            Id = "R_URB_HEIGHT_MAX_75_V",
            Name = "Maximum Building Height",
            Description = "Maximum height is 75 m",
            Kind = "violation",
            Swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
            Text = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
            Project = "default-project",
            Graph = "Metagraph",
        };

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?b"] = "building1" } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        Assert.False(result.Passed);
        Assert.Contains("Missing binding for variable ?h", result.Message);
        Assert.Single(result.FailingBindings);
        Assert.Equal("building1", result.FailingBindings[0].ValuesByVar["?b"]);
    }
}
