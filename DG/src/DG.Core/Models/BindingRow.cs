namespace DG.Core.Models;

public sealed class BindingRow
{
    public Dictionary<string, object?> ValuesByVar { get; } = new(StringComparer.Ordinal);

    public Dictionary<string, ElementRef> ElementRefsByVar { get; } = new(StringComparer.Ordinal);

    /// <summary>
    /// Index of the DesignState ObjState this row was built from (null for a property-only
    /// row). Rows exist only for ObjStates of the rule's class, so this — not the row's own
    /// position — maps a row back onto the ObjState list (ValidStatusMapper).
    /// </summary>
    public int? SourceObjStateIndex { get; set; }
}
