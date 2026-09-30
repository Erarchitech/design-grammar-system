using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Validation;

namespace DG.Tests;

public sealed class RuleEvaluatorTests
{
    [Fact]
    public void BindingResults_DistinguishLegacyUnavailableFromEvaluatedEmptyPopulation()
    {
        Assert.Null(new RuleEvaluationResult().BindingResults);
        var result = new RuleEvaluator().EvaluateRule(HeightRule(), Array.Empty<BindingRow>());
        Assert.Equal(EvidenceStatus.NoPopulation, result.Status);
        Assert.False(result.Passed);
        Assert.Empty(result.FailingBindings);
        Assert.NotNull(result.BindingResults);
        Assert.Empty(result.BindingResults);
    }

    [Fact]
    public void BindingResults_PreserveMixedOutcomesIdentityAndLegacyFieldsBeforeRollup()
    {
        var pass = new BindingRow { ValuesByVar = { ["?b"] = "same", ["?h"] = 60m } };
        var equalValuesDifferentReference = new BindingRow { ValuesByVar = { ["?b"] = "same", ["?h"] = 60m } };
        var fail = new BindingRow { ValuesByVar = { ["?b"] = "other", ["?h"] = 80m } };
        var unknown = new BindingRow { ValuesByVar = { ["?b"] = "missing-height" } };
        var bindings = new[] { pass, equalValuesDifferentReference, fail, unknown, pass };
        var result = new RuleEvaluator().EvaluateRule(HeightRule(), bindings);

        Assert.NotNull(result.BindingResults);
        Assert.Equal(new[] { EvidenceStatus.Passed, EvidenceStatus.Passed, EvidenceStatus.Failed,
            EvidenceStatus.Unknown, EvidenceStatus.Passed }, result.BindingResults.Select(r => r.Status));
        for (var i = 0; i < bindings.Length; i++)
            Assert.Same(bindings[i], result.BindingResults[i].Binding);
        Assert.Null(result.BindingResults[0].Detail);
        Assert.Null(result.BindingResults[2].Detail);
        Assert.Contains("?h", result.BindingResults[3].Detail);
        Assert.Equal(new RuleEvaluator().EvaluateRule(HeightRule(), new[] { unknown }).Message,
            result.BindingResults[3].Detail);
        Assert.Equal(EvidenceStatus.Failed, result.Status);
        Assert.False(result.Passed);
        Assert.Equal("Rule violated by 1 binding(s).", result.Message);
        Assert.Same(fail, Assert.Single(result.FailingBindings));
    }

    [Fact]
    public void BindingResults_RetainUnsupportedAndCaughtErrorDetailsWithoutReevaluation()
    {
        var binding = new BindingRow();
        var unsupported = new RuleEvaluator().EvaluateRule(
            RuleWithAtoms(Build("ObjectPropertyAtom", "belongsTo")), new[] { binding });
        Assert.NotNull(unsupported.BindingResults);
        var refusal = Assert.Single(unsupported.BindingResults);
        Assert.Same(binding, refusal.Binding);
        Assert.Equal(EvidenceStatus.Unsupported, refusal.Status);
        Assert.Equal(unsupported.Message, refusal.Detail);
        Assert.Contains("belongsTo", refusal.Detail);
        Assert.Empty(unsupported.FailingBindings);
        Assert.False(unsupported.Passed);

        var value = new CountingFault();
        binding.ValuesByVar["?x"] = value;
        var atom = Build("BuiltinAtom", "swrlb:equal", ("?x", ArgKind.Variable), ("1", ArgKind.Literal));
        var error = new RuleEvaluator().EvaluateRule(RuleWithAtoms(atom), new[] { binding });
        Assert.NotNull(error.BindingResults);
        var fault = Assert.Single(error.BindingResults);
        Assert.Same(binding, fault.Binding);
        Assert.Equal(EvidenceStatus.Error, fault.Status);
        Assert.Equal("binding-fault", fault.Detail);
        Assert.Equal(fault.Detail, error.Message);
        Assert.Equal(EvidenceStatus.Error, error.Status);
        Assert.False(error.Passed);
        Assert.Same(binding, Assert.Single(error.FailingBindings));
        Assert.Equal(1, value.Calls);
    }

