using DG.Core.Contracts;
using DG.Core.Models;
using DG.Core.Validation;

namespace DG.Tests;

public sealed class ValidationPublishPackageBuilderTests
{
    [Fact]
    public void Build_ShouldKeepPassAndFailEntitiesPerRuleAndPreferFail()
    {
        var sharedRef = new ElementRef
        {
            DgEntityId = "DG-1",
            DisplayName = "Building 1",
            Geometry = "mesh-data",
        };
        var secondRef = new ElementRef
        {
            DgEntityId = "DG-2",
            DisplayName = "Building 2",
        };
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var passingBinding = new BindingRow();
        passingBinding.ValuesByVar["?b"] = "B1";
        passingBinding.ElementRefsByVar["?b"] = sharedRef;

        var failingBinding = new BindingRow();
        failingBinding.ValuesByVar["?b"] = "B2";
        failingBinding.ElementRefsByVar["?b"] = sharedRef;
        failingBinding.ElementRefsByVar["?b2"] = secondRef;

        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = false,
        };
        result.FailingBindings.Add(failingBinding);

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { passingBinding, failingBinding });

        Assert.Equal("project-a", package.Project);
        Assert.Single(package.RuleResults);
        Assert.Equal(new[] { "DG-1", "DG-2" }, package.RuleResults[0].FailedEntityIds);
        Assert.Empty(package.RuleResults[0].PassedEntityIds);

        Assert.Equal(2, package.Entities.Count);
        var sharedEntity = Assert.Single(package.Entities, entity => entity.DgEntityId == "DG-1");
        Assert.Equal("failed", sharedEntity.OverallStatus);
        Assert.Equal("mesh-data", sharedEntity.Geometry);
        Assert.Equal(new[] { "R_HEIGHT" }, sharedEntity.RuleIds);
        Assert.Equal(new[] { "R_HEIGHT" }, sharedEntity.FailedRuleIds);
        Assert.Empty(sharedEntity.PassedRuleIds);
    }

    [Fact]
    public void Build_ShouldAllowBindingsWithoutElementRefs()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "B1";
        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = true,
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        Assert.Single(package.RuleResults);
        Assert.Empty(package.RuleResults[0].FailedEntityIds);
        Assert.Empty(package.RuleResults[0].PassedEntityIds);
        Assert.Empty(package.Entities);
    }

    [Fact]
    public void Build_ShouldUseBoundVariableValueAsFallbackEntityIdWhenElementRefIdIsMissing()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "building32";
        binding.ElementRefsByVar["?b"] = new ElementRef
        {
            Geometry = "mesh-data",
            DisplayName = "Building 32",
        };

        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = false,
        };
        result.FailingBindings.Add(binding);

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        Assert.Single(package.RuleResults);
        Assert.Equal(new[] { "building32" }, package.RuleResults[0].FailedEntityIds);
        Assert.Empty(package.RuleResults[0].PassedEntityIds);

        var entity = Assert.Single(package.Entities);
        Assert.Equal("building32", entity.DgEntityId);
        Assert.Equal("mesh-data", entity.Geometry);
        Assert.Equal(new[] { "R_HEIGHT" }, entity.RuleIds);
        Assert.Equal(new[] { "R_HEIGHT" }, entity.FailedRuleIds);
    }

    [Fact]
    public void Build_ShouldRejectMixedProjects()
    {
        var rules = new[]
        {
            new Rule { Id = "R1", Project = "project-a" },
            new Rule { Id = "R2", Project = "project-b" },
        };
        var results = new[]
        {
            new RuleEvaluationResult { RuleId = "R1", Passed = true },
            new RuleEvaluationResult { RuleId = "R2", Passed = true },
        };

        var ex = Assert.Throws<InvalidOperationException>(() =>
            ValidationPublishPackageBuilder.Build(rules, results, Array.Empty<BindingRow>()));

        Assert.Contains("single DG project", ex.Message);
    }

    [Fact]
    public void Build_CanonicalPairs_UseOnlyOriginalBindingReferencesAndPreserveLegacyFields()
    {
        var rule = new Rule { Id = "R_PAIR", Project = "project-a" };
        var geometry = new object();
        var passed = PairBinding("OBJ", geometry);
        var unsupported = PairBinding("obj");
        var unrelated = PairBinding("OUTSIDE");
        // Equal scalar values do not make these bindings or object identities interchangeable.
        Assert.Equal(passed.ValuesByVar["?b"], unsupported.ValuesByVar["?b"]);
        var result = new RuleEvaluationResult
        {
            RuleId = rule.Id, Passed = false, Status = EvidenceStatus.Error,
            BindingResults = new[]
            {
                new BindingEvaluationResult(unsupported, EvidenceStatus.Unsupported, "unsupported"),
                new BindingEvaluationResult(unrelated, EvidenceStatus.Error, "not in population"),
                new BindingEvaluationResult(passed, EvidenceStatus.Passed, null),
            },
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule }, new[] { result }, new[] { passed, unsupported });

        Assert.Equal(new[] { "OBJ", "obj" }, package.Entities.Select(e => e.DgEntityId));
        Assert.Equal(EvidenceStatus.Passed, CanonicalStatuses(package.Entities[0])[rule.Id]);
        Assert.Equal(EvidenceStatus.Unsupported, CanonicalStatuses(package.Entities[1])[rule.Id]);
        Assert.Same(geometry, package.Entities[0].Geometry);
        Assert.All(package.Entities, entity =>
        {
            Assert.Equal(new[] { rule.Id }, entity.RuleIds);
            Assert.Equal(new[] { rule.Id }, entity.PassedRuleIds);
            Assert.Empty(entity.FailedRuleIds);
            Assert.Equal("passed", entity.OverallStatus);
            Assert.Equal(entity.RuleIds, CanonicalStatuses(entity).Keys);
        });
        var published = Assert.Single(package.RuleResults);
        Assert.False(published.Passed);
        Assert.Equal(EvidenceStatus.Error, published.Status);
        Assert.Equal(new[] { "OBJ", "obj" }, published.PassedEntityIds);
        Assert.Empty(published.FailedEntityIds);
    }

    [Theory]
    [InlineData(EvidenceStatus.Passed)]
    [InlineData(EvidenceStatus.Failed)]
    [InlineData(EvidenceStatus.Unknown)]
    [InlineData(EvidenceStatus.Unsupported)]
    [InlineData(EvidenceStatus.Error)]
    [InlineData(EvidenceStatus.Indeterminate)]
    [InlineData(EvidenceStatus.NotEvaluated)]
    [InlineData(EvidenceStatus.NoPopulation)]
    public void Build_CanonicalPairs_RepeatedBindingsAndMultiRefsRollUpOncePerExactPair(EvidenceStatus status)
    {
        // Non-evaluator statuses here are deliberately injected transport data.
        var rule = new Rule { Id = "R_PAIR" };
        var shared = PairBinding("SHARED");
        shared.ElementRefsByVar["?duplicate"] = new ElementRef { DgEntityId = "SHARED" };
        shared.ElementRefsByVar["?second"] = new ElementRef { DgEntityId = "SECOND" };
        var sibling = PairBinding("SHARED");
        var separate = PairBinding("SEPARATE");
        var result = new RuleEvaluationResult
        {
            RuleId = rule.Id, Passed = false, Status = EvidenceStatus.Error,
            BindingResults = new[]
            {
                new BindingEvaluationResult(shared, EvidenceStatus.Passed, null),
                new BindingEvaluationResult(shared, status, "repeated association"),
                new BindingEvaluationResult(sibling, EvidenceStatus.Unknown, null),
                new BindingEvaluationResult(separate, EvidenceStatus.Passed, null),
            },
        };
        result.FailingBindings.Add(sibling);

        foreach (var population in new[]
        {
            new[] { shared, sibling, shared, separate },
            new[] { separate, shared, sibling, shared },
        })
        {
            var package = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { result }, population);
            var entities = package.Entities.ToDictionary(e => e.DgEntityId, StringComparer.Ordinal);
            Assert.Equal(3, entities.Count);
            Assert.Equal(StatusRollup.Rollup(new[] { EvidenceStatus.Passed, status, EvidenceStatus.Unknown }),
                CanonicalStatuses(entities["SHARED"])[rule.Id]);
            Assert.Equal(StatusRollup.Rollup(new[] { EvidenceStatus.Passed, status }),
                CanonicalStatuses(entities["SECOND"])[rule.Id]);
            Assert.Equal(EvidenceStatus.Passed, CanonicalStatuses(entities["SEPARATE"])[rule.Id]);
            Assert.All(entities.Values, entity =>
            {
                Assert.Single(CanonicalStatuses(entity));
                Assert.Equal(entity.RuleIds, CanonicalStatuses(entity).Keys);
            });
            Assert.Equal("failed", entities["SHARED"].OverallStatus);
            Assert.Equal(new[] { "SHARED" }, package.RuleResults[0].FailedEntityIds);
            Assert.Equal(new[] { "SECOND", "SEPARATE" }, package.RuleResults[0].PassedEntityIds);
        }
    }

    [Theory]
    [InlineData("null")]
    [InlineData("empty")]
    [InlineData("different-reference")]
    [InlineData("partial")]
    public void Build_CanonicalPairs_UnavailableAssociationIsUnknownNotLegacySuccess(string coverage)
    {
        var rule = new Rule { Id = "R_PAIR" };
        var missing = PairBinding("MISSING");
        var known = PairBinding("KNOWN");
        var lookalike = PairBinding("MISSING");
        IReadOnlyList<BindingEvaluationResult>? outcomes = coverage switch
        {
            "null" => null,
            "empty" => Array.Empty<BindingEvaluationResult>(),
            "different-reference" => new[] { new BindingEvaluationResult(lookalike, EvidenceStatus.Passed, null) },
            _ => new[] { new BindingEvaluationResult(known, EvidenceStatus.Passed, null) },
        };
        var result = new RuleEvaluationResult
        {
            RuleId = rule.Id, Passed = true, Status = EvidenceStatus.Passed, BindingResults = outcomes,
        };
        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule }, new[] { result }, new[] { missing, known });
        Assert.Equal(EvidenceStatus.Unknown,
            CanonicalStatuses(Assert.Single(package.Entities, e => e.DgEntityId == "MISSING"))[rule.Id]);
        Assert.Equal(coverage == "partial" ? EvidenceStatus.Passed : EvidenceStatus.Unknown,
            CanonicalStatuses(Assert.Single(package.Entities, e => e.DgEntityId == "KNOWN"))[rule.Id]);
        Assert.All(package.Entities, e => Assert.Equal("passed", e.OverallStatus));
        Assert.True(package.RuleResults[0].Passed);
    }

    [Fact]
    public void Build_CanonicalPairs_KeepOrdinalRulesSeparateAndUseExistingFallbackIdentity()
    {
        var binding = PairBinding("");
        binding.ValuesByVar["?b"] = "  FALLBACK  ";
        var rules = new[] { new Rule { Id = "R" }, new Rule { Id = "r" } };
        var results = new[]
        {
            new RuleEvaluationResult
            {
                RuleId = "R", Passed = false, Status = EvidenceStatus.Unsupported,
                BindingResults = new[] { new BindingEvaluationResult(binding, EvidenceStatus.Unsupported, null) },
            },
            new RuleEvaluationResult
            {
                RuleId = "r", Passed = true, Status = EvidenceStatus.Passed,
                BindingResults = new[] { new BindingEvaluationResult(binding, EvidenceStatus.Passed, null) },
            },
        };
        var package = ValidationPublishPackageBuilder.Build(rules, results, new[] { binding });
        var entity = Assert.Single(package.Entities);
        Assert.Equal("FALLBACK", entity.DgEntityId);
        Assert.Equal(2, CanonicalStatuses(entity).Count);
        Assert.Equal(EvidenceStatus.Unsupported, CanonicalStatuses(entity)["R"]);
        Assert.Equal(EvidenceStatus.Passed, CanonicalStatuses(entity)["r"]);
        Assert.Equal(entity.RuleIds, CanonicalStatuses(entity).Keys);
        Assert.Equal(new[] { "R", "r" }, entity.PassedRuleIds);
        Assert.Equal("passed", entity.OverallStatus);
    }

    [Theory]
    [InlineData("null")]
    [InlineData("empty")]
    [InlineData("different-reference")]
    [InlineData("partial")]
    public void Build_Diagnostics_UnavailableTypedCoverageIsExplicitAndDoesNotChangeLegacy(string coverage)
    {
        var rule = new Rule { Id = "R" };
        var binding = PairBinding("O");
        var other = PairBinding("OTHER");
        var lookalike = PairBinding("O");
        var outcomes = coverage switch
        {
            "null" => null,
            "empty" => Array.Empty<BindingEvaluationResult>(),
            "different-reference" => new[] { new BindingEvaluationResult(lookalike, EvidenceStatus.Passed, "foreign detail") },
            _ => new[] { new BindingEvaluationResult(other, EvidenceStatus.Passed, "real other detail") },
        };
        var result = new RuleEvaluationResult { RuleId = "R", Passed = true,
            BindingResults = outcomes, Message = "legacy result" };
        var package = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { result }, new[] { binding, other });
        var published = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.Unknown, published.Status);
        Assert.True(published.Passed);
        Assert.Equal(new[] { "O", "OTHER" }, published.PassedEntityIds);
        Assert.Empty(published.FailedEntityIds);
        Assert.Contains("typed_binding_outcome_unavailable", published.Warnings);
        Assert.Contains("legacy result", published.Detail);
        var missing = Assert.Single(package.Entities, e => e.DgEntityId == "O");
        Assert.Equal(new[] { "typed_binding_outcome_unavailable" },
            missing.CanonicalWarnings["R"]);
        var text = missing.CanonicalDetails["R"];
        Assert.False(string.IsNullOrWhiteSpace(text));
        Assert.DoesNotContain("foreign detail", text);
        Assert.DoesNotContain("real other detail", text);
        Assert.All(package.Entities, e => Assert.Equal("passed", e.OverallStatus));
    }

    [Theory]
    [InlineData(EvidenceStatus.Passed)]
    [InlineData(EvidenceStatus.Unsupported)]
    [InlineData(EvidenceStatus.Error)]
    [InlineData(EvidenceStatus.NoPopulation)]
    public void Build_Diagnostics_NullTypedCollectionNeverTrustsRuleEnum(EvidenceStatus legacyStatus)
    {
        var package = ValidationPublishPackageBuilder.Build(new[] { new Rule { Id = "R" } },
            new[] { new RuleEvaluationResult { RuleId = "R", Status = legacyStatus, Passed = false } },
            Array.Empty<BindingRow>());
        Assert.Equal(EvidenceStatus.Unknown, Assert.Single(package.RuleResults).Status);
        Assert.Equal(new[] { "typed_binding_outcome_unavailable" }, package.RuleResults[0].Warnings);
        Assert.False(string.IsNullOrWhiteSpace(package.RuleResults[0].Detail));
        Assert.Empty(package.Entities);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void Build_MissingResult_AssociatesOnlyExplicitPopulationWithoutLegacyLists(bool missingFirst)
    {
        var present = new Rule { Id = "R" };
        var missing = new Rule { Id = "r" };
        var binding = PairBinding("O");
        binding.ElementRefsByVar["?second"] = new ElementRef { DgEntityId = "o" };
        var foreign = PairBinding("FOREIGN");
        var result = new RuleEvaluationResult { RuleId = "R", Passed = true, Status = EvidenceStatus.Passed,
            BindingResults = new[] { new BindingEvaluationResult(binding, EvidenceStatus.Passed, "real"),
                                    new BindingEvaluationResult(foreign, EvidenceStatus.Error, "not supplied") } };
        var package = ValidationPublishPackageBuilder.Build(missingFirst ? new[] { missing, present } : new[] { present, missing },
            new[] { result }, new[] { binding, binding, new BindingRow() });
        Assert.Equal(new[] { "O", "o" }, package.Entities.Select(e => e.DgEntityId));
        Assert.All(package.Entities, entity =>
        {
            Assert.Equal(EvidenceStatus.NotEvaluated, entity.CanonicalStatuses["r"]);
            Assert.Contains("r", entity.RuleIds);
            Assert.Equal(new[] { "R" }, entity.PassedRuleIds);
            Assert.Empty(entity.FailedRuleIds);
            Assert.Equal("passed", entity.OverallStatus);
            Assert.DoesNotContain("not supplied", string.Join("", entity.CanonicalDetails.Values));
        });
        var notEvaluated = Assert.Single(package.RuleResults, r => r.RuleId == "r");
        Assert.Equal(EvidenceStatus.NotEvaluated, notEvaluated.Status);
        Assert.False(notEvaluated.Passed);
        Assert.Empty(notEvaluated.PassedEntityIds);
        Assert.Empty(notEvaluated.FailedEntityIds);
        var missingOnly = ValidationPublishPackageBuilder.Build(new[] { missing }, Array.Empty<RuleEvaluationResult>(), new[] { binding });
        Assert.Equal(2, missingOnly.Entities.Count);
        Assert.All(missingOnly.Entities, e => Assert.Equal("unknown", e.OverallStatus));
    }

    [Fact]
    public void Build_Diagnostics_ActualEvaluatorDetailsAndEmptyVersusNoRefsRemainDistinct()
    {
        var rule = new Rule { Id = "R" };
        rule.BodyAtoms.Add(new Atom { Type = "ObjectPropertyAtom", PredicateLabel = "belongsTo" });
        var binding = PairBinding("O");
        var evaluator = new RuleEvaluator();
        var result = evaluator.EvaluateRule(rule, new[] { binding });
        var package = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { result }, new[] { binding });
        Assert.Equal(result.Message, package.RuleResults[0].Detail);
        Assert.False(string.IsNullOrWhiteSpace(package.RuleResults[0].Detail));
        Assert.Equal(result.BindingResults![0].Detail, package.Entities[0].CanonicalDetails["R"]);
        Assert.False(string.IsNullOrWhiteSpace(package.Entities[0].CanonicalDetails["R"]));
        Assert.Empty(package.Entities[0].CanonicalWarnings["R"]);
        var noRef = new BindingRow();
        var noRefResult = evaluator.EvaluateRule(rule, new[] { noRef });
        var noRefPackage = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { noRefResult }, new[] { noRef });
        Assert.Empty(noRefPackage.Entities);
        Assert.Equal(EvidenceStatus.Unsupported, noRefPackage.RuleResults[0].Status);
        var emptyResult = evaluator.EvaluateRule(rule, Array.Empty<BindingRow>());
        var empty = ValidationPublishPackageBuilder.Build(new[] { rule }, new[] { emptyResult }, Array.Empty<BindingRow>());
        Assert.Empty(empty.Entities);
        Assert.Equal(EvidenceStatus.NoPopulation, empty.RuleResults[0].Status);
        Assert.Empty(empty.RuleResults[0].Warnings);
        var unknownRule = new Rule { Id = "UNKNOWN" };
        var atom = new Atom { Type = "BuiltinAtom", PredicateLabel = "swrlb:greaterThan" };
        atom.Args.Add(new AtomArg { Pos = 1, Kind = ArgKind.Variable, Value = "?missing" });
        atom.Args.Add(new AtomArg { Pos = 2, Kind = ArgKind.Literal, Value = "75", Datatype = "xsd:integer" });
        unknownRule.BodyAtoms.Add(atom);
        var unknownResult = evaluator.EvaluateRule(unknownRule, new[] { binding });
        var unknown = ValidationPublishPackageBuilder.Build(new[] { unknownRule }, new[] { unknownResult }, new[] { binding });
        Assert.Equal(EvidenceStatus.Unknown, unknown.RuleResults[0].Status);
        Assert.Equal(unknownResult.Message, unknown.RuleResults[0].Detail);
        Assert.Equal(unknownResult.BindingResults![0].Detail, unknown.Entities[0].CanonicalDetails["UNKNOWN"]);
        Assert.False(string.IsNullOrWhiteSpace(unknown.Entities[0].CanonicalDetails["UNKNOWN"]));
        Assert.Empty(unknown.RuleResults[0].Warnings); // genuine Unknown is not missing typed evidence
    }

    [Fact]
    public void Build_Diagnostics_DuplicateContributionsDeduplicateDiagnosticsNotOutcomes()
    {
        var binding = PairBinding("O");
        var result = new RuleEvaluationResult { RuleId = "R", Status = EvidenceStatus.Failed,
            Message = "genuine rule message", BindingResults = new[]
            {
                new BindingEvaluationResult(binding, EvidenceStatus.Passed, "one"),
                new BindingEvaluationResult(binding, EvidenceStatus.Failed, "two"),
                new BindingEvaluationResult(binding, EvidenceStatus.Failed, "two"),
            } };
        var package = ValidationPublishPackageBuilder.Build(new[] { new Rule { Id = "R" } }, new[] { result }, new[] { binding, binding });
        var entity = Assert.Single(package.Entities);
        Assert.Equal(EvidenceStatus.Failed, entity.CanonicalStatuses["R"]);
        Assert.Equal("one\ntwo", entity.CanonicalDetails["R"]);
        Assert.Equal(new[] { "typed_binding_outcome_inconsistent" }, entity.CanonicalWarnings["R"]);
        Assert.Equal(new[] { "typed_binding_outcome_inconsistent" }, package.RuleResults[0].Warnings);
        Assert.Equal("genuine rule message", package.RuleResults[0].Detail);
        Assert.Equal(StringComparer.Ordinal, entity.CanonicalWarnings.Comparer);
        Assert.Equal(StringComparer.Ordinal, entity.CanonicalDetails.Comparer);
    }

    private static BindingRow PairBinding(string entityId, object? geometry = null)
    {
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "same-value";
        binding.ElementRefsByVar["?b"] = new ElementRef
        {
            DgEntityId = entityId, Geometry = geometry,
        };
        return binding;
    }

    private static IDictionary<string, EvidenceStatus> CanonicalStatuses(ValidationPublishEntity entity) =>
        entity.CanonicalStatuses;

    // --- Phase 1201 plan 02: the publish boundary carries the evaluator's typed Status. ---

    [Fact]
    public void Build_ShouldPublishNotEvaluatedWhenNoResultExistsForRule()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };

        // No RuleEvaluationResult supplied for R_HEIGHT at all — the rule was in scope but never
        // evaluated (or produced no result).
        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            Array.Empty<RuleEvaluationResult>(),
            Array.Empty<BindingRow>());

        var ruleResult = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.NotEvaluated, ruleResult.Status);
        Assert.False(ruleResult.Passed);
    }

    [Fact]
    public void Build_ShouldCopyResultStatusVerbatimWhenResultExists()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "B1";
        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = true,
            Status = EvidenceStatus.Passed,
            BindingResults = new[] { new BindingEvaluationResult(binding, EvidenceStatus.Passed, null) },
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        var ruleResult = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.Passed, ruleResult.Status);
        Assert.True(ruleResult.Passed);
    }

    [Fact]
    public void Build_ShouldPublishUnsupportedStatusRatherThanDisguisingItAsAViolation()
    {
        var rule = new Rule
        {
            Id = "R_HEIGHT",
            Name = "Height",
            Description = "Max height",
            Project = "project-a",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "B1";

        // An unsupported construct: Passed is false (non-authoritative, per the contract), but
        // Status is Unsupported, not Failed — the evaluator never called this a violation.
        var result = new RuleEvaluationResult
        {
            RuleId = "R_HEIGHT",
            RuleName = "Height",
            RuleDescription = "Max height",
            Passed = false,
            Status = EvidenceStatus.Unsupported,
            BindingResults = new[] { new BindingEvaluationResult(binding, EvidenceStatus.Unsupported, "unsupported") },
        };

        var package = ValidationPublishPackageBuilder.Build(
            new[] { rule },
            new[] { result },
            new[] { binding });

        var ruleResult = Assert.Single(package.RuleResults);
        Assert.Equal(EvidenceStatus.Unsupported, ruleResult.Status);
        Assert.False(ruleResult.Passed);
        // Status is not recomputed from Passed — an Unsupported result must not silently read as
        // Failed just because Passed happens to be false.
        Assert.NotEqual(EvidenceStatus.Failed, ruleResult.Status);
    }
}
