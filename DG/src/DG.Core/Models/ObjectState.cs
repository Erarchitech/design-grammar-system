using System.Collections.ObjectModel;

namespace DG.Core.Models;

public class ObjectState
{
    public string StateId { get; init; } = string.Empty;

    public string ObjectInstanceId { get; init; } = string.Empty;

    public string VariableName { get; init; } = string.Empty;

    public string ObjectRef { get; init; } = string.Empty;

    public Collection<string> GeoRefs { get; } = new();

    public DateTimeOffset CapturedAtUtc { get; init; }
}
