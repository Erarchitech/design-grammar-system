using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Services;
using DG.Core.Validation;

namespace DG.Tests;

// VALIDATOR's ValidStatus is "index-matched to DesignState.ObjStates order", but the binder only
// builds rows for ObjStates of the rule's class. Pairing ValidStatus[i] with bindings[i] puts the
// results of a rule on the second class onto the objects of the first class (test
// v12-hexagonal-facade-01, finding F16: R3 on HexagonalUnit reported onto GlassPanel slots).
public sealed class ValidStatusMapperTests
{
    [Theory]
    [InlineData(EvidenceStatus.Passed, true)]
    [InlineData(EvidenceStatus.Failed, false)]
    [InlineData(EvidenceStatus.Unknown, false)]
    [InlineData(EvidenceStatus.NotEvaluated, false)]
    [InlineData(EvidenceStatus.NoPopulation, false)]
    [InlineData(EvidenceStatus.Unsupported, false)]
    [InlineData(EvidenceStatus.Indeterminate, false)]
    [InlineData(EvidenceStatus.Error, false)]
    public void TypedOutcome_OnlyPassedProjectsToTrue(EvidenceStatus outcome, bool expected)
    {
        var row = new BindingRow { SourceObjStateIndex = 1 };
        var status = ValidStatusMapper.PerObjState(3,
            new[] { new BindingEvaluationResult(row, outcome, null) });

        Assert.Equal(new[] { false, expected, false }, status);
    }

    [Fact]
    public void MissingTypedEvidence_LeavesAllObjStatesNotPassed()
    {
        Assert.Equal(new[] { false, false }, ValidStatusMapper.PerObjState(2, null));
        Assert.Equal(new[] { false, false },
            ValidStatusMapper.PerObjState(2, Array.Empty<BindingEvaluationResult>()));
    }

