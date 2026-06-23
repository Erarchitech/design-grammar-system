namespace DG.Core.Models;

/// <summary>
/// Unused scaffolding for the v3.0 DesignState hierarchy, pending wiring in Phase 9/11
/// (see <see cref="DG.Core.Services.DesignStateIdGenerator"/>). No call sites yet.
/// </summary>
public class ObjectInstance
{
    public string InstanceId { get; init; } = string.Empty;

    public string ProjectId { get; init; } = string.Empty;

    public string VariableName { get; init; } = string.Empty;

    public DateTimeOffset CreatedAtUtc { get; init; }
}
