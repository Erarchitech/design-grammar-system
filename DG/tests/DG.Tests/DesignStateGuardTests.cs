using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

// DESIGN STATE (DG.Grasshopper, inside #if GRASSHOPPER_SDK) rejects a composition when the
// PropState and ObjState list lengths differ. The binder never pairs them by index: a PropState
// with an ObjectRef binds to that object's row, one without is broadcast to every row
// (DesignStateBindingService.ApplyPropertyValues). The length rule therefore only has meaning
// for the legacy unlinked PropStates, and must not block a Design State that carries several
// rules over the same objects (test v12-hexagonal-facade-01, finding F15: 976 PropStates over
// 376 ObjStates, all linked).
public sealed class DesignStateGuardTests
{
    private static PropState Linked(string objectRef) => new() { RuleIri = "R", DataPropertyIri = "ex:p", ObjectRef = objectRef };

    private static PropState Unlinked() => new() { RuleIri = "R", DataPropertyIri = "ex:p" };

    [Fact]
    public void LinkedPropStates_OutnumberingObjStates_AreNotAMismatch()
    {
        // two objects, two rules each -> four PropStates, every one tied to its object
        var props = new[] { Linked("obj_0"), Linked("obj_1"), Linked("obj_0"), Linked("obj_1") };

        Assert.False(DesignStateGuard.IsPropObjCountMismatch(2, props));
    }

    [Fact]
    public void UnlinkedPropStates_WithADifferentCount_RemainAMismatch()
    {
        Assert.True(DesignStateGuard.IsPropObjCountMismatch(2, new[] { Unlinked(), Unlinked(), Unlinked() }));
    }

    [Fact]
    public void UnlinkedPropStates_WithTheSameCount_AreNotAMismatch()
    {
        Assert.False(DesignStateGuard.IsPropObjCountMismatch(2, new[] { Unlinked(), Unlinked() }));
    }

    [Fact]
    public void MixedPropStates_OnlyTheUnlinkedOnesAreCounted()
    {
        var matched = new[] { Linked("obj_0"), Linked("obj_1"), Linked("obj_0"), Unlinked(), Unlinked() };
        var unmatched = new[] { Linked("obj_0"), Linked("obj_1"), Unlinked() };

        Assert.False(DesignStateGuard.IsPropObjCountMismatch(2, matched));
        Assert.True(DesignStateGuard.IsPropObjCountMismatch(2, unmatched));
    }

    [Fact]
    public void MismatchMessage_NamesTheUnlinkedCountAndTheFix()
    {
        var message = ErrorMessageTemplates.DesignStatePropObjCountMismatch(376, 3);

        Assert.Contains("3 PropState(s) without an ObjState link", message);
        Assert.Contains("376", message);
        Assert.Contains("wire PROPERTY STATE's ObjState input", message);
    }

    [Fact]
    public void NoObjStatesOrNoPropStates_IsNeverAMismatch()
    {
        Assert.False(DesignStateGuard.IsPropObjCountMismatch(0, new[] { Unlinked(), Unlinked() }));
        Assert.False(DesignStateGuard.IsPropObjCountMismatch(3, Array.Empty<PropState>()));
    }
}
