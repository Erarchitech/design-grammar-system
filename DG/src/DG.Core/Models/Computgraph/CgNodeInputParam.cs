namespace DG.Core.Models.Computgraph;

/// <summary>
/// One input param slot on a raw canvas component -- exists to make JOIN A
/// resolvable. <see cref="CgWire.ToParam"/> carries only an instance GUID,
/// and the owning <see cref="CgNode.Nickname"/> is the component's own
/// nickname, not the input's -- so without this the Computgraph cannot know
/// what a given input is called.
/// </summary>
public class CgNodeInputParam
{
    /// <summary>The input param's own instance GUID -- the value that appears as <see cref="CgWire.ToParam"/>.</summary>
    public string InstanceId { get; init; } = string.Empty;

    /// <summary>IGH_Param.NickName -- the string PARAMETER STATE uses as its ParameterId.</summary>
    public string Nickname { get; init; } = string.Empty;

    /// <summary>IGH_Param.Name -- the display-name fallback.</summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>Zero-based position in Params.Input, so a NickName-less param can still be matched to the param_{i} fallback.</summary>
    public int Index { get; init; }
}
