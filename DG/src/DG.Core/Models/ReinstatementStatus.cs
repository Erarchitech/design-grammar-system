namespace DG.Core.Models;

public enum ReinstatementStatus
{
    Applied,
    MissingTarget,
    TypeMismatch,
    AmbiguousTarget,
    OutOfRange,
    Unchanged,
    WouldApply,
    MissingValue,
}

public static class ReinstatementStatusExtensions
{
    /// <summary>Per-parameter failures that abort the whole reinstate (D-06 atomic abort).</summary>
    public static bool IsBlocking(this ReinstatementStatus status) =>
        status is ReinstatementStatus.MissingTarget
            or ReinstatementStatus.TypeMismatch
            or ReinstatementStatus.AmbiguousTarget
            or ReinstatementStatus.OutOfRange
            or ReinstatementStatus.MissingValue;
}
