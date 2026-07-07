namespace DG.Core.Models;

public class PropState
{
    public string StateId { get; init; } = string.Empty;

    public string RuleIri { get; init; } = string.Empty;

    public string DataPropertyIri { get; init; } = string.Empty;

    /// <summary>
    /// Optional reference to the object instance this property value belongs to
    /// (matches an <see cref="ObjState.ObjectRef"/>). When set, the binder applies
    /// this value only to that object's binding row (per-object properties). When
    /// null, the value is broadcast to all object rows (rule-scoped, legacy behavior).
    /// </summary>
    public string? ObjectRef { get; init; }

    public DesignStateParameter? PropValue { get; init; }
}
