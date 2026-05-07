namespace DG.Core.Models;

public sealed class ReinstatementResult
{
    public required bool Applied { get; init; }
    public required bool Aborted { get; init; }
    public required IReadOnlyList<ReinstatementParameterReport> Reports { get; init; }

    public int AppliedCount => Reports.Count(r => r.Status == ReinstatementStatus.Applied);
    public int BlockedCount => Reports.Count(r => r.Status is ReinstatementStatus.MissingTarget
        or ReinstatementStatus.TypeMismatch
        or ReinstatementStatus.AmbiguousTarget
        or ReinstatementStatus.OutOfRange);
    public int UnchangedCount => Reports.Count(r => r.Status == ReinstatementStatus.Unchanged);
}
