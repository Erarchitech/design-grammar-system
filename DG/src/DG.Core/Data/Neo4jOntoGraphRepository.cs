using DG.Core.Models;
using Neo4j.Driver;

namespace DG.Core.Data;

public sealed class Neo4jOntoGraphRepository : IOntoGraphRepository
{
    private static readonly TimeSpan QueryTimeout = TimeSpan.FromSeconds(20);

    private const string ClassesQuery = """
        MATCH (c:Class {graph:'OntoGraph', project:$project})
        RETURN c.iri AS iri, c.label AS label
        ORDER BY c.label
        """;

    private const string ObjPropertiesQuery = """
        MATCH (p:ObjProperty {graph:'OntoGraph', project:$project})
        RETURN p.iri AS iri, p.label AS label
        ORDER BY p.label
        """;

    private const string DataPropertiesQuery = """
        MATCH (p:DataProperty {graph:'OntoGraph', project:$project})
        RETURN p.iri AS iri, p.label AS label
        ORDER BY p.label
        """;

    public async Task<IReadOnlyList<OntologyClass>> GetClassesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(
            connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(
            options => options.WithDatabase(connection.Database));

        var cursor = await session
            .RunAsync(ClassesQuery, new { project = connection.Project })
            .WaitAsync(QueryTimeout, cancellationToken);

        var items = new List<OntologyClass>();
        await cursor
            .ForEachAsync(record =>
            {
                items.Add(new OntologyClass
                {
                    Iri = record["iri"].As<string>(),
                    Label = record["label"].As<string>(),
                });
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        return items;
    }

    public async Task<IReadOnlyList<OntologyProperty>> GetObjPropertiesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(
            connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(
            options => options.WithDatabase(connection.Database));

        var cursor = await session
            .RunAsync(ObjPropertiesQuery, new { project = connection.Project })
            .WaitAsync(QueryTimeout, cancellationToken);

        var items = new List<OntologyProperty>();
        await cursor
            .ForEachAsync(record =>
            {
                items.Add(new OntologyProperty
                {
                    Iri = record["iri"].As<string>(),
                    Label = record["label"].As<string>(),
                });
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        return items;
    }

    public async Task<IReadOnlyList<OntologyProperty>> GetDataPropertiesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        await using var driver = GraphDatabase.Driver(
            connection.Uri, AuthTokens.Basic(connection.User, connection.Password));
        await using var session = driver.AsyncSession(
            options => options.WithDatabase(connection.Database));

        var cursor = await session
            .RunAsync(DataPropertiesQuery, new { project = connection.Project })
            .WaitAsync(QueryTimeout, cancellationToken);

        var items = new List<OntologyProperty>();
        await cursor
            .ForEachAsync(record =>
            {
                items.Add(new OntologyProperty
                {
                    Iri = record["iri"].As<string>(),
                    Label = record["label"].As<string>(),
                });
            })
            .WaitAsync(QueryTimeout, cancellationToken);

        return items;
    }
}
