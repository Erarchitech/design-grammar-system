namespace DG.Core.Models;

public class DesignState
{
    public string StateId { get; init; } = string.Empty;

    /// <summary>
    /// Human-readable label assigned by the user in DESIGN STATE component.
    /// Surfaces as a tile header in the Model Viewer and as an output of DESIGN STATE DECONSTRUCT.
    /// </summary>
    public string? Label { get; init; }

    public List<ObjState> ObjStates { get; init; } = new();

    public List<ParamState> ParamStates { get; init; } = new();

    public List<PropState> PropStates { get; init; } = new();

    public DateTimeOffset CapturedAtUtc { get; init; }
}
