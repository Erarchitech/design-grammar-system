using DG.Core.Models;
using DG.Core.Services;

namespace DG.Tests;

public sealed class DesignStateIdGeneratorTests
{
    private static List<DesignStateParameter> BuildParameters()
    {
        return new List<DesignStateParameter>
        {
            new()
            {
                ParameterId = "Height",
                DisplayName = "Height",
                Type = DesignStateParameterType.Number,
                NumberValue = 75.0,
            },
            new()
            {
                ParameterId = "Floors",
                DisplayName = "Floors",
                Type = DesignStateParameterType.Integer,
                IntegerValue = 12,
            },
            new()
            {
                ParameterId = "Active",
                DisplayName = "Active",
                Type = DesignStateParameterType.Boolean,
                BooleanValue = true,
            },
        };
    }

    [Fact]
    public void ComputeParamStateId_ShouldBeDeterministic_RegardlessOfInputOrder()
    {
        var parameters = BuildParameters();
        var reversed = new List<DesignStateParameter>(parameters);
        reversed.Reverse();

        var id1 = DesignStateIdGenerator.ComputeParamStateId(parameters);
        var id2 = DesignStateIdGenerator.ComputeParamStateId(reversed);

        Assert.Equal(id1, id2);
        Assert.StartsWith("DS_", id1);
    }

    [Fact]
    public void ComputeParamStateId_ShouldChange_WhenParameterIsAdded()
    {
        var parameters = BuildParameters();
        var withExtra = new List<DesignStateParameter>(parameters)
        {
            new()
            {
                ParameterId = "ExtraParam",
                DisplayName = "ExtraParam",
                Type = DesignStateParameterType.Boolean,
                BooleanValue = false,
            },
        };

        var originalId = DesignStateIdGenerator.ComputeParamStateId(parameters);
        var extendedId = DesignStateIdGenerator.ComputeParamStateId(withExtra);

        Assert.NotEqual(originalId, extendedId);
    }

    [Fact]
    public void ComputeObjectStateId_ShouldBeDeterministic_ForSameInputs()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");

        Assert.Equal(id1, id2);
        Assert.StartsWith("OS_", id1);
    }

    [Fact]
    public void ComputeObjectStateId_ShouldHaveExactlyThreeStringParameters_ProvingCrossRuleIdentity()
    {
        var method = typeof(DesignStateIdGenerator).GetMethod("ComputeObjectStateId");

        Assert.NotNull(method);
        var parameters = method!.GetParameters();
        Assert.Equal(3, parameters.Length);
        Assert.All(parameters, p => Assert.Equal(typeof(string), p.ParameterType));
        Assert.DoesNotContain(parameters, p => string.Equals(p.Name, "ruleId", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ComputeObjectStateId_ShouldChange_WhenObjectInstanceIdChanges()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_abc123", "?b");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OS_different", "?b");

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputePropStateId_ShouldBeDeterministic_ForSameInputs()
    {
        var ruleIri = "dgm:Rule_R_URB_HEIGHT_MAX_75_V";
        var dataPropertyIri = "dg:hasHeight";
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId(ruleIri, dataPropertyIri, value);
        var id2 = DesignStateIdGenerator.ComputePropStateId(ruleIri, dataPropertyIri, value);

        Assert.Equal(id1, id2);
        Assert.StartsWith("PS_", id1);
    }

    [Fact]
    public void ComputePropStateId_ShouldChange_WhenRuleIriChanges()
    {
        var value = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value);
        var id2 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_SETBACK_MIN_10_V", "dg:hasHeight", value);

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputePropStateId_ShouldChange_WhenValueChanges()
    {
        var value1 = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 75.0,
        };
        var value2 = new DesignStateParameter
        {
            ParameterId = "height",
            DisplayName = "Height",
            Type = DesignStateParameterType.Number,
            NumberValue = 100.0,
        };

        var id1 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value1);
        var id2 = DesignStateIdGenerator.ComputePropStateId("dgm:Rule_R_URB_HEIGHT_MAX_75_V", "dg:hasHeight", value2);

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputeDesignStateId_ShouldBeDeterministic_ForSameMemberIds()
    {
        var memberIds = new List<string> { "OS_abc123", "DS_def456", "PS_ghi789" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(memberIds);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(memberIds);

        Assert.Equal(id1, id2);
        Assert.StartsWith("DS_", id1);
    }

    [Fact]
    public void ComputeDesignStateId_ShouldBeDeterministic_RegardlessOfOrder()
    {
        var ordered = new List<string> { "OS_abc", "PS_def", "DS_ghi" };
        var reversed = new List<string> { "DS_ghi", "PS_def", "OS_abc" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(ordered);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(reversed);

        Assert.Equal(id1, id2);
    }

    [Fact]
    public void ComputeDesignStateId_ShouldChange_WhenMembersChange()
    {
        var members1 = new List<string> { "OS_abc", "DS_def" };
        var members2 = new List<string> { "OS_abc", "DS_xyz" };

        var id1 = DesignStateIdGenerator.ComputeDesignStateId(members1);
        var id2 = DesignStateIdGenerator.ComputeDesignStateId(members2);

        Assert.NotEqual(id1, id2);
    }
}
