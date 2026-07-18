namespace DG.Core.Models.Computgraph;

/// <summary>
/// Raw canvas component -- the untyped substrate every tagged entity
/// references by member ids (instance GUIDs). Position order is [x, y].
/// </summary>
public class CgNode
{
    public string InstanceId { get; init; } = string.Empty;

    public string ComponentGuid { get; init; } = string.Empty;

    public string Name { get; init; } = string.Empty;

    public string Nickname { get; init; } = string.Empty;

    public double[] Position { get; init; } = new double[2];

    /// <summary>Slider domain metadata, present only when this node is a number slider.</summary>
    public SliderDomain? Slider { get; init; }

    public bool IsIntegerSlider { get; init; }
}
