using DG.Core.Models;

namespace DG.Core.Services;

/// <summary>
/// Pure, SDK-independent guard predicate for the DESIGN STATE component's ObjState/PropState
/// list-length contract. The component (DG.Grasshopper) is entirely inside
/// <c>#if GRASSHOPPER_SDK</c> and cannot be unit-tested from DG.Tests, so the decision lives
/// here and the component calls it — the same split as <see cref="ObjStateGuard"/>.
///
/// <para>
/// The binder never pairs PropStates with ObjStates by index
/// (<see cref="DesignStateBindingService"/>): a PropState with an <see cref="PropState.ObjectRef"/>
/// binds to that object's row, one without is broadcast to every row. Only the unlinked,
/// legacy PropStates are therefore held to the "one value per object" length rule; linked
/// PropStates may outnumber the ObjStates, which is what a Design State carrying several rules
/// over the same objects looks like.
/// </para>
/// </summary>
public static class DesignStateGuard
{
    /// <summary>
    /// Returns true when the unlinked PropStates (no ObjectRef) do not match the ObjState
    /// count. False when either side is empty.
    /// </summary>
    public static bool IsPropObjCountMismatch(int objStateCount, IReadOnlyCollection<PropState> propStates)
    {
        if (objStateCount == 0 || propStates.Count == 0)
            return false;

        var unlinked = propStates.Count(p => string.IsNullOrWhiteSpace(p.ObjectRef));
        return unlinked > 0 && unlinked != objStateCount;
    }
}
