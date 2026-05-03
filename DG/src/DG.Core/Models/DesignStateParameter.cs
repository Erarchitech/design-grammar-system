namespace DG.Core.Models;

public enum DesignStateParameterType
{
    Number,
    Integer,
    Boolean,
}

public class DesignStateParameter
{
    public string ParameterId { get; init; } = string.Empty;

    public string DisplayName { get; init; } = string.Empty;

    public DesignStateParameterType Type { get; init; }

    public double? NumberValue { get; init; }

    public long? IntegerValue { get; init; }

    public bool? BooleanValue { get; init; }
}
