using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Tests;

public sealed class VariableTypeInferrerTests
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

    [Fact]
    public void Infer_ShouldReturnObject_WhenVariableIsClassAtomSubjectAndAlsoDataPropertySubject()
    {
        // Phase 7 success criterion 1: Object wins on conflict.
        var rule = BuildCanonicalRule();

        var kind = VariableTypeInferrer.Infer(rule, "?b");

        Assert.Equal(VariableKind.Object, kind);
    }

    [Fact]
    public void Infer_ShouldReturnObject_WhenVariableIsClassAtomSubjectOnly()
    {
        var rule = new Rule { Id = "R_TEST_SIMPLE" };
        var classAtom = new Atom { Id = "Body_1", Type = "ClassAtom", PredicateIri = "Building", Side = AtomSide.Body, Order = 1 };
        classAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        rule.BodyAtoms.Add(classAtom);

        var kind = VariableTypeInferrer.Infer(rule, "?b");

        Assert.Equal(VariableKind.Object, kind);
    }

    [Fact]
    public void Infer_ShouldReturnProperty_WhenVariableIsDataPropertyValueOnlyAndNeverInClassAtom()
    {
        var rule = BuildCanonicalRule();

        var kind = VariableTypeInferrer.Infer(rule, "?h");

        // ?h appears at pos-2 of hasHeightM(?b,?h) (DataPropertyAtom) and at pos-1 of the
        // BuiltinAtom swrlb:greaterThan(?h,75) — never as a ClassAtom subject, so Property wins.
        Assert.Equal(VariableKind.Property, kind);
    }

    [Fact]
    public void Infer_ShouldReturnNull_WhenVariableOnlyAppearsInsideBuiltinAtomArgs()
    {
        var rule = new Rule { Id = "R_TEST_BUILTIN_ONLY" };
        var builtinAtom = new Atom { Id = "Body_1", Type = "BuiltinAtom", PredicateIri = "swrlb:greaterThan", Side = AtomSide.Body, Order = 1 };
        builtinAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?h" });
        builtinAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "75", Datatype = "xsd:integer" });
        rule.BodyAtoms.Add(builtinAtom);

        var kind = VariableTypeInferrer.Infer(rule, "?h");

        Assert.Null(kind);
    }

    [Fact]
    public void Infer_ShouldResolveObject_ForCanonicalExampleHeadOnlyPositionViaBodyClassAtom()
    {
        // ?b appears at head pos-1 of violatesMaxHeight(?b,true) (DataPropertyAtom), but it
        // already resolves to Object via the body ClassAtom Building(?b) — confirming the
        // priority chain checks body+head together rather than head in isolation.
        var rule = BuildCanonicalRule();

        var kind = VariableTypeInferrer.Infer(rule, "?b");

        Assert.Equal(VariableKind.Object, kind);
    }

    [Fact]
    public void Infer_ShouldReturnNull_WhenVariableNameNotPresentInRule()
    {
        var rule = BuildCanonicalRule();

        var kind = VariableTypeInferrer.Infer(rule, "?notPresent");

        Assert.Null(kind);
    }

    [Fact]
    public void Infer_ShouldReturnObject_WhenVariableIsObjectPropertyAtomSubjectOnly()
    {
        // adjacentTo(?b1, ?b2) — ?b1 never appears as a ClassAtom subject in this rule, but
        // ObjectPropertyAtom relates two individuals, so it should resolve to Object.
        var rule = new Rule { Id = "R_TEST_OBJECT_PROPERTY" };
        var objectPropertyAtom = new Atom { Id = "Body_1", Type = "ObjectPropertyAtom", PredicateIri = "adjacentTo", Side = AtomSide.Body, Order = 1 };
        objectPropertyAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b1" });
        objectPropertyAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?b2" });
        rule.BodyAtoms.Add(objectPropertyAtom);

        var kindArg1 = VariableTypeInferrer.Infer(rule, "?b1");
        var kindArg2 = VariableTypeInferrer.Infer(rule, "?b2");

        Assert.Equal(VariableKind.Object, kindArg1);
        Assert.Equal(VariableKind.Object, kindArg2);
    }

    [Fact]
    public void Infer_ShouldReturnObject_WhenVariableIsClassAtomSubjectAndAlsoObjectPropertyAtomArg()
    {
        // Building(?b)^adjacentTo(?b,?other) — ClassAtom subject (Priority 1) wins regardless of
        // the ObjectPropertyAtom match, consistent with the existing ClassAtom-vs-DataProperty
        // priority test above.
        var rule = new Rule { Id = "R_TEST_CLASS_AND_OBJECT_PROPERTY" };
        var classAtom = new Atom { Id = "Body_1", Type = "ClassAtom", PredicateIri = "Building", Side = AtomSide.Body, Order = 1 };
        classAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        rule.BodyAtoms.Add(classAtom);

        var objectPropertyAtom = new Atom { Id = "Body_2", Type = "ObjectPropertyAtom", PredicateIri = "adjacentTo", Side = AtomSide.Body, Order = 2 };
        objectPropertyAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        objectPropertyAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?other" });
        rule.BodyAtoms.Add(objectPropertyAtom);

        var kind = VariableTypeInferrer.Infer(rule, "?b");

        Assert.Equal(VariableKind.Object, kind);
    }
}
