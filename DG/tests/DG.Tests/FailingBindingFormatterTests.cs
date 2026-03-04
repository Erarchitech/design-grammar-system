using DG.Core.Models;
using DG.Core.Validation;

namespace DG.Tests;

public sealed class FailingBindingFormatterTests
{
    [Fact]
    public void Format_ShouldRenderSingleClassAtomAndSingleFailedValue()
    {
        var rule = new Rule
        {
            Id = "R_URB_HEIGHT_MAX_75_V",
            Swrl = "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["?b"] = "building32";
        binding.ValuesByVar["?h"] = 83;

        var output = FailingBindingFormatter.Format(rule, binding);

        Assert.Equal("b(building32): h(83)", output);
    }

    [Fact]
    public void Format_ShouldRenderSeveralClassAtomVariables()
    {
        var rule = new Rule
        {
            Id = "R_DIST_MIN_6_V",
            Swrl = "Building(?b1)^Building(?b2)^hasDistanceM(?b1,?b2,?d)^swrlb:lessThan(?d,6)->violatesMinDistance(?b1,true)",
        };
        var binding = new BindingRow();
        binding.ValuesByVar["b1"] = "building32";
        binding.ValuesByVar["b2"] = "building15";
        binding.ValuesByVar["d"] = 5;

        var output = FailingBindingFormatter.Format(rule, binding);

        Assert.Equal("b1(building32), b2(building15): d(5)", output);
    }
}
