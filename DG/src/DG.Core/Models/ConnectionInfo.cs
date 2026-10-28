namespace DG.Core.Models;

public sealed class ConnectionInfo
{
    public string Uri { get; init; } = "bolt://localhost:7687";

    public string User { get; init; } = "neo4j";

    public string Password { get; init; } = string.Empty;

    public string Database { get; init; } = "neo4j";

    public string Project { get; init; } = "default-project";

    /// <summary>
    /// Base URL of a DG data-service whose <c>/connector-graph</c> route serves the graph reads
    /// (Grasshopper server mode: the sign-in answer carried no Neo4j bundle). When set, repositories
    /// read over HTTPS with <see cref="GraphApiToken"/> and never open a Bolt connection.
    /// </summary>
    public string? GraphApiUrl { get; init; }

    /// <summary>The <c>dgk_</c> connector session used as the Bearer for <see cref="GraphApiUrl"/> reads.</summary>
    public string? GraphApiToken { get; init; }

    public bool UsesGraphApi => !string.IsNullOrWhiteSpace(GraphApiUrl);

    public bool IsConnected { get; init; }

    public string StatusMessage { get; init; } = "Not connected";
}
