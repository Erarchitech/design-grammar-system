using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Services;
using DG.Core.Validation;

namespace DG.Tests;

/// <summary>
/// F-01 (2026-10-29): the dg-evaluator path composes the Design State the way OBJECT STATE / PROPERTY STATE /
/// DESIGN STATE do and judges each rule the way VALIDATOR does, so a Revit check without Grasshopper gives the
/// same verdicts and the same StateIds.
/// </summary>
public sealed class CheckEvaluationTests
{
    private const string Dp = "hasMinProjectionClearanceMm";

    private static CheckValue Mm(string ruleId, string objectRef, double value) =>
        new() { RuleId = ruleId, DataPropertyIri = Dp, Ref = objectRef, Number = value };

    private static DesignState StateFor(Rule rule) => CheckEvaluation.BuildDesignState(
        "Opening",
        new[]
        {
            new CheckObject { Ref = "uid-1", Label = "Box [1]" },
            new CheckObject { Ref = "uid-2", Label = "Box [2]" },
            new CheckObject { Ref = "uid-3", Label = "Box [3]" },
        },
        new[] { Mm(rule.Id, "uid-1", 300), Mm(rule.Id, "uid-2", 600) });

    [Fact]
    public void DesignState_UsesTheGrasshopperStateIds()
    {
        var rule = RuleVariableRolesTests.OneClassForm();
        var state = StateFor(rule);

        Assert.Equal(3, state.ObjStates.Count);
        Assert.Equal(DesignStateIdGenerator.ComputeObjectStateIdFromRef("uid-1", "Opening"), state.ObjStates[0].StateId);
        Assert.Equal(2, state.PropStates.Count);
        var first = state.PropStates[0];
        Assert.Equal("prop_0", first.PropValue!.ParameterId);
        Assert.Equal("prop_1", state.PropStates[1].PropValue!.ParameterId);
        Assert.Equal(DesignStateIdGenerator.ComputePropStateId(rule.Id, Dp, first.PropValue, "uid-1"), first.StateId);
        var members = state.ObjStates.Select(o => o.StateId).Concat(state.PropStates.Select(p => p.StateId));
        Assert.Equal(DesignStateIdGenerator.ComputeDesignStateId(members), state.StateId);
    }

    [Fact]
    public void DesignState_SkipsDuplicateObjectsAndValuesWithoutAnObjectOrNumber()
    {
        var state = CheckEvaluation.BuildDesignState(
            "Opening",
            new[] { new CheckObject { Ref = "a" }, new CheckObject { Ref = "a" }, new CheckObject { Ref = " " } },
            new[]
            {
                new CheckValue { RuleId = "R", DataPropertyIri = Dp, Ref = "a", Integer = 2 },
                new CheckValue { RuleId = "R", DataPropertyIri = Dp, Ref = "ghost", Integer = 1 },
                new CheckValue { RuleId = "R", DataPropertyIri = Dp, Ref = "a" },
            });

        Assert.Single(state.ObjStates);
        var prop = Assert.Single(state.PropStates);
        Assert.Equal(DesignStateParameterType.Integer, prop.PropValue!.Type);
        Assert.Equal(2, prop.PropValue.IntegerValue);
    }

    [Fact]
    public void EvaluateRule_MatchesTheValidatorPathAndPackagesEveryBox()
    {
        var rule = RuleVariableRolesTests.AcceptanceRule();
        var state = StateFor(rule);

        var outcome = CheckEvaluation.EvaluateRule(rule, state);

        var bindings = DesignStateBindingService.BuildBindings(rule, state);
        var direct = new RuleEvaluator().EvaluateRule(rule, bindings);
        Assert.Equal(direct.Status, outcome.Result.Status);
        Assert.Equal(EvidenceStatus.Failed, outcome.Result.Status);
        Assert.Equal(new[] { false, true, false }, outcome.ValidStatus);
        Assert.Equal("failed", outcome.ValidStatusNames[0]);
        Assert.Equal("passed", outcome.ValidStatusNames[1]);

        var ruleResult = Assert.Single(outcome.Package.RuleResults);
        Assert.Contains("uid-1", ruleResult.FailedEntityIds);
        Assert.Contains("uid-2", ruleResult.PassedEntityIds);
        Assert.Equal(new[] { "uid-1", "uid-2", "uid-3" }, outcome.Package.Entities.Select(e => e.DgEntityId).OrderBy(x => x));
        Assert.False(string.IsNullOrWhiteSpace(outcome.Package.Entities.Single(e => e.DgEntityId == "uid-1").DisplayName));
        Assert.Single(outcome.FailingLines);
    }
}

/// <summary>F-01: dg-evaluator answers one VALIDATOR-shaped publish body per requested rule.</summary>
public sealed class EvaluatorServiceTests
{
    [Fact]
    public void Evaluate_ReturnsOnePublishBodyPerRuleAndReportsMissingRules()
    {
        var rule = RuleVariableRolesTests.AcceptanceRule();
        var json = $$"""
            {"project":"p","classIri":"Opening","ruleIds":["{{rule.Id}}","R_GONE"],
             "objects":[{"ref":"uid-1","label":"Box [1]"},{"ref":"uid-2"}],
             "values":[{"ruleId":"{{rule.Id}}","dataPropertyIri":"hasMinProjectionClearanceMm","ref":"uid-1","value":300},
                       {"ruleId":"{{rule.Id}}","dataPropertyIri":"hasMinProjectionClearanceMm","ref":"uid-2","value":612.5}]}
            """;
        var request = System.Text.Json.JsonSerializer.Deserialize<DG.Evaluator.EvaluateRequest>(
            json, new System.Text.Json.JsonSerializerOptions(System.Text.Json.JsonSerializerDefaults.Web))!;

        var response = DG.Evaluator.Program.Evaluate(request, new[] { rule });

        Assert.Equal(new[] { "R_GONE" }, response.MissingRules);
        var run = Assert.Single(response.Runs);
        Assert.Equal("failed", run.Status);
        Assert.NotNull(response.StatePayloadJson);
        var publish = run.Publish!;
        Assert.Equal(response.StatePayloadJson, publish.StatePayloadJson);
        Assert.Equal(new[] { false, true }, publish.ValidStatus);
        Assert.Equal(new[] { "uid-1" }, publish.RuleResults.Single().FailedEntityIds);
        Assert.Equal("failed", publish.Entities.Single(e => e.DgEntityId == "uid-1").CanonicalStatuses[rule.Id]);
    }
}
