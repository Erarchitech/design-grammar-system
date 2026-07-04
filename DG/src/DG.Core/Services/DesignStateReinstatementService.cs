using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Stateless service implementing the reinstatement pre-validation algorithm.
/// Takes a snapshot and resolved targets, returns per-parameter validation result.
/// No Grasshopper dependencies — pure logic.
/// </summary>
public sealed class DesignStateReinstatementService
{
    public ReinstatementResult Validate(
        ParamState snapshot,
        IReadOnlyList<ResolvedTarget> resolvedTargets,
        string? lastAppliedStateId)
    {
        // D-09: StateId guard — same snapshot already applied is a no-op
        if (lastAppliedStateId is not null
            && string.Equals(lastAppliedStateId, snapshot.StateId, StringComparison.Ordinal))
        {
            var unchangedReports = snapshot.Parameters.Select(p => new ReinstatementParameterReport
            {
                ParameterId = p.ParameterId,
                DisplayName = p.DisplayName,
                Status = ReinstatementStatus.Unchanged,
                Detail = "Same StateId already applied",
            }).ToList();

            return new ReinstatementResult
            {
                Applied = false,
                Aborted = false,
                Reports = unchangedReports,
            };
        }

        // Build parameter-to-target map
        var targetMap = resolvedTargets.ToDictionary(t => t.ParameterId, StringComparer.Ordinal);
        var reports = new List<ReinstatementParameterReport>(snapshot.Parameters.Count);
        var hasBlocker = false;

        foreach (var parameter in snapshot.Parameters)
        {
            var report = ValidateParameter(parameter, targetMap);
            reports.Add(report);

            if (report.Status is ReinstatementStatus.MissingTarget
                or ReinstatementStatus.TypeMismatch
                or ReinstatementStatus.AmbiguousTarget
                or ReinstatementStatus.OutOfRange)
            {
                hasBlocker = true;
            }
        }

        // D-06: Atomic decision — if any parameter fails, flip all passing to WouldApply
        if (hasBlocker)
        {
            for (var i = 0; i < reports.Count; i++)
            {
                if (reports[i].Status == ReinstatementStatus.Applied)
                {
                    reports[i] = new ReinstatementParameterReport
                    {
                        ParameterId = reports[i].ParameterId,
                        DisplayName = reports[i].DisplayName,
                        Status = ReinstatementStatus.WouldApply,
                        Detail = "Validation passed but apply aborted by sibling failure",
                    };
                }
            }

            return new ReinstatementResult
            {
                Applied = false,
                Aborted = true,
                Reports = reports,
            };
        }

        // Success path: all parameters pass
        return new ReinstatementResult
        {
            Applied = true,
            Aborted = false,
            Reports = reports,
        };
    }

    private static ReinstatementParameterReport ValidateParameter(
        DesignStateParameter parameter,
        Dictionary<string, ResolvedTarget> targetMap)
    {
        // No matching target in the resolved list
        if (!targetMap.TryGetValue(parameter.ParameterId, out var target))
        {
            return new ReinstatementParameterReport
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Status = ReinstatementStatus.MissingTarget,
                Detail = $"No resolved target for parameter '{parameter.ParameterId}'",
            };
        }

        // Target resolution status checks
        if (target.Resolution == TargetResolutionStatus.Missing)
        {
            return new ReinstatementParameterReport
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Status = ReinstatementStatus.MissingTarget,
                Detail = $"No upstream source connected to DESIGN STATE input '{parameter.ParameterId}'",
            };
        }

        if (target.Resolution == TargetResolutionStatus.Ambiguous)
        {
            return new ReinstatementParameterReport
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Status = ReinstatementStatus.AmbiguousTarget,
                Detail = $"Multiple upstream sources share ParameterId '{parameter.ParameterId}'",
            };
        }

        // Type compatibility check (D-02)
        if (target.TargetType is null || target.TargetType != parameter.Type)
        {
            return new ReinstatementParameterReport
            {
                ParameterId = parameter.ParameterId,
                DisplayName = parameter.DisplayName,
                Status = ReinstatementStatus.TypeMismatch,
                Detail = $"Expected {parameter.Type} but target is {target.TargetType?.ToString() ?? "null"}",
            };
        }

        // Domain bounds check (D-11) — only for Number/Integer with bounded domains
        if (target.DomainMin is not null && target.DomainMax is not null)
        {
            var value = parameter.Type switch
            {
                DesignStateParameterType.Number => parameter.NumberValue,
                DesignStateParameterType.Integer => (double?)parameter.IntegerValue,
                _ => null,
            };

            if (value is not null && (value < target.DomainMin || value > target.DomainMax))
            {
                return new ReinstatementParameterReport
                {
                    ParameterId = parameter.ParameterId,
                    DisplayName = parameter.DisplayName,
                    Status = ReinstatementStatus.OutOfRange,
                    Detail = $"Value {value} outside domain [{target.DomainMin}, {target.DomainMax}]",
                };
            }
        }

        // Passed all checks — tentatively Applied (may be flipped to WouldApply by atomic decision)
        return new ReinstatementParameterReport
        {
            ParameterId = parameter.ParameterId,
            DisplayName = parameter.DisplayName,
            Status = ReinstatementStatus.Applied,
        };
    }
}
