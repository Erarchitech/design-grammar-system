using System.Text;

namespace DG.Core.Models;

/// <summary>
/// Outcome of an account sign-in that mints a connector session (D-35).
/// </summary>
public enum ConnectorSessionOutcome
{
    /// <summary>Nothing to do — username or password was blank, no request was sent.</summary>
    NotAttempted,

    /// <summary>Login and connector-session mint succeeded (HTTP 201); a <c>dgk_</c> session was issued.</summary>
    SignedIn,

    /// <summary>The account credentials were rejected (login HTTP 401).</summary>
    Rejected,

    /// <summary>The account is not allowed to mint a connector session (HTTP 403, see <c>ServerCode</c>).</summary>
    Forbidden,

    /// <summary>The server needs a project to be named (HTTP 422); <c>ServerMessage</c> carries the hint.</summary>
    ProjectRequired,

    /// <summary>The login endpoint throttled the attempt (HTTP 429).</summary>
    Throttled,

    /// <summary>Plain http to a non-loopback host — refused before any request was sent.</summary>
    InsecureTransport,

    /// <summary>data-service could not be reached (network error, timeout, or unexpected status).</summary>
    Unreachable,
}

/// <summary>
/// Result of <c>IConnectorSessionClient.SignInAsync</c>. Never carries the account
/// password. It does carry the <c>dgk_</c> session token on success, so
/// <see cref="ToString"/> / the record's printed form redact it.
/// </summary>
public sealed record ConnectorSessionResult(
    ConnectorSessionOutcome Outcome,
    string? Project = null,
    ConnectionBundle? Bundle = null,
    string? SessionToken = null,
    DateTimeOffset? ExpiresAt = null,
    string? ServerCode = null,
    string? ServerMessage = null)
{
    /// <summary>A sign-in that was never attempted (blank credentials).</summary>
    public static ConnectorSessionResult NotAttempted { get; } = new(ConnectorSessionOutcome.NotAttempted);

    // Deliberately omits Bundle (carries the Neo4j password) and prints the token as <redacted>.
    private bool PrintMembers(StringBuilder builder)
    {
        builder.Append("Outcome = ").Append(Outcome);
        builder.Append(", Project = ").Append(Project);
        builder.Append(", ExpiresAt = ").Append(ExpiresAt);
        builder.Append(", ServerCode = ").Append(ServerCode);
        if (!string.IsNullOrEmpty(SessionToken))
        {
            builder.Append(", SessionToken = <redacted>");
        }

        if (Bundle is not null)
        {
            builder.Append(", Bundle = <redacted>");
        }

        return true;
    }
}
