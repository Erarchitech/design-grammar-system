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
}
