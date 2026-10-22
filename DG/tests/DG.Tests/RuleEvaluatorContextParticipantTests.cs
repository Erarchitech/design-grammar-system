using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Services;
using DG.Core.Validation;

namespace DG.Tests;

/// <summary>
/// D-61 (Phase 1303 plan 19): a rule that names several object classes and the relations between
/// them validates exactly like its one-class form; the participants are asserted by the rule,
/// excluded from binding and disclosed in the message. Genuine joins keep the typed refusal.
/// </summary>
public sealed class RuleEvaluatorContextParticipantTests
{
    private const string OneClassViolatedMessage = "Rule violated by 1 binding(s).";

    private const string DisclosureSentence =
        "Asserted by the rule, not verified: Slab(?s), hostedBy(?o, ?s), Column(?c), projectsOnto(?c, ?s), Wall(?w), projectsOnto(?w, ?s).";

    private static PropState Clearance(string ruleId, string objectRef, double millimetres) =>
        new()
        {
            StateId = "PS_" + objectRef,
            RuleIri = ruleId,
            DataPropertyIri = "hasMinProjectionClearanceMm",
            ObjectRef = objectRef,
            PropValue = new DesignStateParameter
            {
                ParameterId = "d",
                Type = DesignStateParameterType.Number,
                NumberValue = millimetres,
            },
        };

    private static DesignState DesignStateWith(string ruleId, params double[] openingClearances)
    {
        var state = new DesignState();
        for (var i = 0; i < openingClearances.Length; i++)
        {
            var id = "O" + (i + 1);
            state.ObjStates.Add(new ObjState { StateId = "OS_" + id, ObjectRef = id, ClassIri = "Opening" });
            state.PropStates.Add(Clearance(ruleId, id, openingClearances[i]));
        }

        state.ObjStates.Add(new ObjState { StateId = "OS_S1", ObjectRef = "S1", ClassIri = "Slab" });
        state.ObjStates.Add(new ObjState { StateId = "OS_C1", ObjectRef = "C1", ClassIri = "Column" });
        state.ObjStates.Add(new ObjState { StateId = "OS_W1", ObjectRef = "W1", ClassIri = "Wall" });
        return state;
    }

    private static string RowSignature(BindingRow row) =>
        string.Join(";", row.ValuesByVar.OrderBy(p => p.Key, StringComparer.Ordinal).Select(p => $"{p.Key}={p.Value}"));

    [Fact]
    public void MultiParticipantRule_EvaluatesLikeItsOneClassForm()
    {
        var acceptance = RuleVariableRolesTests.AcceptanceRule();
        var oneClass = RuleVariableRolesTests.OneClassForm();
        var state = DesignStateWith(acceptance.Id, 300, 600, 700);

        var acceptanceRows = DesignStateBindingService.BuildBindings(acceptance, state);
        var oneClassRows = DesignStateBindingService.BuildBindings(oneClass, state);

        Assert.Equal(3, acceptanceRows.Count);
        Assert.Equal(oneClassRows.Select(RowSignature), acceptanceRows.Select(RowSignature));
        Assert.All(acceptanceRows, row => Assert.DoesNotContain(row.ValuesByVar.Keys, k => k is "?s" or "?c" or "?w"));

        var evaluator = new RuleEvaluator();
        var acceptanceResult = evaluator.EvaluateRule(acceptance, acceptanceRows);
        var oneClassResult = evaluator.EvaluateRule(oneClass, oneClassRows);

        Assert.Equal(EvidenceStatus.Failed, oneClassResult.Status);
        Assert.Equal(oneClassResult.Status, acceptanceResult.Status);
        Assert.Equal(oneClassResult.Passed, acceptanceResult.Passed);
        Assert.Equal(
            oneClassResult.FailingBindings.Select(RowSignature),
            acceptanceResult.FailingBindings.Select(RowSignature));
        Assert.Equal("?o=O1;?d=300".Split(';').OrderBy(x => x, StringComparer.Ordinal), RowSignature(acceptanceResult.FailingBindings.Single()).Split(';').OrderBy(x => x, StringComparer.Ordinal));
        Assert.Equal(
            oneClassResult.BindingResults!.Select(r => r.Status),
            acceptanceResult.BindingResults!.Select(r => r.Status));
    }

    [Fact]
    public void MultiParticipantRule_MessageIsTheOneClassMessageFollowedByTheDisclosure()
    {
        var acceptance = RuleVariableRolesTests.AcceptanceRule();
        var oneClass = RuleVariableRolesTests.OneClassForm();
        var state = DesignStateWith(acceptance.Id, 300, 600, 700);
        var evaluator = new RuleEvaluator();

        var acceptanceResult = evaluator.EvaluateRule(acceptance, DesignStateBindingService.BuildBindings(acceptance, state));
        var oneClassResult = evaluator.EvaluateRule(oneClass, DesignStateBindingService.BuildBindings(oneClass, state));

        // Rule without context atoms keeps today's message byte for byte.
        Assert.Equal(OneClassViolatedMessage, oneClassResult.Message);
        Assert.DoesNotContain("Asserted by the rule", oneClassResult.Message);
        Assert.Equal(OneClassViolatedMessage + " " + DisclosureSentence, acceptanceResult.Message);
    }

