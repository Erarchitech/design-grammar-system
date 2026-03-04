using DG.Core.Models;

namespace DG.Core.Parsing;

public sealed class ParsedSwrlRule
{
    public string Expression { get; init; } = string.Empty;

    public List<Atom> BodyAtoms { get; } = new();

    public List<Atom> HeadAtoms { get; } = new();

    public List<Variable> Variables { get; } = new();
}
