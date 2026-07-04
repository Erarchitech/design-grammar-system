using System.Collections.ObjectModel;

namespace DG.Core.Models;

public class ParamState
{
    public string StateId { get; init; } = string.Empty;

    public DateTimeOffset CapturedAtUtc { get; init; }

    public Collection<DesignStateParameter> Parameters { get; } = new();
}
