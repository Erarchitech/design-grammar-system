using DG.Core.Contracts;
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Tests;

public sealed class SwrlRuleParserTryParseTests
{
    /// <summary>
    /// A small in-test fake resolver, dictionary-backed, for the ObjectProperty and
    /// DatatypeProperty cases (plan's explicit instruction — not a live Neo4j resolver).
    /// </summary>
    private sealed class FakePredicateKindResolver : IPredicateKindResolver
    {
        private readonly Dictionary<string, PredicateKind> _kinds = new(StringComparer.Ordinal);

        public FakePredicateKindResolver With(string predicateIri, PredicateKind kind)
        {
            _kinds[predicateIri] = kind;
            return this;
        }

        public bool TryGetKind(string predicateIri, out PredicateKind kind) => _kinds.TryGetValue(predicateIri, out kind);
    }

    // --- Task 2: TryParse never throws; typed diagnostics; resolver-driven atom typing ---

    [Fact]
    public void TryParse_EmptyExpression_ReturnsErrorStatusWithOneDiagnostic_DoesNotThrow()
    {
        var result = SwrlRuleParser.TryParse("");

        Assert.Equal(EvidenceStatus.Error, result.Status);
        Assert.Single(result.Diagnostics);
        Assert.Equal(ParseDiagnostic.Codes.EmptyExpression, result.Diagnostics[0].Code);
        Assert.Null(result.Rule);
    }

    [Fact]
    public void TryParse_WhitespaceOnlyExpression_ReturnsErrorStatus_DoesNotThrow()
    {
        var result = SwrlRuleParser.TryParse("   ");

        Assert.Equal(EvidenceStatus.Error, result.Status);
        Assert.Equal(ParseDiagnostic.Codes.EmptyExpression, result.Diagnostics[0].Code);
    }

    [Fact]
    public void TryParse_NullExpression_ReturnsErrorStatus_DoesNotThrow()
    {
        var result = SwrlRuleParser.TryParse(null);

        Assert.Equal(EvidenceStatus.Error, result.Status);
        Assert.Equal(ParseDiagnostic.Codes.EmptyExpression, result.Diagnostics[0].Code);
    }

    [Fact]
    public void TryParse_TwoArrows_ReturnsErrorStatusWithArrowArityDiagnostic_DoesNotThrow()
    {
        const string swrl = "Building(?b)->violates(?b)->another(?b)";
        var result = SwrlRuleParser.TryParse(swrl);

        Assert.Equal(EvidenceStatus.Error, result.Status);
        Assert.Contains(result.Diagnostics, d => d.Code == ParseDiagnostic.Codes.ArrowArity);
        Assert.Null(result.Rule);
    }

    [Fact]
    public void TryParse_UnmatchedAtomText_EmitsUnsupportedAtom_KeepsSurroundingAtoms()
    {
        // "badatom" has no parentheses -- fails the atom regex. Surrounding atoms must survive.
        const string swrl = "Building(?b)^badatom^hasHeightM(?b,?h)->violatesMaxHeight(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        Assert.NotNull(result.Rule);
        Assert.Equal(3, result.Rule!.BodyAtoms.Count);
        Assert.Contains(result.Rule.BodyAtoms, a => a.Type == "UnsupportedAtom");
        Assert.Contains(result.Diagnostics, d => d.Code == ParseDiagnostic.Codes.AtomRegexMiss);
        // The other two body atoms are still present and were not dropped.
        Assert.Contains(result.Rule.BodyAtoms, a => a.PredicateIri == "Building");
        Assert.Contains(result.Rule.BodyAtoms, a => a.PredicateIri == "hasHeightM");
    }

    [Fact]
    public void TryParse_ResolverReportsObjectProperty_ProducesObjectPropertyAtom()
    {
        var resolver = new FakePredicateKindResolver().With("adjacentTo", PredicateKind.ObjectProperty);
        const string swrl = "Building(?a)^adjacentTo(?a,?b)->flagged(?a,true)";

        var result = SwrlRuleParser.TryParse(swrl, resolver);

        var atom = Assert.Single(result.Rule!.BodyAtoms, a => a.PredicateIri == "adjacentTo");
        Assert.Equal("ObjectPropertyAtom", atom.Type);
    }

