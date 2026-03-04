using System.Collections.ObjectModel;

namespace DG.Core.Models;

public class Rule
{
    public string Id { get; init; } = string.Empty;

    public string Name { get; init; } = string.Empty;

    public string Description { get; init; } = string.Empty;

    public string Kind { get; init; } = "violation";

    public string Text { get; init; } = string.Empty;

    public string Swrl { get; init; } = string.Empty;

    public string Project { get; init; } = string.Empty;

    public string Graph { get; init; } = "Metagraph";

    public Collection<Atom> BodyAtoms { get; } = new();

    public Collection<Atom> HeadAtoms { get; } = new();

    public Collection<Variable> Variables { get; } = new();
}