    [Fact]
    public void BindingResults_KeepBodyShortCircuitAndParsedUnsupportedIdentity()
    {
        var pass = new BindingRow { ValuesByVar = { ["?h"] = 60m } };
        var rejected = new BindingRow { ValuesByVar = { ["?h"] = 80m } };
        var rule = RuleWithAtoms(GreaterThanBuiltinAtom(), Build("ObjectPropertyAtom", "belongsTo"));
        var result = new RuleEvaluator().EvaluateRule(rule, new[] { pass, rejected });
        Assert.NotNull(result.BindingResults);
        Assert.Equal(EvidenceStatus.Passed, result.BindingResults[0].Status);
        Assert.Null(result.BindingResults[0].Detail);
        Assert.Equal(EvidenceStatus.Unsupported, result.BindingResults[1].Status);
        Assert.Same(rejected, result.BindingResults[1].Binding);
        Assert.Equal(result.Message, result.BindingResults[1].Detail);
        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.Empty(result.FailingBindings);

        var parsed = new RuleEvaluator().EvaluateRule(
            new Rule { Swrl = "unresolved(?x,?y)->Head(?x)" }, new[] { pass, rejected });
        Assert.NotNull(parsed.BindingResults);
        Assert.Equal(2, parsed.BindingResults.Count);
        Assert.All(parsed.BindingResults, r => {
            Assert.Equal(EvidenceStatus.Unsupported, r.Status);
            Assert.Equal(parsed.Message, r.Detail);
        });
        Assert.Same(pass, parsed.BindingResults[0].Binding);
        Assert.Same(rejected, parsed.BindingResults[1].Binding);
    }

    [Theory]
    [InlineData("")]
    [InlineData("no-arrow")]
    [InlineData("malformed->Head(?x)")]
    public void BindingResults_PreserveLegacyThrowingParserBoundary(string swrl)
    {
        var rule = new Rule { Swrl = swrl };
        var before = Record.Exception(() => DG.Core.Parsing.SwrlRuleParser.Parse(swrl));
        var after = Record.Exception(() => new RuleEvaluator().EvaluateRule(rule, new[] { new BindingRow() }));
        Assert.NotNull(before);
        Assert.NotNull(after);
        Assert.Equal(before.GetType(), after.GetType());
        Assert.Equal(before.Message, after.Message);
        var empty = new RuleEvaluator().EvaluateRule(rule, Array.Empty<BindingRow>());
        Assert.Equal(EvidenceStatus.NoPopulation, empty.Status);
        Assert.NotNull(empty.BindingResults);
        Assert.Empty(empty.BindingResults);
    }

    private sealed class CountingFault
    {
        public int Calls { get; private set; }
        public override bool Equals(object? obj)
        {
            Calls++;
            throw new InvalidOperationException("binding-fault");
        }
        public override int GetHashCode() => 0;
    }

    // Phase 1201 plan 03, D-02: these tests used to rely on RuleEvaluator.EvaluateRule's
    // rule.BodyAtoms.Count == 0 fallback silently parsing rule.Swrl via SwrlRuleParser.Parse with
    // no resolver, which used to guess `hasHeightM(?b,?h)` as DataPropertyAtom. After plan 03,
    // SwrlRuleParser.Parse called with no resolver correctly reports an unresolvable ≥2-arg
    // predicate as UnsupportedAtom instead of guessing (the exact defect D-02 exists to end) — so a
    // rule relying on implicit SWRL-text parsing with no resolver injected now evaluates as
    // Unsupported, not Failed/Passed. RuleEvaluator itself has no resolver-injection point (that is
    // out of this plan's file scope — RuleEvaluator.cs belongs to plan 02), so these tests are
    // rewritten to pre-populate rule.BodyAtoms directly (as the file's later D-14 tests already do)
    // rather than depend on implicit, resolver-less SWRL parsing to produce a DataPropertyAtom.
    // This is named explicitly here per the plan's deviation protocol, not quietly edited.

    private static Atom BuildingClassAtom() => Build("ClassAtom", "Building", ("?b", ArgKind.Variable));

    private static Atom HeightDataPropertyAtom() => Build(
        "DataPropertyAtom", "hasHeightM", ("?b", ArgKind.Variable), ("?h", ArgKind.Variable));

    private static Atom GreaterThanBuiltinAtom() => Build(
        "BuiltinAtom", "swrlb:greaterThan", ("?h", ArgKind.Variable), ("75", ArgKind.Literal));

    private static Atom Build(string type, string predicate, params (string Value, ArgKind Kind)[] args)
    {
        var atom = new Atom
        {
            Id = $"Body_{predicate}",
            Type = type,
            PredicateIri = predicate,
            PredicateLabel = predicate,
        };
        var pos = 1;
        foreach (var (value, kind) in args)
        {
            atom.Args.Add(new AtomArg { Pos = pos++, Kind = kind, Value = value, Datatype = kind == ArgKind.Literal ? "xsd:integer" : null });
        }

        return atom;
    }

    [Fact]
    public void EvaluateRule_ShouldFailWhenHeightExceedsLimit()
    {
        var evaluator = new RuleEvaluator();
        var rule = HeightRule();

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
        var rule = HeightRule();

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
        var rule = HeightRule();

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

    private static Rule HeightRule()
    {
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
        rule.BodyAtoms.Add(BuildingClassAtom());
        rule.BodyAtoms.Add(HeightDataPropertyAtom());
        rule.BodyAtoms.Add(GreaterThanBuiltinAtom());
        return rule;
    }

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
