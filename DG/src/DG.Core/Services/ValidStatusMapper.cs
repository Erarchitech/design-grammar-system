using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Builds VALIDATOR's per-ObjState ValidStatus list. Binding rows exist only for ObjStates of
/// the rule's class, so each row is placed by its <see cref="BindingRow.SourceObjStateIndex"/>,
/// never by its position in the binding list (a Design State usually mixes several classes).
/// ObjStates without a binding row get false (D-02: not part of this rule's population).
/// </summary>
public static class ValidStatusMapper
{
    public static List<bool> PerObjState(
        int objStateCount,
        IReadOnlyList<BindingRow> bindings,
        IEnumerable<BindingRow> failingBindings)
    {
        var failing = new HashSet<BindingRow>(failingBindings);
        var status = new bool[objStateCount];
        foreach (var row in bindings)
        {
            if (row.SourceObjStateIndex is int i && i >= 0 && i < objStateCount)
                status[i] = !failing.Contains(row);
        }

        return status.ToList();
    }
}
