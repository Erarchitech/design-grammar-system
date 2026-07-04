namespace DG.Core.Models;

public class ObjState
{
    public string StateId { get; init; } = string.Empty;

    public string ObjectRef { get; init; } = string.Empty;

    public object? Geometry { get; init; }

    public string? Label { get; init; }

    public DateTimeOffset CapturedAtUtc { get; init; }
}
