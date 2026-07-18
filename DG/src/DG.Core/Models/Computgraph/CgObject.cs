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
}
