using DG.Core.Models;

namespace DG.Core.Classification;

public sealed class ClassificationResult
{
    public List<BindingRow> BoundVariables { get; } = new();

    public List<string> MissingVariables { get; } = new();

    public string Status { get; init; } = string.Empty;
}
