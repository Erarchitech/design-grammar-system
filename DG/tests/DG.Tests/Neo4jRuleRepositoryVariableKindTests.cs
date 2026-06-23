using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class Neo4jRuleRepositoryVariableKindTests
{
    private static Rule BuildCanonicalRule()
    {
        // Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)
        var rule = new Rule { Id = "R_URB_HEIGHT_MAX_75_V" };

        var classAtom = new Atom { Id = "Body_1", Type = "ClassAtom", PredicateIri = "Building", Side = AtomSide.Body, Order = 1 };
        classAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        rule.BodyAtoms.Add(classAtom);

        var dataPropertyAtom = new Atom { Id = "Body_2", Type = "DataPropertyAtom", PredicateIri = "hasHeightM", Side = AtomSide.Body, Order = 2 };
        dataPropertyAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        dataPropertyAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?h" });
        rule.BodyAtoms.Add(dataPropertyAtom);

        var builtinAtom = new Atom { Id = "Body_3", Type = "BuiltinAtom", PredicateIri = "swrlb:greaterThan", Side = AtomSide.Body, Order = 3 };
        builtinAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?h" });
        builtinAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "75", Datatype = "xsd:integer" });
        rule.BodyAtoms.Add(builtinAtom);

        var headAtom = new Atom { Id = "Head_1", Type = "DataPropertyAtom", PredicateIri = "violatesMaxHeight", Side = AtomSide.Head, Order = 1 };
        headAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        headAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "true", Datatype = "xsd:boolean" });
        rule.HeadAtoms.Add(headAtom);

        return rule;
    }

    private static Rule BuildBuiltinOnlyRule()
    {
        var rule = new Rule { Id = "R_TEST_BUILTIN_ONLY" };
        var builtinAtom = new Atom { Id = "Body_1", Type = "BuiltinAtom", PredicateIri = "swrlb:greaterThan", Side = AtomSide.Body, Order = 1 };
        builtinAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?h" });
        builtinAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "75", Datatype = "xsd:integer" });
        rule.BodyAtoms.Add(builtinAtom);
        return rule;
    }

    [Fact]
    public void PopulateVariables_ShouldSetObjectKind_ForClassAtomSubjectVariable()
    {
        var rule = BuildCanonicalRule();

        Neo4jRuleRepository.PopulateVariablesForTesting(new[] { rule });

        var variable = rule.Variables.Single(v => v.Name == "?b");
        Assert.Equal(VariableKind.Object, variable.Kind);
    }

    [Fact]
    public void PopulateVariables_ShouldSetPropertyKind_ForDataPropertyValueOnlyVariable()
    {
        var rule = BuildCanonicalRule();

        Neo4jRuleRepository.PopulateVariablesForTesting(new[] { rule });

        var variable = rule.Variables.Single(v => v.Name == "?h");
        Assert.Equal(VariableKind.Property, variable.Kind);
    }

    [Fact]
    public void PopulateVariables_ShouldLeaveKindNull_ForBuiltinOnlyVariable()
    {
        var rule = BuildBuiltinOnlyRule();

        Neo4jRuleRepository.PopulateVariablesForTesting(new[] { rule });

        var variable = rule.Variables.Single(v => v.Name == "?h");
        Assert.Null(variable.Kind);
    }
}
