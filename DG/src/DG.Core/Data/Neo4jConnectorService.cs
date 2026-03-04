using DG.Core.Models;
using Neo4j.Driver;

namespace DG.Core.Data;

public sealed class Neo4jConnectorService : INeo4jConnectorService
{
    private static readonly TimeSpan ConnectionTimeout = TimeSpan.FromSeconds(6);

    public async Task<ConnectionInfo> TryConnectAsync(ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        try
        {
            await using var driver = GraphDatabase.Driver(
                connection.Uri,
                AuthTokens.Basic(connection.User, connection.Password),
                builder => builder.WithConnectionTimeout(ConnectionTimeout));

            await driver.VerifyConnectivityAsync().WaitAsync(ConnectionTimeout, cancellationToken);
            await using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));
            var cursor = await session.RunAsync("RETURN 1 AS ok").WaitAsync(ConnectionTimeout, cancellationToken);
            await cursor.SingleAsync().WaitAsync(ConnectionTimeout, cancellationToken);

            return new ConnectionInfo
            {
                Uri = connection.Uri,
                User = connection.User,
                Password = connection.Password,
                Database = connection.Database,
                Project = connection.Project,
                IsConnected = true,
                StatusMessage = "Connected",
            };
        }
        catch (TimeoutException)
        {
            return new ConnectionInfo
            {
                Uri = connection.Uri,
                User = connection.User,
                Password = connection.Password,
                Database = connection.Database,
                Project = connection.Project,
                IsConnected = false,
                StatusMessage = "Connection timeout. Check URI/port and use bolt://localhost:7687.",
            };
        }
        catch (OperationCanceledException)
        {
            return new ConnectionInfo
            {
                Uri = connection.Uri,
                User = connection.User,
                Password = connection.Password,
                Database = connection.Database,
                Project = connection.Project,
                IsConnected = false,
                StatusMessage = "Connection canceled.",
            };
        }
        catch (Exception ex)
        {
            return new ConnectionInfo
            {
                Uri = connection.Uri,
                User = connection.User,
                Password = connection.Password,
                Database = connection.Database,
                Project = connection.Project,
                IsConnected = false,
                StatusMessage = ex.Message,
            };
        }
    }
}
