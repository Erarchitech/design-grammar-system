namespace DG.Core.Models;

public sealed class AtomArg
{
    public int Pos { get; init; }

    public ArgKind Kind { get; init; }

    public string Value { get; init; } = string.Empty;

    public string? Datatype { get; init; }

    /// <summary>
    /// The language tag from a SWRL literal written as <c>"text"@en</c> (Phase 1201, Task 3).
    /// Additive-only; defaults to <c>null</c> so every existing construction site is unaffected.
    /// Only ever set alongside <see cref="Datatype"/> <c>"xsd:string"</c> — a language tag never
    /// falls through into <see cref="Value"/>.
    /// </summary>
    public string? Language { get; init; }
}
