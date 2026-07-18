namespace DG.Core.Models.Computgraph;

/// <summary>
/// Mirrors dgc:Algorithm -- the whole GH definition (e.g. "1_ALGORITHM").
/// </summary>
public class CgAlgorithm
{
    public int Index { get; init; }

    public string Name { get; init; } = string.Empty;

    public List<CgProcedure> Procedures { get; init; } = new();
}
