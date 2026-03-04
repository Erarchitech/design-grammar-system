namespace DG.Core.Models;

public sealed class ConnectionInfo
{
    public string Uri { get; init; } = "bolt://localhost:7687";

    public string User { get; init; } = "neo4j";

    public string Password { get; init; } = "12345678";

    public string Database { get; init; } = "neo4j";

    public string Project { get; init; } = "default-project";

    public bool IsConnected { get; init; }

    public string StatusMessage { get; init; } = "Not connected";
}
