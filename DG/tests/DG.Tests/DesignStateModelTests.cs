using DG.Core.Models;

namespace DG.Tests;

public sealed class DesignStateModelTests
{
    [Fact]
    public void DesignState_ShouldSetProperties_ThroughInitOnlySetters()
    {
        var now = DateTimeOffset.UtcNow;
        var designState = new DesignState
        {
            StateId = "DS_design1",
            CapturedAtUtc = now,
        };

        Assert.Equal("DS_design1", designState.StateId);
        Assert.Equal(now, designState.CapturedAtUtc);
    }

    [Fact]
    public void DesignState_ShouldAcceptMultipleObjStates()
    {
        var designState = new DesignState
        {
            StateId = "DS_multiobj",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        designState.ObjStates.Add(new ObjState
        {
            StateId = "OS_building1",
            ObjectRef = "building-1",
            Label = "Building One",
        });

        designState.ObjStates.Add(new ObjState
        {
            StateId = "OS_building2",
            ObjectRef = "building-2",
            Label = "Building Two",
        });

        Assert.Equal(2, designState.ObjStates.Count);
        Assert.Contains(designState.ObjStates, o => o.ObjectRef == "building-1");
        Assert.Contains(designState.ObjStates, o => o.ObjectRef == "building-2");
    }

    [Fact]
    public void DesignState_ShouldAcceptMultipleParamStates()
    {
        var designState = new DesignState
        {
            StateId = "DS_multiparam",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        designState.ParamStates.Add(new ParamState
        {
            StateId = "PS_param1",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        });

        designState.ParamStates.Add(new ParamState
        {
            StateId = "PS_param2",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        });

        Assert.Equal(2, designState.ParamStates.Count);
    }

    [Fact]
    public void DesignState_ShouldAcceptMultiplePropStates()
    {
        var designState = new DesignState
        {
            StateId = "DS_multiprop",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        designState.PropStates.Add(new PropState
        {
            StateId = "PS_prop1",
            RuleIri = "dgm:Rule_R_HEIGHT_MAX_75",
            DataPropertyIri = "dg:hasHeight",
            PropValue = new DesignStateParameter
            {
                ParameterId = "height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Number,
                NumberValue = 75.0,
            },
        });

        designState.PropStates.Add(new PropState
        {
            StateId = "PS_prop2",
            RuleIri = "dgm:Rule_R_FLOORS_MIN_5",
            DataPropertyIri = "dg:hasFloors",
            PropValue = new DesignStateParameter
            {
                ParameterId = "floors",
                DisplayName = "Floors",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 8,
            },
        });

        Assert.Equal(2, designState.PropStates.Count);
    }

    [Fact]
    public void DesignState_ThreeLists_ShouldBeIndependent()
    {
        // D-02: three inputs are independent bags — no cross-index alignment
        var designState = new DesignState
        {
            StateId = "DS_indep",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        // Add items to one list shouldn't affect the others
        designState.ObjStates.Add(new ObjState { StateId = "OS_1", ObjectRef = "obj-1" });
        designState.ObjStates.Add(new ObjState { StateId = "OS_2", ObjectRef = "obj-2" });

        Assert.Equal(2, designState.ObjStates.Count);
        Assert.Empty(designState.ParamStates);
        Assert.Empty(designState.PropStates);

        // Add to another list independently
        designState.ParamStates.Add(new ParamState { StateId = "PS_p1", CapturedAtUtc = DateTimeOffset.UtcNow });
        designState.ParamStates.Add(new ParamState { StateId = "PS_p2", CapturedAtUtc = DateTimeOffset.UtcNow });
        designState.ParamStates.Add(new ParamState { StateId = "PS_p3", CapturedAtUtc = DateTimeOffset.UtcNow });

        Assert.Equal(2, designState.ObjStates.Count);
        Assert.Equal(3, designState.ParamStates.Count);
        Assert.Empty(designState.PropStates);
    }

    [Fact]
    public void DesignState_ShouldHaveEmptyStateIdByDefault()
    {
        var designState = new DesignState();

        Assert.Equal("", designState.StateId);
        Assert.Empty(designState.ObjStates);
        Assert.Empty(designState.ParamStates);
        Assert.Empty(designState.PropStates);
    }

    [Fact]
    public void DesignState_ShouldPreserveWiringOrder()
    {
        // Internal list ordering preserves wiring order per research recommendation
        var designState = new DesignState
        {
            StateId = "DS_order",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        designState.ObjStates.Add(new ObjState { StateId = "OS_first", ObjectRef = "first" });
        designState.ObjStates.Add(new ObjState { StateId = "OS_second", ObjectRef = "second" });
        designState.ObjStates.Add(new ObjState { StateId = "OS_third", ObjectRef = "third" });

        Assert.Equal("OS_first", designState.ObjStates[0].StateId);
        Assert.Equal("OS_second", designState.ObjStates[1].StateId);
        Assert.Equal("OS_third", designState.ObjStates[2].StateId);
    }
}
