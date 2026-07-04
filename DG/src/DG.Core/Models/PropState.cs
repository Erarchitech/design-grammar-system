namespace DG.Core.Models;

public class PropState
{
    public string StateId { get; init; } = string.Empty;

    public string RuleIri { get; init; } = string.Empty;

    public string DataPropertyIri { get; init; } = string.Empty;

    public DesignStateParameter? PropValue { get; init; }
}
