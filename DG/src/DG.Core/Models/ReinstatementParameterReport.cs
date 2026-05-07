namespace DG.Core.Models;

public sealed class ReinstatementParameterReport
{
    public required string ParameterId { get; init; }
    public required string DisplayName { get; init; }
    public required ReinstatementStatus Status { get; init; }
    public string? Detail { get; init; }
}
