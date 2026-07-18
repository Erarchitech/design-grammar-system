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

    public List<string> MemberIds { get; init; } = new();

    public List<CgPattern> Patterns { get; init; } = new();

    public List<CgParameter> Parameters { get; init; } = new();

    public List<CgInterface> Interfaces { get; init; } = new();
}
