using System.Collections.ObjectModel;

namespace DG.Core.Models;

/// <summary>
/// Unused scaffolding for the v3.0 DesignState hierarchy, pending wiring in Phase 9/11
/// (see <see cref="DG.Core.Services.DesignStateIdGenerator"/>). No call sites yet.
/// </summary>
public class ObjectState
{
    public string StateId { get; init; } = string.Empty;

    public string ObjectInstanceId { get; init; } = string.Empty;

    public string VariableName { get; init; } = string.Empty;

    public string ObjectRef { get; init; } = string.Empty;

    public Collection<string> GeoRefs { get; } = new();

    public DateTimeOffset CapturedAtUtc { get; init; }
}
