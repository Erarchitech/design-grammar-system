namespace DG.Core.Models;

public class DesignState
{
    public string StateId { get; init; } = string.Empty;

    public List<ObjState> ObjStates { get; init; } = new();

    public List<ParamState> ParamStates { get; init; } = new();

    public List<PropState> PropStates { get; init; } = new();

    public DateTimeOffset CapturedAtUtc { get; init; }
}
