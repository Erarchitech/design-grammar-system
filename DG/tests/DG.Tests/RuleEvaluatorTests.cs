using DG.Core.Contracts;
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

    // Phase 1201 plan 02, D-08: this test formerly asserted the pre-1201 collapsing behavior —
    // a missing variable binding threw InvalidOperationException, was caught by RuleEvaluator's
    // catch-all, and was reported as a failing binding (an ordinary violation). D-08 of the frozen
    // Phase 1200 D-05 situation table requires this to be a typed `unknown` non-verdict instead:
    // evaluation was attempted and could not resolve, which is not the same as a violation. Renamed
    // and rewritten to assert the new, correct behavior; see EvaluateRule_ShouldRollUpToUnknown* for
    // the same case in more detail.
    [Fact]
    public void EvaluateRule_ShouldReturnUnknownWhenVariableIsMissing()
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

        Assert.Equal(EvidenceStatus.Unknown, result.Status);
        Assert.False(result.Passed);
        Assert.Contains("?h", result.Message);
        Assert.Empty(result.FailingBindings);
    }

    // --- Phase 1201 plan 02: D-06 (zero bindings -> no_population) and D-08 (unresolvable binding
    // -> unknown) behaviors, plus the two-binding rollup interactions the plan's behavior spec
    // requires. ---

    private static Rule HeightRule() => new()
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

    [Fact]
    public void EvaluateRule_ShouldReturnNoPopulationForEmptyBindings()
    {
        var evaluator = new RuleEvaluator();
        var rule = HeightRule();

        var result = evaluator.EvaluateRule(rule, new List<BindingRow>());

        Assert.Equal(EvidenceStatus.NoPopulation, result.Status);
        Assert.False(result.Passed);
        Assert.Empty(result.FailingBindings);
        Assert.DoesNotContain("violated", result.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void EvaluateRule_ShouldReturnUnknownForBuiltinArgumentMissingFromBinding()
    {
        var evaluator = new RuleEvaluator();
        var rule = HeightRule();

        // ?b resolves but ?h (the builtin's second argument) does not.
        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?b"] = "building1" } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        Assert.Equal(EvidenceStatus.Unknown, result.Status);
        Assert.False(result.Passed);
        Assert.Empty(result.FailingBindings);
    }

    [Fact]
    public void EvaluateRule_ShouldRollUpToFailedWhenOneBindingUnresolvableAndOneViolates()
    {
        var evaluator = new RuleEvaluator();
        var rule = HeightRule();

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?b"] = "building-unresolvable" } }, // missing ?h -> Unknown
            new() { ValuesByVar = { ["?b"] = "building-violating", ["?h"] = 80m } }, // > 75 -> Failed
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        // Shipped precedence: Failed > Unknown, so the rule-level status is Failed.
        Assert.Equal(EvidenceStatus.Failed, result.Status);
        Assert.False(result.Passed);
        Assert.Single(result.FailingBindings);
        Assert.Equal("building-violating", result.FailingBindings[0].ValuesByVar["?b"]);
    }

    [Fact]
    public void EvaluateRule_ShouldRollUpToUnknownWhenOneBindingUnresolvableAndOneSatisfied()
    {
        var evaluator = new RuleEvaluator();
        var rule = HeightRule();

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?b"] = "building-unresolvable" } }, // missing ?h -> Unknown
            new() { ValuesByVar = { ["?b"] = "building-ok", ["?h"] = 50m } }, // <= 75 -> Passed
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        // An unresolvable binding must never decay into Passed either.
        Assert.Equal(EvidenceStatus.Unknown, result.Status);
        Assert.False(result.Passed);
        Assert.Empty(result.FailingBindings);
    }

    // --- Phase 1201 plan 02, D-14: ObjectPropertyAtom / UnsupportedAtom / unrecognized atom types
    // must be refused (Unsupported), never silently evaluated as satisfied. ---

    private static Rule RuleWithAtoms(params Atom[] bodyAtoms)
    {
        var rule = new Rule
        {
            Id = "R_TEST_ATOM_DISPATCH",
            Name = "Atom dispatch test rule",
            Description = "Constructed directly for atom-dispatch testing.",
            Kind = "violation",
            Swrl = "placeholder(?x)->placeholderHead(?x,true)",
            Text = "placeholder(?x)->placeholderHead(?x,true)",
            Project = "default-project",
            Graph = "Metagraph",
        };
        foreach (var atom in bodyAtoms)
        {
            rule.BodyAtoms.Add(atom);
        }

        return rule;
    }

    [Fact]
    public void EvaluateRule_ShouldReturnUnsupportedForObjectPropertyAtomEvenWhenFullyBound()
    {
        var evaluator = new RuleEvaluator();
        var atom = new Atom
        {
            Id = "Body_1",
            Type = "ObjectPropertyAtom",
            PredicateIri = "hasAdjacentZone",
            PredicateLabel = "hasAdjacentZone",
        };
        atom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?x" });
        atom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?y" });
        var rule = RuleWithAtoms(atom);

        // Every variable in the atom is fully bound, proving the Unsupported result is driven by
        // atom type, not by a resolution failure.
        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?x"] = "zone1", ["?y"] = "zone2" } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.NotEqual(EvidenceStatus.Passed, result.Status);
        Assert.False(result.Passed);
    }

    [Fact]
    public void EvaluateRule_ShouldReturnUnsupportedForUnsupportedAtomEvenWhenFullyBound()
    {
        var evaluator = new RuleEvaluator();
        var atom = new Atom
        {
            Id = "Body_1",
            Type = "UnsupportedAtom",
            PredicateIri = "someUnclassifiablePredicate",
            PredicateLabel = "someUnclassifiablePredicate",
        };
        atom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?x" });
        var rule = RuleWithAtoms(atom);

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?x"] = "zone1" } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.False(result.Passed);
    }

    [Fact]
    public void EvaluateRule_ShouldReturnUnsupportedForUnrecognizedAtomType()
    {
        var evaluator = new RuleEvaluator();
        var atom = new Atom
        {
            Id = "Body_1",
            Type = "SomeFutureAtomTypeThisEvaluatorDoesNotKnow",
            PredicateIri = "futurePredicate",
            PredicateLabel = "futurePredicate",
        };
        atom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?x" });
        var rule = RuleWithAtoms(atom);

        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?x"] = "zone1" } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.False(result.Passed);
    }

    [Fact]
    public void EvaluateRule_ShouldStillEvaluateClassAtomAndDataPropertyAtomWithFullVariableAvailability()
    {
        var evaluator = new RuleEvaluator();
        var classAtom = new Atom
        {
            Id = "Body_1",
            Type = "ClassAtom",
            PredicateIri = "Building",
            PredicateLabel = "Building",
        };
        classAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });

        var dataPropertyAtom = new Atom
        {
            Id = "Body_2",
            Type = "DataPropertyAtom",
            PredicateIri = "hasHeightM",
            PredicateLabel = "hasHeightM",
        };
        dataPropertyAtom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?b" });
        dataPropertyAtom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Variable, Value = "?h" });

        var rule = RuleWithAtoms(classAtom, dataPropertyAtom);

        // Both atoms' variables resolve, so the variable-availability check applies to them —
        // unchanged from pre-1201 behavior — and a fully-matching body is Failed (violation-pattern
        // inversion), not Unsupported.
        var bindings = new List<BindingRow>
        {
            new() { ValuesByVar = { ["?b"] = "building1", ["?h"] = 80m } },
        };

        var result = evaluator.EvaluateRule(rule, bindings);

        Assert.Equal(EvidenceStatus.Failed, result.Status);
        Assert.False(result.Passed);
        Assert.Single(result.FailingBindings);
    }
}
