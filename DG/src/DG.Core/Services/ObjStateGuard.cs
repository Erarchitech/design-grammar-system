namespace DG.Core.Services;

/// <summary>
/// Pure, SDK-independent guard predicates for the OBJECT STATE component's list-length
/// contract (Phase 1202-11, closing REVIEW CR-02 / 1202-VERIFICATION.md gap 2).
///
/// <para>
/// <see cref="ObjectStateComponent"/> (DG.Grasshopper) is entirely inside
/// <c>#if GRASSHOPPER_SDK</c> and cannot be unit-tested from DG.Tests (net9.0, DG.Core-only,
/// no Rhino/Grasshopper SDK). The Object-vs-Geometry list-length decision is therefore
/// factored out here as a pure function over two integers, so DG.Tests can assert every exempt
/// and non-exempt case directly, and the component calls this predicate rather than
/// re-expressing the condition inline — keeping the tested logic and the shipped logic from
/// drifting apart.
/// </para>
/// </summary>
public static class ObjStateGuard
{
    /// <summary>
    /// Returns true when the Object input's list length is a mismatch against the Geometry
    /// list length driving OBJECT STATE's output — i.e. when emitting an ObjState per geometry
    /// index would require silently degrading the Object side (null ClassIri, fallback
    /// ObjectRef) for the indices past the wired Object list's end or ignored past its start.
    ///
    /// <para>Three counts are exempt (return false) — not mismatches:</para>
    /// <list type="bullet">
    /// <item><c>objectCount == 0</c> — Object is a registered-Optional input
    /// (<c>pManager[0].Optional = true</c>); the no-Object path is documented, deliberate
    /// behavior, not an error.</item>
    /// <item><c>objectCount == 1</c> — the deliberate ontology-class broadcast case: a single
    /// OntologyClass's IRI is fanned out to every geometry instance, per the component's own
    /// doc-comment and <c>RegisterInputParams</c> description.</item>
    /// <item><c>objectCount == geometryCount</c> — the matched per-instance identity path: one
    /// Object entry per geometry item, index-aligned.</item>
    /// </list>
    /// <para>
    /// Every other count — including over-supply (<c>objectCount &gt; geometryCount</c>, where
    /// the per-item loop would silently ignore the extra entries) — is a mismatch.
    /// </para>
    /// </summary>
    public static bool IsObjectListLengthMismatch(int geometryCount, int objectCount)
    {
        return objectCount != 0 && objectCount != 1 && objectCount != geometryCount;
    }
}
