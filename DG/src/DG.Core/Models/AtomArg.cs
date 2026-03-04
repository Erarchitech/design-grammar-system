namespace DG.Core.Models;

public sealed class AtomArg
{
    public int Pos { get; init; }

    public ArgKind Kind { get; init; }

    public string Value { get; init; } = string.Empty;

    public string? Datatype { get; init; }
}
