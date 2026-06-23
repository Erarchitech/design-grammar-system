namespace DG.Core.Models;

public class ObjectInstance
{
    public string InstanceId { get; init; } = string.Empty;

    public string ProjectId { get; init; } = string.Empty;

    public string VariableName { get; init; } = string.Empty;

    public DateTimeOffset CreatedAtUtc { get; init; }
}
