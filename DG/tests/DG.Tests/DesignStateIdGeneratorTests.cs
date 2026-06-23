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
    public void ComputeDefStateId_ShouldBeDeterministic_RegardlessOfInputOrder()
    {
        var parameters = BuildParameters();
        var reversed = new List<DesignStateParameter>(parameters);
        reversed.Reverse();

        var id1 = DesignStateIdGenerator.ComputeDefStateId(parameters);
        var id2 = DesignStateIdGenerator.ComputeDefStateId(reversed);

        Assert.Equal(id1, id2);
        Assert.StartsWith("DS_", id1);
    }

    [Fact]
    public void ComputeDefStateId_ShouldChange_WhenParameterIsAdded()
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

        var originalId = DesignStateIdGenerator.ComputeDefStateId(parameters);
        var extendedId = DesignStateIdGenerator.ComputeDefStateId(withExtra);

        Assert.NotEqual(originalId, extendedId);
    }

    [Fact]
    public void ComputeObjectStateId_ShouldBeDeterministic_ForSameInputs()
    {
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OI_abc123", "?b");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OI_abc123", "?b");

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
        var id1 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OI_abc123", "?b");
        var id2 = DesignStateIdGenerator.ComputeObjectStateId("proj-1", "OI_different", "?b");

        Assert.NotEqual(id1, id2);
    }

    [Fact]
    public void ComputeObjectInstanceId_ShouldProduceOiPrefixedString()
    {
        var id = DesignStateIdGenerator.ComputeObjectInstanceId("proj-1", "?b", "rhino-guid-1234");

        Assert.StartsWith("OI_", id);
    }
}
