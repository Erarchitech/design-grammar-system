using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Tests;

/// <summary>
/// D-61 (Phase 1303 plan 19): the shared classifier that separates the checked object (subject)
/// from context-only participants. Design: docs/superpowers/specs/2026-10-21-multi-participant-rule-extraction-design.md §4.
/// </summary>
public sealed class RuleVariableRolesTests
{
    internal static Atom Cls(string id, string cls, string variable, AtomSide side = AtomSide.Body) =>
        new()
        {
            Id = id,
            Type = "ClassAtom",
            PredicateIri = cls,
            Side = side,
            Args = { new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = variable } },
        };

    internal static Atom Obj(string id, string predicate, string left, string right) =>
        new()
        {
            Id = id,
            Type = "ObjectPropertyAtom",
            PredicateIri = predicate,
            Side = AtomSide.Body,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = left },
                new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = right },
            },
        };

    internal static Atom Data(string id, string predicate, string subject, string value) =>
        new()
        {
            Id = id,
            Type = "DataPropertyAtom",
            PredicateIri = predicate,
            Side = AtomSide.Body,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = subject },
                new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = value },
            },
        };

    internal static Atom LessThan(string id, string variable, string literal) =>
        new()
        {
            Id = id,
            Type = "BuiltinAtom",
            PredicateIri = "swrlb:lessThan",
            Side = AtomSide.Body,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = variable },
                new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = literal, Datatype = "xsd:integer" },
            },
        };

    internal static Atom Head(string subject) =>
        new()
        {
            Id = "Head_1",
            Type = "DataPropertyAtom",
            PredicateIri = "hasProjectionClearanceViolation",
            Side = AtomSide.Head,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = subject },
                new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "true", Datatype = "xsd:boolean" },
            },
        };

    internal static Rule AcceptanceRule()
    {
        var rule = new Rule { Id = "R_OpeningSlabEdgeClearance500" };
        rule.BodyAtoms.Add(Cls("B1", "Opening", "?o"));
        rule.BodyAtoms.Add(Cls("B2", "Slab", "?s"));
        rule.BodyAtoms.Add(Obj("B3", "hostedBy", "?o", "?s"));
        rule.BodyAtoms.Add(Cls("B4", "Column", "?c"));
        rule.BodyAtoms.Add(Obj("B5", "projectsOnto", "?c", "?s"));
        rule.BodyAtoms.Add(Cls("B6", "Wall", "?w"));
        rule.BodyAtoms.Add(Obj("B7", "projectsOnto", "?w", "?s"));
        rule.BodyAtoms.Add(Data("B8", "hasMinProjectionClearanceMm", "?o", "?d"));
        rule.BodyAtoms.Add(LessThan("B9", "?d", "500"));
        rule.HeadAtoms.Add(Head("?o"));
        foreach (var name in new[] { "?o", "?s", "?c", "?w", "?d" })
        {
            rule.Variables.Add(new Variable { Name = name });
        }

        return rule;
    }

    internal static Rule OneClassForm()
    {
        var rule = new Rule { Id = "R_OpeningSlabEdgeClearance500" };
        rule.BodyAtoms.Add(Cls("B1", "Opening", "?o"));
        rule.BodyAtoms.Add(Data("B8", "hasMinProjectionClearanceMm", "?o", "?d"));
        rule.BodyAtoms.Add(LessThan("B9", "?d", "500"));
        rule.HeadAtoms.Add(Head("?o"));
        foreach (var name in new[] { "?o", "?d" })
        {
            rule.Variables.Add(new Variable { Name = name });
        }

        return rule;
    }

    internal static Rule JoinRule()
    {
        var rule = new Rule { Id = "R_OpeningBeamJoin" };
        rule.BodyAtoms.Add(Cls("B1", "Opening", "?o"));
        rule.BodyAtoms.Add(Cls("B2", "Beam", "?b"));
        rule.BodyAtoms.Add(Obj("B3", "hostedBy", "?o", "?b"));
        rule.BodyAtoms.Add(Data("B4", "depth", "?b", "?x"));
        rule.BodyAtoms.Add(LessThan("B5", "?x", "1"));
        rule.HeadAtoms.Add(Head("?o"));
        foreach (var name in new[] { "?o", "?b", "?x" })
        {
            rule.Variables.Add(new Variable { Name = name });
        }

        return rule;
    }

    [Fact]
    public void SubjectVariable_IsHeadPositionOneVariable()
    {
        Assert.Equal("?o", RuleVariableRoles.SubjectVariable(AcceptanceRule()));
    }

    [Fact]
    public void SubjectVariable_IsNullWithoutHeadAtomOrWithLiteralSubject()
    {
        var noHead = new Rule { Id = "R_NOHEAD" };
        noHead.BodyAtoms.Add(Cls("B1", "Opening", "?m"));
        Assert.Null(RuleVariableRoles.SubjectVariable(noHead));

        var literalHead = new Rule { Id = "R_LITHEAD" };
        literalHead.BodyAtoms.Add(Cls("B1", "Opening", "?m"));
        literalHead.HeadAtoms.Add(new Atom
        {
            Id = "H1",
            Type = "DataPropertyAtom",
            PredicateIri = "flag",
            Side = AtomSide.Head,
            Args = { new AtomArg { Pos = 1, Kind = ArgKind.Literal, Value = "x" } },
        });
        Assert.Null(RuleVariableRoles.SubjectVariable(literalHead));
    }

    [Fact]
    public void AcceptanceRule_ClassifiesSlabColumnAndWallAsContextOnly()
    {
        var rule = AcceptanceRule();

        Assert.True(RuleVariableRoles.IsContextOnly(rule, "?s"));
        Assert.True(RuleVariableRoles.IsContextOnly(rule, "?c"));
        Assert.True(RuleVariableRoles.IsContextOnly(rule, "?w"));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?o"));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?d"));
    }

    [Fact]
    public void IsContextOnly_ToleratesMissingQuestionMarkAndCase()
    {
        var rule = AcceptanceRule();

        Assert.True(RuleVariableRoles.IsContextOnly(rule, "s"));
        Assert.True(RuleVariableRoles.IsContextOnly(rule, "?S"));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "O"));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?absent"));
    }

    [Fact]
    public void AcceptanceRule_ContextAtomsAreTheSixParticipantAtomsInBodyOrder()
    {
        var rule = AcceptanceRule();

        var ids = RuleVariableRoles.ContextAtoms(rule).Select(a => a.Id).ToArray();

        Assert.Equal(new[] { "B2", "B3", "B4", "B5", "B6", "B7" }, ids);
        Assert.False(RuleVariableRoles.IsContextAtom(rule, rule.BodyAtoms[0]));
        Assert.False(RuleVariableRoles.IsContextAtom(rule, rule.BodyAtoms[7]));
        Assert.False(RuleVariableRoles.IsContextAtom(rule, rule.BodyAtoms[8]));
    }

    [Fact]
    public void OneClassForm_HasNoContextOnlyVariableAndNoContextAtom()
    {
        var rule = OneClassForm();

        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?o"));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?d"));
        Assert.Empty(RuleVariableRoles.ContextAtoms(rule));
    }

    [Fact]
    public void RuleWithoutHeadAtom_HasNoSubjectAndNothingIsContextOnly()
    {
        var rule = new Rule { Id = "R_NOHEAD" };
        rule.BodyAtoms.Add(Cls("B1", "Opening", "?m"));
        rule.BodyAtoms.Add(Cls("B2", "Slab", "?s"));
        rule.BodyAtoms.Add(Obj("B3", "hostedBy", "?m", "?s"));

        Assert.Null(RuleVariableRoles.SubjectVariable(rule));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?s"));
        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?m"));
        Assert.Empty(RuleVariableRoles.ContextAtoms(rule));
    }

    [Fact]
    public void JoinRule_ParticipantWithDataPropertyIsNotContextOnlyAndItsRelationIsNotAContextAtom()
    {
        var rule = JoinRule();

        Assert.False(RuleVariableRoles.IsContextOnly(rule, "?b"));
        Assert.False(RuleVariableRoles.IsContextAtom(rule, rule.BodyAtoms[2]));
        Assert.False(RuleVariableRoles.IsContextAtom(rule, rule.BodyAtoms[1]));
        Assert.Empty(RuleVariableRoles.ContextAtoms(rule));
    }

    [Fact]
    public void ArgumentLessAndSubjectToSubjectObjectPropertyAtomsAreNeverContextAtoms()
    {
        var rule = new Rule { Id = "R_ODD" };
        rule.BodyAtoms.Add(Cls("B1", "Opening", "?o"));
        rule.BodyAtoms.Add(Cls("B2", "Slab", "?s"));
        var argLess = new Atom { Id = "B3", Type = "ObjectPropertyAtom", PredicateIri = "hostedBy", Side = AtomSide.Body };
        var selfRelation = Obj("B4", "rel", "?o", "?o");
        var literalArg = new Atom
        {
            Id = "B5",
            Type = "ObjectPropertyAtom",
            PredicateIri = "rel",
            Side = AtomSide.Body,
            Args =
            {
                new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?s" },
                new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "7" },
            },
        };
        rule.BodyAtoms.Add(argLess);
        rule.BodyAtoms.Add(selfRelation);
        rule.BodyAtoms.Add(literalArg);
        rule.HeadAtoms.Add(Head("?o"));

        Assert.False(RuleVariableRoles.IsContextAtom(rule, argLess));
        Assert.False(RuleVariableRoles.IsContextAtom(rule, selfRelation));
        Assert.False(RuleVariableRoles.IsContextAtom(rule, literalArg));
    }

    [Fact]
    public void RuleBuiltFromSwrlOnly_IsClassifiedFromTheParsedAtoms()
    {
        var rule = new Rule
        {
            Id = "R_SWRL_ONLY",
            Swrl = "Opening(?o) ^ Slab(?s) ^ hasMinProjectionClearanceMm(?o, ?d) ^ swrlb:lessThan(?d, 500) -> hasProjectionClearanceViolation(?o, true)",
        };

        Assert.Equal("?o", RuleVariableRoles.SubjectVariable(rule));
        Assert.True(RuleVariableRoles.IsContextOnly(rule, "?s"));
        Assert.Single(RuleVariableRoles.ContextAtoms(rule));
    }

    [Fact]
    public void Classifier_DoesNotChangeVariableTypeInferrerResults()
    {
        var rule = AcceptanceRule();

        Assert.Equal(VariableKind.Object, VariableTypeInferrer.Infer(rule, "?s"));
        Assert.Equal(VariableKind.Object, VariableTypeInferrer.Infer(rule, "?c"));
        Assert.Equal(VariableKind.Object, VariableTypeInferrer.Infer(rule, "?w"));
        Assert.Equal(VariableKind.Property, VariableTypeInferrer.Infer(rule, "?d"));
    }
}
