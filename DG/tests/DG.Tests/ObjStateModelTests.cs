using DG.Core.Models;

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
}
