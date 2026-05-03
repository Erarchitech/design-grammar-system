namespace DG.Core.Models;

/// <summary>
/// Deterministic output schema for a single validation run returned by the query service.
/// </summary>
public sealed class ValidationRunQueryResult
{
    /// <summary>Run identifier — stable across queries.</summary>
    public string RunId { get; init; } = string.Empty;

    /// <summary>Project the run belongs to.</summary>
    public string Project { get; init; } = string.Empty;

    /// <summary>UTC timestamp when the run was captured.</summary>
    public DateTimeOffset CapturedAtUtc { get; init; }

    /// <summary>Rule IDs evaluated in this run, sorted deterministically.</summary>
    public IReadOnlyList<string> RuleIds { get; init; } = Array.Empty<string>();

    /// <summary>
    /// Per-rule pass/fail result lines for this run.
    /// Format: "{ruleId}:{passed}" e.g. "R_URB_HEIGHT_MAX_75_V:false".
    /// Empty when no result detail is stored.
    /// </summary>
    public IReadOnlyList<string> Results { get; init; } = Array.Empty<string>();

    /// <summary>
    /// Deserialized design state snapshot attached to this run, or null if none was saved.
    /// </summary>
    public DesignStateSnapshot? State { get; init; }

    /// <summary>
    /// Raw JSON payload of the design state, or null if no state was saved.
    /// Preserved for downstream reinstatement without re-serialization.
    /// </summary>
    public string? StatePayloadJson { get; init; }
}
