namespace DG.Core.Models;

public sealed class ValidationPublishRuleResult
{
    public string RuleId { get; init; } = string.Empty;

    /// <summary>
    /// Retained and non-authoritative (Phase 1200 D-03/D-04, Phase 1201 D-05, applied to the
    /// publish boundary by plan 02). Kept for every existing caller that reads it; the
    /// canonical→boolean direction (<see cref="DG.Core.Contracts.EvidenceEnvelopeFactory.ToLegacyBoolean"/>)
    /// is lossy and defined, but inferring a canonical <see cref="Status"/> from this boolean is
    /// undefined and forbidden — see spec/EVIDENCE-CONTRACT.md section 5. Prefer <see cref="Status"/>
    /// for any new code that needs to distinguish, e.g., an unsupported construct or a never-evaluated
    /// rule from a genuine violation.
    /// </summary>
    public bool Passed { get; init; }

    /// <summary>
    /// The authoritative rule-level outcome carried across the publish boundary (Phase 1201 plan 02).
    /// Additive alongside <see cref="Passed"/>. Copied verbatim from
    /// <see cref="RuleEvaluationResult.Status"/> when a result exists for the rule; set to
    /// <see cref="DG.Core.Contracts.EvidenceStatus.NotEvaluated"/> when no result exists (the rule
    /// was in scope but no evaluation was ever attempted or no result was produced) — never
    /// recomputed from <see cref="Passed"/>.
    /// </summary>
    public DG.Core.Contracts.EvidenceStatus Status { get; init; }

    public List<string> FailedEntityIds { get; } = new();

    public List<string> PassedEntityIds { get; } = new();
}
