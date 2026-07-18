namespace DG.Core.Models.Computgraph;

/// <summary>
/// A wire (connection) on the raw canvas. All four endpoints are instance
/// GUIDs -- param instance GUIDs, not param indices, per CONTEXT's
/// "stable under renames" resolution.
/// </summary>
public class CgWire
{
    public string FromNode { get; init; } = string.Empty;

    public string FromParam { get; init; } = string.Empty;

    public string ToNode { get; init; } = string.Empty;

    public string ToParam { get; init; } = string.Empty;
}
