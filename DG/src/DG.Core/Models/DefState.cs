using System.Collections.ObjectModel;

namespace DG.Core.Models;

/// <summary>
/// Unused scaffolding for the v3.0 DesignState hierarchy, pending wiring in Phase 9/11
/// (see <see cref="DG.Core.Services.DesignStateIdGenerator"/>). No call sites yet.
/// </summary>
public class DefState
{
    public string StateId { get; init; } = string.Empty;

    public DateTimeOffset CapturedAtUtc { get; init; }

    public Collection<DesignStateParameter> Parameters { get; } = new();
}
