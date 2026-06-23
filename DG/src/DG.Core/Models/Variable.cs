namespace DG.Core.Models;

public class Variable
{
    public string Name { get; init; } = string.Empty;

    /// <summary>
    /// Not yet populated by the Neo4j-backed pipeline (<see cref="DG.Core.Data.Neo4jRuleRepository"/>'s
    /// PopulateVariables only sets <see cref="Kind"/>). Always null for variables produced by that
    /// path as of Phase 7. Downstream Grasshopper consumers (GhCastingHelpers, MetagraphComponent,
    /// RuleDeconstructComponent) read this field but nothing currently writes it.
    /// </summary>
    public string? InferredDatatype { get; init; }

    public VariableKind? Kind { get; init; }
}
