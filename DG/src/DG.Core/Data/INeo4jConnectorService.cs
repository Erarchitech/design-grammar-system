using DG.Core.Models;

namespace DG.Core.Data;

public interface INeo4jConnectorService
{
    Task<ConnectionInfo> TryConnectAsync(ConnectionInfo connection, CancellationToken cancellationToken = default);
}
