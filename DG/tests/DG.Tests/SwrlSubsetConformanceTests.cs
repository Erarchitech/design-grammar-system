using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using DG.Core.Contracts;
using DG.Core.Parsing;
using DG.Core.Validation;

namespace DG.Tests;

/// <summary>
/// Phase 1201 plan 04 (D-13, D-15, D-16): table-driven conformance corpus for
/// <see cref="SwrlRuleParser.TryParse"/>, and the machine-checkable drift guard binding
/// <c>spec/SWRL-SUBSET.md</c>'s documented builtin allow-list and non-claims status list to the
/// production <see cref="SupportedBuiltins"/> constant and <see cref="EvidenceStatusNames"/>
/// vocabulary respectively, so the doc and the code cannot silently drift apart.
/// </summary>
public sealed class SwrlSubsetConformanceTests
{
    /// <summary>
    /// Walks up from the test assembly's output directory to the repo root, matching the
    /// pattern already used by <c>EvidenceContractTests</c>/<c>CanonicalJsonWriterTests</c>, so this
    /// works regardless of build configuration or target framework subfolder.
    /// </summary>
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "spec", "evidence-contract.schema.json")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException(
            $"SwrlSubsetConformanceTests.FindRepoRoot: could not locate repo root (spec/evidence-contract.schema.json) walking up from {AppContext.BaseDirectory}.");
    }

    public sealed class ParserCase
    {
        public string Id { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Expression { get; set; } = string.Empty;
        public Dictionary<string, string> ResolverConfig { get; set; } = new();
        public string ExpectedStatus { get; set; } = string.Empty;
        public List<string>? ExpectedAtomTypes { get; set; }
        public List<string> ExpectedDiagnosticCodes { get; set; } = new();
        public int? ExpectedArgCount { get; set; }
        public string? ExpectedFirstAtomSecondArgValue { get; set; }
        public string? ExpectedFirstAtomSecondArgDatatype { get; set; }
        public string? ExpectedFirstAtomSecondArgLanguage { get; set; }
        public bool ExpectRuleNull { get; set; }
    }

    public sealed class ParserCorpus
    {
        public List<ParserCase> Cases { get; set; } = new();
    }

    private static string CorpusPath()
        => Path.Combine(FindRepoRoot(), "fixtures", "golden", "parser", "cases.json");

    private static ParserCorpus LoadCorpus()
    {
        var text = File.ReadAllText(CorpusPath());
        var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        var corpus = JsonSerializer.Deserialize<ParserCorpus>(text, options);
        return corpus ?? throw new InvalidOperationException("fixtures/golden/parser/cases.json parsed to null.");
    }

    /// <summary>
    /// xunit <c>MemberData</c> source enumerating the corpus file, so adding a case to the JSON
    /// automatically adds a test -- no test-side code change is needed to pick up a new case.
    /// </summary>
    public static IEnumerable<object[]> Cases()
    {
        foreach (var c in LoadCorpus().Cases)
        {
            yield return new object[] { c };
        }
    }

    private sealed class FakePredicateKindResolver : IPredicateKindResolver
    {
        private readonly Dictionary<string, PredicateKind> _kinds;

        public FakePredicateKindResolver(Dictionary<string, PredicateKind> kinds)
        {
            _kinds = kinds;
        }

        public bool TryGetKind(string predicateIri, out PredicateKind kind) => _kinds.TryGetValue(predicateIri, out kind);
    }

    private static IPredicateKindResolver? BuildResolver(ParserCase testCase)
    {
        if (testCase.ResolverConfig.Count == 0)
        {
            // Empty map means the null-object resolver -- do not pass a resolver at all, exercising
            // TryParse's own default rather than an empty FakePredicateKindResolver, so this case also
            // covers "no resolver argument supplied" (the parser's documented default behavior).
            return null;
        }

        var kinds = new Dictionary<string, PredicateKind>(StringComparer.Ordinal);
        foreach (var (predicateIri, kindName) in testCase.ResolverConfig)
        {
            kinds[predicateIri] = kindName switch
            {
                "ObjectProperty" => PredicateKind.ObjectProperty,
                "DatatypeProperty" => PredicateKind.DatatypeProperty,
                _ => throw new InvalidOperationException(
                    $"SwrlSubsetConformanceTests.BuildResolver: unrecognized resolverConfig kind '{kindName}' for predicate '{predicateIri}'."),
            };
        }

        return new FakePredicateKindResolver(kinds);
    }

    [Theory]
    [MemberData(nameof(Cases))]
    public void ParserCase_ProducesExactlyTheDocumentedOutcome(ParserCase testCase)
    {
        var resolver = BuildResolver(testCase);
        var result = resolver is null
            ? SwrlRuleParser.TryParse(testCase.Expression)
            : SwrlRuleParser.TryParse(testCase.Expression, resolver);

        Assert.True(
            EvidenceStatusNames.TryParseWireName(testCase.ExpectedStatus, out var expectedStatus),
            $"Case '{testCase.Id}': expectedStatus '{testCase.ExpectedStatus}' is not a recognized EvidenceStatus wire name.");
        Assert.Equal(expectedStatus, result.Status);

        Assert.Equal(testCase.ExpectedDiagnosticCodes, result.Diagnostics.Select(d => d.Code).ToList());

        if (testCase.ExpectRuleNull)
        {
            Assert.Null(result.Rule);
            return;
        }

        Assert.NotNull(result.Rule);

        if (testCase.ExpectedAtomTypes is not null)
        {
            var actualAtomTypes = result.Rule!.BodyAtoms.Concat(result.Rule.HeadAtoms).Select(a => a.Type).ToList();
            Assert.Equal(testCase.ExpectedAtomTypes, actualAtomTypes);
        }

        if (testCase.ExpectedArgCount is not null)
        {
            var firstAtom = result.Rule!.BodyAtoms.First();
            Assert.Equal(testCase.ExpectedArgCount.Value, firstAtom.Args.Count);
        }

        if (testCase.ExpectedFirstAtomSecondArgValue is not null)
        {
            var firstAtom = result.Rule!.BodyAtoms.First();
            var secondArg = firstAtom.Args.Single(a => a.Pos == 2);
            Assert.Equal(testCase.ExpectedFirstAtomSecondArgValue, secondArg.Value);
        }

        if (testCase.ExpectedFirstAtomSecondArgDatatype is not null)
        {
            var firstAtom = result.Rule!.BodyAtoms.First();
            var secondArg = firstAtom.Args.Single(a => a.Pos == 2);
            Assert.Equal(testCase.ExpectedFirstAtomSecondArgDatatype, secondArg.Datatype);
        }

        if (testCase.ExpectedFirstAtomSecondArgLanguage is not null)
        {
            var firstAtom = result.Rule!.BodyAtoms.First();
            var secondArg = firstAtom.Args.Single(a => a.Pos == 2);
            Assert.Equal(testCase.ExpectedFirstAtomSecondArgLanguage, secondArg.Language);
        }
    }

    /// <summary>
    /// The count guard (Task 1): a case present in cases.json but not executed by the [Theory] above
    /// would otherwise be silently skipped. This asserts the enumerated case count matches the
    /// corpus's own length, making that failure mode impossible.
    /// </summary>
    [Fact]
    public void Corpus_EveryCaseIsExecutedByTheTheoryAbove()
    {
        var corpus = LoadCorpus();
        var executedCount = Cases().Count();

        Assert.Equal(corpus.Cases.Count, executedCount);
        Assert.True(corpus.Cases.Count >= 9, "Expected at least the 8 ROADMAP cases plus the null-resolver ObjectPropertyAtom counterpart (9 total).");
    }

    [Fact]
    public void NoCorpusCaseExpectsAThrownException()
    {
        // Structural guard: every case in the corpus is driven through TryParse (never Parse) by the
        // theory above, and TryParse's contract (D-01) is that it never throws for any input. This
        // fact documents that invariant explicitly rather than leaving it implicit in the theory.
        foreach (var testCase in LoadCorpus().Cases)
        {
            var resolver = BuildResolver(testCase);
            var exception = Record.Exception(() =>
                resolver is null
                    ? SwrlRuleParser.TryParse(testCase.Expression)
                    : SwrlRuleParser.TryParse(testCase.Expression, resolver));

            Assert.Null(exception);
        }
    }

    // --- D-15 drift guard: spec/SWRL-SUBSET.md's machine-readable builtin block vs SupportedBuiltins ---

    private static IReadOnlySet<string> LoadDocumentedBuiltins()
    {
        var specPath = Path.Combine(FindRepoRoot(), "spec", "SWRL-SUBSET.md");
        var text = File.ReadAllText(specPath);

        const string startMarker = "<!-- swrl-subset:supported-builtins:start -->";
        const string endMarker = "<!-- swrl-subset:supported-builtins:end -->";

        var startIndex = text.IndexOf(startMarker, StringComparison.Ordinal);
        var endIndex = text.IndexOf(endMarker, StringComparison.Ordinal);

        if (startIndex < 0 || endIndex < 0 || endIndex <= startIndex)
        {
            throw new InvalidOperationException(
                $"SwrlSubsetConformanceTests.LoadDocumentedBuiltins: could not locate the machine-readable "
                    + $"builtin block between '{startMarker}' and '{endMarker}' in spec/SWRL-SUBSET.md.");
        }

        var block = text.Substring(startIndex + startMarker.Length, endIndex - (startIndex + startMarker.Length));

        // The block is a fenced code block (```) containing one builtin name per line. Strip the
        // fence lines and blank lines, keep everything else verbatim.
        var names = block
            .Split('\n')
            .Select(line => line.Trim())
            .Where(line => line.Length > 0 && !line.StartsWith("```", StringComparison.Ordinal))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        return names;
    }

    [Fact]
    public void DocumentedBuiltins_MatchSupportedBuiltinsConstant_InBothDirections()
    {
        var documented = LoadDocumentedBuiltins();
        var actual = SupportedBuiltins.Names;

        var documentedOnly = documented.Except(actual, StringComparer.OrdinalIgnoreCase).ToList();
        var codeOnly = actual.Except(documented, StringComparer.OrdinalIgnoreCase).ToList();

        Assert.True(
            documentedOnly.Count == 0 && codeOnly.Count == 0,
            "spec/SWRL-SUBSET.md's documented builtin list and DG.Core.Validation.SupportedBuiltins.Names "
                + $"disagree. Documented-but-not-in-code: [{string.Join(", ", documentedOnly)}]. "
                + $"In-code-but-not-documented: [{string.Join(", ", codeOnly)}]. Edit whichever side is "
                + "missing an entry so the two match exactly.");
    }

    // --- D-14 second guard: every status named in the non-claims section is a real EvidenceStatus wire name ---

    private static IReadOnlyList<string> LoadNonClaimsStatuses()
    {
        var specPath = Path.Combine(FindRepoRoot(), "spec", "SWRL-SUBSET.md");
        var text = File.ReadAllText(specPath);

        const string startMarker = "<!-- swrl-subset:non-claims-statuses:start -->";
        const string endMarker = "<!-- swrl-subset:non-claims-statuses:end -->";

        var startIndex = text.IndexOf(startMarker, StringComparison.Ordinal);
        var endIndex = text.IndexOf(endMarker, StringComparison.Ordinal);

        if (startIndex < 0 || endIndex < 0 || endIndex <= startIndex)
        {
            throw new InvalidOperationException(
                $"SwrlSubsetConformanceTests.LoadNonClaimsStatuses: could not locate the machine-readable "
                    + $"non-claims status block between '{startMarker}' and '{endMarker}' in spec/SWRL-SUBSET.md.");
        }

        var block = text.Substring(startIndex + startMarker.Length, endIndex - (startIndex + startMarker.Length));

        return block
            .Split('\n')
            .Select(line => line.Trim())
            .Where(line => line.Length > 0 && !line.StartsWith("```", StringComparison.Ordinal))
            .ToList();
    }

    [Fact]
    public void NonClaimsStatuses_AreAllRealEvidenceStatusWireNames()
    {
        var statuses = LoadNonClaimsStatuses();

        Assert.NotEmpty(statuses);

        foreach (var statusName in statuses)
        {
            Assert.True(
                EvidenceStatusNames.TryParseWireName(statusName, out _),
                $"spec/SWRL-SUBSET.md's non-claims section names status '{statusName}', which is not a "
                    + "member of the frozen EvidenceStatus wire-name vocabulary. A ninth status cannot be "
                    + "introduced by a doc alone.");
        }
    }
}
