namespace DG.Core.Models;

public sealed class BindingRow
{
    public Dictionary<string, object?> ValuesByVar { get; } = new(StringComparer.Ordinal);
}
