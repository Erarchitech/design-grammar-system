namespace DG.Core.Models.Computgraph;

/// <summary>
/// Mirrors dgc:Interface's disjointUnionOf Input/Output.
/// </summary>
public enum IfaceType
{
    Input,
    Output,
}

/// <summary>
/// Mirrors dgc:Interface -- an inter-procedure connector.
/// </summary>
public class CgInterface
{
    public string Id { get; init; } = string.Empty;

    public string Name { get; init; } = string.Empty;

    public IfaceType IfaceType { get; init; }

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