    [Fact]
    public void MultiParticipantRule_PassedMessageIsDisclosedToo()
    {
        var acceptance = RuleVariableRolesTests.AcceptanceRule();
        var state = DesignStateWith(acceptance.Id, 600, 700, 800);
        var evaluator = new RuleEvaluator();

        var result = evaluator.EvaluateRule(acceptance, DesignStateBindingService.BuildBindings(acceptance, state));

        Assert.Equal(EvidenceStatus.Passed, result.Status);
        Assert.True(result.Passed);
        Assert.Empty(result.FailingBindings);
        Assert.Equal("Rule passed for all bindings. " + DisclosureSentence, result.Message);
    }

    [Fact]
    public void MultiParticipantRule_WithoutOpeningObjStatesIsNoPopulationLikeItsOneClassForm()
    {
        var acceptance = RuleVariableRolesTests.AcceptanceRule();
        var oneClass = RuleVariableRolesTests.OneClassForm();
        var state = DesignStateWith(acceptance.Id); // Slab/Column/Wall ObjStates only
        var evaluator = new RuleEvaluator();

        var acceptanceRows = DesignStateBindingService.BuildBindings(acceptance, state);
        var oneClassRows = DesignStateBindingService.BuildBindings(oneClass, state);
        var acceptanceResult = evaluator.EvaluateRule(acceptance, acceptanceRows);
        var oneClassResult = evaluator.EvaluateRule(oneClass, oneClassRows);

        Assert.Empty(acceptanceRows);
        Assert.Equal(EvidenceStatus.NoPopulation, acceptanceResult.Status);
        Assert.Equal(oneClassResult.Status, acceptanceResult.Status);
        Assert.Equal(oneClassResult.Message, acceptanceResult.Message);
    }

    [Fact]
    public void ContextAtom_IsNotEvaluatedAsAPassingBodyAtom_ViolationStillComesFromTheCheckedAtoms()
    {
        // Prohibition: a context atom must never turn a violation into a pass, nor a pass into a violation.
        var acceptance = RuleVariableRolesTests.AcceptanceRule();
        var state = DesignStateWith(acceptance.Id, 499, 500);
        var evaluator = new RuleEvaluator();

        var result = evaluator.EvaluateRule(acceptance, DesignStateBindingService.BuildBindings(acceptance, state));

        Assert.Equal(EvidenceStatus.Failed, result.Status);
        Assert.Single(result.FailingBindings);
        Assert.Equal("O1", result.FailingBindings[0].ValuesByVar["?o"]);
    }

    [Fact]
    public void JoinRule_StillReturnsUnsupportedWithTodaysRefusalText()
    {
        var join = RuleVariableRolesTests.JoinRule();
        var row = new BindingRow
        {
            ValuesByVar = { ["?o"] = "O1", ["?b"] = "B1", ["?x"] = 0.5m },
        };

        var result = new RuleEvaluator().EvaluateRule(join, new[] { row });

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.False(result.Passed);
        Assert.Empty(result.FailingBindings);
        Assert.Contains("is an object property, which this evaluator recognizes but does not evaluate", result.Message);
        Assert.Contains("predicate 'hostedBy'", result.Message);
        Assert.DoesNotContain("Asserted by the rule", result.Message);
    }

    [Fact]
    public void RuleWithoutHeadAtom_KeepsTheObjectPropertyRefusal()
    {
        var rule = new Rule { Id = "R_NOHEAD" };
        rule.BodyAtoms.Add(RuleVariableRolesTests.Cls("B1", "Opening", "?m"));
        rule.BodyAtoms.Add(RuleVariableRolesTests.Cls("B2", "Slab", "?s"));
        rule.BodyAtoms.Add(RuleVariableRolesTests.Obj("B3", "hostedBy", "?m", "?s"));
        var row = new BindingRow { ValuesByVar = { ["?m"] = "O1", ["?s"] = "S1" } };

        var result = new RuleEvaluator().EvaluateRule(rule, new[] { row });

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.Contains("is an object property, which this evaluator recognizes but does not evaluate", result.Message);
    }

    [Fact]
    public void ArgumentLessObjectPropertyAtom_KeepsTheRefusalEvenInARuleWithAHead()
    {
        var rule = new Rule { Id = "R_ARGLESS" };
        rule.BodyAtoms.Add(RuleVariableRolesTests.Cls("B1", "Opening", "?o"));
        rule.BodyAtoms.Add(new Atom { Id = "B2", Type = "ObjectPropertyAtom", PredicateIri = "hostedBy", Side = AtomSide.Body });
        rule.HeadAtoms.Add(RuleVariableRolesTests.Head("?o"));
        var row = new BindingRow { ValuesByVar = { ["?o"] = "O1" } };

        var result = new RuleEvaluator().EvaluateRule(rule, new[] { row });

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.DoesNotContain("Asserted by the rule", result.Message);
    }

    [Fact]
    public void FailingBindingFormatter_PrintsOnlyTheCheckedObject()
    {
        var acceptance = RuleVariableRolesTests.AcceptanceRule();
        var oneClass = RuleVariableRolesTests.OneClassForm();
        var state = DesignStateWith(acceptance.Id, 300, 600, 700);
        var evaluator = new RuleEvaluator();
        var failing = evaluator
            .EvaluateRule(acceptance, DesignStateBindingService.BuildBindings(acceptance, state))
            .FailingBindings.Single();

        var text = FailingBindingFormatter.Format(acceptance, failing);

        Assert.StartsWith("o(O1)", text);
        Assert.DoesNotContain("s(", text);
        Assert.DoesNotContain("c(", text);
        Assert.DoesNotContain("w(", text);
        Assert.DoesNotContain("<missing>", text);
        Assert.Equal(FailingBindingFormatter.Format(oneClass, failing), text);
    }
}
