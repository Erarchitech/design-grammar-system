using System.Collections.ObjectModel;

namespace DG.Core.Models;

public sealed class Atom
{
    public string Id { get; init; } = string.Empty;

    public string Type { get; init; } = string.Empty;

    public string? PredicateIri { get; init; }

    public string? PredicateLabel { get; init; }

    public AtomSide Side { get; init; }

    public int Order { get; init; }

    public Collection<AtomArg> Args { get; } = new();
}
