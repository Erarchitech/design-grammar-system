namespace DG.Core.Models;

public sealed record ResolvedTarget(
    string ParameterId,
    TargetResolutionStatus Resolution,
    DesignStateParameterType? TargetType,
    double? DomainMin,
    double? DomainMax);

public enum TargetResolutionStatus
{
    Resolved,
    Missing,
    Ambiguous,
}
