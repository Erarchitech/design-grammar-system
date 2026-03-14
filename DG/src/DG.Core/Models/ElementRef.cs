namespace DG.Core.Models;

public class ElementRef
{
    public string DgEntityId { get; init; } = string.Empty;

    public object? Geometry { get; init; }

    public string? DisplayName { get; init; }
}
