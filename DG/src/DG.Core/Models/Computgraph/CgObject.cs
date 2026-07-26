namespace DG.Core.Models.Computgraph;

/// <summary>
/// Mirrors dg:Object (FBS band). Behavior is implicit in v1 -- Object holds
/// Algorithms directly; the envelope collapses the OWL Object/Behavior split.
/// </summary>
public class CgObject
{
    public string Name { get; init; } = string.Empty;

    public string? ClassIri { get; init; }

    public string Source { get; init; } = "tagged";

    /// <summary>
    /// LLM provider that authored this entity when <see cref="Source"/> is <c>"recognized"</c>;
    /// null for hand-tagged entities. Persisted as the Computgraph node's <c>provider</c>
    /// property (Phase 36 UAT F6).
    /// </summary>
    public string? Provider { get; init; }

    /// <summary>Model id behind a recognized entity. See <see cref="Provider"/>.</summary>
    public string? Model { get; init; }

    /// <summary>Recognition confidence (0..1) of a recognized entity. See <see cref="Provider"/>.</summary>
    public double? Confidence { get; init; }

    /// <summary>
    /// Deterministic DG identity minted by <see cref="DG.Core.Services.CgContextDgIdAssigner"/>.
    /// Null until assigned; derived from <c>"obj:"</c> + <see cref="Name"/>.
    /// </summary>
    public string? DgId { get; set; }
}
