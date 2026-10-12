using DG.Core.Models;

namespace DG.Core.Data;

/// <summary>
/// Signs the Grasshopper add-in in with a DG account and obtains a connector
/// session (<c>dgk_</c> token) from data-service (D-35). Replaces the pasted
/// platform token.
/// </summary>
public interface IConnectorSessionClient
{
    /// <summary>
    /// Account login → connector-session mint → best-effort logout. The password is used
    /// only for the login request body; it is never stored or logged.
    /// </summary>
    /// <param name="project">The project to bind the session to, or blank to let the server pick the only eligible one.</param>
    Task<ConnectorSessionResult> SignInAsync(
        string dataServiceUrl,
        string username,
        string password,
        string? project,
        string connectorId = "grasshopper",
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Ends a connector session (<c>DELETE /auth/connector-session</c>). Returns true on 204;
    /// false on any other status or transport failure. Never throws (except caller cancellation).
    /// </summary>
    Task<bool> SignOutAsync(
        string dataServiceUrl,
        string sessionToken,
        CancellationToken cancellationToken = default);
}
