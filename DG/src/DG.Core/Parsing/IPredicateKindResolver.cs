namespace DG.Core.Parsing;

/// <summary>
/// The kind of a predicate IRI in the OntoGraph, as needed to distinguish an
/// <c>ObjectPropertyAtom</c> from a <c>DataPropertyAtom</c> (Phase 1201, D-02).
/// </summary>
public enum PredicateKind
{
    /// <summary>The predicate is an <c>owl:ObjectProperty</c> — relates two individuals.</summary>
    ObjectProperty = 0,

    /// <summary>The predicate is an <c>owl:DatatypeProperty</c> — relates an individual to a literal.</summary>
    DatatypeProperty = 1,
}

/// <summary>
/// Resolves a predicate IRI to its <see cref="PredicateKind"/> so
/// <see cref="SwrlRuleParser.TryParse"/> can distinguish <c>ObjectPropertyAtom</c> from
/// <c>DataPropertyAtom</c> for a ≥2-argument, non-<c>swrlb:</c> predicate, instead of guessing.
///
/// <para>
/// <b>Granularity is bulk-snapshot, never a live per-call round trip.</b>
/// <see cref="DG.Core.Validation.RuleEvaluator.EvaluateRules"/> parses a rule via
/// <see cref="SwrlRuleParser.Parse"/> whenever <c>rule.BodyAtoms</c> is empty, looping over every
/// rule being evaluated — a per-predicate live Neo4j read from inside <see cref="TryGetKind"/>
/// would be N round trips on that exact hot path, the one this phase exists to make safer.
/// Implementations must answer <see cref="TryGetKind"/> synchronously from already-materialized
/// state (e.g. a dictionary loaded once via an async factory), never by opening a connection or
/// awaiting I/O inside the call itself.
/// </para>
/// </summary>
public interface IPredicateKindResolver
{
    /// <summary>
    /// Attempts to resolve <paramref name="predicateIri"/>'s kind from already-materialized state.
    /// Returns <c>false</c> when the predicate is not known to this resolver — callers must treat
    /// that as "unresolvable", never fall back to a guessed kind.
    /// </summary>
    bool TryGetKind(string predicateIri, out PredicateKind kind);
}

/// <summary>
/// The null-object <see cref="IPredicateKindResolver"/>: every predicate is unresolvable.
///
/// <para>
/// This is the whole point of this type, stated bluntly: a parser with no OntoGraph available
/// (unit tests, a caller with no Neo4j connection, or a caller that has not yet loaded a snapshot)
/// must report a predicate's kind as <c>unsupported</c> rather than guessing <c>DataPropertyAtom</c>
/// — guessing is the exact defect Phase 1201's D-02 exists to end. Returning <c>false</c>
/// unconditionally, even for a predicate that "obviously" looks like a datatype property, is
/// correct behavior, not a limitation to work around.
/// </para>
/// </summary>
public sealed class NullPredicateKindResolver : IPredicateKindResolver
{
    /// <summary>The shared singleton instance.</summary>
    public static readonly NullPredicateKindResolver Instance = new();

    private NullPredicateKindResolver()
    {
    }

    /// <inheritdoc />
    public bool TryGetKind(string predicateIri, out PredicateKind kind)
    {
        kind = default;
        return false;
    }
}
