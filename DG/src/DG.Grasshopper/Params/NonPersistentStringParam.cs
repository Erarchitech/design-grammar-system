#if GRASSHOPPER_SDK
using GH_IO.Serialization;
using Grasshopper.Kernel.Parameters;

namespace DG.Grasshopper.Params;

/// <summary>
/// A <see cref="Param_String"/> whose persistent (internalised) data is never
/// serialized to the .gh file (Phase 825, SC-6 / v8.2 "no token in .gh").
///
/// Unlike the Phase 824 every-solve scrub — which cleared a typed token on each
/// solve and made the field feel dead — this lets the user type/paste a token
/// and use it for the whole session; the value is only stripped when the document
/// is written to disk. A saved .gh therefore contains no <c>dgc_</c> secret.
/// </summary>
public sealed class NonPersistentStringParam : Param_String
{
    public override Guid ComponentGuid => new("B2D7E4A9-3C61-4F08-9E2A-7C1D5F6083AA");

    public override bool Write(GH_IWriter writer)
    {
        // Strip any internalised value right before serialization so the secret
        // never lands in the .gh. The live in-memory value is dropped too — the
        // user re-pastes if they keep working after a save (an accepted, safe
        // trade vs. leaking a token into a shared/versioned canvas file).
        PersistentData.Clear();
        return base.Write(writer);
    }
}
#endif
