using DG.Core.Models;
using DG.Core.Parsing;
using DG.Core.Services;

namespace DG.Tests;

public sealed class DesignStateBindingServiceTests
{
    [Fact]
    public void BuildBindings_ObjectVarsMatchByClassIri()
    {
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");

        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_A", ObjectRef = "B1", ClassIri = "ex:Building" },
                new() { StateId = "OS_B", ObjectRef = "W1", ClassIri = "ex:Window" },
                new() { StateId = "OS_C", ObjectRef = "B2", ClassIri = "ex:Building" },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Equal(2, result.Count);
        Assert.Equal("B1", result[0].ValuesByVar["?b"]);
        Assert.Equal("B2", result[1].ValuesByVar["?b"]);
        Assert.Equal("B1", result[0].ElementRefsByVar["?b"].DgEntityId);
    }

    [Fact]
    public void BuildBindings_PropertyVarMatchByDataPropertyIri()
    {
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");
        rule.BodyAtoms.Add(new Atom
        {
            Type = "DataPropertyAtom",
            PredicateIri = "ex:height",
            Side = AtomSide.Body,
            Order = 1,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" },
                new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?h" },
            },
        });
        rule.Variables.Add(new Variable { Name = "?h" });

        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_A", ObjectRef = "B1", ClassIri = "ex:Building" },
            },
            PropStates = new List<PropState>
            {
                new()
                {
                    RuleIri = rule.Id,
                    DataPropertyIri = "ex:height",
                    PropValue = new DesignStateParameter
                    {
                        ParameterId = "h",
                        Type = DesignStateParameterType.Number,
                        NumberValue = 75.0,
                    },
                },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Single(result);
        Assert.Equal(75.0, result[0].ValuesByVar["?h"]);
    }

    [Fact]
    public void BuildBindings_BuiltinOnlyVariableExcluded()
    {
        // Rule with BuiltinAtom "swrlb:lessthan" referencing "?h" and "?max"
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");
        rule.BodyAtoms.Add(new Atom
        {
            Type = "DataPropertyAtom",
            PredicateIri = "ex:height",
            Side = AtomSide.Body,
            Order = 1,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" },
                new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?h" },
            },
        });
        rule.BodyAtoms.Add(new Atom
        {
            Type = "BuiltinAtom",
            PredicateIri = "swrlb:lessthan",
            Side = AtomSide.Body,
            Order = 2,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?h" },
                new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?max" },
            },
        });
        rule.Variables.Add(new Variable { Name = "?h" });
        rule.Variables.Add(new Variable { Name = "?max" });

        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_A", ObjectRef = "B1", ClassIri = "ex:Building" },
            },
            PropStates = new List<PropState>
            {
                new()
                {
                    RuleIri = rule.Id,
                    DataPropertyIri = "ex:height",
                    PropValue = new DesignStateParameter
                    {
                        ParameterId = "h",
                        Type = DesignStateParameterType.Number,
                        NumberValue = 75.0,
                    },
                },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Single(result);
        Assert.True(result[0].ValuesByVar.ContainsKey("?b"));
        Assert.True(result[0].ValuesByVar.ContainsKey("?h"));
        Assert.False(result[0].ValuesByVar.ContainsKey("?max"));
    }

    [Fact]
    public void BuildBindings_UnclassifiedVariableThrows()
    {
        // Variable "?x" at pos-1 of DataPropertyAtom (not qualifying for Object or Property)
        // No ClassAtom or ObjectPropertyAtom for ?x, and pos-1 is not a Property position.
        // VariableTypeInferrer.Infer sees ?x but returns null (priority 4).
        var rule = new Rule
        {
            Id = "R_TEST_UNCLASSIFIED_V",
            Name = "Test Unclassified",
            Variables = { new Variable { Name = "?x" } },
            BodyAtoms =
            {
                new Atom
                {
                    Type = "DataPropertyAtom",
                    PredicateIri = "ex:height",
                    Side = AtomSide.Body,
                    Order = 0,
                    Args =
                    {
                        new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?x" },
                        new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "75.0" },
                    },
                },
            },
        };

        var designState = new DesignState();

        var ex = Assert.Throws<InvalidOperationException>(() =>
            DesignStateBindingService.BuildBindings(rule, designState));

        Assert.Contains("no REFERS_TO link", ex.Message);
    }

    [Fact]
    public void BuildBindings_NoObjStatesWithObjectVarsThrows()
    {
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");
        var designState = new DesignState();

        var ex = Assert.Throws<InvalidOperationException>(() =>
            DesignStateBindingService.BuildBindings(rule, designState));

        Assert.Contains("DesignState contains no ObjStates", ex.Message);
    }

    [Fact]
    public void BuildBindings_PropertyOnlyRuleCreatesSingleRow()
    {
        var rule = new Rule
        {
            Id = "R_TEST_PROP_ONLY_V",
            Name = "Property Only Rule",
            Variables = { new Variable { Name = "?h" } },
            BodyAtoms =
            {
                new Atom
                {
                    Type = "DataPropertyAtom",
                    PredicateIri = "ex:height",
                    Side = AtomSide.Body,
                    Order = 0,
                    Args =
                    {
                        new AtomArg { Pos = 1, Kind = ArgKind.Literal, Value = "ex:Something" },
                        new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?h" },
                    },
                },
            },
        };

        var designState = new DesignState
        {
            PropStates = new List<PropState>
            {
                new()
                {
                    RuleIri = rule.Id,
                    DataPropertyIri = "ex:height",
                    PropValue = new DesignStateParameter
                    {
                        ParameterId = "h",
                        Type = DesignStateParameterType.Number,
                        NumberValue = 75.0,
                    },
                },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Single(result);
        Assert.Equal(75.0, result[0].ValuesByVar["?h"]);
    }

    [Fact]
    public void BuildBindings_ClassIriMatchingPreservesIndexOrder()
    {
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");

        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_0", ObjectRef = "W1", ClassIri = "ex:Window" },
                new() { StateId = "OS_1", ObjectRef = "B1", ClassIri = "ex:Building" },
                new() { StateId = "OS_2", ObjectRef = "W2", ClassIri = "ex:Window" },
                new() { StateId = "OS_3", ObjectRef = "B2", ClassIri = "ex:Building" },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Equal(2, result.Count);
        Assert.Equal("B1", result[0].ValuesByVar["?b"]);
        Assert.Equal("B2", result[1].ValuesByVar["?b"]);
    }

    [Fact]
    public void BuildBindings_NullClassIriSkipped()
    {
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");

        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_A", ObjectRef = "B1", ClassIri = null },
                new() { StateId = "OS_B", ObjectRef = "B2", ClassIri = "ex:Building" },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Single(result);
        Assert.Equal("B2", result[0].ValuesByVar["?b"]);
    }

    [Fact]
    public void BuildBindings_ZeroMatchingObjStatesReturnsEmpty()
    {
        var rule = MakeRuleWithObjectVar("?b", "ex:Building");

        var designState = new DesignState
        {
            ObjStates = new List<ObjState>
            {
                new() { StateId = "OS_A", ObjectRef = "W1", ClassIri = "ex:Window" },
                new() { StateId = "OS_B", ObjectRef = "W2", ClassIri = "ex:Wall" },
            },
        };

        var result = DesignStateBindingService.BuildBindings(rule, designState);

        Assert.Empty(result);
    }

    private static Rule MakeRuleWithObjectVar(string varName, string classIri)
    {
        return new Rule
        {
            Id = "R_TEST_HEIGHT_75_V",
            Name = "Test Rule",
            Variables = { new Variable { Name = varName } },
            BodyAtoms =
            {
                new Atom
                {
                    Type = "ClassAtom",
                    PredicateIri = classIri,
                    Side = AtomSide.Body,
                    Order = 0,
                    Args =
                    {
                        new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = varName },
                    },
                },
            },
        };
    }
}
