using DG.Core.Classification;
using DG.Core.Models;

namespace DG.Tests;

public sealed class VariableBinderTests
{
    [Fact]
    public void BuildBindings_ShouldZipBranchesByRowIndex()
    {
        var variables = new List<Variable>
        {
            new() { Name = "?b" },
            new() { Name = "?h" },
        };

        var values = new Dictionary<string, IReadOnlyList<object?>>
        {
            ["?b"] = new List<object?> { "B1", "B2" },
            ["?h"] = new List<object?> { 60m, 80m },
        };

        var result = VariableBinder.BuildBindings(variables, values);

        Assert.Equal(2, result.BoundVariables.Count);
        Assert.Equal("B2", result.BoundVariables[1].ValuesByVar["?b"]);
        Assert.Equal(80m, result.BoundVariables[1].ValuesByVar["?h"]);
    }
}
