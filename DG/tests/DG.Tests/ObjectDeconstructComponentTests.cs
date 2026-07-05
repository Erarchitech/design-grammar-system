using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class ObjectDeconstructComponentTests
{
    [Fact]
    public void ObjStateWithValues_ReturnsObjectRefGeometryLabel()
    {
        var now = DateTimeOffset.UtcNow;
        var objState = new ObjState
        {
            StateId = "OS_test",
            ObjectRef = "building-42",
            Geometry = "rhino-guid-abc",
            Label = "Main Building",
            CapturedAtUtc = now,
        };

        Assert.Equal("building-42", objState.ObjectRef);
        Assert.Equal("rhino-guid-abc", objState.Geometry);
        Assert.Equal("Main Building", objState.Label);
    }

    [Fact]
    public void ObjStateWithNullGeometryAndLabel_ReturnsEmptyStrings()
    {
        var objState = new ObjState
        {
            StateId = "OS_null",
            ObjectRef = "building-99",
            Geometry = null,
            Label = null,
        };

        Assert.Equal("building-99", objState.ObjectRef);
        Assert.Null(objState.Geometry);
        Assert.Null(objState.Label);
    }

    [Fact]
    public void ObjectDeconstruct_WarningPattern()
    {
        var inputMissing = ErrorMessageTemplates.ObjectDeconstructInputMissing();
        Assert.NotEmpty(inputMissing);
        Assert.Contains("OBJECT DECONSTRUCT", inputMissing);
        Assert.Contains("input is required", inputMissing);

        var castFailed = ErrorMessageTemplates.ObjectDeconstructCastFailed();
        Assert.NotEmpty(castFailed);
        Assert.Contains("OBJECT DECONSTRUCT", castFailed);
        Assert.Contains("Could not unwrap", castFailed);
    }
}
