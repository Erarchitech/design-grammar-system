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
                StatusMessage = Describe(ex),
            };
        }
    }

    /// <summary>Phase 1303-15: type, message and first frames of the innermost exception, so a load or binding
    /// failure inside a host (Rhino.Inside.Revit) can be diagnosed from the canvas bridge. Never credentials: the
    /// driver's messages carry none and the connection values are not included.</summary>
    internal static string Describe(Exception ex)
    {
        var inner = ex;
        while (inner.InnerException is not null)
        {
            inner = inner.InnerException;
        }

        var frames = (inner.StackTrace ?? string.Empty)
            .Split(new[] { '\n' }, StringSplitOptions.RemoveEmptyEntries)
            .Take(4)
            .Select(f => f.Trim());
        var head = ReferenceEquals(inner, ex) ? string.Empty : $"{ex.GetType().Name} <- ";
        return $"{head}{inner.GetType().FullName}: {inner.Message} | {string.Join(" | ", frames)}";
    }
}
