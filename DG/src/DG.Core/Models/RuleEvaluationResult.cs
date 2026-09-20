namespace DG.Core.Models;

public sealed class RuleEvaluationResult
{
    public string RuleId { get; init; } = string.Empty;

    public string RuleName { get; init; } = string.Empty;

    public string RuleDescription { get; init; } = string.Empty;

    /// <summary>
    /// Retained and non-authoritative (Phase 1200 D-03/D-04, Phase 1201 D-05). Kept for every
    /// existing caller that reads it; the canonical→boolean direction
    /// (<see cref="DG.Core.Contracts.EvidenceEnvelopeFactory.ToLegacyBoolean"/>) is lossy and
    /// defined, but inferring a canonical <see cref="Status"/> from this boolean is undefined and
    /// forbidden — see spec/EVIDENCE-CONTRACT.md section 5. Prefer <see cref="Status"/> for any new
    /// code that needs to distinguish, e.g., an unsupported construct from a genuine violation.
    /// </summary>
    public bool Passed { get; init; }

    /// <summary>
    /// The authoritative rule-level outcome (Phase 1200's frozen 8-member vocabulary, Phase 1201
    /// D-05). Additive alongside <see cref="Passed"/> — this property was introduced by Phase 1201
    /// and every pre-existing reader of <see cref="Passed"/> is unaffected by its presence.
    /// </summary>
    public DG.Core.Contracts.EvidenceStatus Status { get; init; }

    public string Message { get; init; } = string.Empty;

    public List<BindingRow> FailingBindings { get; } = new();
}
