using DG.Core.Models;

namespace DG.Core.Data;

/// <summary>
/// Authenticates a platform credential against data-service's
/// <c>POST /connectors/heartbeat</c> endpoint and reports the outcome.
/// </summary>
public interface IConnectorHeartbeatClient
{
    /// <summary>
    /// Sends a heartbeat for the given platform token to <paramref name="dataServiceUrl"/>.
    /// The token is used only to build the Authorization header; it is never stored or logged.
    /// </summary>
    Task<HeartbeatResult> CheckAsync(string dataServiceUrl, string token, CancellationToken cancellationToken = default);
}
