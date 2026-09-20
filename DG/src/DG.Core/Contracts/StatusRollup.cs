using System;
using System.Collections.Generic;
using System.Linq;

namespace DG.Core.Contracts;

/// <summary>
/// The single, shared roll-up precedence for <see cref="EvidenceStatus"/> (spec/EVIDENCE-CONTRACT.md
/// sections 3/4, Phase 1200 D-06/D-07/D-08, Phase 1201 tracer slice). This is the one place the
/// worst-case-first precedence is declared in C# — <see cref="EvidenceEnvelopeFactory"/> delegates
/// to <see cref="Rollup"/> rather than holding its own copy, and every future caller that needs a
/// rule-level or envelope-level status derived from a set of per-row/per-binding statuses must call
/// through here.
///
/// Mirrored byte-for-byte in <c>data-service/evidence_contract.py::_ROLLUP_PRECEDENCE</c>. The order
/// is normatively owned by <c>spec/EVIDENCE-CONTRACT.md</c>; if it ever looks wrong, that is a
/// finding to raise against the spec, not something to fix locally by editing this list.
/// </summary>
public static class StatusRollup
{
    /// <summary>
    /// The eight statuses in shipped worst-case-first order. Implemented as an explicit ordered
    /// list, walked front-to-back by <see cref="Rollup"/> — never by boolean arithmetic or a
    /// max/min over enum ordinal values, either of which would silently depend on declaration
    /// order rather than this deliberately-authored precedence.
    /// </summary>
    public static readonly IReadOnlyList<EvidenceStatus> Precedence = new[]
    {
        EvidenceStatus.Error,
        EvidenceStatus.Failed,
        EvidenceStatus.Indeterminate,
        EvidenceStatus.Unsupported,
        EvidenceStatus.Unknown,
        EvidenceStatus.NotEvaluated,
        EvidenceStatus.NoPopulation,
        EvidenceStatus.Passed,
    };

    /// <summary>
    /// Rolls up a set of statuses (row-level or per-binding) to the single worst-case status,
    /// walking <see cref="Precedence"/> front-to-back and returning the first member present.
    /// An empty input returns <see cref="EvidenceStatus.NotEvaluated"/> — matching
    /// <see cref="EvidenceEnvelopeFactory"/>'s existing zero-row default: nothing was evaluated,
    /// so this cannot roll up to <see cref="EvidenceStatus.Passed"/>.
    /// </summary>
    public static EvidenceStatus Rollup(IEnumerable<EvidenceStatus> statuses)
    {
        var present = statuses.ToHashSet();

        if (present.Count == 0)
        {
            return EvidenceStatus.NotEvaluated;
        }

        foreach (var candidate in Precedence)
        {
            if (present.Contains(candidate))
            {
                return candidate;
            }
        }

        // Unreachable: Precedence enumerates every EvidenceStatus member, and `present` is
        // non-empty here. If this throws, Precedence is missing an EvidenceStatus member.
        throw new InvalidOperationException("StatusRollup.Rollup: no precedence tier matched a non-empty status set. This indicates Precedence is missing an EvidenceStatus member.");
    }
}
