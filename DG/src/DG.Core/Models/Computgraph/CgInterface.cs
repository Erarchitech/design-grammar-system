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
    /// Deterministic DG identity minted by <see cref="DG.Core.Services.CgContextDgIdAssigner"/>.
    /// Null until assigned; derived from <see cref="Id"/>.
    /// </summary>
    public string? DgId { get; set; }
}
