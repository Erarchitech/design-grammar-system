namespace DG.Core.Models;

/// <summary>
/// Outcome of a platform heartbeat check against data-service.
/// </summary>
public enum HeartbeatOutcome
{
    /// <summary>No value supplied — the heartbeat was not attempted.</summary>
    NotAttempted,

    /// <summary>data-service accepted the value (HTTP 200).</summary>
    Authenticated,

    /// <summary>Rejected by data-service (HTTP 401, or a value without the dgc_ shape).</summary>
    Rejected,

    /// <summary>data-service could not be reached (network error, timeout, or unexpected status).</summary>
    Unreachable,
}

/// <summary>
/// Result of a platform heartbeat. Holds the outcome, the derived connector
/// status (active/stale/never_connected), and — on success (Phase 825) — the
/// <see cref="ConnectionBundle"/> the token unlocks. It carries no sensitive
/// input value (never the token), so it can never leak the secret through a
/// serialized or returned object.
/// </summary>
public readonly record struct HeartbeatResult(
    HeartbeatOutcome Outcome,
    string? Status,
    ConnectionBundle? Bundle = null)
{
    /// <summary>A heartbeat that was never attempted (no value supplied).</summary>
    public static HeartbeatResult NotAttempted { get; } = new(HeartbeatOutcome.NotAttempted, null);
}
