using DG.Core.Models;
using DG.Core.Parsing;
using Neo4j.Driver;

namespace DG.Core.Data;

/// <summary>
/// OntoGraph-backed <see cref="IPredicateKindResolver"/> (Phase 1201, D-02). Follows the
/// <see cref="IRuleRepository"/>/<see cref="Neo4jRuleRepository"/> split already in this directory:
/// this class is constructed from an already-materialized snapshot, never a live per-call
/// connection.
///
/// <para>
/// Per this plan's bulk-snapshot decision, <see cref="LoadAsync"/> is the only place this type opens
/// a Neo4j connection — one Cypher query reading every <c>ObjectProperty</c> and
/// <c>DatatypeProperty</c> node's <c>iri</c> for the project, run once, up front.
/// <see cref="TryGetKind"/> itself is a synchronous in-memory dictionary lookup, so it never blocks
/// on I/O and can be called freely from <see cref="DG.Core.Validation.RuleEvaluator.EvaluateRules"/>'s
/// per-rule parse loop without incurring N round trips.
/// </para>
///
/// <para>
/// A predicate IRI absent from the loaded snapshot resolves as unresolvable — an honest "I do not
/// know" that <see cref="SwrlRuleParser"/> turns into an <c>UnsupportedAtom</c>, never a guessed
/// kind. This class intentionally has no fallback default kind.
/// </para>
/// </summary>
public sealed class Neo4jPredicateKindResolver : IPredicateKindResolver
{
    private static readonly TimeSpan QueryTimeout = TimeSpan.FromSeconds(20);

    // Scoped by `project` per the repo-wide project-isolation convention (CLAUDE.md § Key Design
    // Decisions): a single Neo4j database with project isolation via a `project` property on every
    // node. A resolver loaded for one project must never answer with another project's predicates.
    private const string PredicateKindQuery = """
        MATCH (p) WHERE (p:ObjectProperty OR p:DatatypeProperty) AND p.project = $project
        RETURN p.iri AS iri, p:ObjectProperty AS isObjectProperty
        """;

    private readonly IReadOnlyDictionary<string, PredicateKind> _kinds;

    private Neo4jPredicateKindResolver(IReadOnlyDictionary<string, PredicateKind> kinds)
    {
        _kinds = kinds;
    }

    /// <summary>
    /// Loads a snapshot of every <c>ObjectProperty</c>/<c>DatatypeProperty</c> predicate IRI for
    /// <paramref name="connection"/>'s project, and returns a resolver that answers
    /// <see cref="TryGetKind"/> from that in-memory snapshot. Call once per parse session, not per
    /// predicate or per rule.
    /// </summary>
    public static async Task<Neo4jPredicateKindResolver> LoadAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));

        var cursor = await session
            .RunAsync(PredicateKindQuery, new { project = connection.Project })
            .WaitAsync(QueryTimeout, cancellationToken);

        var kinds = new Dictionary<string, PredicateKind>(StringComparer.Ordinal);
        await cursor
            .ForEachAsync(record =>
            {
                var iri = record["iri"].As<string?>();
                if (string.IsNullOrWhiteSpace(iri))
                {
                    return;
                }

                var isObjectProperty = record["isObjectProperty"].As<bool>();
                kinds[iri] = isObjectProperty ? PredicateKind.ObjectProperty : PredicateKind.DatatypeProperty;
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        return new Neo4jPredicateKindResolver(kinds);
    }

    /// <summary>
    /// Test-only entry point constructing a resolver directly from an in-memory map, without a live
    /// Neo4j connection. Not part of the public loading contract — production callers must use
    /// <see cref="LoadAsync"/> so the snapshot is genuinely sourced from the OntoGraph.
    /// </summary>
    internal static Neo4jPredicateKindResolver FromSnapshotForTesting(IReadOnlyDictionary<string, PredicateKind> kinds)
        => new(kinds);

    /// <inheritdoc />
    public bool TryGetKind(string predicateIri, out PredicateKind kind)
        // IRIs are case-sensitive identifiers -- StringComparer.Ordinal at construction time
        // (the dictionary above) already enforces this; TryGetValue here inherits that comparer.
        => _kinds.TryGetValue(predicateIri, out kind);
}
