using DG.Core.Models;
using Neo4j.Driver;

namespace DG.Core.Data;

public sealed class Neo4jConnectorService : INeo4jConnectorService
{
    private static readonly TimeSpan ConnectionTimeout = TimeSpan.FromSeconds(6);
    private static readonly TimeSpan GraphApiTimeout = TimeSpan.FromSeconds(20);

    public async Task<ConnectionInfo> TryConnectAsync(ConnectionInfo connection, CancellationToken cancellationToken = default)
    {
        if (connection.UsesGraphApi)
        {
            return await TryConnectGraphApiAsync(connection, cancellationToken);
        }

        try
        {
            // Synchronous Dispose, never IAsyncDisposable: inside Rhino.Inside.Revit several hosts load their own
            // Microsoft.Bcl.AsyncInterfaces (Carbon Insights 6.0, Rhino 7.0, Speckle 5.0), Neo4j.Driver binds one of them and
            // DG.Core another, and DisposeAsync through the other IAsyncDisposable throws EntryPointNotFoundException
            // (live 2026-10-21). Dispose() needs no cross-assembly interface.
            using var driver = GraphDatabase.Driver(
                connection.Uri,
                AuthTokens.Basic(connection.User, connection.Password),
                builder => builder.WithConnectionTimeout(ConnectionTimeout));

            await driver.VerifyConnectivityAsync().WaitAsync(ConnectionTimeout, cancellationToken);
            using var session = driver.AsyncSession(options => options.WithDatabase(connection.Database));
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

    /// <summary>
    /// Server mode (no Neo4j bundle): proves the signed-in session can read the project's graph over the
    /// data-service by running the cheapest named query. The message is the safe text of
    /// <see cref="GraphApiException"/>; it never carries the token or the server address.
    /// </summary>
    private static async Task<ConnectionInfo> TryConnectGraphApiAsync(ConnectionInfo connection, CancellationToken cancellationToken)
    {
        string status;
        var connected = false;
        try
        {
            using var session = GraphQuerySession.Open(connection);
            await session.QueryAsync("classes", string.Empty, null, cancellationToken).WaitAsync(GraphApiTimeout, cancellationToken);
            connected = true;
            status = "Connected (DG server)";
        }
        catch (GraphApiException ex)
        {
            status = ex.Message;
        }
        catch (TimeoutException)
        {
            status = "The DG server did not answer in time.";
        }
        catch (OperationCanceledException)
        {
            status = "Connection canceled.";
        }
        catch (Exception ex)
        {
            status = Describe(ex);
        }

        return new ConnectionInfo
        {
            Uri = connection.Uri,
            User = connection.User,
            Database = connection.Database,
            Project = connection.Project,
            GraphApiUrl = connection.GraphApiUrl,
            GraphApiToken = connection.GraphApiToken,
            IsConnected = connected,
            StatusMessage = status,
        };
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
