using DG.Core.Models;

namespace DG.Tests;

public sealed class PropStateModelTests
{
    [Fact]
    public void PropState_ShouldSetProperties_ThroughInitOnlySetters()
    {
        var propState = new PropState
        {
            StateId = "PS_abc789",
            RuleIri = "dgm:Rule_R_URB_HEIGHT_MAX_75_V",
            DataPropertyIri = "dg:hasHeight",
            PropValue = new DesignStateParameter
            {
                ParameterId = "height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Number,
                NumberValue = 72.5,
            },
        };

        Assert.Equal("PS_abc789", propState.StateId);
        Assert.Equal("dgm:Rule_R_URB_HEIGHT_MAX_75_V", propState.RuleIri);
        Assert.Equal("dg:hasHeight", propState.DataPropertyIri);
        Assert.NotNull(propState.PropValue);
        Assert.Equal(72.5, propState.PropValue.NumberValue);
    }

    [Fact]
    public void PropState_ShouldAcceptPropValue_AsDesignStateParameter()
    {
        // PropValue reuses DesignStateParameter's typed-nullable pattern per D-08
        var numberProp = new PropState
        {
            StateId = "PS_num",
            RuleIri = "dgm:Rule_R_HEIGHT_MAX_75",
            DataPropertyIri = "dg:hasHeight",
            PropValue = new DesignStateParameter
            {
                ParameterId = "height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Number,
                NumberValue = 75.0,
            },
        };

        Assert.Equal(DesignStateParameterType.Number, numberProp.PropValue!.Type);
        Assert.Equal(75.0, numberProp.PropValue.NumberValue);

        var intProp = new PropState
        {
            StateId = "PS_int",
            RuleIri = "dgm:Rule_R_FLOORS_MIN_5",
            DataPropertyIri = "dg:hasFloors",
            PropValue = new DesignStateParameter
            {
                ParameterId = "floors",
                DisplayName = "Floors",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 8,
            },
        };

        Assert.Equal(DesignStateParameterType.Integer, intProp.PropValue!.Type);
        Assert.Equal(8, intProp.PropValue.IntegerValue);

        var boolProp = new PropState
        {
            StateId = "PS_bool",
            RuleIri = "dgm:Rule_R_HAS_PODIUM",
            DataPropertyIri = "dg:hasPodium",
            PropValue = new DesignStateParameter
            {
                ParameterId = "hasPodium",
                DisplayName = "Has Podium",
                Type = DesignStateParameterType.Boolean,
                BooleanValue = true,
            },
        };

        Assert.Equal(DesignStateParameterType.Boolean, boolProp.PropValue!.Type);
        Assert.True(boolProp.PropValue.BooleanValue);
    }

    [Fact]
    public void PropState_ShouldAcceptIriStrings()
    {
        // Rule and DataProperty stored as plain string IRIs per D-09
        var propState = new PropState
        {
            StateId = "PS_iri",
            RuleIri = "dgm:Rule_R_URB_HEIGHT_MAX_75_V",
            DataPropertyIri = "dg:hasHeight",
        };

        Assert.Equal("dgm:Rule_R_URB_HEIGHT_MAX_75_V", propState.RuleIri);
        Assert.Equal("dg:hasHeight", propState.DataPropertyIri);
    }

    [Fact]
    public void PropState_ShouldHaveEmptyStateIdByDefault()
    {
        var propState = new PropState();

        Assert.Equal("", propState.StateId);
        Assert.Equal("", propState.RuleIri);
        Assert.Equal("", propState.DataPropertyIri);
        Assert.Null(propState.PropValue);
    }

    [Fact]
    public void PropState_ShouldAcceptNullPropValue()
    {
        // PropValue is nullable per D-08 pattern
        var propState = new PropState
        {
            StateId = "PS_null",
            RuleIri = "dgm:Rule_R_TEST",
            DataPropertyIri = "dg:testProp",
            PropValue = null,
        };

        Assert.Null(propState.PropValue);
    }
}
