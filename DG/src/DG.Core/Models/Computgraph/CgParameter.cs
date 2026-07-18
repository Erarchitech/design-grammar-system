namespace DG.Core.Models.Computgraph;

/// <summary>
/// Mirrors dgc:Parameter kinds (dgc:VariableParam / ConstantParam / EmergentParam).
/// Member wording matches CONTEXT.md decision #1, not the OWL individual names.
/// </summary>
public enum ParamKind
{
    Variable,
    Constant,
    Emergent,
}

/// <summary>
/// Mirrors the dgc:ParamDataTypeValue individuals (Float, Integer, Text, Boolean, Geometry).
/// </summary>
public enum ParamDataType
{
    Float,
    Integer,
    Text,
    Boolean,
    Geometry,
}

/// <summary>
/// Numeric slider domain (min/max/step) -- the seam the parser fills from a
/// slider node when inferring a Parameter's dataType/domain.
/// </summary>
public class SliderDomain
{
    public double Min { get; init; }

    public double Max { get; init; }

    public double Step { get; init; }
}

/// <summary>
/// Mirrors dgc:Parameter -- slider/toggle (Variable), fixed preset (Constant),
/// or computed output (Emergent).
/// </summary>
public class CgParameter
{
    public string Id { get; init; } = string.Empty;

    public ParamKind Kind { get; init; }

    public string Name { get; init; } = string.Empty;

    /// <summary>Nullable -- inference from the underlying component may fail.</summary>
    public ParamDataType? DataType { get; init; }

    public SliderDomain? Domain { get; init; }

    public List<string> MemberIds { get; init; } = new();

    public string Source { get; init; } = "tagged";
}
