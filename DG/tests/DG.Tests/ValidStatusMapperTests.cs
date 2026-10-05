using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

// VALIDATOR's ValidStatus is "index-matched to DesignState.ObjStates order", but the binder only
// builds rows for ObjStates of the rule's class. Pairing ValidStatus[i] with bindings[i] puts the
// results of a rule on the second class onto the objects of the first class (test
// v12-hexagonal-facade-01, finding F16: R3 on HexagonalUnit reported onto GlassPanel slots).
public sealed class ValidStatusMapperTests
{
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
        var failing = new[] { bindings[1] }; // second hexagonal unit violates

        var status = ValidStatusMapper.PerObjState(designState.ObjStates.Count, bindings, failing);

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

        var status = ValidStatusMapper.PerObjState(designState.ObjStates.Count, bindings, new[] { bindings[0] });

        Assert.Equal(new[] { false, true, false }, status);
    }
}
