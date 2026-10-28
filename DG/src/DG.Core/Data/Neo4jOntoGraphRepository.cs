using DG.Core.Models;

namespace DG.Core.Data;

public sealed class Neo4jOntoGraphRepository : IOntoGraphRepository
{
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
        using var session = GraphQuerySession.Open(connection);
        var rows = await session.QueryAsync("classes", ClassesQuery, null, cancellationToken);
        return rows
            .Select(record => new OntologyClass { Iri = record.GetString("iri")!, Label = record.GetString("label")! })
            .ToList();
    }

    public async Task<IReadOnlyList<OntologyProperty>> GetObjPropertiesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        using var session = GraphQuerySession.Open(connection);
        var rows = await session.QueryAsync("objProperties", ObjPropertiesQuery, null, cancellationToken);
        return rows
            .Select(record => new OntologyProperty { Iri = record.GetString("iri")!, Label = record.GetString("label")! })
            .ToList();
    }

    public async Task<IReadOnlyList<OntologyProperty>> GetDataPropertiesAsync(
        ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        using var session = GraphQuerySession.Open(connection);
        var rows = await session.QueryAsync("dataProperties", DataPropertiesQuery, null, cancellationToken);
        return rows
            .Select(record => new OntologyProperty { Iri = record.GetString("iri")!, Label = record.GetString("label")! })
            .ToList();
    }
}