    [Fact]
    public void TryParse_ResolverReportsDatatypeProperty_ProducesDataPropertyAtom()
    {
        var resolver = new FakePredicateKindResolver().With("hasHeightM", PredicateKind.DatatypeProperty);
        const string swrl = "Building(?b)^hasHeightM(?b,?h)->flagged(?b,true)";

        var result = SwrlRuleParser.TryParse(swrl, resolver);

        var atom = Assert.Single(result.Rule!.BodyAtoms, a => a.PredicateIri == "hasHeightM");
        Assert.Equal("DataPropertyAtom", atom.Type);
    }

    [Fact]
    public void TryParse_NullObjectResolver_TwoArgNonSwrlbPredicate_ProducesUnsupportedAtom_NeverDataPropertyAtom()
    {
        const string swrl = "Building(?b)^hasHeightM(?b,?h)->flagged(?b,true)";

        var result = SwrlRuleParser.TryParse(swrl);

        var atom = Assert.Single(result.Rule!.BodyAtoms, a => a.PredicateIri == "hasHeightM");
        Assert.Equal("UnsupportedAtom", atom.Type);
        Assert.NotEqual("DataPropertyAtom", atom.Type);
        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
        Assert.Contains(result.Diagnostics, d => d.Code == ParseDiagnostic.Codes.UnresolvablePredicateKind);
    }

    [Fact]
    public void TryParse_OneArgNonSwrlbPredicate_ProducesClassAtom_WithoutConsultingResolver()
    {
        // A resolver that would throw/fail on any call proves ClassAtom resolution never consults it.
        var resolver = new FakePredicateKindResolver();
        const string swrl = "Building(?b)->flagged(?b,true)";

        var result = SwrlRuleParser.TryParse(swrl, resolver);

        var atom = Assert.Single(result.Rule!.BodyAtoms);
        Assert.Equal("ClassAtom", atom.Type);
    }

    [Fact]
    public void TryParse_SwrlbPredicate_ProducesBuiltinAtom_WithoutConsultingResolver()
    {
        var resolver = new FakePredicateKindResolver();
        const string swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->flagged(?b,true)";

        var result = SwrlRuleParser.TryParse(swrl, resolver);

        var atom = Assert.Single(result.Rule!.BodyAtoms, a => a.PredicateIri == "swrlb:greaterThan");
        Assert.Equal("BuiltinAtom", atom.Type);
    }

    [Fact]
    public void Parse_ValidExpression_ReturnsSameParsedRuleAsBefore_IncludingVariableOrdering()
    {
        const string swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)";
        var parsed = SwrlRuleParser.Parse(swrl);

