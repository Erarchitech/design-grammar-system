using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class DesignStateDeconstructComponentTests
{
    [Fact]
    public void DesignStateWithItems_ExposesThreeLists()
    {
        var designState = new DesignState
        {
            StateId = "DS_test",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        designState.ObjStates.Add(new ObjState { StateId = "OS_1", ObjectRef = "obj-1" });
        designState.ObjStates.Add(new ObjState { StateId = "OS_2", ObjectRef = "obj-2" });

        designState.ParamStates.Add(new ParamState
        {
            StateId = "PS_1",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        });

        designState.PropStates.Add(new PropState
        {
            StateId = "PR_1",
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
        designState.PropStates.Add(new PropState { StateId = "PR_2", RuleIri = "dgm:Rule_R_HEIGHT_MIN_10", DataPropertyIri = "dg:hasHeight" });
        designState.PropStates.Add(new PropState { StateId = "PR_3", RuleIri = "dgm:Rule_R_FLOORS_MIN_5", DataPropertyIri = "dg:hasFloors" });

        Assert.Equal(2, designState.ObjStates.Count);
        Assert.Single(designState.ParamStates);
        Assert.Equal(3, designState.PropStates.Count);

        Assert.Contains(designState.ObjStates, o => o.ObjectRef == "obj-1");
        Assert.Contains(designState.ObjStates, o => o.ObjectRef == "obj-2");
        Assert.Contains(designState.PropStates, p => p.StateId == "PR_2");
    }

    [Fact]
    public void EmptyBagPassthrough_ProducesEmptyLists()
    {
        var designState = new DesignState
        {
            StateId = "DS_empty",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        Assert.Empty(designState.ObjStates);
        Assert.Empty(designState.ParamStates);
        Assert.Empty(designState.PropStates);

        // D-07: empty lists are valid, no warning needed when passthrough
    }

    [Fact]
    public void DesignStateWithLabel_ExposesLabel()
    {
        var designState = new DesignState
        {
            StateId = "DS_label",
            Label = "My Design State",
            CapturedAtUtc = DateTimeOffset.UtcNow,
        };

        Assert.Equal("My Design State", designState.Label);
        Assert.Equal("DS_label", designState.StateId);

        // Label is independent of the three state lists
        Assert.Empty(designState.ObjStates);
        Assert.Empty(designState.ParamStates);
        Assert.Empty(designState.PropStates);
    }

    [Fact]
    public void DesignState_MissingInput_WarningPattern()
    {
        var inputMissing = ErrorMessageTemplates.DesignStateDeconstructInputMissing();
        Assert.NotEmpty(inputMissing);
        Assert.Contains("DESIGN STATE DECONSTRUCT", inputMissing);
        Assert.Contains("DesignState input", inputMissing);
        Assert.Contains("required", inputMissing);

        var castFailed = ErrorMessageTemplates.DesignStateDeconstructCastFailed();
        Assert.NotEmpty(castFailed);
        Assert.Contains("DESIGN STATE DECONSTRUCT", castFailed);
        Assert.Contains("Could not unwrap", castFailed);
    }
}
