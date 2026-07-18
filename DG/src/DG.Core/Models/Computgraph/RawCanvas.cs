namespace DG.Core.Models.Computgraph;

/// <summary>
/// Raw canvas group (GH_Group) before classification -- GH-free extractor
/// output. Nesting (a group id inside another group's member list) is
/// captured via <see cref="NestedGroupIds"/> for pattern-nesting detection.
/// </summary>
public class RawGroup
{
    public string Nickname { get; init; } = string.Empty;

    /// <summary>Component instance GUIDs directly owned by this group.</summary>
    public List<string> MemberIds { get; init; } = new();

    /// <summary>Child group ids nested inside this group.</summary>
    public List<string> NestedGroupIds { get; init; } = new();
}

/// <summary>
/// Raw canvas scribble (GH_Scribble) before classification.
/// </summary>
public class RawScribble
{
    public string Text { get; init; } = string.Empty;

    public double[] Position { get; init; } = new double[2];
}

/// <summary>
/// The GH-free shape the DG.Grasshopper extractor produces and the DG.Core
/// parser consumes. Extractor produces RAW structures; classification
/// (tagging into Algorithms/Procedures/Patterns/Parameters/Interfaces)
/// happens in DG.Core, per CONTEXT decision #4.
/// </summary>
public class RawCanvas
{
    public CgDefinition Definition { get; init; } = new();

    public string Project { get; init; } = string.Empty;

    public List<CgNode> Nodes { get; init; } = new();

    public List<CgWire> Wires { get; init; } = new();

    public List<RawGroup> Groups { get; init; } = new();

    public List<RawScribble> Scribbles { get; init; } = new();
}
