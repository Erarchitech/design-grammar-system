namespace DG.Core.Models.Computgraph;

/// <summary>
/// Mirrors dgc:Procedure -- a GH Group/Cluster (e.g. "11_Proc - 2D Truss Configuration").
/// Index is the NN convention: first digit = algorithm index, rest = procedure ordinal.
/// </summary>
public class CgProcedure
{
    public string Id { get; init; } = string.Empty;

    public int Index { get; init; }

    public string Name { get; init; } = string.Empty;

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

    public List<string> MemberIds { get; init; } = new();

    public List<CgPattern> Patterns { get; init; } = new();

    public List<CgParameter> Parameters { get; init; } = new();

    public List<CgInterface> Interfaces { get; init; } = new();

    /// <summary>
    /// Deterministic DG identity minted by <see cref="DG.Core.Services.CgContextDgIdAssigner"/>.
    /// Null until assigned; derived from <see cref="Id"/>.
    /// </summary>
    public string? DgId { get; set; }
}
