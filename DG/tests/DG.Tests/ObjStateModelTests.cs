using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class ObjStateModelTests
{
    [Fact]
    public void ObjState_ShouldSetProperties_ThroughInitOnlySetters()
    {
        var now = DateTimeOffset.UtcNow;
        var objState = new ObjState
        {
            StateId = "OS_test123",
            ObjectRef = "building-42",
            Geometry = null,
            Label = "Main Building",
            CapturedAtUtc = now,
        };

        Assert.Equal("OS_test123", objState.StateId);
        Assert.Equal("building-42", objState.ObjectRef);
        Assert.Null(objState.Geometry);
        Assert.Equal("Main Building", objState.Label);
        Assert.Equal(now, objState.CapturedAtUtc);
    }

    [Fact]
    public void ObjState_ShouldHaveEmptyDefaults()
    {
        var objState = new ObjState();

        Assert.Equal("", objState.StateId);
        Assert.Equal("", objState.ObjectRef);
        Assert.Null(objState.Geometry);
        Assert.Null(objState.Label);
    }

    [Fact]
    public void ObjState_Geometry_ShouldBeObjectType()
    {
        // Geometry is typed as object? to accept in-process Rhino/GH handles
        var objState = new ObjState { Geometry = "rhino-guid-1234" };

        Assert.NotNull(objState.Geometry);
        Assert.IsType<string>(objState.Geometry);

        objState = new ObjState { Geometry = 42 };
        Assert.NotNull(objState.Geometry);
        Assert.IsType<int>(objState.Geometry);
    }

    [Fact]
    public void ObjState_Geometry_ShouldAcceptNull()
    {
        var objState = new ObjState { Geometry = null };

        Assert.Null(objState.Geometry);
    }

    // --- Object-vs-Geometry list-length guard: consequence pinning (Phase 1202-11, CR-02) ---
    //
    // NOTE ON SDK TESTABILITY BOUNDARY: ObjectStateComponent.SolveInstance itself is NOT
    // unit-testable from DG.Tests. The component lives entirely inside `#if GRASSHOPPER_SDK`
    // in DG.Grasshopper, which targets net7.0-windows and requires RhinoCommon.dll,
    // Grasshopper.dll, and GH_IO.dll from a Rhino 8 install. DG.Tests targets net9.0 and
    // references DG.Core only — it must not gain a ProjectReference to DG.Grasshopper (that
    // would force a target-framework and Rhino-SDK dependency onto the whole test project).
    // The guard's logic is therefore tested through the DG.Core predicate
    // (ObjStateGuard.IsObjectListLengthMismatch — see the Theory in
    // ErrorMessageTemplateTests.ObjStateGuard_IsObjectListLengthMismatch_MatchesExpectedShape,
    // which this Fact deliberately does not duplicate but cross-references), and the
    // component's call site is verified by `dotnet build DG/DG.sln -c Release` compiling the
    // GRASSHOPPER_SDK branch plus a targeted grep proving it calls the shared predicate rather
    // than re-expressing the condition inline.
    [Fact]
    public void ObjStateGuard_MismatchCasesAreExactlyTheCasesThatWouldMintADegradedObjState()
    {
        // Same predicate, same (5,3)/(5,7)/(5,0)/(5,1)/(5,5) shapes as
        // ErrorMessageTemplateTests.ObjStateGuard_IsObjectListLengthMismatch_MatchesExpectedShape
        // (Task 1) — this Fact is the ObjState-side statement of the identical contract: every
        // shape the predicate flags as a mismatch is a shape where, absent the Task 2 guard,
        // the component's per-item loop would silently mint an ObjState with ClassIri = null
        // and a fallback ObjectRef for the unmatched tail/head indices.
        Assert.True(ObjStateGuard.IsObjectListLengthMismatch(5, 3), "under-supply must be flagged");
        Assert.True(ObjStateGuard.IsObjectListLengthMismatch(5, 7), "over-supply must be flagged");

        Assert.False(ObjStateGuard.IsObjectListLengthMismatch(5, 0), "no Object wired is exempt");
        Assert.False(ObjStateGuard.IsObjectListLengthMismatch(5, 1), "broadcast case is exempt");
        Assert.False(ObjStateGuard.IsObjectListLengthMismatch(5, 5), "matched per-instance is exempt");
    }
}