        Assert.Equal(3, parsed.BodyAtoms.Count);
        Assert.Single(parsed.HeadAtoms);
        Assert.Equal(2, parsed.Variables.Count);
        Assert.Equal("?b", parsed.Variables[0].Name);
        Assert.Equal("?h", parsed.Variables[1].Name);
    }

    [Fact]
    public void Parse_EmptyExpression_StillThrowsArgumentException()
    {
        var ex = Assert.Throws<ArgumentException>(() => SwrlRuleParser.Parse(""));
        Assert.Equal("swrlExpression", ex.ParamName);
    }

    [Fact]
    public void Parse_TwoArrowExpression_StillThrowsFormatException()
    {
        Assert.Throws<FormatException>(() => SwrlRuleParser.Parse("A(?a)->B(?a)->C(?a)"));
    }

    [Fact]
    public void Parse_UnparseableAtom_StillThrowsFormatException()
    {
        Assert.Throws<FormatException>(() => SwrlRuleParser.Parse("Building(?b)^badatom->flagged(?b,true)"));
    }

    [Fact]
    public void Parse_UnresolvablePredicateKind_DoesNotThrow_ReturnsUnsupportedAtom()
    {
        // Asymmetry: before Phase 1201 this predicate silently became DataPropertyAtom and Parse
        // succeeded. Parse must still succeed today -- but the atom is now UnsupportedAtom.
        const string swrl = "Building(?b)^hasHeightM(?b,?h)->flagged(?b,true)";
        var parsed = SwrlRuleParser.Parse(swrl);

        var atom = Assert.Single(parsed.BodyAtoms, a => a.PredicateIri == "hasHeightM");
        Assert.Equal("UnsupportedAtom", atom.Type);
    }

    // --- Task 3: quoted commas, escaping, unterminated literal, datatype/language literals ---

    [Fact]
    public void TryParse_QuotedLiteralWithEmbeddedComma_SplitsIntoCorrectArgCount_PreservesComma()
    {
        const string swrl = "hasLabel(?b,\"Tower, North\")->flagged(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        var atom = Assert.Single(result.Rule!.BodyAtoms);
        Assert.Equal(2, atom.Args.Count);
        Assert.Equal("Tower, North", atom.Args[1].Value);
    }

    [Fact]
    public void TryParse_BackslashEscapedQuote_DoesNotTerminateLiteral()
    {
        const string swrl = "hasLabel(?b,\"Tower \\\"North\\\"\")->flagged(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        var atom = Assert.Single(result.Rule!.BodyAtoms);
        Assert.Equal(2, atom.Args.Count);
        Assert.Equal("Tower \"North\"", atom.Args[1].Value);
    }

    [Fact]
    public void TryParse_UnterminatedQuotedLiteral_ProducesUnsupportedDiagnostic_NoThrow_NoMisSplit()
    {
        const string swrl = "hasLabel(?b,\"Tower North)->flagged(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        Assert.Contains(result.Diagnostics, d => d.Code == ParseDiagnostic.Codes.UnterminatedQuotedLiteral);
        Assert.Equal(EvidenceStatus.Unsupported, result.Status);
    }

    [Fact]
    public void TryParse_ExplicitDatatypeSuffix_RecordsDatatypeVerbatim_NotReinferred()
    {
        const string swrl = "hasHeightM(?b,\"75.5\"^^xsd:decimal)->flagged(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        var atom = Assert.Single(result.Rule!.BodyAtoms);
        var arg = atom.Args[1];
        Assert.Equal("75.5", arg.Value);
        Assert.Equal("xsd:decimal", arg.Datatype);
    }

    [Fact]
    public void TryParse_LanguageTag_RecordsLanguageAndStringDatatype_NotFallThrough()
    {
        const string swrl = "hasLabel(?b,\"Tower\"@en)->flagged(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        var atom = Assert.Single(result.Rule!.BodyAtoms);
        var arg = atom.Args[1];
        Assert.Equal("Tower", arg.Value);
        Assert.Equal("xsd:string", arg.Datatype);
        Assert.Equal("en", arg.Language);
    }

    [Fact]
    public void TryParse_UnsuffixedLiteralInference_Unchanged_BooleanIntegerDecimalString()
    {
        const string swrl = "hasFlags(?b,true,75,75.5,plain)->flagged(?b,true)";
        var result = SwrlRuleParser.TryParse(swrl);

        var atom = Assert.Single(result.Rule!.BodyAtoms);
        Assert.Equal("xsd:boolean", atom.Args[1].Datatype);
        Assert.Equal("xsd:integer", atom.Args[2].Datatype);
        Assert.Equal("xsd:decimal", atom.Args[3].Datatype);
        Assert.Equal("xsd:string", atom.Args[4].Datatype);
        Assert.Null(atom.Args[4].Language);
    }

    // --- Task 4: Neo4jPredicateKindResolver, constructed from an in-memory snapshot (no live
    // Neo4j required -- the `neo4j` hostname resolves only inside the compose network). ---

    [Fact]
    public void Neo4jPredicateKindResolver_KnownObjectProperty_ResolvesAsObjectProperty()
    {
        var resolver = Neo4jPredicateKindResolver.FromSnapshotForTesting(
            new Dictionary<string, PredicateKind>(StringComparer.Ordinal)
            {
                ["adjacentTo"] = PredicateKind.ObjectProperty,
            });

        Assert.True(resolver.TryGetKind("adjacentTo", out var kind));
        Assert.Equal(PredicateKind.ObjectProperty, kind);
    }

    [Fact]
    public void Neo4jPredicateKindResolver_KnownDatatypeProperty_ResolvesAsDatatypeProperty()
    {
        var resolver = Neo4jPredicateKindResolver.FromSnapshotForTesting(
            new Dictionary<string, PredicateKind>(StringComparer.Ordinal)
            {
                ["hasHeightM"] = PredicateKind.DatatypeProperty,
            });

        Assert.True(resolver.TryGetKind("hasHeightM", out var kind));
        Assert.Equal(PredicateKind.DatatypeProperty, kind);
    }

    [Fact]
    public void Neo4jPredicateKindResolver_AbsentIri_ResolvesAsUnresolvable()
    {
        var resolver = Neo4jPredicateKindResolver.FromSnapshotForTesting(
            new Dictionary<string, PredicateKind>(StringComparer.Ordinal)
            {
                ["hasHeightM"] = PredicateKind.DatatypeProperty,
            });

        Assert.False(resolver.TryGetKind("someUnregisteredPredicate", out _));
    }
}