    [Fact]
    public void MixedOutcomes_PreserveOnlyActuallyPassingObjStates()
    {
        var outcomes = new[]
        {
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 3 }, EvidenceStatus.Passed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 1 }, EvidenceStatus.Unsupported, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 0 }, EvidenceStatus.Failed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 2 }, EvidenceStatus.Unknown, null),
        };

        Assert.Equal(new[] { false, false, false, true, false },
            ValidStatusMapper.PerObjState(5, outcomes));
    }

    [Fact]
    public void MissingOrOutOfRangeSourceIndex_DoesNotWriteAnotherObjState()
    {
        var outcomes = new[]
        {
            new BindingEvaluationResult(new BindingRow(), EvidenceStatus.Passed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = -1 }, EvidenceStatus.Passed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 2 }, EvidenceStatus.Passed, null),
        };

        Assert.Equal(new[] { false, false }, ValidStatusMapper.PerObjState(2, outcomes));
    }

    [Fact]
    public void ObjectPropertyRefusal_DoesNotBecomePassingObjState()
    {
        var rule = new Rule
        {
            Id = "R_FAC_A1_CONTROL_V",
            Variables = { new Variable { Name = "?m" }, new Variable { Name = "?v1" } },
            BodyAtoms =
            {
                new Atom
                {
                    Type = "ClassAtom", PredicateIri = "FacadeModule", Side = AtomSide.Body,
                    Args = { new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?m" } },
                },
                new Atom
                {
                    Type = "ObjectPropertyAtom", PredicateIri = "hasUpperVertex", Side = AtomSide.Body,
                    Args =
                    {
                        new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?m" },
                        new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?v1" },
                    },
                },
            },
        };
        var state = new DesignState
        {
            ObjStates = { new ObjState { ObjectRef = "module_0", ClassIri = "FacadeModule" } },
        };
        var bindings = DesignStateBindingService.BuildBindings(rule, state);
        var result = new RuleEvaluator().EvaluateRule(rule, bindings);

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.Empty(result.FailingBindings);
        Assert.Single(result.BindingResults!);
        var status = ValidStatusMapper.PerObjState(state.ObjStates.Count, result.BindingResults);

        Assert.Equal(new[] { false }, status);
    }

    [Fact]
    public void RuleOnSecondClass_StatusLandsOnThatClassesObjStates()
    {
        // computed geometry: ObjectRefs repeat across classes (obj_0, obj_1), as OBJECT STATE emits them
        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_GP0", ObjectRef = "obj_0", ClassIri = "ex:GlassPanel" },
                new() { StateId = "OS_GP1", ObjectRef = "obj_1", ClassIri = "ex:GlassPanel" },
                new() { StateId = "OS_HU0", ObjectRef = "obj_0", ClassIri = "ex:HexagonalUnit" },
                new() { StateId = "OS_HU1", ObjectRef = "obj_1", ClassIri = "ex:HexagonalUnit" },
            },
        };
        var rule = new Rule
        {
            Id = "R_HEX",
            Variables = { new Variable { Name = "?u" } },
            BodyAtoms =
            {
                new Atom
                {
                    Type = "ClassAtom", PredicateIri = "ex:HexagonalUnit", Side = AtomSide.Body, Order = 0,
                    Args = { new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?u" } },
                },
            },
        };
        var bindings = DesignStateBindingService.BuildBindings(rule, designState);
        var outcomes = new[]
        {
            new BindingEvaluationResult(bindings[0], EvidenceStatus.Passed, null),
            new BindingEvaluationResult(bindings[1], EvidenceStatus.Failed, null),
        };
        var status = ValidStatusMapper.PerObjState(designState.ObjStates.Count, outcomes);

        Assert.Equal(new[] { false, false, true, false }, status);
    }

    [Fact]
    public void RuleOnFirstClass_KeepsThePreviousResult()
    {
        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_B0", ObjectRef = "B1", ClassIri = "ex:Building" },
                new() { StateId = "OS_B1", ObjectRef = "B2", ClassIri = "ex:Building" },
                new() { StateId = "OS_W0", ObjectRef = "W1", ClassIri = "ex:Window" },
            },
        };
        var rule = new Rule
        {
            Id = "R_B",
            Variables = { new Variable { Name = "?b" } },
            BodyAtoms =
            {
                new Atom
                {
                    Type = "ClassAtom", PredicateIri = "ex:Building", Side = AtomSide.Body, Order = 0,
                    Args = { new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" } },
                },
            },
        };
        var bindings = DesignStateBindingService.BuildBindings(rule, designState);

        var outcomes = new[]
        {
            new BindingEvaluationResult(bindings[0], EvidenceStatus.Failed, null),
            new BindingEvaluationResult(bindings[1], EvidenceStatus.Passed, null),
        };
        var status = ValidStatusMapper.PerObjState(designState.ObjStates.Count, outcomes);

        Assert.Equal(new[] { false, true, false }, status);
    }

    // Phase 1303-25 (D-71), live 2026-10-25: 313 boxes without data were unknown in the evidence but false in
    // ValidStatus, and the Revit highlighter painted all of them as violations. VALIDATOR's Status output carries the
    // canonical status per ObjState so a consumer can tell a non-verdict from a failure.
    [Fact]
    public void Status_CarriesTheCanonicalWireNamePerObjState()
    {
        var outcomes = new[]
        {
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 3 }, EvidenceStatus.Passed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 1 }, EvidenceStatus.Unsupported, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 0 }, EvidenceStatus.Failed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 2 }, EvidenceStatus.Unknown, null),
        };

        Assert.Equal(new[] { "failed", "unsupported", "unknown", "passed", "" },
            ValidStatusMapper.PerObjStateStatus(5, outcomes));
    }

    [Fact]
    public void Status_IsEmptyOutsideThePopulationAndAgreesWithValidStatus()
    {
        var outcomes = new[]
        {
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 1 }, EvidenceStatus.Passed, null),
            new BindingEvaluationResult(new BindingRow(), EvidenceStatus.Failed, null),
            new BindingEvaluationResult(new BindingRow { SourceObjStateIndex = 9 }, EvidenceStatus.Failed, null),
        };

        var status = ValidStatusMapper.PerObjStateStatus(3, outcomes);
        Assert.Equal(new[] { "", "passed", "" }, status);
        Assert.Equal(ValidStatusMapper.PerObjState(3, outcomes), status.Select(s => s == "passed").ToList());
        Assert.Equal(new[] { "", "" }, ValidStatusMapper.PerObjStateStatus(2, null));
    }
}
