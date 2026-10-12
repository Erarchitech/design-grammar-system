using DG.Core.Contracts;
using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Builds VALIDATOR's per-ObjState ValidStatus list. Binding rows exist only for ObjStates of
/// the rule's class, so each row is placed by its <see cref="BindingRow.SourceObjStateIndex"/>,
/// never by its position in the binding list (a Design State usually mixes several classes).
/// ObjStates without a binding row get false (D-02: not part of this rule's population).
/// Only a typed Passed outcome projects to true; missing evidence and non-verdicts never do.
/// </summary>
public static class ValidStatusMapper
{
    public static List<bool> PerObjState(
        int objStateCount,
        IReadOnlyList<BindingEvaluationResult>? bindingResults)
    {
        var status = new bool[objStateCount];
        if (bindingResults is null)
            return status.ToList();

        foreach (var outcome in bindingResults)
        {
            var row = outcome.Binding;
            if (row.SourceObjStateIndex is int i && i >= 0 && i < objStateCount)
                status[i] = EvidenceEnvelopeFactory.ToLegacyBoolean(outcome.Status);
        }

        return status.ToList();
    }
}
