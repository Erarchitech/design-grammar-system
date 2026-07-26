namespace DG.Core.Models.Computgraph;

/// <summary>
/// Mirrors dgc:Pattern -- a GH component or small node block; nestable via
/// dgc:patternHostTo. Nesting is modeled as a flat parent-pointer
/// (<see cref="HostPatternId"/>), not a recursive nested List, so arbitrary
/// host-chain depth is representable without unbounded recursion at
/// construction time.
/// </summary>
public class CgPattern
{
    public string Id { get; init; } = string.Empty;

    public string Label { get; init; } = string.Empty;

    public string? Name { get; init; }

    /// <summary>
    /// Id of the host Pattern this Pattern is nested inside (dgc:patternHostTo),
    /// or null when this Pattern is not nested. Flat reference, not a nested List.
    /// </summary>
    public string? HostPatternId { get; init; }

    public List<string> MemberIds { get; init; } = new();

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
    /// Null until assigned; derived from <see cref="Id"/>.
    /// </summary>
    public string? DgId { get; set; }
}
