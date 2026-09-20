using DG.Core.Contracts;

namespace DG.Core.Parsing;

/// <summary>
/// A single typed diagnostic produced while parsing a SWRL expression via
/// <see cref="SwrlRuleParser.TryParse"/>. Carries a stable machine-readable
/// <see cref="Code"/> (see <see cref="Codes"/>), a human-readable <see cref="Message"/> following
/// the What+Where+How-to-fix wording pattern from
/// <see cref="DG.Core.Services.ErrorMessageTemplates"/>, a zero-based character <see cref="Offset"/>
/// into the original expression (or -1 when the diagnostic is not positional), and the
/// <see cref="EvidenceStatus"/> this diagnostic implies for roll-up via
/// <see cref="DG.Core.Contracts.StatusRollup"/>.
/// </summary>
/// <param name="Code">A stable short identifier from <see cref="Codes"/> — not a localized string,
/// safe for callers to switch on.</param>
/// <param name="Message">A human-readable What+Where+How-to-fix message.</param>
/// <param name="Offset">Zero-based index into the original SWRL expression where the diagnostic
/// applies, or -1 when the diagnostic is not positional (e.g. an empty-expression diagnostic has
/// no meaningful offset).</param>
/// <param name="Status">The <see cref="EvidenceStatus"/> this diagnostic implies.</param>
public sealed record ParseDiagnostic(string Code, string Message, int Offset, EvidenceStatus Status)
{
    /// <summary>
    /// The stable diagnostic code set. Tests and future callers should reference these symbols
    /// rather than string literals.
    /// </summary>
    public static class Codes
    {
        /// <summary>The SWRL expression was null, empty, or whitespace-only.</summary>
        public const string EmptyExpression = "empty-expression";

        /// <summary>The expression did not contain exactly one '->' separating body from head.</summary>
        public const string ArrowArity = "arrow-arity";

        /// <summary>An atom's text did not match the atom regex (predicate(args) shape).</summary>
        public const string AtomRegexMiss = "atom-regex-miss";

        /// <summary>A ≥2-arg, non-swrlb: predicate's kind could not be resolved against the
        /// OntoGraph (no resolver, or the resolver reported it unresolvable).</summary>
        public const string UnresolvablePredicateKind = "unresolvable-predicate-kind";

        /// <summary>A quoted literal in an atom's argument list was never terminated.</summary>
        public const string UnterminatedQuotedLiteral = "unterminated-quoted-literal";
    }
}
